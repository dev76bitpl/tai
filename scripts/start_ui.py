"""Look of the project-start scripts: colours, marks, progress bar, section headers.

One place so new-project.py (cleaning) and project-setup.py (guided steps) read as one tool.
Colours only on a real terminal — the same rule as doctor.py: NO_COLOR switches them off,
FORCE_COLOR=1 switches them on, anything that is not a terminal gets plain text.
Stays in the project (project-setup.py needs it after new-project.py removes itself).
"""
import os
import sys

if os.name == "nt":
    os.system("")  # enable ANSI escape sequences on Windows 10+ terminals

DONE, SKIPPED, FAILED, PENDING, PLANNED = "✓", "–", "✗", "·", "○"

_USE_COLOR = (sys.stdout.isatty() and not os.environ.get("NO_COLOR")) or os.environ.get("FORCE_COLOR") == "1"
BOLD, DIM, RED, GREEN, YELLOW, CYAN = "1", "2", "31", "32", "33", "36"
MARK_COLOUR = {DONE: GREEN, SKIPPED: YELLOW, FAILED: RED, PENDING: DIM, PLANNED: DIM}


def paint(text: str, *codes: str) -> str:
    return f"\033[{';'.join(codes)}m{text}\033[0m" if _USE_COLOR and codes else text


def mark(symbol: str) -> str:
    return paint(symbol, MARK_COLOUR.get(symbol, DIM), BOLD)


def progress(done: int, total: int) -> str:
    return paint("▰" * done, GREEN) + paint("▱" * (total - done), DIM)


def question_line(question: str, hint: str) -> str:
    return f"  {paint('?', CYAN, BOLD)} {paint(question, BOLD)} {paint(hint, DIM)} "


def banner(title: str, name: str, note: str) -> None:
    print()
    print(f"  {paint(title, BOLD)} {paint('·', DIM)} {paint(name, CYAN, BOLD)}")
    print(paint(f"  {note}", DIM))


def section(title: str) -> None:
    print(f"\n  {paint(title, BOLD)}")


def item(label: str, text: str, planned: bool = False) -> None:
    """One line of work done (or, in a dry run, only planned)."""
    symbol = PLANNED if planned else DONE
    print(f"  {mark(symbol)} {paint(f'{label:<12}', DIM)} {paint(text, DIM) if planned else text}")


def notice(text: str) -> None:
    print(f"  {paint('⚠', YELLOW, BOLD)} {text}")


def steps_list(steps: list[tuple[str, str]], resume: str) -> None:
    """Plain list of (title, command) — what a run without a terminal prints instead of asking."""
    print("── Kroki startu projektu ───────────────────────────────\n")
    for number, (title, command) in enumerate(steps, start=1):
        print(f"  # {number}. {title}")
        print(f"  {command}\n")
    print(f"  Z terminala przeprowadzi przez nie: {resume}")
    print("────────────────────────────────────────────────────────\n")


def summary(results: list[tuple[str, str, str]], todo: list[str], complete: bool, resume: str) -> None:
    """Results as (title, mark, message), what is left to do, and the closing line."""
    width = max(len(title) for title, _, _ in results) + 2
    print(f"  {paint('Podsumowanie', BOLD)}")
    print(paint("  " + "─" * 54, DIM))
    for title, symbol, message in results:
        print(f"  {mark(symbol)} {title:<{width}}{paint(message, DIM)}")
    if todo:
        print(f"\n  {paint('Co dalej', BOLD)}")
        for number, entry in enumerate(todo, start=1):
            print(f"  {paint(f'{number}.', CYAN, BOLD)} {entry}")
    print()
    if complete:
        print(f"  {paint('✅ Start projektu zakończony.', GREEN, BOLD)}\n")
    else:
        print(f"  {paint('⚠ Start niedokończony', YELLOW, BOLD)} — po naprawie: {paint(resume, BOLD)}\n")
