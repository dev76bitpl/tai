"""Open-issue count at session start (#212): one line, no titles, silent without gh."""
import importlib.util
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "session-context.py"


def _load():
    spec = importlib.util.spec_from_file_location("session_context_issues_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load()


def _gh(monkeypatch, returncode=0, stdout="[]", exc=None):
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        if exc:
            raise exc
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(hook.subprocess, "run", fake_run)
    return calls


def test_should_count_open_issues_with_a_short_timeout(monkeypatch, tmp_path):
    calls = _gh(monkeypatch, stdout=json.dumps([{"number": 1}, {"number": 7}]))
    assert hook.count_open_issues(tmp_path) == 2
    cmd, kw = calls[0]
    assert cmd[:3] == ["gh", "issue", "list"] and "--state" in cmd and "open" in cmd
    assert kw["cwd"] == tmp_path and kw["timeout"] <= 5


def test_should_stay_silent_without_gh(monkeypatch, tmp_path):
    _gh(monkeypatch, exc=FileNotFoundError("gh"))
    assert hook.count_open_issues(tmp_path) is None


def test_should_stay_silent_when_gh_times_out(monkeypatch, tmp_path):
    _gh(monkeypatch, exc=subprocess.TimeoutExpired("gh", 5))
    assert hook.count_open_issues(tmp_path) is None


def test_should_stay_silent_when_gh_fails(monkeypatch, tmp_path):
    _gh(monkeypatch, returncode=1, stdout="")
    assert hook.count_open_issues(tmp_path) is None


def test_should_stay_silent_on_garbage_output(monkeypatch, tmp_path):
    _gh(monkeypatch, stdout="not json")
    assert hook.count_open_issues(tmp_path) is None


def test_should_print_one_line_without_titles():
    line = hook.issue_count_line(3)
    assert line == "📋 Otwarte issues w repo: 3 — przejrzyj: `gh issue list`"
    assert "\n" not in line


def test_should_print_nothing_for_zero_or_unknown():
    assert hook.issue_count_line(0) is None
    assert hook.issue_count_line(None) is None


def test_should_mark_a_count_at_the_limit_as_more():
    assert f"{hook.ISSUE_LIMIT}+" in hook.issue_count_line(hook.ISSUE_LIMIT)
