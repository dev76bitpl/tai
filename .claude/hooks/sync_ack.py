"""How a commit acknowledges a desync with the template (Guard 6, tai#243, jarvis D-014).

One door into the template: a change that belongs there is reported in the template repo
first, and the project commit carries the reference (`tai#N`), which is checked on GitHub.
A change that is only the project's own carries `[skip-sync]` followed by why, on the same
line, in at least MIN_REASON_WORDS words.

Shared by the Claude Code hook (.claude/hooks/guard-template-sync.py) and the commit-msg
guard (scripts/dev-guards/guard_template_sync.py), so both apply one rule. Stdlib only and
no `stack` import: the two guards each have their own stack.py under that module name.
"""
import re
import subprocess
from dataclasses import dataclass

SKIP_FLAG = "[skip-sync]"
MIN_REASON_WORDS = 3
DEFAULT_REPO = "dev76bitpl/tai"
GH_TIMEOUT = 5  # seconds; a slow network must not hold up a commit for long
REF_EXAMPLE = "tai#123"
SKIP_EXAMPLE = "[skip-sync] pricing section is CRM-only"

# tai#12 or dev76bitpl/tai#12; not part of a longer name (mytai#12, tai#12a).
_TAI_REF = re.compile(r"(?<![\w-])(?:[\w.-]+/)?tai#(\d+)(?!\w)")
_REPO_IN_URL = re.compile(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$")

PASS, BLOCK, NONE = "pass", "block", "none"


@dataclass
class Ack:
    status: str  # PASS, BLOCK or NONE (no acknowledgment in the message)
    note: str = ""  # why it blocks, or what could not be checked when it passes


def tai_refs(message: str) -> list[int]:
    return sorted({int(n) for n in _TAI_REF.findall(message)})


def skip_reason(message: str) -> "str | None":
    """Text after [skip-sync] on its line; None without the flag. Several flags: the longest."""
    reasons = [line.split(SKIP_FLAG, 1)[1].strip() for line in message.splitlines() if SKIP_FLAG in line]
    return max(reasons, key=len) if reasons else None


def has_reason(reason: "str | None") -> bool:
    return reason is not None and len(re.findall(r"\w+", reason)) >= MIN_REASON_WORDS


def repo_slug(template_source: str, run=subprocess.run) -> str:
    """owner/name of the template repo, from its URL or the local clone's origin."""
    url = template_source or ""
    if url and not url.startswith(("http://", "https://", "git@", "ssh://")):
        try:
            done = run(["git", "-C", url, "remote", "get-url", "origin"],
                       capture_output=True, text=True, timeout=GH_TIMEOUT)
            url = done.stdout.strip() if done.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            url = ""
    found = _REPO_IN_URL.search(url)
    return found.group(1) if found else DEFAULT_REPO


def ref_exists(repo: str, number: int, run=subprocess.run) -> "bool | None":
    """True/False from GitHub (issues cover PRs too); None when it could not be checked."""
    try:
        done = run(["gh", "api", f"repos/{repo}/issues/{number}", "--jq", ".number"],
                   capture_output=True, text=True, timeout=GH_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode == 0:
        return True
    return False if "404" in (done.stderr or "") else None


def acknowledge(message: str, repo: str, run=subprocess.run) -> Ack:
    refs = tai_refs(message)
    if refs:
        unchecked = []
        for number in refs:
            found = ref_exists(repo, number, run)
            if found is False:
                return Ack(BLOCK, f"tai#{number}: nie ma takiego zgłoszenia ani PR w {repo}")
            if found is None:
                unchecked.append(f"tai#{number}")
        if unchecked:
            return Ack(PASS, f"nie sprawdziłem {', '.join(unchecked)} w {repo} (brak gh, tokenu albo sieci)")
        return Ack(PASS)
    reason = skip_reason(message)
    if reason is None:
        return Ack(NONE)
    if has_reason(reason):
        return Ack(PASS)
    return Ack(BLOCK, f"{SKIP_FLAG} bez powodu — dopisz w tej samej linii, dlaczego to tylko wasze "
                      f"(min. {MIN_REASON_WORDS} słowa), np. `{SKIP_EXAMPLE}`")


def options_text(repo: str = DEFAULT_REPO) -> str:
    """The two ways out, for a block message."""
    return (
        f"  1. Do szablonu? → zgłoś issue albo PR w {repo} i wpisz odnośnik w wiadomości: `{REF_EXAMPLE}`\n"
        f"  2. Tylko wasze? → `{SKIP_EXAMPLE}` — flaga i powód w jednej linii (min. {MIN_REASON_WORDS} słowa)"
    )
