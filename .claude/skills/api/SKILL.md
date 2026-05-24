---
name: api
description: "API design review and contract definition. Invoke before implementing a new API endpoint, reviewing existing API design, or designing REST/GraphQL contracts. Actions: API, endpoint, REST, kontrakt API, zaprojektuj API, nowy endpoint, API design, API review."
---

# Design API

Protokół projektowania i review kontraktów API przed implementacją.

## Kiedy używać

Wywołaj gdy:
- Projektujesz nowy endpoint zanim go zakodysz
- Robisz review istniejącego API
- Zmieniasz kontrakt (dodajesz pola, zmieniasz typy, usuwasz)
- Projektujesz API które będzie konsumowane przez zewnętrznych klientów

## Pytania przed projektowaniem

Odpowiedz na te pytania zanim zaczniesz projektować:

```
1. Kto konsumuje to API?
   (własny frontend, zewnętrzni developerzy, inne serwisy)

2. Jaka jest główna akcja / zasób?
   (np. "zarządzanie zamówieniami", "autentykacja użytkownika")

3. Czy to CRUD czy operacja domenowa?
   CRUD → zasoby RESTowe
   Operacja → action endpoint (POST /orders/{id}/cancel)

4. Jakie są wymagania dotyczące autoryzacji?
   (publiczne, authenticated, role-based, owner-only)

5. Czy API musi być wersjonowane?
   (zewnętrzni klienci = tak; własny frontend = opcjonalnie)
```

## Checklist projektu

### Nazewnictwo i struktura
- [ ] Zasoby w liczbie mnogiej: `/users`, `/orders`, `/products`
- [ ] Hierarchia zasobów odzwierciedla relacje: `/users/{id}/orders`
- [ ] Akcje domenowe jako POST z czasownikiem: `POST /orders/{id}/cancel`
- [ ] Nie mieszaj czasowników w ścieżce RESTowej: nie `GET /getUser`

### Metody HTTP
- [ ] `GET` — pobieranie, idempotentne, bez efektów ubocznych
- [ ] `POST` — tworzenie lub akcja domenowa
- [ ] `PUT` — pełna aktualizacja zasobu (zastąpienie)
- [ ] `PATCH` — częściowa aktualizacja
- [ ] `DELETE` — usuwanie, idempotentne

### Kody odpowiedzi
- [ ] `200` OK — sukces z body
- [ ] `201` Created — zasób stworzony, `Location` header w odpowiedzi
- [ ] `204` No Content — sukces bez body (np. DELETE)
- [ ] `400` Bad Request — błąd walidacji z opisem co jest nie tak
- [ ] `401` Unauthorized — brak autentykacji
- [ ] `403` Forbidden — brak autoryzacji (znamy użytkownika, ale nie ma dostępu)
- [ ] `404` Not Found — zasób nie istnieje
- [ ] `409` Conflict — konflikt stanu (np. duplikat)
- [ ] `422` Unprocessable Entity — poprawna składnia, błąd biznesowy
- [ ] `500` Internal Server Error — nie ujawniaj szczegółów implementacji

### Błędy
- [ ] Spójny format błędów w całym API:
  ```json
  {
    "error": "validation_failed",
    "message": "Pole email jest wymagane",
    "field": "email"
  }
  ```
- [ ] Błędy walidacji wymieniają **wszystkie** błędy naraz, nie tylko pierwszy

### Bezpieczeństwo
- [ ] Autoryzacja sprawdzana per request, nie tylko na poziomie routingu
- [ ] Własność zasobu weryfikowana (`user_id == current_user.id`)
- [ ] Brak wrażliwych danych w URL (tokeny, hasła)
- [ ] Rate limiting dla endpointów publicznych i autentykacyjnych
- [ ] Input walidowany i sanityzowany przed użyciem

### Paginacja (dla list)
- [ ] Wszystkie listy paginowane — nigdy `GET /orders` bez limitu
- [ ] Cursor-based lub offset-based (cursor lepszy dla dużych zbiorów)
- [ ] Odpowiedź zawiera: `data`, `total` (opcjonalnie), `next_cursor` lub `page`

### Wersjonowanie
- [ ] Wersja w URL jeśli API zewnętrzne: `/api/v1/`
- [ ] Backward-compatible zmiany nie wymagają nowej wersji
- [ ] Breaking changes = nowa wersja + stara utrzymana przez min. 6 miesięcy

## Format dokumentacji endpointu

Przed implementacją zdefiniuj kontrakt:

```
### POST /orders/{id}/cancel

**Opis:** Anuluje zamówienie. Możliwe tylko gdy status = 'pending' lub 'confirmed'.

**Auth:** Bearer token, wymagana rola owner lub admin

**Request:**
- Path: id (UUID, wymagane)
- Body: { "reason": "string (opcjonalne, max 500 znaków)" }

**Response 200:**
{ "id": "uuid", "status": "cancelled", "cancelled_at": "ISO8601" }

**Błędy:**
- 404: zamówienie nie istnieje
- 403: brak dostępu
- 409: zamówienie nie może być anulowane w tym stanie (np. już wysłane)
```

## Zasady

- Projektuj kontrakt zanim zaczniesz kodować — zmiana API po implementacji kosztuje więcej
- Nie ujawniaj struktury bazy danych w API — to szczegół implementacyjny
- Backward-compatible = dodawanie pól jest OK; usuwanie lub zmiana typów = breaking change
- Dokumentuj edge case'y i stany błędów — to są najważniejsze części kontraktu
