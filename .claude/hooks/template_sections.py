#!/usr/bin/env python3
"""Which template documents a commit touches and which of their sections the template lacks.

One rule for both template-sync guards (#166): the Claude Code hook (guard-template-sync.py)
and the commit guard (scripts/dev-guards/guard_template_sync.py). Before, the commit guard only
asked whether the template clone's CLAUDE.md had any uncommitted change — it passed on an
unrelated edit there and blocked a section the template already had committed.

The template owns the paths listed in its template-files.json (copy + compare_sections);
other *.md files are the project's own content and are not compared (#237, #240).
"""
import fnmatch
import json
import re
from pathlib import Path, PurePosixPath

LIST_FILE = "template-files.json"
FALLBACK_PATTERNS = ["CLAUDE.md"]


def get_section_headers(text: str) -> set[str]:
    """Every ## and ### heading in the text."""
    headers = set()
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#{2,3}\s+.+", stripped):
            headers.add(stripped)
    return headers


def matches(path: str, pattern: str) -> bool:
    """Same rule as matches() in scripts/update-from-template.py: '*' never crosses '/'."""
    p, q = PurePosixPath(path), PurePosixPath(pattern)
    return p.parent == q.parent and fnmatch.fnmatchcase(p.name, q.name)


def template_patterns(template_root: Path) -> list[str]:
    """Paths the template owns, from its template-files.json. Unreadable list → CLAUDE.md only."""
    try:
        spec = json.loads((template_root / LIST_FILE).read_text(encoding="utf-8"))
        patterns = list(spec.get("copy", [])) + list(spec.get("compare_sections", []))
    except (OSError, ValueError, AttributeError, TypeError):
        return FALLBACK_PATTERNS
    return [p for p in patterns if isinstance(p, str)] or FALLBACK_PATTERNS


def template_md_files(staged: list[str], template_root: Path) -> list[str]:
    """Staged *.md files that belong to the template — the only ones worth comparing."""
    patterns = template_patterns(template_root)
    return sorted({f for f in staged if f.endswith(".md") and any(matches(f, p) for p in patterns)})


def md_issues(project_root: Path, template_root: Path, md_files: list[str]) -> list[str]:
    """One line per section a project document has and the template's copy lacks."""
    issues = []
    for rel in md_files:
        project_file, template_file = project_root / rel, template_root / rel
        if not project_file.is_file() or not template_file.is_file():
            continue  # deleted in the project, or not in the template clone yet
        try:
            project_headers = get_section_headers(project_file.read_text(encoding="utf-8"))
            template_headers = get_section_headers(template_file.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"  ⚠️  Błąd odczytu {rel}: {e}")
            continue
        for h in sorted(project_headers - template_headers):
            issues.append(f"  📝 {rel}: sekcja jest w projekcie, brakuje w template  →  {h}")
    return issues
