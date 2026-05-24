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

    def test_ai_template_path_set(self, template, dest):
        (dest / ".claude" / "hooks").mkdir(parents=True)
        create_config_json(dest, template, dry_run=False)
        data = json.loads((dest / ".claude" / "hooks" / "config.json").read_text())
        assert data["ai_template_path"] == str(template)

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
                mod.init_in_place(fake_root, dry_run=False)
        assert not (fake_root / "tests").exists()
        assert (fake_root / "README.md").read_text() == README_SCAFFOLD

    def test_writes_readme_scaffold(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False)
        assert (fake_root / "README.md").read_text() == README_SCAFFOLD

    def test_self_deletes_script(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False)
        assert not (fake_root / "scripts" / "new-project.py").exists()
        assert (fake_root / "scripts" / "update-skills.py").exists()

    def test_dry_run_removes_nothing(self, tmp_path):
        fake_root = self._setup(tmp_path)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=True)
        assert (fake_root / "tests").exists()
        assert (fake_root / "README.md").read_text() == "# AI Template\n"
        assert (fake_root / "scripts" / "new-project.py").exists()

    def test_init_flag_triggers_init_in_place(self, tmp_path):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--dry-run"]):
            with mock.patch.object(mod, "init_in_place") as m:
                mod.main()
        m.assert_called_once_with(ROOT, True)
