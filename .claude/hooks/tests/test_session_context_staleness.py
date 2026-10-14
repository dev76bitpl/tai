"""Tests for the skills age check in .claude/hooks/session-context.py.

The hook runs on every prompt. The age check used datetime without importing it, so the first
message in every new project ended in a traceback (#141).
"""
import importlib.util
import json
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "session-context.py"


@pytest.fixture()
def hook(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("session_context_staleness", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "MONOREPO_ROOT", tmp_path)
    return module, tmp_path


def _manifest(root: Path, checked: str, reviewed: str) -> None:
    (root / "skills-manifest.json").write_text(json.dumps({
        "stale_after_days": 30,
        "skills": {"security": {"checked": checked}},
        "custom_skills": {"adr": {"reviewed": reviewed}},
    }), encoding="utf-8")


def test_should_read_dated_skills_without_crashing(hook):
    module, root = hook
    _manifest(root, "2000-01-01", "2000-01-01")
    warning = module.check_skills_staleness()
    assert warning  # both dates are long past the limit


def test_should_stay_quiet_when_skills_were_checked_today(hook):
    from datetime import date
    module, root = hook
    today = date.today().isoformat()
    _manifest(root, today, today)
    assert module.check_skills_staleness() is None
