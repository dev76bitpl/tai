#!/usr/bin/env python3
"""
Guard: Testing checklist in docs/TESTING.md.

Blocks feat/* and fix/* commits when docs/TESTING.md has not been touched
anywhere in the current branch (staged now OR committed earlier on this branch).

Bypass: [skip-test-check] in commit message — only for doc-only / chore changes
that have no UI or runtime impact. Requires a justification note in commit body.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_staged_files, is_foreign_repo, is_git_commit_command

TRIGGER_BRANCHES = re.compile(r"^(feat|fix)/")
TESTING_FILE = "docs/TESTING.md"
BASE_BRANCHES = ("main", "master", "develop")


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def current_branch() -> str:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
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
        ["git", "diff", "--name-only", base, "HEAD", "--", TESTING_FILE],
        capture_output=True,
        text=True,
    )
    return TESTING_FILE in r.stdout.splitlines()


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    if "[skip-test-check]" in command:
        sys.exit(0)

    branch = current_branch()
    if not TRIGGER_BRANCHES.match(branch):
        sys.exit(0)

    staged = get_staged_files(command)

    # Pass if TESTING.md is staged in this commit
    if TESTING_FILE in staged:
        sys.exit(0)

    # Pass if TESTING.md was touched in any earlier commit on this branch
    if testing_md_touched_in_branch():
        sys.exit(0)

    msg = (
        f"❌ [BLOCK] docs/TESTING.md nie został zaktualizowany na branchu {branch}.\n\n"
        "  Reguła 16b krok 3: checklist testów manualnych musi trafić do docs/TESTING.md,\n"
        "  nie tylko do czatu.\n\n"
        "  Opcje:\n"
        f"  1. Dopisz checklist do {TESTING_FILE} i dodaj go do staged.\n"
        "  2. Bypass [skip-test-check] — tylko dla zmian czysto dokumentacyjnych\n"
        "     lub nie dotykających UI/runtime. Dopisz uzasadnienie w body commita.\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
