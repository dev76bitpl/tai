# Testing Rules

Always write Pest tests with `test()`:

```php
test('discovers INE indicators from the configured API',
    /**
     * @throws Exception
     */
    function (): void {
        // ...
    });
```

Use the PHPDoc exception block when the closure may throw, including framework, database, HTTP fake, or `firstOrFail()` paths. Keep the block immediately before the closure so it documents the executable test body.

Use `beforeEach()` for resolved actions, queries, services, or reusable setup objects:

```php
beforeEach(function (): void {
    $this->createWaitlistSignup = resolve(CreateWaitlistSignup::class);
});
```

Apply this even if the current file has one test or the object is only used once. This keeps setup consistent and makes later tests cheaper to add.

## Expectations

Always chain Pest expectations with `->and()` when asserting multiple facts in the same test. Do not create separate expectation blocks unless they assert a separate behavior that should be its own test.

```php
expect($waitlistSignup->id)->toBeString()
    ->and($waitlistSignup->email)->toBe('ana@example.com')
    ->and($waitlistSignup->created_at)->not->toBeNull();
```

Avoid this shape:

```php
expect($waitlistSignup->id)->toBeString();
expect($waitlistSignup->email)->toBe('ana@example.com');
expect($waitlistSignup->created_at)->not->toBeNull();
```

## Asserting Database State

Assert persisted state with a Pest expectation over a query you run
yourself — never `assertDatabaseHas` / `assertDatabaseMissing` /
`assertDatabaseCount`. Query through **Eloquent**; reach for the `DB`
facade only when Eloquent genuinely cannot express it, and only for a
stated reason.

```php
// Good — Eloquent query, asserted with expect()->and()
$signup = WaitlistSignup::sole();

expect($signup->email)->toBe('ana@example.com')
    ->and($signup->confirmed_at)->toBeNull()
    ->and(WaitlistSignup::count())->toBe(1);
```

Avoid the framework database assertions:

```php
// Bad — asserts a raw column array, bypassing the model
$this->assertDatabaseHas('waitlist_signups', ['email' => 'ana@example.com']);
$this->assertDatabaseCount('waitlist_signups', 1);
```

Use the `DB` facade only when no model fits the query — a pivot row with no
Eloquent model, or a column the model doesn't expose — and keep it to that
case:

```php
// Acceptable only here — a pivot table with no model
expect(
    DB::table('role_user')->where(['user_id' => $user->id, 'role_id' => $role->id])->exists()
)->toBeTrue();
```

**Why:** `assertDatabaseHas` matches a raw column array, bypassing the
model — it ignores casts and accessors, doesn't exercise the read path the
app actually uses, and silently drifts when a column the model would catch
is renamed. An Eloquent query asserts the same state *through the model the
application reads*, so the test verifies the real shape and stays
expression-consistent with the rest of the suite. The `DB` facade is the
escape hatch for the genuine no-model case, not a default.

## Test Structure

`tests/Unit` mirrors the `app` folder structure, except `app/Console` and `app/Http` code belongs in feature tests.

- `app/Actions/CreateWaitlistSignup.php` -> `tests/Unit/Actions/CreateWaitlistSignupTest.php`
- `app/Queries/ListStatisticsObservationsQuery.php` -> `tests/Unit/Queries/ListStatisticsObservationsQueryTest.php`
- `app/Data/CreateWaitlistSignupData.php` -> `tests/Unit/Data/CreateWaitlistSignupDataTest.php`
- `app/Models/User.php` -> `tests/Unit/Models/UserTest.php`
- `app/Console/Commands/ImportSomething.php` -> `tests/Feature/ImportSomethingCommandTest.php`
- `app/Http/Controllers/WelcomeController.php` -> `tests/Feature/WelcomeControllerTest.php`

Do not create `tests/Unit/Console` or `tests/Unit/Http` for application Console or Http classes.

## Test Order Within A File

Add a new test at the **top** of the file's tests — immediately after the
`beforeEach` / `afterEach` (and any other setup) hooks — never appended to
the bottom. Tests read newest-first; the setup hooks stay anchored at the
very top.

```php
beforeEach(function (): void {
    $this->createWaitlistSignup = resolve(CreateWaitlistSignup::class);
});

// newest test goes directly under the hooks
test('rejects a duplicate email', /** @throws Throwable */ function (): void {
    // ...
});

test('creates a waitlist signup', /** @throws Throwable */ function (): void {
    // ... older test below
});
```

**Why:** the test you just added is the one you are most likely iterating
on, so placing it directly under the setup keeps it in view without
scrolling a long file. A single consistent insertion point (top, after
hooks) also removes the "where does this go?" decision and keeps the hooks
pinned at the top where setup belongs.

## Test Doubles

Do not use generic mocks for project services. Prefer Laravel fakes for framework concerns such as events, queues, mail, notifications, HTTP, storage, bus, and time.

For project service dependencies, implement in-memory services under `tests/Utils/Services` and bind them in the test setup.

```php
beforeEach(function (): void {
    $this->ineIndicatorDataSource = new InMemoryIneIndicatorDataSource();

    $this->app->instance(IneIndicatorDataSource::class, $this->ineIndicatorDataSource);
});
```

## Helper Functions

Never declare a plain `function` inside a Pest test file. Test files have
no namespace and are all loaded into the global namespace, so a function
declared in a test file is global — and the moment a second test file
declares the same name (or the file is loaded twice), PHP fatals with
`Cannot redeclare function ...`.

```php
// Bad — global function in a test file; collides across files
function makeUser(array $attrs = []): User
{
    return User::factory()->create($attrs);
}

test('...', function (): void {
    $user = makeUser();
});
```

Put shared test logic in the right home instead, in this order:

1. **Reusable setup objects / arrange logic** → `beforeEach()`, assigned to
   `$this` (the default for resolved actions/queries/services above).
2. **A small helper used across many files** → declare it **once** in
   `tests/Pest.php`, which is loaded a single time. This is the only
   sanctioned place for a global test helper function.
3. **Substantial reusable behavior** (builders, fakes, in-memory services)
   → a proper namespaced class under `tests/` (e.g.
   `tests/Utils/Services/*`), not a loose function.

```php
// Good — shared helper declared once in tests/Pest.php
function makeUser(array $attrs = []): User
{
    return User::factory()->create($attrs);
}
```

**Why:** the redeclaration fatal is caused precisely by declaring globals
from a file that is included alongside every other test file. `Pest.php`
is included once, so a helper there is safe; `beforeEach`/`$this` and
namespaced util classes avoid the global namespace entirely. The choice
between them follows reuse: setup → `beforeEach`; tiny shared helper →
`Pest.php`; real behavior → a util class.

## Checklist

- Use `test()`, never `it()`.
- Chain related expectations with `->and()`.
- Assert DB state with a Pest `expect()` over an Eloquent query (`sole()`/`exists()`/`count()`), never `assertDatabaseHas`/`Missing`/`Count`; use the `DB` facade only when no model fits.
- Add an exception PHPDoc directly before Pest closures that may throw.
- Put resolved actions, queries, services, and reusable setup objects in `beforeEach()`.
- Assign setup objects to `$this` even if only one test currently uses them.
- Mirror `app/` structure in `tests/Unit`, excluding Console and Http.
- Add new tests at the top of the file, right after the `beforeEach`/`afterEach` hooks (newest-first).
- Put Console and Http tests under `tests/Feature`.
- Prefer Laravel fakes over mocks.
- Use in-memory services in `tests/Utils/Services` for project service dependencies.
- Never declare a global `function` in a test file — use `beforeEach`/`$this`, a helper in `tests/Pest.php`, or a namespaced `tests/Utils` class.
