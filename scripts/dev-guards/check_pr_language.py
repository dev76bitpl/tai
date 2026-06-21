#!/usr/bin/env python3
"""PR title + body must be in English (CLAUDE.md rule 2).

Runs in CI on `pull_request` events (the PR body only exists on GitHub, so a
local pre-commit hook cannot enforce it — this is the server-side counterpart to
guard_commit_lang.py). Reuses the shared detector (lang.py) so the commit and PR
checks never drift.

Input (from the GitHub Actions workflow):
  PR_TITLE  — pull request title
  PR_BODY   — pull request body (markdown)

Code spans are stripped before scanning: fenced ```blocks``` and `inline` code
legitimately carry non-English content (file snippets, quoted UI strings, shell
commands). Prose around them must be English — quote any Polish UI string in
backticks to exclude it.

Bypass: put `[skip-lang]` anywhere in the PR body (rare; e.g. a body that must
quote long Polish copy outside code spans).

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


def strip_code(text: str) -> str:
    """Remove fenced and inline code spans — those may hold non-English content
    by design; only the surrounding prose is held to English."""
    return INLINE_CODE.sub(" ", FENCED_CODE.sub(" ", text))


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
            f"[BLOCK] Polish text '{body_hit}' in PR body (outside code spans).\n\n"
            f"   CLAUDE.md rule 2: PR title and body must be in English.\n"
            f"   Quote Polish UI strings in `backticks` to exclude them, or add\n"
            f"   [skip-lang] to the body if the body must carry Polish prose."
        )
        return 1

    print("OK: PR title and body are in English.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
