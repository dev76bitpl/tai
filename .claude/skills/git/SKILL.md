---
name: git
description: "Git workflow protocol: branch strategy, commit format, PR creation, rebase, conflict resolution. Invoke when starting a feature, creating a commit, opening a PR, or resolving git issues. Actions: git, branch, commit, PR, pull request, merge, rebase, konflikt, gałąź, zacznij feature, nowy branch."
---

# Git Workflow

Protokół pracy z git zgodny z regułami w `CLAUDE.md`.

## Kiedy używać

Wywołaj gdy:
- Zaczynasz nowy feature lub fix
- Tworzysz commit
- Otwierasz PR
- Rozwiązujesz konflikt merge
- Potrzebujesz naprawić historię commitów

## Strategia branchy

```
main          ← stabilny, tylko przez PR
feat/nazwa    ← nowa funkcjonalność
fix/nazwa     ← naprawa buga
docs/nazwa    ← tylko dokumentacja
chore/nazwa   ← konfiguracja, zależności, narzędzia
```

**Nigdy** bezpośrednio na `main`. Każda zmiana = osobny branch + PR.

Zaproponuj nazwę brancha na początku sesji zanim zaczniesz implementację:
```bash
git checkout -b feat/nazwa-funkcjonalnosci
```

## Format commita

```
type(scope): krótki opis po angielsku  ← max 72 znaki

- plik-lub-komponent: co zmieniono i dlaczego
- plik-lub-komponent: co zmieniono i dlaczego

[user-tested] [skip-docs]   ← flagi ZAWSZE w body, nigdy w subject
```

**Typy:** `feat` `fix` `docs` `chore` `refactor` `test` `perf`

**Zasady subject:**
- po angielsku, tryb rozkazujący (`add`, `fix`, `update` — nie `added`, `fixed`)
- max 72 znaki (gitlint twardy limit)
- bez kropki na końcu

## Protokół przed każdym commitem

```bash
# 1. Sprawdź co jest staged
git status

# 2. Dry-run guardów
echo "subject\n\nbody" > /tmp/COMMIT_EDITMSG
COMMIT_EDITMSG=/tmp/COMMIT_EDITMSG pre-commit run --hook-stage commit-msg \
  --commit-msg-filename /tmp/COMMIT_EDITMSG

# 3. Jeśli wszystkie exit 0 → commit
git commit -m "$(cat <<'EOF'
type(scope): opis

- szczegóły

[flagi]
EOF
)"
```

## Tworzenie PR

Po zamknięciu brancha:

```bash
git push -u origin feat/nazwa

gh pr create \
  --title "type(scope): opis" \
  --body "## Summary
- co zmieniono

## Test plan
- [ ] happy path
- [ ] edge case"
```

PR musi zawierać:
- tytuł = subject commita (lub krótsze podsumowanie)
- body: co zmieniono + checklist testów

## Flagi bypass (używaj z uzasadnieniem w body)

| Flaga | Kiedy |
|-------|-------|
| `[user-tested]` | user przetestował manualnie (wymagane na `feat/*`, `fix/*`) |
| `[skip-docs]` | vendored code, brak potrzeby aktualizacji docs/TASKS.md |
| `[skip-test-check]` | zmiana czysto dokumentacyjna |
| `[no-adr]` | decyzja niewymagająca ADR |
| `[skip-sync]` | świadoma różnica z template |

## Częste sytuacje

### Konflikt merge
```bash
git status                    # które pliki mają konflikty
# edytuj pliki, usuń markery <<<< ==== >>>>
git add <rozwiązane-pliki>
git rebase --continue         # lub git merge --continue
```

### Popraw ostatni commit (przed pushem)
```bash
git commit --amend            # zmień message lub dodaj staged zmiany
```

### Wycofaj ostatni commit (zachowaj zmiany)
```bash
git reset HEAD~1              # zmiany wracają do working directory
```

### Interaktywny rebase (napraw historię przed PR)
```bash
# NIE używaj -i (wymaga interakcji) — użyj GIT_SEQUENCE_EDITOR
GIT_SEQUENCE_EDITOR="sed -i 's/^pick HASH/reword HASH/'" git rebase -i origin/main
```

## Zasady

- Jeden commit = jeden zamknięty krok (kod + dokumentacja razem)
- Nie commituj bez dry-runu guardów
- Merge należy do usera — AI nigdy nie merguje samodzielnie
- Force push tylko na feature branchach, nigdy na `main`
- `git push --force-with-lease` zamiast `--force` — bezpieczniejsze
