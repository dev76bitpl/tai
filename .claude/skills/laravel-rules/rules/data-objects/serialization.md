# Data objects across a queue boundary

What happens when a data object is carried by a queued job, and how to
keep it lean and correct. Read alongside [conventions.md](conventions.md)
and [../jobs/conventions.md](../jobs/conventions.md). The queue/serialization
behavior below is framework-level (PHP `serialize()` + `SerializesModels`)
and holds regardless of `spatie/laravel-data` version; if a `Lazy`/`Optional`
object fights the queue, fall back to the rules here rather than patching.

## Rule: a queued data object carries IDs and scalars, never Eloquent models

Laravel serializes a job's properties with PHP `serialize()`. The
`SerializesModels` trait only re-queries Eloquent models that are
**top-level job properties** — a model **nested inside a data object** is
serialized whole, ships stale, and bloats the payload.

So a data object that crosses a queue holds primitives,
[value objects](../value-objects/conventions.md), enums, and IDs (the
same rule the anchor states for *all* data objects). The job passes the
ID; the action re-fetches inside `handle()`.

**Why:** the database is the source of truth. A serialized model snapshot
captured at dispatch time may be out of date — or reference a row that
changed or was deleted — by the time the job runs.

```php
// Good — fields are scalars/IDs; built via ::from() like any Data object;
// the action re-fetches the model by id inside handle()
final class ProcessSignupData extends Data
{
    public function __construct(
        public readonly string $waitlistSignupId,
        public readonly string $locale,
    ) {}
}

ProcessSignup::dispatch(ProcessSignupData::from($signup));

// Bad — an Eloquent model as a field: serialized whole and stale on run
final class ProcessSignupData extends Data
{
    public function __construct(
        public readonly WaitlistSignup $signup,
    ) {}
}
```

## Rule: do not hand-roll `__serialize` / `__unserialize` to paper over Spatie

A Spatie `Data` object is a plain PHP object and serializes natively in
the simple case. The pain shows up around `Lazy` / `Optional` / partial
state and nested models — and reconstructing `readonly` promoted
properties in a custom `__unserialize` is awkward and fragile.

When a Spatie Data object does not round-trip cleanly through the queue,
**sidestep rather than patch**: keep models out (rule above), avoid
`Lazy` on queued objects, and if it still fights you, drop to a plain DTO
(next rule). Do not scatter custom magic-method serialization across data
objects.

**Why:** a hand-rolled `__unserialize` couples your payload to Spatie's
internal state representation, which changes between versions — exactly
the kind of drift the queue will surface in production, not in tests.

## Decision: keep Spatie `Data`, or drop to a plain DTO?

**Default: keep Spatie `Data`.** A Data object is a plain PHP object and
serializes onto a queue fine in the common case — so the everyday object,
including collections (built with `::collect()`), stays Spatie `Data`
created via `::from()` ([spatie-laravel-data.md](spatie-laravel-data.md)).
Carrying IDs (rule above) is what keeps a queued payload lean, not
abandoning the package.

Drop to a **plain readonly DTO implementing `Arrayable` +
`JsonSerializable`** only as a last resort — when a specific Data object
provably will not round-trip through the queue (a `Lazy`/partial edge
case you cannot remove) and you need none of its boundary powers.

```php
// Plain DTO — the narrow exception. It has no ::from() pipeline, so it is
// the one data object you legitimately construct with `new`.
final readonly class LedgerExportData implements Arrayable, JsonSerializable
{
    public function __construct(
        public string $organizationId,
        public string $period,
    ) {}

    /** @return array{organizationId: string, period: string} */
    public function toArray(): array
    {
        return ['organizationId' => $this->organizationId, 'period' => $this->period];
    }

    public function jsonSerialize(): array
    {
        return $this->toArray();
    }
}
```

**Why:** Spatie `Data` is the consistent default everywhere — one way to
build (`::from()`), one way to collect (`::collect()`), casts and mapping
always applied. Reaching for a plain DTO routinely fragments that
consistency; reserve it for the rare object the queue genuinely rejects.

## Edge cases

- **`Optional` on a queued object.** Prefer a concrete nullable type over
  `Optional` for fields that ride a queue, so there is no partial-state
  ambiguity to serialize.
- **Encrypted/sensitive fields.** Do not put secrets in a queued payload;
  carry an ID and load/decrypt inside the job.

## Checklist

- Queued data objects carry IDs, scalars, value objects, enums — no
  Eloquent models.
- The job's action re-fetches models by ID inside `handle()`.
- No bespoke `__serialize`/`__unserialize` added to dodge Spatie quirks.
- Spatie `Data` (built via `::from()`, collected via `::collect()`) is the
  default on queues too; a plain DTO is a last resort for an object that
  provably will not round-trip.
- No secrets in queued payloads.
