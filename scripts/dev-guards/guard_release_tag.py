"""
Guard: release-please manifest version must have a matching git tag.

Detects the case where a Release PR was merged but the git tag was not
created (e.g. Actions lacked permissions, network error, race condition).
Without the tag, release-please refuses to create the next Release PR.
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


def tag_exists(version: str) -> bool:
    result = subprocess.run(
        ["git", "tag", "-l", f"v{version}"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def main() -> int:
    if not changelog_exists():
        return 0

    version = get_manifest_version()
    if not version:
        return 0

    if tag_exists(version):
        return 0

    sys.stdout.buffer.write((
        f"\n[BLOCK] Brakuje taga v{version} dla wersji z .release-please-manifest.json\n"
        f"\n"
        f"  Release PR dla v{version} zostal zmergowany, ale git tag nie powstal.\n"
        f"  release-please odmowi tworzenia kolejnego Release PR dopoki tag nie istnieje.\n"
        f"\n"
        f"  Fix (jednorazowy - AI to zrobi):\n"
        f"    git log --oneline | grep 'chore: release'   # znajdz hash commita release\n"
        f"    git tag v{version} <hash>\n"
        f"    git push origin v{version}\n"
    ).encode("utf-8"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
