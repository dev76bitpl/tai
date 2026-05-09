# UI Guidelines

Standardy UI obowiązujące w projekcie.

---

## Komponenty

- używaj komponentów z design systemu — nie pisz surowego HTML tam gdzie jest gotowy komponent
- `Button`, `Input`, `Select`, `Textarea`, `Label` — zawsze z DS, nigdy `<button>`, `<input>` etc. inline

### Przyciski

| Wariant | Zastosowanie |
|---|---|
| `default` / `primary` | główna akcja na stronie (Zapisz, Dodaj, Wyślij) |
| `outline` / `secondary` | akcje drugorzędne (Edytuj, Anuluj, Archiwizuj) |
| `ghost` / `tertiary` | akcje w nawigacji, mało eksponowane (Wyloguj, link-button) |
| `destructive` / `danger` | nieodwracalne akcje (usunięcie — tylko gdy naprawdę nieodwracalne) |

Rozmiar dobierany do kontekstu: `sm` w tabelach i listach, `default` w formularzach i header'ach.

### Formularze

- Każde pole: `<Label>` + `<Input>` w jednym kontenerze z konsekwentnym odstępem
- Pola w formularzu: jednolity vertical spacing (np. `space-y-4`)
- Przyciski na dole formularza: w `<div>` z gap, primary po lewej lub prawej (konsekwentnie w całej aplikacji)
- Błąd walidacji — inline pod polem (nie `alert()`)
- Błąd serwera — pod całym formularzem, formularz pozostaje wypełniony
- Pola wymagane: etykieta z ` *` (spacja + gwiazdka)
- Pola generowane przez system (np. numer rekordu): pre-wypełnione, edytowalne, bez specjalnego oznaczenia
- Akcje destrukcyjne — dwukrokowy przycisk (stan "potwierdź?" → akcja), nie `confirm()`
- Loading state — przycisk `disabled` + etykieta typu "Zapisywanie..."

### Tabele

- Zawsze komponent `<Table>` z DS, nie surowy `<table>`
- Kolumna akcji: stała szerokość, wyrównana do prawej
- Wartość pusta (brak danych): `—` (em-dash)
- Akcje w wierszu: przyciski `size="sm" variant="outline"` w kontenerze z gap

### Puste stany

```tsx
<p className="text-muted-foreground">Brak [encji]. Dodaj [pierwszą/pierwszego].</p>
```

Lub bardziej rozbudowane: krótki opis + CTA jeśli akcja jest oczywista.

### Stany ładowania

- Przycisk submit: `disabled={loading}` + tekst "Zapisywanie..." / kontekstowa etykieta
- Skeleton loaders / spinner globalny — opcjonalnie zależnie od fazy projektu (patrz "Decyzje MVP")

### Stany błędu (fetch)

```tsx
<div className="p-8 text-destructive">{error}</div>
```

Z opcjonalnym retry. Komunikat user-friendly, bez stack trace.

---

## Kolory i stany

Używamy wyłącznie zmiennych z design systemu (tokens) — żadnych hardkodowanych kolorów (`text-red-500`, `bg-gray-100`, `#fa3e3e`).

| Kategoria tokenów | Zastosowanie |
|---|---|
| `bg-card` / `bg-surface` | tła kart, paneli |
| `text-muted-foreground` | tekst pomocniczy, puste stany |
| `text-destructive` / `text-error` | błędy inline |
| `border` | separatory, ramki tabel |
| sidebar / nav tokens | tła i tekst nawigacji |

Każdy nowy token: zdefiniowany w obu motywach (`:root` + `.dark`) i udostępniony w warstwie design system.

### Motywy (dark/light)

- Aplikacja wspiera oba motywy od dnia 1 (nie dodawać dark trybu post-factum)
- Toggle dostępny w UI (np. w stopce sidebara)
- Domyślny: `light`; opcjonalnie `enableSystem` (motyw systemowy)
- Każdy nowy token koloru: definicja w obu sekcjach (`:root` jasny, `.dark` ciemny)

---

## Statusy

- jeden plik z mapowaniem `status → { label, variant }` dla każdej domeny
- nie duplikować mapowań per-widok
- warianty badge: `success`, `warning`, `error`, `info`, `secondary`

---

## Nawigacja

- breadcrumbs na każdym widoku szczegółowym
- przycisk "Wróć" lub link do listy nadrzędnej

---

## Decyzje MVP (do rewizji w fazie 2+)

Wzorzec: na MVP zostawiamy uproszczenia dla szybkości dostarczenia, ale jawnie odnotowujemy co należy zastąpić w kolejnej fazie. Tabela `Teraz (MVP) | Docelowo` w tym pliku jest źródłem prawdy.

Przykładowe wzorce do typowego MVP (każdy projekt dobiera własny zestaw):

| Teraz (MVP) | Docelowo |
|---|---|
| Błędy inline pod formularzem | Toasty / snackbary dla akcji globalnych |
| Osobne strony `/new` i `/[id]/edit` | Modale / slideover dla szybkiej edycji |
| Brak skeleton loaderów | Skeleton / loading states dla lepszego UX |
| `transition-colors` tylko na hover | Animacje przejść między stronami, micro-interactions |
| Brak potwierdzenia dla archiwizacji | Dialog potwierdzenia dla nieodwracalnych akcji |
