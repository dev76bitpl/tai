# Data objects

A data object is an **immutable, typed shape** that travels between
layers of the application. This file is the package-agnostic anchor — the
*what* and *why*. The project realizes data objects with
`spatie/laravel-data`; its mechanics (mapping, casts, `Optional`,
`toArray()`) live in
[spatie-laravel-data.md](spatie-laravel-data.md), and crossing a queue
boundary lives in [serialization.md](serialization.md).

Building-block folder (internals of one class type, see
[../architecture/placement.md](../architecture/placement.md)).

## Why data objects

- **Contracts between layers.** A data object is the typed handshake
  between HTTP, actions, jobs, and responses. Each layer knows exactly
  what shape it receives and returns.
- **Developer experience.** Promoted typed properties give real
  autocompletion and make the payload self-documenting — no guessing
  array keys.
- **Type safety.** The analyzer enforces the shape; a missing or mistyped
  field fails at the boundary, not three layers deep.

## Rule: data objects are immutable

Promote constructor properties and mark them `readonly`. Construct once;
to change a field, build a new instance.

**Why:** an immutable payload is safe to pass through layers and compare
without action at a distance. The mutable carrier of a
[pipeline](../patterns/pipeline.md) is a *traveller*, a different type —
do not press a data object into that role.

```php
// Good — immutable, typed, promoted readonly properties
final class CreateOrganizationData extends Data
{
    public function __construct(
        public readonly string $name,
        public readonly string $slug,
        public readonly OrganizationTier $tier,
    ) {}
}

// Bad — mutable public state; a data object is not a bag you fill in later
final class CreateOrganizationData extends Data
{
    public string $name = '';
    public ?string $slug = null;
}
```

## Rule: no business logic in a data object

A data object holds and shapes data. It does not query the database, call
services, dispatch jobs, or enforce domain rules. Those belong in
[actions](../actions/conventions.md).

**Why:** the moment a payload reaches out to collaborators it stops being
a portable contract and becomes a hidden mini-action — untestable in
isolation and impossible to pass safely across a boundary.

## Decision: which role — create, update, or response?

Three roles, all immutable, kept as **distinct types** named for intent:

- **Create payload** — input to an action that creates state:
  `CreateOrganizationData`.
- **Update payload** — input to an action that mutates state, typically
  with optional fields for partial updates: `UpdateOrganizationData`.
- **Response object** — the shape returned to an API/frontend:
  `OrganizationResponseData`.

Do not reuse a create payload as a response, or a response as an update
input. If a model alone answers the caller, return the model — introduce
a response object only when the shape is genuinely API-facing or richer
than one model.

**Why:** each role has a *different contract* once serialized to
array/JSON. A dual-purpose object accumulates "set sometimes" fields —
exactly how nullable rot and leaky API payloads begin.

## Rule: carry scalars, value objects, and IDs — not Eloquent models

A data object's fields are primitives, [value objects](../value-objects/conventions.md),
enums, and identifiers — not Eloquent models. Reference a related record
by its ID and let the action load it.

**Why:** a model embedded in a data object is heavy, mutable, and — when
the object crosses a queue — serialized whole and stale (see
[serialization.md](serialization.md)). IDs keep the contract light and
the source of truth in the database.

## Decision: where does a check belong — data object, form request, or action?

- **Shape of the input** (required, type, format, length) → structural
  validation on the data object or a form request at the HTTP edge.
- **A guarantee about domain state** ("slug not already taken", "tier
  allows this") → the **action**, as an invariant — never the data
  object, which cannot see the database.

Governed canonically by
[../architecture/invariants.md](../architecture/invariants.md): a data
object asserts *its fields are well-formed*; it must not assert *the
operation is allowed*.

## Rule: a secret field is a wrapped value object, never a raw string

When a data object carries a credential or PII, the field is a `Secret`
value object and its promoted parameter is marked `#[SensitiveParameter]`.
The full layered pattern (value-object wrap + trace redaction + unwrap at
the boundary + keep out of queue payloads) is governed canonically by
[../security/secrets.md](../security/secrets.md) — do not restate it here.

## Checklist

- Properties are promoted and `readonly`; the object is immutable.
- Secret/PII fields are wrapped value objects (not raw strings) per
  [../security/secrets.md](../security/secrets.md).
- The object holds data only — no queries, services, dispatch, or domain
  rules.
- Role is one of create / update / response, as a distinct type — none
  reused across directions.
- Fields are scalars, value objects, enums, or IDs — no Eloquent models.
- Only structural validation lives here; state-dependent rules are action
  invariants ([../architecture/invariants.md](../architecture/invariants.md)).
- Package mechanics → [spatie-laravel-data.md](spatie-laravel-data.md);
  queue serialization → [serialization.md](serialization.md).
