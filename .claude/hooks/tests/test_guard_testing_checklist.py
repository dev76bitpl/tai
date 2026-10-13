"""Tests for .claude/hooks/guard-testing-checklist.py — a commit on feat/* or fix/* needs
docs/TESTING.md touched somewhere on the branch, or [skip-test-check]."""
import pytest

from hook_harness import BLOCKED, commit, git, make_project, run_hook, stage, stderr

HOOK = "guard-testing-checklist"
COMMIT = 'git commit -m "feat: orders"'


@pytest.fixture
def feature(tmp_path):
    """main with one commit, then feat/orders checked out."""
    project = make_project(tmp_path / "project", branch="main")
    stage(project, "README.md")
    commit(project)
    git(project, "checkout", "-q", "-b", "feat/orders")
    return project


def test_should_block_when_testing_md_was_not_touched_on_the_branch(feature):
    stage(feature, "src/orders.ts")
    result = run_hook(HOOK, feature, COMMIT)
    assert result.returncode == BLOCKED
    assert "[BLOCK] docs/TESTING.md nie został zaktualizowany na branchu feat/orders" in stderr(result)


def test_should_pass_when_testing_md_is_staged(feature):
    stage(feature, "src/orders.ts")
    stage(feature, "docs/TESTING.md")
    result = run_hook(HOOK, feature, COMMIT)
    assert result.returncode == 0, stderr(result)
    assert result.stderr == b""


def test_should_pass_when_testing_md_is_added_in_the_same_command(feature):
    stage(feature, "src/orders.ts")
    (feature / "docs").mkdir()
    (feature / "docs" / "TESTING.md").write_text("x\n", encoding="utf-8")
    assert run_hook(HOOK, feature, f"git add docs/TESTING.md && {COMMIT}").returncode == 0


def test_should_pass_when_testing_md_was_committed_earlier_on_the_branch(feature):
    stage(feature, "docs/TESTING.md")
    commit(feature, "docs: checklist")
    stage(feature, "src/orders.ts")
    assert run_hook(HOOK, feature, COMMIT).returncode == 0


def test_should_block_when_testing_md_was_only_changed_on_main(feature):
    git(feature, "checkout", "-q", "main")
    stage(feature, "docs/TESTING.md")
    commit(feature, "docs: checklist on main")
    git(feature, "checkout", "-q", "feat/orders")
    stage(feature, "src/orders.ts")
    assert run_hook(HOOK, feature, COMMIT).returncode == BLOCKED


def test_should_pass_when_skip_flag_is_inline(feature):
    stage(feature, "src/orders.ts")
    assert run_hook(HOOK, feature, 'git commit -m "docs: typo [skip-test-check]"').returncode == 0


def test_should_pass_when_skip_flag_is_in_message_file(feature, tmp_path):
    stage(feature, "src/orders.ts")
    msg = tmp_path / "MSG"
    msg.write_text("docs: typo\n\n[skip-test-check] docs only\n", encoding="utf-8")
    assert run_hook(HOOK, feature, f"git commit -F {msg}").returncode == 0


def test_should_block_when_message_file_has_no_flag(feature, tmp_path):
    stage(feature, "src/orders.ts")
    msg = tmp_path / "MSG"
    msg.write_text("feat: orders\n", encoding="utf-8")
    assert run_hook(HOOK, feature, f"git commit -F {msg}").returncode == BLOCKED


@pytest.mark.parametrize("branch", ["main", "docs/readme", "chore/deps", "test/139-guards"])
def test_should_pass_on_branch_that_is_not_feat_or_fix(tmp_path, branch):
    project = make_project(tmp_path / "project", branch=branch)
    stage(project, "src/orders.ts")
    assert run_hook(HOOK, project, COMMIT).returncode == 0


def test_should_block_on_first_commit_of_a_fix_branch(tmp_path):
    # a branch with no commits yet is still a fix branch
    project = make_project(tmp_path / "project", branch="fix/1-crash")
    stage(project, "src/orders.ts")
    assert run_hook(HOOK, project, COMMIT).returncode == BLOCKED


@pytest.mark.parametrize("command", ["git status", "git push", 'echo "git commit"'])
def test_should_pass_command_that_is_not_a_commit(feature, command):
    stage(feature, "src/orders.ts")
    result = run_hook(HOOK, feature, command)
    assert result.returncode == 0, stderr(result)
    assert result.stderr == b""


def test_should_pass_commit_aimed_at_another_repository(feature, tmp_path):
    stage(feature, "src/orders.ts")
    other = tmp_path / "other"
    other.mkdir()
    assert run_hook(HOOK, feature, f'git -C {other} commit -m "feat: x"').returncode == 0


# ── any docs/*TESTING*.md is a checklist: a guard-system scenario goes to its own file ──

@pytest.mark.parametrize("checklist", ["docs/GUARDS_TESTING.md", "docs/TEMPLATE_TESTING.md"])
def test_should_pass_when_another_testing_checklist_is_staged(feature, checklist):
    stage(feature, "src/orders.ts")
    stage(feature, checklist)
    assert run_hook(HOOK, feature, COMMIT).returncode == 0


def test_should_pass_when_another_testing_checklist_was_committed_earlier_on_the_branch(feature):
    stage(feature, "docs/GUARDS_TESTING.md")
    commit(feature, "docs: guard scenario")
    stage(feature, "src/orders.ts")
    assert run_hook(HOOK, feature, COMMIT).returncode == 0


@pytest.mark.parametrize("not_a_checklist", ["docs/NOTES.md", "docs/testing/notes.md", "TESTING.md", "docs/SETUP.md"])
def test_should_block_when_staged_doc_is_not_a_testing_checklist(feature, not_a_checklist):
    stage(feature, "src/orders.ts")
    stage(feature, not_a_checklist)
    assert run_hook(HOOK, feature, COMMIT).returncode == BLOCKED
