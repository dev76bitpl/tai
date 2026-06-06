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
- [x] durable lessons: wnioski (bezstanowość AI, guardy fail-open, template=produkt) →
      `docs/AI_TEMPLATE_NOTES.md`; zasady (guard tylko z testem, rozdziel sesje system/projekt)
      → `CLAUDE.md` reguła 13a; lekcje praktyczne (utf-8 w hookach, guard fail-closed) → NOTES

---

## Backlog

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
  zautomatyzować w `new-project.py` post-init. Wykryte w cdue-kti (release-please padał od #2).
- [ ] **Onboarding + update z tai — jeden punkt wejścia** — dziura wykryta przy migracji
      cdue-kti (KROK 3)

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

- [x] **Config canonicalizacja `ai_template_path`** — ✅ KROK 2 zrobiony (ADR-002);
      pozostaje KROK 3: migracja cdue-kti (osobna sesja projektowa, Zasada B)

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

- 2026-06-07: nowa sekcja „SEO / znajdowalność — wzorce z buildu" w `docs/AI_TEMPLATE_NOTES.md`.
  Lekcja z projektu hackersmovie.org (cel C — znajdowalność): trzy uniwersalne wzorce — (1) treść
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
  AI-średnią. Lekcja wyciągnięta z sesji designu w projekcie cdue-kti (5 makiet hero →
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
  `test_guard_template_sync` 16, `_hook` 7). **KROK 3 (migracja cdue-kti) → następna sesja** —
  zaktualizować pliki guarda + `stack.py` w cdue-kti, naprawić `ai_template_path`; Zasada B.
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
  w projekcie cdue-kti: (1) `guard-ai-template` puszczał commit przy `git commit -F`
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
