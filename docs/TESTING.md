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

### Scenariusz 11 — release-please creates Release PR

- [ ] Po merge feat/fix commitów do main, workflow `Release Please` runs
- [ ] Auto-utworzony Release PR z `CHANGELOG.md` + version bump
- [ ] Merge Release PR → tag + GitHub Release
