# DELIVERY CHECKLIST - Feature Closure Standard

Ten dokument jest wywoływany po każdej domkniętej funkcjonalności.
Cel: jeden stały standard domknięcia kroku bez ręcznego przypominania.

---

## 1. Scope closure

- Potwierdź, że zakres funkcjonalności z tej sesji jest domknięty (bez "half done").
- Zanotuj decyzje odłożone (defer) jako jawne TODO lub wpis do `docs/TASKS.md`.

---

## 2. Automated validation (minimum)

Uruchom testy i linter zgodnie ze stackiem projektu. Przykłady:

```bash
# Node.js
npm run lint && npm test

# Python
ruff check . && pytest

# PHP
composer run lint && composer run test

# Go
go vet ./... && go test ./...
```

Dodatkowo (gdy zmienił się schemat danych — zależne od ORM/stacku):
- np. Prisma: `npx prisma validate && npx prisma generate`
- np. Django: `python manage.py migrate --check`

Przy zmianach DB wymagających migracji:
- np. `npm run db:migrate` / `php artisan migrate` / `python manage.py migrate`

---

## 3. Manual validation

- Wykonaj scenariusze z `docs/TESTING.md` dla zmienionych flow.
- Pokryj co najmniej:
  - happy path
  - główny błąd biznesowy / edge case
  - regresje obszarów dotkniętych zmianą
- Przed merge/PR wykonaj obowiązkowy smoke krytycznego flow (minimum):
  1. Wejście do flow i poprawne załadowanie widoku bez błędów runtime.
  2. Akcja główna flow działa end-to-end na poprawnych danych.
  3. Negatywny scenariusz pokazuje poprawny komunikat błędu i nie psuje stanu.
  4. Po zakończeniu flow dane są widoczne tam, gdzie powinny (UI/API/DB zależnie od zakresu).
  5. Brak regresji w obszarze sąsiednim bezpośrednio dotkniętym zmianą (co najmniej 1 szybki scenariusz).
  6. Console/network bez nowych krytycznych błędów (5xx, uncaught errors).

Jeśli pojawił się nowy krytyczny flow, dopisz go do `docs/TESTING.md`.

---

## 4. Regression note

- Krótko zapisz wynik regresji: co sprawdzone, co przeszło, co wymaga follow-up.
- Jeżeli czegoś nie dało się zweryfikować, zapisz to jawnie jako ryzyko.

---

## 5. Documentation sync (required)

Zaktualizuj odpowiednie artefakty:

- `docs/TASKS.md` - status kroków + nowe taski wynikające z sesji
- `docs/ROADMAP.md` - status faz / kolejnych etapów
- `docs/TESTING.md` - nowe lub zmienione scenariusze
- `README.md` - gdy zmienia się flow użycia, komendy, mapa dokumentacji
- `docs/SETUP.md` - gdy zmienia się setup, komendy, pułapki środowiskowe
- `CLAUDE.md` - gdy dochodzi nowa trwała zasada pracy
- `docs/adr/*` - jeśli zapadła decyzja architektoniczna

### Czy flow ma wpis w pomocy / dokumentacji użytkownika?

Nowa funkcjonalność użytkownika nie trafia do pomocy automatycznie. Jeśli projekt ma generowane sekcje pomocy (z rejestrów funkcji), strażnik pilnuje tylko ich wzajemnej spójności — nie wymusza dokumentacji nowego flow. To ręczna bramka:

- [ ] Czy ten flow jest **widoczny dla użytkownika** (ekran / akcja / ustawienie)? Jeśli nie → pomiń (background / dev-only).
- [ ] Jeśli tak — czy ma wpis w pomocy / dokumentacji użytkownika (opis ustawienia, uprawnienia, automatu albo artykuł „jak zrobić X")?
- [ ] Jeśli świadomie odkładamy pomoc → zapisz jako TODO w `docs/TASKS.md`, nie zostawiaj cicho.

---

## 6. Commit package

Zasada:

- jeden commit = jeden domknięty krok
- kod + testy + docs razem

Format commit message:

```text
type(scope): short description

- file-or-component: what changed and why
- file-or-component: what changed and why
- impact if non-obvious
```

Dla małych zmian dopuszczalny sam subject.

---

## 7. Optional release note (recommended)

Przy większej zmianie dopisz 3-liniowe podsumowanie:

- Co zmieniono
- Jak zweryfikowano
- Co jest następnym krokiem
