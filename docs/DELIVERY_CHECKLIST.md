# DELIVERY CHECKLIST - Feature Closure Standard

Ten dokument jest wywolywany po kazdej domknietej funkcjonalnosci.
Cel: jeden staly standard domkniecia kroku bez recznego przypominania.

---

## 1. Scope closure

- Potwierdz, ze zakres funkcjonalnosci z tej sesji jest domkniety (bez "half done").
- Zanotuj decyzje odlozone (defer) jako jawne TODO lub wpis do `docs/TASKS.md`.

---

## 2. Automated validation (minimum)

Uruchom:

```bash
npm run lint
npm run test
```

Dodatkowo (gdy zmienial sie model danych / Prisma):

```bash
npx prisma validate
npx prisma generate
```

Przy zmianach DB wymagajacych migracji:

```bash
npm run db:migrate
```

---

## 3. Manual validation

- Wykonaj scenariusze z `docs/TESTING.md` dla zmienionych flow.
- Pokryj co najmniej:
- happy path
- glowny blad biznesowy / edge case
- regresje obszarow dotknietych zmiana
- Przed merge/PR wykonaj obowiazkowy smoke krytycznego flow (minimum):
  1. Wejscie do flow i poprawne zaladowanie widoku bez bledow runtime.
  2. Akcja glowna flow dziala end-to-end na poprawnych danych.
  3. Negatywny scenariusz pokazuje poprawny komunikat bledu i nie psuje stanu.
  4. Po zakonczeniu flow dane sa widoczne tam, gdzie powinny (UI/API/DB zaleznie od zakresu).
  5. Brak regresji w obszarze sasiednim bezposrednio dotknietym zmiana (co najmniej 1 szybki scenariusz).
  6. Console/network bez nowych krytycznych bledow (5xx, uncaught errors).

Jesli pojawil sie nowy krytyczny flow, dopisz go do `docs/TESTING.md`.

---

## 4. Regression note

- Krotko zapisz wynik regresji: co sprawdzone, co przeszlo, co wymaga follow-up.
- Jezeli czegos nie dalo sie zweryfikowac, zapisz to jawnie jako ryzyko.

---

## 5. Documentation sync (required)

Zaktualizuj odpowiednie artefakty:

- `docs/TASKS.md` - status krokow + nowe taski wynikajace z sesji
- `docs/ROADMAP.md` - status faz / kolejnych etapow
- `docs/TESTING.md` - nowe lub zmienione scenariusze
- `README.md` - gdy zmienia sie flow uzycia, komendy, mapa dokumentacji
- `docs/SETUP.md` - gdy zmienia sie setup, komendy, pulapki srodowiskowe
- `CLAUDE.md` - gdy dochodzi nowa trwala zasada pracy
- `docs/adr/*` - jesli zapadla decyzja architektoniczna

---

## 6. Commit package

Zasada:

- jeden commit = jeden domkniety krok
- kod + testy + docs razem

Format commit message:

```text
type(scope): short description

- file-or-component: what changed and why
- file-or-component: what changed and why
- impact if non-obvious
```

Dla malych zmian dopuszczalny sam subject.

---

## 7. Optional release note (recommended)

Przy wiekszej zmianie dopisz 3-liniowe podsumowanie:

- Co zmieniono
- Jak zweryfikowano
- Co jest nastepnym krokiem
