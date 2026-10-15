#!/usr/bin/env python3
"""
Pokazuje, co projekt może wciągnąć z szablonu (ADR-006), i na życzenie to kopiuje.

Użycie:
    python3 scripts/update-from-template.py           # podgląd, niczego nie zmienia
    python3 scripts/update-from-template.py --apply   # kopiuje pliki „do aktualizacji” i „nowe”

Źródłem jest wydany `main` szablonu (origin/main lokalnego klona albo świeży klon z adresu),
nigdy jego katalog roboczy (#179). Listę plików szablonu czyta z `template-files.json`
w tym samym wydaniu. Plik zmieniony w projekcie nie jest nadpisywany, a `CLAUDE.md` tylko
porównywany po sekcjach.
"""
import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RELEASED_REF = "origin/main"
LIST_FILE = "template-files.json"

CURRENT, OUTDATED, NEW, LOCAL = "current", "outdated", "new", "local"
LABELS = {
    OUTDATED: "do aktualizacji (starsza wersja z szablonu)",
    NEW: "nowy w szablonie",
    LOCAL: "zmieniony lokalnie — porównaj ręcznie, skrypt go nie rusza",
}


@dataclass
class Report:
    files: dict[str, str] = field(default_factory=dict)  # path -> state
    sections: list[str] = field(default_factory=list)  # "CLAUDE.md: ## X (nowa)" lines
    error: str = ""

    def pending(self) -> list[str]:
        return [p for p, s in self.files.items() if s != CURRENT]


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def matches(path: str, pattern: str) -> bool:
    """Glob where '*' stays inside one directory."""
    p, q = PurePosixPath(path), PurePosixPath(pattern)
    return p.parent == q.parent and fnmatch.fnmatchcase(p.name, q.name)


def read_list(repo: Path, ref: str) -> "dict | None":
    shown = git(repo, "show", f"{ref}:{LIST_FILE}")
    if shown.returncode != 0:
        return None
    try:
        return json.loads(shown.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def template_paths(repo: Path, ref: str, spec: dict) -> list[str]:
    listed = git(repo, "ls-tree", "-r", "--name-only", ref).stdout.decode("utf-8").splitlines()
    return sorted(
        p for p in listed
        if any(matches(p, pat) for pat in spec.get("copy", []))
        and not any(matches(p, pat) for pat in spec.get("exclude", []))
    )


def released_blobs(repo: Path, ref: str, paths: list[str]) -> dict[str, str]:
    """path -> blob id of the file at ref."""
    out = git(repo, "ls-tree", "-r", ref, "--", *paths).stdout.decode("utf-8")
    blobs = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        blobs[path] = meta.split()[2]
    return blobs


def historical_blobs(repo: Path, ref: str, paths: list[str]) -> dict[str, set[str]]:
    """path -> every blob id the file ever had in the released history."""
    out = git(repo, "log", "--format=", "--raw", "--no-abbrev", "--no-renames", ref, "--", *paths)
    seen: dict[str, set[str]] = {}
    for line in out.stdout.decode("utf-8").splitlines():
        if not line.startswith(":"):
            continue
        meta, path = line.split("\t", 1)
        fields = meta.split()
        seen.setdefault(path, set()).update(b for b in fields[2:4] if set(b) != {"0"})
    return seen


def blob_of(file: Path) -> str:
    done = subprocess.run(["git", "hash-object", "--no-filters", str(file)], capture_output=True, text=True)
    return done.stdout.strip()


def sections(text: str) -> dict[str, str]:
    """Header line -> body, for ## and ### headers."""
    found: dict[str, str] = {}
    current, body = None, []
    for line in text.splitlines():
        if re.match(r"^#{2,3}\s+\S", line):
            if current:
                found[current] = "\n".join(body).strip()
            current, body = line.strip(), []
        elif current:
            body.append(line)
    if current:
        found[current] = "\n".join(body).strip()
    return found


def compare_sections(repo: Path, ref: str, project: Path, names: list[str]) -> list[str]:
    lines = []
    for name in names:
        shown = git(repo, "show", f"{ref}:{name}")
        local = project / name
        if shown.returncode != 0 or not local.is_file():
            continue
        theirs = sections(shown.stdout.decode("utf-8"))
        ours = sections(local.read_text(encoding="utf-8"))
        for header, body in theirs.items():
            if header not in ours:
                lines.append(f"{name}: {header}  (nowa w szablonie)")
            elif ours[header] != body:
                lines.append(f"{name}: {header}  (inna niż w szablonie)")
    return lines


def compare(repo: Path, ref: str, project: Path) -> Report:
    """Classify every template file in `project` against the template at `ref`."""
    spec = read_list(repo, ref)
    if spec is None:
        return Report(error=f"{ref} szablonu nie ma czytelnego {LIST_FILE} (szablon sprzed ADR-006?)")
    paths = template_paths(repo, ref, spec)
    released = released_blobs(repo, ref, paths)
    history = historical_blobs(repo, ref, paths)
    report = Report()
    for path in paths:
        local = project / path
        if not local.is_file():
            report.files[path] = NEW
            continue
        mine = blob_of(local)
        if mine == released.get(path):
            report.files[path] = CURRENT
        elif mine in history.get(path, set()):
            report.files[path] = OUTDATED
        else:
            report.files[path] = LOCAL
    report.sections = compare_sections(repo, ref, project, spec.get("compare_sections", []))
    return report


def apply(repo: Path, ref: str, project: Path, report: Report) -> list[str]:
    copied = []
    for path, state in report.files.items():
        if state not in (OUTDATED, NEW):
            continue
        content = git(repo, "show", f"{ref}:{path}").stdout
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        copied.append(path)
    return copied


def resolve_source(project: Path) -> "tuple[Path | None, str, Path | None, str]":
    """(repo, ref, temp dir to remove, error). A URL is cloned without blobs into a temp dir."""
    hooks = project / ".claude" / "hooks"
    sys.path.insert(0, str(hooks))
    try:
        from stack import load_config, resolve_template_path
    except ImportError:
        return None, "", None, "brak .claude/hooks/stack.py — nie wiem, gdzie jest szablon"
    config = load_config()
    if config.get("is_template") is True:
        return None, "", None, "to repo jest szablonem — nie ma skąd aktualizować"
    value = resolve_template_path(config)
    if not value:
        return None, "", None, "nie znam ścieżki do szablonu (ai_template_path)"
    if value.startswith(("git@", "https://", "http://", "ssh://")):
        tmp = Path(tempfile.mkdtemp(prefix="ai-template-update-"))
        done = subprocess.run(
            ["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", value, str(tmp)],
            capture_output=True, text=True,
        )
        if done.returncode != 0:
            shutil.rmtree(tmp, ignore_errors=True)
            return None, "", None, f"nie udało się pobrać szablonu z {value}: {done.stderr.strip()[:200]}"
        return tmp, RELEASED_REF, tmp, ""
    repo = Path(value)
    if git(repo, "rev-parse", "--verify", "-q", f"{RELEASED_REF}^{{commit}}").returncode != 0:
        return None, "", None, f"klon szablonu {repo} nie ma {RELEASED_REF} (git fetch w szablonie?)"
    return repo, RELEASED_REF, None, ""


# Session-start check (ADR-006, decisions 7–8). Lives here, next to compare(), so the hook stays
# thin and an old project without this script simply stays quiet.
SWITCH = "template_update_check"
FETCH_STAMP = "ai-template-last-fetch"  # in the template clone's git dir: one fetch a day per clone


def switch_on(repo: Path) -> bool:
    shown = git(repo, "show", f"{RELEASED_REF}:.claude/hooks/config.json")
    try:
        return shown.returncode == 0 and json.loads(shown.stdout.decode("utf-8")).get(SWITCH) is True
    except (ValueError, UnicodeDecodeError):
        return False


def fetch_daily(repo: Path, today: str) -> None:
    common = git(repo, "rev-parse", "--git-common-dir").stdout.decode("utf-8").strip()
    if not common:
        return
    stamp = (repo / common) if not Path(common).is_absolute() else Path(common)
    stamp = stamp / FETCH_STAMP
    try:
        if stamp.read_text(encoding="utf-8").strip() == today:
            return
    except OSError:
        pass
    try:
        subprocess.run(["git", "-C", str(repo), "fetch", "--quiet", "origin", "main"],
                       capture_output=True, timeout=8)
    except (subprocess.TimeoutExpired, OSError):
        pass  # offline: compare with what the clone already has
    try:
        stamp.write_text(today, encoding="utf-8")
    except OSError:
        pass


def session_notice(project: Path, template_path: str, today: str) -> "str | None":
    """One line for the session start, or None. Never changes the project."""
    if not template_path or template_path.startswith(("git@", "https://", "http://", "ssh://")):
        return None  # no local clone: the switch cannot be read without cloning — run the script
    repo = Path(template_path)
    if not repo.is_dir() or not switch_on(repo):
        return None
    fetch_daily(repo, today)
    report = compare(repo, RELEASED_REF, project)
    if report.error:
        return None
    pending = report.pending()
    to_copy = sum(1 for p in pending if report.files[p] in (OUTDATED, NEW))
    local = len(pending) - to_copy
    if not to_copy and not local and not report.sections:
        return None
    parts = [f"{to_copy} plik(ów) do skopiowania"] if to_copy else []
    if local:
        parts.append(f"{local} zmienionych lokalnie do porównania")
    if report.sections:
        parts.append(f"{len(report.sections)} sekcji CLAUDE.md do przejrzenia")
    return f"🔄 [t-ai] Szablon ma zmiany: {', '.join(parts)} → python3 scripts/update-from-template.py"


def print_report(report: Report, applied: "list[str] | None") -> None:
    pending = report.pending()
    if not pending and not report.sections:
        print("✓ Projekt ma aktualne pliki szablonu.")
        return
    for state in (OUTDATED, NEW, LOCAL):
        group = [p for p in pending if report.files[p] == state]
        if group:
            print(f"\n{LABELS[state]}:")
            for path in group:
                done = applied is not None and path in applied
                print(f"  {'✓' if done else '•'} {path}")
    if report.sections:
        print("\nSekcje do przejrzenia ręcznie (skrypt ich nie zmienia):")
        for line in report.sections:
            print(f"  • {line}")
    if applied is None and any(report.files[p] in (OUTDATED, NEW) for p in pending):
        print("\nSkopiowanie plików „do aktualizacji” i „nowych”: python3 scripts/update-from-template.py --apply")
    elif applied:
        print(f"\nSkopiowano {len(applied)} plik(ów). Przejrzyj zmiany (git diff) i zapisz je na gałęzi roboczej.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aktualizacja projektu z szablonu (ADR-006)")
    parser.add_argument("--apply", action="store_true", help="skopiuj pliki do aktualizacji i nowe")
    args = parser.parse_args()

    repo, ref, tmp, error = resolve_source(ROOT)
    if error:
        print(f"❌ {error}")
        return 1
    try:
        print(f"Źródło: {repo if tmp is None else 'klon z adresu zdalnego'} w stanie {ref}")
        report = compare(repo, ref, ROOT)
        if report.error:
            print(f"❌ {report.error}")
            return 1
        applied = apply(repo, ref, ROOT, report) if args.apply else None
        print_report(report, applied)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
