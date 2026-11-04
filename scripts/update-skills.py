#!/usr/bin/env python3
"""
Sprawdza i aktualizuje zewnętrzne skille z ich repozytoriów źródłowych.

Użycie:
    python3 scripts/update-skills.py              # sprawdź aktualizacje (dry-run)
    python3 scripts/update-skills.py --apply      # sprawdź i zastosuj aktualizacje
    python3 scripts/update-skills.py --skill security   # tylko konkretny skill
    python3 scripts/update-skills.py --scan-only  # tylko skan bezpieczeństwa

    python3 scripts/update-skills.py --sync --apply   # w projekcie: wszystkie skille z szablonu

Domyślnie działa w trybie dry-run — żadne zmiany nie są wprowadzane bez --apply.
Skille zewnętrzne pobiera ze źródeł wyłącznie szablon (tai); projekt dostaje je przez --sync (#221).
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# Windows consoles default to cp1250 — force utf-8 so emoji/PL output never crashes.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "skills-manifest.json"

SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))  # skills_sync, skills_upstream


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
SYNC_PATHS = ["skills-manifest.json", ".claude/skills", "scripts/update-skills.py", "scripts/skills_sync.py",
              "scripts/skills_upstream.py", ".gitleaksignore", "scripts/update-from-template.py"]


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


def is_template_repo() -> bool:
    """True in the AI template itself (`is_template: true` in .claude/hooks/config.json)."""
    try:
        config = json.loads((ROOT / ".claude" / "hooks" / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(config, dict) and config.get("is_template") is True


def sync_module(template_root: Path):
    """skills_sync as the template ships it, pointed at this project. The template's copy runs the
    sync it is about to install, and a project that got only this file from an older sync
    (before the split) still works — the module comes along on --apply (SHIPPED_FILES)."""
    for candidate in (template_root / "scripts" / "skills_sync.py", SCRIPTS / "skills_sync.py"):
        if candidate.is_file():
            break
    else:
        print("❌ Brak scripts/skills_sync.py ani w szablonie, ani w projekcie.")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("skills_sync_for_sync", candidate)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT, module.MANIFEST_PATH = ROOT, MANIFEST_PATH
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description="Aktualizacja zewnętrznych skillów")
    parser.add_argument("--apply", action="store_true", help="Zastosuj aktualizacje (domyślnie dry-run)")
    parser.add_argument("--skill", help="Zaktualizuj tylko wskazany skill")
    parser.add_argument("--scan-only", action="store_true", help="Tylko skan bezpieczeństwa, bez diff")
    parser.add_argument("--sync", action="store_true", help="Synchronizuj skille (własne i zewnętrzne) z ai_template_path")
    parser.add_argument("--full-sync", action="store_true", help="To samo co --sync --apply (zostawione dla starych poleceń)")
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
            history = sync_module(template_root).skill_history(tmp_clone, "HEAD")
        else:
            template_root = template_ref
            if not template_root.exists():
                print(f"❌ Template nie istnieje: {template_root}")
                sys.exit(1)
            if is_git_clone(template_root):
                history = sync_module(template_root).skill_history(template_root, RELEASED_REF)
                tmp_clone, reason = released_snapshot(template_root)
                if not tmp_clone:
                    print(f"❌ {reason}")
                    sys.exit(1)
                print(f"  📌 Źródło: {template_root} w stanie {RELEASED_REF} (katalog roboczy pomijam)")
                template_root = tmp_clone

        try:
            sync_module(template_root).sync_from_template(template_root, apply=args.apply, history=history)
        finally:
            if tmp_clone:
                shutil.rmtree(tmp_clone, ignore_errors=True)

        return

    if not is_template_repo():
        # Vendored skills are fetched from upstream and reviewed in the template only (#221);
        # a project fetching them itself drifts away from what every other project runs.
        print("ℹ️  Skille zewnętrzne aktualizuje szablon (tai), nie projekt.")
        print("   Pobierz je z szablonu: python3 scripts/update-skills.py --sync --apply")
        print("   Nowsza wersja u źródła? Zgłoś w tai — trafi do wszystkich projektów naraz.")
        sys.exit(1)

    import skills_sync as base
    import skills_upstream

    manifest = base.load_manifest()
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
        has_updates, is_safe = skills_upstream.check_skill(name, skill, apply=args.apply)
        if has_updates:
            updates_found += 1
            if not is_safe:
                updates_blocked += 1

    # Dry-run and --scan-only only report. check_skill() stamps `checked` on the manifest, and
    # writing it here left a dirty skills-manifest.json after a run that promised to change nothing.
    if args.apply:
        base.save_manifest(manifest)

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
        print(f"\n   Manifest zaktualizowany: {base.MANIFEST_PATH.name}")


if __name__ == "__main__":
    main()
