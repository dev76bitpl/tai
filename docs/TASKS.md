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
