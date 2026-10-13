#!/usr/bin/env python3
"""Stack-aware tests guard (pre-commit stage).

Skipped automatically for docs-only commits (no source files staged).
Command: "test" from .claude/hooks/config.json, else autodetected from the project's files.
When it cannot run, the guard says so on every commit (see stack.guard_command).

Bypass: SKIP=guard-tests git commit ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import SRC_EXTENSIONS, block, detect_stack, get_cmd, get_staged_files, guard_command, run_cmd


def main() -> None:
    stack = detect_stack()
    if get_cmd("test")[0]:
        staged = get_staged_files()
        if not any(f.endswith(SRC_EXTENSIONS) for f in staged):
            print(f"✅ Tests [{stack}] skipped — docs-only commit")
            return

    test_cmd = guard_command("test", "Test", "guard-tests")
    if not test_cmd:
        return

    print(f"🔍 Tests [{stack}]...", flush=True)
    code, output = run_cmd(test_cmd)
    if code != 0:
        block(f"❌ [BLOCK] Tests failed:\n{output}")

    print(f"✅ Tests [{stack}] OK")


if __name__ == "__main__":
    main()
