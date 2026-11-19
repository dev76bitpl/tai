"""Tests for scripts/update-from-template.py — pulling template fixes into a project (ADR-006).

Each case builds a throwaway template repo with history (origin/main set by update-ref) and a
project directory holding copies of its files in various states.
"""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "update-from-template.py"

spec = importlib.util.spec_from_file_location("update_from_template", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LIST = {
    "copy": ["scripts/*.py", "docs/GUARDS.md"],
    "exclude": ["scripts/new-project.py"],
    "compare_sections": ["CLAUDE.md"],
}
CLAUDE_V1 = "# Rules\n\n## One\n\nfirst\n\n## Two\n\nsecond\n"
CLAUDE_V2 = "# Rules\n\n## One\n\nfirst, changed\n\n## Two\n\nsecond\n\n## Three\n\nthird\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _commit(repo: Path, files: dict, message: str) -> None:
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)


@pytest.fixture()
def template(tmp_path):
    repo = tmp_path / "template"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {
        "template-files.json": json.dumps(LIST),
        "scripts/guard.py": "v1\n",
        "scripts/same.py": "same\n",
        "scripts/mine.py": "template\n",
        "scripts/new-project.py": "template only\n",
        "CLAUDE.md": CLAUDE_V1,
    }, "v1")
    _commit(repo, {"scripts/guard.py": "v2\n", "scripts/added.py": "added\n", "CLAUDE.md": CLAUDE_V2}, "v2")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    # Unreleased work in the template's working directory must never reach a project (#179).
    (repo / "scripts" / "guard.py").write_text("unreleased\n", encoding="utf-8")
    (repo / "scripts" / "wip.py").write_text("wip\n", encoding="utf-8")
    return repo


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "project"
    for path, text in {
        "scripts/guard.py": "v1\n",
        "scripts/same.py": "same\n",
        "scripts/mine.py": "edited in the project\n",
        "CLAUDE.md": CLAUDE_V1 + "\n## Project rule\n\nours\n",
    }.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_should_classify_each_template_file_against_the_released_main(template, project):
    report = mod.compare(template, "origin/main", project)
    assert report.files == {
        "scripts/added.py": mod.NEW,
        "scripts/guard.py": mod.OUTDATED,
        "scripts/mine.py": mod.LOCAL,
        "scripts/same.py": mod.CURRENT,
    }


def test_should_not_call_a_crlf_checkout_a_local_change(template, project):
    (project / "scripts" / "same.py").write_bytes(b"same\r\n")
    (project / "scripts" / "guard.py").write_bytes(b"v1\r\n")
    files = mod.compare(template, "origin/main", project).files
    assert files["scripts/same.py"] == mod.CURRENT
    assert files["scripts/guard.py"] == mod.OUTDATED


def test_should_ignore_template_working_directory_and_excluded_files(template, project):
    files = mod.compare(template, "origin/main", project).files
    assert "scripts/wip.py" not in files
    assert "scripts/new-project.py" not in files


def test_should_copy_only_outdated_and_new_files_when_applying(template, project):
    report = mod.compare(template, "origin/main", project)
    copied = mod.apply(template, "origin/main", project, report)
    assert sorted(copied) == ["scripts/added.py", "scripts/guard.py"]
    assert (project / "scripts" / "guard.py").read_text(encoding="utf-8") == "v2\n"
    assert (project / "scripts" / "mine.py").read_text(encoding="utf-8") == "edited in the project\n"
    assert mod.compare(template, "origin/main", project).pending() == ["scripts/mine.py"]


def test_should_not_change_anything_without_apply(template, project, monkeypatch, capsys):
    monkeypatch.setattr(mod, "ROOT", project)
    monkeypatch.setattr(mod, "resolve_source", lambda root: (template, "origin/main", None, ""))
    monkeypatch.setattr("sys.argv", ["update-from-template.py"])
    assert mod.main() == 0
    assert (project / "scripts" / "guard.py").read_text(encoding="utf-8") == "v1\n"
    out = capsys.readouterr().out
    assert "scripts/guard.py" in out and "--apply" in out


def test_should_report_new_and_changed_claude_md_sections_without_touching_the_file(template, project):
    report = mod.compare(template, "origin/main", project)
    assert report.sections == [
        "CLAUDE.md: ## One  (inna niż w szablonie)",
        "CLAUDE.md: ## Three  (nowa w szablonie)",
    ]
    mod.apply(template, "origin/main", project, report)
    assert "## Project rule" in (project / "CLAUDE.md").read_text(encoding="utf-8")


def test_should_fail_clearly_when_template_has_no_file_list(tmp_path, project):
    repo = tmp_path / "old-template"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {"scripts/guard.py": "v1\n"}, "old")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    report = mod.compare(repo, "origin/main", project)
    assert "template-files.json" in report.error


@pytest.mark.parametrize("path,pattern,expected", [
    ("scripts/a.py", "scripts/*.py", True),
    ("scripts/dev-guards/a.py", "scripts/*.py", False),
    ("docs/examples/README.md", "docs/examples/*", True),
])
def test_should_keep_star_inside_one_directory(path, pattern, expected):
    assert mod.matches(path, pattern) is expected


def test_should_list_only_files_that_exist_in_the_template():
    """Every pattern in the real template-files.json must match at least one tracked file."""
    spec = json.loads((ROOT / "template-files.json").read_text(encoding="utf-8"))
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for pattern in spec["copy"] + spec["compare_sections"]:
        assert any(mod.matches(p, pattern) for p in tracked), pattern


def test_should_never_ship_template_only_scripts():
    spec = json.loads((ROOT / "template-files.json").read_text(encoding="utf-8"))
    data = importlib.util.spec_from_file_location("npd", ROOT / "scripts" / "new_project_data.py")
    npd = importlib.util.module_from_spec(data)
    data.loader.exec_module(npd)
    for name in npd.TEMPLATE_ONLY_SCRIPTS:
        path = f"scripts/{name}"
        assert not (
            any(mod.matches(path, p) for p in spec["copy"])
            and not any(mod.matches(path, p) for p in spec["exclude"])
        ), path


# ── session-start notice (ADR-006, decisions 7–8) ──

def _switch(template: Path, on: bool) -> None:
    # Only the config is committed: the fixture's unreleased work must stay out of the release.
    config = template / ".claude" / "hooks" / "config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"template_update_check": on}), encoding="utf-8")
    _git(template, "add", str(config))
    _git(template, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "switch")
    _git(template, "update-ref", "refs/remotes/origin/main", "HEAD")


def test_should_stay_quiet_when_the_template_switch_is_off(template, project):
    _switch(template, False)
    assert mod.session_notice(project, str(template), "2026-10-14") is None


def test_should_say_in_one_line_what_waits_when_the_switch_is_on(template, project):
    _switch(template, True)
    notice = mod.session_notice(project, str(template), "2026-10-14")
    assert notice.count("\n") == 0
    assert "2 plik(ów) do skopiowania" in notice and "1 zmienionych lokalnie" in notice
    assert "python3 scripts/update-from-template.py" in notice
    assert (project / "scripts" / "guard.py").read_text(encoding="utf-8") == "v1\n"  # never copies


def test_should_fetch_the_template_at_most_once_a_day(template, project, monkeypatch):
    _switch(template, True)
    fetches = []
    real_run = mod.subprocess.run

    def spy(cmd, *args, **kwargs):
        if "fetch" in cmd:
            fetches.append(cmd)
            return mod.subprocess.CompletedProcess(cmd, 0, b"", b"")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(mod.subprocess, "run", spy)
    mod.session_notice(project, str(template), "2026-10-14")
    mod.session_notice(project, str(template), "2026-10-14")
    mod.session_notice(project, str(template), "2026-10-15")
    assert len(fetches) == 2


def test_should_stay_quiet_without_a_local_template_clone(project):
    assert mod.session_notice(project, "git@github.com:org/tai.git", "2026-10-14") is None
    assert mod.session_notice(project, "", "2026-10-14") is None


# ── the preview names lint/test commands the released guards will block on (#201) ──

STACK_STUB = '''
import shutil
from pathlib import Path
import json
REPO_ROOT = Path(".")
CONFIG_PATH = REPO_ROOT / "config.json"
LOCAL_CONFIG_PATH = CONFIG_PATH
def get_project_root():
    return REPO_ROOT
def get_cmd(kind):
    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.is_file() else {}
    return (config[kind].split(), True) if kind in config else (["npm", "test"], False)
def why_unavailable(cmd):
    return "" if shutil.which(cmd[0]) else f"`{cmd[0]}` is not installed"
'''


def _config(project: Path, data: dict) -> None:
    path = project / ".claude" / "hooks" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_should_name_a_configured_command_that_will_block_every_commit(template, project):
    _commit(template, {mod.GUARD_STACK: STACK_STUB}, "guards")
    _git(template, "update-ref", "refs/remotes/origin/main", "HEAD")
    _config(project, {"lint": "no-such-tool-201 lint", "test": "git --version"})
    found = mod.blocking_guard_commands(template, "origin/main", project)
    assert found == ["„lint”: no-such-tool-201 lint — `no-such-tool-201` is not installed"]


def test_should_say_nothing_about_guards_when_the_release_has_no_guard_helpers(template, project):
    _config(project, {"lint": "no-such-tool-201 lint"})
    assert mod.blocking_guard_commands(template, "origin/main", project) == []


def test_should_check_the_real_released_guards_against_an_inherited_composer_lint(tmp_path):
    """The real stack.py from this repo, as the preview loads it: composer lint without composer.json."""
    project = tmp_path / "project"
    _config(project, {"lint": "composer lint", "test": "git --version"})
    repo = tmp_path / "template"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {mod.GUARD_STACK: (ROOT / mod.GUARD_STACK).read_text(encoding="utf-8")}, "guards")
    found = mod.blocking_guard_commands(repo, "HEAD", project)
    assert len(found) == 1 and found[0].startswith("„lint”: composer lint — ")


# #271: an --apply that replaced this very script must run the steps after copying from the
# fresh copy — the old code still running does not know steps added in the new version.
def test_should_run_the_steps_after_copying_from_the_fresh_copy_when_the_script_was_replaced(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "update-from-template.py").write_text("", encoding="utf-8")
    calls, steps = [], []
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(mod, "after_apply", lambda project, *a: steps.append(project))
    mod.run_after_apply(tmp_path, ["scripts/update-from-template.py", "scripts/claude_settings.py"])
    assert calls == [[mod.sys.executable, str(tmp_path / "scripts" / "update-from-template.py"), "--after-apply"]]
    assert steps == []


def test_should_run_the_steps_itself_when_the_script_was_not_replaced(tmp_path, monkeypatch):
    calls, steps = [], []
    monkeypatch.setattr(mod.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(mod, "after_apply", lambda project, *a: steps.append(project))
    mod.run_after_apply(tmp_path, ["scripts/claude_settings.py"])
    assert calls == [] and steps == [tmp_path]


def test_should_wire_the_hooks_with_after_apply_alone(tmp_path):
    """The fresh copy, started with --after-apply, wires the hooks without comparing anything."""
    import shutil
    import sys
    for rel in ("scripts/update-from-template.py", "scripts/claude_settings.py", ".claude/settings.local.json.example",
                ".claude/hooks/session-context.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    target = tmp_path / ".claude" / "settings.local.json"
    target.write_text('{"hooks": {}}', encoding="utf-8")
    done = subprocess.run([sys.executable, str(tmp_path / "scripts" / "update-from-template.py"), "--after-apply"],
                          cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "session-context.py" in target.read_text(encoding="utf-8")


# #282: after --apply the hooks come also from the TEMPLATE's example, not only the project's —
# a project that changed its own example (skolaro) keeps it, and a new hook was never wired.
def test_should_wire_a_new_template_hook_into_a_project_with_its_own_example(tmp_path):
    import json as _json
    import shutil
    own = {"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell", "hooks": [
        {"type": "command", "command": "INTERPRETER ${CLAUDE_PROJECT_DIR}/.claude/hooks/guard-process-kill.py"}]}]}}
    repo = tmp_path / "template"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {mod.SETTINGS_EXAMPLE: (ROOT / mod.SETTINGS_EXAMPLE).read_text(encoding="utf-8")}, "example")
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "claude_settings.py", project / "scripts" / "claude_settings.py")
    (project / ".claude" / "hooks").mkdir(parents=True)
    for name in ("guard-process-kill.py", "guard-pr-merge.py"):
        (project / ".claude" / "hooks" / name).write_text("", encoding="utf-8")
    (project / mod.SETTINGS_EXAMPLE).write_text(_json.dumps(own), encoding="utf-8")
    target = project / ".claude" / "settings.local.json"
    target.write_text(_json.dumps(own).replace("INTERPRETER", "python3"), encoding="utf-8")

    mod.after_apply(project, repo, "HEAD")

    assert "guard-pr-merge.py" in target.read_text(encoding="utf-8")
    assert _json.loads((project / mod.SETTINGS_EXAMPLE).read_text(encoding="utf-8")) == own


# Deliberate local differences (tai#286): accepted once with a reason, quiet until the template moves.

def _accept(template: Path, project: Path, path: str, reason: str) -> str:
    report = mod.compare(template, "origin/main", project)
    return mod.accept(project, report, path, reason, "2026-11-19")


def test_should_stop_reporting_a_local_file_accepted_with_a_reason(template, project):
    assert _accept(template, project, "scripts/mine.py", "own guard kept on purpose") == ""
    report = mod.compare(template, "origin/main", project)
    assert report.files["scripts/mine.py"] == mod.ACCEPTED
    assert report.accepted == {"scripts/mine.py": "own guard kept on purpose"}
    assert "scripts/mine.py" not in report.pending()


def test_should_keep_the_session_notice_quiet_about_accepted_files(template, project):
    _switch(template, True)
    before = mod.session_notice(project, str(template), "2026-11-19")
    assert "zmienionych lokalnie" in before
    assert _accept(template, project, "scripts/mine.py", "own guard kept on purpose") == ""
    after = mod.session_notice(project, str(template), "2026-11-19") or ""
    assert "zmienionych lokalnie" not in after


def test_should_compare_an_accepted_file_again_once_the_template_changes_it(template, project):
    assert _accept(template, project, "scripts/mine.py", "own guard kept on purpose") == ""
    _commit(template, {"scripts/mine.py": "template v2\n"}, "v3")
    _git(template, "update-ref", "refs/remotes/origin/main", "HEAD")
    report = mod.compare(template, "origin/main", project)
    assert report.files["scripts/mine.py"] == mod.LOCAL
    assert report.expired == {"scripts/mine.py": "2026-11-19"}


@pytest.mark.parametrize("reason", ["", "ours", "two words"])
def test_should_refuse_to_accept_without_a_real_reason(template, project, reason):
    assert "powód" in _accept(template, project, "scripts/mine.py", reason)
    assert not (project / mod.ACCEPTED_FILE).exists()


@pytest.mark.parametrize("path", ["scripts/same.py", "scripts/guard.py", "scripts/unknown.py"])
def test_should_accept_only_a_file_changed_locally(template, project, path):
    assert _accept(template, project, path, "own guard kept on purpose") != ""
    assert not (project / mod.ACCEPTED_FILE).exists()


def test_should_never_put_the_accepted_list_on_the_template_file_list():
    spec = json.loads((ROOT / "template-files.json").read_text(encoding="utf-8"))
    assert not any(mod.matches(mod.ACCEPTED_FILE, pattern) for pattern in spec["copy"])


def test_should_show_accepted_files_with_their_reason_in_the_preview(template, project, capsys):
    _accept(template, project, "scripts/mine.py", "own guard kept on purpose")
    mod.print_report(mod.compare(template, "origin/main", project), None)
    out = capsys.readouterr().out
    assert "celowo inne" in out
    assert "scripts/mine.py — own guard kept on purpose" in out
    assert "zmieniony lokalnie" not in out


# Deliberately different CLAUDE.md sections (tai#292): the same rule as files, keyed by header.

def _accept_section(template: Path, project: Path, header: str, reason: str) -> str:
    report = mod.compare(template, "origin/main", project)
    return mod.accept_section(project, report, header, reason, "2026-11-19")


def test_should_stop_reporting_a_section_accepted_with_a_reason(template, project):
    assert _accept_section(template, project, "## One", "project keeps its own wording") == ""
    report = mod.compare(template, "origin/main", project)
    assert report.accepted_sections == {"CLAUDE.md: ## One": "project keeps its own wording"}
    assert not any("## One" in line for line in report.sections)
    assert any("## Three" in line for line in report.sections)


def test_should_accept_a_section_given_with_its_file_name(template, project):
    assert _accept_section(template, project, "CLAUDE.md: ## Three", "not used in this project") == ""
    report = mod.compare(template, "origin/main", project)
    assert "CLAUDE.md: ## Three" in report.accepted_sections


def test_should_keep_the_session_notice_quiet_about_accepted_sections(template, project):
    _switch(template, True)
    assert "2 sekcji CLAUDE.md" in mod.session_notice(project, str(template), "2026-11-19")
    _accept_section(template, project, "## One", "project keeps its own wording")
    _accept_section(template, project, "## Three", "not used in this project")
    assert "sekcji CLAUDE.md" not in (mod.session_notice(project, str(template), "2026-11-19") or "")


def test_should_compare_an_accepted_section_again_once_the_template_changes_it(template, project):
    _accept_section(template, project, "## One", "project keeps its own wording")
    _commit(template, {"CLAUDE.md": CLAUDE_V2.replace("first, changed", "first, changed again")}, "v3")
    _git(template, "update-ref", "refs/remotes/origin/main", "HEAD")
    report = mod.compare(template, "origin/main", project)
    assert report.expired_sections == {"CLAUDE.md: ## One": "2026-11-19"}
    assert any("## One" in line and "przyjęta 2026-11-19" in line for line in report.sections)


def test_should_refuse_a_section_that_is_not_different_or_a_short_reason(template, project):
    assert "nie jest sekcją" in _accept_section(template, project, "## Two", "same as the template")
    assert "powód" in _accept_section(template, project, "## One", "ours")
    assert not (project / mod.ACCEPTED_FILE).exists()


def test_should_keep_accepted_files_and_sections_side_by_side(template, project):
    assert _accept(template, project, "scripts/mine.py", "own guard kept on purpose") == ""
    assert _accept_section(template, project, "## One", "project keeps its own wording") == ""
    assert _accept(template, project, "scripts/mine.py", "own guard kept, reworded reason") == ""
    report = mod.compare(template, "origin/main", project)
    assert report.files["scripts/mine.py"] == mod.ACCEPTED
    assert "CLAUDE.md: ## One" in report.accepted_sections


def test_should_show_accepted_sections_with_their_reason_in_the_preview(template, project, capsys):
    _accept_section(template, project, "## One", "project keeps its own wording")
    mod.print_report(mod.compare(template, "origin/main", project), None)
    out = capsys.readouterr().out
    assert "CLAUDE.md: ## One — project keeps its own wording" in out
    assert "--accept-section" in out  # ## Three still waits, so the hint shows
