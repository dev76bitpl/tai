# Conventions

Konwencje kodu obowiązujące w projekcie.

> **Scaffold** — dostosuj do swojego stacku. Sekcje "Nazewnictwo" i "Struktura pliku"
> zależą od języka. Reszta (walidacja, error handling, testy, konfiguracja) jest universalna.

---

## Nazewnictwo

Dostosuj do stacku. Przykłady dla popularnych konwencji:

| Co | TypeScript/JS | Python | PHP |
|----|--------------|--------|-----|
| Pliki komponentów | `PascalCase.tsx` | `pascal_case.py` | `PascalCase.php` |
| Pliki narzędziowe | `camelCase.ts` | `snake_case.py` | `snake_case.php` |
| Zmienne i funkcje | `camelCase` | `snake_case` | `camelCase` |
| Klasy i typy | `PascalCase` | `PascalCase` | `PascalCase` |
| Stałe | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| Tabele DB | `snake_case` | `snake_case` | `snake_case` |

---

## Struktura pliku

Kolejność sekcji w pliku (dostosuj składnię komentarzy do języka):

```
imports zewnętrzne / vendor
imports wewnętrzne / lokalne
typy / interfejsy / schematy
stałe
logika / komponent / klasa
export / public API
```

---

## Walidacja

- Walidacja na granicach systemu: input użytkownika (formularze, API routes, CLI args, message queues, integracje zewnętrzne)
- Wewnątrz logiki domenowej — dane są już zwalidowane, nie powtarzaj walidacji
- Nigdy nie ufaj danym z requesta po stronie klienta bez weryfikacji po stronie serwera
- Wybór biblioteki walidującej zależy od stacku (Zod dla TS, Pydantic dla Python, itp.)

---

## Error handling

**Hybrydowy model — universalny wzorzec:**

### Błędy biznesowe → zwracane explicite

Przewidywalne błędy domenowe (np. "zamówienie już istnieje", "brak uprawnień") zwracane jako wartość, nie wyjątek. Wymusza obsługę błędu przez wywołującego.

Przykład w TypeScript:
```typescript
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string; code?: string }
```

Odpowiednik w Python: dataclass lub `tuple[T | None, str | None]`, w Go: `(T, error)`.

### Błędy infrastrukturalne → wyjątki

Nieoczekiwane błędy (DB niedostępna, sieć) — rzucaj wyjątek, łap na granicy systemu i zwracaj generyczny błąd. User nigdy nie widzi stack trace.

- nie łap błędów żeby je zignorować
- loguj przed zwróceniem generycznego błędu

---

## Testy

- Lokalizacja: testy obok testowanego kodu (np. `*.test.ts`, `*_test.go`, `test_*.py`) lub w `__tests__/` / `tests/`
- Naming: `should_do_X_when_Y` — nazwa testu mówi co sprawdza bez czytania body
- Każda funkcja domenowa ma testy jednostkowe — piszemy je razem z kodem, nie po fakcie
- Testy integracyjne dla krytycznych flow (happy path + główny error case)
- Kod trywialny (getter, mapowanie 1:1) — bez testu, to tylko szum w suite

---

## Dostęp do bazy / zewnętrznych serwisów

- Klient DB/serwisu jako singleton eksportowany z jednego miejsca (`lib/`, `infrastructure/`, `services/`) — nigdy nie twórz nowej instancji poza tym miejscem
- W projektach multi-tenant: każde zapytanie filtruje po identyfikatorze tenanta — bez wyjątków dla tabel operacyjnych

---

## Strefy czasowe / daty

- Strefa czasowa pochodzi z konfiguracji (DB lub env) — nie hardkoduj nazwy strefy inline
- Daty przechowuj w UTC; przed wyświetleniem przelicz przez strefę użytkownika / tenanta
- Do konwersji używaj biblioteki — nie ręcznych obliczeń offsetu
- Przy formatowaniu dat zawsze przekazuj strefę czasową explicite — domyślna strefa serwera może być UTC i dawać błędne wyniki

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
