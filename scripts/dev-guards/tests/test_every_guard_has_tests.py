"""Coverage ratchet: every commit guard has a test file that runs it and checks its exit code.

CLAUDE.md, "Guard only with a test": a guard without a test is either fail-open or dead and
nobody notices. This test fails the moment a guard is added (or a test file removed) without
its counterpart, so coverage cannot quietly go backwards.
"""
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
GUARDS = TESTS.parent
# modules the guards import, not guards themselves; each is exercised through its guards
HELPERS = {"stack.py", "lang.py", "pii.py"}

GUARD_FILES = sorted(p for p in GUARDS.glob("*.py") if p.name not in HELPERS)


def test_should_find_the_guards():
    assert len(GUARD_FILES) >= 13, [p.name for p in GUARD_FILES]


@pytest.mark.parametrize("guard", GUARD_FILES, ids=lambda p: p.name)
def test_should_have_a_test_file_that_checks_the_exit_code(guard):
    test_file = TESTS / f"test_{guard.stem}.py"
    assert test_file.is_file(), (
        f"{guard.name} has no tests: add {test_file.relative_to(GUARDS.parent.parent)} proving that the "
        "guard blocks what it must, passes the rest, and blocks when it cannot check."
    )
    text = test_file.read_text(encoding="utf-8")
    assert guard.stem in text, f"{test_file.name} never mentions {guard.stem}"
    assert "returncode ==" in text, (
        f"{test_file.name} never asserts an exit code — a guard is its exit code, test that."
    )


@pytest.mark.parametrize("helper", sorted(HELPERS))
def test_should_keep_the_helper_list_honest(helper):
    assert (GUARDS / helper).is_file(), f"{helper} is listed as a helper but does not exist"
