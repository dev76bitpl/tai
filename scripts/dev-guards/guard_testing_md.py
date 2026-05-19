#!/usr/bin/env python3
"""docs/TESTING.md must be touched (staged now or committed earlier on branch).

Stage: commit-msg (so [skip-docs] body flag works).

CLAUDE.md rule 16b: manual test checklist must land in docs/TESTING.md, not just
in chat. Every feat/* / fix/* branch that touches src/ must include or update the
checklist somewhere on the branch — proof that the flow was thought through.

Passes when:
  - docs/TESTING.md is staged in the current commit, OR
  - docs/TESTING.md was committed earlier on the current branch (vs main/master)

Branches other than feat/* / fix/* (docs/*, chore/*, refactor/*, test/*) are
exempt — they don't ship runtime changes.

Bypass:
  - [skip-docs] in commit body — for commits where manual testing isn't applicable
    (pure schema migration, internal refactor, config-only change); include reason
  - SKIP=guard-testing-md git commit ... — env var (not committed)
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import block, get_current_branch, get_staged_files, read_commit_msg

ENFORCED_BRANCH_PREFIXES = ("feat/", "fix/")
BASE_BRANCHES = ("main", "master", "develop")
TESTING_FILE = "docs/TESTING.md"
SRC_PREFIXES = ("src/",)


def testing_md_touched_in_branch(branch: str) -> bool:
    """True if docs/TESTING.md appears in any commit on this branch vs base."""
    for base in BASE_BRANCHES:
        r = subprocess.run(
            ["git", "merge-base", "HEAD", base],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            continue
        merge_base = r.stdout.strip()
        r2 = subprocess.run(
            ["git", "diff", "--name-only", merge_base, "HEAD", "--", TESTING_FILE],
            capture_output=True, text=True,
        )
        if TESTING_FILE in r2.stdout.splitlines():
            return True
    return False


def main(argv: list[str]) -> None:
    msg = read_commit_msg(argv)
    if "[skip-docs]" in msg:
        return

    branch = get_current_branch()
    if not branch or branch == "HEAD":
        return  # detached HEAD (rebase, cherry-pick) — skip

    if not any(branch.startswith(p) for p in ENFORCED_BRANCH_PREFIXES):
        return  # docs/*, chore/*, refactor/*, test/* — not required

    staged = get_staged_files()

    has_src = any(any(f.startswith(p) for p in SRC_PREFIXES) for f in staged)
    if not has_src:
        return  # no src/ files staged — docs or config only commit

    # Pass if TESTING.md is staged in this commit
    if any(TESTING_FILE in f for f in staged):
        return

    # Pass if TESTING.md was touched in any earlier commit on this branch
    if testing_md_touched_in_branch(branch):
        return

    block(
        f"❌ [BLOCK] docs/TESTING.md not updated on branch '{branch}'.\n"
        f"\n"
        f"   CLAUDE.md rule 16b: manual test checklist must be written to\n"
        f"   docs/TESTING.md — not just mentioned in chat.\n"
        f"\n"
        f"   Add or update the checklist for the flow you just changed,\n"
        f"   then stage docs/TESTING.md alongside the source change.\n"
        f"\n"
        f"   Bypass (audit trail):  add [skip-docs] to commit body with reason\n"
        f"   Bypass (no audit):     SKIP=guard-testing-md git commit ..."
    )


if __name__ == "__main__":
    main(sys.argv)
