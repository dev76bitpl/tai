#!/usr/bin/env python3
"""
Guard 6: Synchronizacja z AI template repo.
Blokuje (exit 2 + stderr) git commit jeśli w bieżącym projekcie (skolaro)
istnieje sekcja (## lub ###) której brakuje w odpowiadającym pliku w template AI.

Zasada: projekt ⊆ template. To co ląduje w projekcie musi trafić do template.
Projekt może mieć sekcje projektowe (nie trafiają do template — oznaczaj je
nagłówkiem z [projekt] lub [skolaro] żeby guard je pomijał).

Konfiguracja w .claude/hooks/config.json:
{ "ai_template_path": "/home/sabor/Projekty/ai" }

Bez klucza ai_template_path: guard pomija się cicho.
Trigger: tylko gdy staged pliki zawierają *.md.
Bypass: [skip-sync] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_staged_files, load_config, is_foreign_repo


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def get_section_headers(text: str) -> set[str]:
    """Zwraca nagłówki ## i ### z pominięciem sekcji oznaczonych [projekt] lub [skolaro]."""
    headers = set()
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#{2,3}\s+.+", stripped):
            lower = stripped.lower()
            if "[projekt]" in lower or "[skolaro]" in lower:
                continue
            headers.add(stripped)
    return headers


def main():
    chdir_to_project_root()
    command = get_command()

    if "git commit" not in command:
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    if "[skip-sync]" in command:
        sys.exit(0)

    config = load_config()
    template_path = config.get("ai_template_path", "")
    if not template_path:
        sys.exit(0)

    template_root = Path(template_path)
    if not template_root.is_dir():
        print(f"⚠️  [WARN] ai_template_path nie istnieje: {template_path}", file=sys.stderr)
        sys.exit(0)

    staged = get_staged_files(command)

    if not any(f.endswith(".md") for f in staged):
        sys.exit(0)

    project_root = Path.cwd()
    issues: list[str] = []

    # Sprawdź tylko pliki *.md które istnieją w obu repach
    for project_file in sorted(project_root.rglob("*.md")):
        if any(part.startswith(".") for part in project_file.parts[len(project_root.parts):]):
            continue
        if "node_modules" in project_file.parts:
            continue

        rel_path = project_file.relative_to(project_root)
        template_file = template_root / rel_path

        if not template_file.exists():
            continue  # plik tylko w projekcie — OK, może być projektowy

        try:
            project_headers = get_section_headers(project_file.read_text(encoding="utf-8"))
            template_headers = get_section_headers(template_file.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"  ⚠️  Błąd odczytu {rel_path}: {e}")
            continue

        missing = project_headers - template_headers
        for h in sorted(missing):
            issues.append(f"  📝 {rel_path}: sekcja jest w projekcie, brakuje w template  →  {h}")

    if issues:
        msg = "❌ [BLOCK] Desync z AI template repo:\n\n"
        msg += "\n".join(issues)
        msg += "\n\n  Opcje:"
        msg += "\n  1. Dodaj brakujące sekcje do template: /home/sabor/Projekty/ai"
        msg += "\n  2. Oznacz sekcję jako projektową: ## Nazwa [skolaro]"
        msg += "\n  3. Bypass jednorazowy: dodaj [skip-sync] do wiadomości commita."
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
