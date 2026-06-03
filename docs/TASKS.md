# Tasks

Ten plik jest logiem wykonanych prac i backlogiem usprawnień.
Checklisty implementacyjne per faza znajdują się wyłącznie w [docs/ROADMAP.md](ROADMAP.md).

---

## Aktualny fokus

- [x] `update-skills`: klucze manifestu cross-platform (`rel.as_posix()`)
- [ ] `new-project --init`: reset wersjonowania + auto init commit (branch `feat/init-versioning-reset`)
- [ ] `new-project --init`: poprawny `template_root` (błąd A) + auto-instalacja guardów (Q2)

---

## Backlog

- [ ] **Config canonicalizacja `ai_template_path`** (własna sesja + ADR) —
      `guard_template_sync` czyta `.pre-commit-hooks.config.json` (przez
      `stack.load_config`), a `doctor.py` + `new-project.py` używają
      `.claude/hooks/config.json`. Dwa różne pliki → guard sync template'u jest
      w nowych projektach trwale martwy. Dodatkowo `ai_template_path` bywa URL-em,
      a konsumenci wymagają lokalnej ścieżki (`Path(...).is_dir()`).

---

## Stan sesji

- 2026-06-03: fix `update-skills` — `collect_files` używał `str(rel)` (backslashe na
  Windows → rozjazd manifestu między OS). Zmiana na `rel.as_posix()`; 2 wcześniej
  czerwone testy `TestCollectFiles` zielone, 35/35 modułu. Branch `fix/update-skills-path-separator`.
  Wykryto przy okazji: config canonicalizacja (backlog) + błąd A/Q2 w `new-project` (fokus).
