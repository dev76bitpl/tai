# Setup — przykład wypełnienia

> **To jest plik przykładowy** — pokazuje poziom szczegółowości i format SETUP.md.
> Wypełnij `docs/SETUP.md` dla swojego projektu i usuń ten plik.

---

# Setup

## Wymagania

| Narzędzie | Wersja | Sprawdź |
|-----------|--------|---------|
| Node.js | 20+ | `node --version` |
| PostgreSQL | 15+ | `psql --version` |
| Python | 3.9+ | `python3 --version` |

---

## Instalacja

### 1. Zależności

```bash
npm install
```

`prepare` script automatycznie instaluje pre-commit hooks. Oczekiwany wynik:

```
pre-commit installed at .git/hooks/pre-commit
pre-commit installed at .git/hooks/commit-msg
```

### 2. Zmienne środowiskowe

```bash
cp .env.example .env.local
```

Wypełnij w `.env.local`:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/myapp_dev
NEXTAUTH_SECRET=dev-secret-change-in-prod
NEXTAUTH_URL=http://localhost:3000
```

### 3. Baza danych

```bash
npx prisma migrate dev
npm run db:seed
```

Oczekiwany wynik seed:

```
✓ Seeded 3 users
✓ Seeded 10 sample orders
```

### 4. Uruchomienie

```bash
npm run dev
```

Aplikacja dostępna na `http://localhost:3000`.

---

## Weryfikacja (done when)

- [ ] `http://localhost:3000` ładuje się bez błędów
- [ ] `npm run doctor` → wszystkie checksy zielone
- [ ] Login działa (user: `admin@example.com`, hasło: z seed)

---

## Znane pułapki

**`prisma migrate dev` kończy się błędem `relation already exists`**
Baza nie jest czysta. Rozwiązanie: `npx prisma migrate reset` (usuwa dane!).

**pre-commit nie instaluje się: `pipx: command not found`**
Na Ubuntu 24.04+ `pip install --user pre-commit` jest zablokowane przez PEP 668.
Zainstaluj przez: `sudo apt install pipx && pipx install pre-commit`.

**Port 5432 zajęty**
Inny proces (Docker?) trzyma PostgreSQL. Sprawdź: `lsof -i :5432`.
Alternatywnie zmień port w `DATABASE_URL` i uruchom Postgres na innym porcie.

**`npm run dev` — błąd `Cannot find module`**
Brakuje `npm install` po pull. Uruchom `npm install`.
