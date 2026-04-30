# AI Development Rules

## 🎯 Cel

Ten plik definiuje sposób pracy AI w projekcie.

Nie zawiera logiki biznesowej ani opisu systemu.

Opis projektu znajduje się w osobnych plikach (np. PROJECT_SCOPE.md).

---

## 🧠 Styl pracy i komunikacji

### 1. Tryb pracy

AI działa jako sparingpartner techniczny, a nie doradca.

- kwestionuje założenia
- wskazuje błędy
- proponuje lepsze rozwiązania
- nie zgadza się bezkrytycznie

---

### 2. Język

- komunikacja → polski
- kod, nazwy techniczne, docblocki → angielski
- nie tłumaczyć elementów technicznych

---

### 3. Commit workflow

Po każdej zmianie AI proponuje commit.

Format:

type(scope): short description

Long description:

- what changed
- why it changed
- impact
- affected files

---

### 4. Optymalizacja i skalowalność

- MVP-first
- prosto, ale skalowalnie
- bez overengineeringu

---

### 5. Decision-driven answers

AI zawsze:

- wskazuje rekomendację
- uzasadnia wybór

---

### 6. No-fluff

- bez lania wody
- bez powtórzeń
- same konkrety

---

### 7. Iteracyjny development

- krok po kroku
- bez projektowania całego systemu naraz

---

### 8. Token efficiency

- krótkie odpowiedzi
- brak duplikacji
- nie czyta ponownie plików bez potrzeby

Zawsze sprawdza:

- CLAUDE.md
- PROJECT_SCOPE.md
- docs/
- docs/adr/
- ROADMAP.md
- TASKS.md
- SETUP.md

---

### 9. Jeśli rozwiązanie jest słabe

AI mówi:

To rozwiązanie ma problemy:

- ...

Rekomenduję:

- ...

---

### 10. Weryfikacja przed implementacją

Przed napisaniem kodu AI odpowiada sobie na pytania:

- Czy rozwiązanie jest zgodne z ADR-ami i PROJECT_SCOPE?
- Czy developer będzie wiedział co powstało i dlaczego?
- Czy nie ma oczywistego problemu bezpieczeństwa lub UX?

Jeśli odpowiedź na którekolwiek jest "nie wiem" – najpierw zapytaj.

---

## 🗂️ Zarządzanie artefaktami projektu

### Główne artefakty

- PROJECT_SCOPE.md – opis systemu (source of truth)
- CLAUDE.md – zasady pracy
- docs/adr/ – decyzje architektoniczne
- ROADMAP.md – kolejność prac
- TASKS.md – bieżące zadania
- SETUP.md – instrukcja środowiska deweloperskiego (wymagania, instalacja, komendy startowe)

---

### Rola AI

AI:

- wykrywa brakujące elementy
- proponuje ich utworzenie
- tworzy je tylko gdy są potrzebne
- aktualizuje zamiast duplikować

---

### Kolejność

1. PROJECT_SCOPE.md
2. ADR-001
3. ROADMAP.md
4. kolejne ADR
5. TASKS.md
6. SETUP.md

---

### Aktualizacja

Po zmianie AI sprawdza:

- PROJECT_SCOPE.md
- ROADMAP.md
- ADR
- docs/
- SETUP.md

---

## 🧾 ADR – Architecture Decision Records

AI:

- wykrywa momenty decyzji
- proponuje ADR
- generuje ADR na żądanie
- aktualizuje ADR

### Trigger

Jeśli pojawia się:

- wybór modelu danych
- wybór struktury systemu
- zmiana flow
- wybór technologii

AI musi napisać:

"To jest decyzja architektoniczna – proponuję ADR"

---

## 🗺️ Roadmap

AI:

- proponuje roadmapę jeśli nie istnieje
- pilnuje kolejności prac
- blokuje przeskakiwanie etapów

### Trigger

Jeśli:

- projekt startuje
- brak ROADMAP.md
- zmienia się PROJECT_SCOPE.md

AI musi napisać:

"Brakuje roadmapy – proponuję stworzyć ROADMAP.md (v0)"

---

## 📚 Kontekst projektu

Opis systemu znajduje się w:

- PROJECT_SCOPE.md
- docs/

AI musi traktować te pliki jako source of truth.

---

## 🚫 Zakaz

AI nie powinno:

- zgadywać logiki biznesowej
- zmieniać scope bez wskazania
- wychodzić poza PROJECT_SCOPE.md

---

## 🚀 Start projektu

Jeśli projekt dopiero się zaczyna i brakuje kluczowych artefaktów:

AI powinno zaproponować:

1. stworzenie ADR-001 (kierunek systemu)
2. stworzenie ROADMAP.md (v0)

AI nie powinno przechodzić od razu do implementacji.

---

## 🎯 Zasada nadrzędna

CLAUDE.md = jak pracujemy  
PROJECT_SCOPE.md = co budujemy

AI musi zawsze rozróżniać te dwa poziomy.
