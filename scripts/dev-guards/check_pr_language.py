#!/usr/bin/env python3
"""PR title + body must be in English (CLAUDE.md rule 2).

Runs in CI on `pull_request` events (the PR body only exists on GitHub, so a
local pre-commit hook cannot enforce it — this is the server-side counterpart to
guard_commit_lang.py). Reuses the shared detector (lang.py) so the commit and PR
checks never drift.

Input (from the GitHub Actions workflow):
  PR_TITLE  — pull request title
  PR_BODY   — pull request body (markdown)

Code and quoted spans are stripped before scanning: fenced ```blocks```,
`inline` code, and "double-quoted" strings legitimately carry non-English
content (file snippets, UI labels, status names, notification copy). Prose
around them must be English — quote any non-English UI string in backticks OR
double quotes to exclude it. Quoting is the universal "this is a literal, not
my prose" signal; double quotes are how a localized UI label is most naturally
referenced in an English sentence (e.g. the "Zapisz zmiany" button).

Bypass: put `[skip-lang]` anywhere in the PR body (rare; e.g. a body that must
quote long non-English copy outside code/quote spans).

Exit: 0 if English (or bypassed/empty), 1 if Polish detected.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lang import find_polish

FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`]*`")
# Double-quoted spans: straight ("…"), typographic ("…"), and low-opening („…").
# NOT single quotes — English apostrophes (don't, it's) would create bogus
# spans and mask non-English text between them.
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”|„[^”]*”")


def strip_code(text: str) -> str:
    """Remove fenced/inline code spans and double-quoted strings — those may
    hold non-English content by design (snippets, UI labels, status names);
    only the surrounding prose is held to English."""
    text = FENCED_CODE.sub(" ", text)
    text = INLINE_CODE.sub(" ", text)
    return QUOTED.sub(" ", text)


def main() -> int:
    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY", "")

    if "[skip-lang]" in body:
        print("[skip-lang] present in PR body - language check bypassed.")
        return 0

    # Title is short prose (like a commit subject) - checked whole.
    title_hit = find_polish(title)
    if title_hit:
        print(
            f"[BLOCK] Polish text '{title_hit}' in PR title:\n"
            f"   '{title}'\n\n"
            f"   CLAUDE.md rule 2: PR title and body must be in English."
        )
        return 1

    body_hit = find_polish(strip_code(body))
    if body_hit:
        print(
            f"[BLOCK] Polish text '{body_hit}' in PR body (outside code/quote spans).\n\n"
            f"   CLAUDE.md rule 2: PR title and body must be in English.\n"
            f"   Quote non-English UI strings in `backticks` or \"double quotes\" to\n"
            f"   exclude them, or add [skip-lang] to the body to carry foreign prose."
        )
        return 1

    print("OK: PR title and body are in English.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
