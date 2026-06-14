# Observers (guardrail)

> **[Observer](../../LANGUAGE.md)** is defined in `LANGUAGE.md` (a guardrail term); this file owns the grammar.

Model observers and Eloquent model events — framed as a **guardrail**.
Consistent with the no-model-magic stance (explicit reads, no query
scopes), they are **not used in application code**: they hide behavior
behind Eloquent lifecycle hooks that fire implicitly, from every path, and
*don't* fire on the paths that matter most. This file says what to do
instead, the one place they're legitimate (package authorship), and the
decision tree that draws the line. Building-block folder (see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: no model lifecycle hooks in application code

Do not put behavior in a model observer, an `#[ObservedBy]` class, a
`static::booted()` lifecycle closure, or a `$dispatchesEvents` mapping —
anything that reacts to `creating`, `created`, `saving`, `updated`,
`deleting`, …. Put the behavior where it is visible and runs on **every**
write path:

- **Domain side effect** → the [action](../actions/conventions.md) that
  owns the write does it explicitly, in order.
- **Async/external work** → a [job](../jobs/conventions.md) the action
  dispatches after commit
  ([../architecture/transactions.md](../architecture/transactions.md)).
- **A required or derived value on every row** → set it in the action's
  write payload and back it with a database constraint; for bulk writes the
  action sets it per row
  ([../actions/conventions.md](../actions/conventions.md),
  [../database/schema.md](../database/schema.md)).

(Events are *also* a guardrail, not the fallback — see
[../events/conventions.md](../events/conventions.md).)

```php
// Bad — hidden, fires on every save from any path, skipped by bulk writes
#[ObservedBy(OrganizationObserver::class)]
class Organization extends Model { /* ... */ }

class OrganizationObserver
{
    public function created(Organization $organization): void
    {
        SendWelcomeEmail::dispatch($organization->id); // invisible to the action
    }
}

// Good — the action owns it, explicitly and after commit
final class RegisterOrganization
{
    public function handle(RegisterOrganizationData $data): Organization
    {
        $organization = Organization::query()->create($data->toArray());
        DB::afterCommit(fn () => SendWelcomeEmail::dispatch($organization->id));

        return $organization;
    }
}
```

## Why: a hook is both too eager and too lazy

**It fires when you don't want it.** An observer runs on *any* save from
*any* code path — factories, seeders, tinker, an unrelated action, a test.
The behavior runs in contexts you never intended, in an order you do not
control, and by default **mid-transaction**: a `created` hook that
dispatches a job can be picked up by a worker before `COMMIT` (model not
found), or send mail and then have the transaction roll back. Reading the
action tells you nothing about what fires — the single biggest source of
"why did that happen?" in a Laravel codebase.

**It doesn't fire when you need it.** Model events come only from a
hydrated model's `save()`/`delete()`. They fire on **none** of these —
each goes straight to the query builder and never hydrates a model:

`Model::insert()` · `DB::table()->insert()` · mass `Model::query()->update()` ·
`upsert()` · `insertOrIgnore()` · `withoutEvents()` · `saveQuietly()` · raw SQL.

So any invariant you "guarantee" in a hook is silently false on exactly the
bulk/eventless paths a large app relies on
([../database/large-tables.md](../database/large-tables.md),
[../actions/conventions.md](../actions/conventions.md)). Even `HasUuids`
and timestamps are **not** observer logic — Laravel sets them inline in
`performInsert()`, which is why they survive `saveQuietly()` yet *still*
skip `insert()`/`upsert()`. A hand-rolled `creating` hook to set a `uuid`
or `slug` is a worse version of that, broken on the same paths.

## Decision: should this live in a model lifecycle hook?

In **application** code the answer is **no** — it goes in the action. The
tree is the reasoning; walk it in order and the first **stop** is your
answer.

1. **Does it do I/O or dispatch anything?** (write another table, cache,
   queue a job, send mail, call an HTTP API, broadcast) → **stop.** It is a
   side effect: the [action](../actions/conventions.md) owns it (a required
   step), or a [job](../jobs/conventions.md) runs it after commit. A hook
   would fire it mid-transaction, from seeders and tests, and skip it on
   bulk writes.

2. **Does it read or mutate any row other than the one being saved?**
   (relations, counters, aggregates) → **stop.** Cross-aggregate
   consistency is the action's transaction to own; a hook splits one
   invariant across two invisible places and can recurse (`save()` inside a
   `saved` handler loops; `saveQuietly()` "fixes" it only by silencing
   *every* observer).

3. **If the hook never ran, could a row be persisted invalid or incomplete
   through *any* write path** — `insert`, `upsert`, mass `update`,
   `withoutEvents`, query builder, raw SQL? → **stop.** The value must hold
   where no event fires: set it in the action's payload (bulk writes too)
   and back it with a DB constraint
   ([../database/schema.md](../database/schema.md)). A hook gives false
   confidence.

4. **Is it a pure, deterministic derivation of *this row's own*
   attributes, with no I/O?** → in app code, **still set it in the action**
   (or a cast/mutator if it is presentation of a stored value). The
   convenience of a hook does not buy back the invisibility, and gate 3
   already showed it cannot be the guarantee.

**Exception — package authorship.** If you are writing a reusable
*package* (not application code), model events are the only decoupled seam
into a host app you don't control, so an observer is legitimate — but it
must run after commit (`ShouldHandleEventsAfterCommit`) and queue its work
([../queues/conventions.md](../queues/conventions.md)). This exception does
not transfer to application code, which owns every call site.

## When a hook *is* the tool (and why that isn't you)

| Legitimate use | Why it isn't application code |
|---|---|
| Key / timestamp assignment (`HasUuids`, `timestamps`) | a framework concern, set inline in `performInsert()` — you never write it |
| Package extension points / decoupling | only a *package* needs a seam into an app it cannot edit |
| Audit / search-index / cache sync via observer | legitimate only when *packaged*, after-commit, and queued — and it still misses bulk paths, so it is never your invariant |

## Edge cases

- **Cascading deletes / cleanup.** An explicit action (or a foreign-key
  strategy per [../database/migrations.md](../database/migrations.md)) —
  never a `deleting` observer that fans out writes.
- **Normalization** (downcase an email, trim) → set it in the action, or a
  cast/mutator on the stored value — not a lifecycle hook.
- **Audit/timestamps.** Framework `timestamps` and dedicated, packaged
  audit tools are fine; hand-rolled audit logic with I/O is an action or a
  job.

## Checklist

- No observers, `#[ObservedBy]`, `booted()` lifecycle closures, or
  `$dispatchesEvents` in application code.
- Side effects live in actions (required steps) or jobs (async/external),
  dispatched after commit — events are not the fallback.
- Required/derived values are set in the action's write payload and backed
  by DB constraints; bulk writes set them per row
  ([../actions/conventions.md](../actions/conventions.md)).
- The only lifecycle hooks in the codebase are framework-provided
  (`HasUuids`, timestamps) or inside a package you ship — after-commit and
  queued.
