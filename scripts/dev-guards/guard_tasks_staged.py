#!/usr/bin/env python3
"""docs/TASKS.md must be in staged (CLAUDE.md rule 4).

The file is the session log: every commit carries an entry saying what happened
and why. Open work lives in issues (or in this file when the project has no
GitHub remote, ADR-004) — the guard does not look at that, only at the log.

Stage: commit-msg (so [skip-docs] body flag works).

Bypass:
  - [skip-docs] in commit body — committed alongside change (audit trail)
  - SKIP=guard-tasks-staged git commit ... — env var (not committed)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_staged_files, read_commit_msg


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-docs]" in msg:
        return

    staged = get_staged_files()
    if not any("docs/TASKS.md" in f for f in staged):
        block(
            "❌ [BLOCK] docs/TASKS.md is not in staged files.\n"
            "\n"
            "   CLAUDE.md rule 4: add a session log entry (what happened and why)\n"
            "   before committing. Open work goes to an issue, not to this file.\n"
            "\n"
            "   Bypass (audit trail):  add [skip-docs] to commit body\n"
            "   Bypass (no audit):     SKIP=guard-tasks-staged git commit ..."
        )


if __name__ == "__main__":
    main(sys.argv)
