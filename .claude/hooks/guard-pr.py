#!/usr/bin/env python3
"""
Guard 5: PR guard.
Blokuje (exit 2 + stderr) gh pr create jeśli:
- docs/TASKS.md nie był zmodyfikowany w branchu
- testy nie przechodzą

Nieznany stack: ostrzega, nie blokuje dla testów.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, cmd_exists, detect_stack, get_test_cmd, run_cmd


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def get_branch_changed_files() -> list[str]:
    for base in ("main", "origin/main", "master", "origin/master"):
        result = subprocess.run(
            ["git", "diff", f"{base}...HEAD", "--name-only"], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.splitlines()
    return []


def main():
    command = get_command()
    chdir_to_project_root(command)

    if "gh pr create" not in command:
        sys.exit(0)

    issues = []

    changed = get_branch_changed_files()
    if not any("docs/TASKS.md" in f for f in changed):
        issues.append(
            "📋 docs/TASKS.md nie był zmodyfikowany w tym branchu.\n"
            "   Zaktualizuj TASKS.md, scommituj i spróbuj ponownie."
        )

    stack = detect_stack()
    test_cmd = get_test_cmd()

    if not test_cmd:
        print(f"⚠️  [WARN] Nieznany stack — testy pominięte. Skonfiguruj .claude/hooks/config.json")
    elif not cmd_exists(test_cmd):
        print(f"⚠️  [WARN] Komenda test niedostępna: {' '.join(test_cmd)}")
    else:
        print(f"🔍 Testy przed PR [{stack}]...", flush=True)
        code, output = run_cmd(test_cmd)
        if code != 0:
            issues.append(f"🧪 Testy failed:\n{output}")

    if issues:
        msg = "❌ [BLOCK] PR nie może być otwarty:\n\n"
        msg += "\n".join(f"  {i}" for i in issues)
        print(msg, file=sys.stderr)
        sys.exit(2)

    print(f"✅ PR guard OK [{stack}]: TASKS.md ✓  testy ✓")
    sys.exit(0)


if __name__ == "__main__":
    main()
