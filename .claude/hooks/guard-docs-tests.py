#!/usr/bin/env python3
"""
Guard 2: Dokumentacja i testy w staged.
Blokuje (exit 2 + stderr) git commit jeśli:
- docs/TASKS.md nie jest w staged
- zmodyfikowano pliki źródłowe bez plików testowych

Jeśli brakuje testów: komunikat instruuje Claude żeby zaproponował
stworzenie plików testowych przed kontynuacją commita.
Dotyczy też istniejących plików modyfikowanych bez pokrycia testowego.

Bypass: [skip-docs] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_staged_files, is_foreign_repo, is_git_commit_command


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    if "[skip-docs]" in command:
        sys.exit(0)

    staged = get_staged_files(command)

    issues = []

    if not any("docs/TASKS.md" in f for f in staged):
        issues.append("📋 docs/TASKS.md nie jest w staged — zaktualizuj zadanie przed commitem.")

    NEXT_PAGE_PATTERN = re.compile(r"src/app/.*/(page|layout|loading|error|not-found)\.(tsx|ts|jsx|js)$")
    src_files = [
        f for f in staged
        if re.search(r"src/.*\.(ts|tsx|js|jsx|php|py|rb|go)$", f)
        and ".test." not in f
        and "__tests__" not in f
        and ".d.ts" not in f
        and ".spec." not in f
        and not NEXT_PAGE_PATTERN.search(f)
    ]
    test_files = [f for f in staged if ".test." in f or "__tests__" in f or ".spec." in f]

    if src_files and not test_files:
        files_list = "".join(f"     → {f}\n" for f in src_files[:5])
        if len(src_files) > 5:
            files_list += f"     ... i {len(src_files) - 5} więcej\n"
        issues.append(
            f"🧪 Brak plików testowych dla {len(src_files)} plik(ów) w staged:\n"
            + files_list
            + "   Zaproponuj stworzenie plików testowych dla powyższych plików.\n"
            + "   Jeśli testy nie są tu potrzebne: dodaj [skip-docs] do commita."
        )

    if issues:
        msg = "❌ [BLOCK] Sprawdź przed commitem:\n\n" + "\n".join(f"  {i}" for i in issues)
        msg += "\n\n  Bypass dla całości: dodaj [skip-docs] do wiadomości commita."
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
