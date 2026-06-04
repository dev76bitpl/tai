"""Tests for scripts/new-project.py"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "new-project.py"


def _load():
    spec = importlib.util.spec_from_file_location("new_project", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load()
create_config_json = mod.create_config_json
create_settings_local = mod.create_settings_local
README_SCAFFOLD = mod.README_SCAFFOLD
TEMPLATE_META = mod.TEMPLATE_META


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def template(tmp_path: Path) -> Path:
    """Minimal template structure with config.json.example and settings.local.json.example."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)

    config_example = {
        "ai_template_path": "PLACEHOLDER",
        "repos": [{"name": "PLACEHOLDER", "tasks": "docs/TASKS.md"}],
    }
    (hooks / "config.json.example").write_text(
        json.dumps(config_example, indent=2), encoding="utf-8"
    )

    # settings.local.json.example lives in .claude/ directly (not hooks/)
    settings_example = '{"hooks": {"interpreter": "INTERPRETER"}}'
    (tmp_path / ".claude" / "settings.local.json.example").write_text(
        settings_example, encoding="utf-8"
    )

    return tmp_path


@pytest.fixture()
def dest(tmp_path: Path) -> Path:
    d = tmp_path / "new-project"
    d.mkdir()
    return d


# ── create_config_json ────────────────────────────────────────────────────────

class TestCreateConfigJson:
    def test_writes_file(self, template, dest):
        (dest / ".claude" / "hooks").mkdir(parents=True)
        create_config_json(dest, template, dry_run=False)
        cfg = dest / ".claude" / "hooks" / "config.json"
        assert cfg.exists()

    def test_ai_template_path_left_as_placeholder(self, template, dest):
        # ADR-002 decision 3: generator must NOT auto-fill ai_template_path (bug A).
        # The example placeholder is preserved verbatim.
        (dest / ".claude" / "hooks").mkdir(parents=True)
        create_config_json(dest, template, dry_run=False)
        data = json.loads((dest / ".claude" / "hooks" / "config.json").read_text())
        assert data["ai_template_path"] == "PLACEHOLDER"

    def test_repo_name_set_to_dest_name(self, template, dest):
        (dest / ".claude" / "hooks").mkdir(parents=True)
        create_config_json(dest, template, dry_run=False)
        data = json.loads((dest / ".claude" / "hooks" / "config.json").read_text())
        assert data["repos"][0]["name"] == dest.name

    def test_dry_run_does_not_write(self, template, dest):
        create_config_json(dest, template, dry_run=True)
        assert not (dest / ".claude" / "hooks" / "config.json").exists()

    def test_missing_example_is_no_op(self, tmp_path, dest):
        """If template has no example file, function silently returns."""
        empty_template = tmp_path / "empty-template"
        empty_template.mkdir()
        create_config_json(dest, empty_template, dry_run=False)
        assert not (dest / ".claude" / "hooks" / "config.json").exists()


# ── create_settings_local ─────────────────────────────────────────────────────

class TestCreateSettingsLocal:
    def _setup(self, tmp_path):
        tpl = tmp_path / "template"
        (tpl / ".claude").mkdir(parents=True)
        # settings.local.json.example lives in .claude/ directly (not hooks/)
        (tpl / ".claude" / "settings.local.json.example").write_text(
            '{"interpreter": "INTERPRETER"}', encoding="utf-8"
        )
        dst = tmp_path / "dest"
        (dst / ".claude").mkdir(parents=True)
        return tpl, dst

    def test_linux_interpreter(self, tmp_path):
        tpl, dst = self._setup(tmp_path)
        with mock.patch("sys.platform", "linux"):
            create_settings_local(dst, tpl, dry_run=False)
        content = (dst / ".claude" / "settings.local.json").read_text()
        assert "python3" in content
        assert "INTERPRETER" not in content

    def test_windows_interpreter(self, tmp_path):
        tpl, dst = self._setup(tmp_path)
        with mock.patch("sys.platform", "win32"):
            create_settings_local(dst, tpl, dry_run=False)
        content = (dst / ".claude" / "settings.local.json").read_text()
        assert '"py"' in content
        assert "INTERPRETER" not in content

    def test_dry_run_does_not_write(self, template, dest):
        create_settings_local(dest, template, dry_run=True)
        assert not (dest / ".claude" / "settings.local.json").exists()


# ── main() guard: non-empty dest ──────────────────────────────────────────────

class TestMainGuard:
    def test_nonempty_dest_exits(self, tmp_path):
        occupied = tmp_path / "occupied"
        occupied.mkdir()
        (occupied / "existing.txt").write_text("something")

        with mock.patch.object(sys, "argv", ["new-project.py", str(occupied)]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code != 0

    def test_no_args_exits(self):
        with mock.patch.object(sys, "argv", ["new-project.py"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code != 0


# ── init_in_place ─────────────────────────────────────────────────────────────

class TestInitInPlace:
    def _setup(self, tmp_path: Path) -> Path:
        """Create a minimal fake template clone at tmp_path."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_foo.py").write_text("# test")
        (tmp_path / "README.md").write_text("# AI Template\n")
        (tmp_path / "CLAUDE.md").write_text("# Project\n")
        (tmp_path / ".claude" / "hooks").mkdir(parents=True)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "update-skills.py").write_text("# update")
        # Simulate the script itself being there
        script = tmp_path / "scripts" / "new-project.py"
        script.write_text("# self")
        return tmp_path

    def test_removes_template_meta(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False, do_git=False)
        assert not (fake_root / "tests").exists()
        assert (fake_root / "README.md").read_text(encoding="utf-8") == README_SCAFFOLD

    def test_writes_readme_scaffold(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False, do_git=False)
        assert (fake_root / "README.md").read_text(encoding="utf-8") == README_SCAFFOLD

    def test_resets_adr_dir(self, tmp_path):
        fake_root = self._setup(tmp_path)
        adr = fake_root / "docs" / "adr"
        adr.mkdir(parents=True)
        (adr / "ADR-002-template-sync-acknowledgment.md").write_text("# internal\n")
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False, do_git=False)
        assert list(adr.glob("*.md")) == []
        assert (adr / ".gitkeep").exists()

    def test_self_deletes_script(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False, do_git=False)
        assert not (fake_root / "scripts" / "new-project.py").exists()
        assert (fake_root / "scripts" / "update-skills.py").exists()

    def test_dry_run_removes_nothing(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=True, do_git=False)
        assert (fake_root / "tests").exists()
        assert (fake_root / "README.md").read_text() == "# AI Template\n"
        assert (fake_root / "scripts" / "new-project.py").exists()

    def test_init_flag_triggers_init_in_place(self, tmp_path):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--dry-run"]):
            with mock.patch.object(mod, "init_in_place") as m:
                mod.main()
        m.assert_called_once_with(ROOT, True, do_git=True)

    def test_no_git_flag_disables_git(self, tmp_path):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--no-git"]):
            with mock.patch.object(mod, "init_in_place") as m:
                mod.main()
        m.assert_called_once_with(ROOT, False, do_git=False)


# ── reset_versioning ───────────────────────────────────────────────────────────

class TestResetVersioning:
    def _setup(self, tmp_path: Path) -> Path:
        (tmp_path / "CHANGELOG.md").write_text("# template history\n")
        (tmp_path / ".release-please-manifest.json").write_text('{\n  ".": "0.1.14"\n}\n')
        return tmp_path

    def test_removes_inherited_changelog(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_versioning(root, dry_run=False)
        assert not (root / "CHANGELOG.md").exists()

    def test_resets_manifest_to_zero(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_versioning(root, dry_run=False)
        data = json.loads((root / ".release-please-manifest.json").read_text())
        assert data == {".": "0.0.0"}

    def test_dry_run_changes_nothing(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_versioning(root, dry_run=True)
        assert (root / "CHANGELOG.md").exists()
        data = json.loads((root / ".release-please-manifest.json").read_text())
        assert data == {".": "0.1.14"}

    def test_missing_files_is_no_op(self, tmp_path):
        # Neither file present — must not raise.
        mod.reset_versioning(tmp_path, dry_run=False)
        assert not (tmp_path / "CHANGELOG.md").exists()


# ── reset_adr_dir ──────────────────────────────────────────────────────────────

class TestResetAdrDir:
    def _setup(self, tmp_path: Path) -> Path:
        adr = tmp_path / "docs" / "adr"
        adr.mkdir(parents=True)
        (adr / "ADR-001-example.md").write_text("# example\n")
        (adr / "ADR-002-template-sync-acknowledgment.md").write_text("# internal\n")
        return tmp_path

    def test_removes_all_template_adrs(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_adr_dir(root, dry_run=False)
        assert list((root / "docs" / "adr").glob("*.md")) == []

    def test_leaves_gitkeep(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_adr_dir(root, dry_run=False)
        assert (root / "docs" / "adr" / ".gitkeep").exists()

    def test_dry_run_changes_nothing(self, tmp_path):
        root = self._setup(tmp_path)
        mod.reset_adr_dir(root, dry_run=True)
        names = {p.name for p in (root / "docs" / "adr").glob("*.md")}
        assert "ADR-002-template-sync-acknowledgment.md" in names
        assert not (root / "docs" / "adr" / ".gitkeep").exists()

    def test_missing_dir_is_no_op(self, tmp_path):
        # No docs/adr present — must not raise.
        mod.reset_adr_dir(tmp_path, dry_run=False)
        assert not (tmp_path / "docs" / "adr").exists()


# ── fresh_git_history ──────────────────────────────────────────────────────────

class TestFreshGitHistory:
    def test_removes_git_dir_and_makes_init_commit(self, tmp_path):
        (tmp_path / ".git").mkdir()
        calls = []
        with mock.patch.object(mod.subprocess, "run",
                               side_effect=lambda *a, **k: calls.append(a[0])) as _run:
            with mock.patch.object(mod.shutil, "rmtree") as rmtree:
                mod.fresh_git_history(tmp_path, dry_run=False)
        rmtree.assert_called_once()
        # git init, git add -A, git commit ... in order
        assert calls[0][:2] == ["git", "init"]
        assert calls[1][:3] == ["git", "add", "-A"]
        assert calls[2][:2] == ["git", "commit"]

    def test_dry_run_runs_no_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        with mock.patch.object(mod.subprocess, "run") as run:
            with mock.patch.object(mod.shutil, "rmtree") as rmtree:
                mod.fresh_git_history(tmp_path, dry_run=True)
        run.assert_not_called()
        rmtree.assert_not_called()

    def test_git_failure_warns_not_raises(self, tmp_path):
        import subprocess as sp
        with mock.patch.object(mod.subprocess, "run",
                               side_effect=sp.CalledProcessError(1, "git")):
            with mock.patch.object(mod.shutil, "rmtree"):
                # Must not raise — cleaning already happened.
                mod.fresh_git_history(tmp_path, dry_run=False)


# ── init_in_place: versioning + git wiring ─────────────────────────────────────

class TestInitInPlaceVersioning:
    def _setup(self, tmp_path: Path) -> Path:
        (tmp_path / "CLAUDE.md").write_text("# Project\n")
        (tmp_path / "CHANGELOG.md").write_text("# template history\n")
        (tmp_path / ".release-please-manifest.json").write_text('{\n  ".": "0.1.14"\n}\n')
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "new-project.py").write_text("# self")
        return tmp_path

    def test_resets_versioning(self, tmp_path):
        root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"), \
             mock.patch.object(mod, "create_settings_local"):
            mod.init_in_place(root, dry_run=False, do_git=False)
        assert not (root / "CHANGELOG.md").exists()
        assert json.loads((root / ".release-please-manifest.json").read_text()) == {".": "0.0.0"}

    def test_do_git_invokes_fresh_history_and_guards(self, tmp_path):
        root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"), \
             mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod, "fresh_git_history") as fresh, \
             mock.patch.object(mod, "install_guards") as guards:
            mod.init_in_place(root, dry_run=False, do_git=True)
        fresh.assert_called_once()
        guards.assert_called_once()

    def test_no_git_skips_fresh_history_and_guards(self, tmp_path):
        root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"), \
             mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod, "fresh_git_history") as fresh, \
             mock.patch.object(mod, "install_guards") as guards:
            mod.init_in_place(root, dry_run=False, do_git=False)
        fresh.assert_not_called()
        guards.assert_not_called()


# ── install_guards ─────────────────────────────────────────────────────────────

class TestInstallGuards:
    def test_dry_run_runs_nothing(self, tmp_path):
        with mock.patch.object(mod.subprocess, "run") as run:
            mod.install_guards(tmp_path, dry_run=True)
        run.assert_not_called()

    def test_installs_when_pre_commit_available(self, tmp_path):
        with mock.patch.object(mod, "_resolve_pre_commit", return_value=["pre-commit"]):
            with mock.patch.object(mod.subprocess, "run",
                                   return_value=mock.Mock(returncode=0, stderr="")) as run:
                mod.install_guards(tmp_path, dry_run=False)
        args = run.call_args[0][0]
        assert args[:2] == ["pre-commit", "install"]
        assert "--hook-type" in args and "commit-msg" in args

    def test_warns_when_pre_commit_missing(self, tmp_path):
        with mock.patch.object(mod, "_resolve_pre_commit", return_value=None):
            with mock.patch.object(mod.subprocess, "run") as run:
                with mock.patch.object(mod, "warn") as warn:
                    mod.install_guards(tmp_path, dry_run=False)
        run.assert_not_called()
        warn.assert_called_once()
