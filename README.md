# AI Template

Fundament nowego projektu z AI. Skille, guardy workflow i scaffoldy dokumentacji gotowe od pierwszego commita.

---

## Nowy projekt — 3 kroki

```bash
# 1. Sklonuj jako nowy projekt
git clone https://github.com/dev76bitpl/ai.git moj-projekt
cd moj-projekt

# 2. Wyczyść template meta (testy, README, ten skrypt)
python3 scripts/new-project.py --init

# 3. Nowy git + scope
rm -rf .git && git init && git remote add origin <url>
python3 scripts/update-skills.py --apply
claude   # napisz: scope
```

`--init` usuwa pliki template-only (`tests/`, `README.md` → scaffold, sam siebie) i konfiguruje Claude Code hooks. Skille zostają gotowe do pracy.

---

## Co dostajesz

**24 skille** — Claude ładuje je automatycznie gdy wykryje pasujący kontekst:

| Skill | Jak wywołać |
|-------|-------------|
| `scope` | Wywiad 6 pytań → `docs/PROJECT_SCOPE.md` + `ADR-001` |
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
# Vendored skille — sprawdź i zaktualizuj z GitHub
python3 scripts/update-skills.py          # podgląd aktualizacji
python3 scripts/update-skills.py --apply  # zastosuj

# Istniejący projekt — pobierz zmiany z t-ai
python3 scripts/update-skills.py --sync          # podgląd
python3 scripts/update-skills.py --sync --apply  # zastosuj
python3 scripts/update-skills.py --full-sync     # sync + vendored w jednym kroku

# Walidacja
python3 scripts/validate-skills.py        # waliduj frontmatter SKILL.md
```

**Auto-sync** — na starcie każdej sesji Claude sprawdza czy skille są aktualne z t-ai i synchronizuje automatycznie.

Pełny katalog: [docs/SKILLS.md](docs/SKILLS.md)

---

## Istniejący projekt

Jeśli projekt był założony przed wprowadzeniem t-ai:

```bash
# 1. Skopiuj skrypt
cp /sciezka/do/ai/scripts/update-skills.py scripts/update-skills.py

# 2. Ustaw ai_template_path w .claude/hooks/config.json
#    Lokalnie:  "/home/user/Projekty/ai"
#    Zdalnie:   "git@github.com:org/ai.git"

# 3. Pobierz wszystko
python3 scripts/update-skills.py --full-sync
```

---

## Filozofia

```
CLAUDE.md          = jak pracujemy
docs/PROJECT_SCOPE.md = co budujemy
docs/adr/          = dlaczego tak, a nie inaczej
```

AI czyta te pliki na początku każdej sesji. Im lepiej wypełnione, tym mniej wyjaśniania — więcej robienia.
