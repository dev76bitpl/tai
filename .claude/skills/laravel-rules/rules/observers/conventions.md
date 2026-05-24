# Observers (guardrail)

Model observers — framed as a **guardrail**. Consistent with the
no-model-magic stance (explicit reads, no query scopes), observers are
discouraged: they hide side effects behind Eloquent lifecycle hooks. This
file documents what to do instead and the narrow cases where an observer
is tolerable. Building-block folder (see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: do not put side effects in model observers

Do not react to Eloquent lifecycle events (`creating`, `created`,
`saved`, `deleted`, …) by running domain side effects — sending mail,
dispatching jobs, mutating other models, calling services. Put the side
effect where it belongs:

- **Domain side effect** → the [action](../actions/conventions.md) that
  owns the write does it explicitly, in order.
- **Async/external work** → a [job](../jobs/conventions.md) the action
  dispatches after commit.

(Events are *also* a guardrail here, not the fallback — see
[../events/conventions.md](../events/conventions.md).)

**Why:** an observer fires on *any* save from *any* code path —
factories, seeders, tinker, an unrelated action — so the side effect runs
in contexts you never intended and in an order you do not control.
Reading the action tells you nothing about what the observer will do.
Testing anything that touches the model now drags in the observer's
effects. This is the single biggest source of "why did that happen?" in a
Laravel codebase, which is exactly the risk the project avoids.

```php
// Bad — hidden side effect on every save, from any path
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

## Decision: is an observer ever acceptable?

Only for a side-effect-free, persistence-level concern that is intrinsic
to *every* write of the model and has no domain meaning:

- **Tolerable** — deriving a stored column purely from the model's own
  attributes (a `slug` from a `name`, setting a `uuid` on `creating`).
  Pure, no I/O, no other models, no dispatch.
- **Not acceptable** — anything with a side effect or a collaborator:
  mail, jobs, events, touching other records, calling a service.

Even for the tolerable case, prefer doing it in the action or a cast/
mutator if it has any domain nuance; the observer is only for the truly
mechanical, universal-to-every-write derivation.

**Why:** a pure attribute derivation is safe to run on every save because
it has no observable effect beyond the row itself. The moment an observer
does something *other code can notice*, it becomes the hidden side effect
this guardrail forbids.

## Edge cases

- **Cascading deletes / cleanup.** Model this as an explicit action (or a
  database/foreign-key strategy per
  [../database/migrations.md](../database/migrations.md)), not a `deleting`
  observer that fans out writes.
- **Audit/timestamps.** Framework-level concerns (`timestamps`, dedicated
  audit packages) are fine; hand-rolled audit logic with I/O is not — that
  is an action or a job.

## Checklist

- No domain side effects in observers — actions own them, jobs run the
  async/external ones (events are not the fallback).
- The only observer logic present is a pure, side-effect-free attribute
  derivation intrinsic to every write (Decision above).
- Deletes/cascades are explicit actions or DB constraints, not observers.
- After-commit/dispatch rules still apply
  ([../architecture/transactions.md](../architecture/transactions.md)).
