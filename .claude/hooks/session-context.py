#!/usr/bin/env python3
"""
UserPromptSubmit hook: kontekst na start sesji.
Na pierwszej wiadomości sesji:
- czyta docs/TASKS.md z repozytoriów skonfigurowanych w config.json (klucz "repos")
- mówi, czy szablon ma zmiany dla projektu (ADR-006; scripts/update-from-template.py)
Kolejne wiadomości tej samej sesji: hook nie odpala (marker w /tmp).

config.json (wymagane pola):
  "repos": [{"name": "grupavist-fe", "tasks": "grupavist-fe/docs/TASKS.md"}, ...]
  "ai_template_path": "/ścieżka/do/template"  (opcjonalne — bez niego diff pominięty)
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HOOKS_DIR = Path(__file__).resolve().parent
MONOREPO_ROOT = HOOKS_DIR.parent.parent
SESSION_DIR = Path(tempfile.gettempdir()) / "gv-claude-sessions"

sys.path.insert(0, str(HOOKS_DIR))
from stack import DEFAULT_TEMPLATE_URL, load_config, resolve_template_path, resolve_template_source  # noqa: E402

try:
    import skills_check  # noqa: E402
except Exception:  # a partial update of the hooks must not break every prompt — skip the skill checks
    skills_check = None


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


def check_template_updates(config: dict) -> str | None:
    """ADR-006: one line when the template has changes for this project. The logic lives in the
    project's scripts/update-from-template.py; a project without it stays quiet."""
    if config.get("is_template") is True:
        return None
    script = MONOREPO_ROOT / "scripts" / "update-from-template.py"
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("update_from_template_for_hook", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from datetime import date
        return module.session_notice(MONOREPO_ROOT, resolve_template_path(config), date.today().isoformat())
    except Exception:
        return None



def _is_git_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def check_template_path_configured(config: dict) -> str | None:
    """Warns only about a local path that does not exist — a missing setting is no
    longer an error, because resolve_template_source() falls back to the public URL."""
    value, source = resolve_template_source(config)
    if _is_git_url(value) or Path(value).exists():
        return None
    return (
        f"⚠️  [t-ai] ścieżka do template nie istnieje: {value}\n"
        f"  Źródło: {source}\n"
        f"  Popraw ją, albo usuń — bez niej zadziała {DEFAULT_TEMPLATE_URL}"
    )


def render(context: str, visible: str | None) -> str:
    """Plain stdout of UserPromptSubmit reaches only the model. A line the owner must see on
    screen (the template notice, ADR-006) goes out as JSON with systemMessage as well."""
    if not visible:
        return context
    return json.dumps({
        "systemMessage": visible,
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context},
    }, ensure_ascii=False)


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
    template_updates = check_template_updates(config)
    skills_sync_warning = skills_check.check_template_skills_sync(config) if skills_check else None
    skills_warning = skills_check.check_skills_staleness(config) if skills_check else None
    template_path_warning = check_template_path_configured(config)

    if not tasks and not template_updates and not skills_sync_warning and not skills_warning and not template_path_warning:
        sys.exit(0)

    output = "[SESSION START]\n\n"

    if template_path_warning:
        output += template_path_warning + "\n\n---\n\n"

    if template_updates:
        output += template_updates + "\n\n---\n\n"

    if skills_sync_warning:
        output += skills_sync_warning + "\n\n---\n\n"

    if skills_warning:
        output += skills_warning + "\n\n---\n\n"

    if tasks:
        sections = [f"## {name} — docs/TASKS.md\n\n{content}" for name, content in tasks]
        output += "Aktualne zadania z repozytoriów:\n\n"
        output += "\n\n---\n\n".join(sections)
        output += "\n\n---\n\nWYŚWIETL użytkownikowi powyższą listę otwartych zadań dosłownie, zanim odpiszesz na jego wiadomość."

    print(render(output, template_updates))
    sys.exit(0)


if __name__ == "__main__":
    main()
