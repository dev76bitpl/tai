# AI Template

Fundament nowego projektu z AI. Skille, guardy workflow i scaffoldy dokumentacji gotowe od pierwszego commita.

---

## Nowy projekt — 3 kroki

```bash
# 1. Sklonuj template (raz na maszynie)
git clone https://github.com/dev76bitpl/ai.git ~/ai-template

# 2. Utwórz projekt
python3 ~/ai-template/scripts/new-project.py ~/Projekty/moj-projekt

# 3. Wejdź i zdefiniuj co budujesz
cd ~/Projekty/moj-projekt
git init && git remote add origin <url>
claude   # napisz: "zacznij nowy projekt" albo "zdefiniuj scope"
```

Skrypt kopiuje skille, hooki i scaffoldy, a także **automatycznie konfiguruje Claude Code hooks** (interpreter + ścieżka do template).

---

## Co dostajesz

**12 skillów** — Claude ładuje je automatycznie gdy wykryje pasujący kontekst:

| Skill | Jak wywołać |
|-------|-------------|
| `new-project-scope` | "zacznij nowy projekt" / "zdefiniuj scope" |
| `git` | "zacznij feature" / "zrób commit" / "otwórz PR" |
| `debug` | "nie działa" / "szukam buga" / "debug" |
| `deploy` | "deploy" / "wdrożenie" / "idę na produkcję" |
| `retro` | "retrospektywa" / "co poszło dobrze" |
| `adr` | "napisz ADR" / "decyzja architektoniczna" |
| `api` | "zaprojektuj API" / "nowy endpoint" |
| `security` | "security review" / "sprawdź bezpieczeństwo" |
| `a11y` | "dostępność" / "WCAG" / "screen reader" |
| `perf` | "wolna strona" / "Lighthouse" / "Core Web Vitals" |
| `review` | "zrób review" / "sprawdź kod" / "review PR" |
| `ui-ux-pro-max` | "zaprojektuj UI" / "dobierz kolory" / "design system" |

**Guard system** — pre-commit blokuje złe commity: format, brak testów, brak ADR, brak `[user-tested]`.

**Scaffoldy docs** — `TASKS.md`, `ROADMAP.md`, `CONVENTIONS.md`, `SETUP.md`, `UI_GUIDELINES.md` i inne w `docs/`.

---

## Wymagania

- Python 3.9+
- [Claude Code](https://claude.ai/code) CLI
- Git

---

## Zarządzanie skillami

```bash
python3 scripts/update-skills.py          # sprawdź aktualizacje
python3 scripts/update-skills.py --apply  # zastosuj bezpieczne aktualizacje
python3 scripts/validate-skills.py        # waliduj frontmatter SKILL.md
```

Pełny katalog: [docs/SKILLS.md](docs/SKILLS.md)

---

## Filozofia

```
CLAUDE.md          = jak pracujemy
PROJECT_SCOPE.md   = co budujemy
docs/adr/          = dlaczego tak, a nie inaczej
```

AI czyta te pliki na początku każdej sesji. Im lepiej wypełnione, tym mniej wyjaśniania — więcej robienia.
