"""Tests for scripts/dev-guards/guard_tests_with_src.py — source changes ship with tests."""
import pytest

from harness import BLOCKED, run_guard, stage, write_config

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


# ── tests are recognised for every stack, not only JavaScript naming ─────────

@pytest.mark.parametrize("src, test_path", [
    ("src/price.py", "tests/test_price.py"),
    ("src/price.py", "src/price_test.py"),
    ("src/price.py", "src/test_price.py"),
    ("src/price/calc.go", "src/price/calc_test.go"),
    ("src/Service/Order.php", "tests/Service/OrderTest.php"),
    ("src/models/order.rb", "spec/models/order_spec.rb"),
    ("src/models/order.rb", "test/models/order_test.rb"),
    ("src/lib/price.ts", "tests/price.ts"),
])
def test_should_pass_when_a_test_in_the_stack_convention_is_staged(repo, src, test_path):
    stage(repo, src)
    stage(repo, test_path)
    result = run_guard(GUARD, repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("not_a_test", [
    "tests/README.md", "tests/fixtures/orders.json", "src/latest.py", "src/contest_utils.py", "docs/test_plan.md",
])
def test_should_block_when_the_other_staged_file_only_looks_like_a_test(repo, not_a_test):
    stage(repo, "src/price.py")
    stage(repo, not_a_test)
    assert run_guard(GUARD, repo).returncode == BLOCKED


@pytest.mark.parametrize("test_only", ["src/test_price.py", "src/price_test.go", "src/tests/helpers.py"])
def test_should_not_count_a_test_file_as_source(repo, test_only):
    stage(repo, test_only)
    assert run_guard(GUARD, repo).returncode == 0


# ── code directories come from config (src_dirs), default src/ ───────────────

def test_should_block_code_in_configured_directory_without_tests(repo):
    write_config(repo, {"src_dirs": ["app", "lib"]})
    stage(repo, "app/Service/Order.php")
    result = run_guard(GUARD, repo)
    assert result.returncode == BLOCKED
    assert "app/Service/Order.php" in result.stderr


def test_should_pass_code_in_configured_directory_with_its_test(repo):
    write_config(repo, {"src_dirs": ["app"]})
    stage(repo, "app/Service/Order.php")
    stage(repo, "tests/Service/OrderTest.php")
    assert run_guard(GUARD, repo).returncode == 0


def test_should_stop_checking_src_when_config_names_other_directories(repo):
    write_config(repo, {"src_dirs": ["app"]})
    stage(repo, "src/legacy.php")
    assert run_guard(GUARD, repo).returncode == 0


def test_should_not_check_unlisted_directory_by_default(repo):
    stage(repo, "app/Service/Order.php")
    assert run_guard(GUARD, repo).returncode == 0


def test_should_check_code_directory_below_the_root(repo):
    write_config(repo, {"src_dirs": ["app"]})
    stage(repo, "packages/api/app/order.py")
    assert run_guard(GUARD, repo).returncode == BLOCKED


def test_should_not_match_directory_by_name_fragment(repo):
    write_config(repo, {"src_dirs": ["app"]})
    stage(repo, "webapp/order.py")
    assert run_guard(GUARD, repo).returncode == 0


@pytest.mark.parametrize("broken", ["src", [], [""], {"a": 1}, [1, 2], None])
def test_should_fall_back_to_src_when_config_value_is_unusable(repo, broken):
    write_config(repo, {"src_dirs": broken})
    stage(repo, "src/price.py")
    assert run_guard(GUARD, repo).returncode == BLOCKED
