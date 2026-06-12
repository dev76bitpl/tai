# Architecture tests (enforcement)

Codebase-wide invariants that a machine can check are enforced by **Pest
architecture tests**, not left to review. This is the discipline layer that turns
the skill's mandatory, statically-checkable rules into executable guards. Sibling
to [conventions.md](conventions.md) (which owns `test()`-based unit/feature
tests); arch tests are a distinct kind and live apart. Verify Pest arch API
against the Pest docs before use.

## Rule: enforce mandatory, statically-checkable, load-bearing invariants with `arch()`

A rule earns an architecture test when **all three** hold:

1. **Mandatory / codebase-wide** — a settled policy, not a per-case choice.
2. **Statically checkable** — expressible over class / namespace / name /
   reflection (final, suffix, extends, has-method, readonly, uses / not-uses),
   without running the code.
3. **Load-bearing** — silent drift would actually hurt (a leaked column, a
   mutable payload), so a green test pays for itself.

```php
arch('every data object declares its properties readonly')
    ->expect('App\Data')
    ->toHaveReadonlyProperties();
```

**Why:** a rule stated only in prose drifts the first time someone forgets it, and
review catches it only sometimes. An arch test fails the build the moment the rule
breaks — the rule stops being advisory and becomes enforced. A rule that fails any
of the three conditions stays prose + review (see the catalog's last section).

## Rule: prefer a custom arch expectation over an imperative reflection loop

When no built-in expectation fits, **extend arch** — do not drop to a hand-rolled
`test()` that globs files and reflects them. Register a custom expectation with
`expect()->extend()` on top of `Pest\Arch\Expectations\Targeted::make()` (the same
primitive the built-ins use), in `tests/Pest.php`.

```php
// tests/Pest.php — a per-property readonly expectation (toBeReadonly is CLASS-level)
expect()->extend('toHaveReadonlyProperties', function (): Pest\Arch\Contracts\ArchExpectation {
    return Pest\Arch\Expectations\Targeted::make(
        $this,
        function (Pest\Arch\Objects\ObjectDescription $object): bool {
            if (! isset($object->reflectionClass)) {
                return true;
            }

            foreach ($object->reflectionClass->getProperties(ReflectionProperty::IS_PUBLIC) as $property) {
                // only the class's OWN properties — ignore inherited Spatie Data internals
                if ($property->getDeclaringClass()->getName() === $object->name && ! $property->isReadOnly()) {
                    return false;
                }
            }

            return true;
        },
        'to have readonly properties',
        Pest\Arch\Support\FileLineFinder::where(fn (string $line): bool => str_contains($line, 'class')),
    );
});
```

```php
// Bad — an imperative reflection loop masquerading as an arch rule
test('data objects are readonly', function (): void {
    foreach (glob(app_path('Data/*.php')) as $file) {
        // ...reflect each class, assert isReadOnly()... — duplicates target discovery,
        // sits outside the arch API, reads as procedural test code
    }
});
```

**Why:** the custom expectation keeps the rule in the `arch()` vocabulary — it
composes with `->ignoring()`, reports at the offending line, and reads as an
architectural rule. The imperative loop re-implements target discovery and reads
as procedural code. Filter on `getDeclaringClass()->getName() === $object->name`
so an inherited third-party property (a non-readonly base like
`Spatie\LaravelData\Data`) is not falsely flagged.

## Rule: a guard is not trusted until it has been seen to fail

Before relying on an arch test — or any guard — **make it go red** on a real
violation, then restore. A green arch test you have never seen fail may be
vacuous: wrong namespace, an always-true callback, or a target that matched
nothing.

**Why:** the failure mode of a guard is *silent uselessness*. Removing `readonly`
from one property and watching the test fail
(`Expecting 'app/Data/UpdateTeamData.php' to have readonly properties.`) is the
only proof the guard actually guards.

## Placement

- **Arch tests** live in `tests/Arch`, wired as their own `phpunit.xml` testsuite.
  They are neither unit nor feature tests and do **not** mirror `app/`
  ([conventions.md](conventions.md)).
- **Custom arch expectations** are registered once in `tests/Pest.php` — the same
  single-load file that holds global test helpers
  ([conventions.md](conventions.md)) — so the extension is defined exactly once.

## The catalog — what is enforced, and how

The single source of truth for which of this skill's rules are arch-enforced. Each
rule's *definition* lives in its own home (linked); this catalog records the
*enforcement*.

### Built-in expectations

| Rule (home) | Expectation |
|---|---|
| Classes are `final` ([../architecture/classes.md](../architecture/classes.md)) | `expect('App')->toBeFinal()` (ignoring `abstract` bases) |
| `declare(strict_types=1)` ([../architecture/classes.md](../architecture/classes.md)) | `expect('App')->toUseStrictTypes()` |
| `Query` suffix ([../naming/conventions.md](../naming/conventions.md)) | `expect('App\Queries')->toHaveSuffix('Query')` |
| `Service` suffix ([../naming/conventions.md](../naming/conventions.md)) | `expect('App\Services')->toHaveSuffix('Service')` |
| Data objects extend Spatie `Data` ([../data-objects/conventions.md](../data-objects/conventions.md)) | `expect('App\Data')->toExtend(Spatie\LaravelData\Data::class)` |
| Actions expose `handle()` ([../actions/conventions.md](../actions/conventions.md)) | `expect('App\Actions')->toHaveMethod('handle')` |
| Jobs dispatched only from actions ([../architecture/transactions.md](../architecture/transactions.md)) | `expect('App\Jobs')->toOnlyBeUsedIn('App\Actions')` — only actions may *reference* a job class, which catches `::dispatch()`, `new`, and `dispatch(...)` alike |
| No model soft-deletes ([../models/conventions.md](../models/conventions.md)) | `expect('App\Models')->not->toUse(Illuminate\Database\Eloquent\SoftDeletes::class)` |
| Inject over facades ([../architecture/dependency-injection.md](../architecture/dependency-injection.md)) | `expect('App')->not->toUse('Illuminate\Support\Facades')` (with the sanctioned few `->ignoring()`d) |

Dependency-direction expectations (`toOnlyBeUsedIn`, `not->toUse`) are the lever
for any **layering** rule — "layer X is reached only from layer Y". Whenever a
rule is about *who may reference whom* (jobs only from actions, a namespace kept
out of another), reach for them before considering a custom expectation.

### Custom expectations (no built-in fits)

| Rule (home) | Why custom |
|---|---|
| Readonly Data **properties** ([../data-objects/conventions.md](../data-objects/conventions.md)) | `toBeReadonly()` is class-level; a Data object can't be a `readonly class` (it extends a non-readonly base) → per-property `toHaveReadonlyProperties` (above) |
| No Eloquent models in Data fields ([../data-objects/conventions.md](../data-objects/conventions.md)) | inspect constructor parameter types for `Model` subclasses |
| No model query scopes ([../models/conventions.md](../models/conventions.md)) | detect `scope*` methods declared on the model |
| Enums are backed, never pure ([../enums/conventions.md](../enums/conventions.md)) | no generic built-in (`toBeStringBackedEnums` is now too narrow — int is an allowed measured exception) → assert `(new ReflectionEnum($name))->isBacked()`; string-vs-int is a documented decision, not arch-enforced |

### Not arch-suited — enforce by another tool

Arch sees **structure and references** (shape, names, namespaces, who-references-whom)
— not **runtime config**, **call context**, or **behaviour**. When a rule depends
on one of those, route it to the right tool; do **not** contrive a brittle arch
test.

| Rule (home) | Tool |
|---|---|
| Thin controllers / no business logic ([../http/conventions.md](../http/conventions.md)) | review |
| Jobs dispatched **after commit** ([../architecture/transactions.md](../architecture/transactions.md)) | a config test asserting `after_commit => true` on each durable connection ([../queues/conventions.md](../queues/conventions.md)) — arch reads neither runtime config nor the `DB::afterCommit()` call-nesting; pair it with the jobs-only-from-actions arch test above |
| Queries are read-only ([../queries/conventions.md](../queries/conventions.md)) | review |
| No `assertDatabaseHas` / `Missing` / `Count` ([conventions.md](conventions.md)) | grep / lint (an inherited method, not an import → arch `toUse` can't see it) |
| No inline leading-`\` FQCN ([../architecture/imports.md](../architecture/imports.md)) | Pint / PHPStan |
| No raw `$request->...` into `create()` / `fill()` ([../security/mass-assignment.md](../security/mass-assignment.md)) | grep / lint |

## Checklist

- A machine-checkable mandatory rule has an `arch()` test (the three-part trigger).
- No built-in fits → a custom expectation via `expect()->extend()` +
  `Targeted::make()` in `tests/Pest.php`, never an imperative reflection loop.
- Each new or changed guard has been seen to **fail** on a real violation, then
  pass.
- Arch tests live in `tests/Arch` (own testsuite); custom expectations in
  `tests/Pest.php`.
- A rule arch can't express is enforced by grep / lint / PHPStan / Pint or review —
  not a contrived arch test.
- The catalog records enforcement; each rule's definition stays in its home.
