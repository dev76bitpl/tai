"""What the project-start stages done in Claude Code should leave behind — checked, not assumed.

Pure functions of the project root, used by scripts/project-setup.py after the user returns
from Claude Code (brief interview, design stage). Stays in the project with that script.
"""
import json
from pathlib import Path

from start_prompts import DESIGN_HEADING, MOCKUPS_DIR

# A line only the template's own docs/PROJECT_SCOPE.md skeleton contains. While it is there the
# file is a form to fill in, not a brief (a test pins the marker to the real skeleton).
SCOPE_SCAFFOLD_MARKER = "sekcje są scaffoldem"


def scope_is_filled(root: Path) -> bool:
    """True when the project already has its own brief in docs/PROJECT_SCOPE.md."""
    scope = root / "docs" / "PROJECT_SCOPE.md"
    if not scope.is_file():
        return False
    text = scope.read_text(encoding="utf-8", errors="ignore")
    return bool(text.strip()) and SCOPE_SCAFFOLD_MARKER not in text


def brief_checks(root: Path) -> list[tuple[bool, str]]:
    """What the scope interview should have left behind — checked, not assumed."""
    config_path = root / ".claude" / "hooks" / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        config = {}
    stack = config.get("stack") if isinstance(config, dict) else None
    adr_dir = root / "docs" / "adr"
    has_adr = any(path.name != "ADR-001-example.md" for path in adr_dir.glob("ADR-001*.md"))
    return [
        (scope_is_filled(root), "brief: docs/PROJECT_SCOPE.md ma własną treść"),
        (bool(stack), f"stos ustawiony dla strażników: {stack}" if stack else "stos ustawiony dla strażników (scripts/set-stack.py)"),
        (has_adr, "ADR-001 w docs/adr/"),
    ]


def design_checks(root: Path) -> list[tuple[bool, str]]:
    """What the design stage should have left behind."""
    mockups = root / MOCKUPS_DIR
    guidelines = root / "docs" / "UI_GUIDELINES.md"
    try:
        written = DESIGN_HEADING in guidelines.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        written = False
    return [
        (mockups.is_dir() and any(mockups.glob("*.html")), f"makiety kierunków w {MOCKUPS_DIR}/"),
        (written, "zasady wyglądu w docs/UI_GUIDELINES.md (sekcja „Kierunek wizualny projektu”)"),
    ]
