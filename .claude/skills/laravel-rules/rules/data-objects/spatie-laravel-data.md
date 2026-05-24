# Data objects with spatie/laravel-data

How the project realizes [data-object conventions](conventions.md) with
`spatie/laravel-data`. The principles (immutable, roles, no business
logic) live in the anchor; this file is the package mechanics.

The API below is verified against `spatie/laravel-data` v4 (the current
stable line). If you ever land on an older major, confirm attribute names
and the collection-typing idiom with `search-docs`.

## Rule: construct with `::from()` — never `new`

Always create a Spatie Data object through `::from()`, passing a request,
Eloquent model, array, or JSON. Never instantiate one with `new`.

**Why:** `::from()` runs the full pipeline — casts, transformers, name
mapping, and `Optional` resolution. `new` bypasses all of it: casts never
fire (you store raw input instead of the typed value), mapping is
skipped, and you must hand-build every `Optional` yourself. Forget one
and a property that should be *absent* becomes an unintended `null` —
silently changing the output contract (see the `Optional` rule below).

```php
// Good — from() resolves casts, mapping, and Optionals from any source
$data = CreateOrganizationData::from($request->all());  // request / array
$data = CreateOrganizationData::from($organization);     // Eloquent model
$data = CreateOrganizationData::from($payloadJson);      // JSON string

// Bad — new bypasses casts/mapping and forces hand-built Optionals
$data = new CreateOrganizationData(name: 'Acme', vat: new Optional());
```

## Rule: build collections with the data class, not raw arrays

When you need a collection of data objects, build it with the data
class's `::collect()` method — not `array_map(fn () => new ...)`.

**Why:** the collection method runs every item through `::from()`, so
casts, transformers, and mapping apply uniformly across the set. A
hand-mapped array of `new`-ed objects skips the pipeline per item and
loses the type guarantees on serialization — the same trap as `new`, once
per element.

```php
// Good — each item resolved through the pipeline
$rows = CreateOrganizationData::collect($request->input('organizations'));

// Bad — raw array of hand-constructed objects, pipeline skipped
$rows = array_map(
    fn (array $r) => new CreateOrganizationData(...$r),
    $request->input('organizations'),
);
```

## Rule: `Optional` omits the field from output — mind API/frontend contracts

A property typed `Type|Optional` that was not supplied is **excluded**
from `toArray()` / `toJson()` entirely — the key is *absent*, not `null`.
This is the right tool for partial updates (PATCH semantics) and for
responses that should hide unset fields.

**Why:** an absent key and a `null` value mean different things to an API
client. `Optional` says "not provided"; `null` says "explicitly empty."
The wrong choice silently changes the response contract — a frontend
keying on presence behaves differently.

```php
final class UpdateOrganizationData extends Data
{
    public function __construct(
        public readonly string|Optional $name,    // absent in output if not sent
        public readonly string|null     $website, // present as null if cleared
    ) {}
}
```

## Using data objects in actions

The data object is the action's input ([../actions/conventions.md](../actions/conventions.md));
inside `handle()`, turn it into the persisted row.

```php
// Create — toArray() feeds mass assignment
public function handle(CreateOrganizationData $data): Organization
{
    return Organization::query()->create($data->toArray());
}

// Update — same on an existing model; Optional fields are simply skipped
public function handle(Organization $organization, UpdateOrganizationData $data): Organization
{
    $organization->update($data->toArray());

    return $organization->refresh();
}
```

### Exclude properties from the persisted payload

When a field belongs in the input but not the row (a confirmation, a
transient flag), drop it before `toArray()`:

```php
Organization::query()->create($data->except('captchaToken')->toArray());
// or whitelist instead: $data->only('name', 'slug', 'tier')->toArray()
```

### Extend the payload when writing

To add a column the caller does not supply (a derived FK, a server-set
value), prefer an explicit **array spread** at the call site — it keeps
the addition local to this write and out of the object's public shape:

```php
Organization::query()->create([
    ...$data->toArray(),
    'created_by' => $actor->id,
    'slug' => Str::slug($data->name),
]);
```

Use the object's own `->additional([...])` only when the extra field is
part of the object's *output* contract wherever it serializes (e.g. a
computed field that belongs in every API response) — not for a one-off
persistence detail.

## Decision: camelCase or snake_case — and how to map

PHP properties stay **camelCase**. But two consumers usually want
**snake_case**: database columns (so `toArray()` keys match columns on
`create()`/`update()`) and many JSON APIs. Bridge with a mapper rather
than renaming properties:

- `#[MapName(SnakeCaseMapper::class)]` (class-level) — map **both**
  directions; the common case when input, DB, and JSON are all snake_case.
- `#[MapInputName(SnakeCaseMapper::class)]` — incoming snake_case JSON →
  camelCase properties only.
- `#[MapOutputName(SnakeCaseMapper::class)]` — camelCase properties →
  snake_case `toArray()`/`toJson()` only (e.g. snake_case DB columns on
  write while accepting camelCase input).
- Per-property `#[MapInputName('organization_name')]` for a one-off
  mismatch.

```php
#[MapName(SnakeCaseMapper::class)]
final class CreateOrganizationData extends Data
{
    public function __construct(
        public readonly string $displayName, // <- display_name in array & JSON
        public readonly OrganizationTier $tier,
    ) {}
}
```

**Why:** camelCase properties keep PHP idiom and autocompletion; mapping
at the edge lines `toArray()` up with snake_case columns without leaking
snake_case into your PHP, and the input/output split lets the API and the
DB disagree on casing safely.

## Rule: cast on the way in, transform on the way out; enums cast themselves

- A property typed as a **backed enum** is cast automatically from its
  backing value — `public readonly OrganizationTier $tier` accepts
  `'pro'` and yields the enum (see [../enums/conventions.md](../enums/conventions.md)).
  No attribute needed for the common case.
- Turn raw input into a richer type with a **cast** — string/cents →
  `Money` via `#[WithCast(MoneyCast::class)]`.
- Shape a property for array/JSON output with a **transformer** —
  `CarbonImmutable` → ISO string via `#[WithTransformer(...)]`.

Custom casts live in `app/Data/Casts`, transformers in
`app/Data/Transformers` — the **only** sanctioned nesting (registry in
[../architecture/structure.md](../architecture/structure.md)); the data
objects themselves stay flat in `app/Data`.

```php
final class CapturePaymentData extends Data
{
    public function __construct(
        #[WithCast(MoneyCast::class)]
        public readonly Money $amount,            // cast in
        public readonly PaymentMethod $method,    // backed enum, auto-cast
        #[WithTransformer(IsoDateTransformer::class)]
        public readonly CarbonImmutable $capturedAt, // transformed out
    ) {}
}
```

## Edge cases

- **Absent vs null.** `Optional` = key omitted; `?type = null` = key
  present, value null. Choose deliberately (see the `Optional` rule).
- **Collections.** Type the element class explicitly with a docblock
  annotation — `/** @var array<OrganizationData> */` over the property —
  never a bare untyped `array`. (`#[DataCollectionOf(OrganizationData::class)]`
  still works but v4 prefers the annotation, for better static-analysis
  and IDE support.)
- **`toArray()` keys must match columns.** A write that fails on an
  unknown column usually means the output mapping (camel vs snake) is off
  — fix it with a mapper, not by renaming the column.
- **Crossing a queue.** Spatie Data on a job has caveats — see
  [serialization.md](serialization.md).

## Checklist

- Objects are constructed with `::from()` (and collections with
  `::collect()`) — never `new`, so casts/mapping/`Optional` resolve.
- `Optional` vs `null` chosen deliberately; the API/frontend output
  contract is intentional.
- Writes use `->toArray()` with `->only()`/`->except()` or an explicit
  spread for derived columns — not hand-built arrays.
- Casing handled by a mapper (`MapName`/`MapInputName`/`MapOutputName`);
  properties stay camelCase.
- Casts in / transformers out live under `app/Data/Casts` /
  `app/Data/Transformers`; data objects stay flat.
- Backed enums rely on automatic casting; custom types use an explicit
  cast/transformer.
- A `toArray()` round-trip test covers mapping, casting, and transformation.
