#!/usr/bin/env python3
"""TypeScript type check guard (pre-commit stage).

Runs `tsc --noEmit` for Node/TypeScript projects.
Skipped for docs-only changesets.

Bypass: SKIP=guard-typecheck git commit ...
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, cmd_exists, detect_stack, get_staged_files, run_cmd

SRC_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")


def main() -> None:
    stack = detect_stack()
    if stack != "node":
        return

    staged = get_staged_files()
    src_staged = [f for f in staged if Path(f).suffix in SRC_EXTENSIONS]
    if not src_staged:
        print("⚡ TypeScript check skipped (no TS/JS files staged)")
        return

    tsc = ["node_modules/.bin/tsc", "--noEmit"]
    if not cmd_exists(["node_modules/.bin/tsc"]):
        print("⚠️  [WARN] tsc not found — type check skipped")
        return

    print("🔍 TypeScript type check...", flush=True)
    code, output = run_cmd(tsc)
    if code != 0:
        block(f"❌ [BLOCK] TypeScript errors:\n{output}")

    print("✅ TypeScript OK")


if __name__ == "__main__":
    main()
