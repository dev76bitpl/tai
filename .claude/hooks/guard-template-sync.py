#!/usr/bin/env python3
"""
Guard 6: Synchronizacja z AI template repo.
Blokuje (exit 2 + stderr) git commit jeśli:
- plik *.md w projekcie ma sekcję (## lub ###) której brakuje w template, LUB
- plik scripts/dev-guards/*.py w projekcie różni się zawartością od wersji w template.

Zasada: każdy uniwersalny wzorzec wymyślony w projekcie musi trafić do template.
Sekcje project-specific i świadome odejścia od template zostają w projekcie —
przy commicie świadoma decyzja przez bypass [skip-sync].

Konfiguracja w .claude/hooks/config.json (kanoniczny, ADR-002):
{ "ai_template_path": "<lokalna-ścieżka-do-klona-template>" }   # opcjonalne

Model (ADR-002): brak lokalnego klona (brak ścieżki / URL / nieistniejący katalog)
NIE pomija się cicho — bramkuje na CLAUDE.md (sync reguł uniwersalnych, reguła 13a)
z prośbą o [skip-sync] albo przeniesienie do template. Bogate porównanie *.md/guardów
odpala się tylko gdy klon istnieje (auto-weryfikacja dla maintainera).
is_template: true → to repo JEST template'm, sync pomijany.
Trigger: staged pliki zawierają *.md lub scripts/dev-guards/*.py.
Bypass: [skip-sync] w wiadomości commita.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import chdir_to_project_root, get_commit_message, get_staged_files, is_foreign_repo, is_git_commit_command, load_config


def get_command() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("command", "")
    except Exception:
        return ""


def get_section_headers(text: str) -> set[str]:
    """Zwraca wszystkie nagłówki ## i ### z tekstu."""
    headers = set()
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^#{2,3}\s+.+", stripped):
            headers.add(stripped)
    return headers


_URL_PREFIXES = ("http://", "https://", "git@", "ssh://")


def _local_template_root(template_path: str) -> Path | None:
    """Lokalny katalog klona template (ADR-002): URL i nieistniejąca ścieżka → None."""
    if not template_path or template_path.startswith(_URL_PREFIXES):
        return None
    root = Path(template_path)
    return root if root.is_dir() else None


def _touches_claude(staged: list[str]) -> bool:
    return any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged)


def _ack_message() -> str:
    return (
        "❌ [BLOCK] CLAUDE.md zmieniony — potwierdź gdzie ta zmiana należy (reguła 13a).\n\n"
        "   Uniwersalna reguła → przenieś ją też do CLAUDE.md w repo template.\n"
        "   Projektowa / już zsynchronizowana → dodaj [skip-sync] do wiadomości commita.\n\n"
        "   (Brak lokalnego klona template do auto-weryfikacji — ustaw ai_template_path\n"
        "    w .claude/hooks/config.json, jeśli chcesz automatycznego sprawdzania.)"
    )


def main():
    command = get_command()
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    # Bypass flag may live inline (command) OR inside a -F <file> message.
    haystack = command + "\n" + (get_commit_message(command) or "")
    if "[skip-sync]" in haystack:
        sys.exit(0)

    config = load_config()
    if config.get("is_template"):
        sys.exit(0)  # to repo JEST template'm — nie ma czego synchronizować wyżej (ADR-002)

    template_root = _local_template_root(config.get("ai_template_path", ""))
    staged = get_staged_files(command)

    if template_root is None:
        # Brak użytecznego lokalnego klona (brak / URL / nieistniejący katalog).
        # Bogate porównanie *.md/guardów wymaga drzewa roboczego — nie odpala się.
        # Nie pomijaj po cichu (ADR-002): bramkuj na CLAUDE.md (sync reguł uniwersalnych,
        # reguła 13a). Sync pozostałych *.md zostaje bonusem przy klonie, nie bramką,
        # żeby nie blokować każdego commita z docs.
        if _touches_claude(staged):
            print(_ack_message(), file=sys.stderr)
            sys.exit(2)
        sys.exit(0)

    has_md = any(f.endswith(".md") for f in staged)
    has_py = any("scripts/dev-guards/" in f and f.endswith(".py") for f in staged)

    if not has_md and not has_py:
        sys.exit(0)

    project_root = Path.cwd()
    issues: list[str] = []

    if has_md:
        # Sprawdź nagłówki *.md które istnieją w obu repach
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

    if has_py:
        # Sprawdź zawartość scripts/dev-guards/*.py względem template
        guards_dir = project_root / "scripts" / "dev-guards"
        template_guards_dir = template_root / "scripts" / "dev-guards"

        if guards_dir.is_dir() and template_guards_dir.is_dir():
            for project_file in sorted(guards_dir.glob("*.py")):
                if project_file.name == "__init__.py":
                    continue
                rel_path = project_file.relative_to(project_root)
                template_file = template_guards_dir / project_file.name

                if not template_file.exists():
                    issues.append(f"  🐍 {rel_path}: plik jest w projekcie, brakuje w template")
                    continue

                try:
                    project_content = project_file.read_text(encoding="utf-8")
                    template_content = template_file.read_text(encoding="utf-8")
                except Exception as e:
                    issues.append(f"  ⚠️  Błąd odczytu {rel_path}: {e}")
                    continue

                if project_content != template_content:
                    issues.append(f"  🐍 {rel_path}: zawartość różni się od wersji w template")

    if issues:
        msg = "❌ [BLOCK] Desync z AI template repo:\n\n"
        msg += "\n".join(issues)
        msg += "\n\n  Opcje:"
        msg += f"\n  1. Universal? → zsynchronizuj zmiany do template ({template_path}), commit z [template-done]"
        msg += "\n  2. Project-specific / świadome odejście? → bypass [skip-sync] w commicie (z notą w body — co i dlaczego)"
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
