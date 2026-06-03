# Tasks

Ten plik jest logiem wykonanych prac i backlogiem usprawnień.
Checklisty implementacyjne per faza znajdują się wyłącznie w [docs/ROADMAP.md](ROADMAP.md).

---

## Aktualny fokus

- [x] `update-skills`: klucze manifestu cross-platform (`rel.as_posix()`)
- [x] `new-project --init`: reset wersjonowania (usuwa CHANGELOG, manifest → 0.0.0)
- [x] `new-project --init`: świeży git + automatyczny init commit (`--no-git` opt-out)
- [x] `new-project --init`: auto-instalacja guardów (pre-commit + commit-msg)

---

## Backlog

- [ ] **Config canonicalizacja `ai_template_path`** (własna sesja + ADR) —
      `guard_template_sync` czyta `.pre-commit-hooks.config.json` (przez
      `stack.load_config`), a `doctor.py` + `new-project.py` używają
      `.claude/hooks/config.json`. Dwa różne pliki → guard sync template'u jest
      w nowych projektach trwale martwy. Plus `ai_template_path` bywa URL-em, a
      konsumenci wymagają lokalnej ścieżki (`Path(...).is_dir()`). Obejmuje też
      **błąd A**: w `--init` `create_config_json(root, root)` zapisuje remote
      *projektu* jako template path zamiast template'u.

---

## Stan sesji

- 2026-06-03: fix `update-skills` — `collect_files` używał `str(rel)` (backslashe na
  Windows → rozjazd manifestu między OS). Zmiana na `rel.as_posix()`; 2 wcześniej
  czerwone testy `TestCollectFiles` zielone, 35/35 modułu. Branch `fix/update-skills-path-separator`.
  Wykryto przy okazji: config canonicalizacja (backlog) + błąd A/Q2 w `new-project` (fokus).
- 2026-06-03: `new-project.py` domknięty dla trybu `--init` — reset wersjonowania
  + fresh git + init commit + instalacja guardów. 29/29 testów modułu, 2× e2e na
  realnym klonie. Powiązany fix `update-skills` (posix paths) → PR #54. Config
  canonicalizacja + błąd A świadomie odłożone na osobną sesję z ADR (backlog).
