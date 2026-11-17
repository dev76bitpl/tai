#!/usr/bin/env python3
"""Make sure this checkout has .claude/settings.local.json — the file that wires the Claude Code hooks.

  python3 scripts/claude_settings.py      # create it from the .example when missing; never overwrite

The file is per checkout and not in git (it holds this machine's Python command), so every new
`git worktree add` used to start without it: no Claude Code hook ran there at all, only the
pre-commit guards (#260). The git hook post-checkout (installed by pre-commit, see
.pre-commit-config.yaml) runs this after every checkout, `git worktree add` included.
The project start (scripts/new-project.py) builds the file with the same function.
"""
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


def ensure_settings_local(root: Path, example_root: "Path | None" = None) -> str:
    """'created' / 'present' / 'no-example'. An existing file is never touched: it may carry
    the owner's own changes, and doctor reports a broken one."""
    target = root / TARGET
    if target.exists():
        return "present"
    example = (example_root or root) / EXAMPLE
    if not example.is_file():
        return "no-example"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(settings_from_example(example.read_text(encoding="utf-8")), encoding="utf-8")
    return "created"


def main() -> int:
    if ensure_settings_local(ROOT) == "created":
        print(f"[claude-settings] created {TARGET} (interpreter: {interpreter()}) — Claude Code hooks are wired here")
    return 0  # a checkout must never fail because of this


if __name__ == "__main__":
    sys.exit(main())
