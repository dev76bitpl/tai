"""Tests for the input boundary shared by every blocking PreToolUse hook (stack.read_command).

A hook that cannot read its own input must BLOCK (exit 2), not pass: a guard that passes on
garbage looks exactly like a guard that found nothing wrong. The same boundary must not start
blocking tools the hook has no business with (Edit, Write, ...).

The hooks run here as separate processes with the payload on stdin and the exact exit code is
asserted — Claude Code blocks only on 2, so "non-zero" would hide a crash (exit 1 = no block).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
BLOCKING_HOOKS = [
    "guard-process-kill",
    "guard-template-sync",
    "guard-ai-template",
    "guard-testing-checklist",
]


def _load_stack():
    spec = importlib.util.spec_from_file_location("hooks_stack_under_test", HOOKS / "stack.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stack = _load_stack()


def run_hook(name: str, stdin: bytes, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / f"{name}.py")],
        input=stdin, cwd=cwd, capture_output=True,
    )


def payload(**data) -> bytes:
    return json.dumps(data).encode("utf-8")


UNREADABLE = {
    "empty": b"",
    "whitespace": b"  \n",
    "not_json": b"not json",
    "json_array": b'["git commit"]',
    "json_string": b'"git commit"',
    "not_utf8": '{"tool_input":{"command":"echo zażółć"}}'.encode("cp1250"),
    "no_tool_input": payload(tool_name="Bash"),
    "tool_input_not_object": payload(tool_name="Bash", tool_input="ls"),
    "no_command": payload(tool_name="Bash", tool_input={"description": "x"}),
    "command_not_string": payload(tool_name="PowerShell", tool_input={"command": ["ls"]}),
    "no_tool_name_no_command": payload(tool_input={}),
}


# ── parse_hook_input: the three outcomes ──────────────────────────────────────

@pytest.mark.parametrize("raw", UNREADABLE.values(), ids=UNREADABLE.keys())
def test_should_report_error_when_input_cannot_be_read(raw):
    command, error = stack.parse_hook_input(raw)
    assert command is None and error


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_should_return_command_for_shell_tools(tool):
    assert stack.parse_hook_input(payload(tool_name=tool, tool_input={"command": "ls -la"})) == ("ls -la", None)


def test_should_return_command_when_tool_name_is_absent():
    # How a guard is fed by hand: echo '{"tool_input":{"command":"..."}}' | guard.py
    assert stack.parse_hook_input(b'{"tool_input":{"command":"ls"}}') == ("ls", None)


def test_should_return_empty_command_as_a_command():
    assert stack.parse_hook_input(payload(tool_name="Bash", tool_input={"command": ""})) == ("", None)


def test_should_keep_non_ascii_command_intact():
    raw = '{"tool_name":"Bash","tool_input":{"command":"echo zażółć gęślą jaźń"}}'.encode("utf-8")
    assert stack.parse_hook_input(raw) == ("echo zażółć gęślą jaźń", None)


@pytest.mark.parametrize("tool", ["Edit", "Write", "Read", "mcp__x__y"])
def test_should_treat_other_tools_as_not_its_business(tool):
    assert stack.parse_hook_input(payload(tool_name=tool, tool_input={"file_path": "x"})) == (None, None)


# ── every blocking hook, end to end ───────────────────────────────────────────

@pytest.mark.parametrize("hook", BLOCKING_HOOKS)
@pytest.mark.parametrize("raw", UNREADABLE.values(), ids=UNREADABLE.keys())
def test_should_exit_2_when_hook_cannot_read_its_input(hook, raw, tmp_path):
    result = run_hook(hook, raw, tmp_path)
    assert result.returncode == 2, result.stderr.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8")
    assert f"[BLOCK] {hook}: cannot read its own input" in stderr
    assert "Traceback" not in stderr


@pytest.mark.parametrize("hook", BLOCKING_HOOKS)
def test_should_exit_0_when_payload_is_for_another_tool(hook, tmp_path):
    result = run_hook(hook, payload(tool_name="Edit", tool_input={"file_path": "a.py"}), tmp_path)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert result.stderr == b""


@pytest.mark.parametrize("hook", BLOCKING_HOOKS)
@pytest.mark.parametrize("raw", [
    payload(tool_name="Bash", tool_input={"command": "ls -la"}),
    payload(tool_input={"command": "ls -la"}),
    payload(tool_name="Bash", tool_input={"command": ""}),
    '{"tool_name":"Bash","tool_input":{"command":"echo zażółć gęślą jaźń"}}'.encode("utf-8"),
], ids=["shell", "no_tool_name", "empty_command", "non_ascii"])
def test_should_exit_0_for_a_readable_harmless_command(hook, raw, tmp_path):
    result = run_hook(hook, raw, tmp_path)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def test_should_list_every_blocking_hook_registered_in_settings_example():
    # A new PreToolUse hook must join BLOCKING_HOOKS, otherwise its input boundary is unproven.
    example = json.loads((HOOKS.parent / "settings.local.json.example").read_text(encoding="utf-8"))
    registered = {
        Path(h["command"].split()[-1]).stem
        for entry in example["hooks"]["PreToolUse"] for h in entry["hooks"]
    }
    assert registered == set(BLOCKING_HOOKS)
