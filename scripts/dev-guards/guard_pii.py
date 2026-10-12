#!/usr/bin/env python3
"""Block commits that add personal data (PESEL, bank account, phone, private e-mail,
names from the local list). Personal data of real people must never reach a repository.

Stage: pre-commit. Checks only lines added in the staged diff.
Fails closed: when the staged diff cannot be read, the commit is blocked.

Bypass:
  - put `pii-ok` on the line with documented fake data (fixtures, examples)
  - SKIP=guard-pii git commit ...   (only for a false positive you have checked)

Detector: scripts/dev-guards/pii.py (importable on its own, e.g. by a scheduled repo scan).
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pii import load_names, scan_line

SKIP_SUFFIXES = (".lock", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".ico", ".woff", ".woff2")
SKIP_NAMES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock")


def header_path(raw: str) -> str:
    """Path from a `+++ ` diff header. Git quotes paths with special characters and appends
    a tab to paths with spaces; neither may hide the file from the scan."""
    path = raw[4:].rstrip("\t")
    if len(path) >= 2 and path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path[2:] if path.startswith("b/") else path


def main() -> int:
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotePath=false", "diff", "--cached", "--unified=0", "--no-color",
             "--diff-filter=AM"],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        print("guard-pii: nie mozna uruchomic git (%s) - commit zablokowany." % exc)
        return 1
    if proc.returncode != 0:
        print("guard-pii: nie mozna odczytac zmian do commita - commit zablokowany.")
        print(proc.stderr.strip())
        return 1
    names = load_names()
    hits, path, lineno, in_hunk = [], "?", 0, False
    for raw in proc.stdout.splitlines():
        if raw.startswith("diff --git "):
            path, in_hunk = "?", False
            continue
        if raw.startswith("@@"):
            in_hunk = True
            try:
                lineno = int(raw.split("+")[1].split(",")[0].split(" ")[0]) - 1
            except (IndexError, ValueError):
                lineno = 0
            continue
        if not in_hunk:
            if raw.startswith("+++ "):
                path = header_path(raw)
            continue
        if not raw.startswith("+"):
            continue
        lineno += 1
        if path.endswith(SKIP_SUFFIXES) or Path(path).name in SKIP_NAMES:
            continue
        for kind, masked in scan_line(raw[1:], names):
            hits.append("  %s:%d  %s  %s" % (path, lineno, kind, masked))
    if not hits:
        return 0
    print("guard-pii: dane osobowe w zmianach do commita (wartosci zamaskowane):")
    print("\n".join(hits))
    print("Usun je z pliku. Dane testowe oznacz `pii-ok` w tej linii.")
    print("Falszywy alarm, ktory sprawdziles: SKIP=guard-pii git commit ...")
    return 1


if __name__ == "__main__":
    sys.exit(main())
