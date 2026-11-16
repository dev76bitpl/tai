#!/usr/bin/env python3
"""CLAUDE.md changes must be acknowledged against the AI template (CLAUDE.md rule 13a).

Stage: commit-msg

Model (ADR-002): acknowledgment, not silent file comparison. When CLAUDE.md is
staged the guard forces a conscious decision — every time, on any machine, with
zero setup and no local template clone:

  - tai#N in the message           → reported in the template repo; checked on GitHub
                                     (no gh/network: passes with a warning)
  - [skip-sync] <reason> on a line → project-specific, reason of 3+ words (pass)
  - otherwise                      → block
The rule itself lives in .claude/hooks/sync_ack.py, shared with the Claude Code hook
(tai#243, jarvis D-014).

If ai_template_path points at a local template clone, the guard ADDITIONALLY
auto-verifies (git diff) and passes silently when that clone's CLAUDE.md was
touched this session — a convenience for template maintainers, not a requirement.
A URL or a missing path degrades safely to acknowledgment mode (never a silent
skip — the old behavior that left this guard dead in new projects).

is_template: true in config → this repo IS the template, nothing above to sync.

Configuration: .claude/hooks/config.json (canonical, ADR-002 decision 4)
  { "ai_template_path": "/local/path/to/template-clone" }   # optional

Bypass (no audit): SKIP=guard-template-sync git commit ...
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_staged_files, load_config, read_commit_msg

HOOKS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


def _load_sync_ack():
    """The shared rule, imported only when CLAUDE.md is staged: a project with an older copy
    of .claude/hooks must not have every commit crash on a missing module."""
    # Appended, not inserted: .claude/hooks has its own stack.py, and ours must win.
    if str(HOOKS_DIR) not in sys.path:
        sys.path.append(str(HOOKS_DIR))
    try:
        import sync_ack
    except ImportError:
        block(
            "❌ [BLOCK] guard-template-sync: .claude/hooks/sync_ack.py is missing, so the CLAUDE.md\n"
            "   change cannot be checked. Update from the template: python3 scripts/update-from-template.py\n"
            "   Bypass (no audit): SKIP=guard-template-sync git commit ..."
        )
    return sync_ack

_URL_PREFIXES = ("http://", "https://", "git@", "ssh://")


def _staged_touches_claude(staged: list[str]) -> bool:
    return any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged)


def _local_template_claude(template_path: str) -> Path | None:
    """The template's CLAUDE.md if template_path is a usable local clone, else None.

    URLs and non-existent paths return None → acknowledgment mode (ADR-002): the
    sync guard needs a local working tree for `git diff`; a URL can't provide one.
    """
    if not template_path or template_path.startswith(_URL_PREFIXES):
        return None
    claude = Path(template_path) / "CLAUDE.md"
    return claude if claude.is_file() else None


def _template_claude_touched(template_claude: Path) -> bool:
    """True if the template clone's CLAUDE.md has un/staged changes this session.

    Full content comparison won't work — the project CLAUDE.md carries [project]
    sections the template intentionally omits — so we check for *any* local change.
    """
    cwd = str(template_claude.parent)
    unstaged = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CLAUDE.md"],
        capture_output=True, text=True, cwd=cwd,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", "CLAUDE.md"],
        capture_output=True, text=True, cwd=cwd,
    )
    return "CLAUDE.md" in unstaged.stdout or "CLAUDE.md" in staged.stdout


def _block_message(sync_ack, repo: str, note: str, template_claude: "Path | None") -> str:
    msg = "❌ [BLOCK] CLAUDE.md staged — confirm where this change belongs (CLAUDE.md rule 13a).\n"
    if note:
        msg += f"\n   ⛔ {note}\n"
    msg += "\n" + sync_ack.options_text(repo) + "\n"
    if template_claude is None:
        msg += ("\n   (No local template clone configured — set ai_template_path in\n"
                "    .claude/hooks/config.json for automatic verification.)\n")
    else:
        msg += f"\n   Template clone: {template_claude} — the template's CLAUDE.md has no matching changes\n"
    return msg + "\n   Bypass (no audit):     SKIP=guard-template-sync git commit ..."


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)

    staged = get_staged_files()
    if not _staged_touches_claude(staged):
        return  # CLAUDE.md not touched

    config = load_config()
    if config.get("is_template"):
        return  # this repo IS the template — nothing above to sync

    template_source = config.get("ai_template_path", "") or ""
    template_claude = _local_template_claude(template_source)
    if template_claude is not None and _template_claude_touched(template_claude):
        return  # template updated this session

    sync_ack = _load_sync_ack()
    repo = sync_ack.repo_slug(template_source)
    ack = sync_ack.acknowledge(msg, repo)
    if ack.status == sync_ack.PASS:
        if ack.note:
            print(f"⚠️  guard-template-sync: {ack.note} — passing.", file=sys.stderr)
        return
    block(_block_message(sync_ack, repo, ack.note, template_claude))


if __name__ == "__main__":
    main(sys.argv)
