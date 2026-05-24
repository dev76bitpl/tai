# Queues (runtime)

The queue runtime: connection config, queue organization, retries, failed
jobs, and throughput controls. Infrastructure/runtime concern (see
[../architecture/placement.md](../architecture/placement.md)). Distinct
from [../jobs/conventions.md](../jobs/conventions.md) (the job class's
internals) and from dispatch timing/origin
([../architecture/transactions.md](../architecture/transactions.md)).

## Rule: jobs run on a persistent connection, never `sync` in production

Production uses a durable queue connection (Redis/database/SQS), not the
`sync` driver.

**Why:** `sync` runs the job inline, defeating the point — and breaking
the after-commit guarantee, since there is no queue to defer to.

## Rule: enable `after_commit` in the connection config, not only in code

The after-commit dispatch rule ([../architecture/transactions.md](../architecture/transactions.md))
is *enforced* by setting `'after_commit' => true` on the queue connection
in `config/queue.php` — not left to each job/dispatch to remember.

**Why:** code declaring "dispatch after commit" is a per-call promise that
one forgotten `dispatch()` breaks. Setting it on the connection makes
after-commit the default for every dispatch, so the guarantee holds even
when a caller forgets. The principle lives in `transactions.md`; the
config switch that makes it project-wide lives here.

```php
// config/queue.php — connection default
'redis' => [
    'driver' => 'redis',
    'after_commit' => true,
    // ...
],
```

## Rule: queue names are a backed enum, never string literals

Every queue name is a case on a string-backed enum
([../enums/conventions.md](../enums/conventions.md)); jobs and workers
reference the enum, never a magic string.

**Why:** string literals drift — a typo (`'notifcations'`) silently
routes a job to a queue no worker consumes, and the set of queues is
undiscoverable. An enum makes the queue topology a single typed source of
truth that workers and dispatchers share.

```php
enum QueueName: string
{
    case WebInteractive = 'web-interactive'; // dispatched from web requests
    case Notifications  = 'notifications';
    case MassUpdates    = 'mass-updates';    // bulk, long-running
    case Heavy          = 'heavy';           // memory-intensive
}

ProcessSignup::dispatch($signupId)->onQueue(QueueName::Notifications->value);
```

## Rule: organize queues by operational profile, with a worker pool per profile

Do not pile every job on `default`. Segment queues so jobs with different
operational profiles never share a worker, splitting along:

- **Priority** — latency-sensitive vs background; high-priority queues are
  consumed first.
- **Duration** — short jobs vs long-running, so a slow job does not starve
  fast ones (and each pool gets a fitting `timeout`).
- **Memory** — memory-heavy jobs on their own queue, whose workers run
  lower concurrency / higher memory limits.
- **Execution context** — jobs spawned from **web requests** (user-facing,
  must stay responsive) kept apart from **mass updates / batch** work that
  can run on dedicated workers.

Each profile that matters gets its own enum case **and** its own worker
configuration (concurrency, `--timeout`, memory limit, balancing).

**Why:** a single shared queue couples unrelated workloads — one bulk
mass-update or a memory-heavy job behind which a user's interactive
notification waits. Segmenting by profile lets each class of work get
workers tuned to it, so latency, timeouts, and memory are right per queue
instead of a lowest-common-denominator compromise.

## Rule: every job declares retry and timeout limits

Set explicit `$tries` (or `retryUntil()`), `$backoff`, and `$timeout` per
job — do not rely silently on global defaults.

**Why:** without bounds, a job that always fails retries forever and a
hung job blocks a worker indefinitely. Explicit limits make the failure
mode a visible design decision.

```php
final class ProcessSignup implements ShouldQueue
{
    public int $tries = 5;
    public int $timeout = 30;

    /** @return list<int> seconds between attempts */
    public function backoff(): array
    {
        return [10, 30, 60];
    }
}
```

## Rule: design jobs to be idempotent and retry-safe

A job may run more than once (retry, at-least-once delivery). Re-running a
completed job must not double-charge, double-send, or double-write — guard
with a status check or a unique constraint (the DB-constraint backstop in
[../architecture/invariants.md](../architecture/invariants.md)).

**Why:** at-least-once is the queue's contract, not an edge case; a job
assuming exactly-once will eventually duplicate its effect.

## Rule: failed jobs are captured and visible

Implement `failed(Throwable $e)` for cleanup/notification on terminal
failure, and monitor the `failed_jobs` store. A job that exhausts its
retries must not vanish silently.

## Decision: a plain queued job, or a throughput control?

Start with a plain `ShouldQueue` job; add a control only when the workload
proves it needs one:

- **`ShouldBeUnique`** — concurrent duplicates would conflict (two syncs
  for one account).
- **Rate limiting / `WithoutOverlapping`** — a downstream API has limits,
  or a resource must not be processed concurrently.
- **Batching** — many jobs form one logical unit with a completion
  callback (a bulk import that reports when done).

**Why:** these add coordination cost and state; applying them by default
is premature. Add the specific control the workload requires, not all up
front.

## Edge cases

- **Payloads.** Jobs carry IDs and re-fetch; never serialize models or
  secrets ([../jobs/conventions.md](../jobs/conventions.md),
  [../data-objects/serialization.md](../data-objects/serialization.md),
  [../security/secrets.md](../security/secrets.md)).
- **Horizon.** On Redis, define a worker pool per queue (`maxProcesses`,
  balancing, memory) matching the profiles above; keep the dashboard
  behind [authorization](../security/authorization.md).

## Checklist

- Durable connection in production (never `sync`).
- `after_commit => true` set on the connection config, not left to code.
- Queue names are a string-backed enum; no string literals at call sites.
- Queues segmented by priority / duration / memory / execution context,
  each with its own worker pool (Decision above) — not all on `default`.
- Each job sets explicit `$tries`/`retryUntil`, `$backoff`, `$timeout`.
- Jobs are idempotent / retry-safe (at-least-once assumed).
- `failed()` handles terminal failure; `failed_jobs` is monitored.
- Throughput controls added only when the workload requires them.
- No models or secrets in payloads.
