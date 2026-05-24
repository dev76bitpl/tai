# Database — schema

Schema design: column types, nullability, keys, and structural indexing.
Migration *mechanics* (UUID PK, `foreignIdFor(...)->constrained()`,
forward-only, no cascades/defaults/DB-enums) are owned by
[migrations.md](migrations.md); the *performance* lens (which patterns to
index for, N+1) is [performance.md](performance.md). Infrastructure
concern (see [../architecture/placement.md](../architecture/placement.md)).

## Rule: prefer portable column types

Choose the portable Laravel column type that fits the data; keep
engine-specific types out of the shared schema. Engine specifics defer to
[mysql.md](mysql.md) / [postgres.md](postgres.md).

**Why:** portable types keep the same migration valid across the engines
the project runs (local vs CI vs prod), and keep the schema readable
without engine knowledge. Reach for an engine type only when a documented
need justifies it, in the engine file.

- Money: integer minor units (cents) only — never `float`, and never
  `decimal`. One representation (integer cents) avoids rounding drift and
  mixed-type arithmetic; wrap it in a `Money` [value object](../value-objects/conventions.md).
- Percentages / rates: integer basis points (1% = 100 bps) — never
  `float`, never `decimal`, for the same reason; wrap in a `Percentage`
  [value object](../value-objects/conventions.md).
- Time: `timestamp`/`datetime`; store UTC.
- Enums: `string` columns cast to PHP enums ([../enums/conventions.md](../enums/conventions.md)),
  never a DB `enum` (migrations.md).
- Identifiers: `uuid` (migrations.md owns the PK rule).

## Rule: columns are `NOT NULL` unless absence is a real state

Default every column to `NOT NULL`. Make a column nullable only when
"no value" is a genuine, distinct domain state — not as a convenience to
skip supplying a value.

**Why:** a gratuitously nullable column pushes a null-check into every
read and blurs "unset" with "deliberately empty." Because migrations
forbid DB defaults, the value is set explicitly in app code/data objects
anyway — so `NOT NULL` costs nothing and documents that the column always
has a value. (Mirrors `Optional` vs `null` in
[../data-objects/spatie-laravel-data.md](../data-objects/spatie-laravel-data.md).)

## Rule: back domain invariants with constraints

A uniqueness or referential guarantee gets a database constraint — a
unique index, a foreign key — as the backstop, not as the primary check.
The action still validates first and throws a business exception; the
constraint closes the concurrency race.

**Why:** this is the DB-constraint layer from
[../architecture/invariants.md](../architecture/invariants.md): the action
gives a meaningful failure, the constraint guarantees correctness when two
requests race. Both, not either.

```php
$table->string('email');
$table->unique('email'); // backs the "one signup per email" invariant
```

## Rule: declare structural indexes with the table — including foreign keys

Every foreign key and every column the app routinely filters, joins, or
sorts on has an index, declared in the migration alongside the column.
Composite-index column order follows the query (equality columns first,
then range/sort). *Which* patterns need indexes is analysed in
[performance.md](performance.md).

A foreign-key **constraint does not create an index** on the FK column on
every engine — Postgres does not auto-index FKs (MySQL/InnoDB does, see
[postgres.md](postgres.md) / [mysql.md](mysql.md)). So always declare the
FK column's index explicitly; do not assume `constrained()` covers it.

```php
$table->foreignIdFor(User::class)->constrained(); // constraint only
$table->index(['user_id']);                        // index you must add
```

## Edge cases

- **Wide/unbounded text.** Use `text` for free-form content; do not put a
  plain unique index on a long `varchar` (engine key-length limits — see
  [mysql.md](mysql.md)).
- **Polymorphic relations.** Index the `(type, id)` pair together; prefer
  explicit typed FKs where the set of related types is closed.
- **Column order is cosmetic.** Add new columns at the end; never use
  `->after()`/`->first()` — they are MySQL-only and Postgres cannot
  reorder columns ([postgres.md](postgres.md)).

## Checklist

- Portable column types; engine-specific types only in the engine files.
- Money as integer minor units, percentages as integer basis points
  (never float, never decimal); enums as string columns; UTC timestamps.
- Columns `NOT NULL` unless absence is a real domain state.
- Uniqueness/referential invariants backed by a unique index / FK
  (backstop, per invariants.md).
- FKs and routinely-queried columns are indexed; the FK column's index is
  declared explicitly (the constraint does not create it on Postgres);
  composite order matches the query.
