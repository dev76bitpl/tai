# Tasks

Ten plik jest logiem wykonanych prac i backlogiem usprawnień.
Checklisty implementacyjne per faza znajdują się wyłącznie w [docs/ROADMAP.md](ROADMAP.md).

---

## Aktualny fokus

- [x] `update-skills`: klucze manifestu cross-platform (`rel.as_posix()`)
- [x] `new-project --init`: reset wersjonowania (usuwa CHANGELOG, manifest → 0.0.0)
- [x] `new-project --init`: świeży git + automatyczny init commit (`--no-git` opt-out)
- [x] `new-project --init`: auto-instalacja guardów (pre-commit + commit-msg)
- [x] `guard-ai-template`: fail-closed + czyta wiadomość z `-F`/heredoc (koniec cichego
      bypassu przez `git commit -F`; flagi `[no-template]`/`[template-done]` czytane też z pliku)
- [x] `session-context` + `update-skills`: wymuszenie utf-8 (koniec crashy cp1250 na Windows)
- [x] skille `copywriting` + `cro` zwendorowane do template'u (manifest + `.claude/skills/` + `docs/SKILLS.md`)
- [x] `CLAUDE.md` 2a: instrukcja obsługi aplikacji prowadzi tym, co user widzi na ekranie
      (adres, układ), nigdy etykietami wyczytanymi z kodu — user nie ma jak ich zweryfikować
- [x] `CLAUDE.md` 3d: instancja AI nadpisuje **każdą** zmienną przypiętą do domyślnego portu
      (adres bazowy, callbacki, webhooki), nie tylko `PORT` — inaczej AI nie zaloguje się do
      własnej instancji i oddaje pracę, której nie uruchomiło
- [x] durable lessons: wnioski (bezstanowość AI, guardy fail-open, template=produkt) →
      `docs/AI_TEMPLATE_NOTES.md`; zasady (guard tylko z testem, rozdziel sesje system/projekt)
      → `CLAUDE.md` reguła 13a; lekcje praktyczne (utf-8 w hookach, guard fail-closed) → NOTES

---

## Backlog

- [ ] **Lekki tor dla zmian trywialnych — wpiąć w `CLAUDE.md`** (uzgodnione, nie zakodowane)

  > Po ludzku: trywialna decyzja (np. „board: tak/nie") nie może kosztować godziny i 4 PR-ów.
  > Właściciel ustawia kierunek i klika merge; AI robi resztę.

  Ustalenia (dziś tylko w pamięci maszynowej — warstwa ulotna, reguła 13 → do repo):
  (1) **test trywialności** — odwracalne tanio + decyzja w jednym zdaniu + dotyka docs/configu nie
  runtime + zero ryzyka dla usera; choć jedno „nie" → pełny tor; (2) lekki tor **pomija** ADR,
  duplikat w wielu miejscach, branch/PR per drobiazg, hard-stop 16b — **zostaje** commit + uczciwy
  message; (3) **jedno źródło prawdy na poziom** (projekt vs template), w obrębie poziomu fakt ma
  jeden dom, reszta linkuje; (4) **batch** — jeden PR per repo, nie N osobnych; (5) **decyzja „A"**:
  AI robi branch→PR→sprzątanie autonomicznie, właściciel klika **merge raz na batch** (commit
  prosto na main = odrzucone); (6) pełny tor zostaje dla realnego kodu produktu.
  Wpięcie wytnie wyjątki w regułach 3/16b + „AI nie dodaje flag bypass sam" → **sam nie jest
  trywialne, idzie pełnym torem z testami guardów**. Osobna krótka sesja systemowa.

- [ ] **Martwy `script_integrity` w `skills-manifest.json`** — hash `update-skills.py`
      nie zgadza się z plikiem (skrypt zmieniony w PR #57, hash nie). Zero referencji
      w hookach/pre-commit → nic go nie egzekwuje. Albo zaktualizować hash przy każdej
      zmianie skryptu (dodać guard), albo usunąć pole jako mylące.
- [ ] **GitHub: uprawnienie Actions do tworzenia PR-ów** — projekty z template'u

  > Po ludzku: w nowym projekcie release-please nie wystawia release'u (czyli wersja nie
  > powstaje) dopóki nie włączysz jednego ustawienia na GitHubie — pada po cichu w CI.

  Projekty bootstrapowane z template'u mają domyślnie wyłączone „Allow GitHub Actions to
  create and approve pull requests" (`default_workflow_permissions: read`,
  `can_approve_pull_request_reviews: false`). release-please pada przy każdym merge do main:
  `GitHub Actions is not permitted to create or approve pull requests` — aż ktoś ręcznie
  włączy. Fix (per repo):
  `gh api -X PUT repos/<owner>/<repo>/actions/permissions/workflow -f default_workflow_permissions=write -F can_approve_pull_request_reviews=true`
  Do zrobienia: dopisać do `docs/SETUP.md` (sekcja GitHub settings / „Done when") albo
  zautomatyzować w `new-project.py` post-init. Wykryte w projekcie pochodnym (release-please
  padał od #2).
- [ ] **Onboarding + update z tai — jeden punkt wejścia** — dziura wykryta przy migracji
      projektu pochodnego

  > Po ludzku: dev który dostaje gotowy projekt (albo wraca do niego po czasie) nie wie,
  > co odpalić, żeby guardy i hooki działały — info jest porozrzucane. A devu, który chce
  > wciągnąć najnowsze poprawki ze wzorca, nikt nie mówi jak — robi to na piechotę.

  Trzy persony, dziś obsłużone nierówno:
  - **Nowy projekt z tai** — pokryte: README „Nowy projekt — 3 kroki" (`new-project.py --init`
    + `update-skills.py --apply` + `scope`). OK, bez zmian.
  - **Dołączenie do istniejącego projektu** — info istnieje (`docs/SETUP.md` Krok 7 pre-commit,
    Krok 8 Claude hooks; `doctor.py` mówi „skopiuj z config.json.example"), ale **rozsypane**,
    brak jednego punktu wejścia. Do zrobienia: README scaffold projektu kieruje wprost do
    `python3 scripts/doctor.py` jako pierwszego kroku po klonie; doctor robi audyt i wypisuje
    czego brakuje (config.json, pre-commit install, hooki). Rozważ czy doctor ma `--fix`.
  - **Update istniejącego projektu z tai** — **brak mechanizmu**. `update-skills.py --sync`
    pokrywa tylko skille; guardy (`scripts/dev-guards/*.py`, `.claude/hooks/*.py`) aktualizuje
    się ręcznie — dokładnie to, co KROK 3 robi gołymi rękami. Do zrobienia: udokumentowany
    flow „pull z tai" albo skrypt `update-from-template.py` (kopiuje kanoniczne guardy/hooki
    z `ai_template_path`, raportuje diff). To nietrywialne → **zasługuje na ADR-003**.

- [ ] **Bug: NameError w `.claude/hooks/guard-template-sync.py` (linia ~171)** — w ścieżce
      raportu desyncu jest `f"...({template_path})..."`, ale zmienna nazywa się `template_root`
      → `NameError`. Hook wywala się wyjątkiem (exit 1), a exit 1 **nie blokuje** → guard
      fail-open dokładnie w sytuacji, którą ma łapać (lokalny klon ustawiony + wykryty desync
      *.md/guardów). Aktywuje się gdy `ai_template_path` wskazuje realny klon. Fix: `template_path`
      → `template_root`. Wchodzi z testem dowodzącym (Zasada A): desync + valid clone → blok.

- [ ] **Niespójność: `session-context.py` podpowiada URL jako `ai_template_path`** — linia ~361
      sugeruje `"ai_template_path": "git@github.com:dev76bitpl/tai.git"`, ale wg ADR-002 URL jest
      martwy (guard wymaga lokalnego katalogu, URL → tryb potwierdzenia). `config.json.example`
      mówi poprawnie (lokalna ścieżka). Ujednolicić podpowiedź session-context do lokalnej ścieżki.

- [ ] **Migracja śledzenia zadań na GitHub Issues/Projects** — wg **ADR-004** (accepted, wykonanie odłożone)

  > Po ludzku: backlog w pliku markdown przestaje się skalować przy ~30 zadaniach — nieczytelny
  > dla właściciela, nie trzyma stanu (ręczne wykreślanie „zrobione"), brak jednej kolejności →
  > AI dryfuje w rekomendacjach co sesja. Przenosimy taski tam, gdzie i tak żyją PR-y i kod.

  Wg **ADR-004**: Issues = dane (priorytet/klasa jako etykiety, dwuwarstwowy opis przez Issue
  Template); Project = widok (kolumny statusu + jedna kolumna „Up next"); auto-zamykanie przez
  `Closes #N`; roadmapa → milestones; markdown zostaje fallbackiem dla projektów spoza GitHub.
  Do zrobienia: `.github/ISSUE_TEMPLATE/task.yml`, dokument konfiguracji Projects, tryb wyboru
  markdown/Issues w `new-project.py` (wykrycie remote GitHub), usunięcie/przepięcie guardów
  `TASKS.md`, skrypt migracji przez `gh issue create`. Każdy guard z testem (Zasada A).
  **Timing: granica bezpieczna dla projektu (po fazie/MVP), nie w środku krytycznej pracy.**

  **Metoda TAIGA** (**T**asks **A**s **I**ssues, **G**ates, **A**utomation) — rozszerzenia
  z researchu metodyk (CCPM / GitHub Spec Kit): epic + sub-issues dla funkcjonalności
  wielozadaniowych, mini-spec w body issue dla większych tasków, board Projects wyłącznie na
  wbudowanych automatach (zero ręcznych pól), komentarze issue jako audit trail, uporządkowana
  kolumna „Up next". Lekcja z pilota: do listy „Do zrobienia" dochodzi scaffold sekcji SETUP
  „praca z zadaniami przez gh" — kokpit (`gh issue list --milestone/--label`,
  `gh issue status/view --comments`), standup przez API milestones (postęp + due date jednym
  `gh api --jq`), skoki `--web`, board z CLI (scope `project`); wzór do uogólnienia z projektu
  pilotażowego (placeholdery zamiast repo/nazw milestones).

  > Pilot wykonania na konkretnym projekcie + kryterium oceny → prywatny backlog maintainera
  > (`docs/MAINTAINER_BACKLOG.local.md`), poza commitowanym logiem template'u (reguła 13a).

- [ ] **`new-project.py --init` oznacza scaffoldy jako "stan przed implementacją"**

  > Po ludzku: świeży projekt z template'u dostaje SETUP.md, który wygląda jak gotowa
  > instrukcja (`npm run db:migrate`, `localhost:3000`, "Logowanie działa"), choć żadna
  > z tych komend jeszcze nie istnieje. Czytelnik nie odróżnia szkieletu od faktu —
  > dokument kłamie od inicjalizacji do końca fundamentu, chyba że ktoś to zauważy.

  Wykryte w pilocie (2026-06-13): właściciel trafił na `db:migrate` w SETUP.md projektu,
  w którym `package.json` ma tylko `doctor` i `prepare`. Do zrobienia: `--init` dodaje
  automatyczną banderolę na górze scaffoldowanych docs (co działa po init: repo settings,
  clone, guard system, hooki; co jest szkieletem do wypełnienia; TODO usunięcia przy
  zamknięciu fundamentu) — albo scaffold przepisany na jawne placeholdery `<uzupełnij>`.
  Wzór banderoli: docs/SETUP.md w projekcie pilotażowym.

- [x] **Config canonicalizacja `ai_template_path`** — ✅ KROK 2 zrobiony (ADR-002);
      pozostaje KROK 3: migracja projektu pochodnego (osobna sesja projektowa, Zasada B →
      `docs/MAINTAINER_BACKLOG.local.md`)

  > Po ludzku: guard, który pilnuje, by zmiany reguł wracały do wzorca, był w nowych
  > projektach martwy (czytał nieistniejący plik) i wymagał, żeby każdy miał wzorzec
  > na dysku. Po zmianie guard działa dla każdego od pierwszego commita, bez setupu.

  Decyzja: ADR-002 — sync = blokada-potwierdzenie (nie lokalne porównanie); lokalna
  ścieżka `ai_template_path` opcjonalna; jeden kanoniczny config `.claude/hooks/config.json`.
  Inkrementy KROK 2:
  - [x] **A** — `new-project.py`: `reset_adr_dir` czyści `docs/adr/` przy `--init`
        (ADR-y wzorca nie wyciekają do projektów; decyzja 6) + testy
  - [x] **B** — `create_config_json`: usunięty `_git_remote_url`, nie auto-ustawia
        `ai_template_path` (zostaje placeholder; kasuje błąd A; decyzja 3) + test
  - [x] **C** — `scripts/dev-guards/stack.py` `CONFIG_PATH` → `.claude/hooks/config.json`;
        wyczyszczone wszystkie ślady `.pre-commit-hooks.config.json` (decyzja 4)
  - [x] **D** — oba guardy sync przepisane na tryb potwierdzenia
        (`scripts/dev-guards/guard_template_sync.py` + `.claude/hooks/guard-template-sync.py`):
        brak klona/URL/zła ścieżka → blokada-ack na CLAUDE.md zamiast cichego skipu;
        ścieżka do lokalnego klona → auto-weryfikacja (decyzja 1+2) + 23 testy
  - [x] **E** — `tai/.claude/hooks/config.json` z `is_template: true`; oba guardy no-op
        sync we wzorcu (decyzja 5)

---

## Następna sesja (SYSTEM — zacznij tu)

To jest sesja systemu (tai), nie projektu.

Domknięte (2026-06-04): durable lessons (wnioski → `AI_TEMPLATE_NOTES`, zasady A/B →
`CLAUDE.md` 13a), hardening hooków 1–3 (fail-closed guard, utf-8), push+merge
`fix/template-hardening` (PR #57), skille copywriting/cro (PR #59).

**Zadanie do zrobienia — Config canonicalizacja `ai_template_path` (+ADR):** to jedyny
otwarty kawałek hardeningu (items 4–6) i wymaga własnej sesji z ADR. Szczegóły w backlogu
niżej. Obejmuje: jeden kanoniczny plik configu (`guard_template_sync` czyta inny niż
`doctor.py`/`new-project.py` → guard sync martwy w nowych projektach), URL-aware
`ai_template_path` (konsumenci wymagają lokalnej ścieżki), oraz błąd A w `--init`
(`create_config_json(root, root)` zapisuje remote projektu jako template path). Każdy
guard, który tu powstanie/zmieni się, wchodzi z testem (Zasada A).

**Zasady pracy:** commit przez `-m`/heredoc, nigdy `-F` do omijania guardów;
dry-run guardów tą samą treścią co commit; nie mieszaj sesji system/projekt.

---

## Stan sesji

- 2026-06-24: **Lektor „Gotowe" + nazwa projektu — przeniesiony do template'u (branch
  `docs/speak-tts-announcer`).** Po ludzku: po skończonej turze komputer mówi „Gotowe" i nazwę
  projektu, w którym pracujesz — przydatne przy kilku otwartych naraz. Wariant usera (głos Paulina,
  fraza PL) był tylko w globalnym `~/.claude/settings.json`; do repo trafił uniwersalny rdzeń, nie
  żywy hook (reguła 13a — personalny hook narzucałby głos każdemu klonowi). Technicznie:
  `docs/SETUP.md` krok 8d — przełącznik `tts.on`→`speak.on`, Windows używa głosu „Microsoft Paulina
  Desktop" (try/catch fallback) + fraza „Gotowe.", oba warianty (Win + mac/linux) doklejają nazwę
  folderu roboczego (`Split-Path -Leaf $PWD` / `basename $PWD`) — tytułu okna Claude hooki nie widzą.
  Nowe `.claude/commands/speak-on.md` + `speak-off.md` (tworzą/usuwają `~/.claude/speak.on`) jadą
  z klonem, ale mówiący hook zostaje per-maszyna (do wklejenia z SETUP 8d). Globalny `settings.json`
  usera zaktualizowany przy okazji (poza repo). User przetestował lektora na żywo.

- 2026-06-14: **ADR-004 korekta — board zdegradowany do opcjonalnego (wynik pilotażu).**
  Pierwszy pilotaż wykonania metody Issues/Projects w projekcie pochodnym (model 1 właściciel
  + AI) obalił §2 w części „board = widok statusu": kanban bez wartości dla solo (nikt nie
  patrzy — start to sesja, koniec to merge PR-a), oczekiwany auto-postęp na tablicy nie
  istnieje OOTB (dobudowa = przerost, reguła 5/17), a realną potrzebę („czy projekt na czas")
  pokrywa strona Milestones (termin + % zamkniętych). Korekta: blok „Korekta 2026-06-14"
  + wskaźniki w §2/§4/Konsekwencjach — widok statusu = Milestones, board opcjonalny, widok
  „Roadmap" Projects opcjonalny. Kolumna „Up next" zostaje, ale oznaczona jako
  niezweryfikowana pilotażem (kolejność wykonania ≠ dashboard statusu — osobny argument,
  którego pilotaż nie testował; do sprawdzenia w kolejnym projekcie). Reszta decyzji
  (Issues=dane, `Closes #N`, milestones, markdown fallback) bez zmian. Branch
  `docs/adr-004-board-optional`.
- 2026-06-14: **scrub nazw projektów pochodnych z logu (reguła 13a).** Log tai przeciekał
  nazwami konkretnych projektów — proweniencja („wykryte w X") i operacyjne TODO. Rozdział:
  czysta proweniencja → „projekt pochodny" (zero straty); operacyjne TODO związane z nazwanym
  projektem (migracja KROK 3 config-canonicalizacji; pilot wykonania metody TAIGA + kryterium
  oceny) → prywatny, gitignorowany `docs/MAINTAINER_BACKLOG.local.md`. Zasada: generyczna metoda
  i lekcja zostają w commitowanym logu, projektowe wykonanie wychodzi. Atrybucja vendoringu
  (`coreyhaines31/marketingskills`) zostaje — to wymagane źródło zewnętrznego kodu, nie
  proweniencja. `.gitignore`: `docs/*.local.md`. Branch `chore/scrub-project-names`.
- 2026-06-14: `.gitignore` — dodany `.claude/hooks/.sync-hash`. To per-klon stan synchronizacji
  z template'em (`session-context.py` zapisuje hash HEAD template'u po auto-syncu, żeby przy
  starcie sesji wykryć drift). Nie jest współdzielonym baseline'em — gdyby był commitowany, stan
  synchronizacji jednego klonu nadpisywałby inny i każdy sync robiłby śmieciowy diff; dotąd wisiał
  jako untracked w każdym klonie. Branch `chore/gitignore-sync-hash`. Pochodne projekty dostaną
  wpis przez sync.
- 2026-06-14: nowa reguła workflow w `CLAUDE.md` §3 — **sprzątanie brancha po merge'u**. Po
  potwierdzeniu merge'a przez usera AI od razu proponuje i wykonuje `checkout main` → `pull` →
  usunięcie zmergowanego brancha (lokalnie `git branch -d` + zdalnie); kolejne zadanie startuje
  z czystego, dociągniętego maina. Trigger = zmergowany PR, nie „koniec sesji"; `git branch -d`
  (nie `-D`) odmawia skasowania niezmergowanej pracy, więc in-flight branche są bezpieczne.
  Feedback wykryty w sesji projektowej pochodnej (stale branch po merge'u PR + niedociągnięty
  lokalny main) — lekcja systemowa, więc ląduje w template (reguła 13a), nie w projekcie. Branch
  `docs/branch-cleanup-rule`. Pochodne projekty dostaną regułę przez sync skilli/CLAUDE.md.
- 2026-06-13: fix `guard-template-sync` (hook) — czytał `[skip-sync]` tylko z komendy, więc
  `git commit -F <plik>` z flagą w pliku był wadliwie blokowany (wykryte przy domykaniu commita
  w projekcie pochodnym na Windows/PowerShell, gdzie wieloliniowy message idzie przez plik). Bliźniaczy
  `guard-ai-template` umiał czytać `-F` od 2026-06-04, ale template-sync przeoczono. Fix:
  ekstrakcja wiadomości (`-m`/heredoc/here-string/`-F`) wyniesiona do współdzielonego
  `get_commit_message()` w `.claude/hooks/stack.py`; oba hooki jej używają (koniec dwóch kopii
  regexa); bypass sprawdza `haystack = command + message`. Testy: `-F` z flagą przepuszcza,
  `-F` bez flagi nadal blokuje (brak cichego bypassu) — 115/115 suite. Branch
  `fix/template-sync-read-file`. Efekt w projektach pochodnych: fix wsiąknie przez sync skilli.
- 2026-06-07: nowa sekcja „SEO / znajdowalność — wzorce z buildu" w `docs/AI_TEMPLATE_NOTES.md`.
  Lekcja z projektu pochodnego (cel: znajdowalność): trzy uniwersalne wzorce — (1) treść
  renderowana po stronie klienta = pusta strona dla crawlera → pre-render/SSG, diagnoza `curl|grep`;
  (2) jedno źródło domeny (`baseUrl`) → og/robots/sitemap generowane na buildzie, `lastmod` z daty
  zmiany treści nie deployu; (3) testuj output SEO (surowy HTML ma treść, host spójny w og/robots/
  sitemap, JSON-LD parsuje się i `<` zescape'owany). **Forma:** świadomie NIE w skillu `seo` — ten
  jest vendored (zewnętrzna referencja); lekcja z praktyki idzie do tai-owned `AI_TEMPLATE_NOTES.md`
  (ładowany na starcie każdej sesji). Bez testu — to wiedza, nie guard (13a). Branch
  `docs/seo-build-time-patterns` z main.

- 2026-06-04: dopisana uniwersalna meta-zasada do `docs/AI_TEMPLATE_NOTES.md` (sekcja
  „Praca z AI — meta-zasady"): nowy UI nie startuje od estetyki „AI-default", zakotwicz
  w specyfice biznesu, dopcham jeden kierunek do końca, sygnalizuj gdy coś pachnie
  AI-średnią. Lekcja wyciągnięta z sesji designu w projekcie pochodnym (5 makiet hero →
  pierwsze szkice były generyczne; user złapał regresję do średniej). Część user-specific
  została w pamięci maszynowej projektu, do template'u trafił tylko uniwersalny rdzeń
  (reguła 13a). Branch `docs/ui-anti-ai-default`.
- 2026-06-04: Config canonicalizacja KROK 2 KOMPLETNY (branch `feat/config-canonical-template-sync`).
  ADR-002 accepted. A: `reset_adr_dir` czyści `docs/adr/` przy init. B: `create_config_json`
  bez `_git_remote_url`, zostawia placeholder (bug A skasowany). C: `dev-guards/stack.py`
  `CONFIG_PATH` → `.claude/hooks/config.json`, wyczyszczone ślady `.pre-commit-hooks.config.json`.
  D: oba guardy sync (pre-commit + Claude hook) na tryb potwierdzenia — brak klona/URL/zła ścieżka
  → blokada-ack na CLAUDE.md (koniec cichego skipu); klon → auto-weryfikacja. E: `tai/.claude/hooks/
  config.json` z `is_template: true` → guardy no-op we wzorcu. Testy: 111/111 (nowe
  `test_guard_template_sync` 16, `_hook` 7). **KROK 3 (migracja projektu pochodnego) → prywatny
  backlog** — szczegóły projektowe poza commitowanym logiem template'u (`docs/MAINTAINER_BACKLOG.local.md`;
  reguła 13a; Zasada B).
- 2026-06-04: durable lessons utrwalone (branch `docs/durable-ai-lessons`). Wnioski 1–3
  (bezstanowość AI → system nie ufa AI; guardy bywają fail-open/martwe → user realnym
  guardem; template=produkt) → `docs/AI_TEMPLATE_NOTES.md`. Zasady A/B (guard tylko z
  testem; rozdziel sesje system/projekt) → `CLAUDE.md` reguła 13a. Lekcje praktyczne
  (utf-8 na stdout/stderr hooków, guard commit-msg fail-closed) → sekcja guard w NOTES.
  Items 4–6 hardeningu domknięte poza canonicalizacją `ai_template_path` (osobna sesja
  z ADR — patrz „Następna sesja" + backlog).
- 2026-06-04: zwendorowano skille `copywriting` + `cro` z coreyhaines31/marketingskills
  (commit `7f4af1ea`) — wpisy w `skills-manifest.json`, pobrane przez `update-skills.py
  --apply` (skan bezpieczeństwa czysty), wiersze w obu tabelach `docs/SKILLS.md`. Branch
  `feat/vendor-marketing-skills` z main. Item 5 z listy hardeningu 4–6 domknięty. Przy
  okazji wykryto martwy `script_integrity` (→ backlog).
- 2026-06-04: hardening hooków (branch `fix/template-hardening`). Wykryte podczas pracy
  w projekcie pochodnym: (1) `guard-ai-template` puszczał commit przy `git commit -F`
  bo `extract_commit_type` parsował tylko `-m` → cichy bypass; przepisany na fail-closed
  + czytanie wiadomości/flag z pliku `-F`, heredoc, here-string; gdy nie umie odczytać
  wiadomości → blok. Dodatkowo blokuje przy każdym tknięciu plików template'owych (dowolny
  typ), nie tylko feat/fix/docs/refactor. (2) `session-context._remote_head_hash` —
  `ls-remote` bez `encoding=utf-8` → wyjątek w wątku readera na Windows (cp1250); dodano
  `encoding="utf-8", errors="replace"`. (3) `update-skills.py` — brak `stdout.reconfigure`
  → crash przy emoji w `print` na cp1250; dodano reconfigure jak w `stack.py`/`session-context`.
  Przetestowane ręcznie (guard: 5 scenariuszy exit-code; update-skills: emoji print bez crashu).
  Items 4–6 (guard-template-sync URL, skille copywriting/cro do manifestu, AI_TEMPLATE_NOTES)
  odłożone — item 4 łączy się z backlogiem „Config canonicalizacja ai_template_path (+ADR)".
- 2026-06-03: fix `update-skills` — `collect_files` używał `str(rel)` (backslashe na
  Windows → rozjazd manifestu między OS). Zmiana na `rel.as_posix()`; 2 wcześniej
  czerwone testy `TestCollectFiles` zielone, 35/35 modułu. Branch `fix/update-skills-path-separator`.
  Wykryto przy okazji: config canonicalizacja (backlog) + błąd A/Q2 w `new-project` (fokus).
- 2026-06-03: `new-project.py` domknięty dla trybu `--init` — reset wersjonowania
  + fresh git + init commit + instalacja guardów. 29/29 testów modułu, 2× e2e na
  realnym klonie. Powiązany fix `update-skills` (posix paths) → PR #54. Config
  canonicalizacja + błąd A świadomie odłożone na osobną sesję z ADR (backlog).
- 2026-07-25: **Odwrócona domyślna rekomendacja CI — jeden job zamiast równoległych
  (branch `chore/ci-cost-model`, #104).** Powód z pomiaru: trzy projekty na tym template'cie
  wyczerpały wspólny darmowy limit 2000 min GitHub Actions w połowie miesiąca (lipiec: skolaro 986,
  cdue 779, cdue-elearning 227 = 1992). Template zalecał „niezależne checki w równoległych jobach",
  co pomijało jednostkę rozliczeniową: **Actions nalicza każdy JOB w górę do pełnej minuty** —
  zmierzone 487 min pracy → 779 min naliczonych (37% to zaokrąglanie), a w drugim repo 152 z 227 min
  to joby robiące po ~15 s. Do tego `push: main` po merge'u = duplikat wyniku z PR-a (połowa rachunku).
  Zmiana: `AI_TEMPLATE_NOTES` → jeden job domyślnie, zrównoleglenie jako świadomy wyjątek gdy minut
  jest w nadmiarze; dopisana metoda pomiaru (API rachunku bywa zerowe/bez scope'u — licz z czasów
  jobów, filtruj joby z 0 kroków = te które nie wystartowały z braku minut). `ci.yml`: trigger tylko
  `pull_request`, scaffold checków jako kroki w jobie `checks`, osobny job tylko dla skanera we
  własnym kontenerze. Wdrożenia w projektach = osobne PR-y (cdue #327).
- 2026-07-25 (cd.): **Korekta rekomendacji CI — nie „jeden job domyślnie", tylko trzy ruchy w kolejności
  ROI (#104).** Pierwsza wersja tej zmiany ustawiała jeden sekwencyjny job jako domyślny; właściciel
  odrzucił to w projekcie, bo wydłużało oczekiwanie na PR z ~2 do ~4-5 min. Wniosek dla template'u jest
  inny niż pierwotny: **dwa pierwsze ruchy są darmowe czasowo i robimy je zawsze** (zdjęcie CI z
  `push: main`; każde sprawdzenie krótsze niż minuta jako krok w jobie spoza ścieżki krytycznej —
  skaner pracujący 8 s w osobnym jobie kosztuje tyle co minuta builda). **Trzeci ruch — scalenie
  równoległych nóg — JUŻ kosztuje czas i nie ma domyślnej odpowiedzi**: policz obie strony i zapytaj
  właściciela. `ci.yml`: scaffold matrycy i builda wrócił jako opcja obok, z ceną obu stron w komentarzu;
  skan CVE opisany jako krok, nie job. Zostaje reguła zaokrąglania i metoda pomiaru (API rachunku bywa
  zerowe; licz z czasów jobów, odrzuć joby z 0 kroków = te które nie wystartowały z braku minut).
