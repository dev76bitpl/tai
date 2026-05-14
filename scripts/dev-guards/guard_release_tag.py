"""
Guard: release-please manifest version must have a matching GitHub Release.

Detects the case where a Release PR was merged but the GitHub Release was not
created (e.g. Actions lacked permissions, config bug, race condition).
Without the GitHub Release, release-please refuses to create the next Release PR.
"""

import json
import subprocess
import sys
from pathlib import Path


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


def github_release_exists(version: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", f"v{version}"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


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

    if github_release_exists(version):
        return 0

    commit = get_release_commit(version)
    sys.stdout.buffer.write((
        f"\n[BLOCK] Brakuje GitHub Release dla v{version}\n"
        f"\n"
        f"  Release PR dla v{version} zostal zmergowany, ale GitHub Release nie powstal.\n"
        f"  release-please odmowi tworzenia kolejnego Release PR dopoki Release nie istnieje.\n"
        f"\n"
        f"  Fix (jednorazowy):\n"
        f"    gh release create v{version} --title \"v{version}\" --target {commit} --generate-notes\n"
    ).encode("utf-8"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
