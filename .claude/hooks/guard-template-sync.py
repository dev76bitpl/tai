#!/usr/bin/env python3
"""
Guard 6: Synchronizacja z AI template repo.
Blokuje (exit 2 + stderr) git commit jeśli:
- plik *.md w stage, należący do szablonu, ma sekcję (## lub ###) której brakuje w template, LUB
- plik scripts/dev-guards/*.py w projekcie różni się zawartością od wersji w template.

Do szablonu należą pliki z template-files.json klona (copy + compare_sections). Pozostałe
*.md (README.md, docs/PROJECT_SCOPE.md, docs/TASKS.md...) projekt wypełnia własną treścią,
więc nie są porównywane. Pliki *.md spoza stage też nie (#237, #240).

Zasada: każdy uniwersalny wzorzec wymyślony w projekcie musi trafić do template.
Rozjazd przechodzi tylko z potwierdzeniem w wiadomości commita (sync_ack.py, tai#243, D-014):
- „do tai” → odnośnik `tai#N` do istniejącego issue/PR w repo szablonu (sprawdzane w GitHubie;
  bez gh/sieci przepuszcza z ostrzeżeniem na ekranie),
- „tylko nasze” → `[skip-sync] <powód>` w jednej linii, min. 3 słowa.

Ścieżkę template rozstrzyga stack.resolve_template_source():
$AI_TEMPLATE_PATH > config.local.json > config.json > autodetekcja klona obok > URL.
Wpisywanie ścieżki z konkretnej maszyny do commitowanego configu jest opcjonalne.

Model (ADR-002): brak lokalnego klona (brak ścieżki / URL / nieistniejący katalog)
NIE pomija się cicho — bramkuje na CLAUDE.md (sync reguł uniwersalnych, reguła 13a)
z prośbą o [skip-sync] albo przeniesienie do template. Bogate porównanie *.md/guardów
odpala się tylko gdy klon istnieje (auto-weryfikacja dla maintainera).
is_template: true → to repo JEST template'm, sync pomijany.
Trigger: staged pliki zawierają *.md szablonu lub scripts/dev-guards/*.py.
"""
import fnmatch
import json
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_ack
from stack import chdir_to_project_root, get_commit_message, get_staged_files, is_foreign_repo, is_git_commit_command, load_config, read_command, resolve_template_path

LIST_FILE = "template-files.json"
FALLBACK_PATTERNS = ["CLAUDE.md"]


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


def _matches(path: str, pattern: str) -> bool:
    """Same rule as matches() in scripts/update-from-template.py: '*' never crosses '/'."""
    p, q = PurePosixPath(path), PurePosixPath(pattern)
    return p.parent == q.parent and fnmatch.fnmatchcase(p.name, q.name)


def _template_patterns(template_root: Path) -> list[str]:
    """Paths the template owns, from its template-files.json. Unreadable list → CLAUDE.md only."""
    try:
        spec = json.loads((template_root / LIST_FILE).read_text(encoding="utf-8"))
        patterns = list(spec.get("copy", [])) + list(spec.get("compare_sections", []))
    except (OSError, ValueError, AttributeError, TypeError):
        return FALLBACK_PATTERNS
    return [p for p in patterns if isinstance(p, str)] or FALLBACK_PATTERNS


def _template_md_files(staged: list[str], template_root: Path) -> list[str]:
    """Staged *.md files that belong to the template — the only ones worth comparing."""
    patterns = _template_patterns(template_root)
    return sorted({f for f in staged if f.endswith(".md") and any(_matches(f, p) for p in patterns)})


def _touches_claude(staged: list[str]) -> bool:
    return any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged)


NO_CLONE_ISSUE = (
    "  📝 CLAUDE.md zmieniony — potwierdź, gdzie ta zmiana należy (reguła 13a).\n"
    "     (Brak lokalnego klona szablonu do porównania — ustaw ai_template_path\n"
    "      w .claude/hooks/config.json, jeśli chcesz automatycznego sprawdzania.)"
)


def _block_message(issues: list[str], repo: str, note: str = "", template_root: "Path | None" = None) -> str:
    msg = "❌ [BLOCK] Desync z AI template repo:\n\n" + "\n".join(issues)
    if note:
        msg += f"\n\n  ⛔ {note}"
    msg += "\n\n  Opcje:\n" + sync_ack.options_text(repo)
    if template_root is not None:
        msg += f"\n     (lokalny klon szablonu: {template_root})"
    msg += "\n\n  Zablokowane zostało całe polecenie Bash, także kroki przed `git commit`"
    msg += "\n  (np. zapis pliku z wiadomością) — sprawdź, czy się wykonały."
    return msg


def _md_issues(project_root: Path, template_root: Path, md_files: list[str]) -> list[str]:
    issues = []
    for rel in md_files:
        project_file, template_file = project_root / rel, template_root / rel
        if not project_file.is_file() or not template_file.is_file():
            continue  # usunięty w projekcie albo jeszcze nieobecny w klonie szablonu
        try:
            project_headers = get_section_headers(project_file.read_text(encoding="utf-8"))
            template_headers = get_section_headers(template_file.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"  ⚠️  Błąd odczytu {rel}: {e}")
            continue
        for h in sorted(project_headers - template_headers):
            issues.append(f"  📝 {rel}: sekcja jest w projekcie, brakuje w template  →  {h}")
    return issues


def _guard_issues(project_root: Path, template_root: Path) -> list[str]:
    issues = []
    guards_dir = project_root / "scripts" / "dev-guards"
    template_guards_dir = template_root / "scripts" / "dev-guards"
    if not (guards_dir.is_dir() and template_guards_dir.is_dir()):
        return issues
    for project_file in sorted(guards_dir.glob("*.py")):
        if project_file.name == "__init__.py":
            continue
        rel_path = project_file.relative_to(project_root)
        template_file = template_guards_dir / project_file.name
        if not template_file.exists():
            issues.append(f"  🐍 {rel_path}: plik jest w projekcie, brakuje w template")
            continue
        try:
            same = project_file.read_text(encoding="utf-8") == template_file.read_text(encoding="utf-8")
        except Exception as e:
            issues.append(f"  ⚠️  Błąd odczytu {rel_path}: {e}")
            continue
        if not same:
            issues.append(f"  🐍 {rel_path}: zawartość różni się od wersji w template")
    return issues


def main():
    command = read_command("guard-template-sync")
    chdir_to_project_root(command)

    if not is_git_commit_command(command):
        sys.exit(0)

    if is_foreign_repo(command):
        sys.exit(0)

    config = load_config()
    if config.get("is_template"):
        sys.exit(0)  # to repo JEST template'm — nie ma czego synchronizować wyżej (ADR-002)

    template_source = resolve_template_path(config)
    template_root = _local_template_root(template_source)
    staged = get_staged_files(command)

    if template_root is None:
        # Brak użytecznego lokalnego klona (brak / URL / nieistniejący katalog).
        # Bogate porównanie *.md/guardów wymaga drzewa roboczego — nie odpala się.
        # Nie pomijaj po cichu (ADR-002): bramkuj na CLAUDE.md (sync reguł uniwersalnych,
        # reguła 13a). Sync pozostałych *.md zostaje bonusem przy klonie, nie bramką,
        # żeby nie blokować każdego commita z docs.
        issues = [NO_CLONE_ISSUE] if _touches_claude(staged) else []
    else:
        project_root = Path.cwd()
        issues = _md_issues(project_root, template_root, _template_md_files(staged, template_root))
        if any("scripts/dev-guards/" in f and f.endswith(".py") for f in staged):
            issues += _guard_issues(project_root, template_root)

    if not issues:
        sys.exit(0)

    # The acknowledgment may live inline (command) OR inside a -F <file> message.
    # Checked only for a real desync, so ordinary commits never wait on GitHub.
    message = command + "\n" + (get_commit_message(command) or "")
    repo = sync_ack.repo_slug(template_source)
    ack = sync_ack.acknowledge(message, repo)
    if ack.status == sync_ack.PASS:
        if ack.note:
            # Exit 0 with JSON: the owner sees the warning on screen, the commit goes ahead.
            print(json.dumps({"systemMessage": f"⚠️ guard-template-sync: {ack.note} — przepuszczam."},
                             ensure_ascii=False))
        sys.exit(0)

    print(_block_message(issues, repo, ack.note, template_root), file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
