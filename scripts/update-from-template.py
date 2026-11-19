#!/usr/bin/env python3
"""
Pokazuje, co projekt może wciągnąć z szablonu (ADR-006), i na życzenie to kopiuje.

Użycie:
    python3 scripts/update-from-template.py           # podgląd, niczego nie zmienia
    python3 scripts/update-from-template.py --apply   # kopiuje pliki „do aktualizacji” i „nowe”
    python3 scripts/update-from-template.py --accept PLIK "powód"   # różnica celowa, przestań zgłaszać
    python3 scripts/update-from-template.py --accept-section "## Nagłówek" "powód"   # to samo dla sekcji CLAUDE.md

Źródłem jest wydany `main` szablonu (origin/main lokalnego klona albo świeży klon z adresu),
nigdy jego katalog roboczy (#179). Listę plików szablonu czyta z `template-files.json`
w tym samym wydaniu. Plik zmieniony w projekcie nie jest nadpisywany, a `CLAUDE.md` tylko
porównywany po sekcjach.

Plik zmieniony lokalnie po przeglądzie można przyjąć jako celowo inny (`--accept`, tai#286):
wpis z powodem trafia do `.claude/template-accepted.json` i plik przestaje się liczyć do
zgłoszeń. Przyjęcie dotyczy wersji szablonu z chwili przyjęcia — gdy szablon zmieni plik,
wraca on do porównania. Tak samo sekcja `CLAUDE.md` (`--accept-section`, tai#292): przyjęcie
trzyma treść sekcji szablonu i wygasa, gdy szablon ją zmieni.
"""
import argparse
import datetime
import fnmatch
import hashlib
import importlib.util
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

ACCEPTED_FILE = ".claude/template-accepted.json"  # project-only: never on the template list
MIN_REASON_WORDS = 3  # the same bar as [skip-sync] (sync_ack.py)

CURRENT, OUTDATED, NEW, LOCAL, ACCEPTED = "current", "outdated", "new", "local", "accepted"
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
    released: dict[str, str] = field(default_factory=dict)  # path -> released blob id
    accepted: dict[str, str] = field(default_factory=dict)  # path -> reason, still valid
    expired: dict[str, str] = field(default_factory=dict)  # path -> accepted date, template changed since
    section_hashes: dict[str, str] = field(default_factory=dict)  # "CLAUDE.md: ## X" -> template body hash
    accepted_sections: dict[str, str] = field(default_factory=dict)  # same key -> reason, still valid
    expired_sections: dict[str, str] = field(default_factory=dict)  # same key -> accepted date

    def pending(self) -> list[str]:
        return [p for p, s in self.files.items() if s not in (CURRENT, ACCEPTED)]


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
    """The blob id git stores for this file under `* text=auto eol=lf`. A text file (no NUL in the
    first 8000 bytes, git's own test) has CRLF folded to LF first, so a CRLF checkout of an unchanged
    file matches the template history instead of counting as a local change (the same rule as
    git_blob in update-skills.py)."""
    data = file.read_bytes()
    if b"\0" not in data[:8000]:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


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


def section_hash(body: str) -> str:
    return hashlib.sha1(body.encode("utf-8")).hexdigest()


def section_diffs(repo: Path, ref: str, project: Path, names: list[str]) -> list[tuple[str, str, str]]:
    """(key, report line, template body hash) for every section new or different in the template."""
    found = []
    for name in names:
        shown = git(repo, "show", f"{ref}:{name}")
        local = project / name
        if shown.returncode != 0 or not local.is_file():
            continue
        theirs = sections(shown.stdout.decode("utf-8"))
        ours = sections(local.read_text(encoding="utf-8"))
        for header, body in theirs.items():
            key = f"{name}: {header}"
            if header not in ours:
                found.append((key, f"{key}  (nowa w szablonie)", section_hash(body)))
            elif ours[header] != body:
                found.append((key, f"{key}  (inna niż w szablonie)", section_hash(body)))
    return found


def compare_sections(repo: Path, ref: str, project: Path, names: list[str]) -> list[str]:
    return [line for _, line, _ in section_diffs(repo, ref, project, names)]


def _accepted_part(project: Path, part: str) -> dict:
    try:
        data = json.loads((project / ACCEPTED_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    found = data.get(part) if isinstance(data, dict) else None
    return found if isinstance(found, dict) else {}


def read_accepted(project: Path) -> dict:
    """path -> {"reason", "template_blob", "date"}; an unreadable file counts as empty."""
    return _accepted_part(project, "files")


def read_accepted_sections(project: Path) -> dict:
    """"CLAUDE.md: ## X" -> {"reason", "template_hash", "date"} (tai#292)."""
    return _accepted_part(project, "sections")


def write_accepted(project: Path, files: dict, sections: "dict | None" = None) -> None:
    target = project / ACCEPTED_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    if sections is None:
        sections = read_accepted_sections(project)
    data = {
        "_comment": "Template files and CLAUDE.md sections this project keeps different on purpose "
                    "(tai#286, tai#292). Written by scripts/update-from-template.py --accept / "
                    "--accept-section. An entry holds while the template file stays at template_blob "
                    "(a section: at template_hash); once the template changes it, it is compared again.",
        "files": dict(sorted(files.items())),
    }
    if sections:
        data["sections"] = dict(sorted(sections.items()))
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compare(repo: Path, ref: str, project: Path) -> Report:
    """Classify every template file in `project` against the template at `ref`."""
    spec = read_list(repo, ref)
    if spec is None:
        return Report(error=f"{ref} szablonu nie ma czytelnego {LIST_FILE} (szablon sprzed ADR-006?)")
    paths = template_paths(repo, ref, spec)
    released = released_blobs(repo, ref, paths)
    history = historical_blobs(repo, ref, paths)
    accepted = read_accepted(project)
    report = Report(released=released)
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
            entry = accepted.get(path)
            if isinstance(entry, dict) and entry.get("template_blob") == released.get(path):
                report.files[path] = ACCEPTED
                report.accepted[path] = str(entry.get("reason", ""))
            else:
                report.files[path] = LOCAL
                if isinstance(entry, dict):
                    report.expired[path] = str(entry.get("date", ""))
    accepted_sections = read_accepted_sections(project)
    for key, line, digest in section_diffs(repo, ref, project, spec.get("compare_sections", [])):
        report.section_hashes[key] = digest
        entry = accepted_sections.get(key)
        if isinstance(entry, dict) and entry.get("template_hash") == digest:
            report.accepted_sections[key] = str(entry.get("reason", ""))
            continue
        if isinstance(entry, dict):
            report.expired_sections[key] = str(entry.get("date", ""))
            line += f"  (przyjęta {entry.get('date', '')}, szablon od tego czasu ją zmienił)"
        report.sections.append(line)
    return report


def accept(project: Path, report: Report, path: str, reason: str, today: str) -> str:
    """Record `path` as deliberately different; returns an error message or ''."""
    words = len(re.findall(r"\w+", reason or ""))
    if words < MIN_REASON_WORDS:
        return f"podaj powód, co najmniej {MIN_REASON_WORDS} słowa (np. \"własny krok OSV w CI\")"
    state = report.files.get(path)
    if state is None:
        return f"{path} nie jest plikiem szablonu"
    if state not in (LOCAL, ACCEPTED):  # ACCEPTED: a new reason replaces the old one
        return f"{path} nie jest zmieniony lokalnie (stan: {state}) — nie ma czego przyjmować"
    files = read_accepted(project)
    files[path] = {"reason": reason.strip(), "template_blob": report.released[path], "date": today}
    write_accepted(project, files, read_accepted_sections(project))
    return ""


def accept_section(project: Path, report: Report, header: str, reason: str, today: str) -> str:
    """Record a CLAUDE.md section as deliberately different (tai#292); returns an error message or ''."""
    words = len(re.findall(r"\w+", reason or ""))
    if words < MIN_REASON_WORDS:
        return f"podaj powód, co najmniej {MIN_REASON_WORDS} słowa (np. \"blok Next.js dopisuje next dev\")"
    wanted = header.strip()
    keys = [k for k in report.section_hashes if k == wanted or k.split(": ", 1)[1] == wanted]
    if not keys:
        return f"„{wanted}” nie jest sekcją inną niż w szablonie — podaj nagłówek dokładnie jak w podglądzie"
    if len(keys) > 1:
        return f"„{wanted}” pasuje do kilku plików: {', '.join(keys)} — podaj „PLIK: nagłówek”"
    sections = read_accepted_sections(project)
    sections[keys[0]] = {"reason": reason.strip(), "template_hash": report.section_hashes[keys[0]], "date": today}
    write_accepted(project, read_accepted(project), sections)
    return ""


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
    if report.accepted or report.accepted_sections:
        print("\ncelowo inne (przyjęte, nie zgłaszane):")
        for path, reason in sorted({**report.accepted, **report.accepted_sections}.items()):
            print(f"  · {path} — {reason}")
    if not pending and not report.sections:
        print("\n✓ Projekt ma aktualne pliki szablonu.")
        return
    for state in (OUTDATED, NEW, LOCAL):
        group = [p for p in pending if report.files[p] == state]
        if group:
            print(f"\n{LABELS[state]}:")
            for path in group:
                done = applied is not None and path in applied
                note = f"  (przyjęty {report.expired[path]}, szablon od tego czasu go zmienił)" \
                    if path in report.expired else ""
                print(f"  {'✓' if done else '•'} {path}{note}")
    if any(report.files[p] == LOCAL for p in pending):
        print("\nRóżnica celowa? python3 scripts/update-from-template.py --accept PLIK \"powód\"")
    if report.sections:
        print("\nSekcje do przejrzenia ręcznie (skrypt ich nie zmienia):")
        for line in report.sections:
            print(f"  • {line}")
        print("Sekcja celowo inna? python3 scripts/update-from-template.py --accept-section \"## Nagłówek\" \"powód\"")
    if applied is None and any(report.files[p] in (OUTDATED, NEW) for p in pending):
        print("\nSkopiowanie plików „do aktualizacji” i „nowych”: python3 scripts/update-from-template.py --apply")
    elif applied:
        print(f"\nSkopiowano {len(applied)} plik(ów). Przejrzyj zmiany (git diff) i zapisz je na gałęzi roboczej.")


GUARD_STACK = "scripts/dev-guards/stack.py"


def blocking_guard_commands(repo: Path, ref: str, project: Path) -> list[str]:
    """Lint/test commands in the project's config.json that the RELEASED guards will refuse to run.

    Since #185 such a command blocks every commit, so a project that inherited `composer lint`
    from an old template learns it here, before --apply, not from its first failed commit.
    The released stack.py decides — the project's own copy may predate the rule.
    """
    shown = git(repo, "show", f"{ref}:{GUARD_STACK}")
    if shown.returncode != 0:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "released_stack.py"
        source.write_bytes(shown.stdout)
        try:
            spec = importlib.util.spec_from_file_location("released_stack", source)
            stack = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stack)
            stack.REPO_ROOT = project
            stack.CONFIG_PATH = project / ".claude" / "hooks" / "config.json"
            stack.LOCAL_CONFIG_PATH = stack.CONFIG_PATH.with_name("config.local.json")
            stack.get_project_root = lambda: project
            found = []
            for kind in ("lint", "test"):
                cmd, explicit = stack.get_cmd(kind)
                reason = stack.why_unavailable(cmd) if explicit and cmd else ""
                if reason:
                    found.append(f"„{kind}”: {' '.join(cmd)} — {reason}")
            return found
        except Exception:
            return []  # an older release without these helpers: nothing to say


def print_guard_warnings(found: list[str]) -> None:
    if not found:
        return
    print("\n⚠️  Po aktualizacji strażnicy commita zablokują KAŻDY commit — tych poleceń"
          " z .claude/hooks/config.json (albo config.local.json) nie da się uruchomić:")
    for line in found:
        print(f"   {line}")
    print("   Popraw wpis albo go usuń (zostanie polecenie dla stosu): docs/GUARDS.md, „Konfiguracja strażników”.")


SETTINGS_EXAMPLE = ".claude/settings.local.json.example"


def wire_hooks(project: Path, template_example: "Path | None" = None) -> None:
    """Wire the template hooks the project's settings.local.json lacks (#268) — with the copy just
    taken, so a project whose own file never ran session-context.py starts hearing about template
    changes. Runs as a separate process: the module is fresh from the copy. The template's example
    goes along: a project that changed its own example keeps it, so a new hook is not in it (#282)."""
    script = project / "scripts" / "claude_settings.py"
    if script.is_file():
        extra = ["--template-example", str(template_example)] if template_example else []
        subprocess.run([sys.executable, str(script), *extra], cwd=project)


SELF = "scripts/update-from-template.py"


def after_apply(project: Path, repo: "Path | None" = None, ref: str = "") -> None:
    """Steps after the files are copied. A new step goes here; see run_after_apply.
    Without repo/ref (the fresh copy started with --after-apply) the template is found again."""
    tmp = None
    if repo is None:
        repo, ref, tmp, error = resolve_source(project)
    with tempfile.TemporaryDirectory(prefix="ai-template-example-") as scratch:
        example = None
        if repo is not None:
            shown = git(repo, "show", f"{ref}:{SETTINGS_EXAMPLE}")
            if shown.returncode == 0:
                example = Path(scratch) / "settings.local.json.example"
                example.write_bytes(shown.stdout)
        try:
            wire_hooks(project, example)
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)


def run_after_apply(project: Path, applied: "list[str]", repo: "Path | None" = None, ref: str = "") -> None:
    """When --apply replaced this very script, the steps after copying come from the fresh copy,
    not from the old code still running (#271): otherwise a step added in the new version would
    wait for a second --apply."""
    fresh = project / SELF
    if SELF in applied and fresh.is_file():
        subprocess.run([sys.executable, str(fresh), "--after-apply"], cwd=project)
    else:
        after_apply(project, repo, ref)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aktualizacja projektu z szablonu (ADR-006)")
    parser.add_argument("--apply", action="store_true", help="skopiuj pliki do aktualizacji i nowe")
    parser.add_argument("--accept", nargs=2, metavar=("PLIK", "POWÓD"),
                        help="zapisz plik zmieniony lokalnie jako celowo inny, z powodem")
    parser.add_argument("--accept-section", nargs=2, metavar=("NAGŁÓWEK", "POWÓD"),
                        help="zapisz sekcję CLAUDE.md inną niż w szablonie jako celowo inną, z powodem")
    parser.add_argument("--after-apply", action="store_true",
                        help="tylko kroki po skopiowaniu (wywołuje je --apply, gdy podmienił ten skrypt)")
    args = parser.parse_args()
    if args.after_apply:
        after_apply(ROOT)
        return 0

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
        if args.accept:
            path, reason = args.accept
            error = accept(ROOT, report, path, reason, datetime.date.today().isoformat())
            if error:
                print(f"❌ {error}")
                return 1
            print(f"✓ {path} przyjęty jako celowo inny ({ACCEPTED_FILE}). Zapisz plik w commicie.")
            return 0
        if args.accept_section:
            header, reason = args.accept_section
            error = accept_section(ROOT, report, header, reason, datetime.date.today().isoformat())
            if error:
                print(f"❌ {error}")
                return 1
            print(f"✓ sekcja „{header}” przyjęta jako celowo inna ({ACCEPTED_FILE}). Zapisz plik w commicie.")
            return 0
        applied = apply(repo, ref, ROOT, report) if args.apply else None
        print_report(report, applied)
        print_guard_warnings(blocking_guard_commands(repo, ref, ROOT))
        if args.apply:
            run_after_apply(ROOT, applied, repo, ref)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
