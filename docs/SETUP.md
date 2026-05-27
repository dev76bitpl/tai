# SETUP — Developer Environment

Instrukcja dla nowego developera lub nowej maszyny. Przejdź kroki po kolei — nie pomijaj weryfikacji.

---

## Wymagania

| Narzędzie | Wersja | Uwaga |
|---|---|---|
| Runtime (Node / PHP / Python / Go / ...) | ... | uzupełnij per projekt |
| Baza danych | ... | uzupełnij per projekt |
| Docker | ... | jeśli projekt używa |
| Python | 3.9+ | wymagany przez guard system (pre-commit) |
| Git | dowolna | |

---

## Krok 1 – Init repo na GitHub (BLOKER)

> ⚠️ Bez tych ustawień release-please nie tworzy tagów ani GitHub Releases automatycznie, a branche trzeba sprzątać ręcznie po każdym merge. Ustaw zaraz po stworzeniu repo — przed pierwszym commitem.

**Settings → General → Pull Requests**:
- ☑ `Automatically delete head branches` — branche usuwane automatycznie po merge

**Settings → Actions → General → Workflow permissions**:
- ☑ `Read and write permissions`
- ☑ `Allow GitHub Actions to create and approve pull requests`

Weryfikacja i ustawienie przez CLI:

```bash
gh api repos/<owner>/<repo>/actions/permissions/workflow
# oczekiwane: "default_workflow_permissions": "write", "can_approve_pull_request_reviews": true

# jeśli nie — ustaw:
gh api -X PUT repos/<owner>/<repo>/actions/permissions/workflow \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

Alternatywnie (org z ograniczeniami): wygeneruj fine-grained PAT scoped na repo, dodaj jako secret `RELEASE_PLEASE_TOKEN`, zmień workflow żeby używał `token: ${{ secrets.RELEASE_PLEASE_TOKEN }}`.

---

## Krok 2 – Sklonuj repo

```bash
git clone ...
cd ...
```

---

## Krok 3 – Zmienne środowiskowe

```bash
cp .env.example .env
```

Uzupełnij `.env`.

---

## Krok 4 – Uruchom infrastrukturę (baza, cache, itp.)

```bash
docker compose up -d
```

---

## Krok 5 – Zainstaluj zależności

```bash
npm install   # lub: composer install / pip install / go mod download
```

> ℹ️ `npm install` automatycznie uruchomi `prepare` → `scripts/setup-hooks.mjs`, który zainstaluje `pre-commit` i podepnie git hooki. Jeśli automat zawiedzie — patrz Krok 7.

---

## Krok 6 – Migracje i seed

```bash
npm run db:migrate
npm run db:seed
```

---

## Krok 7 – Guard system (pre-commit)

Instalacja jest zautomatyzowana przez `npm install`. Ten krok tylko gdy automat zawiedzie.

**Ubuntu 24.04+** (PEP 668 blokuje `pip install --user`):

```bash
sudo apt install pipx -y
pipx install pre-commit
pipx ensurepath
# nowa sesja terminala lub: source ~/.bashrc
```

**Windows**:

```bash
pip install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

> ⚠️ Guard hooki wymagają `python3` w PATH. Na Windows domyślnie jest tylko `python`.
> Utwórz alias raz (PowerShell jako Administrator):
>
> ```powershell
> New-Item -ItemType HardLink -Path "C:\Python3X\python3.exe" -Target "C:\Python3X\python.exe"
> ```
>
> Zamień `C:\Python3X` na katalog instalacji Pythona (sprawdź: `where python`).

**Starszy Linux**:

```bash
pip install --user pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Weryfikacja:

```bash
npm run doctor
pre-commit run --all-files
```

**Bypass flagi** (tylko z dokumentowanym powodem w body commita):
- `[skip-docs]` — pomiń sprawdzanie TASKS.md i testów
- `[no-adr]` — zmiana architektoniczna bez ADR (świadoma decyzja)
- `[skip-test-check]` — commit bez `[user-tested]` (tylko docs/chore)
- `[skip-sync]` — sekcja project-specific, nie idzie do AI template
- `SKIP=guard-lint,guard-tests git commit ...` — env var, nie ląduje w historii

---

## Krok 8 – Claude Code hooks (per-maszyna)

**Krok 8a — interpreter Python:**

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Zamień `INTERPRETER` na właściwy: `python3` (Ubuntu/macOS) lub `py` (Windows).

**Krok 8b — ścieżka do AI template repo:**

```bash
cp .claude/hooks/config.json.example .claude/hooks/config.json
```

Ustaw `ai_template_path` na lokalną ścieżkę klonu AI template repo. Plik jest w `.gitignore` — każda maszyna ma swoją wersję.

**Krok 8c — klucz API Anthropic (per-projekt, opcjonalnie):**

W `.claude/settings.local.json` dodaj sekcję `env` z kluczem z [console.anthropic.com](https://console.anthropic.com):

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-api03-..."
  },
  "hooks": { ... }
}
```

Plik jest w `.gitignore` — klucz nie trafia do repo. Pełna instrukcja + troubleshooting (Auth conflict, rotacja, cross-platform): [`CLAUDE_AUTH.md`](./CLAUDE_AUTH.md).

---

## Krok 9 – Uruchom aplikację

```bash
npm run dev
```

Otwórz http://localhost:3000.

---

## Done when

- [ ] Infrastruktura działa (`docker compose ps` → running)
- [ ] Aplikacja działa na http://localhost:3000
- [ ] Logowanie działa
- [ ] `npm run doctor` → wszystkie required checks zielone
- [ ] `pre-commit run --all-files` → wszystkie hooki zielone
- [ ] GitHub repo settings ustawione (Krok 1)

---

## Przydatne komendy

```bash
npm run dev        # serwer deweloperski
npm run build      # build produkcyjny
npm run test       # testy
npm run lint       # linting
npm run db:studio  # GUI bazy
npm run doctor     # weryfikacja środowiska
```

---

## Znane pułapki

| Problem | Przyczyna | Rozwiązanie |
|---|---|---|
| `npm warn EBADENGINE` przy `npm install` | za stara wersja Node | `source ~/.nvm/nvm.sh && nvm install 22 && nvm use 22`; sprawdź `engines.node` w `package.json` |
| `npm install` → `pre-commit install failed (exit 2)` z `/usr/bin/py` | Ubuntu 24.04: `/usr/bin/py` to nie Python launcher; `pip install --user` zablokowany przez PEP 668 | `sudo apt install pipx -y && pipx install pre-commit && pipx ensurepath`, nowa sesja, retry `npm install` |
| `error: externally-managed-environment` przy `pip install` | Ubuntu 24.04+ blokuje pip globalnie (PEP 668) | `pipx install pre-commit` |
| Guard hooki → `python3: not found` (Windows) | Guard hooki wymagają `python3` w PATH | utwórz alias — patrz Krok 7 |
| Aplikacja na innym urządzeniu w LAN nie reaguje | Next 15 blokuje cross-origin z hostów spoza localhost | dodaj host LAN do `allowedDevOrigins` w `next.config` przez env (`ALLOWED_DEV_ORIGINS=IP`), restart `npm run dev` |
