#!/usr/bin/env python3
"""CLAUDE.md changes must be synced to the AI template repo (CLAUDE.md rule 13a).

Stage: commit-msg

Bypass:
  - [skip-sync] in commit body — change is project-specific (mark section with [project])
  - SKIP=guard-template-sync git commit ... — env var (not committed)

Configuration:
  Set "ai_template_path" in .pre-commit-hooks.config.json:
  { "ai_template_path": "/path/to/ai-template-repo" }
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_staged_files, load_config, read_commit_msg


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-sync]" in msg:
        return

    staged = get_staged_files()
    if not any(f == "CLAUDE.md" or f.endswith("/CLAUDE.md") for f in staged):
        return  # CLAUDE.md not touched

    config = load_config()
    template_path_str = config.get("ai_template_path")

    if not template_path_str:
        print(
            "⚠ [WARN] CLAUDE.md staged but ai_template_path not set in "
            ".pre-commit-hooks.config.json\n"
            "   CLAUDE.md rule 13a: universal rules must reach the AI template repo.\n"
            "   Add [skip-sync] if this change is project-specific.",
            file=sys.stderr,
        )
        return  # soft warn — can't enforce without path

    template_claude = Path(template_path_str) / "CLAUDE.md"
    if not template_claude.is_file():
        print(
            f"⚠ [WARN] ai_template_path set but {template_claude} not found.\n"
            "   Check the path in .pre-commit-hooks.config.json.",
            file=sys.stderr,
        )
        return

    # Check if template CLAUDE.md has uncommitted changes (was touched in this session).
    # Full content comparison won't work — project CLAUDE.md has [project]-specific sections
    # that the template intentionally omits.
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "CLAUDE.md"],
        capture_output=True,
        text=True,
        cwd=str(template_claude.parent),
    )
    template_has_staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", "CLAUDE.md"],
        capture_output=True,
        text=True,
        cwd=str(template_claude.parent),
    )
    template_touched = (
        "CLAUDE.md" in result.stdout
        or "CLAUDE.md" in template_has_staged.stdout
    )

    if template_touched:
        return  # template was updated in this session

    block(
        "❌ [BLOCK] CLAUDE.md staged but AI template has no corresponding changes.\n"
        "\n"
        "   CLAUDE.md rule 13a: sync universal rules to the template before committing.\n"
        f"   Template: {template_claude}\n"
        "\n"
        "   1. Apply universal changes to the template repo's CLAUDE.md\n"
        "   2. Or add [skip-sync] to commit body if change is project-specific\n"
        "\n"
        "   Bypass (audit trail):  add [skip-sync] to commit body\n"
        "   Bypass (no audit):     SKIP=guard-template-sync git commit ..."
    )


if __name__ == "__main__":
    main(sys.argv)
