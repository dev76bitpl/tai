# UI Guidelines

Standardy UI obowiązujące w projekcie.

---

## Komponenty

- używaj komponentów z design systemu — nie pisz surowego HTML tam gdzie jest gotowy komponent
- `Button`, `Input`, `Select`, `Textarea`, `Label` — zawsze z DS, nigdy `<button>`, `<input>` etc. inline

---

## Formularze

- błędy walidacji — inline pod polem, nie `alert()`
- akcje destrukcyjne — dwukrokowy przycisk (stan "potwierdź?" → akcja), nie `confirm()`
- loading state — przycisk `disabled` + etykieta "Zapisywanie..."

---

## Stany ekranu

Każdy widok obsługuje:
- `loading` — skeleton lub spinner
- `empty` — komunikat + CTA
- `error` — komunikat + retry
- `data` — właściwa treść

---

## Statusy

- jeden plik z mapowaniem `status → { label, variant }` dla każdej domeny
- nie duplikować mapowań per-widok
- warianty badge: `success`, `warning`, `error`, `info`, `secondary`

---

## Nawigacja

- breadcrumbs na każdym widoku szczegółowym
- przycisk "Wróć" lub link do listy nadrzędnej
