"""Tests for scripts/dev-guards/guard_commit_lang.py — the commit subject must be in English."""
import pytest

from harness import BLOCKED, run_guard

GUARD = "guard_commit_lang"


@pytest.mark.parametrize("subject, found", [
    ("fix: dodaj walidację formularza", "ę"),
    ("feat(auth): obsluga logowania przez plik", "przez"),
    ("docs: konfiguracja serwera", "konfiguracja"),
    ("naprawa logowania", "naprawa"),
    ("fix(ui)!: Zażółć gęślą jaźń", "ż"),
])
def test_should_block_when_subject_is_polish(repo, subject, found):
    result = run_guard(GUARD, repo, subject + "\n")
    assert result.returncode == BLOCKED
    assert f"[BLOCK] Polish text '{found}' in commit subject" in result.stderr
    assert subject in result.stderr


@pytest.mark.parametrize("message", [
    "fix: add form validation\n",
    "feat(auth): support login by file\n",
    "chore: bump deps\n\n- package.json: minor updates\n",
    "Merge branch 'main' into feat/x\n",
])
def test_should_pass_when_subject_is_english(repo, message):
    result = run_guard(GUARD, repo, message)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_should_check_only_the_subject_not_the_body(repo):
    message = "fix: add form validation\n\nDodano walidację, bo użytkownik mógł wysłać pusty plik.\n"
    assert run_guard(GUARD, repo, message).returncode == 0


def test_should_pass_on_empty_message(repo):
    # git itself aborts a commit with an empty message; nothing for this guard to judge.
    assert run_guard(GUARD, repo, "\n").returncode == 0


def test_should_block_when_commit_message_file_is_missing(repo):
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "guard_commit_lang: no commit message file given" in result.stderr
