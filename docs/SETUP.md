# SETUP — Developer Environment

---

## Wymagania

| Narzędzie | Wersja | Uwaga |
|---|---|---|
| Node.js | ... | |
| Docker | ... | |

---

## Kroki instalacji

### 1. Sklonuj repo

```bash
git clone ...
cd ...
```

### 2. Zmienne środowiskowe

```bash
cp .env.example .env
```

Uzupełnij `.env`.

### 3. Uruchom bazę

```bash
docker compose up -d
```

### 4. Zainstaluj zależności

```bash
npm install
```

> ℹ️ `npm install` automatycznie uruchomi `prepare` → `scripts/setup-hooks.mjs`, który zainstaluje `pre-commit` (jeśli `pip`/`pipx` dostępny) i podpnie git hooki. Wymagany Python 3.9+ w PATH. Jeśli automat nie znajdzie pip — patrz krok "Guard system" niżej. Po instalacji uruchom `npm run doctor` żeby zweryfikować stan setupu.

### 5. Migracje

```bash
npm run db:migrate
```

### 6. Seed

```bash
npm run db:seed
```

### 7. Uruchom

```bash
npm run dev
```

---

## Guard system (pre-commit framework)

System guardów pilnuje commitów: format, lint, testy, sekrety, ADR, `[user-tested]`, język tytułu. Działa tak samo dla commitów z terminala (developer) i przez Claude — to jest source of truth.

**Instalacja jest zautomatyzowana** (krok 4: `npm install` → `prepare` script → bootstrap). Ten krok wykonujesz tylko gdy automat nie znalazł `pip`/`pipx`, albo gdy chcesz zweryfikować ręcznie.

**Wymaganie**: Python 3.9+ w PATH.

**Ubuntu 24.04+** (PEP 668 blokuje `pip install --user`):

```bash
sudo apt install pipx -y
pipx install pre-commit
pipx ensurepath
# nowa sesja terminala lub: source ~/.bashrc
```

**Windows / starszy Linux**:

```bash
python -m pip install --user pre-commit
python -m pre_commit install --hook-type pre-commit --hook-type commit-msg
```

> ℹ️ Używamy `python -m pip` zamiast `pip` i `python -m pre_commit` zamiast `pre-commit` — to działa cross-platform niezależnie od tego czy `Scripts/` jest w PATH (typowy problem na Windows po `pip install --user`). Standalone `pre-commit` (np. z `pipx`) też działa.

Weryfikacja:

```bash
npm run doctor
```

Doctor raportuje stan setupu: Python, Node, pre-commit, hooki, `.pre-commit-config.yaml`, aktualny branch.

Pełny przebieg hooków na całym repo:

```bash
pre-commit run --all-files
```

**Bypass flagi** (tylko z dokumentowanym powodem w body commita):
- `[skip-docs]` — pomiń sprawdzanie `docs/TASKS.md` i testów do nowych źródeł
- `[no-adr]` — zmiana architektoniczna bez ADR (świadoma decyzja)
- `[skip-test-check]` — commit bez `[user-tested]` (tylko dla zmian docs/chore)
- `[skip-sync]` — sekcja project-specific, nie idzie do AI template
- `SKIP=guard-lint,guard-tests git commit ...` — env var, nie ląduje w historii

CI (`.github/workflows/ci.yml`) uruchamia te same hooki server-side przez `pre-commit run --all-files`. Branch protection rule na `main` powinno wymagać zielonego CI przed merge — `--no-verify` lokalnie nie obejdzie tej warstwy.

---

## Claude Code hooks (opcjonalne, per-maszyna)

Hooki AI-specific w `.claude/hooks/` (sync do template, session context) wymagają dwóch plików per-maszyna (oba w `.gitignore`):

**Krok 1 — interpreter Python:**

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Otwórz `settings.local.json` i zamień `INTERPRETER` na właściwy:
- Ubuntu/macOS: `python3`
- Windows: `py`

**Krok 2 — ścieżka do AI template repo:**

```bash
cp .claude/hooks/config.json.example .claude/hooks/config.json
```

Otwórz `config.json` i ustaw `ai_template_path` na lokalną ścieżkę. Plik `config.json` powinien być w `.gitignore` — nie jest commitowany. Każda maszyna ma swoją wersję.

---

## Required GitHub repo settings (one-time, per repo)

Niektóre workflowy wymagają ustawień których nie można skonfigurować plikami w repo. Sprawdź / włącz po pierwszym klonie:

**Settings → Actions → General → Workflow permissions**:
- ☑ `Read and write permissions` — workflows mogą tworzyć commity i pushować (potrzebne dla `release-please` żeby utworzyć Release PR)
- ☑ `Allow GitHub Actions to create and approve pull requests` — `release-please-action` tworzy Release PR; bez tego workflow failuje z `GitHub Actions is not permitted to create or approve pull requests`

Alternatywnie (premium security): wygenerować fine-grained PAT scoped na to repo, dodać jako secret `RELEASE_PLEASE_TOKEN`, zmienić workflow żeby używał `token: ${{ secrets.RELEASE_PLEASE_TOKEN }}`. Wymagane w org-ach gdzie powyższe checkboxy są wyłączone na poziomie organizacji.

Sprawdzenie obecnych ustawień (CLI):

```bash
gh api repos/<owner>/<repo>/actions/permissions/workflow
```

Oczekiwane: `default_workflow_permissions: "write"`, `can_approve_pull_request_reviews: true`.

Ustawienie przez CLI (zamiast UI):

```bash
gh api -X PUT repos/<owner>/<repo>/actions/permissions/workflow \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

---

## Done when

- aplikacja działa na `http://localhost:3000`
- logowanie działa
- `npm run doctor` → wszystkie required checks zielone
- `pre-commit run --all-files` → wszystkie hooki zielone (lub naprawialne problemy formatowania)
- GitHub repo settings powyżej ustawione (`gh api ...` zwraca `write` + `true`)

---

## Przydatne komendy

```bash
npm run dev        # serwer deweloperski
npm run build      # build produkcyjny
npm run test       # testy
npm run lint       # linting
npm run db:studio  # GUI bazy
```

---

## Znane pułapki

| Problem | Przyczyna | Rozwiązanie |
|---|---|---|
| `npm warn EBADENGINE` przy `npm install` | zainstalowana za stara wersja Node | `source ~/.nvm/nvm.sh && nvm install 22 && nvm use 22`; sprawdź wymaganie `engines.node` w `package.json` |
| `npm install` → `pre-commit install failed (exit 2)` z `/usr/bin/py` | Ubuntu 24.04: `/usr/bin/py` to nie Python launcher (jak na Windows); `pip install --user` zablokowany przez PEP 668 | `sudo apt install pipx -y && pipx install pre-commit && pipx ensurepath`, nowa sesja terminala, retry `npm install` |
| `error: externally-managed-environment` przy `pip install` | Ubuntu 24.04+ blokuje globalne pip (PEP 668) | użyj `pipx install pre-commit` zamiast `pip install --user pre-commit` |
| Aplikacja na innym urządzeniu w LAN (telefon, kiosk) zwraca błąd / formularz nie reaguje, na `localhost` działa | Next 15 dev blokuje cross-origin requesty z hostów spoza `localhost` (asset/HMR/server actions wyciszane lub zwracają błędy) | dodaj host LAN do `allowedDevOrigins` w `next.config` — najlepiej przez env (np. `ALLOWED_DEV_ORIGINS=192.168.1.10`, parsowane jako CSV w configu), nie hardkoduj IP. Restart `npm run dev` po zmianie. |
