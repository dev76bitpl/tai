"""Tests for scripts/dev-guards/guard_tests.py — the project's test command gates commits
that touch source files; docs-only commits skip it."""
from harness import BLOCKED, run_guard, stage, write_config

GUARD = "guard_tests"


def _test_script(repo, code):
    (repo / "run_tests.py").write_text(code, encoding="utf-8")
    write_config(repo, {"test": "python3 run_tests.py"})


FAILING = "import sys\nprint('FAILED test_price')\nsys.exit(1)\n"
PASSING = "print('3 passed')\n"


def test_should_block_and_show_output_when_tests_fail(repo):
    _test_script(repo, FAILING)
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Tests failed" in result.stderr
    assert "FAILED test_price" in result.stderr


def test_should_pass_when_tests_succeed(repo):
    _test_script(repo, PASSING)
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_should_skip_failing_tests_on_docs_only_commit(repo):
    _test_script(repo, FAILING)
    stage(repo, "docs/SETUP.md")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "skipped — docs-only commit" in result.stdout


def test_should_run_tests_when_docs_and_source_are_staged_together(repo):
    _test_script(repo, FAILING)
    stage(repo, "docs/SETUP.md")
    stage(repo, "lib/price.ts")
    assert run_guard(GUARD, repo, message=None).returncode == BLOCKED


def test_should_warn_and_pass_when_stack_is_unknown(repo):
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "[WARN] Unknown stack" in result.stdout


def test_should_warn_and_pass_when_test_command_is_not_installed(repo):
    write_config(repo, {"test": "no-such-runner-xyz"})
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "[WARN] Test command unavailable: no-such-runner-xyz" in result.stdout


def test_should_block_when_staged_files_cannot_be_listed(repo, tmp_path):
    _test_script(repo, PASSING)
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    result = run_guard(GUARD, repo, message=None, cwd=outside)
    assert result.returncode == BLOCKED
    assert "guard_tests: cannot list staged files" in result.stderr
