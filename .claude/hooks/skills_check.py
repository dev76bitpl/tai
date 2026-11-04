"""Skill checks of the session-start hook (session-context.py): sync with the AI template and
reminders to review skills. Split from session-context.py to keep both under 400 lines (#221);
the hook runs without this module when a partial update leaves it out."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
MONOREPO_ROOT = HOOKS_DIR.parent.parent

sys.path.insert(0, str(HOOKS_DIR))
from stack import resolve_template_path  # noqa: E402


SYNC_HASH_FILE = HOOKS_DIR / ".sync-hash"


def _is_git_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def _remote_head_hash(url: str) -> str | None:
    """Returns HEAD hash of remote repo via ls-remote (no clone)."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", url, "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=6,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.split()[0]
    except Exception:
        pass
    return None


def _last_sync_hash() -> str:
    return SYNC_HASH_FILE.read_text().strip() if SYNC_HASH_FILE.exists() else ""


def _save_sync_hash(h: str) -> None:
    try:
        SYNC_HASH_FILE.write_text(h)
    except Exception:
        pass


def _local_desynced(template_root: Path) -> tuple[list[str], list[str], list[str]]:
    """Returns (missing_custom, outdated_custom, vendored_to_sync) for local template. A vendored
    skill waits when the project lacks it or its manifest commit differs from the template's (#221)."""
    template_manifest_path = template_root / "skills-manifest.json"
    project_manifest_path = MONOREPO_ROOT / "skills-manifest.json"

    if not template_manifest_path.exists() or not project_manifest_path.exists():
        return [], [], []
    try:
        tmpl = json.loads(template_manifest_path.read_text("utf-8"))
        proj = json.loads(project_manifest_path.read_text("utf-8"))
    except Exception:
        return [], [], []

    skills_dir = MONOREPO_ROOT / ".claude" / "skills"
    tmpl_skills_dir = template_root / ".claude" / "skills"

    # Skills the project switched off (scripts/select-skills.py) are not "missing", nor are those of
    # groups it left out — the same rule the sync applies (skills_sync.off_by_group, #219).
    excluded = set(proj.get("excluded_skills", []) or []) | _off_by_group(tmpl, proj)

    missing, outdated = [], []
    for name in tmpl.get("custom_skills", {}):
        if name in excluded:
            continue
        pf = skills_dir / name / "SKILL.md"
        tf = tmpl_skills_dir / name / "SKILL.md"
        if not pf.exists():
            missing.append(name)
        elif tf.exists() and pf.read_text("utf-8") != tf.read_text("utf-8"):
            outdated.append(name)

    proj_v = proj.get("skills", {})
    missing_v = sorted(
        name for name, entry in tmpl.get("skills", {}).items()
        if name not in excluded and (
            name not in proj_v
            or proj_v[name].get("commit") != entry.get("commit")
            or not (MONOREPO_ROOT / entry.get("local_path", f".claude/skills/{name}")).exists()
        )
    )
    return missing, outdated, missing_v


def _off_by_group(tmpl: dict, proj: dict) -> set[str]:
    """skills_sync.off_by_group from the project's scripts; nothing when the project lacks it."""
    path = MONOREPO_ROOT / "scripts" / "skills_sync.py"
    try:
        spec = importlib.util.spec_from_file_location("skills_sync_for_hook", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.off_by_group(tmpl, proj)
    except Exception:
        return set()


def _retired(template_root: Path) -> list[str]:
    """Skills in the project's manifest that the template's manifest no longer has (#221)."""
    try:
        tmpl = json.loads((template_root / "skills-manifest.json").read_text("utf-8"))
        proj = json.loads((MONOREPO_ROOT / "skills-manifest.json").read_text("utf-8"))
    except Exception:
        return []
    names = lambda m: set(m.get("custom_skills", {})) | set(m.get("skills", {}))  # noqa: E731
    return sorted(names(proj) - names(tmpl))


def _load_updater(path: Path):
    """The project's scripts/update-skills.py as a module (it owns the released-snapshot rule)."""
    try:
        spec = importlib.util.spec_from_file_location("update_skills_for_hook", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


# update-skills.py prints this line for skills it left alone because the project changed them.
LOCAL_SKILLS_LINE = "Pominięte (zmienione lokalnie):"


def _skipped_local(stdout: str) -> list[str]:
    for line in stdout.splitlines():
        if LOCAL_SKILLS_LINE in line:
            return [n.strip() for n in line.split(LOCAL_SKILLS_LINE, 1)[1].split(",") if n.strip()]
    return []


def _local_notice(names: list[str]) -> str:
    return (f"⚠️  [t-ai] Skille zmienione w projekcie, inne niż w szablonie: {', '.join(names)}"
            f" — nie nadpisane, porównaj ręcznie (python3 scripts/update-skills.py --sync);"
            f" wersja z szablonu zamiast lokalnej: --sync --adopt <nazwa>")


def check_template_skills_sync(config: dict) -> str | None:
    """Detects desync with t-ai template and auto-syncs if needed."""
    template_path = resolve_template_path(config)
    if not template_path:
        return None

    sync_script = MONOREPO_ROOT / "scripts" / "update-skills.py"
    if not sync_script.exists():
        return None

    # ── Remote URL path ───────────────────────────────────────────────────────
    if _is_git_url(template_path):
        remote_hash = _remote_head_hash(template_path)
        if not remote_hash or remote_hash == _last_sync_hash():
            return None
        result = subprocess.run(
            [sys.executable, str(sync_script), "--sync", "--apply"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            _save_sync_hash(remote_hash)
            skipped = _skipped_local(result.stdout)
            lines = ["📦 [t-ai] Pobrano zmiany z template (remote)"]
            return "\n".join(lines + [_local_notice(skipped)] if skipped else lines)
        err = result.stderr.strip()[:200]
        return f"⚠️  [t-ai] Auto-sync nie powiódł się: {err}"

    # ── Local path ────────────────────────────────────────────────────────────
    template_root = Path(template_path)
    if not template_root.exists():
        return None

    # Compare with the template's released state, not its working directory (#179) — the
    # same rule update-skills.py --sync applies when it copies.
    snapshot: Path | None = None
    updater = _load_updater(sync_script)
    if updater and hasattr(updater, "released_snapshot") and updater.is_git_clone(template_root):
        snapshot, reason = updater.released_snapshot(template_root)
        if not snapshot:
            return f"⚠️  [t-ai] Synchronizacja skilli pominięta: {reason}"
    try:
        missing, outdated, missing_v = _local_desynced(snapshot or template_root)
        retired = _retired(snapshot or template_root)
    finally:
        if snapshot:
            shutil.rmtree(snapshot, ignore_errors=True)
    if not missing and not outdated and not missing_v and not retired:
        return None

    result = subprocess.run(
        [sys.executable, str(sync_script), "--sync", "--apply"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode == 0:
        skipped = _skipped_local(result.stdout)
        taken = [n for n in missing + outdated if n not in skipped]
        details = []
        if taken:
            details.append(f"custom: {', '.join(taken)}")
        if missing_v:
            details.append(f"vendored: {', '.join(missing_v)}")
        removed = [n for n in retired if n not in skipped]
        if removed:
            details.append(f"usunięte (wycofane w szablonie): {', '.join(removed)}")
        lines = [f"📦 [t-ai] Pobrano zmiany z template → {' | '.join(details)}"] if details else []
        if skipped:
            lines.append(_local_notice(skipped))
        return "\n".join(lines) or None
    err = result.stderr.strip()[:200]
    return f"⚠️  [t-ai] Auto-sync nie powiódł się: {err}\n  Uruchom: python3 scripts/update-skills.py --sync --apply"


def check_skills_staleness(config: dict | None = None) -> str | None:
    """Zwraca ostrzeżenie jeśli skills w manifest nie były sprawdzane/przeglądane od X dni."""
    manifest_path = MONOREPO_ROOT / "skills-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    stale_after = manifest.get("stale_after_days", 30)
    # Only the template fetches vendored skills from upstream (#221); a project gets them by sync.
    is_template = bool(config) and config.get("is_template") is True
    vendored = manifest.get("skills", {}) if is_template else {}
    custom = manifest.get("custom_skills", {})

    if not vendored and not custom:
        return None

    from datetime import date, datetime
    today = date.today()

    # Check vendored skills (checked = last update check date)
    oldest_vendored = None
    never_checked_vendored = []
    for name, skill in vendored.items():
        checked = skill.get("checked", "never")
        if checked == "never":
            never_checked_vendored.append(name)
        else:
            try:
                d = datetime.strptime(checked, "%Y-%m-%d").date()
                if oldest_vendored is None or d < oldest_vendored:
                    oldest_vendored = d
            except ValueError:
                never_checked_vendored.append(name)

    # Check custom skills (reviewed = last manual review date)
    oldest_custom = None
    never_reviewed_custom = []
    for name, skill in custom.items():
        reviewed = skill.get("reviewed", "never")
        if reviewed == "never":
            never_reviewed_custom.append(name)
        else:
            try:
                d = datetime.strptime(reviewed, "%Y-%m-%d").date()
                if oldest_custom is None or d < oldest_custom:
                    oldest_custom = d
            except ValueError:
                never_reviewed_custom.append(name)

    warnings = []

    if never_checked_vendored:
        warnings.append(
            f"⚠️  [SKILLS] {len(never_checked_vendored)} vendored skill(ów) nigdy nie sprawdzanych: "
            f"{', '.join(never_checked_vendored)}.\n"
            f"  Uruchom: python3 scripts/update-skills.py"
        )
    elif oldest_vendored:
        days_ago = (today - oldest_vendored).days
        if days_ago >= stale_after:
            warnings.append(
                f"⚠️  [SKILLS] Vendored skille nie były sprawdzane od {days_ago} dni "
                f"(próg: {stale_after} dni).\n"
                f"  Uruchom: python3 scripts/update-skills.py"
            )

    if never_reviewed_custom:
        warnings.append(
            f"⚠️  [SKILLS] {len(never_reviewed_custom)} custom skill(ów) bez daty przeglądu: "
            f"{', '.join(never_reviewed_custom)}.\n"
            f"  Zaktualizuj 'reviewed' w skills-manifest.json po przeglądzie."
        )
    elif oldest_custom:
        days_ago = (today - oldest_custom).days
        if days_ago >= stale_after:
            warnings.append(
                f"⚠️  [SKILLS] Custom skille nie były przeglądane od {days_ago} dni "
                f"(próg: {stale_after} dni).\n"
                f"  Zaktualizuj 'reviewed' w skills-manifest.json po przeglądzie."
            )

    return "\n".join(warnings) if warnings else None
