#!/usr/bin/env python3
"""
PostToolUse: PR workflow reminders.
- After git commit on feat/* or fix/*: suggest gh pr create
- After git pull / git checkout main: warn about merged branches not yet deleted
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, is_git_commit_command


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def current_branch() -> str:
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    return result.stdout.strip()


def merged_feature_branches() -> list[str]:
    result = subprocess.run(
        ["git", "branch", "--merged", "main"],
        capture_output=True, text=True
    )
    branches = []
    for line in result.stdout.splitlines():
        b = line.strip().lstrip("* ")
        if b.startswith("feat/") or b.startswith("fix/"):
            branches.append(b)
    return branches


def is_pull_or_checkout_main(command: str) -> bool:
    c = command.strip()
    if "git pull" in c:
        return True
    if "git checkout main" in c or "git checkout master" in c:
        return True
    if "git switch main" in c or "git switch master" in c:
        return True
    return False


def main():
    command = get_command()
    chdir_to_project_root(command)

    if is_git_commit_command(command):
        branch = current_branch()
        if branch.startswith("feat/") or branch.startswith("fix/"):
            print(f"💡 Branch '{branch}' — otwórz PR: gh pr create")
        sys.exit(0)

    if is_pull_or_checkout_main(command):
        stale = merged_feature_branches()
        if stale:
            print("⚠️  Zmergowane branche do usunięcia:")
            for b in stale:
                print(f"   git branch -d {b} && git push origin --delete {b}")
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
