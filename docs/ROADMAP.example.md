# Roadmap — przykład wypełnienia

> **To jest plik przykładowy** — pokazuje poziom szczegółowości i format ROADMAP.md.
> Wypełnij `docs/ROADMAP.md` dla swojego projektu i usuń ten plik.

---

# Roadmap

---

## Faza 1 — Fundament ✅

**Cel:** Działający szkielet aplikacji z auth i podstawowym CRUD.

**Zakres:**
- [x] Auth — logowanie email/hasło, sesje, reset hasła
- [x] Model danych — zamówienia, użytkownicy, statusy
- [x] Dashboard — widok główny z licznikami KPI
- [x] Deploy na staging

**Done when:**
- Można się zalogować i wylogować
- Zamówienie da się stworzyć, edytować i zmienić status
- Staging działa pod własną domeną z SSL

**Zależności:** brak

---

## Faza 2 — Operacje 🚧

**Cel:** Narzędzia do codziennej pracy — lista, filtrowanie, eksport.

> Po ludzku: dziś żeby znaleźć zamówienie trzeba przewijać całą listę.
> Po tej fazie można filtrować po statusie i dacie, a wyniki wyeksportować do Excela.

**Zakres:**
- [x] Lista zamówień z paginacją
- [x] Filtry: status, zakres dat, klient
- [ ] Eksport do CSV
- [ ] Powiadomienia email przy zmianie statusu

**Done when:**
- Filtrowanie działa z kombinacją wszystkich filtrów jednocześnie
- Eksport CSV zawiera te same dane co widok listy z aktywnymi filtrami
- Email dociera w ciągu 60s od zmiany statusu (weryfikacja na staging)

**Zależności:** Faza 1

---

## Faza 3 — Raportowanie 🔜

**Cel:** Widoczność biznesowa — raporty, trendy, panel admina.

> Po ludzku: właściciel dziś nie wie ile zarobił w tym miesiącu bez liczenia w Excelu.
> Po tej fazie ma raport miesięczny jednym kliknięciem.

**Zakres:**
- [ ] Raport miesięczny — przychód, liczba zamówień, top klienci
- [ ] Wykres trendów tygodniowych na dashboardzie
- [ ] Panel admina — zarządzanie użytkownikami i uprawnieniami

**Done when:**
- Raport miesięczny generuje się w < 3s dla 12 miesięcy historii
- Admin może dodać i dezaktywować użytkownika bez ingerencji w kod

**Zależności:** Faza 2
