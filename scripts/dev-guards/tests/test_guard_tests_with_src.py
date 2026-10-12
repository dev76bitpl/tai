"""Tests for scripts/dev-guards/guard_tests_with_src.py — source changes ship with tests."""
import pytest

from harness import BLOCKED, run_guard, stage

GUARD = "guard_tests_with_src"


@pytest.mark.parametrize("path", [
    "src/lib/price.ts", "src/components/Cart.tsx", "src/Service/Order.php", "src/app/api/orders/route.ts",
])
def test_should_block_when_source_is_staged_without_tests(repo, path):
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "[BLOCK] 1 source file(s) staged without any test files" in result.stderr
    assert path in result.stderr


@pytest.mark.parametrize("test_path", [
    "src/lib/price.test.ts", "src/lib/__tests__/price.ts", "e2e/price.spec.ts",
])
def test_should_pass_when_a_test_file_is_staged_too(repo, test_path):
    stage(repo, "src/lib/price.ts")
    stage(repo, test_path)
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr


def test_should_pass_when_skip_docs_flag_is_in_message(repo):
    stage(repo, "src/lib/price.ts")
    assert run_guard(GUARD, repo, "refactor: rename\n\n[skip-docs] rename only\n").returncode == 0


@pytest.mark.parametrize("path", [
    "src/app/orders/page.tsx", "src/app/orders/layout.tsx", "src/types/api.d.ts",
    "README.md", "docs/SETUP.md", "package.json", "scripts/build.py",
])
def test_should_pass_when_staged_file_needs_no_test(repo, path):
    stage(repo, path)
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_should_pass_when_nothing_is_staged(repo):
    assert run_guard(GUARD, repo).returncode == 0


def test_should_list_first_five_files_and_count_the_rest(repo):
    for i in range(7):
        stage(repo, f"src/lib/mod{i}.ts")
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "7 source file(s)" in result.stderr
    assert "... and 2 more" in result.stderr


def test_should_block_when_commit_message_file_is_missing(repo):
    stage(repo, "README.md")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "guard_tests_with_src: no commit message file given" in result.stderr
