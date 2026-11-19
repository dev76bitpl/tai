#!/usr/bin/env python3
"""Make sure this checkout has .claude/settings.local.json — the file that wires the Claude Code hooks.

  python3 scripts/claude_settings.py      # create it from the .example, or add the template hooks it lacks
  python3 scripts/claude_settings.py --template-example FILE   # also the hooks of the template's example (#282)

The file is per checkout and not in git (it holds this machine's Python command), so every new
`git worktree add` used to start without it: no Claude Code hook ran there at all, only the
pre-commit guards (#260). The git hook post-checkout (installed by pre-commit, see
.pre-commit-config.yaml) runs this after every checkout, `git worktree add` included.
The project start (scripts/new-project.py) builds the file with the same function.

A file that already exists keeps everything it has; only the template hooks it does not run yet
are added (#268). A project that had its own settings.local.json before the template came never
ran session-context.py, so its sessions never heard that the template had changes.

The project's own .example is not enough after a template update: a project that changed it keeps
it ("changed locally"), so a new template hook never shows up there and never gets wired (#282).
update-from-template.py therefore passes the template's example with --template-example.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = Path(".claude") / "settings.local.json.example"
TARGET = Path(".claude") / "settings.local.json"


def interpreter() -> str:
    """The Python command the hooks are started with on this machine."""
    return "py" if sys.platform == "win32" else "python3"


def settings_from_example(example_text: str) -> str:
    return example_text.replace("INTERPRETER", interpreter())


HOOK_SCRIPT = re.compile(r"\.claude/hooks/([\w.-]+\.py)")


def _script(command: str) -> "str | None":
    found = HOOK_SCRIPT.search(command or "")
    return found.group(1) if found else None


def _wired_scripts(hooks: object) -> "set[str]":
    names = set()
    if isinstance(hooks, dict):
        for groups in hooks.values():
            for group in groups if isinstance(groups, list) else []:
                for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                    name = _script(hook.get("command", "")) if isinstance(hook, dict) else None
                    if name:
                        names.add(name)
    return names


def _shared_scripts(root: Path) -> "set[str]":
    """Hooks may also be wired in the shared settings.json; a hook wired there is not added again."""
    try:
        data = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return _wired_scripts(data.get("hooks")) if isinstance(data, dict) else set()


def add_missing_hooks(settings: dict, example: dict, root: Path) -> "list[str]":
    """Adds to `settings` (in place) every hook of `example` whose script is not wired yet and
    exists in this checkout. Nothing is removed or changed. Returns the added script names."""
    wired = _wired_scripts(settings.get("hooks")) | _shared_scripts(root)
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return []
    added = []
    for event, groups in (example.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                name = _script(hook.get("command", ""))
                if not name or name in wired or not (root / ".claude" / "hooks" / name).is_file():
                    continue
                mine = hooks.setdefault(event, [])
                if not isinstance(mine, list):
                    continue
                same = next((g for g in mine if isinstance(g, dict) and isinstance(g.get("hooks"), list)
                             and g.get("matcher") == group.get("matcher")), None)
                if same is None:
                    same = {k: v for k, v in group.items() if k != "hooks"} | {"hooks": []}
                    mine.append(same)
                same["hooks"].append(dict(hook))
                wired.add(name)
                added.append(name)
    return added


def _template_hooks(template_example: "Path | None") -> dict:
    """The template's example as a dict; {} when not given or not readable (it only adds hooks)."""
    if template_example is None:
        return {}
    try:
        data = json.loads(settings_from_example(template_example.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def ensure_settings_local(root: Path, example_root: "Path | None" = None,
                          template_example: "Path | None" = None) -> "tuple[str, list[str]]":
    """('created' | 'updated' | 'present' | 'unreadable' | 'no-example', added hook scripts).

    An existing file keeps all it has; only the template hooks it lacks are added (#268) — from the
    project's example and, when given, from the template's (#282).
    A file that is not valid JSON is left alone — doctor reports it."""
    target = root / TARGET
    example = (example_root or root) / EXAMPLE
    if not example.is_file():
        return ("present" if target.exists() else "no-example"), []
    example_text = settings_from_example(example.read_text(encoding="utf-8"))
    created = not target.exists()
    if created:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(example_text, encoding="utf-8")
    try:
        settings = json.loads(target.read_text(encoding="utf-8"))
        template = json.loads(example_text)
    except (OSError, ValueError):
        return ("created", []) if created else ("unreadable", [])
    if not isinstance(settings, dict) or not isinstance(template, dict):
        return ("created", []) if created else ("unreadable", [])
    added = [] if created else add_missing_hooks(settings, template, root)
    added += add_missing_hooks(settings, _template_hooks(template_example), root)
    if added:
        target.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if created:
        return "created", added
    return ("updated", added) if added else ("present", [])


def template_example_arg(argv: "list[str]") -> "Path | None":
    """The file after --template-example, if given (no argparse: unknown arguments must not fail
    a checkout)."""
    if "--template-example" in argv:
        i = argv.index("--template-example")
        if i + 1 < len(argv):
            return Path(argv[i + 1])
    return None


def main() -> int:
    try:
        state, added = ensure_settings_local(ROOT, template_example=template_example_arg(sys.argv[1:]))
    except Exception as exc:  # a checkout must never fail because of this
        print(f"[claude-settings] skipped: {exc}")
        return 0
    if state == "created":
        print(f"[claude-settings] created {TARGET} (interpreter: {interpreter()}) — Claude Code hooks are wired here")
    if state == "updated" or (state == "created" and added):
        print(f"[claude-settings] added template hooks to {TARGET}: {', '.join(added)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
