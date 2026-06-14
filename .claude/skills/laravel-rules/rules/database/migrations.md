# Migration Rules

## IDs And Timestamps

Always use UUID primary keys, and they are **time-ordered** by default:
Laravel's `HasUuids` trait generates UUIDv7 (`Str::uuid7()`) — timestamp-
first and lexically sortable, so generation order is sort order. Add the
trait to the model; the migration column is simply:

```php
$table->uuid('id')->primary();
```

`HasUuids` sets the key in `save()`/`create()` (inline in `performInsert()`,
so it survives `saveQuietly()`) — but it does **not** run on a bulk
`insert()`/`upsert()` or a query-builder write, and the PK is `NOT NULL`
with no DB default. So a bulk-writing action must generate `Str::uuid7()`
per row itself ([../actions/conventions.md](../actions/conventions.md));
do not rely on a DB default like `gen_random_uuid()` (defaults are
forbidden below, and `gen_random_uuid()` is UUIDv4 anyway).

Never use a random UUIDv4 PK. A random PK lands inserts at random points
in the B-tree on large tables — page splits, poor cache locality, write
amplification — which hurts exactly the tens-of-millions-row tables. A
time-ordered UUID inserts near-sequentially and makes `ORDER BY id`
chronological, so `latest('id')` is a valid recency order (see
[history.md](history.md) and [large-tables.md](large-tables.md)). The
trade-off: a UUIDv7 embeds its creation time — acceptable for internal
identifiers.

Always place timestamps immediately after the primary key:

```php
$table->uuid('id')->primary();
$table->timestamps();
```

## Foreign Keys

Always use `foreignIdFor()` for foreign keys and **always** constrain them:

```php
$table->foreignIdFor(User::class)->constrained();
```

The constraint is not optional. Without it, deleting a parent while child
rows still reference it silently leaves orphaned rows — no exception, just
stale data, which is also a GDPR liability when those children hold
personal data you believe was deleted. A constrained foreign key instead
*throws* on the forgotten child, forcing the deletion to be explicit and
complete.

Never use cascading deletes or cascading updates in migrations. Domain
behavior must be explicit in actions, not hidden in database cascade
rules: the action deletes children before the parent, inside one
transaction ([../architecture/transactions.md](../architecture/transactions.md)).
So a constrained FK with no cascade is exactly the safety net — it blocks
an incomplete delete instead of silently orphaning or silently cascading.

## Defaults And Enums

Never define database defaults in migrations. Set defaults explicitly in application code or data objects.

Never use database enum columns. Use strings or other portable column types and cast to PHP enums in Eloquent models.

## Down Methods

Never define a `down()` method. Migrations are forward-only in this project.

## Checklist

- UUID primary key via `$table->uuid('id')->primary()`, generated
  app-side and **time-ordered** (never random UUIDv4).
- `$table->timestamps()` appears immediately after the primary key.
- Foreign keys use `foreignIdFor(...)->constrained()` — always
  constrained, so a forgotten child throws instead of orphaning data.
- No `cascadeOnDelete()`, `cascadeOnUpdate()`, or equivalent cascade
  behavior; children are deleted explicitly in the action's transaction.
- No `SoftDeletes` — deletes are hard deletes (see
  [../models/conventions.md](../models/conventions.md)).
- No column defaults.
- No database enum columns.
- No `down()` method.
