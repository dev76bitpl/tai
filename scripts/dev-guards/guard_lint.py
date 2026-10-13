#!/usr/bin/env python3
"""Stack-aware lint guard (pre-commit stage).

Command: "lint" from .claude/hooks/config.json, else autodetected from the project's files.
When it cannot run, the guard says so on every commit (see stack.guard_command).

Bypass: SKIP=guard-lint git commit ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, detect_stack, guard_command, run_cmd


def main() -> None:
    lint_cmd = guard_command("lint", "Lint", "guard-lint")
    if not lint_cmd:
        return

    stack = detect_stack()
    print(f"🔍 Lint [{stack}]...", flush=True)
    code, output = run_cmd(lint_cmd)
    if code != 0:
        block(f"❌ [BLOCK] Lint failed:\n{output}")

    print(f"✅ Lint [{stack}] OK")


if __name__ == "__main__":
    main()
