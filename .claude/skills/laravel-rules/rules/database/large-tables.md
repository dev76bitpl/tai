# Database — schema changes on large tables

Changing the schema of a table with tens of millions of rows without
taking it down. Portable strategy here; engine specifics live in
[postgres.md](postgres.md) / [mysql.md](mysql.md); general migration
mechanics in [migrations.md](migrations.md). Infrastructure concern (see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: never run a plain blocking DDL on a large table

A bare `ALTER TABLE` / `CREATE INDEX` takes a heavy lock for the whole
operation — on a huge table that is minutes of downtime. Always use the
engine's online path: `CREATE INDEX CONCURRENTLY` on Postgres
([postgres.md](postgres.md)), `ALGORITHM=INPLACE, LOCK=NONE` on MySQL
([mysql.md](mysql.md)), or a copy tool (gh-ost / pt-online-schema-change)
where the engine cannot do it online.

**Why:** the lock, not the work, is what causes the outage. The online
variants do the same work while concurrent reads and writes continue. On
a small table the difference is invisible; on a large one it is the
difference between a deploy and an incident.

## Rule: split add-column → backfill → constrain into separate steps

Adding a populated, constrained column is not one migration. Sequence it:

1. **Add the column nullable** — metadata-only and instant on both engines
   (and the project forbids DB defaults anyway, so it is always nullable
   at first — [migrations.md](migrations.md)).
2. **Backfill in batches** — a job/command using `chunkById()`, *not* a
   migration, so it does not run in one giant locking transaction
   ([performance.md](performance.md)).
3. **Add the index / `NOT NULL`** as its own online step once data is in
   place.

Because migrations are forward-only here, these are also distinct deploys:
add column → ship code that writes it → backfill → constrain.

**Why:** a single migration that adds, backfills, and constrains holds a
long transaction and a lock across all of it. Splitting keeps each step
short and online, and lets the backfill be chunked and resumable.

## Rule: set a lock timeout so a waiting migration doesn't stall the table

Before a DDL statement, set a short `lock_timeout` (and a sane
`statement_timeout`). A migration that blocks waiting for a lock queues
*ahead* of every later query on that table — so a slow lock acquisition
takes the table down even with an "online" operation.

**Why:** the online algorithms still need a brief lock to start; if a
long-running query holds it, the migration waits — and everything queues
behind the migration. Failing fast on the timeout and retrying is far
safer than an unbounded wait that cascades.

## Rule: reach for raw `DB::statement` when the schema builder can't express it

Laravel's schema builder does not emit `CONCURRENTLY` or `ALGORITHM`/
`LOCK` hints. For online DDL, use `DB::statement('...')` with the explicit
clause, and set `public $withinTransaction = false;` on the migration when
the statement cannot run in a transaction (Postgres `CONCURRENTLY`).

## Edge cases

- **Off-peak.** Run heavy DDL and backfills during low traffic; monitor
  replication lag (a long copy can lag replicas).
- **Failed `CONCURRENTLY`.** A failed concurrent index build leaves an
  invalid index — drop it and retry ([postgres.md](postgres.md)).
- **New index discoverability.** Add the FK/query index in the *same*
  online step that the access pattern needs it (the FK constraint does not
  create it on Postgres — [schema.md](schema.md)).

## Checklist

- No plain blocking `ALTER`/`CREATE INDEX` on a large table — online path
  per engine (or gh-ost / pt-osc).
- Add-column, backfill (chunked job), and constrain/index are separate
  steps (and deploys).
- `lock_timeout`/`statement_timeout` set before DDL; fail fast and retry,
  never wait unbounded.
- Online clauses written via raw `DB::statement`; `$withinTransaction =
  false` for Postgres `CONCURRENTLY`.
- Run off-peak; watch replication lag.
