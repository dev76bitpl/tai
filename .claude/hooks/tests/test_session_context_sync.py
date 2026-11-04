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
# The skill checks live in skills_check.py since the split (#221); session-context.py calls them.
SKILLS_CHECK = Path(__file__).resolve().parents[1] / "skills_check.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def hook(tmp_path, monkeypatch):
    module = _load(SKILLS_CHECK, "skills_check_under_test")
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
    (project / ".claude" / "skills" / "security").mkdir()
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
        returncode, stdout, stderr = 0, "", ""

    monkeypatch.setattr(module, "resolve_template_path", lambda config: str(clone))
    ran = _record_sync(module, monkeypatch, Done())
    assert "adr" in module.check_template_skills_sync({})
    assert len(ran) == 1


# ── the template notice must reach the screen, not only the model (ADR-006, decision 7) ──

def test_should_show_template_notice_on_screen_and_keep_it_in_context():
    module = _load(HOOK, "session_context_under_test")
    out = json.loads(module.render("[SESSION START]\n\nnotice", "notice"))
    assert out["systemMessage"] == "notice"
    assert out["hookSpecificOutput"] == {"hookEventName": "UserPromptSubmit", "additionalContext": "[SESSION START]\n\nnotice"}


def test_should_keep_plain_context_when_nothing_must_be_shown():
    module = _load(HOOK, "session_context_under_test")
    assert module.render("[SESSION START]\n\ntasks", None) == "[SESSION START]\n\ntasks"


# ── a skill the sync left alone because the project changed it is not "downloaded" (#201) ──

class _Done:
    def __init__(self, stdout: str):
        self.returncode, self.stdout, self.stderr = 0, stdout, ""


def test_should_read_skipped_skills_from_the_sync_output(hook):
    module, _, _ = hook
    out = f"...\n   {module.LOCAL_SKILLS_LINE} adr, git\n"
    assert module._skipped_local(out) == ["adr", "git"]
    assert module._skipped_local("nothing here") == []


def test_should_report_a_locally_changed_skill_instead_of_a_download(hook, monkeypatch):
    module, project, template = hook
    _template(template)
    (project / "scripts").mkdir()
    (project / "scripts" / "update-skills.py").write_text("# not run: subprocess is replaced", encoding="utf-8")
    for name in ("adr", "prestashop"):
        (project / ".claude" / "skills" / name).mkdir(parents=True)
        (project / ".claude" / "skills" / name / "SKILL.md").write_text("# ours", encoding="utf-8")
    for name in ("security", "wp-plugin-development"):
        (project / ".claude" / "skills" / name).mkdir(parents=True)
    _project(project, {"custom_skills": {"adr": {}, "prestashop": {}}, "skills": {"security": {}, "wp-plugin-development": {}}})
    monkeypatch.setattr(module, "resolve_template_path", lambda config: str(template))
    monkeypatch.setattr(module.subprocess, "run",
                        lambda *a, **k: _Done(f"   {module.LOCAL_SKILLS_LINE} adr, prestashop\n"))
    message = module.check_template_skills_sync({})
    assert "Pobrano" not in message
    assert "adr, prestashop" in message and "porównaj ręcznie" in message


# ── vendored skills follow the template's version, not only its manifest names (#221) ──

ENTRY = {"local_path": ".claude/skills/review", "commit": "c2", "checked": "2000-01-01"}


@pytest.mark.parametrize("project_skills,has_dir,expected", [
    ({"code-review": ENTRY}, True, []),
    ({"code-review": dict(ENTRY, commit="c1")}, True, ["code-review"]),   # template reviewed a newer one
    ({}, False, ["code-review"]),                                          # never synced
    ({"code-review": ENTRY}, False, ["code-review"]),                     # entry without files
])
def test_should_list_vendored_skills_waiting_for_sync(hook, project_skills, has_dir, expected):
    module, project, template = hook
    template.mkdir()
    (template / "skills-manifest.json").write_text(json.dumps({"custom_skills": {}, "skills": {"code-review": ENTRY}}),
                                                   encoding="utf-8")
    _project(project, {"custom_skills": {}, "skills": project_skills})
    if has_dir:
        (project / ".claude" / "skills" / "review").mkdir(parents=True)
    assert module._local_desynced(template)[2] == expected


@pytest.mark.parametrize("config,warns", [({}, False), ({"is_template": True}, True)])
def test_should_ask_to_check_upstream_only_in_the_template(hook, config, warns):
    module, project, _ = hook
    _project(project, {"custom_skills": {}, "skills": {"code-review": ENTRY}})
    warning = module.check_skills_staleness(config) or ""
    assert ("Vendored" in warning) is warns


def test_should_name_skills_the_template_retired(hook):
    module, project, template = hook
    _template(template)
    _project(project, {"custom_skills": {"adr": {}, "old-custom": {}}, "skills": {"security": {}, "redesign": {}}})
    assert module._retired(template) == ["old-custom", "redesign"]


def test_should_sync_and_report_a_retired_skill(hook, monkeypatch):
    module, project, template = hook
    _template(template)
    (project / "scripts").mkdir()
    (project / "scripts" / "update-skills.py").write_text("# not run: subprocess is replaced", encoding="utf-8")
    for name in ("adr", "prestashop", "security", "wp-plugin-development"):
        (project / ".claude" / "skills" / name).mkdir(parents=True)
        (project / ".claude" / "skills" / name / "SKILL.md").write_text("# skill", encoding="utf-8")
    _project(project, {"custom_skills": {"adr": {}, "prestashop": {}},
                       "skills": {"security": {}, "wp-plugin-development": {}, "redesign": {}}})
    monkeypatch.setattr(module, "resolve_template_path", lambda config: str(template))
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: _Done(""))
    assert "usunięte (wycofane w szablonie): redesign" in module.check_template_skills_sync({})


def test_should_run_without_the_skill_checks_module(tmp_path, monkeypatch):
    """A partial update that brings session-context.py without skills_check.py must not break prompts."""
    import shutil
    import sys
    monkeypatch.delitem(sys.modules, "skills_check", raising=False)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if Path(p).resolve() != HOOK.parent])
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    for name in ("session-context.py", "stack.py"):
        shutil.copy2(HOOK.parent / name, hooks / name)
    module = _load(hooks / "session-context.py", "session_context_without_skills_check")
    assert module.skills_check is None
