"""Checks of the Claude Code layer for scripts/doctor.py.

Split out to keep doctor.py under the logic-file size limit. Each check gets the project root
and doctor's own output functions (ok / fail / warn), so it prints exactly like the rest.
"""
import json
import os
import re
from pathlib import Path

_INTERPRETER_PLACEHOLDER = re.compile(r"\bINTERPRETER\b")


def _hook_commands(node) -> list[str]:
    """Every hook `command` string found anywhere in a parsed settings file."""
    if isinstance(node, dict):
        found = [v for k, v in node.items() if k == "command" and isinstance(v, str)]
        for value in node.values():
            found.extend(_hook_commands(value))
        return found
    if isinstance(node, list):
        return [cmd for item in node for cmd in _hook_commands(item)]
    return []


def claude_hooks(root: Path, ok, fail, warn) -> bool:
    """Claude Code layer: are the guard hooks from .claude/hooks/ wired on this machine?

    The commit layer (pre-commit) can be fully green while this one is dead, because the
    hook commands live in a per-machine, gitignored file.
    """
    claude_dir = root / ".claude"
    local = claude_dir / "settings.local.json"
    if not local.is_file():
        warn(
            ".claude/settings.local.json missing — no Claude Code hook runs on this machine",
            "Run: cp .claude/settings.local.json.example .claude/settings.local.json"
            "  then replace INTERPRETER (python3 / py) — see docs/GUARDS.md, section \"Interpreter\".",
        )
        return True

    try:
        local_data = json.loads(local.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        fail(
            ".claude/settings.local.json unreadable — no Claude Code hook can run",
            "Fix the JSON or recreate the file from .claude/settings.local.json.example.",
        )
        return False

    commands = _hook_commands(local_data.get("hooks", {}) if isinstance(local_data, dict) else {})
    healthy = True

    if any(_INTERPRETER_PLACEHOLDER.search(cmd) for cmd in commands):
        fail(
            ".claude/settings.local.json still contains the INTERPRETER placeholder — every hook fails to start",
            "Replace INTERPRETER with python3 (Ubuntu/macOS) or py (Windows) — see docs/GUARDS.md, section \"Interpreter\".",
        )
        healthy = False

    # Hooks may also be wired in the shared settings.json; a guard counts when either file runs it.
    shared = claude_dir / "settings.json"
    if shared.is_file():
        try:
            shared_data = json.loads(shared.read_text(encoding="utf-8"))
            if isinstance(shared_data, dict):
                commands += _hook_commands(shared_data.get("hooks", {}))
        except (json.JSONDecodeError, OSError):
            pass

    guards = sorted(path.name for path in (claude_dir / "hooks").glob("guard-*.py"))
    unwired = [name for name in guards if not any(name in cmd for cmd in commands)]
    if unwired:
        warn(
            f"Guard hooks present in .claude/hooks/ but not wired: {', '.join(unwired)}",
            "Copy their entries from .claude/settings.local.json.example into .claude/settings.local.json.",
        )
    elif healthy:
        ok(f"Claude Code hooks wired ({len(guards)} guard hook(s))")
    return healthy


def _load_hook_config(root: Path, warn) -> tuple[dict, str]:
    """config.json overlaid with config.local.json (per machine) — as the guards read it.

    Returns the merged config and the name of the file that supplied ai_template_path.
    """
    merged: dict = {}
    source = ""
    for name in ("config.json", "config.local.json"):
        path = root / ".claude" / "hooks" / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            warn(f".claude/hooks/{name} present but unparseable — ignored by the guards")
            continue
        if isinstance(data, dict):
            merged.update(data)
            if "ai_template_path" in data:
                source = name
    return merged, source


def claude_template_path(root: Path, ok, warn) -> None:
    """Where the template comes from: $AI_TEMPLATE_PATH > config.local.json > config.json."""
    config, source = _load_hook_config(root, warn)
    if config.get("is_template") is True:
        ok("This repo is the AI template — nothing to sync from")
        return

    template = os.environ.get("AI_TEMPLATE_PATH", "").strip()
    if template:
        source = "$AI_TEMPLATE_PATH"
    else:
        template = str(config.get("ai_template_path", "") or "").strip()
    if not template:
        warn(
            "ai_template_path not set (optional)",
            "Set $AI_TEMPLATE_PATH or put it in .claude/hooks/config.local.json — see docs/GUARDS.md, section \"Konfiguracja strażników\".",
        )
        return
    if "://" in template or template.startswith("git@"):
        ok(f"AI template repo: {template}  (remote, from {source})")
        return
    if not Path(template).expanduser().is_dir():
        warn(
            f"ai_template_path doesn't exist: {template}  (from {source})",
            "AI template sync guard will skip silently.",
        )
        return
    ok(f"AI template repo: {template}  (from {source})")
