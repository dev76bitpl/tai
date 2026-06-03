#!/usr/bin/env python3
"""
Sprawdza i aktualizuje zewnętrzne skille z ich repozytoriów źródłowych.

Użycie:
    python3 scripts/update-skills.py              # sprawdź aktualizacje (dry-run)
    python3 scripts/update-skills.py --apply      # sprawdź i zastosuj aktualizacje
    python3 scripts/update-skills.py --skill security   # tylko konkretny skill
    python3 scripts/update-skills.py --scan-only  # tylko skan bezpieczeństwa

Domyślnie działa w trybie dry-run — żadne zmiany nie są wprowadzane bez --apply.
"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

# Windows consoles default to cp1250 — force utf-8 so emoji/PL output never crashes.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "skills-manifest.json"

# Wzorce podejrzane w plikach skryptów (.py, .sh)
SUSPICIOUS_SCRIPT_PATTERNS = [
    (r"os\.system\s*\(", "wykonanie komendy shell (os.system)"),
    (r"subprocess\.(run|call|Popen|check_output)\s*\(", "wywołanie subprocess"),
    (r"\beval\s*\(", "dynamiczne wykonanie kodu (eval)"),
    (r"\bexec\s*\(", "dynamiczne wykonanie kodu (exec)"),
    (r"__import__\s*\(", "dynamiczny import"),
    (r"curl\s+https?://(?!raw\.githubusercontent\.com|github\.com)", "curl do nieznanego URL"),
    (r"wget\s+https?://(?!raw\.githubusercontent\.com|github\.com)", "wget do nieznanego URL"),
    (r"requests\.(get|post)\s*\(\s*['\"]https?://(?!api\.github\.com)", "request HTTP do nieznanego URL"),
]

# Wzorce HTML/kodu w plikach Markdown — skanowane PO usunięciu bloków kodu.
# <script> w przykładzie kodu to false positive; poza kodem to realne zagrożenie.
SUSPICIOUS_MD_CODE_PATTERNS = [
    (r"<script", "osadzony tag <script>"),
]

# Wzorce prompt injection w plikach Markdown — skanowane BEZ usuwania bloków kodu.
# Claude czyta całą zawartość pliku, łącznie z blokami kodu — ukrycie injection
# w bloku ``` nie czyni go nieszkodliwym.
SUSPICIOUS_MD_INJECTION_PATTERNS = [
    (r"ignore\s+(previous|above|all)\s+instructions", "próba prompt injection"),
    (r"disregard\s+(previous|above|all)", "próba prompt injection"),
    (r"you\s+are\s+now\s+a", "próba zmiany roli AI"),
    (r"new\s+instructions\s*:", "próba nadpisania instrukcji"),
]


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        print("❌ Brak skills-manifest.json w katalogu projektu.")
        sys.exit(1)
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def clone_repo(repo_url: str, target_dir: Path) -> str:
    """Klonuje repo do katalogu tymczasowego. Zwraca hash HEAD."""
    print(f"  ↓ Pobieranie {repo_url}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", "--quiet", repo_url, str(target_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Błąd klonowania: {result.stderr.strip()}")
        return "error"

    hash_result = subprocess.run(
        ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return hash_result.stdout.strip()


def collect_files(path: Path, exclude: list[str] | None = None) -> dict[str, str]:
    """Zbiera pliki z katalogu jako {względna_ścieżka: zawartość}."""
    exclude_set = set(exclude or [])
    files = {}
    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(path)
        if any(part in exclude_set for part in rel.parts):
            continue
        try:
            # as_posix() keeps manifest keys forward-slashed on every OS — str(rel)
            # would emit backslashes on Windows, drifting the manifest per platform.
            files[rel.as_posix()] = file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return files


def strip_md_code_blocks(content: str) -> str:
    """Removes fenced (```) and inline (`) code from markdown before security scanning.

    Patterns inside code blocks are examples, not executable content — scanning them
    produces false positives (e.g. <script> in an XSS guide).
    """
    # fenced blocks: ```...``` (multiline, non-greedy)
    content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    # inline code: `...` (single line)
    content = re.sub(r"`[^`\n]+`", "", content)
    return content


def scan_file(filename: str, content: str) -> list[str]:
    """Skanuje plik w poszukiwaniu podejrzanych wzorców. Zwraca listę ostrzeżeń."""
    warnings = []
    suffix = Path(filename).suffix.lower()

    if suffix == ".md":
        # HTML/code patterns: scan stripped content — <script> in a code example is a false positive
        stripped = strip_md_code_blocks(content)
        for pattern, description in SUSPICIOUS_MD_CODE_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                warnings.append(f"    ⚠️  {filename}: {description}")
        # Injection patterns: scan raw content — Claude reads code blocks too
        for pattern, description in SUSPICIOUS_MD_INJECTION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"    ⚠️  {filename}: {description}")
    else:
        for pattern, description in SUSPICIOUS_SCRIPT_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"    ⚠️  {filename}: {description}")

    return warnings


def diff_files(old: dict[str, str], new: dict[str, str]) -> list[str]:
    """Generuje czytelny diff między dwoma zestawami plików."""
    lines = []
    all_keys = sorted(set(old) | set(new))

    for key in all_keys:
        if key not in old:
            lines.append(f"\n  + NOWY PLIK: {key}")
            new_lines = new[key].splitlines()[:10]
            for line in new_lines:
                lines.append(f"    + {line}")
            if len(new[key].splitlines()) > 10:
                lines.append(f"    ... (+{len(new[key].splitlines()) - 10} linii)")
        elif key not in new:
            lines.append(f"\n  - USUNIĘTY PLIK: {key}")
        else:
            if old[key] != new[key]:
                diff = list(difflib.unified_diff(
                    old[key].splitlines(),
                    new[key].splitlines(),
                    fromfile=f"a/{key}",
                    tofile=f"b/{key}",
                    lineterm="",
                    n=3,
                ))
                if diff:
                    lines.append(f"\n  ~ ZMIENIONY: {key}")
                    for line in diff[2:25]:  # pomiń nagłówki, max 25 linii
                        lines.append(f"    {line}")
                    if len(diff) > 25:
                        lines.append(f"    ... ({len(diff) - 25} linii pominięto)")

    return lines


def check_skill(
    name: str,
    skill: dict,
    apply: bool,
    verbose: bool = True,
) -> tuple[bool, bool]:
    """
    Sprawdza jeden skill pod kątem aktualizacji i bezpieczeństwa.
    Zwraca (has_updates, is_safe).
    """
    print(f"\n{'─' * 50}")
    print(f"🔍 Skill: {name}")
    print(f"   Źródło: {skill['repo']}")
    print(f"   Ostatnio sprawdzony: {skill.get('checked', 'never')}")

    local_path = ROOT / skill["local_path"]
    exclude = skill.get("exclude", [])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "repo"
        new_commit = clone_repo(skill["repo"], tmp_path)

        if new_commit == "error":
            return False, False

        remote_src = tmp_path / skill["remote_path"] if skill["remote_path"] != "." else tmp_path

        old_files = collect_files(local_path, exclude) if local_path.exists() else {}
        new_files = collect_files(remote_src, exclude)

        # Skan bezpieczeństwa nowych plików
        all_warnings: list[str] = []
        for filename, content in new_files.items():
            all_warnings.extend(scan_file(filename, content))

        # Skan plików które się zmieniły
        changed_files = {k: v for k, v in new_files.items() if old_files.get(k) != v}

        if all_warnings:
            print(f"\n  🚨 SKAN BEZPIECZEŃSTWA — znaleziono podejrzane wzorce:")
            for w in all_warnings:
                print(w)
            print()

        old_commit = skill.get("commit", "unknown")
        has_updates = new_commit != old_commit or bool(changed_files)

        if not has_updates:
            print(f"  ✅ Aktualny (commit: {new_commit[:8]})")
            skill["checked"] = str(date.today())
            return False, not bool(all_warnings)

        print(f"  📦 Dostępna aktualizacja:")
        print(f"     Zainstalowany: {old_commit[:8] if old_commit != 'unknown' else 'nieznany'}")
        print(f"     Najnowszy:     {new_commit[:8]}")
        print(f"     Zmienionych plików: {len(changed_files)}")

        # Pokaż diff
        diff_lines = diff_files(old_files, new_files)
        if diff_lines:
            print("\n  📋 Diff:")
            for line in diff_lines:
                print(line)

        is_safe = not bool(all_warnings)

        if not is_safe:
            print("\n  ⛔ Aktualizacja zablokowana — znaleziono podejrzane wzorce.")
            print("     Przejrzyj diff ręcznie i zastosuj aktualizację manualnie jeśli bezpieczna.")
            return True, False

        if apply:
            print(f"\n  ⬆️  Aktualizuję {name}...")
            if local_path.exists():
                shutil.rmtree(local_path)
            shutil.copytree(remote_src, local_path, ignore=shutil.ignore_patterns(*exclude) if exclude else None)
            skill["commit"] = new_commit
            skill["checked"] = str(date.today())
            print(f"  ✅ Zaktualizowano do {new_commit[:8]}")
        else:
            print(f"\n  ℹ️  Dry-run — uruchom z --apply żeby zastosować.")
            skill["checked"] = str(date.today())
            skill["commit"] = new_commit  # zapamiętaj hash nawet w dry-run

        return True, True


def is_git_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def clone_template(url: str) -> Path:
    """Shallow-clone template repo to a temp dir. Caller must remove it."""
    tmp = Path(tempfile.mkdtemp(prefix="ai-template-"))
    print(f"  📥 Klonuję template z {url}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", "--quiet", url, str(tmp)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"❌ Nie można pobrać template: {result.stderr.strip()}")
        sys.exit(1)
    return tmp


def find_template_ref() -> "Path | str | None":
    """Returns local Path or git URL from .claude/hooks/config.json."""
    config_path = ROOT / ".claude" / "hooks" / "config.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        value = config.get("ai_template_path", "")
        if not value:
            return None
        return value if is_git_url(value) else Path(value)
    except Exception:
        return None


def sync_from_template(template_root: Path, apply: bool) -> None:
    """
    Synchronize custom skills and manifest from the AI template.

    Copies custom skills missing or outdated in the project.
    Updates skills-manifest.json with any new vendored skill entries.
    Optionally copies the latest update-skills.py script itself.
    """
    template_manifest_path = template_root / "skills-manifest.json"
    if not template_manifest_path.exists():
        print(f"❌ Brak skills-manifest.json w template: {template_root}")
        sys.exit(1)

    template_manifest = json.loads(template_manifest_path.read_text(encoding="utf-8"))
    project_manifest = (
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if MANIFEST_PATH.exists()
        else {"skills": {}, "custom_skills": {}}
    )

    template_custom = template_manifest.get("custom_skills", {})
    project_custom = project_manifest.get("custom_skills", {})
    template_vendored = template_manifest.get("skills", {})
    project_vendored = project_manifest.get("skills", {})

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"🔄  update-skills.py --sync — tryb: {mode}")
    print(f"    Template: {template_root}")
    print(f"    Projekt:  {ROOT}\n")

    synced = 0
    skipped = 0

    # ── Custom skills ─────────────────────────────────────────────────────────
    print("── Custom skills ───────────────────────────────────────")
    for skill_name in template_custom:
        src = template_root / ".claude" / "skills" / skill_name
        dst = ROOT / ".claude" / "skills" / skill_name
        if not src.exists():
            continue

        src_files = collect_files(src)
        dst_files = collect_files(dst) if dst.exists() else {}

        if src_files == dst_files:
            print(f"  ✅ {skill_name:<25} aktualny")
            continue

        if not dst_files:
            print(f"  + {skill_name:<25} NOWY")
        else:
            changed = sum(1 for k, v in src_files.items() if dst_files.get(k) != v)
            added = sum(1 for k in src_files if k not in dst_files)
            print(f"  ~ {skill_name:<25} zmieniony ({changed} plików, +{added} nowych)")

        synced += 1
        if apply:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            project_custom[skill_name] = template_custom[skill_name]

    # ── Vendored skill entries (manifest only, no GitHub fetch) ───────────────
    print("\n── Vendored skills (manifest) ──────────────────────────")
    new_vendored = 0
    for skill_name, skill_data in template_vendored.items():
        if skill_name not in project_vendored:
            print(f"  + {skill_name:<25} NOWY wpis w manifeście")
            new_vendored += 1
            if apply:
                entry = dict(skill_data)
                entry["commit"] = "unknown"
                entry["checked"] = "never"
                project_vendored[skill_name] = entry
        else:
            print(f"  ✅ {skill_name:<25} w manifeście")

    # ── update-skills.py script itself ───────────────────────────────────────
    print("\n── Scripts ─────────────────────────────────────────────")
    template_script = template_root / "scripts" / "update-skills.py"
    project_script = ROOT / "scripts" / "update-skills.py"
    if template_script.exists() and project_script.exists():
        if template_script.read_text(encoding="utf-8") != project_script.read_text(encoding="utf-8"):
            print(f"  ~ update-skills.py        zmieniony")
            synced += 1
            if apply:
                shutil.copy2(template_script, project_script)
        else:
            print(f"  ✅ update-skills.py        aktualny")

    # ── .gitleaksignore ──────────────────────────────────────────────────────
    template_ignore = template_root / ".gitleaksignore"
    project_ignore = ROOT / ".gitleaksignore"
    if template_ignore.exists():
        if not project_ignore.exists() or template_ignore.read_text("utf-8") != project_ignore.read_text("utf-8"):
            print(f"  ~ .gitleaksignore         {'NOWY' if not project_ignore.exists() else 'zmieniony'}")
            synced += 1
            if apply:
                shutil.copy2(template_ignore, project_ignore)
        else:
            print(f"  ✅ .gitleaksignore         aktualny")

    # ── Save manifest ─────────────────────────────────────────────────────────
    if apply:
        project_manifest["custom_skills"] = project_custom
        project_manifest["skills"] = project_vendored
        save_manifest(project_manifest)

    print(f"\n{'═' * 50}")
    print(f"📊 Podsumowanie:")
    print(f"   Custom skills do synchronizacji: {synced}")
    print(f"   Nowe wpisy vendored w manifeście: {new_vendored}")
    if not apply and (synced > 0 or new_vendored > 0):
        print(f"\n   Uruchom z --apply żeby zastosować.")
        if new_vendored > 0:
            print(f"   Potem: python3 scripts/update-skills.py --apply  (pobierze vendored skille z GitHub)")
    elif apply:
        print(f"\n   Manifest zaktualizowany.")
        if new_vendored > 0:
            print(f"   Uruchom teraz: python3 scripts/update-skills.py --apply  (pobierze nowe vendored skille)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja zewnętrznych skillów")
    parser.add_argument("--apply", action="store_true", help="Zastosuj aktualizacje (domyślnie dry-run)")
    parser.add_argument("--skill", help="Zaktualizuj tylko wskazany skill")
    parser.add_argument("--scan-only", action="store_true", help="Tylko skan bezpieczeństwa, bez diff")
    parser.add_argument("--sync", action="store_true", help="Synchronizuj custom skille z ai_template_path")
    parser.add_argument("--full-sync", action="store_true", help="--sync --apply + pobierz vendored skille z GitHub")
    args = parser.parse_args()

    if args.full_sync:
        args.sync = True
        args.apply = True

    if args.sync:
        template_ref = find_template_ref()
        if not template_ref:
            print("❌ Brak ai_template_path w .claude/hooks/config.json")
            print("   Ustaw ścieżkę lokalną lub git URL repozytorium AI template.")
            sys.exit(1)

        tmp_clone: Path | None = None
        if isinstance(template_ref, str):
            tmp_clone = clone_template(template_ref)
            template_root = tmp_clone
        else:
            template_root = template_ref
            if not template_root.exists():
                print(f"❌ Template nie istnieje: {template_root}")
                sys.exit(1)

        try:
            sync_from_template(template_root, apply=args.apply)
        finally:
            if tmp_clone:
                shutil.rmtree(tmp_clone, ignore_errors=True)

        if not args.full_sync:
            return
        print(f"\n{'═' * 50}")
        print(f"🛠️  Pobieranie vendored skillów z GitHub...\n")

    manifest = load_manifest()
    skills = manifest.get("skills", {})

    if args.skill and args.skill not in skills:
        print(f"❌ Nieznany skill: {args.skill}")
        print(f"   Dostępne: {', '.join(skills.keys())}")
        sys.exit(1)

    target_skills = {args.skill: skills[args.skill]} if args.skill else skills

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"🛠️  update-skills.py — tryb: {mode}")
    print(f"   Sprawdzam {len(target_skills)} skill(ów)...\n")

    updates_found = 0
    updates_blocked = 0

    for name, skill in target_skills.items():
        has_updates, is_safe = check_skill(name, skill, apply=args.apply)
        if has_updates:
            updates_found += 1
            if not is_safe:
                updates_blocked += 1

    save_manifest(manifest)

    print(f"\n{'═' * 50}")
    print(f"📊 Podsumowanie:")
    print(f"   Sprawdzono: {len(target_skills)} skill(ów)")
    print(f"   Aktualizacji dostępnych: {updates_found}")
    if updates_blocked:
        print(f"   ⛔ Zablokowanych (bezpieczeństwo): {updates_blocked}")
    if not args.apply and updates_found > updates_blocked:
        safe_updates = updates_found - updates_blocked
        print(f"\n   Uruchom z --apply żeby zastosować {safe_updates} bezpieczną aktualizację.")
    elif args.apply:
        print(f"\n   Manifest zaktualizowany: {MANIFEST_PATH.name}")


if __name__ == "__main__":
    main()
