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
claude   # → /new-project-scope
```

Skrypt kopiuje skille, hooki i scaffoldy, a także **automatycznie konfiguruje Claude Code hooks** (interpreter + ścieżka do template).

---

## Co dostajesz

**12 skillów** — wywołaj `/nazwa` w Claude Code:

| Skill | Do czego |
|-------|---------|
| `/new-project-scope` | Wywiad → `PROJECT_SCOPE.md` + `ADR-001` |
| `/git` | Branch strategy, commit format, PR protocol |
| `/debug` | Systematyczny protokół debugowania |
| `/deploy` | Checklist przed wdrożeniem |
| `/retro` | Retrospektywa → action items |
| `/adr` | Architecture Decision Record |
| `/api` | REST API design review |
| `/security` | OWASP Top 10:2025, ASVS 5.0 |
| `/a11y` | Audit dostępności WCAG 2.2 AA |
| `/perf` | Core Web Vitals, Lighthouse |
| `/review` | Code review 15+ języków |
| `/ui-ux-pro-max` | Design intelligence, 161 palet, 57 font pairings |

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
