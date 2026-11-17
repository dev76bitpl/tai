"""The release rule (jarvis D-019, tai#248) lives where it reaches every project: the skills.

CLAUDE.md is only compared section by section and docs/RULES_REFERENCE.md is not shipped at all,
so a rule written only there never arrives (the reason #248 exists). The skills are synced into
every project at session start; these tests keep the rule and its check command in them.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
SEARCH = 'gh pr list --state open --search "chore: release in:title"'


@pytest.mark.parametrize("skill", ["git", "deploy"])
def test_should_carry_the_release_rule_and_its_check(skill):
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "D-019" in text
    assert SEARCH in text
    assert "gh release list --limit 1" in text  # the tag is checked, not assumed


def test_should_say_which_changes_are_worth_a_release():
    text = (SKILLS / "git" / "SKILL.md").read_text(encoding="utf-8")
    assert "kronika zmian" in text and "nie blokada" in text
    assert "`feat`, `fix` i zmiany\n  łamiące" in text or "`feat`, `fix` i zmiany łamiące" in text
    assert "`docs`, `chore`, `test`, `refactor` — nie" in text


def test_should_ship_the_skills_that_carry_it():
    import json
    custom = json.loads((ROOT / "skills-manifest.json").read_text(encoding="utf-8"))["custom_skills"]
    assert {"git", "deploy"} <= set(custom)
