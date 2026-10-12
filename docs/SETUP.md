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

**Język artefaktów (CLAUDE.md reguła 2) — angielski, egzekwowany na dwóch warstwach:**
- **subject commita** → lokalny guard `guard-commit-lang` (commit-msg stage); bypass `SKIP=guard-commit-lang`
- **tytuł + opis PR** → CI workflow `PR language` (`pull_request`, bo PR body istnieje tylko na GitHubie — pre-commit go nie widzi); polskie stringi UI w opisie trzymaj w \`backtickach\` (bloki kodu są pomijane); bypass: `[skip-lang]` w body PR
- wspólny detektor: `scripts/dev-guards/lang.py` (jedna lista, oba checki)

**Dane osobowe — strażnik `guard-pii` (pre-commit stage):**

> Po ludzku: commit, który dodaje dane prawdziwej osoby, nie przechodzi. Z historii Gita takich
> danych nie da się potem wygodnie usunąć, więc zatrzymujemy je przed wejściem.

- łapie w **dodanych liniach**: PESEL (z sumą kontrolną), numer konta (26 cyfr, mod 97), telefon
  komórkowy, e-mail w publicznej domenie pocztowej (gmail, wp, onet…) oraz nazwiska z lokalnej listy;
  w komunikacie wartości są zamaskowane
- **lista nazwisk nie istnieje, dopóki jej nie założysz** — bez niej strażnik łapie numery i e-maile,
  ale nazwisk nie. Plik `~/.config/76bit/pii-names.txt`, jedno nazwisko w linii (min. 3 znaki, `#` =
  komentarz). Inna ścieżka: zmienna `PII_NAMES_FILE`. Lista zostaje na maszynie, nigdy w repo
- publiczne dane firmowe (telefon biura, adres kontaktowy w prywatnej domenie pocztowej) dopisz do
  `~/.config/76bit/pii-public.txt` (albo `PII_PUBLIC_FILE`) — przestają być zgłaszane
- zmyślone dane w testach i przykładach: dopisz `pii-ok` w tej samej linii
- fałszywy alarm, który sprawdziłeś: `SKIP=guard-pii git commit ...`
- gdy strażnik nie umie odczytać zmian, **blokuje** commit zamiast przepuścić
- pomija pliki binarne i lockfile; detektor `scripts/dev-guards/pii.py` da się zaimportować osobno
  (np. do cyklicznego skanu całego repo)
- nazwy rodzajów zwracane przez detektor (`PESEL`, `bank account`, `phone`, `private e-mail`,
  `listed name`) są **kontraktem**: skan, który zapisuje je w kluczach własnej listy wyjątków, po
  zmianie nazwy przestaje rozpoznawać stare klucze. Do 2026-10-12 nazwy były polskie — istniejącą
  listę przepisz raz, z kopią zapasową:
  ```bash
  cp lista-wyjatkow.txt lista-wyjatkow.txt.bak
  sed -i -e 's/:numer konta:/:bank account:/' -e 's/:telefon:/:phone:/' \
         -e 's/:e-mail prywatny:/:private e-mail:/' -e 's/:nazwisko z listy:/:listed name:/' lista-wyjatkow.txt
  ```

---

### Testy strażników

Każdy strażnik ma test, który uruchamia go jako osobny proces i sprawdza kod wyjścia. Testy
leżą obok strażników, więc jadą z nimi do projektu:

- `.claude/hooks/tests/` — hooki Claude Code (blokada = kod `2`)
- `scripts/dev-guards/tests/` — strażnicy commita i sprawdzenie języka PR (blokada = kod `1`)

```bash
python3 -m pytest -q        # z katalogu głównego; katalogi wymienia pytest.ini
```

Wymaga `pytest` (`pip install pytest`; na Ubuntu 24.04+ `sudo apt install python3-pytest`).
Nowy strażnik bez pliku testów wywala `test_every_guard_has_tests.py` /
`test_every_hook_has_tests.py` — pokrycie nie może się cofnąć po cichu. Wzór testu:
`scripts/dev-guards/tests/harness.py` i `.claude/hooks/tests/hook_harness.py` (tymczasowe
repozytorium, kopia strażników, `run_guard` / `run_hook`).

`npm run doctor` sprawdza, czy `pytest` jest dostępny, i przy braku podaje polecenie instalacji
(ostrzeżenie, nie błąd — bez `pytest` strażnicy działają, nie da się tylko uruchomić ich testów).

**Projekt o innym stosie niż Python** (np. node): testy strażników są w Pythonie, a
`guard-tests` przy commicie odpala wyłącznie komendę testów wykrytego stosu — więc **przy
commicie test własnego strażnika nie uruchamia się sam**. Pilnuje go CI: krok `Run tests`
w `.github/workflows/guards.yml` (`python3 -m pytest -q`) jedzie z szablonem i chodzi przy każdym
PR. Lokalnie, po zmianie strażnika albo dopisaniu nowego, uruchom `python3 -m pytest -q` ręcznie
przed commitem. Katalog `tests/` (testy narzędzi szablonu) znika przy `new-project.py --init`;
wpis `tests` w `pytest.ini` może zostać — `pytest` pomija nieistniejący katalog.

---

## Krok 8 – Claude Code hooks (per-maszyna)

**Krok 8a — interpreter Python:**

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Zamień `INTERPRETER` na właściwy: `python3` (Ubuntu/macOS) lub `py` (Windows).

Sprawdzenie: `npm run doctor`, sekcja „Claude Code hooks”. Ten plik jest per-maszyna i poza
repozytorium, więc warstwa commita może być cała zielona, gdy żaden hook Claude Code nie działa:

| Co widać w raporcie | Co to znaczy | Skutek |
|---|---|---|
| `⚠ .claude/settings.local.json missing` | pliku nie skopiowano — żaden hook się nie odpala | ostrzeżenie |
| `✗ ... still contains the INTERPRETER placeholder` | znacznik niepodmieniony — każdy hook wywala się przy starcie | błąd, kod wyjścia `1` |
| `✗ .claude/settings.local.json unreadable` | plik nie jest poprawnym JSON-em | błąd, kod wyjścia `1` |
| `⚠ Guard hooks present ... but not wired: <nazwy>` | strażnik `guard-*.py` jest w `.claude/hooks/`, ale nie ma go w pliku (np. doszedł z szablonu później) — dopisz wpis z `settings.local.json.example` | ostrzeżenie |
| `✓ Claude Code hooks wired (N guard hook(s))` | wszystkie strażniki z repo są podpięte | — |

**Krok 8b — konfiguracja strażników (dwa pliki):**

| Plik | Dla kogo | W repozytorium? | Co w nim trzymać |
|---|---|---|---|
| `.claude/hooks/config.json` | cały zespół | **tak, commitowany** | ustawienia projektu: komendy `lint` / `test`, `adr_patterns`, `dev_user_ports`, `repos` |
| `.claude/hooks/config.local.json` | jedna maszyna | nie (`.gitignore`) | to, co różni się między maszynami — przede wszystkim lokalna ścieżka klona szablonu |

```bash
cp .claude/hooks/config.json.example .claude/hooks/config.json   # dostosuj do projektu i zacommituj
```

`config.local.json` nakłada się na `config.json` — wartość z pliku lokalnego wygrywa. Czytają go
tak samo **obie warstwy strażników** (hooki Claude Code i strażnicy commita) oraz `npm run doctor`.

**Ścieżki ze swojego komputera nie wpisuj do `config.json`** — ten plik trafia do commita. Lokalny
klon szablonu wskaż jednym z dwóch sposobów (kolejność: pierwszy znaleziony wygrywa):

1. `export AI_TEMPLATE_PATH=/sciezka/do/klona` w `~/.bashrc` — jeden wpis obsługuje wszystkie projekty
2. `{"ai_template_path": "/sciezka/do/klona"}` w `.claude/hooks/config.local.json`
3. `ai_template_path` w `config.json` — tylko adres wspólny dla wszystkich (publiczny URL szablonu)

Bez żadnego z nich działa autodetekcja klona obok projektu, a potem publiczny URL. `npm run doctor`
pokazuje w sekcji „Optional integrations”, skąd wziął ścieżkę (`from $AI_TEMPLATE_PATH` /
`from config.local.json` / `from config.json`).

Pułapka: `config.local.json` potrafi też nadpisać komendę `lint` albo `test` — wtedy strażnik
commita na tej jednej maszynie sprawdza co innego niż u reszty zespołu i w repozytorium tego nie
widać. Trzymaj tam ścieżki i porty, nie komendy sprawdzające.

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

**Krok 8d — opcjonalny lektor „Done" po turze (cross-platform):**

Wygoda: system mówi na głos „Done" + nazwę projektu (folder roboczy), gdy Claude kończy turę —
przydatne, gdy nie patrzysz na ekran i masz otwartych kilka projektów naraz.
Realizuje to hook `Stop` w `~/.claude/settings.json`. Bramkowany **plikiem-przełącznikiem**
`~/.claude/speak.on`: hook odzywa się tylko gdy plik istnieje, więc włączasz/wyłączasz bez edycji configu.
Domyślnie **wyłączony** (nie twórz pliku, dopóki nie chcesz). Jest osobisty i per-maszyna — nie wpisuj go do repo.

Wybierz wariant dla swojego OS i dołóż sekcję `hooks` do `~/.claude/settings.json` (scal z istniejącą,
nie nadpisuj):

```jsonc
// macOS / Linux — używa pierwszego dostępnego: say (macOS), spd-say lub espeak (Linux)
{
  "hooks": {
    "Stop": [
      { "hooks": [ {
        "type": "command",
        "async": true,
        "command": "[ -f \"$HOME/.claude/speak.on\" ] && { p=$(basename \"$PWD\"); command -v say >/dev/null && say \"Done $p\" || command -v spd-say >/dev/null && spd-say \"Done $p\" || command -v espeak >/dev/null && espeak \"Done $p\"; } || true"
      } ] }
    ]
  }
}
```

```jsonc
// Windows — wbudowany lektor .NET (nic nie instalujesz). Wybiera polski głos "Paulina" jeśli
// jest w systemie, w przeciwnym razie używa domyślnego (try/catch nie wywala się przy jego braku).
{
  "hooks": {
    "Stop": [
      { "hooks": [ {
        "type": "command",
        "shell": "powershell",
        "async": true,
        "command": "if (Test-Path \"$env:USERPROFILE\\.claude\\speak.on\") { Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; try { $s.SelectVoice('Microsoft Paulina Desktop') } catch {}; $proj = Split-Path -Leaf $PWD; $s.Speak(\"Gotowe. $proj\") }"
      } ] }
    ]
  }
}
```

Włącz / wyłącz (działa na każdym OS z basha; Windows — Git Bash):

```bash
touch ~/.claude/speak.on   # włącz
rm -f ~/.claude/speak.on   # wyłącz
```

Dla wygody repo dostarcza gotowe komendy slash w `.claude/commands/speak-on.md` i `speak-off.md` —
tworzą/usuwają plik-przełącznik, więc włączasz lektora wpisując `/speak-on`, a wyłączasz `/speak-off`
(bez ręcznego `touch`/`rm`). Komendy są per-repo; skopiuj je do `~/.claude/commands/`, jeśli chcesz mieć
je globalnie w każdym projekcie.

Uwagi: hook odzywa się po **każdej** turze (zdarzenie `Stop`), nie tylko „koniec dużego tematu".
Nazwa projektu to nazwa folderu roboczego (`basename $PWD` / `Split-Path -Leaf $PWD`) — hooki nie mają
dostępu do tytułu okna Claude, więc folder jest pewnym, cross-platformowym źródłem. Wariant macOS/Linux
mówi „Done <projekt>" (celowo ASCII — `say`/`espeak` z domyślnym głosem potrafią zepsuć znaki
diakrytyczne); wariant Windows z polskim głosem czyta „Gotowe. <projekt>" poprawnie. Podmień frazę
i głos na własne, jeśli Twój lektor czyta lokalny język dobrze.

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
| Release PR (release-please) → CI w stanie `action_required` | GitHub od 2026-06-11 wstrzymuje workflowy z PR-ów tworzonych przez `github-actions[bot]` (zdarzenia z `GITHUB_TOKEN`) — zmiana bezpieczeństwa, nie błąd repo | kliknij „Approve workflows to run" w merge boxie release PR-a, albo zmerguj jeśli brak wymaganych checków; stałe obejście = App token/PAT zamiast `GITHUB_TOKEN` ([changelog](https://github.blog/changelog/2026-06-11-bot-created-pull-requests-can-run-workflows-if-approved/)) |
