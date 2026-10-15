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
