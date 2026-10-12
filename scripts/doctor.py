#!/usr/bin/env python3
"""Health check for developer environment.

Run: `npm run doctor` or `python scripts/doctor.py`

Reports prerequisites:
  - Python ≥ 3.9
  - Node ≥ 22
  - pre-commit installed + hooks linked into .git/hooks
  - .pre-commit-config.yaml present and parseable
  - pytest available (optional — runs the guard tests)
  - Claude Code hooks wired in .claude/settings.local.json (per machine)
  - AI template source: $AI_TEMPLATE_PATH, config.local.json or config.json (optional)
  - Docker running (optional but recommended)

Exit code 0 if all REQUIRED checks pass (optional checks may be ✗ without
failing the overall exit code). Exit code 1 if any required check fails.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Enable ANSI escape sequences on Windows 10+ terminals (cmd.exe, Windows Terminal).
if os.name == "nt":
    os.system("")

REPO_ROOT = Path(__file__).resolve().parent.parent

_USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"


def _c(code: str) -> str:
    return code if _USE_COLOR else ""


GREEN = _c("\033[32m")
RED = _c("\033[31m")
YELLOW = _c("\033[33m")
DIM = _c("\033[2m")
RESET = _c("\033[0m")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str, hint: str = "") -> None:
    print(f"  {RED}✗{RESET} {msg}")
    if hint:
        print(f"    {DIM}{hint}{RESET}")


def warn(msg: str, hint: str = "") -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")
    if hint:
        print(f"    {DIM}{hint}{RESET}")


def header(msg: str) -> None:
    print(f"\n{msg}")


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, (result.stdout + result.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1, ""


def check_python() -> bool:
    if sys.version_info < (3, 9):
        fail(
            f"Python {sys.version_info.major}.{sys.version_info.minor} — required: 3.9+",
            "Install Python 3.9 or newer.",
        )
        return False
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_node() -> bool:
    if not shutil.which("node"):
        fail("node not in PATH", "Install Node.js 22+ — see docs/SETUP.md step 1.")
        return False
    code, out = run(["node", "--version"])
    if code != 0:
        fail("node --version failed")
        return False
    version = out.lstrip("v").split(".")[0]
    try:
        major = int(version)
    except ValueError:
        warn(f"node version unrecognized: {out}")
        return True
    if major < 22:
        fail(f"node {out} — required: 22+", "Upgrade via nvm.")
        return False
    ok(f"node {out}")
    return True


_PRE_COMMIT_INVOCATION: list[str] | None = None


def _resolve_pre_commit() -> list[str] | None:
    """Returns the argv prefix needed to invoke pre-commit, or None if unavailable.

    Tries standalone binary first, then `python -m pre_commit` (works on Windows
    after `pip install --user` when Scripts/ isn't on PATH).
    """
    global _PRE_COMMIT_INVOCATION
    if _PRE_COMMIT_INVOCATION is not None:
        return _PRE_COMMIT_INVOCATION
    if shutil.which("pre-commit"):
        code, _ = run(["pre-commit", "--version"])
        if code == 0:
            _PRE_COMMIT_INVOCATION = ["pre-commit"]
            return _PRE_COMMIT_INVOCATION
    for py in ("python", "python3", "py"):
        if not shutil.which(py):
            continue
        code, _ = run([py, "-m", "pre_commit", "--version"])
        if code == 0:
            _PRE_COMMIT_INVOCATION = [py, "-m", "pre_commit"]
            return _PRE_COMMIT_INVOCATION
    return None


def check_pre_commit() -> bool:
    invocation = _resolve_pre_commit()
    if invocation is None:
        fail(
            "pre-commit not available",
            "Install via: python -m pip install --user pre-commit  (or rerun `npm install`)",
        )
        return False
    code, out = run([*invocation, "--version"])
    if code != 0:
        fail(f"{' '.join(invocation)} --version failed")
        return False
    via = "standalone" if invocation == ["pre-commit"] else f"via {' '.join(invocation[:-1])}"
    ok(f"{out}  ({via})")
    return True


def check_hooks_installed() -> bool:
    pre_commit_hook = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    commit_msg_hook = REPO_ROOT / ".git" / "hooks" / "commit-msg"
    if not pre_commit_hook.is_file():
        fail(
            ".git/hooks/pre-commit not installed",
            "Run: pre-commit install --hook-type pre-commit --hook-type commit-msg",
        )
        return False
    if not commit_msg_hook.is_file():
        fail(
            ".git/hooks/commit-msg not installed",
            "Run: pre-commit install --hook-type commit-msg",
        )
        return False
    # Sanity check: pre-commit framework writes a marker line in its hook scripts.
    content = pre_commit_hook.read_text(encoding="utf-8", errors="ignore")
    if "pre-commit" not in content.lower():
        warn(
            ".git/hooks/pre-commit exists but doesn't look like pre-commit framework",
            "May be a stale hook — reinstall with: pre-commit install",
        )
        return False
    ok("Git hooks installed (pre-commit + commit-msg)")
    return True


def check_config_yaml() -> bool:
    config = REPO_ROOT / ".pre-commit-config.yaml"
    if not config.is_file():
        fail(".pre-commit-config.yaml missing at repo root")
        return False
    invocation = _resolve_pre_commit()
    if invocation is None:
        warn(".pre-commit-config.yaml not validated (pre-commit unavailable)")
        return False
    code, out = run([*invocation, "validate-config"])
    if code != 0:
        fail(".pre-commit-config.yaml invalid", out[-500:] if out else "")
        return False
    ok(".pre-commit-config.yaml valid")
    return True


def check_pytest() -> None:
    code, out = run([sys.executable, "-m", "pytest", "--version"])
    if code != 0:
        warn(
            "pytest not available (optional) — guard tests cannot run on this machine",
            "Install via: python3 -m pip install --user pytest"
            "  (Ubuntu 24.04+, where pip is blocked by PEP 668: sudo apt install python3-pytest)",
        )
        return
    ok(out.splitlines()[0] if out else "pytest available")


_INTERPRETER_PLACEHOLDER = re.compile(r"\bINTERPRETER\b")


def _hook_commands(node) -> list[str]:
    """Every hook `command` string found anywhere in a parsed settings file."""
    if isinstance(node, dict):
        found = [v for k, v in node.items() if k == "command" and isinstance(v, str)]
        for value in node.values():
            found.extend(_hook_commands(value))
        return found
    if isinstance(node, list):
        return [cmd for item in node for cmd in _hook_commands(item)]
    return []


def check_claude_hooks() -> bool:
    """Claude Code layer: are the guard hooks from .claude/hooks/ wired on this machine?

    The commit layer (pre-commit) can be fully green while this one is dead, because the
    hook commands live in a per-machine, gitignored file.
    """
    claude_dir = REPO_ROOT / ".claude"
    local = claude_dir / "settings.local.json"
    if not local.is_file():
        warn(
            ".claude/settings.local.json missing — no Claude Code hook runs on this machine",
            "Run: cp .claude/settings.local.json.example .claude/settings.local.json"
            "  then replace INTERPRETER (python3 / py) — see docs/SETUP.md step 8a.",
        )
        return True

    try:
        local_data = json.loads(local.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        fail(
            ".claude/settings.local.json unreadable — no Claude Code hook can run",
            "Fix the JSON or recreate the file from .claude/settings.local.json.example.",
        )
        return False

    commands = _hook_commands(local_data.get("hooks", {}) if isinstance(local_data, dict) else {})
    healthy = True

    if any(_INTERPRETER_PLACEHOLDER.search(cmd) for cmd in commands):
        fail(
            ".claude/settings.local.json still contains the INTERPRETER placeholder — every hook fails to start",
            "Replace INTERPRETER with python3 (Ubuntu/macOS) or py (Windows) — see docs/SETUP.md step 8a.",
        )
        healthy = False

    # Hooks may also be wired in the shared settings.json; a guard counts when either file runs it.
    shared = claude_dir / "settings.json"
    if shared.is_file():
        try:
            shared_data = json.loads(shared.read_text(encoding="utf-8"))
            if isinstance(shared_data, dict):
                commands += _hook_commands(shared_data.get("hooks", {}))
        except (json.JSONDecodeError, OSError):
            pass

    guards = sorted(path.name for path in (claude_dir / "hooks").glob("guard-*.py"))
    unwired = [name for name in guards if not any(name in cmd for cmd in commands)]
    if unwired:
        warn(
            f"Guard hooks present in .claude/hooks/ but not wired: {', '.join(unwired)}",
            "Copy their entries from .claude/settings.local.json.example into .claude/settings.local.json.",
        )
    elif healthy:
        ok(f"Claude Code hooks wired ({len(guards)} guard hook(s))")
    return healthy


def _load_hook_config() -> tuple[dict, str]:
    """config.json overlaid with config.local.json (per machine) — as the guards read it.

    Returns the merged config and the name of the file that supplied ai_template_path.
    """
    merged: dict = {}
    source = ""
    for name in ("config.json", "config.local.json"):
        path = REPO_ROOT / ".claude" / "hooks" / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            warn(f".claude/hooks/{name} present but unparseable — ignored by the guards")
            continue
        if isinstance(data, dict):
            merged.update(data)
            if "ai_template_path" in data:
                source = name
    return merged, source


def check_claude_template_path() -> None:
    """Where the template comes from: $AI_TEMPLATE_PATH > config.local.json > config.json."""
    config, source = _load_hook_config()
    if config.get("is_template") is True:
        ok("This repo is the AI template — nothing to sync from")
        return

    template = os.environ.get("AI_TEMPLATE_PATH", "").strip()
    if template:
        source = "$AI_TEMPLATE_PATH"
    else:
        template = str(config.get("ai_template_path", "") or "").strip()
    if not template:
        warn(
            "ai_template_path not set (optional)",
            "Set $AI_TEMPLATE_PATH or put it in .claude/hooks/config.local.json — see docs/SETUP.md step 8b.",
        )
        return
    if "://" in template or template.startswith("git@"):
        ok(f"AI template repo: {template}  (remote, from {source})")
        return
    if not Path(template).expanduser().is_dir():
        warn(
            f"ai_template_path doesn't exist: {template}  (from {source})",
            "AI template sync guard will skip silently.",
        )
        return
    ok(f"AI template repo: {template}  (from {source})")


def check_docker() -> None:
    if not shutil.which("docker"):
        warn("docker not in PATH (optional)", "Required to run the dev database.")
        return
    code, _ = run(["docker", "ps"])
    if code != 0:
        warn("docker installed but daemon not running")
        return
    ok("docker daemon running")


def check_git_branch() -> None:
    code, out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        return
    branch = out.strip()
    if branch in ("main", "master"):
        warn(
            f"Currently on branch '{branch}'",
            "no-commit-to-branch will block commits. Switch via: git checkout -b feat/your-task",
        )
    else:
        ok(f"On branch: {branch}")


def main() -> int:
    print("Developer environment health check\n" + "=" * 35)

    required: list[bool] = []

    header("Prerequisites")
    required.append(check_python())
    required.append(check_node())

    header("Guard system")
    required.append(check_pre_commit())
    required.append(check_hooks_installed())
    required.append(check_config_yaml())
    check_pytest()

    header("Claude Code hooks")
    required.append(check_claude_hooks())

    header("Optional integrations")
    check_claude_template_path()
    check_docker()

    header("Repository state")
    check_git_branch()

    print()
    if all(required):
        print(f"{GREEN}All required checks passed.{RESET}")
        return 0
    failed_count = sum(1 for r in required if not r)
    print(f"{RED}{failed_count} required check(s) failed — see hints above.{RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
