#!/usr/bin/env python3
"""CLAUDE.md changes must be acknowledged against the AI template (CLAUDE.md rule 13a).

Stage: commit-msg

Model (ADR-002): acknowledgment, not silent file comparison. When CLAUDE.md is
staged the guard forces a conscious decision — every time, on any machine, with
zero setup and no local template clone:

  - [skip-sync] in body  → change is project-specific or already synced (pass)
  - otherwise            → block: apply the universal rule to the template repo

If ai_template_path points at a local template clone, the guard ADDITIONALLY
auto-verifies (git diff) and passes silently when that clone's CLAUDE.md was
touched this session — a convenience for template maintainers, not a requirement.
A URL or a missing path degrades safely to acknowledgment mode (never a silent
skip — the old behavior that left this guard dead in new projects).

is_template: true in config → this repo IS the template, nothing above to sync.

Configuration: .claude/hooks/config.json (canonical, ADR-002 decision 4)
  { "ai_template_path": "/local/path/to/template-clone" }   # optional

Bypass:
  - [skip-sync] in commit body
  - SKIP=guard-template-sync git commit ...
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_staged_files, load_config, read_commit_msg

_URL_PREFIXES = ("http://", "https://", "git@", "ssh://")


def _staged_touches_claude(staged: list[str]) -> bool:
    return any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged)


def _local_template_claude(template_path: str) -> Path | None:
    """The template's CLAUDE.md if template_path is a usable local clone, else None.

    URLs and non-existent paths return None → acknowledgment mode (ADR-002): the
    sync guard needs a local working tree for `git diff`; a URL can't provide one.
    """
    if not template_path or template_path.startswith(_URL_PREFIXES):
        return None
    claude = Path(template_path) / "CLAUDE.md"
    return claude if claude.is_file() else None


def _template_claude_touched(template_claude: Path) -> bool:
    """True if the template clone's CLAUDE.md has un/staged changes this session.

    Full content comparison won't work — the project CLAUDE.md carries [project]
    sections the template intentionally omits — so we check for *any* local change.
    """
    cwd = str(template_claude.parent)
    unstaged = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CLAUDE.md"],
        capture_output=True, text=True, cwd=cwd,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", "CLAUDE.md"],
        capture_output=True, text=True, cwd=cwd,
    )
    return "CLAUDE.md" in unstaged.stdout or "CLAUDE.md" in staged.stdout


BLOCK_ACKNOWLEDGE = (
    "❌ [BLOCK] CLAUDE.md staged — confirm where this change belongs (CLAUDE.md rule 13a).\n"
    "\n"
    "   Universal rule  → apply it to the AI template repo's CLAUDE.md too.\n"
    "   Project-specific or already synced → add [skip-sync] to the commit body.\n"
    "\n"
    "   (No local template clone configured — set ai_template_path in\n"
    "    .claude/hooks/config.json for automatic verification.)\n"
    "\n"
    "   Bypass (audit trail):  add [skip-sync] to commit body\n"
    "   Bypass (no audit):     SKIP=guard-template-sync git commit ..."
)


def _block_not_synced(template_claude: Path) -> str:
    return (
        "❌ [BLOCK] CLAUDE.md staged but the template's CLAUDE.md has no matching changes.\n"
        "\n"
        "   CLAUDE.md rule 13a: sync universal rules to the template before committing.\n"
        f"   Template: {template_claude}\n"
        "\n"
        "   1. Apply universal changes to the template repo's CLAUDE.md\n"
        "   2. Or add [skip-sync] if this change is project-specific\n"
        "\n"
        "   Bypass (audit trail):  add [skip-sync] to commit body\n"
        "   Bypass (no audit):     SKIP=guard-template-sync git commit ..."
    )


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-sync]" in msg:
        return

    staged = get_staged_files()
    if not _staged_touches_claude(staged):
        return  # CLAUDE.md not touched

    config = load_config()
    if config.get("is_template"):
        return  # this repo IS the template — nothing above to sync

    template_claude = _local_template_claude(config.get("ai_template_path", ""))
    if template_claude is None:
        block(BLOCK_ACKNOWLEDGE)  # acknowledgment mode — no usable local clone
        return

    if _template_claude_touched(template_claude):
        return  # template updated this session
    block(_block_not_synced(template_claude))


if __name__ == "__main__":
    main(sys.argv)
