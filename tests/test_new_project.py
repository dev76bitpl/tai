"""Tests for scripts/new-project.py"""
import importlib.util
import json
import re
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
git_mod = sys.modules["new_project_git"]  # git steps live in their own module
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


# ── --stack is optional: the scope wizard normally sets the stack (set-stack.py) ──

REAL_EXAMPLE = ROOT / ".claude" / "hooks" / "config.json.example"


@pytest.fixture()
def real_template(tmp_path: Path) -> Path:
    """A template root holding the repository's real config.json.example."""
    hooks = tmp_path / "real-template" / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "config.json.example").write_text(REAL_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path / "real-template"


def _generated_config(template_root: Path, dest: Path, stack):
    (dest / ".claude" / "hooks").mkdir(parents=True)
    create_config_json(dest, template_root, dry_run=False, stack=stack)
    return json.loads((dest / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8"))


class TestDocsOfANewProject:
    """What is left in docs/ after --init, checked on a copy of the real template docs.

    The worked examples used to be deleted before anyone could use them, while the template's
    own session log (600+ lines) and its own test scenarios travelled into every project.
    """

    @pytest.fixture()
    def started(self, tmp_path):
        import shutil as _shutil
        root = tmp_path / "project"
        _shutil.copytree(ROOT / "docs", root / "docs")
        (root / ".claude" / "hooks").mkdir(parents=True)
        (root / "scripts").mkdir()
        (root / "README.md").write_text("# AI Template\n")
        with mock.patch.object(mod, "create_config_json"), mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod, "hand_over_to_setup"):
            mod.init_in_place(root, dry_run=False, do_git=False)
        return root / "docs"

    @pytest.mark.parametrize("example", ["SETUP.example.md", "TASKS.example.md", "ROADMAP.example.md",
                                         "ADR-001-example.md", "README.md"])
    def test_should_keep_worked_examples_in_the_project(self, started, example):
        assert (started / "examples" / example).is_file()

    def test_should_start_the_project_with_an_empty_session_log(self, started):
        log = (started / "TASKS.md").read_text(encoding="utf-8")
        assert "## Stan sesji" in log and "examples/TASKS.example.md" in log
        assert len(log.splitlines()) < 20
        assert not re.search(r"^- 20\d\d-\d\d-\d\d", log, flags=re.M)  # no entries of the template

    def test_should_not_teach_backlog_in_the_session_log_pattern(self):
        # open work lives in issues; the old pattern showed "Backlog" and "Aktualny fokus" checklists
        for path in (ROOT / "docs" / "examples" / "TASKS.example.md",):
            text = path.read_text(encoding="utf-8")
            assert "- [ ]" not in text and "## Backlog" not in text
        assert "- [ ]" not in mod.SCAFFOLD_DOCS["TASKS.md"] and "Backlog" not in mod.SCAFFOLD_DOCS["TASKS.md"]

    @pytest.mark.parametrize("name, limit", [("SETUP.md", 160), ("TESTING.md", 60)])
    def test_should_leave_project_skeletons_not_template_documents(self, started, name, limit):
        text = (started / name).read_text(encoding="utf-8")
        assert len(text.splitlines()) <= limit, f"{name} is no longer a skeleton"
        assert "new-project.py" not in text and "Scenariusz 1" not in text

    def test_should_remove_template_only_scenarios_and_decisions(self, started):
        assert not (started / "TEMPLATE_TESTING.md").exists()
        assert [p.name for p in (started / "adr").glob("*.md")] == []

    @pytest.mark.parametrize("name", ["GUARDS.md", "GUARDS_TESTING.md"])
    def test_should_keep_the_description_of_the_guards_the_project_uses(self, started, name):
        assert (started / name).is_file()

    def test_should_not_mention_the_deleted_start_script_in_documents_that_stay(self, started):
        # GUARDS.md describes the guided start, which begins with new-project.py; nothing else should
        for path in started.rglob("*.md"):
            if path.name in ("GUARDS.md", "GUARDS_TESTING.md", "AI_TEMPLATE_NOTES.md"):
                continue
            assert "new-project.py" not in path.read_text(encoding="utf-8"), path.name

    def test_should_refer_to_the_examples_from_the_rules(self):
        assert "docs/examples/" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    def test_should_list_in_readme_scaffold_only_documents_the_project_has(self, started):
        for target in re.findall(r"\]\((docs/[^)]+)\)", mod.README_SCAFFOLD):
            assert (started.parent / target).exists(), target


class TestGuardCommandsInNewProject:
    """A new project must not inherit lint/test commands of a stack it does not use."""

    def test_should_not_ship_lint_or_test_commands_in_the_example(self):
        example = json.loads(REAL_EXAMPLE.read_text(encoding="utf-8"))
        assert "lint" not in example and "test" not in example

    @pytest.mark.parametrize("stack", [None, "node", "laravel", "prestashop"])
    def test_should_leave_guard_commands_to_autodetection_after_init(self, real_template, dest, stack):
        data = _generated_config(real_template, dest, stack)
        assert "lint" not in data and "test" not in data

    def test_should_show_lint_and_test_guard_output_on_every_commit(self):
        # verbose: true — otherwise "checks NOTHING" hides behind a green "Passed"
        config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        for hook in ("guard-lint", "guard-tests"):
            block = config.split(f"- id: {hook}\n", 1)[1].split("- id: ", 1)[0]
            assert "verbose: true" in block, hook


class TestStackFlag:
    def test_should_leave_guards_on_defaults_when_no_stack_is_given(self, real_template, dest):
        data = _generated_config(real_template, dest, None)
        assert data["src_dirs"] == ["src"]
        active = " ".join(description for _, description in data["adr_patterns"])
        assert "PrestaShop" not in active and "WordPress" not in active and "Magento" not in active

    def test_should_apply_the_stack_table_when_flag_is_given(self, real_template, dest):
        data = _generated_config(real_template, dest, "prestashop")
        assert data["src_dirs"] == ["modules", "override"]
        assert "nowy moduł PrestaShop" in [description for _, description in data["adr_patterns"]]

    def test_should_not_ask_anything_during_init(self):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--no-git"]):
            with mock.patch("builtins.input", side_effect=AssertionError("init must not ask")):
                with mock.patch.object(mod, "init_in_place") as m:
                    mod.main()
        m.assert_called_once_with(ROOT, False, do_git=False, stack=None)

    def test_should_pass_stack_from_flag_to_init(self):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--no-git", "--stack", "laravel"]):
            with mock.patch.object(mod, "init_in_place") as m:
                mod.main()
        m.assert_called_once_with(ROOT, False, do_git=False, stack="laravel")

    def test_should_reject_unknown_stack_flag(self):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--stack", "cobol"]):
            with pytest.raises(SystemExit):
                mod.main()

    def test_should_apply_stack_during_init(self, real_template):
        (real_template / "scripts").mkdir()
        with mock.patch.object(mod, "create_settings_local"):
            mod.init_in_place(real_template, dry_run=False, do_git=False, stack="laravel")
        data = json.loads((real_template / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8"))
        assert data["src_dirs"] == ["app"]

    def test_should_keep_set_stack_script_in_the_project_after_init(self, tmp_path):
        # the scope wizard runs it after the interview; new-project.py itself is deleted
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "set-stack.py").write_text("# stays")
        (tmp_path / "scripts" / "new-project.py").write_text("# self")
        (tmp_path / ".claude" / "hooks").mkdir(parents=True)
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(tmp_path, dry_run=False, do_git=False)
        assert (tmp_path / "scripts" / "set-stack.py").exists()
        assert not (tmp_path / "scripts" / "new-project.py").exists()


# ── after cleaning, init hands over to the guided steps (project-setup.py) ───

class TestHandOver:
    def _root(self, tmp_path: Path, with_setup: bool = True) -> Path:
        (tmp_path / ".claude" / "hooks").mkdir(parents=True)
        (tmp_path / "scripts").mkdir()
        if with_setup:
            (tmp_path / "scripts" / "project-setup.py").write_text("# steps")
        return tmp_path

    def test_should_run_project_setup_in_the_project_at_the_end_of_init(self, tmp_path):
        root = self._root(tmp_path)
        with mock.patch.object(mod, "create_config_json"), mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod.os, "chdir") as chdir, mock.patch.object(mod.os, "execv") as execv:
            mod.init_in_place(root, dry_run=False, do_git=False)
        chdir.assert_called_once_with(root)
        execv.assert_called_once_with(sys.executable, [sys.executable, str(root / "scripts" / "project-setup.py")])

    def test_should_not_hand_over_during_dry_run(self, tmp_path):
        root = self._root(tmp_path)
        with mock.patch.object(mod, "hand_over_to_setup") as hand_over:
            mod.init_in_place(root, dry_run=True, do_git=False)
        hand_over.assert_not_called()

    def test_should_point_to_setup_docs_when_steps_script_is_missing(self, tmp_path, capsys):
        root = self._root(tmp_path, with_setup=False)
        with mock.patch.object(mod.os, "execv") as execv:
            mod.hand_over_to_setup(root)
        execv.assert_not_called()
        assert "docs/SETUP.md" in capsys.readouterr().out

    def test_should_keep_the_steps_script_in_the_project_after_init(self, tmp_path):
        # it has to be runnable again after a failed step is fixed; new-project.py deletes itself
        root = self._root(tmp_path)
        (root / "scripts" / "new-project.py").write_text("# self")
        with mock.patch.object(mod, "create_config_json"), mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod, "hand_over_to_setup"):
            mod.init_in_place(root, dry_run=False, do_git=False)
        assert (root / "scripts" / "project-setup.py").exists()
        assert not (root / "scripts" / "new-project.py").exists()

    def test_should_not_tell_the_user_to_delete_git_in_readme(self):
        # README used to say `rm -rf .git && git init` after --init, wiping the freshly
        # installed guards and the init commit
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "rm -rf .git" not in readme


class TestTemplateOnlyScripts:
    def test_should_remove_every_template_only_script_during_init(self, tmp_path):
        (tmp_path / ".claude" / "hooks").mkdir(parents=True)
        (tmp_path / "scripts").mkdir()
        for name in [*mod.TEMPLATE_ONLY_SCRIPTS, "set-stack.py", "project-setup.py"]:
            (tmp_path / "scripts" / name).write_text("# x")
        with mock.patch.object(mod, "create_config_json"), mock.patch.object(mod, "create_settings_local"), \
             mock.patch.object(mod, "hand_over_to_setup"):
            mod.init_in_place(tmp_path, dry_run=False, do_git=False)
        left = sorted(p.name for p in (tmp_path / "scripts").iterdir())
        assert left == ["project-setup.py", "set-stack.py"]

    def test_should_list_every_new_project_file_as_template_only(self):
        on_disk = {p.name for p in (ROOT / "scripts").glob("new[-_]project*.py")}
        assert on_disk == set(mod.TEMPLATE_ONLY_SCRIPTS)

    @pytest.mark.parametrize("name", ["new-project.py", "new_project_git.py"])
    def test_should_keep_logic_files_under_the_size_limit(self, name):
        # CLAUDE.md rule 20: logic files max 400 lines; data files (new_project_data.py) are exempt
        assert len((ROOT / "scripts" / name).read_text(encoding="utf-8").splitlines()) <= 400


class TestMainBranch:
    def test_should_start_on_main_whatever_the_machine_git_config_says(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
        monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
        for name in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
            monkeypatch.setenv(name, "Test")
        for name in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
            monkeypatch.setenv(name, "test@example.com")
        for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
            monkeypatch.delenv(name, raising=False)
        (tmp_path / "file.txt").write_text("x")
        mod.fresh_git_history(tmp_path, dry_run=False)
        import subprocess
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=tmp_path,
                                capture_output=True, text=True).stdout.strip()
        assert branch == "main"
        # the guided start never runs `npm install`, so it must set what setup-hooks.mjs sets
        autocrlf = subprocess.run(["git", "config", "--local", "core.autocrlf"], cwd=tmp_path,
                                  capture_output=True, text=True).stdout.strip()
        assert autocrlf == "input"


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

    def test_should_keep_guard_tests_when_removing_template_tests(self, tmp_path):
        # A new project must be able to satisfy "no guard without a test" out of the box:
        # guard tests live next to the guards and travel with them, only tests/ (tests of the
        # template's own tooling) goes away.
        fake_root = self._setup(tmp_path)
        hook_tests = fake_root / ".claude" / "hooks" / "tests"
        commit_tests = fake_root / "scripts" / "dev-guards" / "tests"
        for directory in (hook_tests, commit_tests):
            directory.mkdir(parents=True)
            (directory / "test_guard_example.py").write_text("# guard test")
        (fake_root / "pytest.ini").write_text("[pytest]\n")
        with mock.patch.object(mod, "create_config_json"):
            with mock.patch.object(mod, "create_settings_local"):
                mod.init_in_place(fake_root, dry_run=False, do_git=False)
        assert not (fake_root / "tests").exists()
        assert (hook_tests / "test_guard_example.py").exists()
        assert (commit_tests / "test_guard_example.py").exists()
        assert (fake_root / "pytest.ini").exists()

    def test_should_not_list_guard_test_dirs_as_template_meta(self):
        removed = [Path(name) for name in TEMPLATE_META]
        for kept in (".claude/hooks/tests", "scripts/dev-guards/tests", "pytest.ini"):
            kept_path = Path(kept)
            assert not any(kept_path == r or r in kept_path.parents for r in removed), kept

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
        m.assert_called_once_with(ROOT, True, do_git=True, stack=None)

    def test_no_git_flag_disables_git(self, tmp_path):
        with mock.patch.object(sys, "argv", ["new-project.py", "--init", "--no-git"]):
            with mock.patch.object(mod, "init_in_place") as m:
                mod.main()
        m.assert_called_once_with(ROOT, False, do_git=False, stack=None)


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
        with mock.patch.object(git_mod.subprocess, "run",
                               side_effect=lambda *a, **k: calls.append(a[0])) as _run:
            with mock.patch.object(git_mod.shutil, "rmtree") as rmtree:
                mod.fresh_git_history(tmp_path, dry_run=False)
        rmtree.assert_called_once()
        # git init, line-ending setting, git add -A, git commit ... in order
        assert calls[0][:2] == ["git", "init"]
        assert calls[1] == ["git", "config", "--local", "core.autocrlf", "input"]
        assert calls[2][:3] == ["git", "add", "-A"]
        assert calls[3][:2] == ["git", "commit"]

    def test_dry_run_runs_no_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        with mock.patch.object(git_mod.subprocess, "run") as run:
            with mock.patch.object(git_mod.shutil, "rmtree") as rmtree:
                mod.fresh_git_history(tmp_path, dry_run=True)
        run.assert_not_called()
        rmtree.assert_not_called()

    def test_git_failure_warns_not_raises(self, tmp_path):
        import subprocess as sp
        with mock.patch.object(git_mod.subprocess, "run",
                               side_effect=sp.CalledProcessError(1, "git")):
            with mock.patch.object(git_mod.shutil, "rmtree"):
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
        with mock.patch.object(git_mod.subprocess, "run") as run:
            mod.install_guards(tmp_path, dry_run=True)
        run.assert_not_called()

    def test_installs_when_pre_commit_available(self, tmp_path):
        with mock.patch.object(git_mod, "_resolve_pre_commit", return_value=["pre-commit"]):
            with mock.patch.object(git_mod.subprocess, "run",
                                   return_value=mock.Mock(returncode=0, stderr="")) as run:
                mod.install_guards(tmp_path, dry_run=False)
        args = run.call_args[0][0]
        assert args[:2] == ["pre-commit", "install"]
        assert "--hook-type" in args and "commit-msg" in args

    def test_warns_when_pre_commit_missing(self, tmp_path):
        with mock.patch.object(git_mod, "_resolve_pre_commit", return_value=None):
            with mock.patch.object(git_mod.subprocess, "run") as run:
                with mock.patch.object(git_mod, "warn") as warn:
                    mod.install_guards(tmp_path, dry_run=False)
        run.assert_not_called()
        warn.assert_called_once()
