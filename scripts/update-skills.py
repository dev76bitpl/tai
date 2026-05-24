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

# Wzorce podejrzane w plikach Markdown (.md)
SUSPICIOUS_MD_PATTERNS = [
    (r"<script", "osadzony tag <script>"),
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
            files[str(rel)] = file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    return files


def scan_file(filename: str, content: str) -> list[str]:
    """Skanuje plik w poszukiwaniu podejrzanych wzorców. Zwraca listę ostrzeżeń."""
    warnings = []
    suffix = Path(filename).suffix.lower()

    patterns = SUSPICIOUS_MD_PATTERNS if suffix == ".md" else SUSPICIOUS_SCRIPT_PATTERNS

    for pattern, description in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja zewnętrznych skillów")
    parser.add_argument("--apply", action="store_true", help="Zastosuj aktualizacje (domyślnie dry-run)")
    parser.add_argument("--skill", help="Zaktualizuj tylko wskazany skill")
    parser.add_argument("--scan-only", action="store_true", help="Tylko skan bezpieczeństwa, bez diff")
    args = parser.parse_args()

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
