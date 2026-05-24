# Transactions & side-effect timing

The transactional integrity of writes and their side effects. One
coupled story: side effects must not fire until the write commits, and
only actions own writes — so only actions dispatch. Settled,
codebase-wide **policy** (see [placement.md](placement.md)). This is the
canonical home; `actions/`, `jobs/`, and `events/` link here.

## Rule: single-write actions need no transaction

A single-responsibility action that performs exactly one database write
does not wrap it in a transaction.

**Why:** a lone write is already atomic. Wrapping it adds ceremony and
falsely signals a multi-step workflow.

## Rule: multi-write orchestrators wrap in a transaction

An orchestrator action that performs more than one write wraps the
workflow in a single `DB::transaction()`.

**Why:** partial application of a multi-step workflow leaves the domain
in an invalid state. The transaction makes the workflow all-or-nothing.

```php
// Good — orchestrator, multiple writes
public function handle(RegisterOrganizationData $data): Organization
{
    return DB::transaction(function () use ($data): Organization {
        $organization = $this->createOrganization->handle($data->organization());
        $this->attachUserToOrganization->handle($data->owner(), $organization);
        return $organization;
    });
}
```

`DB::transaction()` is declared `@throws Throwable` (it rethrows the
closure and can throw on deadlock/rollback), so the wrapping method
declares `@throws Throwable` in its docblock alongside its business
exceptions — see [../exceptions/conventions.md](../exceptions/conventions.md).

## Rule: dispatch jobs and emit events only after commit

Jobs and events fire only **after** the surrounding transaction commits
— never mid-transaction.

**Why:** a job or listener may run (on a fast queue, or synchronously)
before the transaction commits, and read rows that don't exist yet — or
the transaction may roll back after the side effect already fired,
acting on data that was never persisted.

```php
// Good
DB::afterCommit(fn () => ProcessSignup::dispatch($waitlistSignup->id));
// or a job declared with: public bool $afterCommit = true;

// Bad — dispatched inside the transaction
DB::transaction(function () use ($signup) {
    $signup->save();
    ProcessSignup::dispatch($signup->id); // may run before commit
});
```

## Rule: dispatch jobs only from actions

Jobs are dispatched from **actions**, not from controllers, commands,
queries, or other jobs.

**Why:** dispatching is a side effect of a business operation, and
business operations live in actions (CQRS, see [cqrs.md](cqrs.md)).
Centralizing dispatch in actions keeps the "what fires when" decision in
one layer and preserves the after-commit guarantee, which only the
write owner can honor.

## Checklist

- Single-write actions use no transaction.
- Multi-write orchestrators wrap the workflow in one transaction.
- Jobs/events fire via `DB::afterCommit` or `$afterCommit = true`.
- Jobs are dispatched from actions only.
