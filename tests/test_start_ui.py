"""Tests for scripts/start_ui.py — the shared look of new-project.py and project-setup.py."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "start_ui.py"


def _load():
    spec = importlib.util.spec_from_file_location("start_ui_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def ui():
    return _load()


def test_should_colour_marks_when_colour_is_on(ui, monkeypatch):
    monkeypatch.setattr(ui, "_USE_COLOR", True)
    assert ui.mark(ui.DONE) == "\033[32;1m✓\033[0m"
    assert ui.mark(ui.FAILED) == "\033[31;1m✗\033[0m"
    assert "\033[" in ui.progress(2, 6)


def test_should_leave_text_untouched_when_colour_is_off(ui, monkeypatch):
    monkeypatch.setattr(ui, "_USE_COLOR", False)
    assert ui.mark(ui.DONE) == "✓"
    assert ui.progress(2, 6) == "▰▰▱▱▱▱"
    assert ui.paint("tekst", ui.BOLD) == "tekst"
    assert ui.question_line("Repo:", "[Enter = pomiń]") == "  ? Repo: [Enter = pomiń] "


@pytest.mark.parametrize("env, expected", [({"NO_COLOR": "1"}, False), ({"FORCE_COLOR": "1"}, True), ({}, True)])
def test_should_follow_no_color_and_force_color_on_a_terminal(monkeypatch, env, expected):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True, raising=False)
    assert _load()._USE_COLOR is expected


def test_should_stay_plain_when_output_is_not_a_terminal(monkeypatch):
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: False, raising=False)
    assert _load()._USE_COLOR is False


def test_should_mark_work_done_and_work_only_planned_differently(ui, monkeypatch, capsys):
    monkeypatch.setattr(ui, "_USE_COLOR", False)
    ui.item("rm", "README.md")
    ui.item("rm", "README.md", planned=True)
    done, planned = capsys.readouterr().out.splitlines()
    assert done.strip().startswith(ui.DONE) and planned.strip().startswith(ui.PLANNED)
    assert "README.md" in done and "README.md" in planned


def test_should_stay_in_the_project_after_init():
    # project-setup.py imports it, and that script outlives new-project.py
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from new_project_data import TEMPLATE_ONLY_SCRIPTS
    assert "start_ui.py" not in TEMPLATE_ONLY_SCRIPTS
