"""Tests for scripts/select-skills.py — a project keeps only the skill groups it chose.

The template ships every skill; unchosen groups are removed from the project and recorded as
excluded, so template sync (the session hook and update-skills.py --sync) does not bring them back.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "select-skills.py"
REAL_MANIFEST = ROOT / "skills-manifest.json"


def _load(name="select_skills", path=SCRIPT):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def project(tmp_path, monkeypatch):
    """A project with the real manifest and a directory for every skill it names."""
    mod = _load()
    manifest = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
    (tmp_path / "skills-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    skills = tmp_path / ".claude" / "skills"
    for entry in manifest["skills"].values():
        (tmp_path / entry["local_path"]).mkdir(parents=True, exist_ok=True)
        (tmp_path / entry["local_path"] / "SKILL.md").write_text("# skill", encoding="utf-8")
    for name in manifest["custom_skills"]:
        (skills / name).mkdir(parents=True, exist_ok=True)
        (skills / name / "SKILL.md").write_text("# skill", encoding="utf-8")
    (skills / "seo").mkdir()  # a skill directory the manifest does not know about
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "MANIFEST_PATH", tmp_path / "skills-manifest.json")
    monkeypatch.setattr(mod, "CONFIG_PATH", tmp_path / ".claude" / "hooks" / "config.json")
    monkeypatch.setattr(mod, "SKILLS_DIR", skills)
    return mod, tmp_path


def _manifest(root: Path) -> dict:
    return json.loads((root / "skills-manifest.json").read_text(encoding="utf-8"))


def _dirs(root: Path) -> set[str]:
    return {p.name for p in (root / ".claude" / "skills").iterdir()}


GENERAL = {"git", "new-project-scope", "adr", "api", "debug", "deploy", "retro"}


# ── the table of groups matches the template ─────────────────────────────────

def test_should_cover_every_vendored_skill_with_exactly_one_group():
    mod = _load()
    vendored = [name for group in mod.GROUPS.values() for name in group["vendored"]]
    assert sorted(vendored) == sorted(json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["skills"])


def test_should_leave_general_skills_outside_every_group():
    mod = _load()
    custom = set(json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))["custom_skills"])
    grouped = {name for group in mod.GROUPS.values() for name in group["custom"]}
    assert grouped <= custom
    assert custom - grouped == GENERAL


def test_should_propose_only_known_groups_for_every_stack():
    mod = _load()
    set_stack = _load("set_stack_for_skills", ROOT / "scripts" / "set-stack.py")
    for stack, groups in mod.STACK_DEFAULTS.items():
        assert stack in set_stack.STACK_PRESETS
        assert set(groups) <= set(mod.GROUPS)
    assert mod.default_groups("inny") == list(mod.GROUPS)  # unknown stack: everything
    assert mod.default_groups(None) == list(mod.GROUPS)


# ── apply_selection ──────────────────────────────────────────────────────────

def test_should_remove_unchosen_groups_from_disk_and_manifest(project):
    mod, root = project
    manifest = mod.load_manifest()
    removed = mod.apply_selection(manifest, ["php", "review"])
    mod.save_manifest(manifest)
    after = _manifest(root)
    assert "wp-plugin-development" in removed and "prestashop" in removed
    assert "wp-plugin-development" not in after["skills"] and "prestashop" not in after["custom_skills"]
    assert "wp-plugin-development" not in _dirs(root) and "prestashop" not in _dirs(root)
    assert {"laravel-rules", "php-modernization", "symfony", "review", "security"} <= _dirs(root)
    assert after["skill_groups"] == ["php", "review"]
    assert "wp-plugin-development" in after["excluded_skills"] and "laravel-rules" not in after["excluded_skills"]


def test_should_never_touch_general_skills_or_unknown_directories(project):
    mod, root = project
    manifest = mod.load_manifest()
    mod.apply_selection(manifest, [])
    mod.save_manifest(manifest)
    assert GENERAL <= _dirs(root)
    assert "seo" in _dirs(root)
    assert set(_manifest(root)["custom_skills"]) == GENERAL


def test_should_remove_skill_by_its_manifest_directory_not_by_its_name(project):
    # code-review lives in .claude/skills/review, web-quality-skills in .claude/skills/perf
    mod, root = project
    manifest = mod.load_manifest()
    removed = mod.apply_selection(manifest, ["php"])
    assert "code-review" in removed and "web-quality-skills" in removed
    assert "review" not in _dirs(root) and "perf" not in _dirs(root)


def test_should_keep_everything_when_all_groups_are_chosen(project):
    mod, root = project
    before = _dirs(root)
    manifest = mod.load_manifest()
    assert mod.apply_selection(manifest, list(mod.GROUPS)) == []
    assert _dirs(root) == before
    assert manifest["excluded_skills"] == []


def test_should_stop_excluding_a_group_when_it_is_chosen_again(project):
    mod, root = project
    manifest = mod.load_manifest()
    mod.apply_selection(manifest, ["review"])
    mod.apply_selection(manifest, ["review", "wordpress"])
    assert "wp-plugin-development" not in manifest["excluded_skills"]
    assert manifest["skill_groups"] == ["wordpress", "review"]


def test_should_refuse_to_delete_outside_the_skills_directory(project):
    mod, root = project
    (root / "important").mkdir()
    manifest = mod.load_manifest()
    manifest["skills"]["copywriting"]["local_path"] = "important"
    mod.apply_selection(manifest, [])
    assert (root / "important").is_dir()


# ── answers ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("answer, expected", [
    ("", ["php", "review"]), ("w", "ALL"), ("1 4", ["wordpress", "typescript"]),
    ("4,1", ["wordpress", "typescript"]), ("php review", ["php", "review"]), ("8 8", ["review"]),
    ("5", ["design"]), ("9", None), ("0", None), ("cobol", None),
])
def test_should_read_answer_as_proposed_all_numbers_or_names(answer, expected):
    mod = _load()
    result = mod.parse_answer(answer, ["php", "review"])
    assert result == (list(mod.GROUPS) if expected == "ALL" else expected)


# ── interactive choice ───────────────────────────────────────────────────────

def _answers(monkeypatch, *answers):
    replies = list(answers)
    monkeypatch.setattr("builtins.input", lambda prompt: replies.pop(0))


def test_should_propose_groups_for_the_project_stack(project, monkeypatch, capsys):
    mod, root = project
    (root / ".claude" / "hooks").mkdir(parents=True)
    (root / ".claude" / "hooks" / "config.json").write_text(json.dumps({"stack": "laravel"}), encoding="utf-8")
    _answers(monkeypatch, "", "")  # Enter = proposed, Enter = confirm removal
    assert mod.choose_interactively(mod.load_manifest()) == ["php", "design", "ui", "review"]
    assert "laravel" in capsys.readouterr().out


def test_should_propose_everything_when_stack_is_not_set(project, monkeypatch):
    mod, _ = project
    _answers(monkeypatch, "")  # nothing to remove, so no confirmation
    assert mod.choose_interactively(mod.load_manifest()) == list(mod.GROUPS)


def test_should_name_what_will_be_removed_and_change_nothing_when_user_declines(project, monkeypatch, capsys):
    mod, root = project
    before = _dirs(root)
    _answers(monkeypatch, "8", "n")
    assert mod.choose_interactively(mod.load_manifest()) is None
    out = capsys.readouterr().out
    assert "wp-plugin-development" in out and "Usunę z projektu" in out
    assert _dirs(root) == before


def test_should_ask_again_when_answer_is_not_understood(project, monkeypatch):
    mod, _ = project
    _answers(monkeypatch, "cobol", "w")
    assert mod.choose_interactively(mod.load_manifest()) == list(mod.GROUPS)


def test_should_show_current_choice_when_run_again(project, monkeypatch):
    mod, root = project
    manifest = mod.load_manifest()
    mod.apply_selection(manifest, ["review"])
    _answers(monkeypatch, "")
    assert mod.choose_interactively(manifest) == ["review"]


# ── command line ─────────────────────────────────────────────────────────────

def _cli(root: Path, *args: str):
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    for name in ("select-skills.py", "start_ui.py"):
        (scripts / name).write_text((ROOT / "scripts" / name).read_text(encoding="utf-8"), encoding="utf-8")
    return subprocess.run([sys.executable, str(scripts / "select-skills.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)


def test_should_apply_keep_flag_from_the_command_line(project):
    _, root = project
    result = _cli(root, "--keep", "php,review")
    assert result.returncode == 0, result.stderr
    assert _manifest(root)["skill_groups"] == ["php", "review"]
    assert "wp-plugin-development" not in _dirs(root)


def test_should_change_nothing_without_a_terminal_and_without_flags(project):
    _, root = project
    before = (root / "skills-manifest.json").read_text(encoding="utf-8")
    result = _cli(root)
    assert result.returncode == 0
    assert "--keep" in result.stdout
    assert (root / "skills-manifest.json").read_text(encoding="utf-8") == before


def test_should_reject_unknown_group_and_change_nothing(project):
    _, root = project
    before = _dirs(root)
    assert _cli(root, "--keep", "php,cobol").returncode != 0
    assert _dirs(root) == before


def test_should_list_groups_without_writing(project):
    _, root = project
    before = (root / "skills-manifest.json").read_text(encoding="utf-8")
    result = _cli(root, "--list")
    assert result.returncode == 0 and "WordPress" in result.stdout
    assert (root / "skills-manifest.json").read_text(encoding="utf-8") == before


# ── sync must not bring excluded skills back ─────────────────────────────────

def test_should_not_resync_excluded_skills_in_update_skills(tmp_path, monkeypatch, capsys):
    updater = _load("update_skills_for_exclusion", ROOT / "scripts" / "update-skills.py")
    template = tmp_path / "template"
    project_root = tmp_path / "project"
    for name in ("prestashop", "adr"):
        (template / ".claude" / "skills" / name).mkdir(parents=True)
        (template / ".claude" / "skills" / name / "SKILL.md").write_text("# skill", encoding="utf-8")
    (template / "skills-manifest.json").write_text(json.dumps({
        "custom_skills": {"prestashop": {}, "adr": {}},
        "skills": {"wp-plugin-development": {"repo": "x", "local_path": ".claude/skills/wp-plugin-development",
                                             "remote_path": "."},
                   "security": {"repo": "x", "local_path": ".claude/skills/security", "remote_path": "."}},
    }), encoding="utf-8")
    project_root.mkdir()
    manifest_path = project_root / "skills-manifest.json"
    manifest_path.write_text(json.dumps({
        "custom_skills": {}, "skills": {}, "excluded_skills": ["prestashop", "wp-plugin-development"],
    }), encoding="utf-8")
    monkeypatch.setattr(updater, "ROOT", project_root)
    monkeypatch.setattr(updater, "MANIFEST_PATH", manifest_path)
    updater.sync_from_template(template, apply=True)
    after = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "adr" in after["custom_skills"] and "prestashop" not in after["custom_skills"]
    assert "security" in after["skills"] and "wp-plugin-development" not in after["skills"]
    assert not (project_root / ".claude" / "skills" / "prestashop").exists()
    assert (project_root / ".claude" / "skills" / "adr").exists()
    assert after["excluded_skills"] == ["prestashop", "wp-plugin-development"]
