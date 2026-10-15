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
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
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
        # Blobless, not shallow: the history tells a skill changed in the project from an old release.
        ["git", "clone", "--filter=blob:none", "--quiet", url, str(tmp)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"❌ Nie można pobrać template: {result.stderr.strip()}")
        sys.exit(1)
    return tmp


# A local template clone is read at this ref, never from its working directory: whoever works
# on the template in that directory would otherwise send unfinished, unmerged files to every
# project on the machine (#179). Only what the sync reads is exported.
RELEASED_REF = "origin/main"
# update-from-template.py rides along so projects older than ADR-006 get it; it changes nothing
# without --apply, so the rule "guards are never replaced silently" still holds.
SYNC_PATHS = ["skills-manifest.json", ".claude/skills", "scripts/update-skills.py", ".gitleaksignore",
              "scripts/update-from-template.py"]


def is_git_clone(root: Path) -> bool:
    return (root / ".git").exists()  # a directory in a clone, a file in a worktree


def released_snapshot(root: Path) -> "tuple[Path | None, str]":
    """(temp directory with the template at RELEASED_REF, "") or (None, reason). Caller removes it."""
    def git(*args: str, **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, **kw)

    head = git("rev-parse", "--verify", "-q", f"{RELEASED_REF}^{{commit}}", text=True)
    if head.returncode != 0:
        return None, f"klon szablonu {root} nie ma {RELEASED_REF} (git fetch w szablonie?)"
    listed = git("ls-tree", "--name-only", RELEASED_REF, "--", *SYNC_PATHS, text=True)
    paths = listed.stdout.split()
    if listed.returncode != 0 or not paths:
        return None, f"{RELEASED_REF} w {root} nie ma plików skilli"
    archive = git("archive", "--format=tar", RELEASED_REF, "--", *paths)
    if archive.returncode != 0:
        return None, f"nie udało się odczytać {RELEASED_REF} z {root}"
    tmp = Path(tempfile.mkdtemp(prefix="ai-template-released-"))
    with tempfile.TemporaryFile() as raw:
        raw.write(archive.stdout)
        raw.seek(0)
        with tarfile.open(fileobj=raw) as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(tmp, filter="data")
            else:  # Python without extraction filters; the archive comes from our own repo
                tar.extractall(tmp)
    return tmp, ""


SKILLS_DIR = ".claude/skills"
LOCAL_SKILLS_LINE = "Pominięte (zmienione lokalnie):"


def git_blob(file: Path) -> str:
    """The blob id git gives this file's bytes (`git hash-object --no-filters`), without a process."""
    data = file.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def skill_history(repo: Path, ref: str) -> "dict[str, set[str]] | None":
    """path -> every blob id a skill file ever had up to ref; None when the history cannot be read."""
    out = subprocess.run(["git", "-C", str(repo), "log", "--format=", "--raw", "--no-abbrev", "--no-renames",
                          ref, "--", SKILLS_DIR], capture_output=True)
    if out.returncode != 0:
        return None
    seen: dict[str, set[str]] = {}
    for line in out.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith(":") and "\t" in line:
            meta, path = line.split("\t", 1)
            seen.setdefault(path, set()).update(b for b in meta.split()[2:4] if set(b) != {"0"})
    return seen


def skill_state(name: str, src: Path, dst: Path, history: "dict[str, set[str]] | None") -> str:
    """new / current / outdated / local — "local": the project changed a file the template never had
    in that shape (the same rule as update-from-template.py). Without history every difference
    counts as outdated, as before."""
    if not dst.exists():
        return "new"
    released = {f.relative_to(src).as_posix(): git_blob(f) for f in src.rglob("*") if f.is_file()}
    mine = {f.relative_to(dst).as_posix(): git_blob(f) for f in dst.rglob("*") if f.is_file()}
    if released == mine:
        return "current"
    if history is None:
        return "outdated"
    for rel, blob in mine.items():
        if blob != released.get(rel) and blob not in history.get(f"{SKILLS_DIR}/{name}/{rel}", set()):
            return "local"
    return "outdated"


def find_template_ref() -> "Path | str | None":
    """Returns local Path or git URL, resolved by stack.resolve_template_source().

    Kolejność: $AI_TEMPLATE_PATH > config.local.json > config.json >
    autodetekcja klona obok > publiczny URL template.
    """
    hooks_dir = ROOT / ".claude" / "hooks"
    if not (hooks_dir / "stack.py").is_file():
        return None
    sys.path.insert(0, str(hooks_dir))
    try:
        from stack import resolve_template_path
    except Exception:
        return None
    value = resolve_template_path()
    if not value:
        return None
    return value if is_git_url(value) else Path(value)


def sync_from_template(template_root: Path, apply: bool, history: "dict[str, set[str]] | None" = None) -> None:
    """
    Synchronize custom skills and manifest from the AI template.

    Copies custom skills missing or outdated in the project. A skill the project changed itself
    is left alone and listed (needs `history`, see skill_state()).
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
    # Skills the project switched off (scripts/select-skills.py) — sync must not bring them back.
    excluded = set(project_manifest.get("excluded_skills", []) or [])

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"🔄  update-skills.py --sync — tryb: {mode}")
    print(f"    Template: {template_root}")
    print(f"    Projekt:  {ROOT}\n")

    synced = 0
    local_skills: list[str] = []

    # ── Custom skills ─────────────────────────────────────────────────────────
    print("── Custom skills ───────────────────────────────────────")
    for skill_name in template_custom:
        if skill_name in excluded:
            print(f"  – {skill_name:<25} wyłączony w projekcie")
            continue
        src = template_root / ".claude" / "skills" / skill_name
        dst = ROOT / ".claude" / "skills" / skill_name
        if not src.exists():
            continue

        state = skill_state(skill_name, src, dst, history)
        if state == "current":
            print(f"  ✅ {skill_name:<25} aktualny")
            continue
        if state == "local":
            print(f"  ! {skill_name:<25} zmieniony lokalnie — porównaj ręcznie, synchronizacja go nie rusza")
            local_skills.append(skill_name)
            continue

        src_files = collect_files(src)
        dst_files = collect_files(dst) if dst.exists() else {}
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
        if skill_name in excluded:
            print(f"  – {skill_name:<25} wyłączony w projekcie")
            continue
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

    # ── update-from-template.py: added or refreshed, so projects older than ADR-006 get it ──
    template_updater = template_root / "scripts" / "update-from-template.py"
    project_updater = ROOT / "scripts" / "update-from-template.py"
    if template_updater.exists():
        if not project_updater.exists() or template_updater.read_bytes() != project_updater.read_bytes():
            print(f"  ~ update-from-template.py {'NOWY' if not project_updater.exists() else 'zmieniony'}")
            synced += 1
            if apply:
                shutil.copy2(template_updater, project_updater)
        else:
            print(f"  ✅ update-from-template.py aktualny")

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
    if local_skills:
        # The session-start hook reads this line (session-context.py) — keep its wording.
        print(f"   {LOCAL_SKILLS_LINE} {', '.join(local_skills)}")
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
        history: "dict[str, set[str]] | None" = None
        if isinstance(template_ref, str):
            tmp_clone = clone_template(template_ref)
            template_root = tmp_clone
            history = skill_history(tmp_clone, "HEAD")
        else:
            template_root = template_ref
            if not template_root.exists():
                print(f"❌ Template nie istnieje: {template_root}")
                sys.exit(1)
            if is_git_clone(template_root):
                history = skill_history(template_root, RELEASED_REF)
                tmp_clone, reason = released_snapshot(template_root)
                if not tmp_clone:
                    print(f"❌ {reason}")
                    sys.exit(1)
                print(f"  📌 Źródło: {template_root} w stanie {RELEASED_REF} (katalog roboczy pomijam)")
                template_root = tmp_clone

        try:
            sync_from_template(template_root, apply=args.apply, history=history)
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

    # Dry-run and --scan-only only report. check_skill() stamps `checked` on the manifest, and
    # writing it here left a dirty skills-manifest.json after a run that promised to change nothing.
    if args.apply:
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
