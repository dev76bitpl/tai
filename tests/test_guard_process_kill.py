"""Tests for .claude/hooks/guard-process-kill.py (CLAUDE.md 3d — never kill by name/pattern).

The hook blocks process kills that cannot be proven to target only the AI's own instance:
kills by name/pattern, kills aimed at the user's dev port, kills with an unresolved target.
Text inside heredocs and quoted strings is data (commit messages, docs), never a kill.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard-process-kill.py"


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
