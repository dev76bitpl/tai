# AI Template

Fundament nowego projektu z AI. Skille, guardy workflow i scaffoldy dokumentacji gotowe od pierwszego commita.

---

## Nowy projekt — 3 kroki

```bash
# 1. Sklonuj jako nowy projekt
git clone https://github.com/dev76bitpl/tai.git moj-projekt
cd moj-projekt

# 2. Wyczyść template meta (testy, README, ten skrypt) i przejdź kroki startu
python3 scripts/new-project.py --init

# 3. Przerwane albo któryś krok się nie udał? Dokończ — zrobione kroki są pomijane
python3 scripts/project-setup.py
```

`--init` usuwa pliki template-only (`tests/`, `README.md` → scaffold, sam siebie), zakłada świeżą historię Gita na gałęzi `main`, instaluje strażników commita i konfiguruje Claude Code hooks. Potem prowadzi przez kroki startu, każdy z pytaniem i wynikiem ✓ / ✗:

1. **Repo** — adres istniejącego albo `wlasciciel/nazwa` nowego do założenia na GitHubie (Enter = pomiń)
2. **Ustawienia repo** — kasowanie gałęzi po scaleniu i, gdy projekt ma automat wydań, uprawnienia automatów GitHuba; jedno pytanie
3. **Etykiety zgłoszeń** — `owner` i `idea`
4. **Kontrola środowiska** — raport `doctor`
5. **Brief** — wywiad `scope` w Claude Code: zakres, dla kogo i stos; ze stosu `scripts/set-stack.py` ustawia strażników (katalogi kodu, wzorce ADR platformy — tabela w `docs/GUARDS.md`, sekcja „Konfiguracja strażników”). Projekt z gotowym briefem wywiad pomija
6. **Skille** — wybór grup, które zostają w projekcie (stos podpowiada, które); niewybrane znikają i nie wracają przy synchronizacji. Zmiana później: `python3 scripts/select-skills.py`
7. **Szablon graficzny** — Claude Code przygotowuje dwa kierunki wyglądu (każdy jasny i ciemny) jako makiety w `mockups/propozycje/`; po wyborze zasady trafiają do `docs/UI_GUIDELINES.md`. Projekt bez interfejsu pomija krok

Gdy krok się nie uda, skrypt proponuje uruchomienie Claude Code z opisem błędu, a po powrocie ponowienie kroku. Claude Code otwiera się jako etap: po wyjściu z niego (`/exit`) wracasz do kroków, skrypt sprawdza, czy brief, stos i ADR-001 powstały, i kończy podsumowaniem. Bez terminala (AI, CI) o nic nie pyta — drukuje listę kroków. Skille zostają gotowe do pracy w wersji z szablonu — start nie pobiera nowszych z sieci (to utrzymanie, sekcja „Zarządzanie skillami”). Wynik startu zapisujesz pierwszym commitem na gałęzi roboczej (`git switch -c chore/project-start`), bo na `main` commit jest zablokowany. Testy strażników zostają — mieszkają obok nich (`.claude/hooks/tests/`, `scripts/dev-guards/tests/`), a `tests/` to testy narzędzi samego szablonu.

---

## Co dostajesz

**26 skilli** — Claude ładuje je automatycznie gdy wykryje pasujący kontekst (projekt wybiera przy starcie, które grupy zostają):

| Skill | Jak wywołać |
|-------|-------------|
| `scope` | Interaktywny wywiad (pytania po jednym, z dopytaniem) → `docs/PROJECT_SCOPE.md` + `ADR-001` + stos dla strażników |
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

**Scaffoldy docs** — `TASKS.md`, `ROADMAP.md`, `SETUP.md`, `TESTING.md`, `PROJECT_SCOPE.md` jako puste szkielety, a obok wypełnione wzory w `docs/examples/`. `docs/GUARDS.md` opisuje strażników i narzędzia AI, które projekt dostaje gotowe.

---

## Wymagania

- Python 3.9+
- [Claude Code](https://claude.ai/code) CLI
- Git

---

## Zarządzanie skillami

Aktualizacja skilli to utrzymanie, nie część startu: zmienia dziesiątki plików, więc rób ją na
gałęzi roboczej (np. `git switch -c chore/update-skills`), nigdy na `main`. Gdy skan bezpieczeństwa
zablokuje aktualizację skilla („znaleziono podejrzane wzorce”), skill zostaje w obecnej wersji i dalej
działa — przejrzyj zgłoszone linie w źródle i zdecyduj; zablokowanej aktualizacji nie wymuszaj.

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
cp /sciezka/do/tai/scripts/update-skills.py scripts/update-skills.py

# 2. Pobierz wszystko — ścieżka do template rozstrzyga się sama
python3 scripts/update-skills.py --full-sync
```

### Poprawki z szablonu: strażnicy, hooki, skrypty

```bash
python3 scripts/update-from-template.py           # podgląd: co jest do aktualizacji, co nowe, co zmienione lokalnie
python3 scripts/update-from-template.py --apply   # kopiuje pliki „do aktualizacji” i „nowe”
```

Źródłem jest wydany `main` szablonu, a listę plików szablon trzyma w `template-files.json`. Plik zmieniony
w projekcie nie jest nadpisywany, a `CLAUDE.md` jest tylko porównywany po sekcjach. Podgląd ostrzega też, gdy
polecenie lintu albo testów wpisane w `.claude/hooks/config.json` nie da się uruchomić — po aktualizacji
strażnicy zablokowaliby nim każdy commit (typowo odziedziczone `composer lint` / `composer test`).

**Projekt bez `scripts/update-from-template.py`** (założony przed ADR-006) dostaje go w trzech krokach, na gałęzi
roboczej. Samo `update-skills.py` bez `--sync` sprawdza tylko skille z GitHuba i skryptów szablonu nie rusza:

```bash
python3 scripts/update-skills.py --sync           # 1. podgląd — stara wersja nadpisuje skille zmienione w projekcie
python3 scripts/update-skills.py --sync --apply   # 2. podmienia sam update-skills.py
python3 scripts/update-skills.py --sync --apply   # 3. nowa wersja dokłada update-from-template.py
python3 scripts/update-from-template.py           # potem podgląd i --apply jak wyżej
```

Skill zmieniony w projekcie (treść, której nie było w żadnej wersji szablonu) synchronizacja zostawia w spokoju
i wypisuje jako „zmieniony lokalnie — porównaj ręcznie”. Dotyczy to dopiero nowej wersji `update-skills.py`
— stara, uruchomiona w kroku 2, kasuje i kopiuje od nowa każdy zmieniony skill, dlatego podgląd w kroku 1
jest obowiązkowy. Gdy szablon ma w swoim `.claude/hooks/config.json`
`"template_update_check": true`, hook startu sesji w każdym projekcie z lokalnym klonem szablonu dociąga
`main` najwyżej raz na dobę i mówi jednym zdaniem, co czeka. Szczegóły: [ADR-006](docs/adr/ADR-006-updating-projects-from-template.md).

### Skąd brana jest ścieżka do template

Pierwsze trafienie wygrywa:

| # | Źródło | Kiedy używać |
|---|--------|--------------|
| 1 | `$AI_TEMPLATE_PATH` | **zalecane na stałe** — jeden `export` obsługuje wszystkie projekty na maszynie |
| 2 | `.claude/hooks/config.local.json` | gdy jeden projekt ma wskazywać inny klon; plik jest gitignorowany |
| 3 | `ai_template_path` w `config.json` | commitowane, wspólne dla zespołu — najlepiej URL, nie ścieżka lokalna |
| 4 | autodetekcja klona obok | katalog obok projektu z `is_template: true` w swoim configu |
| 5 | `https://github.com/dev76bitpl/tai.git` | domyślnie, gdy nic powyżej nie zadziałało |

```bash
# raz na maszynie, w ~/.bashrc
export AI_TEMPLATE_PATH="$HOME/Projekty/76bit/tai"
```

Ścieżka lokalna daje podpowiedź o zmianach w szablonie na starcie sesji i diff `*.md`; URL wystarcza do
auto-syncu skilli. **Skille z lokalnego klona idą zawsze ze stanu `origin/main`**, nie z katalogu roboczego: gałąź w toku i niezacommitowane zmiany w klonie nie trafiają do projektów. Projekty widzą nową wersję szablonu po `git pull` (albo `git fetch`) w klonie. Klon bez `origin/main` → synchronizacja odmawia z komunikatem. Ścieżka z konkretnej maszyny **nie powinna** trafiać do
commitowanego `config.json` — to warstwy 1 i 2.

Autodetekcja rozpoznaje klon po zawartości (`is_template` + `skills-manifest.json`),
nigdy po nazwie katalogu — repo bywa przemianowane (`ai` → `tai`) i dopasowanie
po nazwie rozwala się przy każdej takiej zmianie.

---

## Filozofia

```
CLAUDE.md          = jak pracujemy
docs/PROJECT_SCOPE.md = co budujemy
docs/adr/          = dlaczego tak, a nie inaczej
```

AI czyta te pliki na początku każdej sesji. Im lepiej wypełnione, tym mniej wyjaśniania — więcej robienia.
