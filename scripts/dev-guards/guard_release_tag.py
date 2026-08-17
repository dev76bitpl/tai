"""
Guard: release-please manifest version must have a matching GitHub Release.

Detects the case where a Release PR was merged but the GitHub Release was not
created (e.g. Actions lacked permissions, config bug, race condition).
Without the GitHub Release, release-please refuses to create the next Release PR.

Three states, not two. The guard used to read every non-zero exit from `gh` as "the
release is missing" and block. On a day when GitHub answered 503 that stopped every
commit in the repository — twice, in two parallel sessions — while the release existed
and had been published for a month. A guard exists to catch one specific mistake, not
to turn somebody else's outage into a work stoppage.

So: block only on a CONFIRMED absence. When the check itself could not be made (GitHub
down, `gh` not logged in, no network, rate limit), warn and pass.
"""

import json
import subprocess
import sys
from pathlib import Path

# Long enough for a slow API, short enough not to stall a commit.
_TIMEOUT_S = 15


def get_manifest_version() -> str | None:
    manifest = Path(".release-please-manifest.json")
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return data.get(".")
    except (json.JSONDecodeError, KeyError):
        return None


def changelog_exists() -> bool:
    return Path("CHANGELOG.md").exists()


def list_release_tags() -> list[str] | None:
    """
    Published release tags, or None when the question could not be answered.

    Decides on the PARSED JSON, not on the exit code: `gh` can print an error and still
    exit 0, and then stdout holds a message where the array should be. Trusting the exit
    code there means concluding "no releases exist" from an answer never received.
    """
    try:
        result = subprocess.run(
            ["gh", "release", "list", "--limit", "100", "--json", "tagName"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None  # gh missing, or it died — not an answer

    if result.returncode != 0:
        return None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None  # an error message where the array should be

    if not isinstance(data, list):
        return None
    return [row.get("tagName", "") for row in data if isinstance(row, dict)]


def get_release_commit(version: str) -> str:
    result = subprocess.run(
        ["git", "log", "--oneline", "--grep", "chore: release"],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().splitlines()
    return lines[0].split()[0] if lines else "<commit-hash>"


def main() -> int:
    if not changelog_exists():
        return 0

    version = get_manifest_version()
    if not version:
        return 0

    tags = list_release_tags()

    if tags is None:
        # Could not check. Say so and let the commit through: the repository may be
        # perfectly fine, and blocking here punishes the developer for GitHub's weather.
        sys.stdout.buffer.write((
            f"\n[WARN] Nie udalo sie sprawdzic, czy istnieje GitHub Release dla v{version}.\n"
            f"       (GitHub niedostepny, `gh` niezalogowany albo brak sieci.)\n"
            f"       Commit przepuszczony — sprawdz recznie: gh release list\n"
        ).encode("utf-8"))
        return 0

    if f"v{version}" in tags:
        return 0

    commit = get_release_commit(version)
    sys.stdout.buffer.write((
        f"\n[BLOCK] Brakuje GitHub Release dla v{version}\n"
        f"\n"
        f"  Release PR dla v{version} zostal zmergowany, ale GitHub Release nie powstal.\n"
        f"  release-please odmowi tworzenia kolejnego Release PR dopoki Release nie istnieje.\n"
        f"\n"
        f"  Sprawdzone na liscie wydan — v{version} faktycznie tam nie ma.\n"
        f"\n"
        f"  Fix (jednorazowy):\n"
        f"    gh release create v{version} --title \"v{version}\" --target {commit} --generate-notes\n"
    ).encode("utf-8"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
