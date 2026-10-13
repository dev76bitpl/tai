"""Tests for scripts/set-stack.py — the stack decided in the scope interview configures the guards.

Nobody is asked where the code lives and nobody edits the config by hand: one stack name sets
the code directories for guard-tests-with-src and switches on that platform's ADR patterns.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "set-stack.py"
REAL_EXAMPLE = ROOT / ".claude" / "hooks" / "config.json.example"
SKILL = ROOT / ".claude" / "skills" / "new-project-scope" / "SKILL.md"


def _load():
    spec = importlib.util.spec_from_file_location("set_stack", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def _example() -> dict:
    return json.loads(REAL_EXAMPLE.read_text(encoding="utf-8"))


def _descriptions(config: dict) -> list[str]:
    return [description for _, description in config["adr_patterns"]]


# ── apply_stack ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("stack, dirs", [
    ("node", ["src"]), ("laravel", ["app"]), ("symfony", ["src"]),
    ("wordpress", ["wp-content/themes", "wp-content/plugins"]),
    ("prestashop", ["modules", "override"]), ("magento", ["app/code"]),
    ("python", ["src"]), ("go", ["cmd", "internal", "pkg"]), ("rails", ["app", "lib"]),
    ("inny", ["src"]),
])
def test_should_set_code_directories_for_the_stack(stack, dirs):
    assert mod.apply_stack(_example(), stack)["src_dirs"] == dirs


def test_should_have_a_case_above_for_every_preset():
    assert set(mod.STACK_PRESETS) == {
        "node", "laravel", "symfony", "wordpress", "prestashop", "magento", "python", "go", "rails", "inny",
    }


@pytest.mark.parametrize("stack, label", [
    ("wordpress", "nowy plugin WordPress"),
    ("prestashop", "nowy moduł PrestaShop"),
    ("magento", "nowy moduł Magento"),
])
def test_should_switch_on_adr_patterns_of_the_chosen_platform_only(stack, label):
    config = mod.apply_stack(_example(), stack)
    active = " ".join(_descriptions(config))
    assert label in active
    others = {"WordPress", "PrestaShop", "Magento"} - {mod.STACK_PRESETS[stack]["adr_group"]}
    assert not any(other in active for other in others)


@pytest.mark.parametrize("stack", ["node", "laravel", "symfony", "python", "go", "rails", "inny"])
def test_should_leave_platform_adr_patterns_off_for_other_stacks(stack):
    active = " ".join(_descriptions(mod.apply_stack(_example(), stack)))
    assert "PrestaShop" not in active and "WordPress" not in active and "Magento" not in active


def test_should_keep_generic_and_project_own_patterns(stack="prestashop"):
    config = _example()
    config["adr_patterns"].append(["billing/", "billing rules change"])
    descriptions = _descriptions(mod.apply_stack(config, stack))
    assert "billing rules change" in descriptions
    assert "migracja bazy danych — zmiana schematu" in descriptions


def test_should_switch_previous_platform_off_when_stack_changes():
    config = mod.apply_stack(_example(), "prestashop")
    config = mod.apply_stack(config, "laravel")
    assert "PrestaShop" not in " ".join(_descriptions(config))
    assert config["src_dirs"] == ["app"]


def test_should_give_the_same_result_when_run_twice():
    once = mod.apply_stack(_example(), "wordpress")
    twice = mod.apply_stack(json.loads(json.dumps(once)), "wordpress")
    assert once == twice


def test_should_keep_the_catalogue_of_platform_groups_intact():
    config = mod.apply_stack(_example(), "magento")
    assert config["_adr_patterns_optional"] == _example()["_adr_patterns_optional"]


def test_should_name_only_adr_groups_that_exist_in_the_example():
    groups = {preset["adr_group"] for preset in mod.STACK_PRESETS.values()} - {None}
    assert groups == set(_example()["_adr_patterns_optional"])


def test_should_set_directories_when_config_has_no_platform_catalogue():
    assert mod.apply_stack({"lint": "x"}, "laravel") == {"lint": "x", "src_dirs": ["app"]}


# ── command line: what the scope wizard runs ─────────────────────────────────

@pytest.fixture()
def project(tmp_path):
    """A project directory with its own copy of the script and a config.json from the example."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "set-stack.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "config.json").write_text(REAL_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _run(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(project / "scripts" / "set-stack.py"), *args],
                          capture_output=True, text=True, encoding="utf-8")


def _config(project: Path) -> dict:
    return json.loads((project / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8"))


def test_should_write_stack_into_project_config(project):
    result = _run(project, "prestashop")
    assert result.returncode == 0, result.stderr
    assert "modules, override" in result.stdout and "PrestaShop" in result.stdout
    config = _config(project)
    assert config["src_dirs"] == ["modules", "override"]
    assert "nowy moduł PrestaShop" in _descriptions(config)


def test_should_list_every_stack_without_writing(project):
    before = (project / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8")
    result = _run(project, "--list")
    assert result.returncode == 0
    for name in mod.STACK_PRESETS:
        assert name in result.stdout
    assert (project / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8") == before


def test_should_refuse_unknown_stack_and_change_nothing(project):
    before = (project / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8")
    result = _run(project, "cobol")
    assert result.returncode != 0
    assert (project / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8") == before


def test_should_fail_with_a_hint_when_config_is_missing(project):
    (project / ".claude" / "hooks" / "config.json").unlink()
    result = _run(project, "laravel")
    assert result.returncode == 1
    assert "config.json.example" in result.stderr


def test_should_fail_and_keep_the_file_when_config_is_not_json(project):
    path = project / ".claude" / "hooks" / "config.json"
    path.write_text("{ not json", encoding="utf-8")
    result = _run(project, "laravel")
    assert result.returncode == 1
    assert path.read_text(encoding="utf-8") == "{ not json"


# ── the scope wizard knows the same stacks as the script ─────────────────────

def test_should_mention_every_stack_name_in_the_scope_skill():
    skill = SKILL.read_text(encoding="utf-8")
    assert "scripts/set-stack.py" in skill
    for name in mod.STACK_PRESETS:
        assert f"`{name}`" in skill, name


def test_should_run_the_interview_one_question_at_a_time_in_the_scope_skill():
    # the wizard used to send all six questions in one message; it is an instruction for the AI,
    # so this only pins the wording that decides the behaviour
    skill = SKILL.read_text(encoding="utf-8")
    assert "one question at a time" in skill
    assert "AskUserQuestion" in skill
    assert "one message with all questions" not in skill
    assert "Follow-up questions" in skill
