# CLAUDE_AUTH — Klucz API dla Claude Code (per-projekt)

Instrukcja jak ustawić klucz Anthropic API per-projekt (a nie per-user / per-machine) oraz jak rozwiązywać typowe problemy z uwierzytelnianiem.

---

## Po co per-projekt

- Klucz wpięty w `.claude/settings.local.json` w katalogu projektu — Claude Code wczytuje go automatycznie po starcie sesji w tym katalogu.
- Każdy projekt może mieć własny klucz (osobne fakturowanie / limity / organizacje w Anthropic Console).
- Plik jest w `.gitignore` — klucz nie trafia do repo.

---

## Setup

**1. Wygeneruj klucz** w [console.anthropic.com](https://console.anthropic.com) → **Settings → API Keys → Create Key**.

**2. Otwórz `.claude/settings.local.json`** (skopiuj z `.example` jeśli jeszcze nie istnieje):

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

**3. Dodaj sekcję `env`** na początku obiektu:

```json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-api03-..."
  },
  "hooks": { ... }
}
```

**4. Restart Claude Code** (env var jest ładowany przy starcie sesji):
- Terminal: `/exit` lub `Ctrl+C` × 2, potem `claude`
- VS Code: zamknij panel Claude i otwórz ponownie (lub `Developer: Reload Window`)

**5. Weryfikacja** — w Claude Code:
```
/cost
```
Koszty powinny iść na klucz z `settings.local.json` (sprawdź organizację w Anthropic Console).

---

## Hierarchia auth

Claude Code wybiera klucz w tej kolejności (pierwszy znaleziony wygrywa):

1. Cloud providers (Bedrock, Vertex)
2. `ANTHROPIC_AUTH_TOKEN` (env var)
3. **`ANTHROPIC_API_KEY`** (env var lub `settings.local.json` → `env`)
4. `apiKeyHelper` (skrypt z `~/.claude/api-key-helper.sh`)
5. `CLAUDE_CODE_OAUTH_TOKEN` (env var)
6. Subscription OAuth (zalogowanie przez `/login`)

Per-projekt setup z `settings.local.json` → `env.ANTHROPIC_API_KEY` ląduje na **pozycji 3** i nadpisuje OAuth z subskrypcji.

---

## Sprawdzenie który klucz jest aktywny

**W terminalu z którego uruchamiasz Claude:**
```bash
env | grep ANTHROPIC_API_KEY
```

**Wewnątrz Claude Code** (slash command):
```
/cost
```

Pokazuje organizację / konto na które idą koszty.

---

## Rotacja klucza

1. Wygeneruj nowy klucz w Anthropic Console.
2. Zastąp wartość w `.claude/settings.local.json`.
3. Stary klucz **usuń w Console** (Settings → API Keys → Delete).
4. Restart Claude Code.

---

## Troubleshooting

### A. Komunikat: `Auth conflict: Using ANTHROPIC_API_KEY instead of Anthropic Console key`

**Objaw:** ostrzeżenie pokazuje się przy każdym starcie sesji, mimo że klucz z `settings.local.json` faktycznie działa (koszty idą na właściwe konto).

**Przyczyna:** Claude Code wykrywa dwa źródła auth jednocześnie:
- klucz z `settings.local.json` (`env.ANTHROPIC_API_KEY`)
- pozostałości zapisanej sesji Console w `~/.claude.json` (pola `oauthAccount` i `primaryApiKey`)

`/logout` czyści tylko `~/.claude/.credentials.json`, **nie** czyści pól w `~/.claude.json`.

**Naprawa:**

1. Backup:
   ```bash
   # Linux / macOS
   cp ~/.claude.json ~/.claude.json.bak

   # Windows (PowerShell)
   Copy-Item $env:USERPROFILE\.claude.json $env:USERPROFILE\.claude.json.bak
   ```

2. Otwórz `~/.claude.json` w edytorze i **usuń dwa pola na końcu pliku**:
   ```json
   "oauthAccount": { ... },
   "primaryApiKey": "sk-ant-api03-..."
   ```

3. Popraw przecinek przed `}` żeby JSON zostawał poprawny. Końcówka pliku powinna wyglądać tak:
   ```json
     "seenNotifications": {}
   }
   ```

4. Walidacja JSON:
   ```bash
   python3 -c "import json; json.load(open('$HOME/.claude.json')); print('OK')"
   ```

5. Restart Claude Code (`/exit` → `claude`).

**Każdy dev w zespole musi to zrobić jednorazowo** — pliki Claude Code są per-user, nie per-projekt.

---

### B. Klucz nie jest wczytywany

**Objaw:** Claude Code pyta o `/login` mimo że klucz jest w `settings.local.json`.

**Diagnostyka:**
1. Walidacja JSON:
   ```bash
   python3 -c "import json; json.load(open('.claude/settings.local.json')); print('OK')"
   ```
2. Sprawdź czy klucz nie ma whitespace / nowych linii.
3. Sprawdź czy startujesz Claude **z katalogu projektu** (nie z domowego).
4. Wykonaj pełny restart (zamknięcie sesji, nie reload).

---

### C. Koszty idą na zły klucz

**Objaw:** `/cost` pokazuje inną organizację niż oczekiwana.

**Przyczyna:** zmienna `ANTHROPIC_API_KEY` jest ustawiona globalnie w shellu (`.bashrc` / `.zshrc` / `$PROFILE`) i ma pierwszeństwo nad `settings.local.json` w niektórych konfiguracjach.

**Diagnostyka:**
```bash
# Linux / macOS
grep -rn "ANTHROPIC_API_KEY" ~/.bashrc ~/.zshrc ~/.profile ~/.bash_profile 2>/dev/null

# Windows (PowerShell)
[Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
```

**Naprawa:** usuń globalny export i polegaj wyłącznie na `settings.local.json`.

---

### D. Klucz wyciekł

Jeśli klucz został zacommitowany lub wkleił się gdzieś poza `.claude/settings.local.json`:

1. **Natychmiast** wygeneruj nowy klucz w Anthropic Console i usuń stary.
2. Zaktualizuj `.claude/settings.local.json` na każdej maszynie.
3. Jeśli klucz trafił do gita: użyj `git filter-repo` / BFG do usunięcia z historii (sam revert nie wystarczy — klucz zostaje w obiektach git).

---

## Cross-platform — lokalizacje plików

| Plik | Linux / macOS | Windows |
|------|---------------|---------|
| Klucz per-projekt | `.claude/settings.local.json` | `.claude\settings.local.json` |
| Console OAuth state | `~/.claude.json` | `%USERPROFILE%\.claude.json` |
| Credentials cache | `~/.claude/.credentials.json` | `%USERPROFILE%\.claude\.credentials.json` |
| Global settings | `~/.claude/settings.json` | `%USERPROFILE%\.claude\settings.json` |

---

## Linki

- [Anthropic Console — API Keys](https://console.anthropic.com)
- [Claude Code — Authentication docs](https://code.claude.com/docs/en/authentication)
- [Claude Code — Settings docs](https://code.claude.com/docs/en/settings)
