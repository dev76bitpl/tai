"""Checks of the Claude Code layer for scripts/doctor.py.

Split out to keep doctor.py under the logic-file size limit. Each check gets the project root
and doctor's own output functions (ok / fail / warn), so it prints exactly like the rest.
"""
import importlib.util
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
            "Run: sed 's/INTERPRETER/python3/g' .claude/settings.local.json.example"
            " > .claude/settings.local.json  (Windows: py instead of python3 —"
            " see docs/GUARDS.md, section \"Interpreter\")",
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
            warn(
                f".claude/hooks/{name} present but unparseable — ignored by the guards",
                f"Fix the JSON syntax: python3 -m json.tool .claude/hooks/{name}",
            )
            continue
        if isinstance(data, dict):
            merged.update(data)
            if "ai_template_path" in data:
                source = name
    return merged, source


ACK_MODE = ("without a local template clone the sync guards cannot compare documents and ask on every "
            "CLAUDE.md change for tai#N or [skip-sync] <reason>")


def _hooks_stack(root: Path):
    """The project's .claude/hooks/stack.py — the guards' own rules; None when it cannot load."""
    try:
        spec = importlib.util.spec_from_file_location("doctor_hooks_stack", root / ".claude" / "hooks" / "stack.py")
        hooks_stack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hooks_stack)
        return hooks_stack
    except (OSError, ImportError, SyntaxError):
        return None


def _clone_next_to(root: Path) -> "Path | None":
    """A template clone next to the project, found the way the guards find it (#151, #166):
    autodetection in .claude/hooks/stack.py. None when that file or the function is missing."""
    try:
        return _hooks_stack(root)._autodetect_template_root()
    except AttributeError:
        return None


def _is_template_repo(root: Path) -> "bool | None":
    """Whether root's git origin is the template repository (#144); None when it cannot tell."""
    try:
        return _hooks_stack(root).is_template_repo(root)
    except AttributeError:
        return None


def claude_template_path(root: Path, ok, warn) -> None:
    """Where the template comes from, in the guards' order:
    $AI_TEMPLATE_PATH > config.local.json > config.json > a template clone next to the project."""
    config, source = _load_hook_config(root, warn)
    if config.get("is_template") is True:
        if _is_template_repo(root) is False:
            warn(
                "is_template is set, but this repo's git origin is not the AI template",
                "A flag copied from the template switches the sync guards off here and is ignored by "
                "autodetection elsewhere (#144). Remove \"is_template\" from .claude/hooks/config.json.",
            )
            return
        ok("This repo is the AI template — nothing to sync from")
        return

    template = os.environ.get("AI_TEMPLATE_PATH", "").strip()
    if template:
        source = "$AI_TEMPLATE_PATH"
    else:
        template = str(config.get("ai_template_path", "") or "").strip()
    if not template:
        clone = _clone_next_to(root)
        if clone is not None:
            ok(f"AI template repo: {clone}  (template clone next to the project)")
            return
        warn(
            "ai_template_path not set (optional)",
            f"{ACK_MODE[0].upper()}{ACK_MODE[1:]}. For automatic verification set $AI_TEMPLATE_PATH or put it in "
            ".claude/hooks/config.local.json — see docs/GUARDS.md, section \"Konfiguracja strażników\".",
        )
        return
    if "://" in template or template.startswith("git@"):
        ok(f"AI template repo: {template}  (remote, from {source}) — {ACK_MODE}")
        return
    if not Path(template).expanduser().is_dir():
        warn(
            f"ai_template_path doesn't exist: {template}  (from {source})",
            f"{ACK_MODE[0].upper()}{ACK_MODE[1:]}. Fix the path for automatic verification.",
        )
        return
    ok(f"AI template repo: {template}  (from {source})")
