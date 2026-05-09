#!/usr/bin/env python3
"""
Guard 2: Dokumentacja i testy w staged.
Blokuje (exit 2 + stderr) git commit jeśli:
- docs/TASKS.md nie jest w staged
- zmodyfikowano pliki źródłowe bez plików testowych

Bypass: [skip-docs] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, is_foreign_repo


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def main():
    chdir_to_project_root()
    command = get_command()

    if "git commit" not in command:
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    if "[skip-docs]" in command:
        sys.exit(0)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    ).stdout.splitlines()

    issues = []

    if not any("docs/TASKS.md" in f for f in staged):
        issues.append("📋 docs/TASKS.md nie jest w staged — zaktualizuj zadanie przed commitem.")

    src_files = [
        f for f in staged
        if re.search(r"src/.*\.(ts|tsx|js|jsx|php|py|rb|go)$", f)
        and ".test." not in f
        and "__tests__" not in f
        and ".d.ts" not in f
        and ".spec." not in f
    ]
    test_files = [f for f in staged if ".test." in f or "__tests__" in f or ".spec." in f]

    if src_files and not test_files:
        files_list = "".join(f"     → {f}\n" for f in src_files[:5])
        if len(src_files) > 5:
            files_list += "     ...\n"
        issues.append(
            f"🧪 {len(src_files)} plik(ów) źródłowych bez plików testowych w staged.\n"
            + files_list
            + "   Czy testy są potrzebne? Jeśli nie — dodaj [skip-docs]."
        )

    if issues:
        msg = "❌ [BLOCK] Sprawdź przed commitem:\n\n" + "\n".join(f"  {i}" for i in issues)
        msg += "\n\n  Jeśli to świadoma decyzja: dodaj [skip-docs] do wiadomości commita."
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
