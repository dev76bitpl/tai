"""Tests for .claude/hooks/guard-pr-merge.py (green CI before merge, tai#211).

The hook intercepts `gh pr merge` and blocks it unless the PR's CI is green. The CI state
comes from `gh pr view --json statusCheckRollup`; the tests monkeypatch that call so they are
deterministic and never touch the network. The end-to-end block exits 2 (Claude Code blocks a
tool call only on 2); the gh-independent paths (not a merge, bypass flag, unreadable input)
are also run as a real process with the exit code asserted.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "guard-pr-merge.py"


def _load():
    sys.modules.pop("stack", None)
    spec = importlib.util.spec_from_file_location("guard_pr_merge", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def guard():
    return _load()


def _fake_checks(result):
    """A fetch_checks replacement returning a fixed (checks, error)."""
    return lambda ref: result


CHECK_PASS = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS", "name": "Guards"}
CHECK_FAIL = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "FAILURE", "name": "Guards"}
CHECK_RUNNING = {"__typename": "CheckRun", "status": "IN_PROGRESS", "conclusion": None, "name": "Guards"}
CHECK_SKIP = {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SKIPPED", "name": "Guards"}
CTX_PASS = {"__typename": "StatusContext", "state": "SUCCESS", "context": "ci/ext"}
CTX_PENDING = {"__typename": "StatusContext", "state": "PENDING", "context": "ci/ext"}


# ── detection: is this actually a `gh pr merge` command? ──────────────────────

@pytest.mark.parametrize("cmd", [
    "gh pr merge 48 --squash --delete-branch",
    "gh pr merge --squash",
    "gh pr merge https://github.com/o/r/pull/7 --merge",
    "git fetch && gh pr merge 3 --rebase",
])
def test_should_detect_a_merge_command(guard, cmd):
    assert guard.is_merge_command(cmd)


@pytest.mark.parametrize("cmd", [
    "gh pr view 48 --json statusCheckRollup",
    "gh pr list",
    "git commit -m 'chore: document gh pr merge policy'",   # a mention in a message
    "echo 'run gh pr merge later'",                          # a mention in a string
    "cat <<'EOF'\nthen gh pr merge 48\nEOF",                 # a mention in a heredoc body
    "ls -la",
])
def test_should_not_detect_a_non_merge_command(guard, cmd):
    assert not guard.is_merge_command(cmd)


def test_should_read_the_positional_pr_ref(guard):
    assert guard.pr_ref("gh pr merge 48 --squash") == "48"
    assert guard.pr_ref("gh pr merge --squash") == ""   # current branch's PR


# ── classify one check ────────────────────────────────────────────────────────

def test_should_classify_each_check_state(guard):
    assert guard.classify(CHECK_PASS) == "pass"
    assert guard.classify(CHECK_SKIP) == "pass"
    assert guard.classify(CHECK_FAIL) == "fail"
    assert guard.classify(CHECK_RUNNING) == "pending"
    assert guard.classify(CTX_PASS) == "pass"
    assert guard.classify(CTX_PENDING) == "pending"


# ── verdict: the whole decision, with gh mocked ───────────────────────────────

def test_should_allow_when_all_checks_are_green(guard):
    guard.fetch_checks = _fake_checks(([CHECK_PASS, CTX_PASS, CHECK_SKIP], None))
    assert guard.verdict("gh pr merge 48 --squash") is None


def test_should_block_when_a_check_is_failing(guard):
    guard.fetch_checks = _fake_checks(([CHECK_PASS, CHECK_FAIL], None))
    reason = guard.verdict("gh pr merge 48 --squash")
    assert reason is not None and "not green" in reason and "Guards" in reason


def test_should_block_when_a_check_is_still_running(guard):
    guard.fetch_checks = _fake_checks(([CHECK_RUNNING], None))
    reason = guard.verdict("gh pr merge 48")
    assert reason is not None and "still running" in reason


def test_should_block_when_there_are_no_checks(guard):
    guard.fetch_checks = _fake_checks(([], None))
    assert guard.verdict("gh pr merge 48") is not None


def test_should_block_when_the_state_cannot_be_read(guard):
    guard.fetch_checks = _fake_checks(([], "gh CLI not found"))
    reason = guard.verdict("gh pr merge 48")
    assert reason is not None and "could not read" in reason


def test_should_allow_with_the_bypass_flag_without_calling_gh(guard):
    def explode(ref):  # fetch_checks must not be called when bypassed
        raise AssertionError("gh must not be queried when [skip-merge-check] is present")
    guard.fetch_checks = explode
    assert guard.verdict("gh pr merge 48 --squash [skip-merge-check]") is None


def test_should_ignore_a_non_merge_command_without_calling_gh(guard):
    def explode(ref):
        raise AssertionError("gh must not be queried for a non-merge command")
    guard.fetch_checks = explode
    assert guard.verdict("gh pr view 48 --json statusCheckRollup") is None


def test_self_test_cases_all_pass(guard):
    # The in-file self-test monkeypatches fetch_checks to a failing check; replay it here.
    saved = guard.fetch_checks
    guard.fetch_checks = _fake_checks(([CHECK_FAIL], None))
    try:
        for cmd, should_block in guard.SELF_TEST:
            assert (guard.verdict(cmd) is not None) == should_block, cmd
    finally:
        guard.fetch_checks = saved


# ── end to end: the hook as a separate process, exit code checked ────────────
# These cover only the gh-independent paths so they stay deterministic offline:
# a non-merge command and a bypassed merge exit 0; unreadable input exits 2. The
# red/pending/green decision is proven above against verdict() with gh mocked.

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
    "ls -la",
    "gh pr view 48 --json statusCheckRollup",
    "gh pr merge 48 --squash [skip-merge-check]",
    "gh pr merge 48 --squash  # [skip-merge-check]",   # the form gh accepts (#280)
])
def test_should_exit_0_when_no_check_is_needed(cmd):
    result = run_hook(cmd)
    assert result.returncode == 0
    assert result.stderr == b""


def test_should_exit_2_when_input_is_not_json():
    result = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True)
    assert result.returncode == 2
    assert "cannot read its own input" in result.stderr.decode("utf-8")


def test_should_mention_the_hook_name_when_blocking():
    # A merge with the bypass absent and gh unavailable blocks; the message names the hook.
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "gh pr merge 999999999 --squash"}}).encode("utf-8"),
        capture_output=True,
    )
    assert result.returncode == 2
    assert "[BLOCK] guard-pr-merge" in result.stderr.decode("utf-8")


def test_should_show_the_bypass_as_a_shell_comment_gh_accepts():
    """gh rejects [skip-merge-check] as an extra argument; the hint must give the comment form (#280)."""
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "gh pr merge 999999999 --squash"}}).encode("utf-8"),
        capture_output=True,
    )
    assert "# [skip-merge-check]" in result.stderr.decode("utf-8")
