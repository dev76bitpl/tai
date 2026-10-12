"""Tests for scripts/dev-guards/guard_user_tested.py — feat/* and fix/* need [user-tested]."""
import pytest

from harness import BLOCKED, commit, git, make_repo, run_guard, stage

GUARD = "guard_user_tested"


@pytest.mark.parametrize("branch", ["feat/login", "fix/42-crash"])
def test_should_block_on_feature_branch_without_flag(tmp_path, branch):
    repo = make_repo(tmp_path / "repo", branch=branch)
    result = run_guard(GUARD, repo, "feat: add login\n")
    assert result.returncode == BLOCKED
    assert f"[BLOCK] Commit on branch '{branch}' without [user-tested] flag" in result.stderr


@pytest.mark.parametrize("message", [
    "feat: add login\n\n[user-tested]\n",
    "docs: typo\n\n[skip-test-check] docs only\n",
])
def test_should_pass_on_feature_branch_with_flag(tmp_path, message):
    repo = make_repo(tmp_path / "repo", branch="feat/login")
    result = run_guard(GUARD, repo, message)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


@pytest.mark.parametrize("branch", ["main", "docs/readme", "chore/deps", "test/139-guards", "feature-x"])
def test_should_pass_on_branch_that_does_not_require_the_flag(tmp_path, branch):
    repo = make_repo(tmp_path / "repo", branch=branch)
    assert run_guard(GUARD, repo, "chore: something\n").returncode == 0


def test_should_block_on_feature_branch_that_already_has_commits(tmp_path):
    repo = make_repo(tmp_path / "repo", branch="main")
    stage(repo, "README.md")
    commit(repo)
    git(repo, "checkout", "-q", "-b", "fix/7-typo")
    assert run_guard(GUARD, repo, "fix: typo\n").returncode == BLOCKED


def test_should_pass_on_detached_head(tmp_path):
    # rebase / cherry-pick replay commits that were already accepted on their branch
    repo = make_repo(tmp_path / "repo", branch="feat/login")
    stage(repo, "README.md")
    commit(repo)
    git(repo, "checkout", "-q", "--detach")
    assert run_guard(GUARD, repo, "feat: add login\n").returncode == 0


def test_should_block_when_commit_message_file_is_missing(tmp_path):
    repo = make_repo(tmp_path / "repo", branch="feat/login")
    result = run_guard(GUARD, repo, message=None)
    assert result.returncode == BLOCKED
    assert "guard_user_tested: no commit message file given" in result.stderr


def test_should_block_when_branch_cannot_be_read(tmp_path):
    repo = make_repo(tmp_path / "repo", branch="feat/login")
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    result = run_guard(GUARD, repo, "feat: add login\n", cwd=outside)
    assert result.returncode == BLOCKED
    assert "cannot read the current branch" in result.stderr
