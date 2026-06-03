# Cache invalidation, versioning & stampede

Keeping the cache honest after a write: when and how to invalidate, how to
invalidate a large group cheaply, and how to survive the resulting misses. The
write/freshness side of [caching](../patterns/caching.md); reads are
[reads.md](reads.md), infrastructure is [conventions.md](conventions.md).

Two rules carry everything here: **invalidate by delete, not update**, and
**every entry has a TTL** as the self-healing backstop. Every explicit
invalidation scheme has a race; TTL is the only thing that guarantees recovery.

## Rule: invalidation is a write — a dedicated class, triggered from the action

Invalidation is a side effect of a domain change, so it lives on the write side:
a dedicated `Invalidate*Cache` class (it reads like an
[action](../actions/conventions.md)), **triggered from the action that made the
change** — never from an [observer or event](../observers/conventions.md), never
inside a query. It references the cache-query's key vocabulary
([reads.md](reads.md)) rather than re-deriving keys.

```php
final class InvalidateUserTeamsCache
{
    public function handle(int $userId): void
    {
        Cache::forget(TeamCacheQuery::key($userId)); // delete, never update
    }
}
```

## Rule: delete, never update

On a write, **forget** the affected keys and let the next read repopulate from
the DB. Never write the new value into the cache on the write path.

**Why:** two concurrent writers that both *update* the cache can interleave and
leave the older value resident. Delete defers repopulation to a read, where the
DB — the single source of truth for ordering — reseeds it. (This is why
[write-through](../patterns/caching.md) is discouraged.)

## Rule: invalidation timing — Redis-side after commit, the version counter in the transaction

- **Redis deletes** (`forget`, `tags()->flush()`) and any dispatched **flush
  job** fire **after the transaction commits**
  ([../architecture/transactions.md](../architecture/transactions.md)): a Redis
  delete cannot be rolled back, so it must not fire against a write that may roll
  back.
- **The DB version-counter bump** (below) fires **inside** the domain
  transaction — it is an intra-DB write that rolls back with the transaction, so
  making it atomic with the write is correct and leaves no commit→invalidate
  staleness window.

## Rule: match the mechanism to the blast radius

| Scope | Mechanism |
|---|---|
| One entity | `Cache::forget($key)` |
| Small **bounded** group (per-user/per-team) | scoped `Cache::tags([...])->flush()`, inline after commit |
| Large/heavy bounded group | the same, **dispatched as a job** |
| Large/unbounded group, or a mass update | a **generational version key** (below) — never a mega-tag |
| — | **never** `Cache::flush()` to invalidate (it wipes the whole store, ignoring the prefix — [conventions.md](conventions.md)) |

Tag groups must be **bounded by their nature** (`user:{id}:teams`), never by
table size (`teams`). A tag whose membership grows with the table is the bug —
on Redis, `tags()->flush()` **deletes every member** (chunked, blocking the
single-threaded server), so a million-member tag is a self-inflicted outage.

## Rule: every cached entry has a TTL; `forever()` is banned

Set a TTL on every write. With explicit invalidation, TTL is not the freshness
mechanism — it is the **backstop** that heals a missed/raced/failed invalidation
(and, with version keys, reclaims orphaned generations). `forever()` removes that
backstop: a single missed invalidation becomes permanent stale data, and on a
generational store orphans never reclaim. Truly-immutable reference data may use
a long TTL — still not `forever`.

## Versioned group caching (opt-in: large or mass invalidation)

When one event invalidates a **large or unbounded** set you cannot cheaply
enumerate — a mass import, a wholesale reference-data republish (pricing/tax/
flags), a per-tenant reset, a deploy that changes cached *shape* — do not delete
N keys. Make them unreachable in O(1) by bumping a version embedded in the key.
For a single entity or a small bounded group, stay on `forget`/`tags`.

### Rule: the version lives in the key; invalidate-all is one `INCR`

Keys read as `vehicles:v{N}:...`; to invalidate the whole group, increment the
version. Old entries are orphaned and reclaimed by TTL + the cache's
[`allkeys-lru`](conventions.md). Cost is constant regardless of group size — the
only mechanism that survives "a million" or "all of it". Version keys also
**close the cache-aside stale-set race for free**: a slow reader's late write
lands under the old version, a namespace nobody reads after the bump.

### Rule: the version counter lives in the database

The counter must be **durable and monotonic**, so it must **not** live on the
`allkeys-lru` cache instance — LRU is licensed to evict it (and a snapshot
restore rolls it back), and a counter that resets to a colliding generation
serves stale silently. Keep it in a `cache_versions(name, version)` table, read
once per request (a request-scoped memo, **not** `Cache::memo()`).

```php
interface VersionCounter
{
    public function current(CacheGroup $group, ?string $scope = null): int;
    public function bump(CacheGroup $group, ?string $scope = null): int; // INCR, in the domain tx
}
```

### Rule: group names are a backed enum, never literals

A `CacheGroup` enum is the typed registry shared by the read (key-building) and
the write (the bump) — the [`QueueName` rule](../queues/conventions.md) applied to
cache groups. It carries `versionKey(?scope)` (a scope id yields per-tenant
groups) and `ttl()`, and stays thin ([../enums/conventions.md](../enums/conventions.md)).

### Rule: build versioned keys only through the trait

A `VersionedCache` interface + `CachesVersioned` trait
(`@phpstan-require-implements`, mirroring
[`ProjectsToData`](../queries/conventions.md)) is the **sole** key path —
version always injected, `flexible()` + TTL always applied, repopulation
lock-protected (below). Add it only to a query that participates in a versioned
group; single-entity reads stay on plain `forget` keys.

## Rule: single-flight the repopulation; warm only known query-shaped paths

After a key expires — or a version bump empties a whole namespace — concurrent
misses stampede the DB. Defenses, in order:

- **Per-key `lock()` single-flight (primary).** The first miss takes the lock and
  does the one DB read; concurrent misses wait and read the result. No
  enumeration; the herd collapses to one query per key. **`Cache::flexible()`
  does not single-flight a *cold* miss** (its lock only guards the deferred
  stale-refresh), so the trait must wrap cold repopulation in a `lock()`.
- **`flexible()` (SWR) for expiry of a stale-tolerable hot key** — serves the
  stale value while one task refreshes. Useless right after a version bump (the
  new namespace is empty — there is no stale value to serve).
- **Warm only known query-shaped paths** (listing page 1, homepage) in the bump
  job, rate-limited. **Never** warm "the hot subset of records" — that
  re-introduces the enumeration problem version keys exist to avoid; the long
  tail is handled by single-flight, which warms each key once on first access.

## Edge cases

- **Hot key saturating one node.** Replicate the value across N sub-keys
  (`key:{0..N-1}`, reader picks one) to spread load — rare; every copy must then
  be invalidated.
- **Negative entries.** A create must forget the tombstone for the new id
  ([reads.md](reads.md)).

## Checklist

- Invalidation lives in `Invalidate*Cache` classes, triggered from actions;
  never observers/events/queries.
- Delete, never update.
- Redis deletes/jobs fire after commit; the DB version bump fires inside the
  transaction.
- Mechanism matches blast radius; tags bounded by nature; never `Cache::flush()`
  to invalidate.
- Every entry has a TTL; `forever()` is banned.
- Large/mass invalidation uses a version key (`INCR`), the counter in the DB,
  group names a `CacheGroup` enum, keys built only through the trait.
- Repopulation is single-flighted via `lock()`; warming limited to known
  query-shaped paths.
