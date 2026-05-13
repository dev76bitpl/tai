#!/usr/bin/env python3
"""Source file changes require accompanying tests (CLAUDE.md rule 16).

Stage: commit-msg.

Excludes:
  - Next.js page/layout files (page.tsx, layout.tsx, loading.tsx, error.tsx, not-found.tsx)
  - *.d.ts declarations
  - Test files themselves

Bypass:
  - [skip-docs] in commit body — committed alongside change
  - SKIP=guard-tests-with-src git commit ... — env var
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_staged_files, read_commit_msg

NEXT_PAGE_PATTERN = re.compile(r"src/app/.*/(page|layout|loading|error|not-found)\.(tsx|ts|jsx|js)$")
SRC_PATTERN = re.compile(r"src/.*\.(ts|tsx|js|jsx|php|py|rb|go)$")


def is_source_file(f: str) -> bool:
    if not SRC_PATTERN.search(f):
        return False
    if ".test." in f or "__tests__" in f or ".spec." in f or ".d.ts" in f:
        return False
    if NEXT_PAGE_PATTERN.search(f):
        return False
    return True


def is_test_file(f: str) -> bool:
    return ".test." in f or "__tests__" in f or ".spec." in f


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-docs]" in msg:
        return

    staged = get_staged_files()
    src_files = [f for f in staged if is_source_file(f)]
    test_files = [f for f in staged if is_test_file(f)]

    if src_files and not test_files:
        files_list = "".join(f"     → {f}\n" for f in src_files[:5])
        if len(src_files) > 5:
            files_list += f"     ... and {len(src_files) - 5} more\n"
        block(
            f"❌ [BLOCK] {len(src_files)} source file(s) staged without any test files:\n"
            + files_list
            + "\n"
            + "   CLAUDE.md rule 16: every non-trivial change ships with tests.\n"
            + "\n"
            + "   Bypass (audit trail):  add [skip-docs] to commit body\n"
            + "   Bypass (no audit):     SKIP=guard-tests-with-src git commit ..."
        )


if __name__ == "__main__":
    main(sys.argv)
