"""Tests for .claude/hooks/guard-ai-template.py — a commit that may carry something generic
must say whether it belongs in the template: [template-done] or [no-template]."""
import pytest

from hook_harness import BLOCKED, make_project, run_hook, stage, stderr

HOOK = "guard-ai-template"


@pytest.fixture
def project(tmp_path):
    return make_project(tmp_path / "project", config={"ai_template_path": "/somewhere/template"})


@pytest.mark.parametrize("path", [
    "scripts/dev-guards/guard_x.py", ".claude/hooks/guard-x.py", "CLAUDE.md",
    "docs/adr/ADR-009-x.md", "docs/CONVENTIONS.md",
])
def test_should_block_when_generic_file_is_staged_without_decision(project, path):
    stage(project, path)
    result = run_hook(HOOK, project, 'git commit -m "chore: tweak"')
    assert result.returncode == BLOCKED
    assert "[BLOCK] Ocena AI template repo" in stderr(result)
    assert path in stderr(result)
    assert "/somewhere/template" in stderr(result)


@pytest.mark.parametrize("ctype", ["feat", "fix", "docs", "refactor"])
def test_should_block_substantive_commit_even_without_generic_files(project, ctype):
    stage(project, "src/orders.ts")
    result = run_hook(HOOK, project, f'git commit -m "{ctype}: orders"')
    assert result.returncode == BLOCKED
    assert f"Commit typu '{ctype}'" in stderr(result)


@pytest.mark.parametrize("flag", ["[no-template]", "[template-done]"])
def test_should_pass_when_decision_flag_is_inline(project, flag):
    stage(project, "scripts/build.py")
    result = run_hook(HOOK, project, f'git commit -m "feat: build {flag}"')
    assert result.returncode == 0, stderr(result)
    assert result.stderr == b""


def test_should_pass_when_decision_flag_is_in_heredoc(project):
    stage(project, "scripts/build.py")
    command = "git commit -F - <<'EOF'\nfeat: build\n\n[no-template] project only\nEOF"
    assert run_hook(HOOK, project, command).returncode == 0


def test_should_pass_when_decision_flag_is_in_message_file(project, tmp_path):
    stage(project, "scripts/build.py")
    msg = tmp_path / "MSG"
    msg.write_text("feat: build\n\n[template-done]\n", encoding="utf-8")
    assert run_hook(HOOK, project, f"git commit -F {msg}").returncode == 0


def test_should_block_when_message_file_has_no_flag(project, tmp_path):
    # -F must not become a silent bypass
    stage(project, "scripts/build.py")
    msg = tmp_path / "MSG"
    msg.write_text("feat: build\n", encoding="utf-8")
    assert run_hook(HOOK, project, f"git commit -F {msg}").returncode == BLOCKED


@pytest.mark.parametrize("command", [
    "git commit -F /no/such/file.txt",
    "git commit",
    "git commit --amend --no-edit",
])
def test_should_block_when_commit_message_cannot_be_read(project, command):
    stage(project, "src/orders.ts")
    result = run_hook(HOOK, project, command)
    assert result.returncode == BLOCKED
    assert "Nie mogę odczytać wiadomości commita" in stderr(result)


@pytest.mark.parametrize("ctype", ["chore", "test", "style", "ci"])
def test_should_pass_housekeeping_commit_without_generic_files(project, ctype):
    stage(project, "src/orders.ts")
    result = run_hook(HOOK, project, f'git commit -m "{ctype}: tidy"')
    assert result.returncode == 0, stderr(result)


@pytest.mark.parametrize("command", [
    "git status",
    "ls -la scripts",
    'gh pr create --title "x" --body "run git commit -m feat: y afterwards"',
    'echo "git commit"',
])
def test_should_pass_command_that_is_not_a_commit(project, command):
    stage(project, "scripts/build.py")
    result = run_hook(HOOK, project, command)
    assert result.returncode == 0, stderr(result)
    assert result.stderr == b""


def test_should_see_files_added_in_the_same_command(project):
    (project / "scripts").mkdir()
    (project / "scripts" / "build.py").write_text("x\n", encoding="utf-8")
    result = run_hook(HOOK, project, 'git add scripts/build.py && git commit -m "chore: tweak"')
    assert result.returncode == BLOCKED
    assert "scripts/build.py" in stderr(result)


def test_should_pass_commit_aimed_at_another_repository(project, tmp_path):
    stage(project, "scripts/build.py")
    other = tmp_path / "other"
    other.mkdir()
    assert run_hook(HOOK, project, f'git -C {other} commit -m "feat: x"').returncode == 0
