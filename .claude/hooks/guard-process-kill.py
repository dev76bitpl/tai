#!/usr/bin/env python3
"""
Guard: no killing processes by name or pattern (PreToolUse on Bash|PowerShell).

Why: the AI runs its own dev server next to the user's. A kill by *name* ("next dev", "node",
"php artisan serve") hits both instances — the user's server dies "by accident", the shared
build cache corrupts, and the session derails into phantom 404s. Seen repeatedly; a rule alone
did not stop it, so the command is blocked before it runs.

Blocked (exit 2 + stderr):
  - name/pattern kills: pkill, killall, pgrep, taskkill /IM, Stop-Process -Name, Get-Process <name> | Stop-Process
  - port-based kills aimed at a user port (config.json "dev_user_ports", default [3000]):
    fuser -k 3000/tcp, lsof -ti:3000 | xargs kill, kill-port 3000, Get-NetTCPConnection -LocalPort 3000
  - kill with an unresolved target (command substitution / xargs that is not a .pid file)

Allowed:
  - kill <numeric pid>, kill $(cat something.pid), Stop-Process -Id <pid>
  - port-based kills on any port that is NOT a user port (i.e. the AI's own port)
  - docker kill/stop (containers, not dev processes)

No bypass flag on purpose: if the user's server really must go down, the user runs the command
(CLAUDE.md 3d — ask, wait for consent, restore afterwards).

Self-test: python3 guard-process-kill.py --self-test
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_USER_PORTS = [3000]

NAME_KILL = re.compile(
    r"(?<![\w-])(pkill|killall|pgrep)\b"
    r"|taskkill\b[^\n|;&]*?/IM\b"
    r"|Stop-Process\b[^\n|;&]*?-Name\b"
    r"|Get-Process\s+(?!-Id\b)[^\n|;&]*\|\s*Stop-Process",
    re.IGNORECASE,
)
KILL_VERB = re.compile(
    r"(?<![\w-])(kill|fuser\s+-k|kill-port|taskkill|Stop-Process)\b"
    r"|Get-NetTCPConnection\b",
    re.IGNORECASE,
)
DOCKER_KILL = re.compile(r"\bdocker(\s+\w+)*\s+(kill|stop)\b", re.IGNORECASE)
PORT_REFS = re.compile(
    r"(?:-i\s*:?|:|-LocalPort\s+|kill-port\s+)(\d{2,5})\b|(\d{2,5})/(?:tcp|udp)\b",
    re.IGNORECASE,
)
PID_FILE_SUBST = re.compile(r"\$\(\s*cat\s+[^)]*\.pid\s*\)|`\s*cat\s+[^`]*\.pid\s*`|Get-Content\s+[^\s|;]*\.pid", re.IGNORECASE)
UNRESOLVED = re.compile(r"\$\(|`|\bxargs\b|\|\s*kill\b", re.IGNORECASE)
NUMERIC_KILL = re.compile(r"(?<![\w-])kill\s+(?:-\w+\s+|--\s+)*-?\d+(\s+-?\d+)*\s*(?:[;&|\n]|$)|Stop-Process\b[^\n|;&]*-Id\s+\d+", re.IGNORECASE)


def user_ports() -> list[int]:
    try:
        from stack import load_config  # type: ignore
        ports = load_config().get("dev_user_ports")
        if isinstance(ports, list) and ports:
            return [int(p) for p in ports]
    except Exception:
        pass
    return DEFAULT_USER_PORTS


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\b", re.DOTALL)
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'[^']*'")


def executable_text(command: str) -> str:
    """The parts of a command that actually run: heredoc bodies and quoted strings are data
    (commit messages, docs being written, grep patterns), not process kills."""
    return QUOTED.sub("''", HEREDOC.sub("", command))


def verdict(command: str, ports: list[int] | None = None) -> str | None:
    """None = allowed; otherwise the reason to block."""
    ports = DEFAULT_USER_PORTS if ports is None else ports
    stripped = DOCKER_KILL.sub("", executable_text(command))
    if not KILL_VERB.search(stripped) and not NAME_KILL.search(stripped):
        return None
    if NAME_KILL.search(stripped):
        return "kill by process NAME or PATTERN — hits the user's instance as well as yours"
    referenced = [int(p) for m in PORT_REFS.finditer(stripped) for p in m.groups() if p]
    if referenced:
        hit = [p for p in referenced if p in ports]
        if hit:
            return f"kill aimed at the user's port {hit[0]} — that server is not yours"
        return None  # port-based kill on the AI's own port
    if PID_FILE_SUBST.search(stripped) or NUMERIC_KILL.search(stripped):
        return None
    if UNRESOLVED.search(stripped):
        return "kill with an unresolved target (substitution / xargs) — cannot tell whose process dies"
    return None


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def main() -> None:
    command = get_command()
    reason = verdict(command, user_ports())
    if reason is None:
        sys.exit(0)
    ports = ", ".join(str(p) for p in user_ports())
    print(
        "❌ [BLOCK] guard-process-kill: " + reason + "\n"
        f"User ports: {ports}. Stop ONLY your own instance, addressed by what is unique to it:\n"
        "  - by its port:  fuser -k <ai-port>/tcp   |  Stop-Process -Id (Get-NetTCPConnection -LocalPort <ai-port>).OwningProcess\n"
        "  - by its pid:   kill $(cat <file>.pid)    (record the pid when you start the server)\n"
        "Never by name (pkill/killall/taskkill /IM/Stop-Process -Name). If the user's server must stop,\n"
        "hand the command to the user and wait (CLAUDE.md 3d). No bypass flag for this guard.",
        file=sys.stderr,
    )
    sys.exit(2)


SELF_TEST: list[tuple[str, bool]] = [
    # (command, should_block)
    ('pkill -f "next dev" -u 1000', True),
    ("killall node", True),
    ("kill $(pgrep -f 'next dev')", True),
    ("taskkill /F /IM node.exe", True),
    ("Stop-Process -Name node -Force", True),
    ("Get-Process node | Stop-Process -Force", True),
    ("fuser -k 3000/tcp", True),
    ("lsof -ti:3000 | xargs kill -9", True),
    ("npx kill-port 3000", True),
    ("Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess", True),
    ("kill $(lsof -t -i :3000)", True),
    ("ps aux | grep next | awk '{print $2}' | xargs kill", True),
    ("fuser -k 3100/tcp", False),
    ("lsof -ti:3100 | xargs kill", False),
    ("Stop-Process -Id (Get-NetTCPConnection -LocalPort 3100).OwningProcess", False),
    ("kill 12345", False),
    ("kill -9 12345", False),
    ("kill -TERM 12345 67890", False),
    ("kill $(cat /tmp/x/dev-ai.pid)", False),
    ("Stop-Process -Id 4242", False),
    ("docker kill skolaro-postgres-1", False),
    ("docker compose stop", False),
    ("npm run dev:ai", False),
    ("git commit -m 'fix: killer feature'", False),
    ("grep -rn skill src", False),
    # data, not commands: heredoc bodies and quoted strings
    ("cat > docs/X.md <<'EOF'\nNever run pkill -f \"next dev\" or killall node.\nEOF\n", False),
    ("git commit -m \"docs: forbid pkill -f and taskkill /IM\"", False),
    ("python3 - <<'EOF'\ns = 'Stop-Process -Name node'\nEOF\necho done", False),
    ("grep -rn 'pkill' .claude/hooks", False),
    # ...but the command itself still counts even with quoted args
    ("pkill -f 'next dev'", True),
    ("echo x; killall 'node'", True),
]


def self_test() -> None:
    failed = 0
    for cmd, should_block in SELF_TEST:
        blocked = verdict(cmd, DEFAULT_USER_PORTS) is not None
        if blocked != should_block:
            failed += 1
            print(f"FAIL  expected {'BLOCK' if should_block else 'allow'}: {cmd}")
    print(f"{len(SELF_TEST) - failed}/{len(SELF_TEST)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    main()
