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


# ── the hook compares with the template's origin/main, not its working directory (#179) ──

import subprocess


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main",
                    *args], cwd=cwd, check=True, capture_output=True)


def _clone_with_work_in_progress(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / ".claude" / "skills" / "adr").mkdir(parents=True)
    (source / ".claude" / "skills" / "adr" / "SKILL.md").write_text("released", encoding="utf-8")
    (source / "skills-manifest.json").write_text(json.dumps({"custom_skills": {"adr": {}}, "skills": {}}),
                                                 encoding="utf-8")
    _git(source, "init", "-q")
    _git(source, "add", ".")
    _git(source, "commit", "-qm", "init")
    clone = tmp_path / "template-clone"
    _git(tmp_path, "clone", "-q", str(source), str(clone))
    _git(clone, "switch", "-qc", "feat/work-in-progress")
    (clone / ".claude" / "skills" / "adr" / "SKILL.md").write_text("unfinished", encoding="utf-8")
    return clone


def _record_sync(module, monkeypatch, result=None) -> list:
    """Record only the sync call; git commands of the snapshot run for real."""
    real, ran = module.subprocess.run, []

    def run(args, *rest, **kw):
        if "--sync" in args:
            ran.append(args)
            return result
        return real(args, *rest, **kw)

    monkeypatch.setattr(module.subprocess, "run", run)
    return ran


def _project_with_released_skill(project: Path) -> None:
    (project / ".claude" / "skills" / "adr").mkdir(parents=True)
    (project / ".claude" / "skills" / "adr" / "SKILL.md").write_text("released", encoding="utf-8")
    _project(project, {"custom_skills": {"adr": {}}, "skills": {}})
    (project / "scripts").mkdir()
    updater = Path(__file__).resolve().parents[3] / "scripts" / "update-skills.py"
    (project / "scripts" / "update-skills.py").write_text(updater.read_text(encoding="utf-8"), encoding="utf-8")


def test_should_not_see_work_in_progress_of_the_template_as_a_change(hook, tmp_path, monkeypatch):
    module, project, _ = hook
    clone = _clone_with_work_in_progress(tmp_path)
    _project_with_released_skill(project)
    monkeypatch.setattr(module, "resolve_template_path", lambda config: str(clone))
    ran = _record_sync(module, monkeypatch)
    assert module.check_template_skills_sync({}) is None
    assert ran == []  # nothing to sync: origin/main equals the project


def test_should_sync_when_the_released_template_differs(hook, tmp_path, monkeypatch):
    module, project, _ = hook
    clone = _clone_with_work_in_progress(tmp_path)
    _project_with_released_skill(project)
    (project / ".claude" / "skills" / "adr" / "SKILL.md").write_text("old", encoding="utf-8")

    class Done:
        returncode, stderr = 0, ""

    monkeypatch.setattr(module, "resolve_template_path", lambda config: str(clone))
    ran = _record_sync(module, monkeypatch, Done())
    assert "adr" in module.check_template_skills_sync({})
    assert len(ran) == 1
