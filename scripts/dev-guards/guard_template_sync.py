#!/usr/bin/env python3
"""Template documents changed in a project must be acknowledged against the AI template
(CLAUDE.md rule 13a).

Stage: commit-msg

Model (ADR-002): acknowledgment, not silent file comparison. The decision lives in the
commit message:

  - tai#N in the message           → reported in the template repo; checked on GitHub
                                     (no gh/network: passes with a warning)
  - [skip-sync] <reason> on a line → project-specific, reason of 3+ words (pass)
  - otherwise                      → block
The rule itself lives in .claude/hooks/sync_ack.py, shared with the Claude Code hook
(tai#243, jarvis D-014).

When does it ask — the same rule as the Claude Code hook (#166):
  - a local template clone is found → compare the staged *.md files the template owns
    (its template-files.json) section by section; ask only when the template lacks a section
    the project has (.claude/hooks/template_sections.py, shared with the hook)
  - no local clone (none, a URL, a missing path) → ask whenever CLAUDE.md is staged; never a
    silent skip, the old behavior that left this guard dead in new projects

The clone is found the way the hook finds it, by resolve_template_source() in
.claude/hooks/stack.py: $AI_TEMPLATE_PATH > config.local.json > config.json > a template
clone next to the project. Unlike the hook, this guard does not compare scripts/dev-guards/*.py
— a hand-made commit there must not start blocking for a new reason.

is_template: true in config → this repo IS the template, nothing above to sync.

Bypass (no audit): SKIP=guard-template-sync git commit ...
"""
import importlib
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_project_root, get_staged_files, load_config, read_commit_msg

HOOKS_DIR = Path(__file__).resolve().parents[2] / ".claude" / "hooks"

_URL_PREFIXES = ("http://", "https://", "git@", "ssh://")


def _load_shared(name: str):
    """A module shared with the Claude Code hook, imported only when it is needed: a project
    with an older copy of .claude/hooks must not have every commit crash on a missing module."""
    # Appended, not inserted: .claude/hooks has its own stack.py, and ours must win.
    if str(HOOKS_DIR) not in sys.path:
        sys.path.append(str(HOOKS_DIR))
    try:
        return importlib.import_module(name)
    except ImportError:
        block(
            f"❌ [BLOCK] guard-template-sync: .claude/hooks/{name}.py is missing, so the template\n"
            "   documents cannot be checked. Update from the template: python3 scripts/update-from-template.py\n"
            "   Bypass (no audit): SKIP=guard-template-sync git commit ..."
        )


def _template_source(config: dict) -> str:
    """Where the template is, by the same layers as the Claude Code hook (#166).

    .claude/hooks/stack.py shares its module name with ours, so it is loaded under another
    name. A project with an older copy that lacks resolve_template_source() falls back to
    the config value alone, as before.
    """
    fallback = str(config.get("ai_template_path", "") or "")
    try:
        spec = importlib.util.spec_from_file_location("hooks_stack", HOOKS_DIR / "stack.py")
        hooks_stack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hooks_stack)
        return hooks_stack.resolve_template_source(config)[0]
    except (OSError, ImportError, AttributeError, SyntaxError):
        return fallback


def _local_template_root(template_path: str) -> Path | None:
    """The template clone's directory, or None for a URL / missing path (acknowledgment mode)."""
    if not template_path or template_path.startswith(_URL_PREFIXES):
        return None
    root = Path(template_path)
    return root if root.is_dir() else None


def _staged_touches_claude(staged: list[str]) -> bool:
    return any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged)


def _issues(staged: list[str], template_root: "Path | None") -> list[str]:
    """What needs a decision; empty = nothing to ask."""
    if template_root is None:
        return ["  📝 CLAUDE.md staged — no local template clone to compare with."] if _staged_touches_claude(staged) else []
    sections = _load_shared("template_sections")
    return sections.md_issues(get_project_root(), template_root, sections.template_md_files(staged, template_root))


def _block_message(sync_ack, repo: str, issues: list[str], note: str, template_root: "Path | None") -> str:
    msg = "❌ [BLOCK] Template documents staged — confirm where this change belongs (CLAUDE.md rule 13a).\n\n"
    msg += "\n".join(issues) + "\n"
    if note:
        msg += f"\n   ⛔ {note}\n"
    msg += "\n" + sync_ack.options_text(repo) + "\n"
    if template_root is None:
        msg += ("\n   (No local template clone found — export AI_TEMPLATE_PATH, or set ai_template_path\n"
                "    in .claude/hooks/config.local.json, for automatic verification.)\n")
    else:
        msg += f"\n   Template clone: {template_root}\n"
    return msg + "\n   Bypass (no audit):     SKIP=guard-template-sync git commit ..."


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)

    staged = get_staged_files()
    if not any(f.endswith(".md") for f in staged):
        return  # no document staged — nothing the template could own

    config = load_config()
    if config.get("is_template"):
        return  # this repo IS the template — nothing above to sync

    template_source = _template_source(config)
    template_root = _local_template_root(template_source)
    issues = _issues(staged, template_root)
    if not issues:
        return

    sync_ack = _load_shared("sync_ack")
    repo = sync_ack.repo_slug(template_source)
    ack = sync_ack.acknowledge(msg, repo)
    if ack.status == sync_ack.PASS:
        if ack.note:
            print(f"⚠️  guard-template-sync: {ack.note} — passing.", file=sys.stderr)
        return
    block(_block_message(sync_ack, repo, issues, ack.note, template_root))


if __name__ == "__main__":
    main(sys.argv)
