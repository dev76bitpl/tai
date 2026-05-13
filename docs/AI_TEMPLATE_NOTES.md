# AI Template Notes

Dobre praktyki zebrane w trakcie pracy z AI. Aktualizowane na bieżąco — każda generyczna zasada niezależna od domeny trafia tutaj.

---

## Zasady pracy z AI (CLAUDE.md)

- **Guard system na bazie `pre-commit` framework** — industry standard substrate zamiast własnych wrapperów. `.pre-commit-config.yaml` definiuje: built-ins (whitespace, EOF, `no-commit-to-branch`), `gitlint` (Conventional Commits), `gitleaks` (sekrety), custom local hooks dla CLAUDE.md enforcement (user-tested, ADR, TASKS.md, tests-with-src, commit-lang). CI workflow mirror'uje server-side (`pre-commit run --all-files`), nie do obejścia przez `--no-verify`. Bootstrap zautomatyzowany przez `npm prepare` → `scripts/setup-hooks.mjs` + `npm run doctor` jako health check. Auto-changelog przez `release-please` (Google) — Release PR z CHANGELOG.md przy merge do main. **Bypass flagi** (z dokumentowanym powodem w body commita): `[skip-docs]`, `[no-adr]`, `[skip-test-check]`, `[skip-sync]`, `[user-tested]`, `[template-done]`. **Trójwarstwowa ochrona**: `npm prepare` (auto-install), `npm run doctor` (manual check), CI (server-side enforcement). Stack-agnostyczny: Python guard scripts działają niezależnie od node/php/python/go.
- **Zakaz `alert()/confirm()/prompt()`** — błędy inline lub dwukrokowy przycisk; `confirm()` = stan "potwierdź?" → akcja. Natywne dialogi JS łamią UX i są niekontrolowalne.
- **Zakaz hardcoded wartości** — config od dnia 1, nawet na dev; seed czyta z env, nie hardkoduje slugów/nazw/haseł.
- **Branch + PR workflow** — każda zmiana na osobnym branchu (`feat/`, `fix/`, `docs/`), merge przez PR; AI proponuje nazwę brancha na starcie sesji.
- **Off-plan digressions** — każde wyjście poza główny temat sesji notować w "Stan sesji" w TASKS.md z dopiskiem dlaczego; pozwala odróżnić cel sesji od dygresji.
- **Testy razem z kodem** — nie po fakcie; moduł bez testów nie jest domknięty.
- **Commit po każdym domkniętym kroku** — AI proponuje commit bez czekania na pytanie usera.

---

## Architektura / struktura projektu

- **Konfigurowalność przez JSON settings** — opcje formularzy (listy wyboru, parametry operacyjne) żyją w tabeli tenant/config jako JSON, nie w hardcoded tablicach; zmienialne bez migracji schematu.
- **Seed idempotentny z merge defaultów** — `upsert` + post-merge brakujących kluczy; nowe defaults trafiają do istniejących rekordów bez nadpisywania customizacji użytkownika.
- **`.env` vs `.env.local`** — narzędzia infrastrukturalne (Docker Compose) czytają `.env`, framework aplikacyjny (Next.js, Prisma) czyta `.env.local`; osobne pliki, osobne odpowiedzialności.

---

## Nawigacja / UX

- **Breadcrumbs od początku** — każdy widok szczegółowy potrzebuje breadcrumb i/lub "Wróć"; trudno dorobić globalnie po fakcie.
- **Spójność kolorów statusów** — jedno mapowanie (`getStatusMeta`) podpięte wszędzie: kalendarz, modal, dashboard, tabele; nie duplikować per-widok.
- **Dwukrokowy przycisk zamiast confirm()** — pierwsze kliknięcie = stan "potwierdź?", drugie = akcja; bezpieczny, sterowalny, zgodny z design systemem.
- **Audyt hardcoded opcji formularzy** — periodycznie sprawdzaj czy selekty/dropdowny nie używają hardcoded tablic zamiast czytać z konfiguracji per-tenant.

---

## Praca z AI — meta-zasady

- **Po 2-3 nieudanych iteracjach — zatrzymaj się i zapytaj o cel, nie proponuj kolejnej wariacji** — jeśli kolejne próby dają wynik "nadal nie to", problem nie leży w implementacji tylko w niejasnym celu. AI powinno powiedzieć wprost: "coś jest nie tak z kierunkiem — powiedz mi co ten element ma robić dla odbiorcy" i poczekać na odpowiedź. Kontynuowanie iteracji bez tego to przepalanie tokenów i czasu.

---

## HTML do druku / generowanie PDF

- **Iteruj w przeglądarce, nie w PDF rendererze** — Puppeteer/Chromium headless zachowuje się inaczej niż przeglądarka przy `height` w mm, flex, grid i `page-break`. Dopracuj layout w zwykłym pliku HTML (`temp/templates/nazwa.html`) otwartym w Chrome, PDF generuj dopiero na końcu jako weryfikację. Każda iteracja przez PDF renderer kosztuje restart + akcję w UI — to 10× wolniej niż odświeżenie pliku.

- **Zanim zaczniesz layout — zwerbalizuj cel dokumentu, nie wygląd** — "oficjalny druk z rubrykami" to inny dokument niż "potwierdzenie dla klienta". Różny cel = inny layout. Format: "ten dokument dostaje X po to żeby Y" — to wystarczy żeby AI zaproponowało właściwy kierunek.

- **Static import dla stałych szablonów, nie `await import()`** — dynamiczny `await import()` jest cachowany przez Node.js przez cały czas życia procesu. Jeśli stała zmieni się w pliku, a serwer nie jest zrestartowany, `await import()` zwróci starą wartość bez żadnego błędu. Dla stałych: zawsze static import na górze pliku.

- **Server action resetująca dane w DB powinna zwracać nową wartość do klienta** — `router.refresh()` po server action nie resetuje stanu React komponentu (stan jest zachowany między soft-refresh). Zwróć nową wartość z akcji i ustaw stan bezpośrednio (`setState(result.data.value)`). Bez tego użytkownik widzi brak zmiany mimo zaktualizowanej bazy — cichy błąd trudny do zdiagnozowania.

---

## Claude Code Hooks — pułapki implementacyjne

- **`exit(2)` blokuje, `exit(1)` nie** — PreToolUse hook musi wyjść z kodem 2 żeby zablokować tool use. Exit 1 (np. unhandled exception w Pythonie) nie blokuje — narzędzie wykona się normalnie.
- **Komunikat blokujący idzie przez `stderr`, nie `stdout`** — Claude Code wyświetla `stderr` jako powód blokady. Print na `stdout` w blokującym hooku znika.
- **CWD hooka = CWD basha który go triggeruje** — nie ma stałego CWD dla hooków; jeśli użytkownik/AI zrobi `cd podkatalog`, hooki uruchomią się z tego podkatalogu. Rozwiązanie: każdy skrypt hooka na starcie wywołuje `git rev-parse --show-toplevel` i robi `os.chdir()` do roota projektu.
- **Ścieżki w `settings.json` są relatywne do CWD w momencie wykonania** — jeśli CWD = projekt root, użyj `.claude/hooks/skrypt.py`; jeśli CWD = `.claude/hooks/`, użyj `skrypt.py`. Nie zakładaj stałego CWD.
- **Hookom dane przychodzą przez stdin jako JSON** — format: `{"tool_name": "Bash", "tool_input": {"command": "..."}, "cwd": "...", ...}`. Komenda do sprawdzenia: `data["tool_input"]["command"]`.

---

## Dokumentacja

- **CLAUDE.md** — zasady pracy AI, nie logika biznesowa; source of truth dla każdej maszyny i każdego developera.
- **ADR** — każda nieodwracalna decyzja architektoniczna dostaje ADR; bez tego "dlaczego tak" ginie po pierwszej rotacji w zespole.
- **TASKS.md jako log sesji** — "Stan sesji" na dole TASKS.md = historia co kiedy i dlaczego; nieocenione przy wznowieniu po przerwie lub zmianie maszyny.
- **SETUP.md z pułapkami** — nie tylko "jak zainstalować" ale "co poszło nie tak i jak naprawić"; pisać z rzeczywistych problemów, nie z wyobraźni.
