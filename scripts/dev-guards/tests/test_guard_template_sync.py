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


# ── _local_template_root ──────────────────────────────────────────────────────

class TestLocalTemplateRoot:
    def test_empty_path_is_none(self):
        assert g._local_template_root("") is None

    def test_url_is_none(self):
        assert g._local_template_root("https://github.com/x/tai.git") is None
        assert g._local_template_root("git@github.com:x/tai.git") is None

    def test_missing_dir_is_none(self, tmp_path):
        assert g._local_template_root(str(tmp_path / "nope")) is None

    def test_existing_dir_is_the_root(self, tmp_path):
        assert g._local_template_root(str(tmp_path)) == tmp_path


# ── main() without a local clone: acknowledgment whenever CLAUDE.md is staged ──

class TestMainWithoutClone:
    def _run(self, msg="docs: x\n\nbody", staged=None, config=None, source=""):
        staged = staged if staged is not None else ["CLAUDE.md"]
        with mock.patch.object(g, "read_commit_msg", return_value=msg), \
             mock.patch.object(g, "get_staged_files", return_value=staged), \
             mock.patch.object(g, "load_config", return_value=config or {}), \
             mock.patch.object(g, "_template_source", return_value=source):
            g.main(["guard", "/tmp/msg"])

    def test_skip_sync_with_reason_passes(self):
        self._run(msg="docs: x\n\n[skip-sync] rule only matters here")  # must not raise

    def test_claude_not_staged_passes(self):
        self._run(staged=["docs/README.md"])

    def test_is_template_passes(self):
        self._run(config={"is_template": True})

    def test_no_path_blocks(self):
        with pytest.raises(SystemExit):
            self._run()

    def test_url_blocks(self):
        with pytest.raises(SystemExit):
            self._run(source="https://github.com/x/tai.git")

    def test_missing_dir_blocks(self, tmp_path):
        with pytest.raises(SystemExit):
            self._run(source=str(tmp_path / "nope"))

    def test_bare_skip_sync_blocks(self, capsys):
        # tai#243: the flag alone is no decision; it needs a reason on its line.
        with pytest.raises(SystemExit):
            self._run(msg="docs: x\n\n[skip-sync]")
        assert "bez powodu" in capsys.readouterr().err

    def test_missing_shared_module_blocks_with_a_hint(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(g, "HOOKS_DIR", tmp_path)
        monkeypatch.setattr(sys, "path", [p for p in sys.path if not p.endswith("/.claude/hooks")])
        monkeypatch.delitem(sys.modules, "sync_ack", raising=False)
        with pytest.raises(SystemExit):
            self._run(msg="docs: x\n\n[skip-sync] rule only matters here")
        assert "sync_ack.py is missing" in capsys.readouterr().err


# ── end to end: the guard as a separate process, exit code checked ───────────
# The unit tests above mock the inputs and only assert "SystemExit was raised". These run the
# real script in a real repository and assert the exit code pre-commit acts on.

from harness import BLOCKED, commit, git, make_repo, run_guard, stage, write_config  # noqa: E402

RULES = "# rules\n\n## Old rule\n"
NEW_RULE = RULES + "\n## New rule\n"


@pytest.fixture
def clone(tmp_path):
    """A local template clone: its own repository with a committed CLAUDE.md."""
    root = make_repo(tmp_path / "template")
    stage(root, "CLAUDE.md", RULES)
    commit(root)
    return root


class TestEndToEnd:
    GUARD = "guard_template_sync"

    def test_should_block_when_claude_md_is_staged_and_no_clone_is_configured(self, repo):
        stage(repo, "CLAUDE.md")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == BLOCKED
        assert "[BLOCK] Template documents staged — confirm where this change belongs" in result.stderr
        assert "No local template clone found" in result.stderr

    def test_should_block_and_name_the_section_the_template_lacks(self, repo, clone):
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "CLAUDE.md", NEW_RULE)
        result = run_guard(self.GUARD, repo)
        assert result.returncode == BLOCKED
        assert "CLAUDE.md: sekcja jest w projekcie, brakuje w template  →  ## New rule" in result.stderr
        assert f"Template clone: {clone}" in result.stderr

    def test_should_pass_when_the_template_has_every_section(self, repo, clone):
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "CLAUDE.md", RULES + "\nproject text inside an existing section\n")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == 0, result.stderr

    def test_should_pass_when_the_section_is_already_committed_in_the_template(self, repo, clone):
        # the old rule ("is the clone's CLAUDE.md dirty?") blocked this: a clean clone that has it
        stage(clone, "CLAUDE.md", NEW_RULE)
        commit(clone)
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo).returncode == 0

    def test_should_block_when_the_clone_only_has_an_unrelated_change(self, repo, clone):
        # the old rule let this through: any uncommitted edit in the clone counted as "synced"
        (clone / "CLAUDE.md").write_text(RULES + "\n## Something else\n", encoding="utf-8")
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo).returncode == BLOCKED

    def test_should_compare_other_documents_the_template_owns(self, repo, clone):
        (clone / "template-files.json").write_text('{"copy": ["CLAUDE.md", "docs/RULES.md"]}', encoding="utf-8")
        stage(clone, "docs/RULES.md", "# r\n")
        commit(clone)
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "docs/RULES.md", "# r\n\n## Project rule\n")
        result = run_guard(self.GUARD, repo)
        assert result.returncode == BLOCKED
        assert "docs/RULES.md: sekcja jest w projekcie" in result.stderr

    def test_should_not_compare_the_projects_own_documents(self, repo, clone):
        write_config(repo, {"ai_template_path": str(clone)})
        stage(repo, "docs/PROJECT_SCOPE.md", "# scope\n\n## Only ours\n")
        assert run_guard(self.GUARD, repo).returncode == 0

    def test_should_pass_when_skip_sync_flag_is_in_message(self, repo):
        stage(repo, "CLAUDE.md")
        assert run_guard(self.GUARD, repo, "docs: project rule\n\n[skip-sync] rule is project only\n").returncode == 0

    def test_should_pass_when_no_document_is_staged(self, repo):
        stage(repo, "src/app.py")
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


class TestEndToEndTemplateLayers:
    """The commit guard finds the template clone the way the Claude Code hook does (#166).
    The project adds "## New rule"; a clone that has it lets the commit through."""
    GUARD = "guard_template_sync"

    @staticmethod
    def _has_rule(clone):
        (clone / "CLAUDE.md").write_text(NEW_RULE, encoding="utf-8")

    def test_should_find_the_clone_through_ai_template_path(self, repo, clone):
        self._has_rule(clone)
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo, AI_TEMPLATE_PATH=str(clone)).returncode == 0

    def test_should_find_the_clone_through_config_local_json(self, repo, clone):
        self._has_rule(clone)
        write_config(repo, {"ai_template_path": str(clone)}, name="config.local.json")
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo).returncode == 0

    def test_should_find_a_template_clone_next_to_the_project(self, repo, clone):
        write_config(clone, {"is_template": True})
        (clone / "skills-manifest.json").write_text("{}", encoding="utf-8")
        self._has_rule(clone)
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo).returncode == 0

    def test_should_prefer_ai_template_path_over_config(self, repo, clone, tmp_path):
        other = make_repo(tmp_path / "other")
        stage(other, "CLAUDE.md", RULES)
        commit(other)
        write_config(repo, {"ai_template_path": str(clone)})
        self._has_rule(clone)
        stage(repo, "CLAUDE.md", NEW_RULE)
        result = run_guard(self.GUARD, repo, AI_TEMPLATE_PATH=str(other))
        assert result.returncode == BLOCKED
        assert f"Template clone: {other}" in result.stderr

    def test_should_fall_back_to_config_when_the_hooks_stack_is_missing(self, repo, clone):
        # a project with an older .claude/hooks copy must not crash on every commit
        (repo / ".claude" / "hooks" / "stack.py").unlink()
        write_config(repo, {"ai_template_path": str(clone)})
        self._has_rule(clone)
        stage(repo, "CLAUDE.md", NEW_RULE)
        assert run_guard(self.GUARD, repo).returncode == 0


class TestEndToEndAcknowledgment:
    GUARD = "guard_template_sync"

    def test_should_block_bare_skip_sync(self, repo):
        stage(repo, "CLAUDE.md")
        result = run_guard(self.GUARD, repo, "docs: project rule\n\n[skip-sync]\n")
        assert result.returncode == BLOCKED, result.stderr
        assert "bez powodu" in result.stderr
        assert "Traceback" not in result.stderr
