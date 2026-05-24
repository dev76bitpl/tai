# Database — performance

The performance lens on queries and schema: indexing for real access
patterns, avoiding N+1, and bounding large reads. Structural index
*declaration* lives in [schema.md](schema.md); read-composition shape
lives in [../queries/conventions.md](../queries/conventions.md); engine
tuning in [mysql.md](mysql.md) / [postgres.md](postgres.md).
Infrastructure concern (see [../architecture/placement.md](../architecture/placement.md)).

## Rule: index for the queries you actually run

Add indexes to match real `WHERE` / `JOIN` / `ORDER BY` patterns, not
speculatively. Verify with `EXPLAIN` that a hot query uses an index;
order composite indexes equality-first, then range/sort.

**Why:** an index pays read time with write time and storage. Indexing
every column slows writes and bloats the table for queries that never run;
indexing the columns hot queries filter on is where the payoff is. Match
the index to the access pattern the app demonstrably has.

## Rule: no N+1 — eager-load what the read needs

A read that touches a relation per row eager-loads it (`with(...)`);
never lazy-load inside a loop. Enable `Model::preventLazyLoading()` in
non-production so an accidental N+1 fails loudly. Read composition belongs
in a [query object](../queries/conventions.md).

**Why:** N+1 turns one read into hundreds of round-trips that pass tests
on seed data and collapse in production. Failing on lazy-load in dev
surfaces it at the moment it is introduced.

```php
// Bad — one query per organization
$organizations->each(fn ($o) => $o->owner->name);

// Good — one extra query for all owners
Organization::query()->with('owner')->get();
```

## Rule: never load an unbounded set

List endpoints and reads that can grow are paginated; batch processing
uses `chunkById()` / `lazy()`, not `all()`. Select only the columns the
read needs for large result sets.

**Why:** `Model::all()` on a growing table is a latent out-of-memory
incident — fine at 100 rows, fatal at a million. Pagination and chunking
keep memory bounded regardless of table size.

## Decision: add an index, or leave it?

- **Add** — the column is in a hot query's `WHERE`/`JOIN`/`ORDER BY`, the
  table is large enough for a scan to hurt, and reads dominate.
- **Leave** — a small/lookup table, a write-heavy column where the index
  cost outweighs rare reads, or a query that does not run hot.

**Why:** indexes are not free; the decision is a read/write trade measured
against table size and query frequency, not a reflex.

## Edge cases

- **Counting / existence.** Use `exists()` / `count()` rather than
  loading rows to check; avoid `count()` in a loop.
- **Pagination on huge offsets.** Deep `OFFSET` scans the skipped rows —
  prefer keyset/cursor pagination on large tables.
- **Engine specifics.** JSONB/partial/expression indexes
  ([postgres.md](postgres.md)) and key-length/prefix limits
  ([mysql.md](mysql.md)) are engine-owned.

## Checklist

- Indexes match real query patterns, verified with `EXPLAIN`; composite
  order equality-first.
- Reads eager-load relations (`with`); `preventLazyLoading()` on in
  dev/test; no lazy-load in loops.
- No unbounded reads — pagination for lists, `chunkById`/`lazy` for
  batches, column selection for large sets.
- Index decisions made via the read/write trade (Decision above), not
  reflexively.
