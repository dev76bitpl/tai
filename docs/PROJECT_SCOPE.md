# Zakres systemu

Ten plik opisuje **co budujemy, dla kogo i po co**. Wypełnij dla swojego projektu — sekcje są scaffoldem, nie dogmatem (możesz dodać/usunąć).

PROJECT_SCOPE jest source of truth dla logiki biznesowej. Gdy pojawia się konflikt między tym co AI "wie" a tym co tu jest — wygrywa ten plik.

---

## 🎯 Cel systemu

Jedno-dwa zdania: co system robi i dla kogo.

> Przykład: *"System X dla branży Y, rozwiązuje problem Z. Pilotaż: konkretny klient. Docelowo: Y."*

---

## 🧠 Główna koncepcja

Krótko opisz fundamentalne założenie systemu (jedna rzecz, wokół której wszystko się kręci):

- jednostka operacyjna (np. zlecenie, zamówienie, wizyta, sesja)
- kluczowe zdarzenie (np. transakcja, rejestracja, dostarczenie)
- mechanizm identyfikacji / autoryzacji użytkownika

Wskaż core entity wokół których budowany jest system — to pomoże AI utrzymać spójność modelu danych przez kolejne fazy.

---

## 👥 Persony

Lista ról / typów użytkownika z krótkim opisem co robią w systemie:

- **Rola A** — co robi, kiedy, dlaczego
- **Rola B** — j.w.

Persony powinny mieć odzwierciedlenie w autoryzacji (role, permissions). Każda persona = inny use case → inny widok / panel.

---

## 🧩 Moduły

Lista głównych obszarów funkcjonalnych. Trzymaj się core domain — nie wymyślaj modułów "może się przyda".

### Moduł A
- co zawiera
- jakie operacje
- jakie powiązania z innymi modułami

### Moduł B
- j.w.

---

## ⚖️ Priorytety

Podziel moduły na warstwy priorytetowe — to porządkuje fazy ROADMAP:

**CORE** (MVP — bez tego system nie ma sensu):
- moduł 1
- moduł 2

**OPERACYJNE** (niezbędne dla codziennej pracy):
- moduł 3
- moduł 4

**ADMIN** (dla osoby zarządzającej, niski wolumen):
- moduł 5

**INTEGRACJE** (zewnętrzne systemy — odłożone do późniejszej fazy):
- integracja A
- integracja B

---

## 🗄️ Baza danych

Wysokopoziomowe założenia (konkretny wybór technologii → ADR-001):

- model danych: relacyjny / dokumentowy / event-sourced
- vendor lock: tak / nie
- multi-tenancy: jeśli tak — jak izolowane (DB per tenant / schema per tenant / row-level)

Wybór konkretnej bazy uzasadnij w ADR.

---

## 🧠 Architektura

Wysokopoziomowe założenia (konkretny stack → ADR-001):

- styl: API-based / monolith / microservices / event-driven
- separacja warstw: tak / nie (i jak)
- frontend: SPA / SSR / hybrid

Stack technologiczny i konkretne biblioteki uzasadnij w ADR.

---

## 🚫 Zakres wykluczony

Lista funkcjonalności które **świadomie** NIE wchodzą w zakres tego systemu — chroni przed scope creep i pomaga AI sygnalizować gdy ktoś prosi o coś poza scope:

- funkcja 1 (powód: realizowane przez inny system / niepotrzebne)
- funkcja 2

---

## 🧠 Wymagane decyzje (ADR)

Lista głównych decyzji architektonicznych do podjęcia przed lub w trakcie fazy 1:

- ADR-001: kierunek techniczny systemu (stack, architektura)
- ADR-002: ...
- ADR-003: ...

W miarę jak decyzje są podejmowane, dopisuj numer ADR i tytuł.

---

## 🎯 Cel końcowy

Co znaczy "system gotowy do realnego użycia" w fazie 1:

- użytkownik X może...
- użytkownik Y może...
- minimalny zestaw funkcjonalny pokrywa scenariusz biznesowy Z

To NIE jest pełna roadmapa (od tego jest `docs/ROADMAP.md`) — tylko definicja "MVP done".
