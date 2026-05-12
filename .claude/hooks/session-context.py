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
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
MONOREPO_ROOT = HOOKS_DIR.parent.parent
SESSION_DIR = Path("/tmp/gv-claude-sessions")


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


def read_tasks(config: dict) -> list[tuple[str, str]]:
    result = []
    for repo in config.get("repos", []):
        name = repo.get("name", "")
        tasks_rel = repo.get("tasks", "")
        if not name or not tasks_rel:
            continue
        path = MONOREPO_ROOT / tasks_rel
        if path.exists():
            result.append((name, path.read_text(encoding="utf-8").strip()))
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

    if not tasks and not sync_diffs:
        sys.exit(0)

    output = "[SESSION START]\n\n"

    if sync_diffs:
        output += "⚠️  [DESYNC] .claude/hooks/ różni się od AI template repo:\n"
        output += "\n".join(sync_diffs)
        output += f"\n  Template: {config.get('ai_template_path', '')}\n"
        output += "  Zsynchronizuj zmiany z template przed commitowaniem.\n\n---\n\n"

    if tasks:
        sections = [f"## {name} — docs/TASKS.md\n\n{content}" for name, content in tasks]
        output += "Aktualne zadania z repozytoriów:\n\n"
        output += "\n\n---\n\n".join(sections)
        output += "\n\n---\n\nZapytaj użytkownika nad czym dziś pracuje i wskaż pasujące zadania z powyższego kontekstu."

    print(output)
    sys.exit(0)


if __name__ == "__main__":
    main()
