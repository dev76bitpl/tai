"""Coverage ratchet: every blocking hook has a test file that runs it and checks its exit code.

CLAUDE.md, "Guard only with a test": a guard without a test is either fail-open or dead and
nobody notices. This test fails the moment a guard-*.py hook is added (or a test file removed)
without its counterpart, so coverage cannot quietly go backwards.
"""
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
HOOKS = TESTS.parent

HOOK_FILES = sorted(HOOKS.glob("guard-*.py"))


def test_should_find_the_hooks():
    assert len(HOOK_FILES) >= 4, [p.name for p in HOOK_FILES]


@pytest.mark.parametrize("hook", HOOK_FILES, ids=lambda p: p.name)
def test_should_have_a_test_file_that_checks_the_exit_code(hook):
    stem = hook.stem.replace("-", "_")
    # "_hook" suffix: for a hook whose commit-guard twin already owns the plain test name
    candidates = [TESTS / f"test_{stem}.py", TESTS / f"test_{stem}_hook.py"]
    test_file = next((c for c in candidates if c.is_file()), None)
    assert test_file is not None, (
        f"{hook.name} has no tests: add .claude/hooks/tests/test_{stem}.py proving that the hook "
        "blocks with exit code 2, passes the rest with 0, and blocks when it cannot read its input."
    )
    text = test_file.read_text(encoding="utf-8")
    assert hook.stem in text, f"{test_file.name} never mentions {hook.stem}"
    assert "returncode ==" in text, f"{test_file.name} never asserts an exit code — a hook is its exit code."


@pytest.mark.parametrize("hook", HOOK_FILES, ids=lambda p: p.name)
def test_should_be_covered_by_the_input_boundary_tests(hook):
    text = (TESTS / "test_hook_input.py").read_text(encoding="utf-8")
    assert f'"{hook.stem}"' in text, f"add {hook.stem} to BLOCKING_HOOKS in test_hook_input.py"
