#!/usr/bin/env python3
"""
Bootstrap a new project from the AI template.

Copies skills, hooks, scripts, and doc scaffolds to a new directory.
Skips: .git/, README.md, and AI template meta content.

Usage:
    python3 scripts/new-project.py /path/to/new-project
    python3 scripts/new-project.py /path/to/new-project --dry-run
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── What to copy ────────────────────────────────────────────────────────────

# Full directories (symlinks preserved — skills point to src/)
COPY_DIRS = [
    ".claude",
    "src",
]

# Root-level files
COPY_FILES = [
    "CLAUDE.md",
    "skills-manifest.json",
]

# docs/ — generic, reusable content (copy as-is)
COPY_DOCS = [
    "CONVENTIONS.md",
    "DELIVERY_CHECKLIST.md",
    "SETUP.md",
    "SKILLS.md",
    "TESTING.md",
    "UI_GUIDELINES.md",
    "USER_PROFILE.example",
]

# docs/ — project-specific scaffolds (overwrite with minimal content)
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

<!-- Wygeneruj za pomocą `/new-project-scope` lub wypełnij ręcznie -->

## Faza 1 — [Nazwa]

**Cel:**

**Zakres:**

**Done when:**

**Zależności:** brak
""",
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def log(label: str, path: str, dry_run: bool) -> None:
    prefix = "  [dry]" if dry_run else "  ✓"
    print(f"{prefix} {label:<12} {path}")


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


def create_config_json(dest: Path, template_root: Path, dry_run: bool) -> None:
    """Creates .claude/hooks/config.json with ai_template_path pre-filled."""
    example_src = template_root / ".claude" / "hooks" / "config.json.example"
    if not example_src.exists():
        return
    log("auto-config", ".claude/hooks/config.json  (ai_template_path pre-filled)", dry_run)
    if dry_run:
        return
    config = json.loads(example_src.read_text(encoding="utf-8"))
    config["ai_template_path"] = str(template_root)
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


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap a new project from the AI template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python3 scripts/new-project.py ~/Projekty/my-app",
    )
    parser.add_argument("dest", help="Destination directory for the new project")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be copied without making changes",
    )
    args = parser.parse_args()

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

    # 1. Full directories (.claude/ and src/)
    print("── Directories ─────────────────────────────────────────")
    for d in COPY_DIRS:
        src = ROOT / d
        if src.exists():
            copy_dir(src, dest / d, dry_run)

    # 2. Root files
    print("\n── Root files ──────────────────────────────────────────")
    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            copy_file(src, dest / f, dry_run)

    # 3. scripts/ — everything (skip __pycache__ and .pyc)
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
        rel = item.relative_to(scripts_src)
        copy_file(item, scripts_dst / rel, dry_run)

    # 4. docs/ — generic copies
    print("\n── docs/ (generic) ─────────────────────────────────────")
    docs_dst = dest / "docs"
    if not dry_run:
        docs_dst.mkdir(parents=True, exist_ok=True)
    for doc in COPY_DOCS:
        src = ROOT / "docs" / doc
        if src.exists():
            copy_file(src, docs_dst / doc, dry_run)

    # 5. docs/ — scaffolded (project-specific, minimal)
    print("\n── docs/ (scaffolded) ──────────────────────────────────")
    for name, content in SCAFFOLD_DOCS.items():
        scaffold_file(docs_dst / name, dest, content, dry_run)

    # 6. docs/adr/ — empty directory
    mkdir(docs_dst / "adr", dest, dry_run)

    # 7. Auto-configure Claude Code hooks
    print("\n── Claude Code hooks (auto) ────────────────────────────")
    create_config_json(dest, ROOT, dry_run)
    create_settings_local(dest, ROOT, dry_run)

    # ── Done ──────────────────────────────────────────────────────────────

    if dry_run:
        print("\n✅  Dry-run complete — no files were written.\n")
        return

    print(f"\n✅  Project created: {dest}\n")
    print("── Następne kroki ──────────────────────────────────────\n")
    print(f"  cd {dest}\n")
    print("  # 1. Inicjalizuj git")
    print("  git init")
    print("  git remote add origin <url-nowego-repo>\n")
    print("  # 2. Zdefiniuj scope projektu")
    print("  claude   # → /new-project-scope\n")
    print("  # 3. (Opcjonalnie) Dostosuj lint/test commands do swojego stacku")
    print("  # → .claude/hooks/config.json\n")
    print("  # 4. (Opcjonalnie) Zainstaluj guard hooki pre-commit")
    print("  pre-commit install --hook-type pre-commit --hook-type commit-msg\n")
    print("────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
