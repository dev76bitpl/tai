#!/usr/bin/env python3
"""Stack-aware lint guard (pre-commit stage).

Bypass: SKIP=guard-lint git commit ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, cmd_exists, detect_stack, get_lint_cmd, run_cmd


def main() -> None:
    stack = detect_stack()
    lint_cmd = get_lint_cmd()

    if not lint_cmd:
        print(f"⚠️  [WARN] Unknown stack — lint skipped. Configure .pre-commit-hooks.config.json")
        return

    if not cmd_exists(lint_cmd):
        print(f"⚠️  [WARN] Lint command unavailable: {' '.join(lint_cmd)}")
        return

    print(f"🔍 Lint [{stack}]...", flush=True)
    code, output = run_cmd(lint_cmd)
    if code != 0:
        block(f"❌ [BLOCK] Lint failed:\n{output}")

    print(f"✅ Lint [{stack}] OK")


if __name__ == "__main__":
    main()
