# Mass assignment

Guarding Eloquent writes against unintended attribute assignment
(over-posting). Cross-cutting security concern (see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: never mass-assign raw request input — the data object is the allow-list

Never pass `$request->all()` (or any unfiltered array) to `create()`,
`update()`, `fill()`, or `forceCreate()`. Writes go through a typed
[data object](../data-objects/conventions.md): the action receives the
data object and persists `$data->toArray()`, whose keys are exactly its
declared properties.

**Why:** a raw request array lets a caller post fields you never intended
(`is_admin`, `organization_id`, `verified_at`) and have them silently
persisted. A data object is a fixed allow-list *by construction* — only
its typed properties can reach the column set — so over-posting is
impossible at the boundary, before any model-level guard is consulted.
Same rule as [../http/conventions.md](../http/conventions.md), from the
security side.

```php
// Bad — over-postable: any extra field rides straight into the row
Organization::query()->create($request->all());

// Good — the data object is the allow-list; keys are its typed properties
Organization::query()->create(
    RegisterOrganizationData::from($request->validated())->toArray(),
);
```

## Decision: unguarded models, or an explicit `$fillable`?

Because the data object is already the allow-list, the model-level guard
is a *second* allow-list covering a path this codebase forbids (raw input
reaching a write). Two defensible positions:

- **Unguarded (`$guarded = []`, or global `Model::unguard()`) —
  acceptable here, and the project default.** The data object is the
  single source of truth for what may be written; `$fillable` would only
  duplicate it and drift from it.
  - *Pros:* one allow-list, not two that can disagree; no `$fillable` to
    maintain against migrations; no silent attribute-drop (a key missing
    from `$fillable` is silently ignored by Eloquent — a confusing
    "why didn't it save?" bug).
  - *Cons:* it removes the last backstop. Unguarded is **only as safe as
    the discipline that no raw array ever reaches a write** — one
    `create($request->all())` and over-posting is wide open. Factories,
    importers, and package code that build arrays from external data can
    over-post too.
- **Explicit `$fillable`** — keep it when the team wants defense in depth
  or cannot guarantee the boundary holds. Never `$guarded = []` *and* no
  discipline — that is the worst of both.

**The condition that makes unguarded safe:** if you unguard, the
"never mass-assign raw input" rule stops being best-practice and becomes
**load-bearing**, so enforce it mechanically — a
[Pest arch test or grep/lint](../testing/architecture.md) that fails when
`create(`/`update(`/`fill(` receives `$request->...` (this rule is the
grep/lint case — an inherited request method isn't arch-expressible). Global `Model::unguard()` is the most consistent (no
per-model drift); the trade is the broadest blast radius if the boundary
ever breaks.

## Edge cases

- **Server-set columns** (a derived FK, `created_by`). Add them via an
  explicit array spread when persisting, not from input (see the spread
  pattern in [../data-objects/spatie-laravel-data.md](../data-objects/spatie-laravel-data.md)).
- **Route-model binding** resolves *which* record; it does not authorize
  the write — pair it with [authorization.md](authorization.md) so a bound
  model the actor may not touch is still rejected.

## Checklist

- No `create`/`update`/`fill` with `$request->all()` or unfiltered arrays.
- Writes go through a data object; server-set columns added via explicit
  spread, not from input.
- Guard choice made via the Decision: unguarded with an **enforced**
  no-raw-input rule (default), or explicit `$fillable` — never
  `$guarded = []` without the enforced boundary.
- A test posts an unexpected field and asserts it is not persisted; if
  unguarded, a test/lint fails on raw input reaching a write.
