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

## Error handling

- błędy domenowe zwracane jako `Result<T>` (`{ success: true, data }` | `{ success: false, error }`)
- wyjątki tylko dla sytuacji nieoczekiwanych
- nie łap błędów żeby je zignorować

---

## Komentarze

- domyślnie brak
- komentarz tylko gdy WHY jest nieoczywiste
- nie opisuj CO robi kod — nazwy mówią same za siebie
