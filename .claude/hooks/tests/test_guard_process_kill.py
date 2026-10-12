"""Tests for .claude/hooks/guard-process-kill.py (CLAUDE.md 3d — never kill by name/pattern).

The hook blocks process kills that cannot be proven to target only the AI's own instance:
kills by name/pattern, kills aimed at the user's dev port, kills with an unresolved target.
Text inside heredocs and quoted strings is data (commit messages, docs), never a kill.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "guard-process-kill.py"


def _load():
    sys.modules.pop("stack", None)
    spec = importlib.util.spec_from_file_location("guard_process_kill", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def guard():
    return _load()


@pytest.mark.parametrize("cmd", [
    'pkill -f "next dev" -u 1000',
    "killall node",
    "kill $(pgrep -f 'php artisan serve')",
    "taskkill /F /IM node.exe",
    "Stop-Process -Name node -Force",
    "Get-Process node | Stop-Process -Force",
    "echo x; killall 'node'",
])
def test_should_block_kill_by_name_or_pattern(guard, cmd):
    assert guard.verdict(cmd, [3000]) is not None


@pytest.mark.parametrize("cmd", [
    "fuser -k 3000/tcp",
    "lsof -ti:3000 | xargs kill -9",
    "npx kill-port 3000",
    "Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess",
    "kill $(lsof -t -i :3000)",
])
def test_should_block_kill_aimed_at_user_port(guard, cmd):
    assert "port 3000" in guard.verdict(cmd, [3000])


def test_should_honour_configured_user_ports(guard):
    assert guard.verdict("fuser -k 8000/tcp", [8000]) is not None
    assert guard.verdict("fuser -k 3000/tcp", [8000]) is None


def test_should_block_kill_with_unresolved_target(guard):
    assert guard.verdict("ps aux | grep next | awk '{print $2}' | xargs kill", [3000]) is not None


@pytest.mark.parametrize("cmd", [
    "fuser -k 3100/tcp",
    "lsof -ti:3100 | xargs kill",
    "Stop-Process -Id (Get-NetTCPConnection -LocalPort 3100).OwningProcess",
    "kill 12345",
    "kill -9 12345",
    "kill -TERM 12345 67890",
    "kill $(cat /tmp/x/dev-ai.pid)",
    "Stop-Process -Id 4242",
])
def test_should_allow_kill_of_own_instance_by_port_or_pid(guard, cmd):
    assert guard.verdict(cmd, [3000]) is None


@pytest.mark.parametrize("cmd", [
    "docker kill my-postgres",
    "docker compose stop",
    "npm run dev:ai",
    "git commit -m 'fix: killer feature'",
    "grep -rn skill src",
    "cat > docs/X.md <<'EOF'\nNever run pkill -f \"next dev\" or killall node.\nEOF\n",
    'git commit -m "docs: forbid pkill -f and taskkill /IM"',
    "python3 - <<'EOF'\ns = 'Stop-Process -Name node'\nEOF\necho done",
    "grep -rn 'pkill' .claude/hooks",
])
def test_should_ignore_data_and_unrelated_commands(guard, cmd):
    assert guard.verdict(cmd, [3000]) is None


def test_self_test_cases_all_pass(guard):
    for cmd, should_block in guard.SELF_TEST:
        assert (guard.verdict(cmd, guard.DEFAULT_USER_PORTS) is not None) == should_block, cmd


# ── end to end: the hook as a separate process, exit code checked ────────────
# Everything above calls verdict() directly, so it cannot see the two things Claude Code
# actually depends on: how the hook reads its payload from stdin and which exit code it ends
# with. Only exit code 2 blocks a tool call — 1 is a non-blocking error. These tests run the
# real script and assert the exact code; change sys.exit(2) in main() to 1 and they fail
# while every verdict() test stays green.

import json  # noqa: E402
import subprocess  # noqa: E402


def run_hook(command: str, tool_name: str | None = "Bash") -> subprocess.CompletedProcess:
    data = {"tool_input": {"command": command}}
    if tool_name is not None:
        data["tool_name"] = tool_name
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
    )


@pytest.mark.parametrize("cmd", [
    "killall node",
    'pkill -f "next dev"',
    "ps aux | grep next | awk '{print $2}' | xargs kill",
    'echo "zażółć gęślą jaźń" && killall node',
])
def test_should_exit_2_and_explain_when_kill_is_blocked(cmd):
    result = run_hook(cmd)
    assert result.returncode == 2
    assert "[BLOCK] guard-process-kill" in result.stderr.decode("utf-8")


@pytest.mark.parametrize("cmd", [
    "kill 12345",
    "kill $(cat /tmp/x/dev-ai.pid)",
    "npm run dev:ai",
    'git commit -m "docs: forbid pkill -f and taskkill /IM"',
    'echo "zażółć gęślą jaźń"',
])
def test_should_exit_0_silently_when_command_is_allowed(cmd):
    result = run_hook(cmd)
    assert result.returncode == 0
    assert result.stderr == b""


def test_should_block_and_allow_the_same_way_without_tool_name():
    # The payload shape used when feeding the hook by hand.
    assert run_hook("killall node", tool_name=None).returncode == 2
    assert run_hook("kill 12345", tool_name=None).returncode == 0


def test_should_block_under_powershell_tool_name():
    assert run_hook("Stop-Process -Name node -Force", tool_name="PowerShell").returncode == 2


def test_should_exit_2_when_input_is_not_json():
    result = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True)
    assert result.returncode == 2
    assert "cannot read its own input" in result.stderr.decode("utf-8")
