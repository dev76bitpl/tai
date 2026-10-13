#!/usr/bin/env python3
"""Guided project start — the steps that follow `new-project.py`, one at a time.

  python3 scripts/project-setup.py          # walk through the steps
  python3 scripts/project-setup.py --list   # only print them

Each step says what it is about to do, asks, runs and shows the result. A step that is
already done is skipped, so the script is safe to run again — which is how the remaining
steps get finished after a failed one has been fixed.

When a step fails the script offers to start Claude Code with the step, the command and the
error, so the AI helps with the repair instead of leaving the user alone with a traceback.

Without a terminal (AI, script, CI) nothing is asked and nothing is run: the steps are
printed as a list. new-project.py deletes itself after --init; this script stays.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
RESUME = "python3 scripts/project-setup.py"

# A line only the template's own docs/PROJECT_SCOPE.md skeleton contains. While it is there the
# file is a form to fill in, not a brief (a test pins the marker to the real skeleton).
SCOPE_SCAFFOLD_MARKER = "sekcje są scaffoldem"

# Issue labels a project starts with: (name, colour, description).
PROJECT_LABELS = [
    ("owner", "D93F0B", "Sprawa czeka na właściciela projektu"),
    ("idea", "FBCA04", "Pomysł: czeka na potwierdzenie, plan albo odrzucenie"),
]

DONE, SKIPPED = "✓", "–"


class StepFailed(Exception):
    def __init__(self, command: list[str], code: int, output: str):
        super().__init__(f"{' '.join(command)} (exit {code})")
        self.command, self.code, self.output = command, code, output


# ── seams: everything that talks to the user or runs a process goes through these ──

def is_tty() -> bool:
    return sys.stdin.isatty()


def ask(prompt: str) -> str:
    return input(prompt).strip()


def confirm(question: str) -> bool:
    """Enter means yes — the steps are what a new project normally wants."""
    return ask(f"  {question} [T/n]: ").lower() in ("", "t", "tak", "y", "yes")


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
            print(f"    {line}", end="")
    return process.wait(), "".join(lines)


def must(command: list[str], show: bool = False) -> str:
    code, output = run(command, show)
    if code != 0:
        raise StepFailed(command, code, output)
    return output


def start_claude(prompt: str) -> None:
    """Hand the terminal over to Claude Code. Does not return when claude is installed."""
    if not shutil.which("claude"):
        print("  ⚠ Nie znalazłem polecenia `claude`. Uruchom Claude Code w katalogu projektu i wklej:")
        print(f"    {prompt.splitlines()[0]}\n")
        return
    os.chdir(ROOT)
    os.execvp("claude", ["claude", prompt])


# ── helpers ──────────────────────────────────────────────────────────────────

def scope_is_filled() -> bool:
    """True when the project already has its own brief in docs/PROJECT_SCOPE.md."""
    scope = ROOT / "docs" / "PROJECT_SCOPE.md"
    if not scope.is_file():
        return False
    text = scope.read_text(encoding="utf-8", errors="ignore")
    return bool(text.strip()) and SCOPE_SCAFFOLD_MARKER not in text


def origin_url() -> str:
    code, output = run(["git", "remote", "get-url", "origin"])
    return output.strip() if code == 0 else ""


def classify_repo_answer(answer: str) -> str:
    """'url' for an existing repository address, 'slug' for owner/name to create, else ''."""
    if "://" in answer or answer.startswith("git@") or answer.endswith(".git"):
        return "url"
    return "slug" if re.fullmatch(r"[\w.-]+/[\w.-]+", answer) else ""


# ── steps: return (DONE | SKIPPED, message); raise StepFailed when a command fails ──

def step_git() -> tuple[str, str]:
    if (ROOT / ".git").exists():
        return DONE, "repozytorium Git jest"
    if not confirm("Założyć repozytorium Git (gałąź main)?"):
        return SKIPPED, "pominięte — bez repozytorium strażnicy commita nie działają"
    must(["git", "init", "-q", "-b", "main"])
    return DONE, "założone, gałąź main"


def step_remote() -> tuple[str, str]:
    if not (ROOT / ".git").exists():
        return SKIPPED, "pominięte — najpierw repozytorium Git"
    url = origin_url()
    if url:
        return DONE, f"podpięte: {url}"
    print("  Podaj adres istniejącego repo (git@… / https://…)")
    print("  albo nazwę nowego do założenia na GitHubie (wlasciciel/nazwa). Enter = pomiń.")
    while True:
        answer = ask("  Repo: ")
        if not answer:
            return SKIPPED, "pominięte — podepniesz później: git remote add origin <adres>"
        kind = classify_repo_answer(answer)
        if kind:
            break
        print("  ❌ to nie wygląda na adres ani na wlasciciel/nazwa")
    if kind == "url":
        must(["git", "remote", "add", "origin", answer])
        return DONE, f"podpięte: {answer}"
    visibility = "--private" if confirm("Repo prywatne?") else "--public"
    must(["gh", "repo", "create", answer, visibility, "--source", ".", "--remote", "origin"], show=True)
    return DONE, f"założone na GitHubie ({visibility.lstrip('-')}) i podpięte: {answer}"


def step_labels() -> tuple[str, str]:
    url = origin_url()
    if "github.com" not in url:
        return SKIPPED, "pominięte — etykiety zakładam w repo na GitHubie, a takiego nie ma podpiętego"
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
    if not (ROOT / "scripts" / "update-skills.py").is_file():
        return SKIPPED, "pominięte — brak scripts/update-skills.py"
    if not confirm("Zainstalować vendored skille (pobiera z sieci)?"):
        return SKIPPED, "pominięte — później: python3 scripts/update-skills.py --apply"
    must([sys.executable, "scripts/update-skills.py", "--apply"], show=True)
    return DONE, "skille zainstalowane"


def step_doctor() -> tuple[str, str]:
    if not (ROOT / "scripts" / "doctor.py").is_file():
        return SKIPPED, "pominięte — brak scripts/doctor.py"
    must([sys.executable, "scripts/doctor.py"], show=True)
    return DONE, "wymagane sprawdzenia przeszły"


def step_brief() -> tuple[str, str]:
    if scope_is_filled():
        return DONE, ("brief już jest (docs/PROJECT_SCOPE.md) — wywiad pominięty; "
                      "strażników pod stos ustawia: python3 scripts/set-stack.py <stos>")
    if not confirm("Ustalamy brief projektu teraz? (wywiad: co budujemy, dla kogo, w jakim stosie)"):
        return SKIPPED, "pominięte — później: uruchom `claude` w katalogu projektu i napisz: scope"
    start_claude("scope")
    return SKIPPED, "wywiad nie ruszył — napisz `scope` w Claude Code"


STEPS = [
    ("Repozytorium Git", "git init -b main", step_git),
    ("Repo na GitHubie", "git remote add origin <adres>   albo   gh repo create <wlasciciel/nazwa>", step_remote),
    ("Etykiety zgłoszeń", "gh label create owner / idea", step_labels),
    ("Skille", "python3 scripts/update-skills.py --apply", step_skills),
    ("Kontrola środowiska", "python3 scripts/doctor.py", step_doctor),
    ("Brief projektu", "claude   # napisz: scope — wywiad ustawi też strażników pod Twój stos", step_brief),
]


# ── flow ─────────────────────────────────────────────────────────────────────

def print_steps() -> None:
    print("── Kroki startu projektu ───────────────────────────────\n")
    for number, (title, command, _) in enumerate(STEPS, start=1):
        print(f"  # {number}. {title}")
        print(f"  {command}\n")
    print(f"  Z terminala przeprowadzi przez nie: {RESUME}")
    print("────────────────────────────────────────────────────────\n")


def help_prompt(title: str, failure: StepFailed) -> str:
    tail = "\n".join(failure.output.strip().splitlines()[-30:])[-3000:]
    return (
        f"Krok startu projektu „{title}” nie powiódł się.\n"
        f"Polecenie: {' '.join(failure.command)}\n"
        f"Kod wyjścia: {failure.code}\n"
        f"Końcówka wyniku:\n{tail or '(brak wyniku)'}\n\n"
        f"Pomóż mi to naprawić. Po naprawie pozostałe kroki dokończy: {RESUME}"
    )


def handle_failure(title: str, failure: StepFailed) -> None:
    print(f"  ✗ nie udało się: {' '.join(failure.command)}  (kod {failure.code})")
    for line in failure.output.strip().splitlines()[-8:]:
        print(f"    {line}")
    print()
    if confirm("Poprosić Claude o pomoc z tym krokiem?"):
        start_claude(help_prompt(title, failure))
    print(f"  Po naprawie dokończ pozostałe kroki: {RESUME}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guided project start — the steps after new-project.py.")
    parser.add_argument("--list", action="store_true", help="print the steps without running them")
    args = parser.parse_args(argv)

    if args.list or not is_tty():
        print_steps()
        return 0

    try:
        for number, (title, _, step) in enumerate(STEPS, start=1):
            print(f"── Krok {number}/{len(STEPS)}: {title}")
            try:
                mark, message = step()
            except StepFailed as failure:
                handle_failure(title, failure)
                return 1
            print(f"  {mark} {message}\n")
    except (KeyboardInterrupt, EOFError):
        print(f"\n  Przerwane. Dokończ później: {RESUME}\n")
        return 130
    print("✅  Start projektu zakończony.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
