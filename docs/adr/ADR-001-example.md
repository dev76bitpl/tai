# ADR-001 — Guard system: pre-commit + gitlint + gitleaks

> **To jest plik przykładowy** — pokazuje jak wypełnić ADR w tym projekcie.
> Twój pierwszy ADR zastąpi ten plik lub będzie numerowany ADR-002.

**Status:** accepted
**Data:** 2026-01-15

---

## Kontekst

Projekt ma kilku współpracowników i korzysta z AI (Claude Code) do implementacji.
Bez mechanicznej weryfikacji commity regularnie łamały konwencję nazewnictwa,
brakowało aktualizacji TASKS.md, a sekrety zdarzało się przypadkowo commitować.

Potrzebowaliśmy systemu który blokuje złe commity zanim trafią do historii —
bez polegania na tym że każdy pamięta zasady.

---

## Decyzje i uzasadnienia

### 1. pre-commit framework jako substrat

Używamy `pre-commit` (Python) jako runtime dla wszystkich hooków.

**Dlaczego:** industry standard, działa niezależnie od stacku projektu (Node, PHP, Python, Go),
ma gotowe integracje z gitlint i gitleaks, CI może mirror'ować lokalną konfigurację
jedną komendą (`pre-commit run --all-files`).

**Odrzucone:** własne skrypty bash w `.git/hooks/` — nie są wersjonowane, trudne do
dystrybuowania między developerami, brak standardowego mechanizmu bypass.

### 2. gitlint dla formatu commit message

Wymuszamy Conventional Commits (`feat:`, `fix:`, `docs:` itd.) przez gitlint.

**Dlaczego:** release-please parsuje subject commita do generowania CHANGELOG i version bump.
Niestandaryzowany subject = brak automatycznego releasu. Gitlint blokuje commit zanim
trafi do historii, nie po fakcie.

**Odrzucone:** commitlint (Node) — wymaga Node w każdym projekcie; gitlint działa wszędzie
gdzie jest Python.

### 3. gitleaks dla wykrywania sekretów

Skanujemy staged pliki przed każdym commitem.

**Dlaczego:** sekrety commitowane do historii wymagają rotacji kluczy i przepisania historii —
koszt wielokrotnie wyższy niż blokada przed commitem. gitleaks ma aktywnie utrzymywany
ruleset dla popularnych providerów (AWS, GitHub, Stripe itp.).

**Odrzucone:** ręczny review — zawodny przy wielu plikach i pracy pod presją czasu.

### 4. Własne hooki Python dla reguł projektu

Reguły specyficzne dla tego projektu (`[user-tested]`, ADR heuristic, TASKS.md staged)
jako lokalne skrypty Python w `scripts/dev-guards/`.

**Dlaczego:** reguły projektowe nie istnieją w żadnej gotowej bibliotece; Python jest
dostępny wszędzie gdzie działa pre-commit; skrypty są proste i łatwe do modyfikacji.

---

## Konsekwencje

- Każdy developer musi mieć Python 3.9+ i uruchomić `npm install` (auto-bootstrap hooków)
- Bypass możliwy przez flagi w body commita (`[skip-docs]`, `[no-adr]` itp.) — wymaga
  świadomego uzasadnienia, nie jest przypadkowy
- CI mirror'uje hooki server-side — `--no-verify` lokalnie nie pomaga przy push do main
- Dodanie nowej reguły = nowy skrypt w `scripts/dev-guards/` + wpis w `.pre-commit-config.yaml`
