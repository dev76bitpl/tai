# Tasks — przykład wypełnienia

> **To jest plik przykładowy** — pokazuje jak prowadzić TASKS.md przez sesje.
> Wypełnij `docs/TASKS.md` dla swojego projektu i usuń ten plik.

---

# Tasks

Ten plik jest logiem wykonanych prac i backlogiem usprawnień.
Checklisty implementacyjne per faza znajdują się wyłącznie w [docs/ROADMAP.md](ROADMAP.md).

---

## Aktualny fokus

- [x] Lista zamówień z paginacją — filtr statusu i daty
- [ ] Eksport zamówień do CSV

---

## Backlog

- [ ] Powiadomienia email przy zmianie statusu zamówienia
- [ ] Panel admina — zarządzanie użytkownikami
- [ ] Raport miesięczny PDF

---

## Ukończone

- [x] Auth — logowanie, sesje, reset hasła
- [x] Dashboard — liczniki KPI, wykres tygodniowy
- [x] Zamówienia — CRUD, zmiana statusu

---

## Stan sesji

- **2026-03-12:** Domknięto filtrowanie zamówień (status + zakres dat). Wyszła potrzeba
  eksportu CSV — dodano do backlogu. Cel sesji: filtrowanie. CSV = dygresja, odłożone świadomie.

- **2026-03-08:** Auth gotowy, testy integracyjne przeszły. Znaleziono bug z reset hasła
  przy wygasłym tokenie — naprawiono w tej samej sesji (mały zakres, domknięte od razu).

- **2026-03-05:** Kick-off. Stworzono PROJECT_SCOPE, ADR-001, ROADMAP. Brak kodu — sesja
  planistyczna. Następne: auth.
