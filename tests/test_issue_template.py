"""The issue template and the rule in CLAUDE.md agree on the deadline line (#218)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "sprawa.md"
DEADLINE = re.compile(r"^termin: (\d{4}-\d{2}-\d{2})$", re.MULTILINE)


def test_should_give_the_issue_template_a_deadline_line():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert text.startswith("---\nname: ")
    assert re.search(r"^termin:\s*$", text, re.MULTILINE)


def test_should_not_ship_a_made_up_deadline_in_the_template():
    assert not DEADLINE.search(TEMPLATE.read_text(encoding="utf-8"))


def test_should_state_the_deadline_format_in_the_rules():
    assert "`termin: RRRR-MM-DD`" in (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "## § Termin w issue" in (ROOT / "docs" / "RULES_REFERENCE.md").read_text(encoding="utf-8")
