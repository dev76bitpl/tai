# Write-behind counters (disposable data only)

The one place a write goes to the cache *first* and the database *later*: a
**write-absorbing counter** (views, likes, impressions, metrics) where the write
rate would hammer the DB and a small amount of loss is acceptable. This is the
lossy escape hatch named in the [caching topology menu](../patterns/caching.md);
everything else writes to the DB first (write-around + cache-aside).

It earns its place by **coalescing**: thousands of increments collapse into one
periodic DB write. That is the whole point — and the whole risk.

## Rule: write-behind is for disposable derived data only

Use it only for counters/metrics whose loss the business tolerates. **Durable or
domain data is never write-behind** — orders, balances, anything you cannot lose.
If you cannot lose it but still want the write off the request path, that is not
this pattern: it is **async writing via a durable queued job**
([../queues/conventions.md](../queues/conventions.md)), where durability lives in
the queue, not the cache.

**Why:** an acked write that lives only in the cache is gone if the node dies (or
the key is evicted) before it flushes. The "ack" is a promise the cache cannot
keep for durable data.

## Rule: the action bumps the counter; the DB write is deferred

The write path performs an atomic cache increment and returns — no DB write. As
with all caching, an [action](../actions/conventions.md) owns the write.

```php
final class RecordVehicleView
{
    public function handle(int $vehicleId): void
    {
        Cache::increment("vehicle:{$vehicleId}:views"); // coalesces in Redis; no DB write
    }
}
```

## Rule: a scheduled job flushes by delta — decrement, never reset

A scheduled, idempotent job persists each dirty counter as **one** DB increment,
then **decrements the cache key by the amount it flushed** — never sets it to `0`.

```php
final class FlushVehicleViewCounts implements ShouldQueue
{
    public function handle(): void
    {
        foreach ($this->dirtyKeys() as $vehicleId => $key) {
            $delta = (int) Cache::get($key, 0);
            if ($delta === 0) continue;

            Vehicle::whereKey($vehicleId)->increment('views', $delta); // one coalesced write
            Cache::decrement($key, $delta);                            // preserve mid-flush increments
        }
    }
}
```

**Why:** resetting to `0` drops every increment that arrived between the read and
the reset — a lost update. Decrementing by exactly the flushed delta keeps those.
The flush is a plain scheduled job, not an after-commit side effect (there is no
domain transaction), and is idempotent — a delta of `0` is a no-op.

## Rule: pick the counter store by how much loss you tolerate

- **Loss truly disposable** → the counter may live on the `allkeys-lru` cache
  instance; accept that eviction drops un-flushed increments, and **flush often**
  to bound the window.
- **Loss should be bounded** → put the counter on the `noeviction` store
  ([conventions.md](conventions.md)) and flush periodically — which nudges it from
  "lossy" toward a durable buffer.

## Rule: a read is the DB base plus the live cache delta

A displayed total is the persisted column **plus** the un-flushed cache delta
(or, for a hot live count, just the cache value). Do not read the DB column alone
between flushes — it lags by the current delta.

## Edge cases

- **Eviction loss is silent.** If the count must never *under*-report, do not put
  it on an evicting store; use the `noeviction` store and short flush intervals.
- **Backfill / reconciliation.** A periodic recompute from the source-of-truth
  table corrects any drift from lost increments, if the metric warrants it.
- **Per-entity fan-out.** Track the set of dirty keys (a Redis set the increment
  also writes to) so the flush job does not scan the whole keyspace.

## Checklist

- Used only for disposable derived counters/metrics; durable/domain data goes to
  the DB first (or async via a durable queue job, not this).
- Write path is an action doing `Cache::increment`; no DB write inline.
- A scheduled, idempotent job flushes one coalesced DB increment per key and
  **decrements by the flushed delta**, never resets to `0`.
- Counter store chosen by loss tolerance (LRU + frequent flush vs `noeviction`).
- Reads combine the DB base with the live cache delta.
