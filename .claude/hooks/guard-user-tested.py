#!/usr/bin/env python3
"""
Guard 6: User-tested flag.
Blokuje (exit 2 + stderr) git commit na branchach feat/* i fix/* jeśli:
- wiadomość commita nie zawiera [user-tested]

Backup dla module closure protocol (CLAUDE.md reguła 16b):
- AI nie może commitować zanim user explicite nie potwierdził manualnego testu.
- Flaga [user-tested] = "user przeszedł manual checklist z docs/TESTING.md i zaakceptował".

Bypass:
- [skip-test-check] — dla zmian dokumentacyjnych / chore nie dotykających runtime'u
- inne typy branchy (docs/*, chore/*, refactor/*, test/*) — flaga nie wymagana
- detached HEAD / brak brancha — pominięte (rebase, cherry-pick itp.)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, is_foreign_repo


ENFORCED_BRANCH_PREFIXES = ("feat/", "fix/")


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def extract_commit_message(command: str) -> str:
    m = re.search(r'-m\s+"([^"]+)"', command)
    if m:
        return m.group(1)
    m = re.search(r"-m\s+'([^']+)'", command)
    if m:
        return m.group(1)
    m = re.search(r"<<['\"]?EOF['\"]?\s*\n(.*?)\nEOF", command, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    chdir_to_project_root()
    command = get_command()

    if "git commit" not in command:
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    # Bypass globalny dla docs/chore-only commits
    if "[skip-test-check]" in command:
        sys.exit(0)

    branch = get_current_branch()
    if not branch or branch == "HEAD":
        # detached HEAD (rebase, cherry-pick) — nie blokujemy
        sys.exit(0)

    if not branch.startswith(ENFORCED_BRANCH_PREFIXES):
        # docs/*, chore/*, refactor/*, test/* — flaga nie wymagana
        sys.exit(0)

    msg = extract_commit_message(command)
    if not msg:
        # pre-commit.py i tak to złapie z lepszym komunikatem
        sys.exit(0)

    if "[user-tested]" not in msg:
        block(
            "❌ [BLOCK] Commit na branchu '" + branch + "' bez flagi [user-tested].\n"
            "\n"
            "   CLAUDE.md reguła 16b (module closure protocol):\n"
            "   commit dozwolony dopiero po manualnym teście usera wg docs/TESTING.md.\n"
            "\n"
            "   Jeśli user explicite zaakceptował zmianę:\n"
            "     → dodaj [user-tested] do wiadomości commita.\n"
            "\n"
            "   Jeśli zmiana jest czysto dokumentacyjna / chore (bez runtime'u):\n"
            "     → użyj [skip-test-check] z uzasadnieniem w body commita.\n"
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
