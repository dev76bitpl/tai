# Testing

Checklisty testów manualnych dla krytycznych flow.

---

## Zasady

- testy automatyczne pokrywają logikę domenową i integracje
- testy manualne dla krytycznych ścieżek użytkownika
- przed każdym merge: smoke test zmienionych flow

---

## Flow: [nazwa]

### Happy path
- [ ] ...

### Edge cases
- [ ] ...

---

<!-- Dodawaj nowe flow gdy pojawia się krytyczna ścieżka -->

---

## Guard system — pre-commit framework

**Setup**: `npm install` (auto-bootstrap) lub ręcznie: `pipx install pre-commit` (Ubuntu 24.04+ — PEP 668 blokuje `pip install --user`) / `pip install pre-commit` (inne systemy), następnie `pre-commit install --hook-type pre-commit --hook-type commit-msg`. Wymagany Python 3.9+.

### Scenariusz 1 — installation works

- [ ] `npm install` w czystym klonie → `prepare` script wywołuje `setup-hooks.mjs` → auto-instaluje pre-commit → `pre-commit install`
- [ ] `npm run doctor` → wszystkie required sekcje zielone (Python, Node, pre-commit, hooks installed, config valid)
- [ ] `pre-commit run --all-files` → wszystkie hooki zielone (lub naprawialne fixy whitespace/EOF)

### Scenariusz 2 — bad commit format blocked

- [ ] Próba commita z tytułem `bad title` → gitlint blokuje
- [ ] Tytuł `feat: x` → blokuje (description < 3 chars)
- [ ] Tytuł `feat: add new feature` → OK

### Scenariusz 3 — commit on main blocked

- [ ] `git checkout main`, próba pustego commita → `no-commit-to-branch` blokuje
- [ ] Powrót na branch feat/fix

### Scenariusz 4 — source files require tests

- [ ] Dodaj nowy plik źródłowy (np. `src/foo.ts`), bez testu, próba commita → `guard-tests-with-src` blokuje
- [ ] Dodaj `src/foo.test.ts`, commit → przechodzi
- [ ] Bypass: `[skip-docs]` w body → przechodzi

### Scenariusz 5 — `[user-tested]` flag on feat/*

- [ ] Na branchu `feat/*` próba commita bez flagi → `guard-user-tested` blokuje
- [ ] Z `[user-tested]` w body → przechodzi
- [ ] Bypass: `[skip-test-check]` z uzasadnieniem → przechodzi
- [ ] Na `docs/*` / `chore/*` flaga nie jest wymagana

### Scenariusz 6 — Polish text in subject blocked

- [ ] Tytuł zawierający `ą`/`ó`/`ę` itp. → `guard-commit-lang` blokuje
- [ ] Tytuł z polskim słowem (`dodaj`, `usuń`) bez polish chars → blokuje
- [ ] Tytuł po angielsku → OK

### Scenariusz 7 — gitleaks blocks committed secret

- [ ] Dodaj plik z prawidłowo sformatowanym fake-secretem (np. `AKIA[A-Z0-9]{16}`), stage, próba commita → `gitleaks` blokuje
- [ ] Uwaga: gitleaks ma allowlist dla example keys (zawierających `EXAMPLE`) — to intencjonalne, test wymaga klucza bez tego substringa

### Scenariusz 8 — ADR heuristic

- [ ] Zmiana w `prisma/schema.prisma` lub innym ADR-trigger pattern, stage, próba commita → `guard-adr` blokuje
- [ ] Bypass: `[no-adr]` w body → przechodzi
- [ ] Lub: dodaj `docs/adr/ADR-XXX.md` do staged → przechodzi

### Scenariusz 9 — docs/TASKS.md required

- [ ] Commit bez `docs/TASKS.md` w staged → `guard-tasks-staged` blokuje
- [ ] Stage `docs/TASKS.md` → przechodzi
- [ ] Bypass: `[skip-docs]` w body → przechodzi

### Scenariusz 10 — CI mirror green on PR

- [ ] Push branchu, otwórz PR → GitHub Actions job `guards` runs → wszystkie hooki zielone
- [ ] Branch protection rule na `main` wymaga `guards` zielony przed merge

### Scenariusz 10a — skan sekretów w CI obejmuje całe repo

- [ ] Otwórz PR → w zadaniu `Checks` jest krok `Scan working tree for secrets (gitleaks)` i jest zielony
- [ ] Na gałęzi próbnej dodaj plik z fałszywym kluczem (jak w scenariuszu 7), wypchnij z `--no-verify` → krok czerwony, w logu nazwa pliku i reguły, wartość zamaskowana; gałąź próbną usuń
- [ ] Lokalnie: `python3 -m pytest -q tests/test_ci_secret_scan.py` → 5 zielonych (wersja obrazu = `rev` hooka `gitleaks`)

### Scenariusz 10b — doctor widzi niepodpięte hooki Claude Code

- [ ] Bez `.claude/settings.local.json`: `npm run doctor` → w sekcji „Claude Code hooks” ostrzeżenie o braku pliku, raport kończy się „All required checks passed”
- [ ] `cp .claude/settings.local.json.example .claude/settings.local.json`, `npm run doctor` → błąd o znaczniku `INTERPRETER`, raport kończy się błędem (kod wyjścia `1`)
- [ ] Podmień `INTERPRETER` na `python3` / `py`, `npm run doctor` → „Claude Code hooks wired (N guard hook(s))”
- [ ] Usuń z pliku wpis jednego strażnika, `npm run doctor` → ostrzeżenie z jego nazwą; przywróć wpis
- [ ] Bez `pytest` na maszynie: ostrzeżenie z poleceniem instalacji, raport nadal kończy się sukcesem

### Scenariusz 10c — prowadzony start projektu

Na świeżej kopii szablonu **poza** repo szablonu (w samym szablonie tylko `--dry-run`):

- [ ] `python3 scripts/new-project.py --init` w terminalu → baner „Przygotowanie projektu”, sprzątanie z nagłówkami, potem baner „Start projektu” i osiem kroków z paskiem postępu: Git, repo, ustawienia repo, etykiety, kontrola środowiska, brief, skille, szablon graficzny
- [ ] `git branch --show-current` → `main`, także na maszynie bez `init.defaultBranch`
- [ ] Krok „Repo na GitHubie”: Enter → pominięty; adres → `git remote -v` pokazuje `origin`; `wlasciciel/nazwa` → repo powstaje na GitHubie, nic nie jest wypychane
- [ ] Krok „Etykiety zgłoszeń”: bez repo → pominięty z wyjaśnieniem; z repo podpiętym przez alias SSH (adres bez `github.com`) → proponuje założenie `owner` i `idea`
- [ ] Krok „Kontrola środowiska” → raport `doctor`; przy czerwonym raporcie pytanie „Poprosić Claude o pomoc z tym krokiem?”, a po powrocie „Ponowić ten krok teraz?”
- [ ] Krok „Brief projektu”: „tak” → Claude Code startuje i prowadzi wywiad po jednym pytaniu; po `/exit` wracasz do kroków i widzisz trzy `✓` (brief, stos, ADR-001)
- [ ] Wyjście z Claude Code w połowie wywiadu → `✗` przy brakujących punktach i pytanie „Wrócić do Claude Code i dokończyć?”
- [ ] Na końcu „Podsumowanie” ze znakiem przy każdym kroku i lista „Co dalej”; przy nieudanym kroku „Start niedokończony” z poleceniem wznowienia
- [ ] `python3 scripts/project-setup.py` uruchomiony ponownie → kroki zrobione są pomijane
- [ ] `python3 scripts/new-project.py --init < /dev/null` (bez terminala) → żadnego pytania, sama lista kroków; wynik przekierowany do pliku nie zawiera kodów kolorów

### Scenariusz 10g — ustawienia repo na GitHubie

- [ ] Świeżo założone repo, projekt z `.github/workflows/release-please.yml`: krok „Ustawienia repo” wymienia dwa braki z powodem i pyta raz; po „tak” w ustawieniach repo włączone jest automatyczne kasowanie gałęzi, a Actions mają zapis i zatwierdzanie PR
- [ ] Projekt bez pliku automatu wydań: krok proponuje tylko kasowanie gałęzi
- [ ] Ponowne uruchomienie `python3 scripts/project-setup.py` → „ustawienia repo są na miejscu”, bez pytania
- [ ] Repo w organizacji z ograniczeniami (albo bez uprawnień właściciela): krok pokazuje polecenia `gh api …` do ręcznego wykonania i start idzie dalej
- [ ] `npm run doctor` w projekcie z domyślnymi ustawieniami → ostrzeżenie „GitHub repo settings missing: …”; po ustawieniu → „GitHub repo settings in place”

### Scenariusz 10h — strażnicy lintu i testów w świeżym projekcie

- [ ] Po `--init`: `grep '"lint"\|"test"' .claude/hooks/config.json` → nic (żadnych odziedziczonych poleceń)
- [ ] Na gałęzi roboczej, z plikiem w `src/` w indeksie: `pre-commit run guard-lint` (bez `--verbose`) → „Passed” i pod spodem `[WARN] Lint guard checks NOTHING: npm run lint --silent — package.json has no "lint" script`
- [ ] `npm run doctor` → w „Guard system” `⚠ Lint guard checks nothing: …` i `⚠ Test guard checks nothing: …`
- [ ] Dodaj do `package.json` skrypt `lint`, który kończy się błędem → commit zablokowany „Lint failed”; skrypt przechodzący → `✅ Lint [node] OK`, a doctor pokazuje `✓ Lint guard runs: …`
- [ ] Wpisz w `.claude/hooks/config.json` `"lint": "nie-ma-takiego-polecenia"` → commit zablokowany „Lint command from .claude/hooks/config.json cannot run”, doctor: `⚠ Lint guard BLOCKS every commit: …`

### Scenariusz 10i — końce linii

- [ ] Po `--init`: `git config core.autocrlf` → `input`; w katalogu głównym jest `.gitattributes` z `* text=auto eol=lf`
- [ ] `npm run doctor` → w „Repository state” `✓ Line endings: .gitattributes (eol=lf)`; po usunięciu pliku → ostrzeżenie „No .gitattributes rule for line endings”
- [ ] Klon na Windows bez wcześniejszego `npm install`: `git status` czysty, commit pliku tekstowego nie jest odbijany przez `mixed-line-ending`
- [ ] `git check-attr eol -- README.md` → `eol: lf`

### Scenariusz 10e — wybór skilli

- [ ] Krok „Skille” po wywiadzie: `●` przy grupach proponowanych dla stosu z wywiadu; Enter je przyjmuje, `w` zostawia wszystko, numery wybierają ręcznie
- [ ] Przed usunięciem skrypt wymienia skille z nazwy i pyta „Usunąć?”; „n” niczego nie zmienia
- [ ] Po wyborze w `.claude/skills/` nie ma odrzuconych grup, a `skills-manifest.json` ma `skill_groups` i `excluded_skills`
- [ ] Nowa sesja Claude Code w projekcie, jedna wiadomość → odrzucone skille nie wracają (synchronizacja z szablonu je pomija)
- [ ] `python3 scripts/select-skills.py --list` pokazuje aktualny wybór; ponowne uruchomienie pozwala go zmienić
- [ ] Skille ogólne (`scope`, `adr`, `api`, `debug`, `deploy`, `git`, `retro`) zostają przy każdym wyborze

### Scenariusz 10f — szablon graficzny

- [ ] Krok „Szablon graficzny”: najpierw pytanie o `impeccable` z `[t/N]` — Enter pomija, `t` uruchamia instalator; po nim `.claude/skills/impeccable` istnieje, a `.claude/settings.local.json` nie ma wpisów `impeccable`
- [ ] Z zainstalowanym `impeccable` Claude Code wczytuje go na początku, tworzy `PRODUCT.md` z briefu i przed pokazaniem makiet robi ich krytykę; bez niego mówi, którym skillem pracuje i dlaczego
- [ ] Makiety trafiają do `mockups/propozycje/`: `index.html` i dwa kierunki, każdy jasny i ciemny, z treścią z briefu
- [ ] Po wyborze kierunku `docs/UI_GUIDELINES.md` ma sekcję „Kierunek wizualny projektu”; po `/exit` skrypt pokazuje dwa `✓`
- [ ] Projekt bez interfejsu: odpowiedź „n” → krok pominięty, start kończy się normalnie
- [ ] Grupa „Projektowanie wyglądu” odrzucona w wyborze skilli → krok o tym mówi i podaje `python3 scripts/select-skills.py`

### Scenariusz 10d — strażnicy dopasowani do stosu

- [ ] Projekt bez platformy sklepowej, nowy plik w `modules/` → `guard-adr` nie blokuje; po `python3 scripts/set-stack.py prestashop` → blokuje „nowy moduł PrestaShop”
- [ ] `src/price.py` + `tests/test_price.py` w jednym commicie → `guard-tests-with-src` przepuszcza; samo `src/price.py` → blokuje
- [ ] Po `python3 scripts/set-stack.py laravel`: `app/Service/Order.php` bez testu → blokuje; z `tests/Service/OrderTest.php` → przepuszcza

### Scenariusz 11 — release-please creates Release PR

- [ ] Po merge feat/fix commitów do main, workflow `Release Please` runs
- [ ] Auto-utworzony Release PR z `CHANGELOG.md` + version bump
- [ ] Merge Release PR → tag + GitHub Release

### Scenariusz 11a — personal data blocked (`guard-pii`)

- [ ] Plik z linią `uczen 44051401359` (przykładowy PESEL z poprawną sumą kontrolną), stage, <!-- pii-ok -->
      `python3 scripts/dev-guards/guard_pii.py` → blokada `❌ [BLOCK] Personal data in staged changes`
      z nazwą pliku, numerem linii, rodzajem `PESEL` i wartością zamaskowaną (`44*******59`); pełny numer nie pojawia się w komunikacie <!-- pii-ok -->
- [ ] Usuń plik ze staged → to samo polecenie nie wypisuje nic (cisza = poprawny wynik)
- [ ] Ta sama linia z dopiskiem `pii-ok` → przechodzi
- [ ] Plik z polskimi znakami albo spacją w nazwie → nadal blokuje
- [ ] Nazwisko wpisane do `~/.config/76bit/pii-names.txt` i użyte w pliku → blokuje; bez listy — nie

### Scenariusz 11b — hook blokuje, gdy nie odczyta własnego wejścia

Dotyczy czterech hooków blokujących: `guard-process-kill`, `guard-template-sync`, `guard-ai-template`,
`guard-testing-checklist`. Polecenia niczego nie ubijają ani nie commitują — hook dostaje tylko tekst.
Po każdym poleceniu `echo $?` pokazuje kod wyjścia (blokuje wyłącznie kod **2**).

- [ ] `echo 'not json' | python3 .claude/hooks/guard-process-kill.py; echo $?` → komunikat
      `❌ [BLOCK] guard-process-kill: cannot read its own input (input is not valid JSON)` i kod `2`
- [ ] To samo dla pozostałych trzech hooków → ten sam komunikat z nazwą hooka i kod `2`
- [ ] `printf '' | python3 .claude/hooks/guard-process-kill.py; echo $?` (puste wejście) → blokada, kod `2`
- [ ] `echo '{"tool_name":"Edit","tool_input":{"file_path":"x"}}' | python3 .claude/hooks/guard-process-kill.py; echo $?`
      → nic nie wypisuje, kod `0` (inne narzędzie niż powłoka — cisza jest poprawnym wynikiem)
- [ ] `echo '{"tool_input":{"command":"killall node"}}' | python3 .claude/hooks/guard-process-kill.py; echo $?`
      → blokada `kill by process NAME or PATTERN`, kod `2` (wejście bez `tool_name` też jest czytane)
- [ ] `echo '{"tool_input":{"command":"kill 12345"}}' | python3 .claude/hooks/guard-process-kill.py; echo $?`
      → nic nie wypisuje, kod `0`
- [ ] `python3 -m pytest -q` z katalogu głównego → wszystkie testy zielone, w tym te z `.claude/hooks/tests/`

### Scenariusz 11d — strażnik commita blokuje, gdy nie może sprawdzić

- [ ] `python3 scripts/dev-guards/guard_user_tested.py; echo $?` (bez pliku wiadomości) →
      `❌ [BLOCK] guard_user_tested: no commit message file given, so the commit was NOT checked.` i kod `1`
- [ ] `PR_TITLE= PR_BODY= python3 scripts/dev-guards/check_pr_language.py; echo $?` → `[BLOCK] PR_TITLE is empty` i kod `1`
- [ ] `PR_TITLE="fix: keep the filter" PR_BODY= python3 scripts/dev-guards/check_pr_language.py; echo $?` → `OK: ...` i kod `0`
- [ ] Zwykły commit w tym repo przechodzi jak dotąd (strażnicy dostają plik wiadomości od pre-commit)

### Scenariusz 11c — `guard-template-sync` blokuje rozjazd z szablonem zamiast się wywalać

Wymaga projektu postawionego z szablonu, z lokalnym klonem szablonu (`ai_template_path` albo klon obok).

- [ ] W projekcie dopisz do dowolnego `*.md` istniejącego też w szablonie nagłówek `## Tylko tutaj`, `git add` tego pliku
- [ ] `echo '{"tool_input":{"command":"git commit -m \"docs: x\""}}' | python3 .claude/hooks/guard-template-sync.py; echo $?`
      → `❌ [BLOCK] Desync z AI template repo` z nazwą pliku, nagłówkiem i ścieżką klona szablonu; kod `2`, bez `Traceback`
- [ ] To samo z `[skip-sync]` w wiadomości → nic nie wypisuje, kod `0`
- [ ] Cofnij zmianę (`git restore --staged <plik>` i usuń nagłówek)

---

## Rozstrzyganie ścieżki do template (`resolve_template_source`)

Kontekst: `ai_template_path` był czytany tylko z commitowanego `config.json`, więc
każdy klon wymagał wpisania ścieżki z konkretnej maszyny — i ta ścieżka wjeżdżała
do repo. Resolver dokłada warstwy i autodetekcję po markerze.

### Scenariusz 12 — kolejność warstw

- [ ] `export AI_TEMPLATE_PATH=/tmp/z-env` + `ai_template_path` w `config.json` → w nowej sesji auto-sync używa `/tmp/z-env` (ostrzeżenie o nieistniejącej ścieżce wskazuje źródło `$AI_TEMPLATE_PATH`)
- [ ] `unset AI_TEMPLATE_PATH`, `.claude/hooks/config.local.json` z inną ścieżką → wygrywa `config.local.json`
- [ ] Usuń `config.local.json` → wygrywa `config.json`
- [ ] Usuń `ai_template_path` z `config.json`, klon template leży obok projektu → autodetekcja go znajduje, auto-sync skilli działa
- [ ] Przenieś klon template gdzie indziej → `python3 scripts/update-skills.py` ciągnie z `https://github.com/dev76bitpl/tai.git` (bez żadnej konfiguracji)

### Scenariusz 13 — autodetekcja nie zależy od nazwy

- [ ] Zmień nazwę katalogu klona template (np. `tai` → `szablon`) → autodetekcja nadal go znajduje (marker `is_template` w jego `config.json`)
- [ ] Katalog obok bez `is_template: true` (zwykły projekt z template'a) → **nie** jest brany za template
- [ ] Projekt, który sam jest template'm (`is_template: true`) → nie wskazuje sam na siebie

### Scenariusz 13a — config.local.json widzą też strażnicy commita i doctor

W projekcie postawionym z szablonu (w samym szablonie doctor pokazuje tylko „This repo is the AI template”):

- [ ] W `.claude/hooks/config.local.json` wpisz `{"lint": "false"}`, zrób commit → `Stack-aware lint` blokuje (komenda z pliku lokalnego wygrała); usuń wpis → commit przechodzi
- [ ] W `.claude/hooks/config.local.json` wpisz `ai_template_path` na istniejący katalog, `npm run doctor` → `AI template repo: <ścieżka>  (from config.local.json)`
- [ ] `AI_TEMPLATE_PATH=<inny katalog> npm run doctor` → ta ścieżka i `(from $AI_TEMPLATE_PATH)`
- [ ] Bez pliku lokalnego i zmiennej, z adresem URL w `config.json` → `(remote, from config.json)`, bez ostrzeżenia

### Scenariusz 14 — config.local.json nie trafia do repo

- [ ] Utwórz `.claude/hooks/config.local.json`, `git status` → plik nie pojawia się jako untracked
- [ ] `git add .claude/hooks/config.local.json` → git odmawia (ignored)
