#!/usr/bin/env python3
"""
Guard: Testing checklist in docs/TESTING.md.

Blocks feat/* and fix/* commits when no manual-test checklist has been touched
anywhere in the current branch (staged now OR committed earlier on this branch).
A checklist is docs/TESTING.md (flows of the project) or any other docs/*TESTING*.md
(e.g. docs/GUARDS_TESTING.md for the guard system) — the scenario goes where it belongs.

Bypass: [skip-test-check] in commit message — only for doc-only / chore changes
that have no UI or runtime impact. Requires a justification note in commit body.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_commit_message, get_staged_files, is_foreign_repo, is_git_commit_command, read_command

TRIGGER_BRANCHES = re.compile(r"^(feat|fix)/")
TESTING_FILE = "docs/TESTING.md"
TESTING_FILES = re.compile(r"^docs/[^/]*TESTING[^/]*\.md$")
BASE_BRANCHES = ("main", "master", "develop")


def current_branch() -> str:
    # --show-current also answers on a branch with no commits yet, where rev-parse HEAD fails
    # (and a failure here would read as "not a feat/fix branch" = pass).
    r = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def merge_base(branch: str) -> str:
    for base in BASE_BRANCHES:
        r = subprocess.run(["git", "merge-base", "HEAD", base], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
    return ""


def testing_md_touched_in_branch() -> bool:
    base = merge_base(current_branch())
    if not base:
        return False
    r = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD", "--", "docs/"],
        capture_output=True,
        text=True,
    )
    return any(TESTING_FILES.match(name) for name in r.stdout.splitlines())


def main():
    command = read_command("guard-testing-checklist")
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    # Bypass flag may live inline (command) OR inside a -F <file> message.
    if "[skip-test-check]" in command + "\n" + (get_commit_message(command) or ""):
        sys.exit(0)

    branch = current_branch()
    if not TRIGGER_BRANCHES.match(branch):
        sys.exit(0)

    staged = get_staged_files(command)

    # Pass if TESTING.md is staged in this commit
    if any(TESTING_FILES.match(name) for name in staged):
        sys.exit(0)

    # Pass if TESTING.md was touched in any earlier commit on this branch
    if testing_md_touched_in_branch():
        sys.exit(0)

    msg = (
        f"❌ [BLOCK] docs/TESTING.md nie został zaktualizowany na branchu {branch}.\n\n"
        "  Reguła 16b krok 3: checklist testów manualnych musi trafić do docs/TESTING.md,\n"
        "  nie tylko do czatu.\n\n"
        "  Opcje:\n"
        f"  1. Dopisz checklist do {TESTING_FILE} (flow projektu) albo do innego docs/*TESTING*.md\n"
        "     (np. docs/GUARDS_TESTING.md dla strażników) i dodaj plik do staged.\n"
        "  2. Bypass [skip-test-check] — tylko dla zmian czysto dokumentacyjnych\n"
        "     lub nie dotykających UI/runtime. Dopisz uzasadnienie w body commita.\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
