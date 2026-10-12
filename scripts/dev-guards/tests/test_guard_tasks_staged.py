"""Tests for scripts/dev-guards/guard_tasks_staged.py.

Zasada A: every guard proves (1) it blocks what it must, (2) it passes the rest.

End to end on purpose: the script runs as a subprocess inside a real git repository and
the test asserts the exit code, so a guard broken into "always pass" fails here.
"""
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / "guard_tasks_staged.py"


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "docs").mkdir()
    return tmp_path


def _stage(repo: Path, name: str) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=repo, check=True)


def _run(repo: Path, message: str = "docs: something\n"):
    msg = repo / "COMMIT_EDITMSG"
    msg.write_text(message, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(GUARD), str(msg)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_should_pass_when_session_log_is_staged(repo):
    _stage(repo, "docs/TASKS.md")
    _stage(repo, "src/app.py")
    assert _run(repo).returncode == 0


def test_should_block_when_session_log_is_not_staged(repo):
    _stage(repo, "src/app.py")
    result = _run(repo)
    assert result.returncode == 1
    assert "docs/TASKS.md is not in staged files" in result.stderr
    assert "session log entry" in result.stderr


def test_should_block_when_only_another_docs_file_is_staged(repo):
    _stage(repo, "docs/ROADMAP.md")
    assert _run(repo).returncode == 1


def test_should_pass_when_skip_docs_flag_is_in_body(repo):
    _stage(repo, "src/app.py")
    assert _run(repo, "fix: typo\n\n[skip-docs]\n").returncode == 0


def test_should_block_when_nothing_is_staged(repo):
    assert _run(repo).returncode == 1


def test_should_block_when_it_cannot_read_staged_files(tmp_path):
    """Outside a git repository the guard cannot check, so it must not pass."""
    assert _run(tmp_path).returncode == 1
