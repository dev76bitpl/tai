---
name: a11y
description: "Accessibility audit and implementation. Invoke when building or reviewing UI for accessibility compliance (WCAG 2.2 AA), fixing keyboard navigation, screen reader support, color contrast, or ARIA patterns. Actions: accessibility, dostępność, a11y, WCAG, kontrast, czytnik ekranu, klawiatura, aria, focus, screen reader."
---

# Dostępność — WCAG 2.2 AA

Wytyczne dostępności oparte na [fecarrico/A11Y.md](https://github.com/fecarrico/A11Y.md) — certyfikacja WCAG 2.2 AA, ISO 9241-171, ADA.

Pełne wytyczne: przeczytaj `A11Y.md` w tym katalogu.
Szczegóły per komponent: katalog `references/`.

## Zasada nadrzędna

Dostępność to **warunek wstępny działania**, nie dodatek. Jeśli użytkownik nie może wykonać zadania przez barierę dostępności — funkcjonalność jest **technicznie zepsuta**.

## Poziomy ważności

| Poziom | Opis | Wymaganie |
|--------|------|-----------|
| 🔴 CRITICAL | Blokuje Task Completion (np. brak nawigacji klawiaturą) | MUST FIX |
| 🟠 HIGH | Znacząco zwiększa Error Rate (np. za niski kontrast) | MUST FIX |
| 🟡 MEDIUM | Obniża efektywność (np. brak skrótów klawiaturowych) | SHOULD FIX |
| 🔵 LOW | Kosmetyczny (np. brak aria-label na dekoracji) | MAY FIX |

## Kluczowe zasady techniczne (POUR)

### Perceivable (Postrzegalny)
- Kontrast tekstu: min **4.5:1**, elementy UI: min **3:1**
- Obrazy znaczące: `alt` opisujący treść; dekoracyjne: `alt=""`
- Wideo: napisy, transkrypcja

### Operable (Obsługiwalny)
- Wszystkie interakcje dostępne z klawiatury (Tab, Enter, Space, Esc, strzałki)
- Widoczny focus ring na każdym interaktywnym elemencie
- Modalne: focus trap wewnątrz, Esc zamyka, focus wraca po zamknięciu
- Skip link "Przejdź do treści" jako pierwszy element strony

### Understandable (Zrozumiały)
- `<html lang="pl">` (lub odpowiedni język)
- Widoczne etykiety formularzy (`<label for="">`, nie tylko placeholder)
- Błędy walidacji: konkretny opis + jak naprawić, `role="alert"` lub `aria-live`

### Robust (Niezawodny)
- Semantyczny HTML: `<button>` dla akcji, `<a>` dla nawigacji, nigdy `<div onClick>`
- ARIA tylko gdy natywny HTML nie wystarczy — preferuj natywne elementy
- Nagłówki: kolejność h1→h6 bez pomijania poziomów

## Protokół audytu

1. **Automatyczny skan** → narzędzie axe-core / Lighthouse Accessibility
2. **Test klawiaturą** → przejdź całą stronę tylko Tab/Shift+Tab/Enter/Esc
3. **Test czytnikiem** → VoiceOver (Mac/iOS) lub NVDA/JAWS (Windows)
4. **Kontrast** → sprawdź narzędziem (np. WebAIM Contrast Checker)

## Szczegółowe wytyczne per komponent

- Przyciski → `references/examples-buttons.md`
- Formularze → `references/examples-forms.md`
- Modalne → `references/examples-modals.md`
- Nawigacja → `references/examples-navigation.md`
- Obrazy → `references/examples-images.md`
- Treść dynamiczna → `references/examples-content-interaction.md`

## Przed dodaniem `onClick` do non-semantycznego elementu

Zanim dodasz `onClick` do `<div>` lub `<span>` — zaproponuj zastąpienie natywnym elementem lub pełnym wzorcem ARIA. To CRITICAL issue jeśli brak keyboard support.
