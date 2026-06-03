# Cache reads (application data)

How a read is served from cache: the decorator query, what may be stored, and
the per-request layer. The read side of [caching](../patterns/caching.md); the
write/freshness side is [invalidation](invalidation.md), the infrastructure is
[runtime](conventions.md).

## Rule: a cached read is a decorator over a query, never a cache call inside the query

A cached read is a separate `*CacheQuery` that **decorates** the plain
[query](../queries/conventions.md) — `TeamCacheQuery` wraps `TeamQuery` (the
Eloquent read), alongside `TeamDBQuery` (the DB-facade sibling). The base query
stays cache-agnostic and testable uncached; the decorator adds cache-aside. This
is the [pluggable](../patterns/pluggable.md) pattern: one read contract, a cached
implementation.

```php
final class TeamCacheQuery
{
    public function __construct(private readonly TeamQuery $inner) {}

    /** the public key vocabulary — referenced by the invalidator, never a literal */
    public static function key(int $userId): string { return "user:{$userId}:teams"; }

    public function forUser(int $userId): TeamData
    {
        return Cache::flexible(self::key($userId), [60, 300],
            fn () => TeamData::from(($this->inner)()->forUser($userId)->firstOrFail()),
        );
    }
}
```

**Why:** decoration keeps cache concerns out of the read logic, lets the base
query be tested without a cache, and gives the cache-query a single home that
**owns its key vocabulary** — which the write-side invalidator references rather
than re-deriving ([invalidation.md](invalidation.md)).

## Rule: populating the cache on a read miss is allowed (the CQRS carve-out)

CQRS says [a query never mutates state](../architecture/cqrs.md) — but that
protects **domain/persistence** state. Writing a derived copy into the cache on
a miss is transparent: re-reading returns the same logical value, the business
world is unchanged. So a cache-query may populate on a miss. What it may **not**
do is invalidate — that is a write triggered by a domain change, and lives on
the write side ([invalidation.md](invalidation.md)).

## Rule: cache objects directly; keep models off the response path

The project sets `serializable_classes => true` ([conventions.md](conventions.md)),
so you cache `Data`, `DataCollection`, models, Eloquent collections, and
paginators **directly** — Laravel serializes on write and unserializes on read,
no encode/decode layer. Two cautions remain, neither about serialization:

- **A cached model lazy-loads on access.** An unserialized model comes back with
  `exists = true`; touching a relation it did not carry will query — or fail
  outside a request. Eager-load the relations you need *before* caching, or cache
  a `Data` projection instead of the model.
- **The response boundary still demands a `Data` object.** A cached *model* may
  serve an internal consumer, but never crosses to a response — that is the
  output-safety rule ([../security/output.md](../security/output.md)), unchanged
  by what the cache holds.

Because a serialized object embeds its class shape, **a deploy that changes a
cached class** (adds/removes/renames a property) can mis-hydrate old payloads —
bump the group version on such a deploy so they are never read back
([invalidation.md](invalidation.md)).

## Rule: negative results are cached through a null-safe envelope

`Cache::remember()`/`flexible()` cannot cache `null` — a stored null is
indistinguishable from a miss, so the callback re-runs every time. To cache a
miss (and stop cache penetration by repeated lookups of absent keys), wrap the
value in an envelope so even null is stored. Give negatives a **short TTL**, and
**invalidate the negative entry on insert** — the create action forgets the
tombstone.

```php
$stored = Cache::flexible($key, $ttl, fn () => ['v' => $produce()]); // null-safe
return $stored['v'];
```

## Rule: in-process (L1) caching is per-request only

Memoize within a request via `Cache::memo()` or a request-scoped object —
**never** a `static`/global that survives across requests in a long-lived worker
(Octane, queue workers), which would serve one request's value to thousands more
with no invalidation path. L2 (Redis) is the shared, coherent tier; do not put a
cross-request cache in front of it without a short TTL. Clear the memo when the
same request invalidates the key.

## Rule: cache external-service reads at the service boundary

A [service](../architecture/cqrs.md) wrapping a third-party API may cache its
**reads** (same TTL discipline). But you **cannot invalidate a third party** —
freshness rests on **TTL** plus conditional requests
(`ETag`/`If-Modified-Since` → `304`) where the API supports them. Never cache a
write or an auth/token call.

## Edge cases

- **Cached model relations.** `exists = true` after unserialize; a relation not
  carried at cache time lazy-loads (or fails) on access. Eager-load before
  caching, or cache a `Data` projection.
- **Class-shape changes on deploy.** Bump the group version
  ([invalidation.md](invalidation.md)) so stale-shaped serialized payloads are
  never read back.
- **Response boundary.** A cached model may go to an internal consumer; the
  response edge still ships a `Data` object
  ([../security/output.md](../security/output.md)).

## Tests

- Test the inner query and the decorator **separately**; the decorator test
  injects a **call-counting** fake inner query and asserts
  miss-computes-once / hit-does-not-recompute, with `freezeTime()`/`travel()` for
  TTL.
- The `array` store keeps the **live object** (no serialize/unserialize), so it
  will not catch a serialization or class-shape problem — round-trip the cached
  shapes (models with relations, `Data`, paginators) against **real Redis**
  where that fidelity matters ([../testing/conventions.md](../testing/conventions.md)).

## Checklist

- Cached reads are `*CacheQuery` decorators over plain queries; the base query
  stays uncached and testable.
- Cache is populated on a miss (allowed); never invalidated from the read side.
- Objects cached directly (`serializable_classes => true`); relations eager-loaded
  before caching a model; no model crosses to a response.
- Class-shape-changing deploys bump the group version.
- Negatives cached via the null-safe envelope (short TTL, tombstone forgotten on
  insert).
- L1 is per-request only; no cross-request static cache.
- External-service reads cached at the boundary with TTL + conditional requests;
  no writes/auth cached.
- Decorator tested with a counting fake; serialized shapes round-tripped against
  real Redis.
