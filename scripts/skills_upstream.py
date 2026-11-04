"""Fetching vendored skills from their upstream repositories, with a security scan and a diff.
Only the AI template does this (ADR-006, decision 10); projects take vendored skills by sync."""
import difflib
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import skills_sync as base

# Wzorce podejrzane w plikach skryptów (.py, .sh)
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

    local_path = base.ROOT / skill["local_path"]
    exclude = skill.get("exclude", [])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "repo"
        new_commit = clone_repo(skill["repo"], tmp_path)

        if new_commit == "error":
            return False, False

        remote_src = tmp_path / skill["remote_path"] if skill["remote_path"] != "." else tmp_path
        if not remote_src.is_dir():
            # The upstream moved or retired the skill: copying would delete ours and leave nothing.
            print(f"  ⛔ Źródło nie ma już {skill['remote_path']} (przeniesiony albo wycofany) — skill zostaje bez zmian.")
            return True, False

        old_files = base.collect_files(local_path, exclude) if local_path.exists() else {}
        new_files = base.collect_files(remote_src, exclude)

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
