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
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

# Sibling modules (data and git steps) — importable also when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from new_project_data import (  # noqa: E402
    COPY_DIRS, COPY_DOCS, COPY_FILES, README_SCAFFOLD, SCAFFOLD_DOCS, TEMPLATE_META, TEMPLATE_ONLY_SCRIPTS,
)
from new_project_git import fresh_git_history, install_guards, log, warn  # noqa: E402,F401

# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _load_set_stack():
    """scripts/set-stack.py as a module — it owns the stack table and stays in the project
    (the scope wizard runs it later), while this script deletes itself after --init."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("set_stack", ROOT / "scripts" / "set-stack.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


set_stack = _load_set_stack()


def create_config_json(dest: Path, template_root: Path, dry_run: bool,
                       stack: str | None = None) -> None:
    """Creates .claude/hooks/config.json from the template's example.

    ai_template_path is left as the example placeholder, not auto-filled (ADR-002
    decision 3): it's an optional per-machine path to a local template clone that
    the generator can't know, and the sync guard works without it (acknowledgment
    mode). Auto-filling it was the source of bug A — in --init the project's own
    remote got written as the template path.

    stack is optional here: normally the scope wizard decides it after the interview and
    runs scripts/set-stack.py. Passing --stack applies the same table right away, for
    someone who already knows the stack.
    """
    example_src = template_root / ".claude" / "hooks" / "config.json.example"
    if not example_src.exists():
        return
    preset = set_stack.STACK_PRESETS.get(stack) if stack else None
    suffix = f", stack = {stack}: {', '.join(preset['src_dirs'])}" if preset else ""
    log("auto-config", f".claude/hooks/config.json  (ai_template_path = placeholder{suffix})", dry_run)
    if dry_run:
        return
    config = json.loads(example_src.read_text(encoding="utf-8"))
    if config.get("repos") and isinstance(config["repos"], list):
        config["repos"][0]["name"] = dest.name
        config["repos"][0]["tasks"] = "docs/TASKS.md"
    if preset:
        set_stack.apply_stack(config, stack)
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


def reset_adr_dir(root: Path, dry_run: bool) -> None:
    """Drop the template's own ADRs so the project starts with a clean docs/adr/.

    docs/adr/ in the template plays two roles — a scaffold example for projects
    AND the home for the template's own engineering decisions (ADR-002+). Without
    a reset those internal ADRs leak into every project (they document template
    plumbing the project has no stake in). Mirrors reset_versioning: the project
    gets a clean start. End state — empty docs/adr/ with .gitkeep — matches the
    copy mode (which mkdirs an empty adr/).
    """
    adr_dir = root / "docs" / "adr"
    if not adr_dir.is_dir():
        return
    for adr in sorted(adr_dir.glob("*.md")):
        remove(adr, root, dry_run)
    if dry_run:
        return
    (adr_dir / ".gitkeep").touch()


# ── Init in-place ─────────────────────────────────────────────────────────────

def hand_over_to_setup(root: Path) -> None:
    """Continue with the guided steps (remote, labels, skills, doctor, brief).

    They live in scripts/project-setup.py because this script deletes itself after --init,
    and the steps have to be runnable again after a failed one is fixed. Without a terminal
    project-setup.py only prints the steps.
    """
    setup = root / "scripts" / "project-setup.py"
    if not setup.is_file():
        print("  ⚠ Brak scripts/project-setup.py — dalsze kroki: docs/SETUP.md\n")
        return
    sys.stdout.flush()
    os.chdir(root)
    os.execv(sys.executable, [sys.executable, str(setup)])


def init_in_place(root: Path, dry_run: bool, do_git: bool = True,
                  stack: str | None = None) -> None:
    """Remove template meta and turn this clone into a clean project directory."""
    print("🚀  new-project.py — INIT IN-PLACE")
    print(f"    Directory: {root}\n")

    print("── Usuwam template meta ────────────────────────────────")
    for name in TEMPLATE_META:
        remove(root / name, root, dry_run)

    print("\n── Reset wersjonowania ─────────────────────────────────")
    reset_versioning(root, dry_run)

    print("\n── Reset docs/adr (czysty start) ───────────────────────")
    reset_adr_dir(root, dry_run)

    print("\n── README scaffold ─────────────────────────────────────")
    log("scaffold", "README.md", dry_run)
    if not dry_run:
        (root / "README.md").write_text(README_SCAFFOLD, encoding="utf-8")

    print("\n── Claude Code hooks (auto) ────────────────────────────")
    create_config_json(root, root, dry_run, stack)
    create_settings_local(root, root, dry_run)

    # Remove this script before any git commit — it's template-only.
    print("\n── Usuwam template-only skrypt ──────────────────────────")
    for name in TEMPLATE_ONLY_SCRIPTS:
        remove(root / "scripts" / name, root, dry_run)

    if do_git:
        print("\n── Świeża historia git + init commit ────────────────────")
        fresh_git_history(root, dry_run)
        print("\n── Instalacja guardów (pre-commit + commit-msg) ─────────")
        install_guards(root, dry_run)

    if dry_run:
        print("\n✅  Dry-run complete — no files were written.\n")
        return

    print(f"\n✅  Gotowe: {root}\n")
    if not do_git:
        print("  Historia git szablonu została (--no-git). Nową założysz tak:")
        print("  rm -rf .git && git init -b main")
        print("  pre-commit install --hook-type pre-commit --hook-type commit-msg\n")
    hand_over_to_setup(root)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new project from the AI template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "In-place (after git clone):\n"
            "  python3 scripts/new-project.py --init\n"
            "  python3 scripts/new-project.py --init --stack laravel\n\n"
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
    parser.add_argument(
        "--stack", choices=list(set_stack.STACK_PRESETS), metavar="STACK",
        help="Optional. Project stack: " + ", ".join(set_stack.STACK_PRESETS) + ". Sets the code "
             "directories and platform ADR patterns for the commit guards right away. Without "
             "it the scope wizard sets them after its interview (scripts/set-stack.py)",
    )
    args = parser.parse_args()

    if not args.init and not args.dest:
        parser.error("dest is required (or use --init for in-place initialization)")

    stack = args.stack

    if args.init:
        init_in_place(ROOT, args.dry_run, do_git=not args.no_git, stack=stack)
        return

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
        if item.name in TEMPLATE_ONLY_SCRIPTS:
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
    create_config_json(dest, ROOT, dry_run, stack)
    create_settings_local(dest, ROOT, dry_run)

    if dry_run:
        print("\n✅  Dry-run complete — no files were written.\n")
        return

    print(f"\n✅  Project created: {dest}\n")
    hand_over_to_setup(dest)


if __name__ == "__main__":
    main()
