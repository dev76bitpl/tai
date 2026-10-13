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

> Wzór wypełnienia tego pliku: [docs/examples/SETUP.example.md](examples/SETUP.example.md).

---

## Krok 1 – Sklonuj repo

```bash
git clone ...
cd ...
```

---

## Krok 2 – Zmienne środowiskowe

```bash
cp .env.example .env
```

Uzupełnij `.env`.

---

## Krok 3 – Uruchom infrastrukturę (baza, cache, itp.)

```bash
docker compose up -d
```

---

## Krok 4 – Zainstaluj zależności

```bash
npm install   # lub: composer install / pip install / go mod download
```

> ℹ️ `npm install` automatycznie uruchomi `prepare` → `scripts/setup-hooks.mjs`, który zainstaluje `pre-commit` i podepnie git hooki. Jeśli automat zawiedzie — [docs/GUARDS.md](GUARDS.md), sekcja „Strażnicy commita”.

---

## Krok 5 – Migracje i seed

```bash
npm run db:migrate
npm run db:seed
```

---

## Krok 6 – Strażnicy i narzędzia AI

Każda nowa maszyna potrzebuje trzech rzeczy, żeby strażnicy projektu działali:

```bash
npm install                                    # instaluje pre-commit i podpina strażników commita
cp .claude/settings.local.json.example .claude/settings.local.json   # hooki Claude Code; zamień INTERPRETER
npm run doctor                                 # pokaże, czego brakuje
```

Nowy projekt przechodzi to (i resztę startu: repo, etykiety, brief, skille) krok po kroku przez
`python3 scripts/project-setup.py`. Opis każdego elementu, konfiguracja i pułapki:
[docs/GUARDS.md](GUARDS.md).

---

## Krok 7 – Uruchom aplikację

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
- [ ] Ustawienia repo na GitHubie są na miejscu (`npm run doctor`, sekcja „Repository state”)

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
| Aplikacja na innym urządzeniu w LAN nie reaguje | Next 15 blokuje cross-origin z hostów spoza localhost | dodaj host LAN do `allowedDevOrigins` w `next.config` przez env (`ALLOWED_DEV_ORIGINS=IP`), restart `npm run dev` |

Pułapki strażników i narzędzi AI (pre-commit, Python, release-please): [docs/GUARDS.md](GUARDS.md), sekcja „Znane pułapki”.
