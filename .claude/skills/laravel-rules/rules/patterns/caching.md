# Caching (pattern)

An **optional** technique — opted into per case (`patterns/`, see
[../architecture/placement.md](../architecture/placement.md)), never on by
default. A cache is a derived copy of data the database already owns: every
entry is a freshness liability and a memory cost. Reach for it only when a read
proves hot *and* expensive enough to repay the machinery — the same posture as
[queues](../queues/conventions.md) ("escalate only when the workload proves
it").

This file is the **decision map**: *should I cache, and which shape?* The
mechanics live in the `cache/` leaves — [reads](../cache/reads.md) (decorator
queries, payload), [invalidation](../cache/invalidation.md) (delete-on-write,
versioning, stampede, TTL), and [runtime](../cache/conventions.md) (stores,
policies, operational caching). Verify cache API syntax against Laravel docs
before use.

## Decision: cache, or leave it on the database?

Do not cache until a read is **both** hot (high frequency) **and** costly (an
expensive query/computation, or a slow external call). A correctly indexed query
under moderate traffic does not need a cache — it needs the index
([../database/performance.md](../database/performance.md)). Caching a cheap or
cold read buys a freshness bug and a memory cost for no gain.

**Why:** every entry can go stale, must be invalidated, and consumes memory that
evicts other entries. That cost is repaid only when the read is genuinely hot
and expensive. Premature caching trades a simple correctness model for a hard
one (invalidation) with nothing to show for it.

## Decision: which read/write topology?

Start with the default; escalate only when the workload forces it. Each entry
names *what it is | when | the failure it introduces*.

**Reads — default: cache-aside (look-aside).** The app checks the cache; on a
miss it reads the DB, populates, and returns — the
[decorator query](../cache/reads.md). *Read-through* (a library loads on miss) is
the same read topology, app-orchestrated: the decorator **is** our read-through,
so we never reach for a separate read-through library.

**Writes — default: write-around + cache-aside.** Write to the DB,
**invalidate** the affected keys ([delete, never update](../cache/invalidation.md)),
and let the next read lazily refill. Safe by construction: the DB is always the
source of truth and the cache never holds a write the DB does not.

- **Write-through** (write DB *and* update the cache synchronously) — *when:* you
  must read-your-own-write instantly and the value is cheap/safe to set.
  *Failure:* it **conflicts with delete-not-update** (concurrent writers can
  leave the older value resident) and pollutes the cache with maybe-never-read
  data. Prefer delete; reach for write-through only in a narrow
  read-your-writes case.
- **Write-behind** (ack the caller, persist later) — two very different shapes:
  - *Persist via a **durable queue** job* — **not lossy** (durability lives in
    the queue); it is simply **async writing**. Fine when the DB may lag the
    cache, provided the job is idempotent and order-safe
    ([../queues/conventions.md](../queues/conventions.md)).
  - *Buffer writes **in the cache** and flush in batches* — **lossy**: an acked
    write is gone if the cache node dies before the flush. Allowed **only** for
    disposable derived data (view/like counters, metrics) via Redis atomic
    `INCR`, coalescing many increments into one DB write, with the loss
    explicitly accepted — mechanics in
    [../cache/write-behind.md](../cache/write-behind.md).
  - **Durable/domain data is never write-behind** — orders, payments, anything
    the business cannot lose. The DB stays the source of truth.

**Stale-while-revalidate** (`Cache::flexible()`) is a freshness tactic layered on
cache-aside, not a separate topology — see
[stampede](../cache/invalidation.md).

## Decision: which layer?

Caching is a stack; each layer's rule owns its concern.

- **Application data (Redis)** — the core, and the default home:
  [reads](../cache/reads.md) + [invalidation](../cache/invalidation.md) +
  [runtime](../cache/conventions.md).
- **HTTP responses** — in an authed app, cache *data*, not responses;
  full-response caching is public/anonymous only
  ([../http/conventions.md](../http/conventions.md)).
- **In-process / L1** — per-request memoization only
  ([../cache/reads.md](../cache/reads.md)).
- **Framework operational** (config/route/view) — a boot/deploy concern, not
  data freshness ([../cache/conventions.md](../cache/conventions.md)).

## Checklist

- Caching is opt-in and justified — the read is both hot and expensive; a
  cheap/cold read is left on the (indexed) DB.
- Reads use cache-aside via a decorator query; no separate read-through library.
- Writes default to write-around + cache-aside (write DB → invalidate → lazy
  refill).
- Write-through only for a narrow read-your-writes case (it fights
  delete-not-update).
- Write-behind only via a durable queue (async) or for disposable counters
  (lossy, accepted) — never for durable/domain data.
- The correct layer's rule is followed (data / HTTP / L1 / operational).
