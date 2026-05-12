#!/usr/bin/env python3
"""
Guard 3: Heurystyka ADR.
Blokuje (exit 2 + stderr) git commit jeśli staged files sugerują decyzję
architektoniczną i żaden plik ADR nie jest w staged.

Wzorce konfigurowalne przez .claude/hooks/config.json:
{ "adr_patterns": [["migrations/", "migracja bazy danych"]] }

Bypass: [no-adr] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_adr_patterns, is_foreign_repo, is_git_commit_command


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

    if "[no-adr]" in command:
        sys.exit(0)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    ).stdout.splitlines()

    if any(re.search(r"docs/adr/", f) for f in staged):
        sys.exit(0)

    patterns = get_adr_patterns()
    hits = []
    seen: set[str] = set()
    for f in staged:
        for pattern, description in patterns:
            if re.search(pattern, f) and f not in seen:
                hits.append(f"  → {f}  ({description})")
                seen.add(f)
                break

    if hits:
        msg = "❌ [BLOCK] Wykryto zmiany które mogą wymagać ADR:\n\n"
        msg += "\n".join(hits)
        msg += "\n\n  Jeśli ADR jest potrzebny: utwórz docs/adr/ADR-XXX.md i dodaj do staged."
        msg += "\n  Jeśli nie: dodaj [no-adr] do wiadomości commita."
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
