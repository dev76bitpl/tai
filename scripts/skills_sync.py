"""Skill sync from the AI template: compare a project's skills with the template's released
state and copy what is new or outdated, delete what the template retired, keep what the project
changed. Used by `scripts/update-skills.py --sync` and the session-start hook (ADR-006)."""
import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # update-skills.py points it at the project
MANIFEST_PATH = ROOT / "skills-manifest.json"

# Files the sync keeps equal to the template's next to the skills (see sync_from_template).
SHIPPED_FILES = ["scripts/update-skills.py", "scripts/skills_sync.py", "scripts/skills_upstream.py",
                 "scripts/update-from-template.py", ".gitleaksignore"]


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


SKILLS_DIR = ".claude/skills"
LOCAL_SKILLS_LINE = "Pominięte (zmienione lokalnie):"
RETIRED_SKILLS_LINE = "Wycofane w szablonie:"


# Generated next to a skill's scripts and never tracked: they say nothing about the skill's content.
UNTRACKED_PARTS = {"__pycache__"}
UNTRACKED_SUFFIXES = {".pyc", ".pyo"}


def git_blob(file: Path) -> str:
    """The blob id git stores for this file under `* text=auto eol=lf`, without a process.
    A text file (no NUL in the first 8000 bytes, git's own test) has CRLF folded to LF first, so a
    working tree checked out with CRLF matches the template's LF history instead of looking edited."""
    data = file.read_bytes()
    if b"\0" not in data[:8000]:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def skill_blobs(root: Path) -> dict[str, str]:
    """relative path -> blob id for every file of a skill except generated ones (__pycache__, .pyc)."""
    blobs = {}
    for f in root.rglob("*"):
        rel = f.relative_to(root)
        if not f.is_file() or UNTRACKED_PARTS & set(rel.parts) or f.suffix in UNTRACKED_SUFFIXES:
            continue
        blobs[rel.as_posix()] = git_blob(f)
    return blobs


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
    released, mine = skill_blobs(src), skill_blobs(dst)
    if released == mine:
        return "current"
    if history is None:
        return "outdated"
    for rel, blob in mine.items():
        if blob != released.get(rel) and blob not in history.get(f"{SKILLS_DIR}/{name}/{rel}", set()):
            return "local"
    return "outdated"


def off_by_group(template_manifest: dict, project_manifest: dict) -> set[str]:
    """Skills of groups the project left out. select-skills.py records the kept groups in the
    project's `skill_groups`; a skill added later to a group left out must not arrive either (#219).
    The group of a skill is the `group` of its entry in the template's manifest. A project that
    never chose groups gets every group except the template's `opt_in_groups`."""
    kept = project_manifest.get("skill_groups")
    if isinstance(kept, list):
        off = lambda group: group not in kept  # noqa: E731
    else:
        opt_in = set(template_manifest.get("opt_in_groups", []) or [])
        off = lambda group: group in opt_in  # noqa: E731
    return {name for section in ("custom_skills", "skills")
            for name, entry in template_manifest.get(section, {}).items()
            if isinstance(entry, dict) and entry.get("group") and off(entry["group"])}


def retired_state(dst: Path, history: "dict[str, set[str]] | None") -> str:
    """"retired" when every file of a skill the template no longer has is one the template once
    shipped there — safe to delete; otherwise "local" (the project changed it or it is its own).
    Without history nothing counts as shipped, so nothing is deleted."""
    if history is None:
        return "local"
    for rel, blob in skill_blobs(dst).items():
        if blob not in history.get(f"{SKILLS_DIR}/{dst.name}/{rel}", set()):
            return "local"
    return "retired"


def sync_skill_dir(label: str, src: Path, dst: Path, history: "dict[str, set[str]] | None",
                   apply: bool) -> str:
    """Report one skill directory against the template and, with apply, copy it when it is new or
    outdated. Returns its state (see skill_state()); a "local" skill is never touched."""
    state = skill_state(dst.name, src, dst, history)
    if state == "current":
        print(f"  ✅ {label:<25} aktualny")
        return state
    if state == "local":
        print(f"  ! {label:<25} zmieniony lokalnie — porównaj ręcznie, synchronizacja go nie rusza")
        return state
    if state == "new":
        print(f"  + {label:<25} NOWY")
    else:
        src_files, dst_files = collect_files(src), collect_files(dst)
        changed = sum(1 for k, v in src_files.items() if dst_files.get(k) != v)
        added = sum(1 for k in src_files if k not in dst_files)
        print(f"  ~ {label:<25} zmieniony ({changed} plików, +{added} nowych)")
    if apply:
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    return state


def sync_from_template(template_root: Path, apply: bool, history: "dict[str, set[str]] | None" = None) -> None:
    """
    Synchronize skills and manifest from the AI template.

    Copies custom and vendored skills missing or outdated in the project — the template is the
    only place vendored skills are fetched from upstream and reviewed (#221). A skill the project
    changed itself is left alone and listed (needs `history`, see skill_state()).
    Vendored entries in skills-manifest.json follow the template's (commit, checked).
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
    excluded = set(project_manifest.get("excluded_skills", []) or []) | off_by_group(template_manifest, project_manifest)

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

        state = sync_skill_dir(skill_name, src, dst, history, apply)
        if state == "local":
            local_skills.append(skill_name)
        elif state != "current":
            synced += 1
            if apply:
                project_custom[skill_name] = template_custom[skill_name]

    # ── Vendored skills: files come from the template, not from upstream (#221) ──
    print("\n── Vendored skills ─────────────────────────────────────")
    new_vendored = 0
    for skill_name, skill_data in template_vendored.items():
        if skill_name in excluded:
            print(f"  – {skill_name:<25} wyłączony w projekcie")
            continue
        local_path = skill_data.get("local_path", f"{SKILLS_DIR}/{skill_name}")
        src, dst = template_root / local_path, ROOT / local_path
        if not src.exists():
            continue
        state = sync_skill_dir(skill_name, src, dst, history, apply)
        if state == "local":
            local_skills.append(skill_name)
            continue
        if state != "current":
            synced += 1
        if skill_name not in project_vendored:
            new_vendored += 1
        if apply:
            project_vendored[skill_name] = dict(skill_data)

    # ── Retired: in the project's manifest, gone from the template's (#221) ──────
    print("\n── Wycofane w szablonie ────────────────────────────────")
    retired: list[str] = []
    for project_section, template_section in ((project_custom, template_custom), (project_vendored, template_vendored)):
        for skill_name in [n for n in project_section if n not in template_section]:
            entry = project_section[skill_name]
            local_path = entry.get("local_path") if isinstance(entry, dict) else None
            dst = ROOT / (local_path or f"{SKILLS_DIR}/{skill_name}")
            if dst.exists() and retired_state(dst, history) == "local":
                print(f"  ! {skill_name:<25} wycofany w szablonie, ale zmieniony w projekcie — zostaje, porównaj ręcznie")
                local_skills.append(skill_name)
                continue
            print(f"  - {skill_name:<25} wycofany w szablonie — {'usunięty' if apply else 'do usunięcia'}")
            retired.append(skill_name)
            synced += 1
            if apply:
                if dst.exists():
                    shutil.rmtree(dst)
                del project_section[skill_name]
    if not retired:
        print("  ✅ brak")

    # ── Scripts that ride along: the sync itself, its modules, the template updater ──
    # update-from-template.py comes too, so projects older than ADR-006 get it; it changes
    # nothing without --apply, so "guards are never replaced silently" still holds.
    print("\n── Scripts ─────────────────────────────────────────────")
    for rel in SHIPPED_FILES:
        theirs, ours = template_root / rel, ROOT / rel
        if not theirs.exists():
            continue
        if ours.exists() and git_blob(theirs) == git_blob(ours):
            print(f"  ✅ {Path(rel).name:<25} aktualny")
            continue
        print(f"  ~ {Path(rel).name:<25} {'zmieniony' if ours.exists() else 'NOWY'}")
        synced += 1
        if apply:
            ours.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(theirs, ours)

    # ── Save manifest ─────────────────────────────────────────────────────────
    if apply:
        project_manifest["custom_skills"] = project_custom
        project_manifest["skills"] = project_vendored
        save_manifest(project_manifest)

    print(f"\n{'═' * 50}")
    print(f"📊 Podsumowanie:")
    print(f"   Skille do synchronizacji: {synced}")
    print(f"   Nowe skille zewnętrzne: {new_vendored}")
    if retired:
        print(f"   {RETIRED_SKILLS_LINE} {', '.join(retired)}")
    if local_skills:
        # The session-start hook reads this line (session-context.py) — keep its wording.
        print(f"   {LOCAL_SKILLS_LINE} {', '.join(local_skills)}")
    if not apply and synced > 0:
        print(f"\n   Uruchom z --apply żeby zastosować.")
    elif apply:
        print(f"\n   Manifest zaktualizowany.")
