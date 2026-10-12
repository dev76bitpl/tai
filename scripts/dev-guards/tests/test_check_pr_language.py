"""Tests for scripts/dev-guards/check_pr_language.py — PR title and body must be in English.

Runs in CI, not in pre-commit: input comes from PR_TITLE / PR_BODY, the verdict is the exit
code (1 fails the job) and the message goes to stdout.
"""
import subprocess
import sys

import pytest

from harness import BLOCKED, GUARDS, clean_env

CHECK = GUARDS / "check_pr_language.py"
TITLE = "fix(orders): keep the filter after reload"


def run_check(title=TITLE, body="", unset=()):
    env = clean_env(PR_TITLE=title, PR_BODY=body)
    for name in unset:
        env.pop(name, None)
    return subprocess.run([sys.executable, str(CHECK)], env=env, capture_output=True,
                          text=True, encoding="utf-8")


@pytest.mark.parametrize("title, found", [
    ("fix: napraw filtr zamówień", "ó"),
    ("docs: konfiguracja serwera", "konfiguracja"),
])
def test_should_fail_when_title_is_polish(title, found):
    result = run_check(title=title)
    assert result.returncode == BLOCKED
    assert f"[BLOCK] Polish text '{found}' in PR title" in result.stdout


@pytest.mark.parametrize("body, found", [
    ("## Summary\n\n- naprawiono filtr\n", "naprawiono"),
    ("Refunds of 600 zł were rounded down.", "ł"),
    ("Renamed label: Zapisz zmianę.", "ę"),
])
def test_should_fail_when_body_prose_is_polish(body, found):
    result = run_check(body=body)
    assert result.returncode == BLOCKED
    assert f"[BLOCK] Polish text '{found}' in PR body" in result.stdout


@pytest.mark.parametrize("body", [
    "## Summary\n\n- keep the filter after reload\n\n## Test plan\n\n- [ ] reload the list\n",
    "Renamed the `Zapisz zmianę` button.",
    'Renamed the "Zapisz zmianę" button.',
    "Renamed the „Zapisz zmianę” button.",
    "Output:\n\n```\nBłąd: nie znaleziono pliku\n```\n",
    "Refunds of 600 PLN were rounded down.",
    "",
])
def test_should_pass_when_prose_is_english(body):
    result = run_check(body=body)
    assert result.returncode == 0, result.stdout
    assert "OK: PR title and body are in English." in result.stdout


def test_should_pass_when_skip_lang_flag_is_in_body():
    result = run_check(body="Cytat klienta: nie działa filtr.\n\n[skip-lang]")
    assert result.returncode == 0
    assert "[skip-lang] present" in result.stdout


def test_should_still_check_the_title_when_body_has_only_code():
    assert run_check(title="fix: napraw filtr", body="```\nok\n```").returncode == BLOCKED


@pytest.mark.parametrize("unset, title", [((), ""), ((), "   "), (("PR_TITLE",), TITLE)])
def test_should_fail_when_the_title_did_not_arrive(unset, title):
    # every pull request has a title; an empty one means the workflow passed nothing
    result = run_check(title=title, unset=unset)
    assert result.returncode == BLOCKED
    assert "[BLOCK] PR_TITLE is empty" in result.stdout
