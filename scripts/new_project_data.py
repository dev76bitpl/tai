"""Data for scripts/new-project.py: what to copy, what to remove, document skeletons.

Kept apart from the logic so new-project.py stays readable (file-size rule: data files have
no limit, logic files do). Template-only, like new-project.py itself: removed by --init and
not copied in copy-to-dir mode (TEMPLATE_ONLY_SCRIPTS).
"""

# Scripts that exist only to start a project from the template.
TEMPLATE_ONLY_SCRIPTS = ["new-project.py", "new_project_data.py", "new_project_git.py"]

# ── What to copy (copy-to-dir mode) ─────────────────────────────────────────

COPY_DIRS = [".claude"]

COPY_FILES = ["CLAUDE.md", "skills-manifest.json"]

COPY_DOCS = [
    "AI_TEMPLATE_NOTES.md",
    "CONVENTIONS.md",
    "DELIVERY_CHECKLIST.md",
    "SETUP.md",
    "SKILLS.md",
    "TESTING.md",
    "UI_GUIDELINES.md",
    "USER_PROFILE.example",
]

SCAFFOLD_DOCS: dict[str, str] = {
    "TASKS.md": """\
# Tasks

> Stan sesji: projekt zainicjalizowany — scope do zdefiniowania.

---

## Backlog

- [ ] Zdefiniuj scope projektu — napisz Claude'owi: `scope`

## In Progress

## Done
""",
    "ROADMAP.md": """\
# Roadmap

<!-- Wygeneruj za pomocą `scope` lub wypełnij ręcznie -->

## Faza 1 — [Nazwa]

**Cel:**

**Zakres:**

**Done when:**

**Zależności:** brak
""",
}

# ── What to remove + replace in --init mode ──────────────────────────────────

README_SCAFFOLD = """\
# [Nazwa projektu]

> Krótki opis — co to jest i dla kogo.

---

## Uruchomienie

```bash
# TODO: uzupełnij
```

## Stack

<!-- TODO: opisz stack -->

## Dokumentacja

- [Scope projektu](docs/PROJECT_SCOPE.md)
- [Konwencje](docs/CONVENTIONS.md)
- [Zadania](docs/TASKS.md)
- [Roadmapa](docs/ROADMAP.md)
"""

# Paths relative to ROOT that are template-only and removed during --init.
# The script itself is removed last (it's added in init_in_place after this list).
TEMPLATE_META: list[str] = [
    "tests",
    "README.md",
    "docs/SETUP.example.md",
    "docs/TASKS.example.md",
    "docs/ROADMAP.example.md",
]
# docs/adr/ is reset wholesale by reset_adr_dir (not listed here) — the template's
# own ADRs (ADR-002+) plus the example must all go, leaving a clean docs/adr/.
