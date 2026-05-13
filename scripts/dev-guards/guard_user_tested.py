#!/usr/bin/env python3
"""[user-tested] flag required on feat/* and fix/* branches (CLAUDE.md rule 16b).

Stage: commit-msg.

Module closure protocol: AI cannot commit until user explicitly confirms manual
testing per docs/TESTING.md. The flag is the mechanical proof of that step.

Branches other than feat/* / fix/* (docs/*, chore/*, refactor/*, test/*) are
exempt — they don't ship runtime changes.

Bypass:
  - [skip-test-check] in commit body — for docs-only / chore commits not touching runtime
  - SKIP=guard-user-tested git commit ... — env var
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_current_branch, read_commit_msg

ENFORCED_BRANCH_PREFIXES = ("feat/", "fix/")


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if not msg:
        return  # gitlint will catch missing message

    if "[skip-test-check]" in msg:
        return

    branch = get_current_branch()
    if not branch or branch == "HEAD":
        return  # detached HEAD (rebase, cherry-pick) — skip

    if not branch.startswith(ENFORCED_BRANCH_PREFIXES):
        return  # docs/*, chore/*, refactor/*, test/* — flag not required

    if "[user-tested]" not in msg:
        block(
            f"❌ [BLOCK] Commit on branch '{branch}' without [user-tested] flag.\n"
            f"\n"
            f"   CLAUDE.md rule 16b (module closure protocol):\n"
            f"   AI cannot commit until user explicitly confirms manual testing per docs/TESTING.md.\n"
            f"\n"
            f"   If user explicitly accepted the change:\n"
            f"     → add [user-tested] to commit message.\n"
            f"\n"
            f"   If the change is docs-only / chore (no runtime impact):\n"
            f"     → add [skip-test-check] with reason in commit body.\n"
            f"\n"
            f"   Emergency bypass (no audit): SKIP=guard-user-tested git commit ..."
        )


if __name__ == "__main__":
    main(sys.argv)
