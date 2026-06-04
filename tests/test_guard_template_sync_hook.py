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
