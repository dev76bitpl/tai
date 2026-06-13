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

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
HOOK = HOOKS / "guard-template-sync.py"


def _load():
    sys.modules.pop("stack", None)
    sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location("guard_tpl_sync_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


h = _load()


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
        with mock.patch.object(h, "get_command", return_value="git commit -m x"), \
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
        with mock.patch.object(h, "get_command", return_value=command), \
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
