# Enums

Internals of PHP enums: how they are backed, named, kept, and cast.
Building-block folder (internals of one class type, see
[../architecture/placement.md](../architecture/placement.md)). Use an enum
for a **fixed, closed set** of values — the boundary against a
[value object](../value-objects/conventions.md) (open but structured) is
in that file's Decision.

## Rule: enums are string-backed

Every domain enum is a backed enum with **string** backing values, not
`int` and not pure (unbacked).

**Why:** string backing survives persistence and serialization legibly —
a row or JSON payload reads `'pending'`, not `2`. Integer backing couples
meaning to position, so reordering or removing a case silently rewrites
stored data; pure enums cannot be cast or persisted at all.

```php
// Good — string-backed, values are stable and self-describing
enum OrderStatus: string
{
    case Pending = 'pending';
    case Paid = 'paid';
    case Refunded = 'refunded';
}

// Bad — int backing ties stored data to ordering; pending becomes "1"
enum OrderStatus: int
{
    case Pending = 1;
}
```

## Rule: name without an `Enum` suffix

The type is named for the concept (`OrderStatus`, `OrganizationTier`), not
`OrderStatusEnum`. Governed by [../naming/conventions.md](../naming/conventions.md).

## Rule: cast on the model; never use a native DB enum column

Declare the enum in the model's `casts()` so reads/writes are typed; store
it in a plain `string` column. Do not use a database `enum` column type.

**Why:** the cast makes the model attribute a real enum end to end. A
native DB `enum` column hard-codes the value set into a migration, so
adding a case needs a schema change and engines disagree on the type —
the no-DB-enum rule lives in
[../database/migrations.md](../database/migrations.md).

```php
// model
protected function casts(): array
{
    return ['status' => OrderStatus::class];
}
```

A data object property typed as the enum is cast automatically by Spatie
Data from its backing value (see
[../data-objects/spatie-laravel-data.md](../data-objects/spatie-laravel-data.md)).

## Decision: how much behavior belongs on the enum?

Keep enums thin by default; add a method only when the logic is a pure
function of the case itself:

- **Belongs on the enum** — derivations intrinsic to the value: a display
  `label()`, a `color()`, an `isTerminal()` predicate, an allowed-
  transitions check. Pure, no I/O, no dependencies.
- **Does not belong** — anything needing the database, services, or other
  models, or any state mutation. That is an [action](../actions/conventions.md)
  or a [query](../queries/conventions.md), not an enum method.

**Why:** a method that is a pure function of the case keeps related
knowledge with the type and is trivially testable. The moment an enum
reaches for collaborators it becomes a hidden service in disguise — the
same trap the [data-object](../data-objects/conventions.md) "no business
logic" rule guards against.

```php
enum OrderStatus: string
{
    case Pending = 'pending';
    case Paid = 'paid';
    case Refunded = 'refunded';

    public function label(): string
    {
        return ucfirst($this->value);
    }

    public function isTerminal(): bool
    {
        return $this === self::Refunded;
    }
}
```

## Edge cases

- **Persisted set changes.** Because backing values are the stored
  contract, never repurpose an existing string; add a new case and migrate
  data deliberately.
- **`from()` vs `tryFrom()`.** Use `from()` when an unknown value is a bug
  worth throwing on; `tryFrom()` only where an unmatched value is a valid
  "none" you handle.

## Checklist

- Enum is string-backed (not int, not pure).
- Named for the concept, no `Enum` suffix.
- Cast in the model's `casts()`; stored in a `string` column, never a
  native DB `enum`.
- Methods are pure functions of the case only — no DB/services/state.
- Backing values are treated as a stable contract; cases added, never
  repurposed.
- Tested: backing values, and any `label()`/predicate/transition logic.
