# Cache runtime

The cache as infrastructure: which store, which connection, which eviction
policy, what may be serialized — plus the framework's own operational caches,
which are a different concern entirely. Strategy lives in
[../patterns/caching.md](../patterns/caching.md); mechanics in
[reads.md](reads.md) and [invalidation.md](invalidation.md). Verify config keys
against Laravel docs before use.

## Rule: separate stores by eviction needs — cache, locks, counters, queues do not share

Each has a different durability requirement, so each gets its own home:

| Concern | Store | Policy | Why |
|---|---|---|---|
| Cache data | dedicated Redis instance | `allkeys-lru` | evictable by design; LRU is the memory backstop for orphaned/cold entries |
| Atomic locks | Redis (`default` connection) | `noeviction` | an evicted lock breaks mutual exclusion → breaks single-flight and `withoutOverlapping` |
| Version counters | the **database** | — | no eviction, no snapshot rollback ([invalidation.md](invalidation.md)) |
| Queues / sessions | their own store | `noeviction` | LRU would evict jobs/sessions |

A separate Redis *database* (DB 1) on a shared instance is **not** enough —
`maxmemory-policy` is per-instance, so the cache's `allkeys-lru` would evict
locks/jobs sharing the instance. The cache needs its own instance.

**Why:** the entire freshness model assumes the cache may lose any entry at any
time (TTL + LRU is the backstop). Locks and version counters assume the
opposite — they must **not** vanish, or mutual exclusion and generation
identity break silently. Co-locating them under one eviction policy makes one of
the two assumptions false.

## Rule: objects are cached directly (`serializable_classes => true`)

The project caches `Data`/value objects, models, and collections **directly**,
so `config/cache.php` sets `serializable_classes => true` — Laravel serializes on
write and unserializes on read ([reads.md](reads.md)). This is a deliberate
ergonomics-over-surface tradeoff: it reopens PHP's unserialize surface, so it
relies on the **cache store being trusted infrastructure** (anyone who can write
to Redis can inject objects). Two consequences are managed, not ignored:

- **Deploy-shape brittleness.** A serialized object whose class gains/loses/renames
  a property can fatal or mis-hydrate on read — bump the group version on any
  deploy that changes a cached class's shape ([invalidation.md](invalidation.md))
  so old payloads are never read back.
- **No secret-bearing object on a path a response can echo** — the response
  boundary still ships a `Data` object ([../security/output.md](../security/output.md)).

## Rule: `Cache::flush()` is a maintenance/test operation, not an invalidation tool

`flush()`/`clear()` wipe the **entire** store and **ignore the cache prefix**, so
on any shared store they delete other data too. Use it only for an authorized,
logged, rate-limited admin "clear everything" (safe precisely because the cache
instance is dedicated) or in test teardown — never to invalidate application
data ([invalidation.md](invalidation.md)).

## Operational caching (boot speed, not data freshness)

`config:cache` / `route:cache` / `view:cache` / `event:cache` (run together by
`php artisan optimize`) cache the framework's **boot artifacts** — a deploy
concern, unrelated to the data caching above.

- **Production** runs `optimize` on deploy; **local** does not — a cached config
  silently masks `.env` changes (clear with `optimize:clear`).
- Two code-shape constraints follow, owned elsewhere: **call `env()` only in
  `config/*`** (cached config returns `null` for `env()` elsewhere —
  [../security/secrets.md](../security/secrets.md)) and **no closures in routes**
  (uncacheable — [../http/conventions.md](../http/conventions.md)).
- Do not conflate `cache:clear` (the data store) with `optimize:clear` (boot
  artifacts).

## Rate limiting (uses the cache store, not a caching pattern)

`RateLimiter` and the `throttle` middleware are backed by the cache store
(atomic `increment` + locks) but are a **throttling** concern, not read-caching —
noted here only because they share infrastructure. Their counters tolerate
`allkeys-lru` eviction (a reset just restarts a window), so they may sit on the
cache instance; keep them off the lock/version-counter stores above.

## Checklist

- Cache data on a dedicated `allkeys-lru` Redis instance; locks on a `noeviction`
  store; version counters in the DB; queues/sessions separate.
- `serializable_classes => true`; objects cached directly; class-shape-changing
  deploys bump the group version; no secret-bearing object on a response path.
- `Cache::flush()` reserved for admin-clear / test teardown, never invalidation.
- Operational caches run in production (`optimize`), not local; `env()` only in
  config; no route closures.
- Rate-limiter state kept off the lock/version-counter stores.
