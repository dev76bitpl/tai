#!/usr/bin/env python3
"""
Guard 4: Ocena AI template repo.
Blokuje (exit 2 + stderr) feat/fix/docs/refactor commit i pyta czy zmiana
powinna trafić do repo template AI.

Bypass: [no-template] lub [template-done] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_staged_files, is_foreign_repo, is_git_commit_command, load_config

TEMPLATE_PATTERNS: list[str] = [
    r"^\.claude/",
    r"CLAUDE\.md$",
    r"docs/AI_TEMPLATE",
    r"docs/adr/",
    r"docs/CONVENTIONS",
    r"scripts/",
]

TRIGGER_TYPES = ("feat", "fix", "docs", "refactor")


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def extract_commit_type(command: str) -> str:
    m = re.search(r'-m\s+["\']([^"\']+)', command)
    if not m:
        m = re.search(r"<<['\"]?EOF['\"]?\s*\n([^\n]+)", command)
    if not m:
        # PowerShell heredoc: git commit -m @'\n<first line>\n'@
        m = re.search(r"-m\s+@['\"]?\n([^\n]+)", command)
    if m:
        t = re.match(r"^(feat|fix|docs|refactor|test|chore|style|perf|ci|build)", m.group(1).strip())
        if t:
            return t.group(1)
    return ""


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    if "[no-template]" in command or "[template-done]" in command:
        sys.exit(0)

    if extract_commit_type(command) not in TRIGGER_TYPES:
        sys.exit(0)

    staged = get_staged_files(command)

    template_hits = [f for f in staged if any(re.search(p, f) for p in TEMPLATE_PATTERNS)]

    config = load_config()
    template_path = config.get("ai_template_path", "<ai_template_path not set in .claude/hooks/config.json>")

    msg = "❌ [BLOCK] Ocena AI template repo:\n\n"
    if template_hits:
        msg += "  Pliki potencjalnie generyczne w staged:\n"
        msg += "".join(f"  → {f}\n" for f in template_hits[:10])
        msg += f"\n  Czy powinny trafić do template ({template_path}) ?\n"
    else:
        commit_type = extract_commit_type(command)
        msg += f"  Commit typu '{commit_type}' — czy coś z tej zmiany jest generyczne\n"
        msg += "  i powinno trafić do template AI?\n"

    msg += "\n  Tak  → zsynchronizuj, potem dodaj [template-done] i commituj."
    msg += "\n  Nie  → dodaj [no-template] do wiadomości commita."
    print(msg, file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
