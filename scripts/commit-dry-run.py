#!/usr/bin/env python3
"""Dry run of everything that can stop a `git commit`, with the message you are about to use.

  python3 scripts/commit-dry-run.py <message-file>

Two layers guard a commit, and the old dry run (pre-commit commit-msg stage alone) saw only one:

  1. Claude Code hooks (PreToolUse on Bash/PowerShell, wired in .claude/settings.local.json):
     guard-ai-template, guard-template-sync, ... They fire on the `git commit` command itself and
     are not in .pre-commit-config.yaml, so a green dry run still ended in a blocked commit (#135).
     Each one gets the same payload Claude Code would send for `git commit -F <message-file>`.
  2. pre-commit, commit-msg stage: gitlint, language, flags, ...

The pre-commit stage (lint, tests, secrets) is not repeated here: the commit runs it anyway.
Exit code 0 = one `git commit -F <message-file>` goes through; 1 = something blocks, shown above.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
HOOK_IN_COMMAND = re.compile(r"\.claude/hooks/([\w.-]+\.py)")
SHELL_TOOLS = re.compile(r"\b(Bash|PowerShell)\b")


def shell_hooks(root: Path) -> list[Path]:
    """The hook files Claude Code runs before a shell command, from the wired settings.

    settings.local.json is what this machine really runs; without it the .example shows what
    the project ships (a guard that is not wired here does not block here either — doctor says so).
    """
    for name in ("settings.local.json", "settings.local.json.example"):
        path = root / ".claude" / name
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        hooks: list[Path] = []
        for entry in settings.get("hooks", {}).get("PreToolUse", []) or []:
            if not isinstance(entry, dict) or not SHELL_TOOLS.search(str(entry.get("matcher", ""))):
                continue
            for hook in entry.get("hooks", []) or []:
                found = HOOK_IN_COMMAND.search(str(hook.get("command", "")))
                if found and (root / ".claude" / "hooks" / found.group(1)).is_file():
                    hooks.append(root / ".claude" / "hooks" / found.group(1))
        return list(dict.fromkeys(hooks))
    return []


def run_hook(root: Path, hook: Path, message_file: Path) -> tuple[bool, str]:
    """(passes, what it said) for one hook fed `git commit -F <message_file>`."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": f"git commit -F {message_file}"}})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    done = subprocess.run([sys.executable, str(hook)], input=payload, cwd=root, env=env,
                          capture_output=True, text=True, encoding="utf-8")
    said = (done.stderr or "").strip()
    if done.returncode == 0 and done.stdout.strip():
        try:  # exit 0 + JSON systemMessage: a warning shown to the owner, the commit goes ahead
            said = json.loads(done.stdout).get("systemMessage", "") or said
        except ValueError:
            said = done.stdout.strip()
    return done.returncode == 0, said


def pre_commit_command() -> "list[str] | None":
    if shutil.which("pre-commit"):
        return ["pre-commit"]
    probe = subprocess.run([sys.executable, "-m", "pre_commit", "--version"], capture_output=True)
    return [sys.executable, "-m", "pre_commit"] if probe.returncode == 0 else None


def run_commit_msg_stage(root: Path, message_file: Path) -> tuple[bool, str]:
    base = pre_commit_command()
    if base is None:
        return False, "pre-commit is not installed — the commit-msg guards cannot be checked (npm run doctor)"
    done = subprocess.run([*base, "run", "--hook-stage", "commit-msg", "--commit-msg-filename", str(message_file)],
                          cwd=root, env={**os.environ, "COMMIT_EDITMSG": str(message_file)},
                          capture_output=True, text=True, encoding="utf-8")
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def dry_run(root: Path, message_file: Path, with_pre_commit: bool = True) -> bool:
    ok = True
    hooks = shell_hooks(root)
    print(f"── Claude Code hooks on `git commit` ({len(hooks)}) ──")
    if not hooks:
        print("  (none wired — nothing from this layer will block)")
    for hook in hooks:
        passes, said = run_hook(root, hook, message_file)
        ok &= passes
        print(f"  {'✅' if passes else '❌'} {hook.stem}")
        for line in said.splitlines() if said else []:
            print(f"     {line}")
    if with_pre_commit:
        print("\n── pre-commit, commit-msg stage ──")
        passes, said = run_commit_msg_stage(root, message_file)
        ok &= passes
        for line in said.splitlines():
            print(f"  {line}")
    print(f"\n{'✅ All green — one `git commit -F ' + str(message_file) + '` goes through.' if ok else '❌ Something blocks — fix it before committing.'}")
    return ok


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    message_file = Path(argv[1]).resolve()
    if not message_file.is_file():
        print(f"❌ No message file: {message_file}", file=sys.stderr)
        return 2
    return 0 if dry_run(ROOT, message_file) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
