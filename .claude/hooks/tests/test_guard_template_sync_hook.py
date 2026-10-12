"""Tests for .claude/hooks/guard-template-sync.py (ADR-002 acknowledgment model).

The Claude Code PreToolUse variant: richer *.md/guard comparison when a local
template clone exists, acknowledgment gate on CLAUDE.md when it doesn't.

Note: this hook does `from stack import ...` against .claude/hooks/stack.py, while
the pre-commit guard imports scripts/dev-guards/stack.py under the same module name
"stack". We pop the cached module so this file loads the correct one regardless of
test order.
"""
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

HOOKS = Path(__file__).resolve().parents[1]
HOOK = HOOKS / "guard-template-sync.py"


def _load():
    sys.modules.pop("stack", None)
    sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location("guard_tpl_sync_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h = _load()


@pytest.fixture(autouse=True)
def _no_machine_template_path(monkeypatch):
    # $AI_TEMPLATE_PATH wins over every config file (stack.resolve_template_source), so a machine
    # that sets it made the "no clone" cases find one and fail. Each test states its own setup.
    monkeypatch.delenv("AI_TEMPLATE_PATH", raising=False)
    # Autodetection scans sibling directories of the repo, so a neighbouring project marked as a
    # template had the same effect. Patched in the stack module this hook actually imported.
    monkeypatch.setitem(h.resolve_template_path.__globals__, "_autodetect_template_root", lambda: None)


# ── _local_template_root ──────────────────────────────────────────────────────

class TestLocalTemplateRoot:
    def test_empty_is_none(self):
        assert h._local_template_root("") is None

    def test_url_is_none(self):
        assert h._local_template_root("https://github.com/x/tai.git") is None
        assert h._local_template_root("git@github.com:x/tai.git") is None

    def test_missing_dir_is_none(self, tmp_path):
        assert h._local_template_root(str(tmp_path / "nope")) is None

    def test_valid_dir_returns_path(self, tmp_path):
        assert h._local_template_root(str(tmp_path)) == tmp_path


# ── _touches_claude ───────────────────────────────────────────────────────────

class TestTouchesClaude:
    def test_root_claude(self):
        assert h._touches_claude(["CLAUDE.md"]) is True

    def test_nested_claude(self):
        assert h._touches_claude(["a/CLAUDE.md"]) is True

    def test_other_md_false(self):
        assert h._touches_claude(["docs/x.md"]) is False


# ── main(): no-clone acknowledgment branch ────────────────────────────────────

class TestMainNoClone:
    def _run(self, *, config, staged):
        with mock.patch.object(h, "read_command", return_value="git commit -m x"), \
             mock.patch.object(h, "chdir_to_project_root"), \
             mock.patch.object(h, "is_git_commit_command", return_value=True), \
             mock.patch.object(h, "is_foreign_repo", return_value=False), \
             mock.patch.object(h, "load_config", return_value=config), \
             mock.patch.object(h, "get_staged_files", return_value=staged):
            h.main()

    def test_is_template_passes(self):
        with pytest.raises(SystemExit) as exc:
            self._run(config={"is_template": True}, staged=["CLAUDE.md"])
        assert exc.value.code == 0

    def test_no_clone_with_claude_blocks(self):
        with pytest.raises(SystemExit) as exc:
            self._run(config={}, staged=["CLAUDE.md"])
        assert exc.value.code == 2

    def test_url_with_claude_blocks(self):
        with pytest.raises(SystemExit) as exc:
            self._run(config={"ai_template_path": "https://github.com/x/tai.git"},
                      staged=["CLAUDE.md"])
        assert exc.value.code == 2

    def test_no_clone_without_claude_passes(self):
        with pytest.raises(SystemExit) as exc:
            self._run(config={}, staged=["docs/README.md"])
        assert exc.value.code == 0


# ── main(): [skip-sync] bypass across message styles ──────────────────────────
# The bypass flag must be honored whether it sits inline (-m / heredoc) or inside
# a -F <file> message. Reading only the bare command string missed the file case
# and wrongly blocked `git commit -F <file>` even with [skip-sync] in the file.

class TestSkipSyncBypass:
    def _run(self, command: str, *, staged):
        with mock.patch.object(h, "read_command", return_value=command), \
             mock.patch.object(h, "chdir_to_project_root"), \
             mock.patch.object(h, "is_git_commit_command", return_value=True), \
             mock.patch.object(h, "is_foreign_repo", return_value=False), \
             mock.patch.object(h, "load_config", return_value={}), \
             mock.patch.object(h, "get_staged_files", return_value=staged):
            h.main()

    def test_inline_skip_sync_passes(self):
        with pytest.raises(SystemExit) as exc:
            self._run('git commit -m "docs: x [skip-sync]"', staged=["CLAUDE.md"])
        assert exc.value.code == 0

    def test_heredoc_skip_sync_passes(self):
        cmd = "git commit -F - <<'EOF'\ndocs: x\n\n[skip-sync] reason\nEOF"
        with pytest.raises(SystemExit) as exc:
            self._run(cmd, staged=["CLAUDE.md"])
        assert exc.value.code == 0

    def test_file_skip_sync_passes(self, tmp_path):
        # THE FIX: flag lives in the -F file, not in the command string.
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text("docs: x\n\n[skip-sync] reason\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._run(f"git commit -F {msg}", staged=["CLAUDE.md"])
        assert exc.value.code == 0

    def test_file_without_flag_still_blocks(self, tmp_path):
        # Regression: -F must not become a silent bypass when the flag is absent.
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text("docs: x\n\nno bypass here\n", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            self._run(f"git commit -F {msg}", staged=["CLAUDE.md"])
        assert exc.value.code == 2


# ── end to end: the hook as a separate process, exit code checked ────────────
# Claude Code blocks a tool call only on exit code 2. A hook that crashes exits 1, which is a
# non-blocking error — so these tests run the real script with a real payload on stdin and
# assert the exact code. Calling main() with mocks cannot see a crash on the way to exit(2).

import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def project(tmp_path):
    """A project with its own copy of the hook and a local template clone next to it."""
    template = tmp_path / "template"
    (template / "scripts" / "dev-guards").mkdir(parents=True)
    (template / "NOTES.md").write_text("# Notes\n\n## Shared\n", encoding="utf-8")
    (template / "scripts" / "dev-guards" / "guard_x.py").write_text("X = 1\n", encoding="utf-8")

    root = tmp_path / "project"
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("guard-template-sync.py", "stack.py"):
        shutil.copy(HOOKS / name, hooks / name)
    (hooks / "config.json").write_text(
        json.dumps({"ai_template_path": str(template)}), encoding="utf-8")
    (root / "scripts" / "dev-guards").mkdir(parents=True)
    (root / "NOTES.md").write_text("# Notes\n\n## Shared\n", encoding="utf-8")
    (root / "scripts" / "dev-guards" / "guard_x.py").write_text("X = 1\n", encoding="utf-8")
    _git(root, "init", "-q")
    return root


def run_hook(root, command):
    env = {k: v for k, v in os.environ.items() if k != "AI_TEMPLATE_PATH"}
    return subprocess.run(
        [sys.executable, str(root / ".claude" / "hooks" / "guard-template-sync.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8",
    )


class TestEndToEndWithClone:
    def test_should_exit_2_when_md_section_is_missing_in_template(self, project):
        (project / "NOTES.md").write_text("# Notes\n\n## Shared\n\n## Only here\n", encoding="utf-8")
        _git(project, "add", "NOTES.md")
        result = run_hook(project, 'git commit -m "docs: x"')
        assert result.returncode == 2, result.stderr
        assert "## Only here" in result.stderr
        assert "Traceback" not in result.stderr

    def test_should_exit_2_when_guard_differs_from_template(self, project):
        guard = project / "scripts" / "dev-guards" / "guard_x.py"
        guard.write_text("X = 2\n", encoding="utf-8")
        _git(project, "add", str(guard.relative_to(project)))
        result = run_hook(project, 'git commit -m "fix: x"')
        assert result.returncode == 2, result.stderr
        assert "guard_x.py" in result.stderr

    def test_should_name_the_template_location_in_the_block_message(self, project):
        (project / "NOTES.md").write_text("# Notes\n\n## Only here\n", encoding="utf-8")
        _git(project, "add", "NOTES.md")
        result = run_hook(project, 'git commit -m "docs: x"')
        assert str(project.parent / "template") in result.stderr

    def test_should_exit_0_when_project_matches_template(self, project):
        _git(project, "add", "NOTES.md")
        result = run_hook(project, 'git commit -m "docs: x"')
        assert result.returncode == 0, result.stderr

    def test_should_exit_0_when_skip_sync_flag_is_present(self, project):
        (project / "NOTES.md").write_text("# Notes\n\n## Only here\n", encoding="utf-8")
        _git(project, "add", "NOTES.md")
        result = run_hook(project, 'git commit -m "docs: x [skip-sync]"')
        assert result.returncode == 0, result.stderr

    def test_should_exit_0_for_a_command_that_is_not_a_commit(self, project):
        result = run_hook(project, "ls -la")
        assert result.returncode == 0, result.stderr
