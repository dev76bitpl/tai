"""Tests for scripts/dev-guards/guard_template_sync.py (ADR-002 acknowledgment model).

Zasada A: every guard proves (1) it blocks what it must, (2) it passes the rest.
"""
import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

GUARD = Path(__file__).resolve().parents[1] / "guard_template_sync.py"


def _load():
    # .claude/hooks/stack.py is a different module with the same name; drop a cached one
    # so the guard imports the stack.py that sits next to it, whatever the test order.
    sys.modules.pop("stack", None)
    spec = importlib.util.spec_from_file_location("guard_template_sync", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g = _load()


def _template_clone(tmp_path: Path) -> Path:
    """A local template clone with a CLAUDE.md."""
    (tmp_path / "CLAUDE.md").write_text("# template\n", encoding="utf-8")
    return tmp_path


# ── _staged_touches_claude ────────────────────────────────────────────────────

class TestStagedTouchesClaude:
    def test_root_claude(self):
        assert g._staged_touches_claude(["CLAUDE.md"]) is True

    def test_nested_claude(self):
        assert g._staged_touches_claude(["sub/CLAUDE.md"]) is True

    def test_other_md_does_not_count(self):
        assert g._staged_touches_claude(["docs/README.md", "x.py"]) is False

    def test_empty(self):
        assert g._staged_touches_claude([]) is False


# ── _local_template_claude ────────────────────────────────────────────────────

class TestLocalTemplateClaude:
    def test_empty_path_is_none(self):
        assert g._local_template_claude("") is None

    def test_url_is_none(self):
        assert g._local_template_claude("https://github.com/x/tai.git") is None
        assert g._local_template_claude("git@github.com:x/tai.git") is None

    def test_dir_without_claude_is_none(self, tmp_path):
        assert g._local_template_claude(str(tmp_path)) is None

    def test_valid_clone_returns_claude_path(self, tmp_path):
        clone = _template_clone(tmp_path)
        result = g._local_template_claude(str(clone))
        assert result == clone / "CLAUDE.md"


# ── main() decision matrix ────────────────────────────────────────────────────

class TestMain:
    def _patch(self, msg="subject\n\nbody", staged=None, config=None, touched=False):
        staged = staged if staged is not None else ["CLAUDE.md"]
        config = config if config is not None else {}
        return (
            mock.patch.object(g, "read_commit_msg", return_value=msg),
            mock.patch.object(g, "get_staged_files", return_value=staged),
            mock.patch.object(g, "load_config", return_value=config),
            mock.patch.object(g, "_template_claude_touched", return_value=touched),
        )

    def _run(self, **kw):
        patches = self._patch(**kw)
        with patches[0], patches[1], patches[2], patches[3]:
            g.main(["guard", "/tmp/msg"])

    # ── passes ──
    def test_skip_sync_passes(self):
        self._run(msg="docs: x\n\n[skip-sync]")  # must not raise

    def test_claude_not_staged_passes(self):
        self._run(staged=["docs/README.md"])

    def test_is_template_passes(self):
        self._run(config={"is_template": True})

    def test_local_template_touched_passes(self, tmp_path):
        clone = _template_clone(tmp_path)
        self._run(config={"ai_template_path": str(clone)}, touched=True)

    # ── blocks ──
    def test_no_path_blocks_acknowledge(self):
        with pytest.raises(SystemExit):
            self._run(config={})

    def test_url_path_blocks_acknowledge(self):
        with pytest.raises(SystemExit):
            self._run(config={"ai_template_path": "https://github.com/x/tai.git"})

    def test_missing_dir_blocks_acknowledge(self, tmp_path):
        with pytest.raises(SystemExit):
            self._run(config={"ai_template_path": str(tmp_path / "nope")})

    def test_local_template_untouched_blocks(self, tmp_path):
        clone = _template_clone(tmp_path)
        with pytest.raises(SystemExit):
            self._run(config={"ai_template_path": str(clone)}, touched=False)


# ── end to end: the guard as a separate process, exit code checked ───────────
# Everything above mocks the inputs and only asserts "SystemExit was raised". These run the
# real script in a real repository and assert the exit code pre-commit acts on.

from harness import BLOCKED, commit, git, make_repo, run_guard, stage, write_config  # noqa: E402


@pytest.fixture
def clone(tmp_path):
    """A local template clone: its own repository with a committed CLAUDE.md."""
    root = make_repo(tmp_path / "template")
    stage(root, "CLAUDE.md", "# template rules\n")
    commit(root)
    return root


class TestEndToEnd:
    GUARD = "guard_template_sync"

    def test_should_block_when_claude_md_is_staged_and_no_clone_is_configured(self, repo):
        stage(repo, "CLAUDE.md")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == BLOCKED
        assert "[BLOCK] CLAUDE.md staged — confirm where this change belongs" in result.stderr

    def test_should_block_when_template_clone_has_no_matching_change(self, repo, clone):
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "CLAUDE.md")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == BLOCKED
        assert "the template's CLAUDE.md has no matching changes" in result.stderr
        assert str(clone / "CLAUDE.md") in result.stderr

    def test_should_pass_when_template_clone_was_changed_too(self, repo, clone):
        write_config(repo, {"ai_template_path": str(clone)})
        (clone / "CLAUDE.md").write_text("# template rules\n\n## New rule\n", encoding="utf-8")
        stage(repo, "CLAUDE.md")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == 0, result.stderr

    def test_should_pass_when_skip_sync_flag_is_in_message(self, repo):
        stage(repo, "CLAUDE.md")
        assert run_guard(self.GUARD, repo, "docs: project rule\n\n[skip-sync] project only\n").returncode == 0

    def test_should_pass_when_claude_md_is_not_staged(self, repo):
        stage(repo, "docs/SETUP.md")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""

    def test_should_pass_in_the_template_repository_itself(self, repo):
        write_config(repo, {"is_template": True})
        stage(repo, "CLAUDE.md")
        assert run_guard(self.GUARD, repo).returncode == 0

    def test_should_block_when_commit_message_file_is_missing(self, repo):
        stage(repo, "docs/SETUP.md")
        result = run_guard(self.GUARD, repo, message=None)
        assert result.returncode == BLOCKED
        assert "guard_template_sync: no commit message file given" in result.stderr
