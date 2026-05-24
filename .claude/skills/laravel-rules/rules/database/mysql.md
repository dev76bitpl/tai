# Database — MySQL

MySQL-specific concerns that differ from the portable defaults. Portable
rules live in [schema.md](schema.md) / [migrations.md](migrations.md) /
[performance.md](performance.md); reach here only for engine behavior.
Verify exact syntax/limits against the running MySQL version.

## Rule: `utf8mb4` charset and a `utf8mb4` collation

Tables use `utf8mb4` (real 4-byte Unicode, including emoji), with a
`utf8mb4` collation (e.g. `utf8mb4_unicode_ci`, or `utf8mb4_0900_ai_ci` on
MySQL 8). Never the legacy `utf8` (3-byte) charset.

**Why:** MySQL's `utf8` silently truncates 4-byte characters, corrupting
emoji and some scripts. `utf8mb4` is the only correct Unicode charset.

## Rule: mind index key-length limits on string columns

InnoDB caps index key length (≈3072 bytes with `DYNAMIC` row format).
A unique index on a long `varchar(255)` `utf8mb4` column (4 bytes/char)
can exceed it. Keep indexed string columns appropriately short, or use a
prefix index.

**Why:** a too-long index errors at migration time or silently degrades —
sizing the column for its index is the fix, not widening the limit.

## Rule: JSON columns are plain JSON — index via generated columns

MySQL has only `JSON` (no `JSONB`). To index a JSON path, add a generated
(virtual/stored) column and index that; you cannot index a JSON document
directly. If JSON querying/indexing is central, reconsider whether the
data should be relational columns.

## Rule: change large tables with online DDL, stated explicitly

On a big table, run schema changes online and name the algorithm so MySQL
fails fast instead of silently falling back to a copying, locking build:
`ALTER TABLE ... ADD INDEX ..., ALGORITHM=INPLACE, LOCK=NONE`. Add-column
is often `INSTANT` (8.0.12+) at end-of-table; index builds are `INPLACE,
LOCK=NONE`. For operations InnoDB cannot do online (or older MySQL), use
**gh-ost** or **pt-online-schema-change** (shadow table + chunked copy +
swap). Portable strategy: [large-tables.md](large-tables.md).

**Why:** an unqualified `ALTER` may pick a copying algorithm that locks
the table for the whole rebuild. Stating `ALGORITHM`/`LOCK` makes MySQL
reject the statement rather than lock a tens-of-millions-row table behind
your back.

## Note: InnoDB auto-indexes foreign keys (Postgres does not)

InnoDB automatically creates an index on a foreign-key column, so the FK
is covered for joins/filters even if you forget. Still declare the FK
index explicitly in migrations ([schema.md](schema.md)) for portability —
the same migration must perform on Postgres, which does **not** auto-index
FKs ([postgres.md](postgres.md)).

## Rule: respect REPEATABLE READ and locking semantics

InnoDB defaults to `REPEATABLE READ` and uses next-key/gap locks. A
multi-write [action](../actions/conventions.md) that reads-then-writes
under contention takes an explicit row lock (`lockForUpdate()`) inside its
[transaction](../architecture/transactions.md) to avoid lost updates.

**Why:** the default isolation can still lose updates on read-modify-write
without an explicit lock; gap locks can also cause unexpected blocking on
range conditions. Locking the rows you will write makes the contention
deterministic.

## Checklist

- `utf8mb4` charset + `utf8mb4` collation; never legacy `utf8`.
- Indexed string columns sized within InnoDB key-length limits (or prefix
  indexed).
- JSON paths indexed via generated columns; relational columns preferred
  when JSON is queried heavily.
- Large-table schema changes use explicit `ALGORITHM=INPLACE, LOCK=NONE`
  (or gh-ost / pt-osc) — never an unqualified locking `ALTER`.
- Read-modify-write under contention uses `lockForUpdate()` within the
  action's transaction.
