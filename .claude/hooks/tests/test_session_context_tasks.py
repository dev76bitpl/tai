"""Tests for extract_open_tasks in .claude/hooks/session-context.py.

docs/TASKS.md in a project is a session log (### date — what happened), not a task list. Only
real tasks may reach the session start: checkboxes, or ### headings that carry a **Status:**.
"""
import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "session-context.py"

spec = importlib.util.spec_from_file_location("session_context_under_test", HOOK)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LOG = """# Tasks — log sesji

## Log sesji

### 2026-11-19 — aktualizacja z tai v0.1.26 (#594)

Dwa przebiegi update-from-template.py.

### 2026-11-18 — Grafik na telefonie (#578)

Poprawka wyboru dnia.
"""


def test_should_not_turn_session_log_headings_into_tasks():
    assert mod.extract_open_tasks(LOG) == ""


def test_should_still_list_headings_with_an_open_status():
    content = "## Backlog\n\n### Login page\n**Status:** In progress\n\n### Old thing\n**Status:** Done\n"
    out = mod.extract_open_tasks(content)
    assert "- [ ] Login page (In progress)" in out
    assert "Old thing" not in out


def test_should_prefer_checkboxes_when_present():
    content = LOG + "\n## Open\n\n- [ ] real task\n"
    out = mod.extract_open_tasks(content)
    assert "- [ ] real task" in out
    assert "2026-11-19" not in out
