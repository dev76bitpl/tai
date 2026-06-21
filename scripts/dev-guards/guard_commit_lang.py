#!/usr/bin/env python3
"""Commit subject must be in English (CLAUDE.md rule 2).

Stage: commit-msg.

Heuristics (any match → block):
  1. Subject contains Polish-specific characters: ą ć ę ł ń ó ś ź ż (and uppercase)
  2. Subject contains common Polish words after the conventional-commit prefix

Bypass:
  - SKIP=guard-commit-lang git commit ...

Note: scope and description after `type(scope):` are checked. Body is not checked
(body can contain rationale in Polish for now — only the subject travels in CI logs,
PR titles, changelogs).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, read_commit_msg
from lang import find_polish


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if not msg.strip():
        return

    subject = msg.splitlines()[0].strip()
    if not subject:
        return

    # Strip conventional-commits prefix: `type(scope): ` — only check the description.
    m = re.match(
        r"^(?:feat|fix|docs|refactor|test|chore|style|perf|ci|build)"
        r"(?:\([a-zA-Z0-9_/.-]+\))?!?:\s*(.+)$",
        subject,
    )
    description = m.group(1) if m else subject

    found = find_polish(description)
    if found:
        block(
            f"❌ [BLOCK] Polish text '{found}' in commit subject:\n"
            f"   '{subject}'\n"
            f"\n"
            f"   CLAUDE.md rule 2: commit messages must be in English.\n"
            f"\n"
            f"   Bypass (no audit): SKIP=guard-commit-lang git commit ..."
        )


if __name__ == "__main__":
    main(sys.argv)
