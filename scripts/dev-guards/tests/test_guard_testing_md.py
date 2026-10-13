"""Tests for scripts/dev-guards/guard_testing_md.py — feat/fix branches touching src/ must
update docs/TESTING.md somewhere on the branch."""
import pytest

from harness import BLOCKED, commit, git, make_repo, run_guard, stage

GUARD = "guard_testing_md"


@pytest.fixture
def feature(tmp_path):
    """main with one commit, then feat/orders checked out."""
    repo = make_repo(tmp_path / "repo", branch="main")
    stage(repo, "README.md")
    commit(repo)
    git(repo, "checkout", "-q", "-b", "feat/orders")
    return repo


def test_should_block_when_src_changes_without_testing_md(feature):
    stage(feature, "src/orders.ts")
    result = run_guard(GUARD, feature)
    assert result.returncode == BLOCKED
    assert "[BLOCK] docs/TESTING.md not updated on branch 'feat/orders'" in result.stderr


def test_should_pass_when_testing_md_is_staged_in_this_commit(feature):
    stage(feature, "src/orders.ts")
    stage(feature, "docs/TESTING.md")
    result = run_guard(GUARD, feature)
    assert result.returncode == 0, result.stderr


def test_should_pass_when_testing_md_was_committed_earlier_on_the_branch(feature):
    stage(feature, "docs/TESTING.md")
    commit(feature, "docs: checklist")
    stage(feature, "src/orders.ts")
    result = run_guard(GUARD, feature)
    assert result.returncode == 0, result.stderr


def test_should_block_when_testing_md_was_only_changed_on_main(feature):
    git(feature, "checkout", "-q", "main")
    stage(feature, "docs/TESTING.md")
    commit(feature, "docs: checklist on main")
    git(feature, "checkout", "-q", "feat/orders")
    stage(feature, "src/orders.ts")
    assert run_guard(GUARD, feature).returncode == BLOCKED


def test_should_pass_when_skip_docs_flag_is_in_message(feature):
    stage(feature, "src/orders.ts")
    assert run_guard(GUARD, feature, "refactor: rename\n\n[skip-docs] internal\n").returncode == 0


@pytest.mark.parametrize("path", ["docs/SETUP.md", "package.json", "scripts/build.py"])
def test_should_pass_when_no_src_file_is_staged(feature, path):
    stage(feature, path)
    result = run_guard(GUARD, feature)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("branch", ["main", "docs/readme", "chore/deps"])
def test_should_pass_on_branch_that_is_not_feat_or_fix(tmp_path, branch):
    repo = make_repo(tmp_path / "repo", branch=branch)
    stage(repo, "src/orders.ts")
    assert run_guard(GUARD, repo).returncode == 0


def test_should_block_on_first_commit_of_a_fix_branch(tmp_path):
    # a branch with no commits yet is still a fix branch
    repo = make_repo(tmp_path / "repo", branch="fix/1-crash")
    stage(repo, "src/orders.ts")
    assert run_guard(GUARD, repo).returncode == BLOCKED


def test_should_block_when_commit_message_file_is_missing(feature):
    stage(feature, "src/orders.ts")
    result = run_guard(GUARD, feature, message=None)
    assert result.returncode == BLOCKED
    assert "guard_testing_md: no commit message file given" in result.stderr


# ── any docs/*TESTING*.md is a checklist: a guard-system scenario goes to its own file ──

@pytest.mark.parametrize("checklist", ["docs/GUARDS_TESTING.md", "docs/TEMPLATE_TESTING.md"])
def test_should_pass_when_another_testing_checklist_is_staged(feature, checklist):
    stage(feature, "src/orders.ts")
    stage(feature, checklist)
    assert run_guard(GUARD, feature).returncode == 0


def test_should_pass_when_another_testing_checklist_was_committed_earlier_on_the_branch(feature):
    stage(feature, "docs/GUARDS_TESTING.md")
    commit(feature, "docs: guard scenario")
    stage(feature, "src/orders.ts")
    assert run_guard(GUARD, feature).returncode == 0


@pytest.mark.parametrize("not_a_checklist", ["docs/NOTES.md", "docs/testing/notes.md", "TESTING.md", "docs/SETUP.md"])
def test_should_block_when_staged_doc_is_not_a_testing_checklist(feature, not_a_checklist):
    stage(feature, "src/orders.ts")
    stage(feature, not_a_checklist)
    assert run_guard(GUARD, feature).returncode == BLOCKED
