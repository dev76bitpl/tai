#!/usr/bin/env python3
"""Stack-aware tests guard (pre-commit stage).

Skipped automatically for docs-only commits (no source files staged).

Bypass: SKIP=guard-tests git commit ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import SRC_EXTENSIONS, block, cmd_exists, detect_stack, get_staged_files, get_test_cmd, run_cmd


def main() -> None:
    stack = detect_stack()
    test_cmd = get_test_cmd()

    if not test_cmd:
        print(f"⚠️  [WARN] Unknown stack — tests skipped. Configure .claude/hooks/config.json")
        return

    staged = get_staged_files()
    if not any(f.endswith(SRC_EXTENSIONS) for f in staged):
        print(f"✅ Tests [{stack}] skipped — docs-only commit")
        return

    if not cmd_exists(test_cmd):
        print(f"⚠️  [WARN] Test command unavailable: {' '.join(test_cmd)}")
        return

    print(f"🔍 Tests [{stack}]...", flush=True)
    code, output = run_cmd(test_cmd)
    if code != 0:
        block(f"❌ [BLOCK] Tests failed:\n{output}")

    print(f"✅ Tests [{stack}] OK")


if __name__ == "__main__":
    main()
