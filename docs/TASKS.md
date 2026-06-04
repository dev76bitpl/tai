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
- [ ] **Config canonicalizacja `ai_template_path`** — 🚧 w toku (ADR-002 accepted)

  > Po ludzku: guard, który pilnuje, by zmiany reguł wracały do wzorca, był w nowych
  > projektach martwy (czytał nieistniejący plik) i wymagał, żeby każdy miał wzorzec
  > na dysku. Po zmianie guard działa dla każdego od pierwszego commita, bez setupu.

  Decyzja: ADR-002 — sync = blokada-potwierdzenie (nie lokalne porównanie); lokalna
  ścieżka `ai_template_path` opcjonalna; jeden kanoniczny config `.claude/hooks/config.json`.
  Inkrementy KROK 2:
  - [x] **A** — `new-project.py`: `reset_adr_dir` czyści `docs/adr/` przy `--init`
        (ADR-y wzorca nie wyciekają do projektów; decyzja 6) + testy
  - [ ] **B** — `create_config_json`: usuń `_git_remote_url`, przestań auto-ustawiać
        `ai_template_path` (kasuje błąd A `create_config_json(root, root)`; decyzja 3)
  - [ ] **C** — `scripts/dev-guards/stack.py` `CONFIG_PATH` → `.claude/hooks/config.json`;
        usuń ślady `.pre-commit-hooks.config.json` (decyzja 4)
  - [ ] **D** — przepisz oba guardy sync (`scripts/dev-guards/guard_template_sync.py` +
        `.claude/hooks/guard-template-sync.py`) na tryb potwierdzenia (decyzja 1+2)
  - [ ] **E** — flaga `is_template: true` w `.claude/hooks/config.json` wzorca; guard
        respektuje (no-op sync we wzorcu; decyzja 5)

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

- 2026-06-04: Config canonicalizacja (branch `feat/config-canonical-template-sync`).
  ADR-002 napisany i zaakceptowany (sync = blokada-potwierdzenie zamiast lokalnego porównania;
  `ai_template_path` opcjonalny; kanoniczny `.claude/hooks/config.json`; reset `docs/adr/` przy
  init). Inkrement A domknięty: `new-project.py` → `reset_adr_dir` (na wzór `reset_versioning`)
  czyści `docs/adr/` przy `--init`, wpis ADR usunięty z `TEMPLATE_META`; 5 nowych testów, 34/34.
  Pozostałe inkrementy B–E (bug A, repoint stack.py, przepisanie guardów, flaga is_template) w toku.
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
