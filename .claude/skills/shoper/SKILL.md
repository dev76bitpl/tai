---
name: shoper
description: "Shoper SaaS e-commerce development: Twig templates, ObjectApi, layouts, modules, REST API, webhooks, App Store OAuth2. Invoke when working on Shoper store customization or integration. Actions: shoper, motyw shoper, szablon shoper, shoper api, shoper REST, shoper aplikacja, shoper webhook, shoper twig."
---

# Shoper Development

Przewodnik po customizacji sklepu Shoper — szablony Twig, ObjectApi, REST API i integracje przez App Store.

Źródło: [storefront.developers.shoper.pl](https://storefront.developers.shoper.pl) · [developers.shoper.pl](https://developers.shoper.pl)

## Kiedy używać

Wywołaj gdy:
- Modyfikujesz lub tworzysz motyw Shoper
- Budujesz moduł szablonu (wyświetlanie danych w Twig)
- Integrujesz się przez REST API (produkty, zamówienia, klienci)
- Budujesz aplikację do Shoper App Store (OAuth2 + webhooks)

## Architektura — co można, czego nie można

Shoper to **SaaS** — brak dostępu do serwera i kodu PHP silnika.

| Warstwa | Dostęp | Metoda |
|---------|--------|--------|
| Wygląd / HTML | ✅ pełny | Szablony Twig w panelu admina lub FTP |
| Dane sklepu w szablonie | ✅ tylko odczyt | ObjectApi w Twig |
| Zewnętrzne dane / logika | ✅ | REST API + własny backend |
| Zdarzenia sklepu | ✅ | Webhooks |
| Kod PHP silnika | ❌ | Niedostępny — to SaaS |

## Szablony Twig

### Składnia

```twig
{# Wyświetlenie zmiennej #}
{{ product_id }}

{# Logika / warunek #}
{% if product.name == 'Koszulka' %}
  <p>To jest koszulka!</p>
{% endif %}

{# Pętla #}
{% for product in products %}
  <p>{{ product.name }}</p>
{% endfor %}

{# Przypisanie zmiennej #}
{% set title = 'Mój sklep' %}

{# Filtr #}
{{ product.name | upper }}
{{ product.price | number_format(2, ',', ' ') }}
```

### ObjectApi — pobieranie danych sklepu

ObjectApi to fasada do danych sklepu dostępna w każdym szablonie.

```twig
{# Pobierz produkt po ID (dostępny w kontekście strony produktu) #}
{% set product = ObjectApi.getProduct(product_id) %}
{{ product.name }}
{{ product.price }}
{{ product.description }}

{# Pobierz kategorię #}
{% set category = ObjectApi.getCategory(category_id) %}
{{ category.name }}

{# Pobierz koszyk #}
{% set basket = ObjectApi.getBasket() %}
{{ basket.products_count }}
{{ basket.total_price }}

{# Pobierz dane sklepu #}
{% set shop = ObjectApi.getShop() %}
{{ shop.name }}
{{ shop.email }}
```

**Zasada:** Zmienne kontekstowe (`product_id`, `category_id`) są dostępne tylko w odpowiednich layoutach — `product_id` tylko na stronie produktu, `category_id` tylko na stronie kategorii.

### Konteksty — dostępne zmienne per strona

| Kontekst | Zmienne |
|----------|---------|
| Strona produktu | `product_id` |
| Lista kategorii | `category_id` |
| Wyniki wyszukiwania | `search_query` |
| Koszyk | kontekst basket |
| Strona bloga | `blog_article_id` |
| Strona informacyjna | `info_page_id` |

### Struktura layoutu

Każdy layout składa się z siatki kolumn z modułami.

```twig
<div class="grid">
  <div class="grid__row">
    <div class="grid__col">
      {{ module("header", 1) }}
    </div>
  </div>
  <div class="grid__row">
    <div class="grid__col grid__col--8">
      {{ module("product_gallery", 1) }}
    </div>
    <div class="grid__col grid__col--4">
      {{ module("product_actions", 1) }}
    </div>
  </div>
  <div class="grid__row">
    <div class="grid__col">
      {{ module("footer", 1) }}
    </div>
  </div>
</div>
```

`{{ module("nazwa_modulu", id) }}` — wstawia moduł w danym miejscu layoutu.

### Własny moduł Twig

Moduły to fragmenty szablonu wielokrotnego użytku.

```twig
{# modules/my_banner/template.twig #}
{% set shop = ObjectApi.getShop() %}

<div class="my-banner">
  <h2>{{ module_settings.title }}</h2>
  <p>{{ module_settings.description }}</p>
  <a href="{{ module_settings.link_url }}">
    {{ module_settings.link_label }}
  </a>
</div>
```

`module_settings` — obiekt z ustawieniami modułu konfigurowanymi przez właściciela sklepu w Visual Editorze.

## REST API

Docs: [developers.shoper.pl/developers/api](https://developers.shoper.pl/developers/api/getting-started)

### Autentykacja

```bash
# 1. Pobierz token (Basic Auth)
curl -X POST "https://twojsklep.pl/webapi/rest/auth" \
  -u "login:haslo" \
  -H "Content-Type: application/json"
# → {"access_token": "TOKEN", "token_type": "Bearer", "expires_in": 3600}

# 2. Używaj tokenu w nagłówku
curl "https://twojsklep.pl/webapi/rest/products" \
  -H "Authorization: Bearer TOKEN"
```

### Główne zasoby

```bash
# Produkty
GET    /webapi/rest/products
GET    /webapi/rest/products/{id}
POST   /webapi/rest/products
PUT    /webapi/rest/products/{id}
DELETE /webapi/rest/products/{id}

# Zamówienia
GET    /webapi/rest/orders
GET    /webapi/rest/orders/{id}
PUT    /webapi/rest/orders/{id}          # np. zmiana statusu

# Klienci
GET    /webapi/rest/customers
GET    /webapi/rest/customers/{id}

# Kategorie
GET    /webapi/rest/categories
GET    /webapi/rest/categories/{id}

# Warianty produktu
GET    /webapi/rest/products/{id}/stocks

# Zdjęcia produktu
GET    /webapi/rest/products/{id}/images
POST   /webapi/rest/products/{id}/images
```

### Parametry listowania

```bash
# Paginacja i filtrowanie
GET /webapi/rest/products?page=1&limit=50
GET /webapi/rest/orders?filters[status]=2&filters[date_from]=2025-01-01
GET /webapi/rest/products?filters[stock][operator]=>&filters[stock][value]=0
```

### Bulk — wiele operacji w jednym żądaniu (max 25)

```bash
POST /webapi/rest/bulk
Content-Type: application/json

{
  "requests": [
    { "method": "GET", "url": "/webapi/rest/products/1" },
    { "method": "GET", "url": "/webapi/rest/products/2" },
    { "method": "PUT", "url": "/webapi/rest/orders/100",
      "body": { "status": 3 } }
  ]
}
```

### Uprawnienia OAuth2 (aplikacje App Store)

```
products_read       products_create     products_update     products_delete
orders_read         orders_update
customers_read      customers_create
webhooks_create     webhooks_delete
categories_read
```

## Webhooks

```bash
# Zarejestruj webhook (wymaga uprawnienia webhooks_create)
POST /webapi/rest/webhooks
{
  "event":   "orders/create",
  "callback": "https://twoja-aplikacja.pl/webhook/order-created",
  "secret":  "tajny_klucz"
}
```

Dostępne zdarzenia:

| Zdarzenie | Kiedy |
|-----------|-------|
| `orders/create` | nowe zamówienie |
| `orders/update` | zmiana zamówienia (status, dane) |
| `products/create` | nowy produkt |
| `products/update` | edycja produktu |
| `products/delete` | usunięcie produktu |
| `customers/create` | rejestracja klienta |

```php
// Weryfikacja sygnatury webhooka (HMAC-SHA256)
$payload   = file_get_contents('php://input');
$signature = $_SERVER['HTTP_X_SHOPER_SIGNATURE'] ?? '';
$expected  = hash_hmac('sha256', $payload, 'tajny_klucz');

if (!hash_equals($expected, $signature)) {
    http_response_code(401);
    exit;
}

$data = json_decode($payload, true);
```

## Aplikacja App Store (OAuth2)

```
1. Właściciel sklepu klika "Zainstaluj" w App Store
2. Redirect do: GET /oauth/authorize?client_id=ID&redirect_uri=URL&scope=orders_read products_read
3. Właściciel akceptuje uprawnienia
4. Shoper redirectuje na redirect_uri?code=AUTH_CODE
5. Wymień kod na token:
   POST https://sklep.pl/webapi/rest/auth
   { "grant_type": "authorization_code", "code": AUTH_CODE,
     "client_id": ID, "client_secret": SECRET }
6. Otrzymujesz access_token + refresh_token
```

```php
// PHP — odświeżanie tokenu (pankrok/shoper-appstore-bundle lub własna implementacja)
$response = $http->post("{$shopUrl}/webapi/rest/auth", [
    'grant_type'    => 'refresh_token',
    'refresh_token' => $storedRefreshToken,
    'client_id'     => $clientId,
    'client_secret' => $clientSecret,
]);
$newToken = $response['access_token'];
```

## Checklist integracji API

- [ ] Token przechowywany bezpiecznie (nie w kodzie, nie w repo)
- [ ] Obsługa wygaśnięcia tokenu (kod 401 → odśwież przez refresh_token)
- [ ] Paginacja — nie zakładaj że `limit=50` zwraca wszystko
- [ ] Weryfikacja sygnatury HMAC na każdym webhookowym żądaniu
- [ ] Obsługa błędów API (429 rate limit, 503 maintenance)
- [ ] Idempotentność webhooka — ten sam event może przyjść dwa razy

## Checklist szablonu

- [ ] Zmienne kontekstowe używane tylko w odpowiednim layoucie
- [ ] Dane z ObjectApi sprawdzone przed użyciem (`{% if product %}`)
- [ ] Teksty widoczne dla klienta możliwe do przetłumaczenia (`{{ 'tekst' | translate }}`)
- [ ] Layout używa siatki `grid > grid__row > grid__col`
- [ ] Moduły wstawiane przez `{{ module("nazwa", id) }}`
- [ ] Motyw przetestowany na mobile i desktop

## Zasady

- Cała logika biznesowa (obliczenia, zewnętrzne API) → własny backend, nie w Twig
- Nie przechowuj tokenów OAuth2 w localStorage — tylko backend
- Szablony Twig to wyświetlanie, nie przetwarzanie danych
- Przy każdym wywołaniu REST API sprawdź rate limit (nagłówek `X-RateLimit-Remaining`)
- Zmiany w layoucie testuj w Shoper Visual Editorze przed publikacją
