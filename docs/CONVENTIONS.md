# Conventions

Konwencje kodu obowiązujące w projekcie.

---

## Nazewnictwo

- pliki komponentów: `PascalCase.tsx`
- pliki narzędziowe: `camelCase.ts`
- zmienne i funkcje: `camelCase`
- typy i interfejsy: `PascalCase`
- stałe: `UPPER_SNAKE_CASE`
- tabele DB: `snake_case`

---

## Struktura pliku

```
// imports zewnętrzne
// imports wewnętrzne
// typy
// stałe
// komponent / funkcja
// export
```

---

## Walidacja

- Walidacja na granicach systemu: input użytkownika (formularze, API routes, CLI args, message queues, integracje zewnętrzne)
- Wewnątrz logiki domenowej — dane są już zwalidowane, nie powtarzaj walidacji
- Nigdy nie ufaj danym z requesta po stronie klienta bez weryfikacji po stronie serwera
- Wybór biblioteki walidującej zależy od stacku (Zod dla TS, Pydantic dla Python, itp.)

---

## Error handling

- błędy domenowe zwracane jako `Result<T>` (`{ success: true, data }` | `{ success: false, error }`)
- wyjątki tylko dla sytuacji nieoczekiwanych
- nie łap błędów żeby je zignorować

---

## Testy

- Lokalizacja: testy obok testowanego kodu (np. `*.test.ts` lub `__tests__/`)
- Naming: `should_do_X_when_Y` — nazwa testu mówi co sprawdza bez czytania body
- Każda funkcja domenowa ma testy jednostkowe — piszemy je razem z kodem, nie po fakcie
- Testy integracyjne dla krytycznych flow (happy path + główny error case)
- UI: nie robimy snapshotów/pixel-testów jako standardu; krytyczne flow zabezpieczamy testami integracyjnymi (actions/API), warstwę wizualną domyka manualna checklista regresji
- Kod trywialny (getter, mapowanie 1:1) — bez testu, to tylko szum w suite

---

## Konfiguracja

- Żadnych hardcoded wartości które mogą się różnić między środowiskami
- Zmienne środowiskowe w `.env` (dev) → docelowo zewnętrzny config / baza (prod)
- Stałe aplikacyjne (progi, limity, mapowania enum→tekst, etykiety UI) w dedykowanym pliku config — nie inline w komponencie/module
- Współdzielone stałe sprawdzaj zanim zdefiniujesz nową — nie duplikuj

---

## Komentarze

- domyślnie brak
- komentarz tylko gdy WHY jest nieoczywiste
- nie opisuj CO robi kod — nazwy mówią same za siebie
