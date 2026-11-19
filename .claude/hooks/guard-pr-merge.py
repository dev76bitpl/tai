#!/usr/bin/env python3
"""
Guard: no `gh pr merge` while the PR's CI is not green (PreToolUse on Bash|PowerShell).

Why: GitHub branch protection / rulesets (a server-side "require green check before merge")
are gated behind a paid plan for a PRIVATE repo on the free plan (HTTP 403 "Upgrade to GitHub
Pro or make this repository public"). Most projects built from this template are private, so
the rule "green CI before merge" is enforced here instead, at the one place a session can
merge: the `gh pr merge` command. Origin: the cdue pilot, where PRs were merged with a red
check before anyone looked at the status — a rule in prose was not enough (tai#211).

Scope / limits:
  - Binds merges run from a Claude session / this machine via `gh pr merge`. It does NOT and
    cannot stop a merge clicked in the GitHub web UI — that gap is accepted; only branch
    protection (GitHub Pro for a private repo) closes it.
  - Blocks (exit 2 + stderr) when: any CI check is failing or still pending/running, OR the
    PR has no checks at all, OR the check state cannot be read (no gh, no PR, network). A guard
    that cannot confirm green does not pass — but there IS a bypass, because merge is the
    owner's call.

Bypass: put [skip-merge-check] anywhere in the command. Use it only for a deliberate merge
the owner has approved despite a red/pending/unknown check (e.g. an unrelated flaky external
check). Unlike guard-process-kill, this guard has a bypass on purpose: it encodes a workflow
policy, not a safety invariant.

Self-test: python3 guard-pr-merge.py --self-test
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stack import read_command

BYPASS = "[skip-merge-check]"

HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\b", re.DOTALL)
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
MERGE_CMD = re.compile(r"(?<![\w-])gh\s+pr\s+merge\b", re.IGNORECASE)
# Positional PR ref right after `merge` (number, URL or branch), only when not a flag.
PR_REF = re.compile(r"(?<![\w-])gh\s+pr\s+merge\s+(?!-)(\S+)", re.IGNORECASE)

# conclusions/states that count as "this check is fine"
OK_OUTCOME = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _strip_noise(command: str) -> str:
    """Remove heredoc bodies and quoted spans so a mere MENTION of `gh pr merge`
    (in a commit message, a doc, an echo) is not mistaken for the command itself."""
    no_heredoc = HEREDOC.sub("\n", command)
    return QUOTED.sub("''", no_heredoc)


def is_merge_command(command: str) -> bool:
    return bool(MERGE_CMD.search(_strip_noise(command)))


def pr_ref(command: str) -> str:
    """The positional PR ref (number/url/branch) if given right after `merge`, else ""
    (gh then uses the current branch's PR)."""
    m = PR_REF.search(_strip_noise(command))
    return m.group(1) if m else ""


def fetch_checks(ref: str) -> tuple[list[dict], str | None]:
    """Returns (checks, error). checks is the statusCheckRollup list. error is a human
    string when the state could not be read (caller must BLOCK)."""
    args = ["gh", "pr", "view"]
    if ref:
        args.append(ref)
    args += ["--json", "statusCheckRollup"]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return [], "gh CLI not found"
    except subprocess.TimeoutExpired:
        return [], "gh timed out"
    if proc.returncode != 0:
        msg = proc.stderr.strip() or f"gh exited {proc.returncode}"
        return [], msg
    try:
        data = json.loads(proc.stdout or "{}")
    except ValueError:
        return [], "gh returned unparseable JSON"
    rollup = data.get("statusCheckRollup")
    if not isinstance(rollup, list):
        return [], "no statusCheckRollup in gh output"
    return rollup, None


def classify(check: dict) -> str:
    """'pass' | 'fail' | 'pending' for one statusCheckRollup entry.
    CheckRun carries status + conclusion; StatusContext carries state."""
    if check.get("__typename") == "CheckRun":
        if (check.get("status") or "").upper() != "COMPLETED":
            return "pending"
        return "pass" if (check.get("conclusion") or "").upper() in OK_OUTCOME else "fail"
    state = (check.get("state") or check.get("conclusion") or "").upper()
    if state in OK_OUTCOME:
        return "pass"
    if state in {"PENDING", "EXPECTED", "QUEUED", "IN_PROGRESS", "WAITING", ""}:
        return "pending"
    return "fail"


def name_of(check: dict) -> str:
    return check.get("name") or check.get("context") or "(unnamed check)"


def verdict(command: str) -> str | None:
    """Reason to BLOCK, or None to allow. Pure except for the gh call inside."""
    if not is_merge_command(command):
        return None
    if BYPASS in command:
        return None

    ref = pr_ref(command)
    target = f"PR {ref}" if ref else "the current branch's PR"
    checks, error = fetch_checks(ref)
    if error is not None:
        return f"could not read the CI state of {target} ({error})"
    if not checks:
        return f"{target} has no CI checks — cannot confirm the build is green"

    bad = [(name_of(c), classify(c)) for c in checks]
    failing = [n for n, s in bad if s == "fail"]
    pending = [n for n, s in bad if s == "pending"]
    if not failing and not pending:
        return None

    lines = []
    if failing:
        lines.append("  failing: " + ", ".join(sorted(failing)))
    if pending:
        lines.append("  still running: " + ", ".join(sorted(pending)))
    return f"CI on {target} is not green:\n" + "\n".join(lines)


def main() -> None:
    command = read_command("guard-pr-merge")
    reason = verdict(command)
    if reason is None:
        sys.exit(0)
    print(
        f"❌ [BLOCK] guard-pr-merge: {reason}.\n"
        "Project rule: a PR is merged only once its CI is green.\n"
        "  - wait for the checks to pass (watch: gh pr checks <pr> --watch), then merge; or\n"
        f"  - if the owner has approved this merge despite the check, add {BYPASS} to the command.\n"
        "Note: this guard only covers `gh pr merge`; a merge from the GitHub web UI is not checked.",
        file=sys.stderr,
    )
    sys.exit(2)


# (command, should_block) — verdict() is monkeypatched to avoid real gh calls in self-test.
SELF_TEST: list[tuple[str, bool]] = [
    ("gh pr merge 48 --squash --delete-branch", True),   # red/pending per fake
    ("gh pr merge --squash", True),
    ("gh pr merge 48 --squash [skip-merge-check]", False),  # bypass
    ("git commit -m 'chore: document gh pr merge policy'", False),  # mention, not command
    ("echo 'run gh pr merge later'", False),
    ("cat <<'EOF'\nthen gh pr merge 48\nEOF", False),  # heredoc body
    ("gh pr view 48 --json statusCheckRollup", False),  # not a merge
    ("gh pr list && echo done", False),
]


def self_test() -> None:
    global fetch_checks
    original = fetch_checks
    # Fake: pretend every queried PR has one failing check.
    fetch_checks = lambda ref: ([{"__typename": "CheckRun", "status": "COMPLETED",
                                  "conclusion": "FAILURE", "name": "Guards"}], None)
    failed = 0
    try:
        for cmd, should_block in SELF_TEST:
            blocked = verdict(cmd) is not None
            if blocked != should_block:
                failed += 1
                print(f"FAIL  expected {'BLOCK' if should_block else 'allow'}: {cmd}")
    finally:
        fetch_checks = original
    print(f"{len(SELF_TEST) - failed}/{len(SELF_TEST)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    main()
