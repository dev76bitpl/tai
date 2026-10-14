#!/usr/bin/env python3
"""Guided project start — the steps that follow `new-project.py`, one at a time.

  python3 scripts/project-setup.py          # walk through the steps
  python3 scripts/project-setup.py --list   # only print them

Each step says what it is about to do, asks, runs and shows the result. A step that is
already done is skipped, so the script is safe to run again — which is how the remaining
steps get finished after a failed one has been fixed.

When a step fails the script offers to start Claude Code with the step, the command and the
error, so the AI helps with the repair instead of leaving the user alone with a traceback.

Claude Code runs as a child process: when the user leaves it, they are back here. After the
brief interview the script checks what was actually produced; after help with a failed step
it offers to run that step again. Every run ends with a summary.

Without a terminal (AI, script, CI) nothing is asked and nothing is run: the steps are
printed as a list. new-project.py deletes itself after --init; this script stays.
"""
import argparse
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RESUME = "python3 scripts/project-setup.py"

# Issue labels a project starts with: (name, colour, description).
PROJECT_LABELS = [
    ("owner", "D93F0B", "Sprawa czeka na właściciela projektu"),
    ("idea", "FBCA04", "Pomysł: czeka na potwierdzenie, plan albo odrzucenie"),
]

# Look (colours, marks, progress bar) is shared with new-project.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from start_ui import (  # noqa: E402
    BOLD, CYAN, DIM, DONE, FAILED, PENDING, RED, SKIPPED, YELLOW,
    banner, mark, notice, paint, progress, question_line, steps_list, summary,
)
from start_prompts import SCOPE_PROMPT, design_prompt, help_prompt  # noqa: E402
import repo_settings  # noqa: E402
import start_checks  # noqa: E402
from repo_settings import classify_repo_answer  # noqa: E402
from start_checks import SCOPE_SCAFFOLD_MARKER  # noqa: E402,F401


class StepFailed(Exception):
    def __init__(self, command: list[str], code: int, output: str):
        super().__init__(f"{' '.join(command)} (exit {code})")
        self.command, self.code, self.output = command, code, output


# ── seams: everything that talks to the user or runs a process goes through these ──

def is_tty() -> bool:
    return sys.stdin.isatty()


def ask(prompt: str) -> str:
    return input(prompt).strip()


def confirm(question: str, default: bool = True) -> bool:
    """Enter means yes — the steps are what a new project normally wants. default=False
    flips it for things that should happen only on an explicit "t"."""
    answer = ask(question_line(question, "[T/n]" if default else "[t/N]")).lower()
    return default if not answer else answer in ("t", "tak", "y", "yes")


def run(command: list[str], show: bool = False) -> tuple[int, str]:
    """Run in the project root; returns (exit code, combined output). show=True streams it."""
    try:
        process = subprocess.Popen(command, cwd=str(ROOT), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return 127, f"nie znaleziono polecenia: {command[0]}"
    lines: list[str] = []
    for line in process.stdout:
        lines.append(line)
        if show:
            print(f"  {paint('│', DIM)} {paint(line.rstrip(), DIM)}")
    return process.wait(), "".join(lines)


def run_interactive(command: list[str]) -> int:
    """Run a command that talks to the user itself (the terminal stays attached)."""
    return subprocess.call(command, cwd=str(ROOT))


def must(command: list[str], show: bool = False) -> str:
    code, output = run(command, show)
    if code != 0:
        raise StepFailed(command, code, output)
    return output


def start_claude(prompt: str) -> bool:
    """Run Claude Code with `prompt` and come back when the user leaves it.

    A child process, not a replacement of this one — otherwise leaving Claude Code would
    drop the user into an empty terminal with the remaining steps lost. Returns False when
    claude is not installed (nothing was started).
    """
    if not shutil.which("claude"):
        notice(f"Nie znalazłem polecenia `claude`. Uruchom Claude Code w katalogu projektu i wklej: "
               f"{prompt.splitlines()[0]}\n")
        return False
    print(f"\n  {paint('→ Otwieram Claude Code.', CYAN, BOLD)} Gdy skończysz, wyjdź z niego "
          f"({paint('/exit', BOLD)}) — wrócisz do kroków startu.\n")
    # Ctrl+C belongs to Claude Code while it runs; it must not kill this script behind it.
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        subprocess.call(["claude", prompt], cwd=str(ROOT))
    finally:
        signal.signal(signal.SIGINT, previous)
    print(f"\n  {paint('← Z powrotem w krokach startu projektu.', CYAN, BOLD)}\n")
    return True


# ── helpers ──────────────────────────────────────────────────────────────────

def scope_is_filled() -> bool:
    return start_checks.scope_is_filled(ROOT)


def brief_checks() -> list[tuple[bool, str]]:
    return start_checks.brief_checks(ROOT)


def design_checks() -> list[tuple[bool, str]]:
    return start_checks.design_checks(ROOT)


def origin_url() -> str:
    code, output = run(["git", "remote", "get-url", "origin"])
    return output.strip() if code == 0 else ""


# ── steps: return (DONE | SKIPPED, message); raise StepFailed when a command fails ──

def step_git() -> tuple[str, str]:
    if (ROOT / ".git").exists():
        return DONE, "repozytorium Git jest"
    if not confirm("Założyć repozytorium Git (gałąź main)?"):
        return SKIPPED, "pominięte — bez repozytorium strażnicy commita nie działają"
    must(["git", "init", "-q", "-b", "main"])
    must(["git", "config", "--local", "core.autocrlf", "input"])
    return DONE, "założone, gałąź main"


def step_remote() -> tuple[str, str]:
    if not (ROOT / ".git").exists():
        return SKIPPED, "pominięte — najpierw repozytorium Git"
    url = origin_url()
    if url:
        return DONE, f"podpięte: {url}"
    print(paint("  Podaj adres istniejącego repo (git@… / https://…) albo wlasciciel/nazwa nowego.", DIM))
    while True:
        answer = ask(question_line("Repo:", "[Enter = pomiń]"))
        if not answer:
            return SKIPPED, "pominięte — podepniesz później: git remote add origin <adres>"
        kind = classify_repo_answer(answer)
        if kind:
            break
        print(f"  {mark(FAILED)} to nie wygląda na adres ani na wlasciciel/nazwa — spróbuj jeszcze raz")
    if kind == "url":
        must(["git", "remote", "add", "origin", answer])
        return DONE, f"podpięte: {answer}"
    visibility = "--private" if confirm("Repo prywatne?") else "--public"
    must(["gh", "repo", "create", answer, visibility, "--source", ".", "--remote", "origin"], show=True)
    return DONE, f"założone na GitHubie ({visibility.lstrip('-')}) i podpięte: {answer}"


def step_repo_settings() -> tuple[str, str]:
    return repo_settings.step(ROOT, run, confirm, bool(origin_url()))


def step_labels() -> tuple[str, str]:
    if not origin_url():
        return SKIPPED, "pominięte — etykiety zakładam w repo na GitHubie, a żadnego repo nie ma podpiętego"
    # Ask gh, do not read the address: with an SSH host alias (git@github-work:owner/name.git)
    # the URL never contains "github.com", and gh resolves such aliases itself.
    code, repo = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if code == 127:
        return SKIPPED, "pominięte — brak polecenia `gh` (GitHub CLI), etykiety założysz później"
    if code != 0:
        return SKIPPED, "pominięte — podpięte repo nie jest na GitHubie albo `gh` nie ma do niego dostępu"
    existing = set(must(["gh", "label", "list", "--limit", "200", "--json", "name", "--jq", ".[].name"]).split("\n"))
    missing = [label for label in PROJECT_LABELS if label[0] not in existing]
    if not missing:
        return DONE, "etykiety są: " + ", ".join(name for name, _, _ in PROJECT_LABELS)
    names = ", ".join(name for name, _, _ in missing)
    if not confirm(f"Założyć etykiety zgłoszeń: {names}?"):
        return SKIPPED, "pominięte"
    for name, colour, description in missing:
        must(["gh", "label", "create", name, "--color", colour, "--description", description])
    return DONE, f"założone: {names}"


def step_skills() -> tuple[str, str]:
    """Choose which skill groups the project keeps.

    No refresh from the network here: the template's skills work as they are, and a refresh on
    main leaves ~100 changed files that cannot be committed there. Refreshing is maintenance.
    """
    if not (ROOT / "scripts" / "select-skills.py").is_file():
        return SKIPPED, "pominięte — brak scripts/select-skills.py"
    code = run_interactive([sys.executable, "scripts/select-skills.py"])
    if code != 0:
        raise StepFailed([sys.executable, "scripts/select-skills.py"], code, "wybór skilli nie powiódł się")
    print()
    return DONE, "skille w wersji z szablonu"


def step_doctor() -> tuple[str, str]:
    if not (ROOT / "scripts" / "doctor.py").is_file():
        return SKIPPED, "pominięte — brak scripts/doctor.py"
    must([sys.executable, "scripts/doctor.py"], show=True)
    return DONE, "wymagane sprawdzenia przeszły"


def claude_stage(question: str, prompt: str, checks, done: str, later: str) -> tuple[str, str]:
    """A step done inside Claude Code: ask, open it, then check what was actually produced."""
    while True:
        if not confirm(question):
            return SKIPPED, f"pominięte — {later}"
        if not start_claude(prompt):
            return SKIPPED, f"Claude Code nie ruszył — {later}"
        results = checks()
        for ok, label in results:
            print(f"    {mark(DONE if ok else FAILED)} {label}")
        if all(ok for ok, _ in results):
            return DONE, done
        print()
        question = "Czegoś brakuje. Wrócić do Claude Code i dokończyć?"
        later = "brakuje: " + "; ".join(label for ok, label in results if not ok) + f" — {later}"


def step_brief() -> tuple[str, str]:
    if all(ok for ok, _ in brief_checks()):
        return DONE, "brief, stos i ADR-001 już są — wywiad pominięty"
    if scope_is_filled():
        question = "Brief już jest, ale nie wszystko po nim. Otworzyć Claude Code, żeby dokończyć (stos, ADR-001)?"
    else:
        question = "Ustalamy brief projektu teraz? (wywiad: co budujemy, dla kogo, w jakim stosie)"
    return claude_stage(question, SCOPE_PROMPT, brief_checks, "brief gotowy, strażnicy ustawieni pod stos",
                        "później: uruchom `claude` w katalogu projektu i napisz: scope")


IMPECCABLE_INSTALL = ["npx", "impeccable", "install", "--providers=claude", "--scope=project", "--no-hooks"]


def offer_impeccable() -> None:
    """Optionally install the impeccable design skill into this project — only on an explicit yes.

    It is not part of the template: the template's security scan stops on its bundled scripts.
    --no-hooks keeps the installer away from .claude/settings.local.json, where the guards live.
    """
    if (ROOT / ".claude" / "skills" / "impeccable").exists():
        return
    print(paint("  impeccable to osobne narzędzie do projektowania (poza szablonem): instalator zapisze", DIM))
    print(paint("  .claude/skills/impeccable w projekcie i pobierze swój program do ~/.impeccable/bin.", DIM))
    if not confirm("Zainstalować skill impeccable w tym projekcie?", default=False):
        return
    code = run_interactive(IMPECCABLE_INSTALL)
    if code != 0:
        notice(f"Instalacja impeccable nie powiodła się (kod {code}) — szablon graficzny powstanie bez niego. "
               f"Ręcznie: {' '.join(IMPECCABLE_INSTALL)}")
    print()


def step_design() -> tuple[str, str]:
    if all(ok for ok, _ in design_checks()):
        return DONE, "szablon graficzny już jest — makiety i zasady wyglądu"
    if not (ROOT / ".claude" / "skills" / "design-taste-frontend").exists():
        notice("Grupa skilli „Projektowanie wyglądu” nie jest w projekcie — szablon powstanie na pozostałych. "
               "Przywrócisz ją: python3 scripts/select-skills.py")
    offer_impeccable()
    return claude_stage(
        "Założyć szablon graficzny projektu? (makiety dwóch kierunków wyglądu; projekt bez interfejsu: n)",
        design_prompt((ROOT / ".claude" / "skills" / "impeccable").exists()), design_checks, "szablon graficzny gotowy: makiety i zasady wyglądu",
        "później: uruchom `claude` i poproś o szablon graficzny projektu")


# (title, the command shown in the plain list, one line saying what the step is for, function)
# Brief first: its stack proposes the skill groups, and the design stage reads the brief.
# Skille before the design stage, so it already runs in a project without the unneeded skills.
STEPS = [
    ("Repozytorium Git", "git init -b main",
     "Historia zmian projektu. Bez niej strażnicy commita nie mają czego pilnować.", step_git),
    ("Repo na GitHubie", "git remote add origin <adres>   albo   gh repo create <wlasciciel/nazwa>",
     "Miejsce na kod, zgłoszenia i pull requesty. Nic nie jest wypychane.", step_remote),
    ("Ustawienia repo", "gh api …   # kasowanie gałęzi po scaleniu, uprawnienia automatów — docs/GUARDS.md",
     "Dwa ustawienia, bez których automat wydań pada, a gałęzie zostają po scaleniu.", step_repo_settings),
    ("Etykiety zgłoszeń", "gh label create owner / idea",
     "Dwie etykiety, po których widać sprawy czekające na właściciela i pomysły.", step_labels),
    ("Kontrola środowiska", "python3 scripts/doctor.py",
     "Sprawdzenie, czy narzędzia i strażnicy naprawdę działają na tej maszynie.", step_doctor),
    ("Brief projektu", "claude   # napisz: scope — wywiad ustawi też strażników pod Twój stos",
     "Krótki wywiad z Claude: co budujemy, dla kogo i w jakim stosie.", step_brief),
    ("Skille", "python3 scripts/select-skills.py",
     "Wybór, które zestawy instrukcji dla Claude zostają w projekcie — reszta to szum.", step_skills),
    ("Szablon graficzny", "claude   # poproś: przygotuj szablon graficzny projektu (makiety w mockups/propozycje/)",
     "Dwa kierunki wyglądu do obejrzenia w przeglądarce i zasady, których trzymają się kolejne ekrany.", step_design),
]


# ── flow ─────────────────────────────────────────────────────────────────────

def handle_failure(title: str, failure: StepFailed) -> bool:
    """Show the failure, offer the AI's help; True when the step should be run again."""
    print(f"  {mark(FAILED)} {paint('nie udało się:', RED, BOLD)} {' '.join(failure.command)}  "
          f"{paint(f'(kod {failure.code})', DIM)}")
    for line in failure.output.strip().splitlines()[-8:]:
        print(f"  {paint('│', RED)} {line}")
    print()
    if confirm("Poprosić Claude o pomoc z tym krokiem?"):
        start_claude(help_prompt(title, " ".join(failure.command), failure.code, failure.output, RESUME))
    return confirm("Ponowić ten krok teraz?")


def print_banner() -> None:
    banner("🚀 Start projektu", ROOT.name,
           f"{len(STEPS)} kroków. Enter wybiera odpowiedź domyślną; Ctrl+C przerywa — "
           "dokończysz później tym samym poleceniem.")
    print()


def what_is_left(results: list[tuple[str, str, str]]) -> list[str]:
    marks = {title: symbol for title, symbol, _ in results}
    todo: list[str] = []
    if FAILED in marks.values() or PENDING in marks.values():
        todo.append(f"dokończ kroki: {RESUME}  (zrobione zostaną pominięte)")
    if DONE in (marks.get("Brief projektu"), marks.get("Skille"), marks.get("Szablon graficzny")):
        todo.append("zapisz wynik startu na gałęzi roboczej (na main commit jest zablokowany): "
                    "git switch -c chore/project-start, potem git add docs/ mockups/ "
                    ".claude/hooks/config.json skills-manifest.json .claude/skills i commit")
    if marks.get("Repo na GitHubie") == SKIPPED:
        todo.append("podepnij repo, gdy będzie: git remote add origin <adres>")
    return todo


def run_steps() -> tuple[list[tuple[str, str, str]], bool]:
    """Walk the steps; returns (results for the summary, True when nothing failed)."""
    results: list[tuple[str, str, str]] = []
    total = len(STEPS)
    for number, (title, _, why, step) in enumerate(STEPS, start=1):
        print(f"  {progress(number, total)}  {paint(f'Krok {number}/{total}', DIM)} {paint('·', DIM)} {paint(title, BOLD)}")
        print(paint(f"  {why}", DIM))
        while True:
            try:
                symbol, message = step()
            except StepFailed as failure:
                if handle_failure(title, failure):
                    print()
                    continue
                results.append((title, FAILED, f"nie udało się: {' '.join(failure.command)}"))
                results.extend((later, PENDING, "nie doszło — czeka na naprawę poprzedniego kroku")
                               for later, _, _, _ in STEPS[number:])
                return results, False
            break
        print(f"  {mark(symbol)} {message}\n")
        results.append((title, symbol, message))
    return results, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guided project start — the steps after new-project.py.")
    parser.add_argument("--list", action="store_true", help="print the steps without running them")
    args = parser.parse_args(argv)

    if args.list or not is_tty():
        steps_list([(title, command) for title, command, _, _ in STEPS], RESUME)
        return 0

    print_banner()
    try:
        results, complete = run_steps()
    except (KeyboardInterrupt, EOFError):
        print(f"\n\n  {paint('Przerwane.', YELLOW, BOLD)} Dokończ później: {paint(RESUME, BOLD)}\n")
        return 130
    summary(results, what_is_left(results), complete, RESUME)
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())
