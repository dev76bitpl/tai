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

---

## Backlog

- [ ] **Martwy `script_integrity` w `skills-manifest.json`** — hash `update-skills.py`
      nie zgadza się z plikiem (skrypt zmieniony w PR #57, hash nie). Zero referencji
      w hookach/pre-commit → nic go nie egzekwuje. Albo zaktualizować hash przy każdej
      zmianie skryptu (dodać guard), albo usunąć pole jako mylące.
- [ ] **Config canonicalizacja `ai_template_path`** (własna sesja + ADR) —
      `guard_template_sync` czyta `.pre-commit-hooks.config.json` (przez
      `stack.load_config`), a `doctor.py` + `new-project.py` używają
      `.claude/hooks/config.json`. Dwa różne pliki → guard sync template'u jest
      w nowych projektach trwale martwy. Plus `ai_template_path` bywa URL-em, a
      konsumenci wymagają lokalnej ścieżki (`Path(...).is_dir()`). Obejmuje też
      **błąd A**: w `--init` `create_config_json(root, root)` zapisuje remote
      *projektu* jako template path zamiast template'u.

---

## Następna sesja (SYSTEM — zacznij tu)

To jest sesja systemu (tai), nie projektu. Pierwszy ruch = utrwalić wnioski z
2026-06-04 (wyszły w cdue-kti), żeby system pracował na nich, a nie AI na ich pamiętaniu.

**Zadanie 1 (durable):** wpisz do `docs/AI_TEMPLATE_NOTES.md` + dodaj zasady do `CLAUDE.md`:
- Wniosek 1: AI jest bezstanowy — co nie jest w repo/guardzie, znika. Liczenie na
  pamięć/zrozumienie AI to bug. System ma NIE ufać AI.
- Wniosek 2: guardy pisze ten sam AI, który tnie zakręty → bywają fail-open
  (guard-ai-template omijany przez `git commit -F`) albo martwe (guard-template-sync
  przy URL). Dlatego user wciąż jest realnym guardem.
- Wniosek 3: template = produkt; projekty to miejsca, gdzie wychodzą jego błędy.
  Lekcja ma lądować w guardzie Z TESTEM — inaczej zostaje "w głowie" = nigdzie.
- **Zasada A:** żaden guard nie wchodzi bez testu dowodzącego, że blokuje bypass i
  przepuszcza resztę.
- **Zasada B:** rozdzielaj sesje "projekt" i "system" — nie mieszaj (mieszanie było
  źródłem dzisiejszego chaosu).

**Potem:** hardening A/B (patrz wpis 2026-06-04 niżej + backlog "Config canonicalizacja")
i push brancha `fix/template-hardening` (commit `fb05114`).

**Zasady pracy:** commit przez `-m`/heredoc, nigdy `-F` do omijania guardów;
dry-run guardów tą samą treścią co commit.

---

## Stan sesji

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
