#!/usr/bin/env python3
"""ADR heuristic — block commits with architectural changes lacking an ADR file.

Stage: commit-msg.

Patterns are configurable via .pre-commit-hooks.config.json:
  { "adr_patterns": [["migrations/", "database migration"]] }

Bypass:
  - [no-adr] in commit body — committed alongside change (audit trail)
  - SKIP=guard-adr git commit ... — env var
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_adr_patterns, get_staged_files, read_commit_msg


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[no-adr]" in msg:
        return

    staged = get_staged_files()

    if any(re.search(r"docs/adr/", f) for f in staged):
        return

    patterns = get_adr_patterns()
    hits: list[str] = []
    seen: set[str] = set()
    for f in staged:
        for pattern, description in patterns:
            if re.search(pattern, f) and f not in seen:
                hits.append(f"  → {f}  ({description})")
                seen.add(f)
                break

    if hits:
        block(
            "❌ [BLOCK] Architectural changes detected — ADR may be required:\n\n"
            + "\n".join(hits)
            + "\n\n"
            + "   If an ADR is needed: create docs/adr/ADR-XXX.md and stage it.\n"
            + "\n"
            + "   Bypass (audit trail):  add [no-adr] to commit body\n"
            + "   Bypass (no audit):     SKIP=guard-adr git commit ..."
        )


if __name__ == "__main__":
    main(sys.argv)
