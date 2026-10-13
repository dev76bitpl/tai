#!/usr/bin/env python3
"""Choose which skills this project keeps.

The template ships every skill (WordPress, Laravel, TypeScript, marketing, ...). A project
needs a few of them; the rest is noise for Claude. This script removes the groups the project
does not want and records the choice, so template sync does not bring them back.

  python3 scripts/select-skills.py                  # ask (in a terminal)
  python3 scripts/select-skills.py --list           # show the groups and what is kept now
  python3 scripts/select-skills.py --keep php,ui    # keep these groups, remove the others
  python3 scripts/select-skills.py --all            # keep everything

General skills (scope, adr, api, debug, deploy, git, retro) are not in any group and always stay.
Changing your mind is running it again: a group you add back returns on the next template sync
(`python3 scripts/update-skills.py --sync --apply`, then `--apply` for the vendored ones).

The choice lives in skills-manifest.json: `skill_groups` (kept) and `excluded_skills` (names the
sync must skip — honoured by .claude/hooks/session-context.py and update-skills.py --sync).
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "skills-manifest.json"
CONFIG_PATH = ROOT / ".claude" / "hooks" / "config.json"
SKILLS_DIR = ROOT / ".claude" / "skills"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from start_ui import BOLD, CYAN, DIM, DONE, GREEN, SKIPPED, mark, notice, paint, question_line  # noqa: E402

# name -> label, vendored skills (keys of "skills" in the manifest), template's own skills
# (keys of "custom_skills"). Directories come from the manifest's local_path / the skill name.
GROUPS: dict[str, dict] = {
    "wordpress": {"label": "WordPress / WooCommerce", "custom": [], "vendored": [
        "wp-plugin-development", "wp-theme-development", "wp-security-review",
        "wp-woocommerce-dev", "wp-block-development"]},
    "php": {"label": "PHP / Laravel / Symfony", "custom": ["symfony"],
            "vendored": ["laravel-rules", "php-modernization"]},
    "shops": {"label": "Sklepy (PrestaShop, Shoper)", "custom": ["prestashop", "shoper"], "vendored": []},
    "typescript": {"label": "TypeScript / Next.js", "custom": [],
                   "vendored": ["mastering-typescript", "nextjs-app-router"]},
    "design": {"label": "Projektowanie wyglądu", "custom": [],
               "vendored": ["design-taste-frontend", "redesign-existing-projects"]},
    "ui": {"label": "UI i dostępność", "custom": [], "vendored": ["ui-ux-pro-max", "a11y", "web-quality-skills"]},
    "marketing": {"label": "Marketing i treści", "custom": [], "vendored": ["copywriting", "cro"]},
    "review": {"label": "Przegląd kodu i bezpieczeństwo", "custom": [], "vendored": ["code-review", "security"]},
}

# Groups proposed for a stack (the name scripts/set-stack.py records in config.json).
STACK_DEFAULTS: dict[str, list[str]] = {
    "node": ["typescript", "design", "ui", "review"],
    "laravel": ["php", "design", "ui", "review"],
    "symfony": ["php", "design", "ui", "review"],
    "magento": ["php", "design", "ui", "review"],
    "wordpress": ["wordpress", "php", "design", "ui", "marketing", "review"],
    "prestashop": ["php", "shops", "design", "ui", "review"],
    "rails": ["design", "ui", "review"],
    "python": ["ui", "review"],
    "go": ["ui", "review"],
}


def group_names(group: str) -> list[str]:
    return [*GROUPS[group]["vendored"], *GROUPS[group]["custom"]]


def default_groups(stack: str | None) -> list[str]:
    """Proposed groups for a stack; everything when the stack is unknown."""
    return list(STACK_DEFAULTS.get(stack or "", GROUPS))


def project_stack() -> str | None:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return config.get("stack") if isinstance(config, dict) else None


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def kept_groups(manifest: dict) -> list[str]:
    """Groups kept now: the recorded choice, or all when no choice was made yet."""
    chosen = manifest.get("skill_groups")
    return [g for g in chosen if g in GROUPS] if isinstance(chosen, list) else list(GROUPS)


def skill_dir(manifest: dict, name: str) -> Path | None:
    """Directory of a skill inside .claude/skills, or None when it must not be touched."""
    entry = manifest.get("skills", {}).get(name)
    path = (ROOT / entry["local_path"]) if isinstance(entry, dict) and entry.get("local_path") else SKILLS_DIR / name
    path = path.resolve()
    inside = SKILLS_DIR.resolve() in path.parents
    return path if inside else None


def apply_selection(manifest: dict, keep: list[str]) -> list[str]:
    """Remove the skills of every group not in `keep`; returns the names removed from disk.

    Removed names leave the manifest and go to excluded_skills, so sync skips them. Names of
    kept groups leave excluded_skills — their files return with the next template sync.
    """
    removed: list[str] = []
    excluded: list[str] = []
    for group in GROUPS:
        if group in keep:
            continue
        for name in group_names(group):
            excluded.append(name)
            path = skill_dir(manifest, name)
            if path is not None and path.is_dir():
                shutil.rmtree(path)
                removed.append(name)
            manifest.get("skills", {}).pop(name, None)
            manifest.get("custom_skills", {}).pop(name, None)
    manifest["skill_groups"] = [group for group in GROUPS if group in keep]
    manifest["excluded_skills"] = sorted(excluded)
    return removed


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_answer(answer: str, proposed: list[str]) -> list[str] | None:
    """Groups for a typed answer: empty = proposed, 'w' = all, numbers or names; None = not understood."""
    answer = answer.strip().lower()
    if not answer:
        return list(proposed)
    if answer in ("w", "wszystkie", "all"):
        return list(GROUPS)
    names = list(GROUPS)
    chosen: list[str] = []
    for token in answer.replace(",", " ").split():
        if token.isdigit() and 1 <= int(token) <= len(names):
            group = names[int(token) - 1]
        elif token in GROUPS:
            group = token
        else:
            return None
        if group not in chosen:
            chosen.append(group)
    return [group for group in names if group in chosen]


def print_groups(manifest: dict, highlighted: list[str]) -> None:
    present = set(manifest.get("skills", {})) | set(manifest.get("custom_skills", {}))
    for number, (group, data) in enumerate(GROUPS.items(), start=1):
        on = group in highlighted
        box = paint("●", GREEN, BOLD) if on else paint("○", DIM)
        names = ", ".join(n if n in present else paint(f"{n} (brak)", DIM) for n in group_names(group))
        print(f"  {box} {paint(str(number), CYAN, BOLD)}  {paint(data['label'], BOLD) if on else data['label']}")
        print(f"       {paint(names, DIM)}")


def choose_interactively(manifest: dict) -> list[str] | None:
    """Ask which groups stay; None when the user declines to remove anything."""
    stack = project_stack()
    already = isinstance(manifest.get("skill_groups"), list)
    proposed = kept_groups(manifest) if already else default_groups(stack)
    if already:
        print(paint("  ● = grupy, które projekt ma teraz.", DIM))
    elif stack in STACK_DEFAULTS:
        print(paint(f"  ● = propozycja dla stosu „{stack}”. Skille ogólne zostają zawsze.", DIM))
    else:
        print(paint("  Stos projektu nie jest jeszcze ustawiony, więc proponuję wszystkie grupy.", DIM))
    print_groups(manifest, proposed)
    print()
    while True:
        answer = input(question_line("Które grupy zostają?", "[Enter = ● · w = wszystkie · numery, np. 1 5 6]"))
        keep = parse_answer(answer, proposed)
        if keep is not None:
            break
        print(f"  {mark('✗')} nie rozumiem — podaj numery albo nazwy grup z listy, „w” albo sam Enter")
    going = [name for group in GROUPS if group not in keep for name in group_names(group)
             if (skill_dir(manifest, name) or Path("/nonexistent")).is_dir()]
    if going:
        print(f"\n  Usunę z projektu {len(going)} skilli: {paint(', '.join(going), DIM)}")
        confirm = input(question_line("Usunąć?", "[T/n]")).strip().lower()
        if confirm not in ("", "t", "tak", "y", "yes"):
            return None
    return keep


def report(manifest: dict, removed: list[str]) -> None:
    kept = kept_groups(manifest)
    labels = ", ".join(GROUPS[g]["label"] for g in kept) or "tylko skille ogólne"
    print(f"  {mark(DONE)} Grupy skilli w projekcie: {labels}")
    if removed:
        print(f"  {mark(DONE)} Usunięte: {', '.join(removed)}")
    returning = [name for group in kept for name in group_names(group)
                 if name not in manifest.get("skills", {}) and name not in manifest.get("custom_skills", {})]
    if returning:
        notice(f"Do przywrócenia z szablonu: {', '.join(returning)}")
        print("    python3 scripts/update-skills.py --sync --apply && python3 scripts/update-skills.py --apply")
    print(paint("  Zmiana wyboru: python3 scripts/select-skills.py", DIM))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Choose which skill groups this project keeps.")
    parser.add_argument("--list", action="store_true", help="show the groups and what is kept now")
    parser.add_argument("--keep", metavar="GROUPS", help="comma-separated groups to keep: " + ", ".join(GROUPS))
    parser.add_argument("--all", action="store_true", help="keep every group")
    args = parser.parse_args(argv)

    if not MANIFEST_PATH.is_file():
        print(f"✗ Brak {MANIFEST_PATH.name} — nie ma czego wybierać.", file=sys.stderr)
        return 1
    manifest = load_manifest()

    if args.list:
        print_groups(manifest, kept_groups(manifest))
        return 0
    if args.all:
        keep: list[str] | None = list(GROUPS)
    elif args.keep is not None:
        keep = parse_answer(args.keep, []) if args.keep.strip() else []
        if keep is None:
            parser.error("nieznana grupa w --keep; dostępne: " + ", ".join(GROUPS))
    elif sys.stdin.isatty():
        keep = choose_interactively(manifest)
        if keep is None:
            print(f"  {mark(SKIPPED)} bez zmian — nic nie usunięto")
            return 0
    else:
        print_groups(manifest, kept_groups(manifest))
        print("\n  Bez terminala niczego nie zmieniam. Użyj --keep <grupy> albo --all.")
        return 0

    removed = apply_selection(manifest, keep)
    save_manifest(manifest)
    report(manifest, removed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
