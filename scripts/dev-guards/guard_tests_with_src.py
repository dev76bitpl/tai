#!/usr/bin/env python3
"""Source file changes require accompanying tests (CLAUDE.md rule 16).

Stage: commit-msg.

What counts as source: files with a source extension inside the project's code directories —
`src_dirs` in .claude/hooks/config.json, default ["src"]. new-project.py sets it at project start.

What counts as a test (built in, every stack — no configuration):
  - JavaScript/TypeScript: *.test.*, *.spec.*, __tests__/
  - Python: test_*.py, *_test.py        - Go: *_test.go
  - PHP: *Test.php                      - Ruby: *_spec.rb, *_test.rb
  - any source file under tests/, test/ or spec/

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
from stack import block, get_staged_files, load_config, read_commit_msg

NEXT_PAGE_PATTERN = re.compile(r"src/app/.*/(page|layout|loading|error|not-found)\.(tsx|ts|jsx|js)$")
SRC_EXTENSION = re.compile(r"\.(ts|tsx|js|jsx|php|py|rb|go)$")
DEFAULT_SRC_DIRS = ["src"]

TEST_DIRS = {"tests", "test", "spec", "__tests__"}
TEST_NAME_PATTERN = re.compile(
    r"^(test_.*\.py|.*_test\.py|.*_test\.go|.*Test\.php|.*_spec\.rb|.*_test\.rb)$"
)


def get_src_dirs() -> list[str]:
    """Code directories from config; anything unusable falls back to the default."""
    value = load_config().get("src_dirs")
    if not isinstance(value, list):
        return DEFAULT_SRC_DIRS
    dirs = [d.strip().strip("/") for d in value if isinstance(d, str)]
    return [d for d in dirs if d] or DEFAULT_SRC_DIRS


def is_test_file(f: str) -> bool:
    if ".test." in f or ".spec." in f or "__tests__" in f:
        return True
    parts = f.split("/")
    if TEST_NAME_PATTERN.match(parts[-1]):
        return True
    return bool(SRC_EXTENSION.search(f)) and any(part in TEST_DIRS for part in parts[:-1])


def is_source_file(f: str, src_dirs: list[str]) -> bool:
    if not SRC_EXTENSION.search(f):
        return False
    # a code directory may sit below the root (monorepo: packages/api/src/...)
    if not any(re.search(rf"(^|/){re.escape(d)}/", f) for d in src_dirs):
        return False
    if is_test_file(f) or ".d.ts" in f:
        return False
    if NEXT_PAGE_PATTERN.search(f):
        return False
    return True


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-docs]" in msg:
        return

    staged = get_staged_files()
    src_dirs = get_src_dirs()
    src_files = [f for f in staged if is_source_file(f, src_dirs)]
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
