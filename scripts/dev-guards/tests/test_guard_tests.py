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


def test_should_pass_but_say_it_checks_nothing_when_stack_is_unknown(repo):
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0
    assert "[WARN] Test guard checks NOTHING: unknown stack" in result.stdout


def test_should_block_when_the_project_own_test_command_cannot_run(repo):
    # a command the project itself wrote into config.json is a promise; one that cannot run
    # used to print a warning nobody saw and let every commit through
    write_config(repo, {"test": "no-such-runner-xyz"})
    stage(repo, "src/price.py")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Test command from .claude/hooks/config.json cannot run: no-such-runner-xyz" in result.stderr
    assert "`no-such-runner-xyz` is not installed" in result.stderr


def test_should_not_block_docs_only_commit_even_when_test_command_cannot_run(repo):
    write_config(repo, {"test": "no-such-runner-xyz"})
    stage(repo, "docs/NOTES.md")
    assert run_guard(GUARD, repo, message=None).returncode == 0


def test_should_pass_with_a_warning_when_autodetected_stack_has_no_test_script_yet(repo):
    # a fresh node project: package.json is there, tests are not set up — the first commits
    # must go through, but not silently
    stage(repo, "package.json", '{"scripts": {"doctor": "node x.mjs"}}\n')
    stage(repo, "src/price.js")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == 0, result.stderr
    assert "[WARN] Test guard checks NOTHING" in result.stdout
    assert 'package.json has no "test" script' in result.stdout


def test_should_run_autodetected_test_script_when_the_project_has_one(repo):
    stage(repo, "package.json", '{"scripts": {"test": "node -e \\"process.exit(1)\\""}}\n')
    stage(repo, "src/price.js")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "[BLOCK] Tests failed" in result.stderr


def test_should_block_when_staged_files_cannot_be_listed(repo, tmp_path):
    _test_script(repo, PASSING)
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    result = run_guard(GUARD, repo, message=None, cwd=outside)
    assert result.returncode == BLOCKED
    assert "guard_tests: cannot list staged files" in result.stderr
