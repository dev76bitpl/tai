#!/usr/bin/env python3
"""
Guard 4: Ocena AI template repo.
Blokuje (exit 2 + stderr) commit dotykający plików generycznych i pyta,
czy zmiana powinna trafić do repo template AI.

FAIL-CLOSED: jeśli nie da się odczytać wiadomości commita, guard BLOKUJE
zamiast po cichu przepuszczać. Czyta wiadomość z -m, heredoc ORAZ z pliku
(-F/--file) — żeby `git commit -F` nie omijał guarda (regresja: typ był
parsowany tylko z -m, więc -F dawał exit 0 = cichy bypass).

Bypass: [no-template] lub [template-done] w wiadomości commita
(wykrywane w -m, heredoc oraz w pliku -F).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_commit_message, get_staged_files, is_foreign_repo, is_git_commit_command, load_config

TEMPLATE_PATTERNS: list[str] = [
    r"^\.claude/",
    r"CLAUDE\.md$",
    r"docs/AI_TEMPLATE",
    r"docs/adr/",
    r"docs/CONVENTIONS",
    r"scripts/",
]

TRIGGER_TYPES = ("feat", "fix", "docs", "refactor")
CONVENTIONAL = r"^(feat|fix|docs|refactor|test|chore|style|perf|ci|build)"


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def commit_type_of(message: str) -> str:
    """Conventional-commit type from message first line, or '' if none."""
    m = re.match(CONVENTIONAL, message.strip())
    return m.group(1) if m else ""


def _block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)
    if is_foreign_repo(command):
        sys.exit(0)

    message = get_commit_message(command)

    # Bypass flags may live in the inline message OR the -F file.
    haystack = command + "\n" + (message or "")
    if "[no-template]" in haystack or "[template-done]" in haystack:
        sys.exit(0)

    config = load_config()
    template_path = config.get("ai_template_path", "<ai_template_path not set in .claude/hooks/config.json>")

    # FAIL-CLOSED: cannot read the message → do not silently pass.
    if message is None:
        _block(
            "❌ [BLOCK] Nie mogę odczytać wiadomości commita.\n\n"
            "  Guard AI-template musi sprawdzić typ i treść commita, ale nie znalazł\n"
            "  jej w komendzie (brak -m / heredoc / -F z czytelnym plikiem).\n\n"
            "  Commituj z -m, heredoc lub -F <plik>, albo dodaj [no-template]/[template-done]."
        )

    staged = get_staged_files(command)
    template_hits = [f for f in staged if any(re.search(p, f) for p in TEMPLATE_PATTERNS)]
    ctype = commit_type_of(message)

    # Touching generic/template files → always force the decision (any commit type).
    if template_hits:
        msg = "❌ [BLOCK] Ocena AI template repo:\n\n"
        msg += "  Pliki potencjalnie generyczne w staged:\n"
        msg += "".join(f"  → {f}\n" for f in template_hits[:10])
        msg += f"\n  Czy powinny trafić do template ({template_path}) ?\n"
        msg += "\n  Tak  → zsynchronizuj, potem dodaj [template-done] i commituj."
        msg += "\n  Nie  → dodaj [no-template] do wiadomości commita."
        _block(msg)

    # No template files touched: nag only on substantive commit types.
    if ctype in TRIGGER_TYPES:
        msg = "❌ [BLOCK] Ocena AI template repo:\n\n"
        msg += f"  Commit typu '{ctype}' — czy coś z tej zmiany jest generyczne\n"
        msg += "  i powinno trafić do template AI?\n"
        msg += "\n  Tak  → zsynchronizuj, potem dodaj [template-done] i commituj."
        msg += "\n  Nie  → dodaj [no-template] do wiadomości commita."
        _block(msg)

    sys.exit(0)


if __name__ == "__main__":
    main()
