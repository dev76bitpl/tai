---
name: prestashop
description: "PrestaShop module and theme development guide: hooks, overrides, controllers, Webservice API, multistore, BO configuration, Smarty templates, upgrade safety. Invoke when working on PrestaShop project. Actions: prestashop, presta, moduł prestashop, override prestashop, hook prestashop, webservice prestashop, multisklep, smarty prestashop."
---

# PrestaShop Development

Przewodnik po budowaniu modułów, motywów i customizacji PrestaShop 1.7/8.x — bez łamania upgrade'ów i z zachowaniem bezpieczeństwa.

## Kiedy używać

Wywołaj gdy:
- Tworzysz lub modyfikujesz moduł PrestaShop
- Potrzebujesz podpiąć logikę przez hook bez edycji core
- Budujesz lub nadpisujesz szablon Smarty
- Pracujesz z Webservice API (REST)
- Masz do czynienia z multisklepem lub multijęzykowością
- Piszesz migrację danych lub upgrade script

## Architektura modułu

```
my_module/
  my_module.php          # główna klasa modułu — install(), uninstall(), hookXxx()
  config.xml             # cache metadanych (generowany automatycznie)
  logo.png               # 32×32 lub 57×57 px
  controllers/
    front/
      ajax.php           # ModuleFrontController
    admin/
      AdminMyModule.php  # ModuleAdminController
  views/
    templates/
      front/
        my_template.tpl  # Smarty
      hook/
        display_top.tpl
    js/
    css/
  classes/
    MyModel.php          # ObjectModel
  sql/
    install.sql
    uninstall.sql
  translations/          # .xlf (PS 8) lub .php (PS 1.7)
```

## Klasa główna modułu

```php
if (!defined('_PS_VERSION_')) exit;

class My_Module extends Module
{
    public function __construct()
    {
        $this->name        = 'my_module';   // musi być identyczny z nazwą katalogu
        $this->tab         = 'front_office_features';
        $this->version     = '1.0.0';
        $this->author      = 'Twoja firma';
        $this->need_instance = 0;
        $this->ps_versions_compliancy = ['min' => '1.7', 'max' => _PS_VERSION_];
        $this->bootstrap   = true;

        parent::__construct();

        $this->displayName = $this->l('Mój moduł');
        $this->description = $this->l('Opis modułu.');
    }

    public function install(): bool
    {
        return parent::install()
            && $this->registerHook('displayHeader')
            && $this->registerHook('actionCartSave')
            && $this->installDb();
    }

    public function uninstall(): bool
    {
        return parent::uninstall() && $this->uninstallDb();
    }
}
```

## Hooki — gdzie co podpiąć

### Najczęstsze hooki display

| Hook | Gdzie renderuje |
|------|----------------|
| `displayHeader` | `<head>` — enqueue CSS/JS |
| `displayTop` | nad nawigacją |
| `displayNav1` / `displayNav2` | pasek nawigacji |
| `displayHome` | strona główna |
| `displayFooter` | stopka |
| `displayProductAdditionalInfo` | strona produktu — dodatkowe info |
| `displayShoppingCart` | koszyk |
| `displayOrderConfirmation` | potwierdzenie zamówienia |
| `displayAdminProductsExtra` | zakładka w BO — formularz produktu |

### Najczęstsze hooki action

| Hook | Kiedy odpala |
|------|-------------|
| `actionCartSave` | zapisanie koszyka |
| `actionOrderStatusUpdate` | zmiana statusu zamówienia |
| `actionProductAdd` / `actionProductUpdate` | dodanie/edycja produktu |
| `actionCustomerAccountAdd` | rejestracja klienta |
| `actionValidateOrder` | złożenie zamówienia |
| `actionAdminControllerSetMedia` | enqueue w panelu admina |

```php
// Metoda hooka w klasie modułu
public function hookDisplayHeader(): string
{
    $this->context->controller->addCSS($this->_path . 'views/css/front.css');
    $this->context->controller->addJS($this->_path . 'views/js/front.js');
    return '';
}

public function hookActionOrderStatusUpdate(array $params): void
{
    $order     = $params['order'];
    $newStatus = $params['newOrderStatus'];
    // logika
}
```

## Override — nadpisanie klasy core

Override to jedyna akceptowalna metoda modyfikacji zachowania core bez edycji plików PS.

```php
// override/classes/Cart.php
class Cart extends CartCore
{
    public function getOrderTotal(
        bool $with_taxes = true,
        int $type = Cart::BOTH,
        ?array $products = null,
        ?int $id_carrier = null,
        bool $use_cache = true
    ): float {
        $total = parent::getOrderTotal($with_taxes, $type, $products, $id_carrier, $use_cache);
        // twoja modyfikacja
        return $total;
    }
}
```

```php
// override/controllers/front/CartController.php
class CartController extends CartControllerCore
{
    public function initContent(): void
    {
        parent::initContent();
        // dodatkowa logika
    }
}
```

**Po dodaniu override wyczyść cache:**
```bash
php bin/console cache:clear   # PS 8
rm -rf var/cache/*            # PS 1.7
```

**Zasady override:**
- Zawsze wywołuj `parent::method()` chyba że świadomie całkowicie zastępujesz
- Jeden override na klasę — dwa moduły nie mogą nadpisać tej samej klasy
- Nie overriduj jeśli hook wystarczy

## ObjectModel — własna tabela

```php
class MyModel extends ObjectModel
{
    public int $id_shop;
    public string $name;
    public string $content;
    public bool $active;
    public string $date_add;
    public string $date_upd;

    public static $definition = [
        'table'     => 'my_module_items',
        'primary'   => 'id_my_module_item',
        'multilang' => true,          // usuń jeśli nie potrzebujesz tłumaczeń
        'fields'    => [
            'id_shop'  => ['type' => self::TYPE_INT,  'validate' => 'isUnsignedId'],
            'active'   => ['type' => self::TYPE_BOOL, 'validate' => 'isBool'],
            'name'     => ['type' => self::TYPE_STRING, 'validate' => 'isCleanHtml', 'lang' => true, 'required' => true],
            'content'  => ['type' => self::TYPE_HTML,   'validate' => 'isCleanHtml', 'lang' => true],
            'date_add' => ['type' => self::TYPE_DATE,  'validate' => 'isDate'],
            'date_upd' => ['type' => self::TYPE_DATE,  'validate' => 'isDate'],
        ],
    ];
}
```

## Controller front (AJAX / strona modułu)

```php
// controllers/front/ajax.php
class My_ModuleAjaxModuleFrontController extends ModuleFrontController
{
    public bool $ajax = true;

    public function initContent(): void
    {
        parent::initContent();

        if (!$this->isTokenValid()) {
            $this->ajaxRender(json_encode(['error' => 'Invalid token']));
            return;
        }

        $action = Tools::getValue('action');
        // obsłuż akcję
        $this->ajaxRender(json_encode(['success' => true]));
    }
}
```

URL: `/index.php?fc=module&module=my_module&controller=ajax`

## Konfiguracja w BO (formularz ustawień)

```php
public function getContent(): string
{
    $output = '';

    if (Tools::isSubmit('submit_my_module')) {
        $value = Tools::getValue('MY_MODULE_KEY');
        if (!Validate::isCleanHtml($value)) {
            $output .= $this->displayError($this->l('Nieprawidłowa wartość.'));
        } else {
            Configuration::updateValue('MY_MODULE_KEY', $value);
            $output .= $this->displayConfirmation($this->l('Zapisano.'));
        }
    }

    return $output . $this->renderForm();
}

private function renderForm(): string
{
    $helper = new HelperForm();
    $helper->submit_action = 'submit_my_module';
    $helper->token = Tools::getAdminTokenLite('AdminModules');

    $fields_form = [[
        'form' => [
            'legend' => ['title' => $this->l('Ustawienia')],
            'input'  => [
                [
                    'type'  => 'text',
                    'label' => $this->l('Wartość'),
                    'name'  => 'MY_MODULE_KEY',
                ],
            ],
            'submit' => ['title' => $this->l('Zapisz')],
        ],
    ]];

    $helper->fields_value['MY_MODULE_KEY'] = Configuration::get('MY_MODULE_KEY');
    return $helper->generateForm($fields_form);
}
```

## Webservice API

```php
// Dodaj uprawnienia w install()
public function install(): bool
{
    return parent::install()
        && $this->addWebserviceResources();
}

private function addWebserviceResources(): bool
{
    $resources = [
        'my_items' => [
            'description' => 'My module items',
            'class'       => 'WebserviceRequestMyItems',
        ],
    ];
    // Zarejestruj przez hookActionWebserviceResources
    return true;
}
```

```bash
# Testowanie API
curl -u API_KEY: "https://sklep.pl/api/products?output_format=JSON&limit=5"
curl -u API_KEY: "https://sklep.pl/api/orders/123?output_format=JSON"
```

## Smarty — szablony

```smarty
{* views/templates/hook/display_top.tpl *}
{extends file='customer/page.tpl'}

{block name='page_content'}
  <div class="my-module-block">
    <h2>{$my_title|escape:'html':'UTF-8'}</h2>
    {foreach $items as $item}
      <p>{$item.name|escape:'html':'UTF-8'}</p>
    {/foreach}
  </div>
{/block}
```

```php
// Przekaż zmienne do szablonu z hooka
public function hookDisplayHome(): string
{
    $this->context->smarty->assign([
        'my_title' => Configuration::get('MY_MODULE_TITLE'),
        'items'    => MyModel::getActiveItems(),
    ]);
    return $this->display(__FILE__, 'views/templates/hook/display_home.tpl');
}
```

**Zawsze escape'uj zmienne w Smarty:** `{$var|escape:'html':'UTF-8'}`

## Multistore i multijęzykowość

```php
// Pobierz wartość dla aktualnego sklepu
$value = Configuration::get('MY_KEY', null, null, $this->context->shop->id);

// Zapisz dla konkretnego sklepu
Configuration::updateValue('MY_KEY', $value, false, null, $id_shop);

// Pobierz tłumaczenie
$name = $this->l('Tekst do przetłumaczenia');

// ObjectModel z multilang — pobierz we wszystkich językach
$item = new MyModel($id, $id_lang, $id_shop);
```

## Bezpieczeństwo

```php
// Walidacja danych wejściowych
$id    = (int) Tools::getValue('id_product');       // zawsze rzutuj int
$text  = Tools::getValue('my_text');
if (!Validate::isCleanHtml($text)) {
    throw new PrestaShopException('Invalid input');
}

// Token CSRF w formularzach front
$token = Tools::getToken(false);
// weryfikacja
if (!Tools::isSubmit('token') || Tools::getValue('token') !== $token) {
    Tools::redirect('index.php');
}

// Zapytania do bazy
$result = Db::getInstance()->executeS(
    'SELECT * FROM `' . _DB_PREFIX_ . 'product` WHERE `id_product` = ' . (int) $id_product
);
// lub przez ObjectModel->getFields() — nie buduj zapytań przez string interpolation z user input
```

## wp-cli odpowiednik — PS console (PS 8)

```bash
# Wyczyść cache
php bin/console cache:clear --env=prod

# Lista modułów
php bin/console prestashop:module list

# Zainstaluj/odinstaluj moduł
php bin/console prestashop:module install my_module
php bin/console prestashop:module uninstall my_module

# Generuj sitemap
php bin/console prestashop:generate:sitemap

# Eksport tłumaczeń
php bin/console prestashop:translation:export --locale=pl-PL
```

## Checklist przed wdrożeniem

- [ ] `define('_PS_MODE_DEV_', false)` w config/defines.inc.php produkcyjnym
- [ ] Wszystkie dane wejściowe przez `Validate::isXxx()` lub rzutowanie
- [ ] Zapytania SQL przez `(int)` / `pSQL()` — bez string interpolation z user input
- [ ] Token CSRF na formularzach front
- [ ] `parent::install()` wywołane w `install()`
- [ ] `uninstall()` czyści konfigurację i tabele (`Configuration::deleteByName()`)
- [ ] Override wywoływane przez `parent::method()`
- [ ] Cache wyczyszczony po dodaniu override
- [ ] Moduł przetestowany na PS 1.7 i 8.x jeśli ma być kompatybilny z oboma
- [ ] Tłumaczenia w `.xlf` (PS 8) lub `.php` (PS 1.7)

## Zasady

- Nigdy nie edytuj plików core PS — zawsze hook albo override
- Prefiks `_DB_PREFIX_` w każdym zapytaniu SQL
- Nazwy klas i katalogu modułu identyczne (case-sensitive na Linuksie)
- Jeden moduł = jeden katalog = jedna klasa główna
- Konfigurację modułu trzymaj w `ps_configuration` przez `Configuration::get/updateValue`
- Testuj z włączonym `_PS_MODE_DEV_` i sprawdź logi w `var/logs/`
