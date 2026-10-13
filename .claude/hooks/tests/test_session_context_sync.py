"""Tests for the template-sync check in .claude/hooks/session-context.py.

A project may switch skill groups off (scripts/select-skills.py). The hook runs on every prompt
and auto-syncs whatever it finds "missing" — so an excluded skill must not count as missing,
otherwise the choice would be undone by the next message.
"""
import importlib.util
import json
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "session-context.py"


@pytest.fixture()
def hook(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("session_context_under_test", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(module, "MONOREPO_ROOT", project)
    return module, project, tmp_path / "template"


def _template(root: Path) -> None:
    for name in ("adr", "prestashop"):
        (root / ".claude" / "skills" / name).mkdir(parents=True)
        (root / ".claude" / "skills" / name / "SKILL.md").write_text("# skill", encoding="utf-8")
    (root / "skills-manifest.json").write_text(json.dumps({
        "custom_skills": {"adr": {}, "prestashop": {}},
        "skills": {"security": {}, "wp-plugin-development": {}},
    }), encoding="utf-8")


def _project(root: Path, manifest: dict) -> None:
    (root / "skills-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_should_report_skills_missing_when_nothing_is_excluded(hook):
    module, project, template = hook
    _template(template)
    _project(project, {"custom_skills": {}, "skills": {}})
    missing, outdated, missing_vendored = module._local_desynced(template)
    assert sorted(missing) == ["adr", "prestashop"]
    assert missing_vendored == ["security", "wp-plugin-development"]


def test_should_not_report_excluded_skills_as_missing(hook):
    module, project, template = hook
    _template(template)
    _project(project, {"custom_skills": {}, "skills": {}, "excluded_skills": ["prestashop", "wp-plugin-development"]})
    missing, outdated, missing_vendored = module._local_desynced(template)
    assert missing == ["adr"]
    assert missing_vendored == ["security"]


def test_should_see_no_desync_when_only_excluded_skills_are_absent(hook):
    module, project, template = hook
    _template(template)
    (project / ".claude" / "skills" / "adr").mkdir(parents=True)
    (project / ".claude" / "skills" / "adr" / "SKILL.md").write_text("# skill", encoding="utf-8")
    _project(project, {"custom_skills": {"adr": {}}, "skills": {"security": {}},
                       "excluded_skills": ["prestashop", "wp-plugin-development"]})
    assert module._local_desynced(template) == ([], [], [])
