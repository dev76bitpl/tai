"""Tests for scripts/dev-guards/guard_template_sync.py (ADR-002 acknowledgment model).

Zasada A: every guard proves (1) it blocks what it must, (2) it passes the rest.
"""
import importlib.util
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "scripts" / "dev-guards" / "guard_template_sync.py"


def _load():
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
