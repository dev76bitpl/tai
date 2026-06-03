#!/usr/bin/env python3
"""
Bootstrap a new project from the AI template.

Two modes:

  --init          Initialize THIS cloned repo as a new project in-place.
                  Removes template meta (tests/, README, this script),
                  resets release versioning (drops template CHANGELOG, manifest
                  → 0.0.0), replaces template git history with a single init
                  commit, and installs pre-commit/commit-msg guards.
                  Use --no-git to skip the git reset + guard install.
                  Run once after: git clone ai my-project && cd my-project

  <dest>          Copy template to a separate new directory.
                  Use when keeping the template repo intact.

Usage:
    python3 scripts/new-project.py --init
    python3 scripts/new-project.py --init --dry-run
    python3 scripts/new-project.py /path/to/new-project
    python3 scripts/new-project.py /path/to/new-project --dry-run
"""
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

# ── What to copy (copy-to-dir mode) ─────────────────────────────────────────

COPY_DIRS = [".claude"]

COPY_FILES = ["CLAUDE.md", "skills-manifest.json"]

COPY_DOCS = [
    "AI_TEMPLATE_NOTES.md",
    "CONVENTIONS.md",
    "DELIVERY_CHECKLIST.md",
    "SETUP.md",
    "SKILLS.md",
    "TESTING.md",
    "UI_GUIDELINES.md",
    "USER_PROFILE.example",
]

SCAFFOLD_DOCS: dict[str, str] = {
    "TASKS.md": """\
# Tasks

> Stan sesji: projekt zainicjalizowany — scope do zdefiniowania.

---

## Backlog

- [ ] Zdefiniuj scope projektu — napisz Claude'owi: `scope`

## In Progress

## Done
""",
    "ROADMAP.md": """\
# Roadmap

<!-- Wygeneruj za pomocą `scope` lub wypełnij ręcznie -->

## Faza 1 — [Nazwa]

**Cel:**

**Zakres:**

**Done when:**

**Zależności:** brak
""",
}

# ── What to remove + replace in --init mode ──────────────────────────────────

README_SCAFFOLD = """\
# [Nazwa projektu]

> Krótki opis — co to jest i dla kogo.

---

## Uruchomienie

```bash
# TODO: uzupełnij
```

## Stack

<!-- TODO: opisz stack -->

## Dokumentacja

- [Scope projektu](docs/PROJECT_SCOPE.md)
- [Konwencje](docs/CONVENTIONS.md)
- [Zadania](docs/TASKS.md)
- [Roadmapa](docs/ROADMAP.md)
"""

# Paths relative to ROOT that are template-only and removed during --init.
# The script itself is removed last (it's added in init_in_place after this list).
TEMPLATE_META: list[str] = [
    "tests",
    "README.md",
    "docs/adr/ADR-001-example.md",
    "docs/SETUP.example.md",
    "docs/TASKS.example.md",
    "docs/ROADMAP.example.md",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def log(label: str, path: str, dry_run: bool) -> None:
    prefix = "  [dry]" if dry_run else "  ✓"
    print(f"{prefix} {label:<12} {path}")


def remove(path: Path, root: Path, dry_run: bool) -> None:
    label = "rmdir" if path.is_dir() else "rm"
    display = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    log(label, display, dry_run)
    if dry_run:
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def copy_dir(src: Path, dst: Path, dry_run: bool) -> None:
    log("dir", str(src.relative_to(ROOT)) + "/", dry_run)
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True)


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    log("file", str(src.relative_to(ROOT)), dry_run)
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def scaffold_file(dst: Path, dest: Path, content: str, dry_run: bool) -> None:
    log("scaffold", str(dst.relative_to(dest)), dry_run)
    if dry_run:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")


def mkdir(path: Path, dest: Path, dry_run: bool) -> None:
    log("mkdir", str(path.relative_to(dest)) + "/", dry_run)
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)
    (path / ".gitkeep").touch()


def _git_remote_url(repo_root: Path) -> str | None:
    """Returns git remote origin URL, or None if unavailable."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    url = result.stdout.strip()
    return url if result.returncode == 0 and url else None


def create_config_json(dest: Path, template_root: Path, dry_run: bool) -> None:
    """Creates .claude/hooks/config.json with ai_template_path pre-filled.

    Prefers git remote URL over local path so config works across machines.
    """
    example_src = template_root / ".claude" / "hooks" / "config.json.example"
    if not example_src.exists():
        return
    log("auto-config", ".claude/hooks/config.json  (ai_template_path pre-filled)", dry_run)
    if dry_run:
        return
    config = json.loads(example_src.read_text(encoding="utf-8"))
    config["ai_template_path"] = _git_remote_url(template_root) or str(template_root)
    if config.get("repos") and isinstance(config["repos"], list):
        config["repos"][0]["name"] = dest.name
        config["repos"][0]["tasks"] = "docs/TASKS.md"
    out = dest / ".claude" / "hooks" / "config.json"
    out.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def create_settings_local(dest: Path, template_root: Path, dry_run: bool) -> None:
    """Creates .claude/settings.local.json with correct interpreter for current OS."""
    example_src = template_root / ".claude" / "settings.local.json.example"
    if not example_src.exists():
        return
    interpreter = "py" if sys.platform == "win32" else "python3"
    log("auto-config", f".claude/settings.local.json  (interpreter: {interpreter})", dry_run)
    if dry_run:
        return
    content = example_src.read_text(encoding="utf-8").replace("INTERPRETER", interpreter)
    out = dest / ".claude" / "settings.local.json"
    out.write_text(content, encoding="utf-8")


def reset_versioning(root: Path, dry_run: bool) -> None:
    """Drop the template's release history so the new project versions from scratch.

    Without this, the project inherits the template's manifest version and CHANGELOG.
    guard_release_tag then blocks the first commit (a declared version with no
    matching GitHub Release). Deleting CHANGELOG.md lets release-please regenerate
    it on the first real release; manifest → 0.0.0 makes that first release start
    clean (first feat → 0.1.0).
    """
    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        remove(changelog, root, dry_run)

    manifest = root / ".release-please-manifest.json"
    if manifest.exists():
        log("reset", ".release-please-manifest.json  → 0.0.0", dry_run)
        if not dry_run:
            manifest.write_text('{\n  ".": "0.0.0"\n}\n', encoding="utf-8")


def _on_rm_error(func, path, _exc_info) -> None:
    """rmtree onerror handler: clear read-only bit (Windows .git pack files) and retry."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def fresh_git_history(root: Path, dry_run: bool) -> None:
    """Replace the template's git history with a single init commit for the project.

    The new repo has no remote and no installed hooks yet, so the init commit is
    unguarded by design — guards apply once the user wires up origin and installs
    pre-commit (see next steps).
    """
    git_dir = root / ".git"
    log("rmdir", ".git  (template history)", dry_run)
    log("git", "init", dry_run)
    log("git", 'commit -m "chore: initialize project from AI template"', dry_run)
    if dry_run:
        return
    if git_dir.exists():
        shutil.rmtree(git_dir, onerror=_on_rm_error)
    try:
        subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore: initialize project from AI template"],
            cwd=str(root), check=True,
        )
    except subprocess.CalledProcessError as exc:
        warn(
            f"git init/commit failed (exit {exc.returncode}). "
            "Cleaning is done; finish git manually:\n"
            "    git init && git add -A && "
            'git commit -m "chore: initialize project from AI template"'
        )


def warn(msg: str) -> None:
    print(f"⚠️  {msg}", file=sys.stderr)


def _resolve_pre_commit() -> list[str] | None:
    """argv prefix to invoke pre-commit — standalone binary or `python -m pre_commit`.

    Falls back to the module form because on Windows `pip install --user` often
    leaves the binary off PATH while `python -m pre_commit` still works.
    """
    if shutil.which("pre-commit"):
        return ["pre-commit"]
    for py in ("python", "python3", "py"):
        if not shutil.which(py):
            continue
        probe = subprocess.run(
            [py, "-m", "pre_commit", "--version"], capture_output=True
        )
        if probe.returncode == 0:
            return [py, "-m", "pre_commit"]
    return None


def install_guards(root: Path, dry_run: bool) -> None:
    """Install pre-commit + commit-msg git hooks so the project is guarded from commit #1.

    Runs after the init commit (the fresh repo defaults to branch main, where
    no-commit-to-branch would otherwise block a guarded init commit). Soft-fails:
    a missing pre-commit warns with the manual command instead of aborting init.
    """
    log("git-hooks", "pre-commit install (pre-commit + commit-msg)", dry_run)
    if dry_run:
        return
    invocation = _resolve_pre_commit()
    if invocation is None:
        warn(
            "pre-commit not found — guards not installed. Install later with:\n"
            "    npm install   (or: pre-commit install "
            "--hook-type pre-commit --hook-type commit-msg)"
        )
        return
    result = subprocess.run(
        [*invocation, "install", "--hook-type", "pre-commit", "--hook-type", "commit-msg"],
        cwd=str(root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        warn(f"pre-commit install failed: {result.stderr.strip()[:300]}")


# ── Init in-place ─────────────────────────────────────────────────────────────

def init_in_place(root: Path, dry_run: bool, do_git: bool = True) -> None:
    """Remove template meta and turn this clone into a clean project directory."""
    print("🚀  new-project.py — INIT IN-PLACE")
    print(f"    Directory: {root}\n")

    print("── Usuwam template meta ────────────────────────────────")
    for name in TEMPLATE_META:
        remove(root / name, root, dry_run)

    print("\n── Reset wersjonowania ─────────────────────────────────")
    reset_versioning(root, dry_run)

    print("\n── README scaffold ─────────────────────────────────────")
    log("scaffold", "README.md", dry_run)
    if not dry_run:
        (root / "README.md").write_text(README_SCAFFOLD, encoding="utf-8")

    print("\n── Claude Code hooks (auto) ────────────────────────────")
    create_config_json(root, root, dry_run)
    create_settings_local(root, root, dry_run)

    # Remove this script before any git commit — it's template-only.
    print("\n── Usuwam template-only skrypt ──────────────────────────")
    remove(root / "scripts" / "new-project.py", root, dry_run)

    if do_git:
        print("\n── Świeża historia git + init commit ────────────────────")
        fresh_git_history(root, dry_run)
        print("\n── Instalacja guardów (pre-commit + commit-msg) ─────────")
        install_guards(root, dry_run)

    if dry_run:
        print("\n✅  Dry-run complete — no files were written.\n")
        return

    print(f"\n✅  Gotowe: {root}\n")
    print("── Następne kroki ──────────────────────────────────────\n")
    if not do_git:
        print("  # 0. Nowa historia git (pominięta przez --no-git)")
        print("  rm -rf .git && git init")
        print("  pre-commit install --hook-type pre-commit --hook-type commit-msg\n")
    print("  # 1. Podłącz zdalne repo")
    print("  git remote add origin <url>\n")
    print("  # 2. Zainstaluj vendored skille")
    print("  python3 scripts/update-skills.py --apply\n")
    print("  # 3. Zdefiniuj scope projektu")
    print("  claude   # napisz: scope\n")
    print("────────────────────────────────────────────────────────\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new project from the AI template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "In-place (after git clone):\n"
            "  python3 scripts/new-project.py --init\n\n"
            "New directory:\n"
            "  python3 scripts/new-project.py ~/Projekty/my-app"
        ),
    )
    parser.add_argument(
        "dest", nargs="?",
        help="Destination directory (omit when using --init)",
    )
    parser.add_argument(
        "--init", action="store_true",
        help="Initialize this cloned repo as a project in-place",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--no-git", action="store_true",
        help="Skip git history reset and init commit (--init only)",
    )
    args = parser.parse_args()

    if args.init:
        init_in_place(ROOT, args.dry_run, do_git=not args.no_git)
        return

    if not args.dest:
        parser.error("dest is required (or use --init for in-place initialization)")

    dest = Path(args.dest).resolve()
    dry_run = args.dry_run

    # Guard: don't overwrite a non-empty directory
    if dest.exists() and any(dest.iterdir()):
        print(f"❌  Destination exists and is not empty: {dest}")
        print("    Remove it first or choose a different path.")
        sys.exit(1)

    mode = "DRY-RUN" if dry_run else "CREATING"
    print(f"🚀  new-project.py — {mode}")
    print(f"    Template:    {ROOT}")
    print(f"    Destination: {dest}\n")

    print("── Directories ─────────────────────────────────────────")
    for d in COPY_DIRS:
        src = ROOT / d
        if src.exists():
            copy_dir(src, dest / d, dry_run)

    print("\n── Root files ──────────────────────────────────────────")
    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            copy_file(src, dest / f, dry_run)

    print("\n── scripts/ ────────────────────────────────────────────")
    scripts_src = ROOT / "scripts"
    scripts_dst = dest / "scripts"
    if not dry_run:
        scripts_dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(scripts_src.rglob("*")):
        if not item.is_file():
            continue
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        if item.name == "new-project.py":
            continue  # template-only, not needed in new projects
        rel = item.relative_to(scripts_src)
        copy_file(item, scripts_dst / rel, dry_run)

    print("\n── docs/ (generic) ─────────────────────────────────────")
    docs_dst = dest / "docs"
    if not dry_run:
        docs_dst.mkdir(parents=True, exist_ok=True)
    for doc in COPY_DOCS:
        src = ROOT / "docs" / doc
        if src.exists():
            copy_file(src, docs_dst / doc, dry_run)

    print("\n── docs/ (scaffolded) ──────────────────────────────────")
    for name, content in SCAFFOLD_DOCS.items():
        scaffold_file(docs_dst / name, dest, content, dry_run)

    mkdir(docs_dst / "adr", dest, dry_run)

    print("\n── Claude Code hooks (auto) ────────────────────────────")
    create_config_json(dest, ROOT, dry_run)
    create_settings_local(dest, ROOT, dry_run)

    if dry_run:
        print("\n✅  Dry-run complete — no files were written.\n")
        return

    print(f"\n✅  Project created: {dest}\n")
    print("── Następne kroki ──────────────────────────────────────\n")
    print(f"  cd {dest}\n")
    print("  git init && git remote add origin <url>\n")
    print("  python3 scripts/update-skills.py --apply\n")
    print("  claude   # napisz: scope\n")
    print("────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
