"""Data for scripts/new-project.py: what to copy, what to remove, document skeletons.

Kept apart from the logic so new-project.py stays readable (file-size rule: data files have
no limit, logic files do). Template-only, like new-project.py itself: removed by --init
(TEMPLATE_ONLY_SCRIPTS).
"""

# Scripts that exist only to start a project from the template.
TEMPLATE_ONLY_SCRIPTS = ["new-project.py", "new_project_data.py", "new_project_git.py"]

SCAFFOLD_DOCS: dict[str, str] = {
    "TASKS.md": """\
# Tasks

Ten plik jest **logiem sesji**: co się wydarzyło i dlaczego. Otwarta praca żyje w GitHub Issues
(`gh issue list`), nie tutaj. Fazy definiuje [docs/ROADMAP.md](ROADMAP.md).
Wzór wpisu: [docs/examples/TASKS.example.md](examples/TASKS.example.md).

---

## Stan sesji

<!-- Najnowszy wpis na górze. Jeden akapit na domknięty krok: data, co się zmieniło po ludzku,
     potem technicznie (pliki, funkcje, pułapki). -->
""",
}

# ── What to remove + replace in --init mode ──────────────────────────────────

README_SCAFFOLD = """\
# [Nazwa projektu]

> Krótki opis — co to jest i dla kogo.

---

## Po sklonowaniu

```bash
python3 scripts/doctor.py
```

Raport pokazuje, czy strażnicy commita i hooki Claude Code działają na tym komputerze. Przy każdym
braku podaje polecenie, które go naprawia — wykonaj je i uruchom raport jeszcze raz.

## Uruchomienie

```bash
# TODO: uzupełnij
```

## Stack

<!-- TODO: opisz stack -->

## Dokumentacja

- [Scope projektu](docs/PROJECT_SCOPE.md)
- [Instalacja i uruchomienie](docs/SETUP.md)
- [Konwencje](docs/CONVENTIONS.md)
- [Log sesji](docs/TASKS.md) — otwarta praca jest w GitHub Issues
- [Roadmapa](docs/ROADMAP.md)
- [Strażnicy i narzędzia AI](docs/GUARDS.md)
- [Wzory dokumentów](docs/examples/README.md)
"""

# Paths relative to ROOT that are template-only and removed during --init.
# The script itself is removed last (it's added in init_in_place after this list).
TEMPLATE_META: list[str] = [
    "tests",
    "README.md",
    "docs/TEMPLATE_TESTING.md",
]
# docs/adr/ is reset wholesale by reset_adr_dir (not listed here) — the template's own ADRs
# must all go, leaving a clean docs/adr/. The worked examples live in docs/examples/ and STAY
# in the project: they used to be deleted here, before anyone could use them as a pattern.

# Documents the template keeps for its own work under the names a project needs empty.
# --init replaces them with the skeletons from SCAFFOLD_DOCS (the template's session log,
# for one, must not become the first 600 lines of a new project's log).
INIT_SKELETONS: list[str] = ["TASKS.md"]
