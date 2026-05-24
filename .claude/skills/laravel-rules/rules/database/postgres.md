# Database — PostgreSQL

PostgreSQL-specific concerns that differ from the portable defaults.
Portable rules live in [schema.md](schema.md) / [migrations.md](migrations.md)
/ [performance.md](performance.md); reach here only for engine behavior.
Verify exact syntax against the running PostgreSQL version.

## Rule: use `JSONB`, not `JSON`, and index it with GIN

Store document data as `JSONB` (binary, queryable, indexable), not `JSON`
(text). Index a `JSONB` column you query with a `GIN` index. As with
MySQL, if the data is queried relationally, prefer real columns over a
JSON blob.

**Why:** `JSON` is stored verbatim and cannot be indexed usefully;
`JSONB` supports containment/path operators and GIN indexes. `JSONB` is
the only sensible choice on Postgres.

## Rule: reach for partial and expression indexes when they fit

Postgres supports indexes that the portable schema cannot express:

- **Partial index** (`WHERE`) — index only the rows that matter (e.g.
  `WHERE deleted_at IS NULL`, or only `active` rows).
- **Expression index** — index a computed value (`lower(email)`) to back
  case-insensitive lookups.

Declare these in a raw statement within the migration when a hot query
justifies them ([performance.md](performance.md)).

**Why:** a partial/expression index is smaller and more selective than a
full-column index for the matching query — a Postgres advantage worth
using deliberately, not a default.

## Rule: UUID primary keys are generated app-side

The UUID PK rule ([migrations.md](migrations.md)) stands: the application
generates the UUID (Laravel `HasUuids` / the model), not a database
default — migrations forbid DB defaults, so do not rely on
`gen_random_uuid()` as a column default.

**Why:** generating the id in the model keeps the value known before
insert (usable in the same request/transaction) and keeps id generation
portable and explicit rather than hidden in a DB default.

## Rule: build/drop indexes on large tables `CONCURRENTLY`

On a big table, create and drop indexes with `CREATE INDEX CONCURRENTLY`
/ `DROP INDEX CONCURRENTLY` so writes are not blocked
([large-tables.md](large-tables.md)). It cannot run inside a transaction,
so set `public $withinTransaction = false;` on the migration and issue it
via raw `DB::statement` (the schema builder does not emit `CONCURRENTLY`).
A failed concurrent build leaves an **invalid** index — drop it and retry.
For a column that must become `NOT NULL`, add a `CHECK ... NOT VALID` then
`VALIDATE CONSTRAINT` (weak lock) instead of a scanning `SET NOT NULL`.
Set a short `lock_timeout` before DDL so a blocked migration does not
queue ahead of the whole table.

**Why:** a plain `CREATE INDEX` takes an `ACCESS EXCLUSIVE`-class lock that
stops writes for the build — minutes of outage on a large table.
`CONCURRENTLY` trades a longer build for staying online.

## Rule: never reorder columns — no `->after()` / `->first()`

Postgres cannot reposition a column. `->after('x')` and `->first()` are
MySQL-only; on Postgres they do not reorder anything. Genuinely changing
physical column order would require recreating the table — create a new
table, copy the data, drop the old one, rename — which this project does
not do.

**Why:** physical column order is cosmetic — it has no effect on queries,
Eloquent, or the API, so it never justifies a destructive table rebuild.
Add new columns at the end of the table and leave order alone; reaching
for `->after()` to "tidy" placement either silently does nothing
(Postgres) or tempts an unnecessary rebuild.

## Rule: index foreign keys explicitly — Postgres does not

A foreign-key constraint in Postgres indexes the **referenced** (parent)
column, but creates **no index on the referencing (child) FK column**. A
query that filters or joins by the relation therefore does a sequential
scan unless you declare the index yourself.

**Why:** this is the most common "the FK is there, why is it slow?"
surprise on Postgres. Unlike MySQL/InnoDB (which auto-creates the index),
Postgres leaves it to you — so declare `$table->index('user_id')`
alongside the constraint whenever you query by that relation
([schema.md](schema.md)).

## Rule: respect READ COMMITTED and locking semantics

Postgres defaults to `READ COMMITTED`. A multi-write
[action](../actions/conventions.md) that reads-then-writes under
contention takes an explicit `lockForUpdate()` inside its
[transaction](../architecture/transactions.md); use advisory locks for
coordination that is not tied to specific rows.

**Why:** under `READ COMMITTED`, a read-modify-write can lose updates
without an explicit row lock. Locking the rows you will write (or an
advisory lock for cross-row coordination) makes contention deterministic.

## Checklist

- Document data is `JSONB` (GIN-indexed when queried); relational columns
  preferred when queried heavily.
- Partial/expression indexes used where a hot query justifies them.
- UUID PKs generated app-side (no `gen_random_uuid()` default), per
  migrations.md.
- FK columns indexed explicitly (Postgres does not auto-index them).
- No `->after()`/`->first()`; new columns added at the end (Postgres
  cannot reorder columns).
- Index changes on large tables use `CONCURRENTLY` (`$withinTransaction =
  false`, raw `DB::statement`, `lock_timeout` set); failed builds dropped
  and retried.
- Read-modify-write under contention uses `lockForUpdate()` (or advisory
  locks) within the action's transaction.
