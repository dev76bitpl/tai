#!/usr/bin/env python3
"""
UserPromptSubmit hook: kontekst na start sesji.
Na pierwszej wiadomości sesji:
- czyta docs/TASKS.md z repozytoriów skonfigurowanych w config.json (klucz "repos")
- porównuje .claude/hooks/*.py z ai_template_path — ostrzega o desyncu
Kolejne wiadomości tej samej sesji: hook nie odpala (marker w /tmp).

config.json (wymagane pola):
  "repos": [{"name": "grupavist-fe", "tasks": "grupavist-fe/docs/TASKS.md"}, ...]
  "ai_template_path": "/ścieżka/do/template"  (opcjonalne — bez niego diff pominięty)
"""
import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HOOKS_DIR = Path(__file__).resolve().parent
MONOREPO_ROOT = HOOKS_DIR.parent.parent
SESSION_DIR = Path(tempfile.gettempdir()) / "gv-claude-sessions"


def load_config() -> dict:
    config_path = HOOKS_DIR / "config.json"
    if config_path.is_file():
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_session_id() -> str:
    try:
        data = json.load(sys.stdin)
        return data.get("session_id", "")
    except Exception:
        return ""


def extract_open_tasks(content: str, max_detail_lines: int = 3) -> str:
    lines = content.splitlines()
    parts: list[str] = []
    current_section = ""
    last_section_added = ""
    i = 0
    checkbox_found = False

    # Mode 1: checkbox format (- [ ])
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
        if stripped.startswith("- [ ]"):
            checkbox_found = True
            if current_section != last_section_added:
                parts.append(f"\n**{current_section}**")
                last_section_added = current_section
            task_lines = [line]
            j = i + 1
            detail_count = 0
            while j < len(lines) and detail_count < max_detail_lines:
                next_line = lines[j]
                if not next_line.strip():
                    break
                if next_line.lstrip().startswith("- ["):
                    break
                task_lines.append(next_line)
                detail_count += 1
                j += 1
            parts.append("\n".join(task_lines))
        i += 1

    if checkbox_found:
        return "\n".join(parts).strip()

    # Mode 2: ### heading + **Status:** format (fallback dla BE-style TASKS.md)
    parts = []
    current_section = ""
    last_section_added = ""
    i = 0
    completed_statuses = {"Completed", "Done"}
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            current_section = stripped.lstrip("#").strip()
        elif stripped.startswith("### "):
            task_name = stripped.lstrip("#").strip()
            if task_name.startswith("✅"):
                i += 1
                continue
            status = ""
            for j in range(i + 1, min(i + 6, len(lines))):
                next_stripped = lines[j].strip()
                if next_stripped.startswith("**Status:**"):
                    status = next_stripped.replace("**Status:**", "").strip()
                    break
            if status and any(s in status for s in completed_statuses):
                i += 1
                continue
            if current_section != last_section_added:
                parts.append(f"\n**{current_section}**")
                last_section_added = current_section
            suffix = f" ({status})" if status else ""
            parts.append(f"- [ ] {task_name}{suffix}")
        i += 1

    return "\n".join(parts).strip()


def read_tasks(config: dict) -> list[tuple[str, str]]:
    result = []
    for repo in config.get("repos", []):
        name = repo.get("name", "")
        tasks_rel = repo.get("tasks", "")
        if not name or not tasks_rel:
            continue
        path = MONOREPO_ROOT / tasks_rel
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            open_tasks = extract_open_tasks(content)
            if open_tasks:
                result.append((name, open_tasks))
    return result


def check_template_sync(config: dict) -> list[str]:
    """Zwraca listę plików .py które różnią się między hooks/ a template."""
    template_path = config.get("ai_template_path", "")
    if not template_path:
        return []

    template_hooks = Path(template_path) / ".claude" / "hooks"
    if not template_hooks.is_dir():
        return []

    diffs = []
    for project_file in sorted(HOOKS_DIR.glob("*.py")):
        template_file = template_hooks / project_file.name
        if not template_file.exists():
            diffs.append(f"  + {project_file.name}  (brak w template)")
            continue
        if project_file.read_text(encoding="utf-8") != template_file.read_text(encoding="utf-8"):
            diffs.append(f"  ~ {project_file.name}  (różni się od template)")

    for template_file in sorted(template_hooks.glob("*.py")):
        if not (HOOKS_DIR / template_file.name).exists():
            diffs.append(f"  - {template_file.name}  (tylko w template, brak w projekcie)")

    return diffs


def check_skills_staleness() -> str | None:
    """Zwraca ostrzeżenie jeśli skills w manifest nie były sprawdzane/przeglądane od X dni."""
    manifest_path = MONOREPO_ROOT / "skills-manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    stale_after = manifest.get("stale_after_days", 30)
    vendored = manifest.get("skills", {})
    custom = manifest.get("custom_skills", {})

    if not vendored and not custom:
        return None

    from datetime import date
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


def main():
    session_id = get_session_id()
    if not session_id:
        sys.exit(0)

    SESSION_DIR.mkdir(exist_ok=True)
    marker = SESSION_DIR / session_id
    if marker.exists():
        sys.exit(0)
    marker.touch()

    config = load_config()
    tasks = read_tasks(config)
    sync_diffs = check_template_sync(config)
    skills_warning = check_skills_staleness()

    if not tasks and not sync_diffs and not skills_warning:
        sys.exit(0)

    output = "[SESSION START]\n\n"

    if sync_diffs:
        output += "⚠️  [DESYNC] .claude/hooks/ różni się od AI template repo:\n"
        output += "\n".join(sync_diffs)
        output += f"\n  Template: {config.get('ai_template_path', '')}\n"
        output += "  Zsynchronizuj zmiany z template przed commitowaniem.\n\n---\n\n"

    if skills_warning:
        output += skills_warning + "\n\n---\n\n"

    if tasks:
        sections = [f"## {name} — docs/TASKS.md\n\n{content}" for name, content in tasks]
        output += "Aktualne zadania z repozytoriów:\n\n"
        output += "\n\n---\n\n".join(sections)
        output += "\n\n---\n\nWYŚWIETL użytkownikowi powyższą listę otwartych zadań dosłownie, zanim odpiszesz na jego wiadomość."

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
