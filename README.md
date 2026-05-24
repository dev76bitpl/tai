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
claude   # napisz: scope
```

Skrypt kopiuje skille, hooki i scaffoldy, a także **automatycznie konfiguruje Claude Code hooks** (interpreter + ścieżka do template).

---

## Co dostajesz

**24 skille** — Claude ładuje je automatycznie gdy wykryje pasujący kontekst:

| Skill | Jak wywołać |
|-------|-------------|
| `scope` | Wywiad 6 pytań → `PROJECT_SCOPE.md` + `ADR-001` |
| `debug` | Protokół debugowania krok po kroku |
| `deploy` | Checklist przed wdrożeniem na produkcję |
| `retro` | Retrospektywa → action items do `TASKS.md` |
| `adr` | Generator ADR → `docs/adr/ADR-NNN.md` |
| `api design` | REST API design review |
| `git` | Branch strategy, commit format, PR |
| `security review` | OWASP Top 10:2025, ASVS 5.0 |
| `a11y` | Audit dostępności WCAG 2.2 AA |
| `perf` | Core Web Vitals, Lighthouse |
| `review` | Code review PR |
| `ui design` | Design intelligence — style, kolory, typografia |
| `wp plugin` | Architektura pluginu WP, hooks, CPT, WordPress.org |
| `wp theme` | Motyw WP, template hierarchy, FSE, theme.json |
| `wp security` | Sanitization, escaping, nonces, vulnerability patterns |
| `woocommerce` | Rozszerzenia WC, szablony, REST API, wydajność |
| `gutenberg` | Gutenberg blocks, block.json, Interactivity API |
| `prestashop` | Moduły PS, hooki, override'y, Webservice API, PS 1.7/8.x |
| `shoper` | Twig, ObjectApi, REST API, webhooks, App Store OAuth2 |
| `laravel` | CQRS Actions/Queries, Pest, Eloquent UUID, kolejki, spatie/laravel-data |
| `php modernization` | PHP 8.1–8.5, readonly, enums, DTOs, PHPStan, Rector, PSR/PER |
| `symfony` | DDD/CQRS, Messenger, API Platform, Doctrine, DI, Voters, best practices |
| `typescript` | TypeScript 5.9+, generics, Zod, React integration, NestJS, Vite |
| `nextjs` | Next.js App Router, RSC, Server Actions, streaming, caching |

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
