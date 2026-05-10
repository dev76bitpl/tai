#!/usr/bin/env python3
"""
PostToolUse: suggest PR after git commit on feat/* or fix/* branch.
Prints a reminder — does not block.
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


def main():
    chdir_to_project_root()
    command = get_command()

    if not is_git_commit_command(command):
        sys.exit(0)

    branch = current_branch()
    if not (branch.startswith("feat/") or branch.startswith("fix/")):
        sys.exit(0)

    print(f"💡 Branch '{branch}' — otwórz PR: gh pr create")
    sys.exit(0)


if __name__ == "__main__":
    main()
