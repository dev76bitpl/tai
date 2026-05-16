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

## Done when

- aplikacja działa na `http://localhost:3000`
- logowanie działa

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
