# Value objects

Internals of domain value objects — small immutable types that model a
*value with rules and behavior* (`Money`, `Email`, `Percentage`),
compared by their contents rather than by identity. Building-block folder
(internals of one class type, see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: immutable, validated in the constructor

A value object is `readonly`, and it validates its own invariants in the
constructor — an invalid value object cannot exist. To change a value,
build a new instance.

**Why:** "always-valid" is the whole point. If a `Money` can hold a
negative amount or an `Email` an unparseable string, every consumer must
re-check it. Validating once at construction means a value object in hand
is, by type, a value that holds.

```php
// Good — readonly, self-validating, cannot exist in an invalid state
final readonly class Email
{
    public function __construct(
        public string $value,
    ) {
        if (! filter_var($value, FILTER_VALIDATE_EMAIL)) {
            throw new InvalidArgumentException("Invalid email: {$value}");
        }
    }
}

// Bad — mutable, unvalidated; just a string with extra steps
final class Email
{
    public string $value = '';
}
```

## Rule: equality is by value, not identity

Two value objects with the same contents are equal. Expose an
`equals(self $other): bool` rather than relying on `===` (which compares
object identity).

**Why:** a value has no identity — €5 is €5 regardless of which instance
holds it. Comparing by identity would make two equal values test as
different, which is never what domain code means.

```php
final readonly class Money
{
    public function __construct(
        public int $cents,
        public Currency $currency, // backed enum
    ) {}

    public function equals(self $other): bool
    {
        return $this->cents === $other->cents
            && $this->currency === $other->currency;
    }
}
```

## Decision: value object, scalar, enum, or data object?

Reach for a value object only when a plain type cannot carry the meaning:

- **vs a scalar** — use a value object when the value has **invariants or
  behavior** (validation, formatting, arithmetic): `Money`, `Email`. A
  free-form `string $title` with no rules stays a scalar.
- **vs an [enum](../enums/conventions.md)** — use an enum when the values
  are a **fixed, closed set** (`OrderStatus`). Use a value object when the
  space of valid values is open but structured (any valid email, any
  positive amount).
- **vs a [data object](../data-objects/conventions.md)** — a data object
  is a *message/payload* (a command's inputs, an API response), compared
  field-by-field and serialized to array/JSON. A value object is a single
  *domain value* with behavior and value-equality. `Money` is a value
  object; `CreateInvoiceData` is a data object. Value objects are often
  *fields inside* data objects.

**Why:** each upgrade buys something — invariants (over scalar), open
domain (over enum), behavior + equality (over data object). Introducing a
value object that buys none of these is ceremony; skipping one when you
need it scatters the same validation across every call site.

## Rule: persist via an explicit model cast

A value object stored on a model is wired with an explicit attribute cast
(`CastsAttributes`), declared in the model's `casts()` per
[../models/conventions.md](../models/conventions.md). The cast hydrates
the value object on read and serializes it on write.

**Why:** the cast is the single place that maps column ⇄ value object, so
the rest of the code only ever touches the typed value, never the raw
column. (This is a *model* cast — distinct from a Spatie Data cast, which
lives under `app/Data/Casts`; see
[../architecture/structure.md](../architecture/structure.md).)

## Rule: secrets are a redacting value object

A credential/PII value (`Secret` / `HiddenString`) is a value object that
redacts itself on `__toString`, `jsonSerialize`, and `toArray`, exposing
the raw value only through an explicit `reveal()`. This is the central
leak guard data objects rely on; the full pattern is governed by
[../security/secrets.md](../security/secrets.md).

## Edge cases

- **Multi-field values.** A value object may hold several fields
  (`Money` = amount + currency); it is still one value, and equality
  covers all fields.
- **Named constructors.** Add `static` factories for clarity
  (`Money::fromCents(...)`, `Email::fromString(...)`) when raw
  construction is ambiguous — they still funnel through the validating
  constructor.
- **Don't reach for the database.** Validation in the constructor is
  structural only (format, range). "This email isn't already registered"
  is a domain invariant for an [action](../architecture/invariants.md),
  not the value object.

## Checklist

- `readonly`; constructor enforces invariants so an invalid instance
  cannot exist.
- Equality compared by value via `equals()`, not by identity.
- Introduced only when it beats a scalar/enum/data object (Decision
  above) — not as reflexive wrapping.
- Constructor validation is structural; domain/state rules stay in
  actions.
- Persisted through an explicit model cast (see
  [../models/conventions.md](../models/conventions.md)).
- Tested for construction (valid + rejected-invalid) and `equals()`.
