# UI Guidelines

Standardy UI obowiązujące w projekcie.

> **Scaffold** — zasady UX są universalne. Implementacja (nazwy komponentów, klasy CSS,
> tokeny) zależy od stacku. Dostosuj sekcje implementacyjne do swojego design systemu.

---

## Zasada podstawowa

Używaj komponentów z design systemu projektu — nie pisz surowego HTML tam gdzie jest gotowy komponent. Spójność wizualna pochodzi z jednego źródła, nie z lokalnych decyzji per-widok.

---

## Przyciski

Każdy projekt definiuje warianty przycisku odpowiadające hierarchii akcji:

| Wariant | Zastosowanie |
|---|---|
| Primary | główna akcja na stronie (Zapisz, Dodaj, Wyślij) |
| Secondary / Outline | akcje drugorzędne (Edytuj, Anuluj, Archiwizuj) |
| Ghost / Tertiary | akcje w nawigacji, mało eksponowane |
| Destructive / Danger | nieodwracalne akcje (usunięcie — tylko gdy naprawdę nieodwracalne) |

Rozmiar dobierany do kontekstu: mniejszy w tabelach i listach, standardowy w formularzach i nagłówkach.

---

## Formularze

### Struktura pola

Każde pole formularza: etykieta + input w jednym kontenerze z konsekwentnym odstępem. Pola wymagane oznaczone (np. ` *` przy etykiecie).

### Obsługa błędów

- Błąd walidacji — inline pod polem, nie alert()
- Błąd serwera — pod całym formularzem, formularz pozostaje wypełniony
- Pola generowane przez system: pre-wypełnione i edytowalne, bez specjalnego oznaczenia

### Loading state

Przycisk submit: zablokowany + kontekstowa etykieta ("Zapisywanie...") podczas żądania.

### Akcje destrukcyjne

Dwukrokowy przycisk zamiast `confirm()`: pierwsze kliknięcie = stan "potwierdź?", drugie = akcja.

---

## Tabele

- Kolumna akcji: stała szerokość, wyrównana do prawej
- Wartość pusta (brak danych): `—` (em-dash), nie puste miejsce
- Akcje w wierszu: małe przyciski z jednolitym odstępem

---

## Stany komponentów

### Pusty stan

Krótki komunikat wyjaśniający brak danych + CTA jeśli akcja jest oczywista.

Przykład: *"Brak zamówień. Dodaj pierwsze zamówienie."*

### Stan ładowania

- Przycisk submit: zablokowany + kontekstowa etykieta
- Skeleton loaders / spinner globalny — opcjonalnie zależnie od fazy projektu

### Stan błędu (fetch)

Komunikat user-friendly bez stack trace, z opcjonalnym retry. Widoczny w obszarze gdzie dane miały się pojawić.

---

## Kolory i tokeny

Używaj wyłącznie zmiennych z design systemu — żadnych hardkodowanych wartości kolorów (`#fa3e3e`, nazwy kolorów bezpośrednio z biblioteki CSS). Każdy nowy token: zdefiniowany dla wszystkich obsługiwanych motywów.

Kategorie tokenów do zdefiniowania per projekt:
- tła kart i paneli
- tekst pomocniczy / placeholder
- błędy inline
- separatory i ramki
- kolory nawigacji

---

## Motywy (dark/light)

Jeśli projekt wspiera wiele motywów — definiuj od dnia 1, nie dodawaj post-factum. Każdy nowy token koloru definiowany w obu motywach jednocześnie.

---

## Statusy

- jeden plik z mapowaniem `status → { label, wariant }` dla każdej domeny
- nie duplikować mapowań per-widok (kalendarz, tabela, modal — wszystkie z tego samego źródła)
- warianty badge dobrane do design systemu: success, warning, error, info, neutral

---

## UX flow — formularz

1. User otwiera formularz
2. Pola generowane przez system są pre-wypełnione
3. Walidacja klienta blokuje submit przy błędach lokalnych
4. Po submit — loading state na przycisku
5. Błąd serwera — wyświetlony pod formularzem, formularz pozostaje wypełniony
6. Sukces — redirect na listę lub widok szczegółowy

---

## Nawigacja

- breadcrumbs na każdym widoku szczegółowym
- przycisk "Wróć" lub link do listy nadrzędnej

---

## Decyzje MVP (do rewizji w fazie 2+)

Wzorzec: na MVP zostawiamy uproszczenia dla szybkości dostarczenia, ale jawnie odnotowujemy co należy zastąpić. Poniżej przykładowe kompromisy — każdy projekt definiuje własne.

| Teraz (MVP) | Docelowo |
|---|---|
| Błędy inline pod formularzem | Toasty / snackbary dla akcji globalnych |
| Osobne strony `/new` i `/edit` | Modale / slideover dla szybkiej edycji |
| Brak skeleton loaderów | Skeleton / loading states dla lepszego UX |
| Brak potwierdzenia dla archiwizacji | Dialog potwierdzenia dla nieodwracalnych akcji |
