# Database — historical / temporal data

Modelling a value that changes over time and whose history matters — a
user's credit score, a price, a status. Schema-design concern; sits beside
[schema.md](schema.md) and the read-shape rules in
[performance.md](performance.md). See
[../architecture/placement.md](../architecture/placement.md).

## Rule: the append-only history table is the source of truth

Store every change as a new immutable row in a history table
(`credit_scores`: `user_id`, `score`, `created_at`), never updated or
deleted. The current value is *derived* — the latest row per subject — not
the canonical store.

**Why:** append-only never loses data, gives a full audit trail for free,
and fits this project's ethos — no destructive updates, forward-only,
immutable records. A single mutable "current value" column overwrites
history on every change; once you need "what was it last month?" the
answer is gone.

```php
// each change is an insert, never an update
CreditScore::query()->create([
    'user_id' => $user->id,
    'score'   => $score,
]);
```

## Decision: derive latest on read, or cache a "current" on the parent?

Append-only is always the source of truth; the question is only how you
read "latest":

- **Derive on read (default).** Query the latest row per subject. Correct
  and simple; one place to write. Use when latest-reads are not a hot
  path.
- **Cache a current value on the parent** (a column on `users`, or a
  `current_*` table) **in addition to** the history. Only when latest-reads
  are genuinely hot and the derive query is measurably too slow. The
  [action](../actions/conventions.md) writes the history row *and* updates
  the cached value in **one transaction**
  ([../architecture/transactions.md](../architecture/transactions.md)).

**Why:** the cached current is a denormalization — it duplicates data and
risks drift, so it must be earned by a real read-performance need, not
added speculatively. Default to deriving; cache only when the numbers say
so.

## Rule: index and order the "latest" query deliberately

To fetch the latest row per subject efficiently, index
`(user_id, created_at DESC)` and order by `created_at` (Laravel's
`latest()`); tie-break by `id` for rows sharing a timestamp, or index
`(user_id, created_at DESC, id DESC)`.

**Why:** without the composite index, "latest per user" scans the table.
The index turns it into a range scan. Ordering by `created_at` is the
semantic recency order; ordering by `id` is only valid because PKs are
**time-ordered UUIDs** ([migrations.md](migrations.md)) — so `latest('id')`
also works and needs no extra column, while a random UUIDv4 id would carry
no recency at all.

```php
// latest score for one user
CreditScore::query()->where('user_id', $user->id)->latest()->first();
```

For "latest per user across many users", use a window function /
`DISTINCT ON` (Postgres) rather than N queries
([performance.md](performance.md)).

## Edge cases

- **Unbounded growth.** A history table only grows — plan partitioning or
  archival (by time range) before it is a problem on a hot table.
- **No updates/deletes.** Corrections are *new* rows (a superseding
  entry), preserving the audit trail; never mutate a past row.
- **Latest-per-many.** Avoid the N+1 of one latest-query per subject; do
  it set-based.

## Checklist

- History is an append-only table (insert per change; no update/delete);
  it is the source of truth.
- "Latest" derived on read by default; a cached current value is added
  only for a proven hot read, written with the history row in one
  transaction.
- `(user_id, created_at DESC)` index for the latest query; order by
  `created_at` (or time-ordered `id`), tie-broken by `id`.
- Latest-per-many is set-based (`DISTINCT ON` / window), not N queries.
- Growth handled by partitioning/archival.
