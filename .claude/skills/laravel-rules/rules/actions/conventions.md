# Action Rules

> **[Action](../../LANGUAGE.md)** is defined in `LANGUAGE.md`; this file owns the grammar.

## Purpose

Actions encapsulate all business logic and state mutation workflows. Controllers, console commands, and jobs may depend on actions, but they must not implement business logic themselves.

Every action exposes a `handle()` method:

```php
final class CreateOrganization
{
    public function handle(CreateOrganizationData $createOrganizationData): Organization
    {
        // ...
    }
}
```

Name actions with a verb first, then the affected subject or subjects. Use names like `RegisterOrganization`, `CreateOrganization`, and `AttachUserToOrganization`.

## Inputs

Avoid passing Eloquent models directly into actions. Pass purpose-built data objects instead so the action receives an explicit command-shaped input.

- Good: `CreateWaitlistSignupData $createWaitlistSignupData`
- Avoid: `User $user` when a data object can describe the operation.

Use names that describe the input value, not generic names like `$data` when a precise data object name exists.

## Reads: inject a query — never read Eloquent inline

An action's only direct database operation is the **write**
(`create`/`update`/`delete`). Every **read** it needs — loading the
aggregate it is about to mutate, an existence check backing an invariant —
goes through an **injected [query](../queries/conventions.md)**. An action
never writes `Model::query()->find()/where()/get()`.

```php
final class UpdateArticle
{
    public function __construct(
        private readonly FindArticleQuery $findArticle,   // reads go through it
    ) {}

    public function handle(UpdateArticleData $data): Article
    {
        $article = ($this->findArticle)()->forId($data->id)->firstOrFail(); // READ via query
        $article->update($data->except('id')->toArray());                    // WRITE

        return $article;
    }
}
```

A create needs no read, so it goes straight to the write:

```php
final class CreateArticle
{
    public function handle(CreateArticleData $data): Article
    {
        return Article::query()->create($data->toArray());   // write only
    }
}
```

**Why:** keeping reads in injected queries makes the query layer the sole
home of composed Eloquent reads (CQRS, [../architecture/cqrs.md](../architecture/cqrs.md)),
so an action's collaborators are explicit and its reads are reusable and
testable in isolation. Loading the aggregate *inside* the action is also
where a `lockForUpdate()` belongs when the write is contended
([../database/mysql.md](../database/mysql.md) /
[postgres.md](../database/postgres.md)) — the query returns the model on
its write-path terminal ([../queries/conventions.md](../queries/conventions.md)),
the action mutates it. The id reaches the action **inside the data
object** (a typed identifier), not as a passed model.

## Rule: bulk and eventless writes set their own values

When an action writes in bulk — `insert()`, `upsert()`, `insertOrIgnore()`,
a mass `update()`, or raw SQL — it goes straight to the query builder and
**bypasses the model layer entirely**: no model events fire, `HasUuids`
does not run, casts and mutators do not apply, and `created_at`/`updated_at`
are not filled. So the action must set, **per row**, everything a single
`save()` would have set for it:

- the **primary key** — `Str::uuid7()` (time-ordered, [../database/migrations.md](../database/migrations.md));
- any **derived column** (slug, normalized value) — computed in PHP into the row;
- the **timestamps**.

```php
final class ImportOrganizations
{
    public function handle(ImportOrganizationsData $data): void
    {
        $now = now();

        $rows = $data->organizations->map(fn (NewOrganizationData $org): array => [
            'id'         => Str::uuid7()->toString(),   // HasUuids does NOT run here
            'name'       => $org->name,
            'slug'       => Str::slug($org->name),       // no mutator/observer fires
            'created_at' => $now,
            'updated_at' => $now,
        ]);

        Organization::query()->insert($rows->all());     // chunk for large sets
    }
}
```

**Why:** a derived value or key that an [observer](../observers/conventions.md)
or `HasUuids` would set on a `save()` is silently skipped on these paths —
leaving a `NOT NULL` column to throw mid-insert, or a nullable one to fill
with `NULL` across every row. The only place a value is guaranteed on every
write path is the action's payload (and a DB constraint as backstop,
[../database/schema.md](../database/schema.md)). Large backfills run the
same way from a chunked job ([../database/large-tables.md](../database/large-tables.md),
[../database/performance.md](../database/performance.md)).

## Decision: single-responsibility vs orchestrator

Two action shapes. Choose by responsibility and number of writes:

- **Single-responsibility** — one focused operation. Reach for this by
  default.
- **Orchestrator** — coordinates a workflow, usually injecting other
  actions. Reach for this when the operation composes ≥2 actions or
  spans multiple writes.

When an orchestrator's steps are conditional, reorderable, or
independently swappable, consider structuring it with the
[pipeline pattern](../patterns/pipeline.md) rather than inline calls.

Transaction timing for multi-write workflows is governed by
[architecture/transactions.md](../architecture/transactions.md) — single
writes need no transaction; orchestrators wrap multiple writes in one.

## Dependencies

Actions may be dependencies of controllers, console commands, jobs, and
other orchestrator actions.

Services must not contain internal business logic. Use services only for
external systems; actions may depend on services when they need to call
third-party APIs or remote systems.

Controllers, console commands, and jobs validate or prepare input, call
an action, then return/output/dispatch. They must not enforce domain
workflows directly.

## Domain invariants

Actions are the enforcer of domain invariants, and they signal a
violation with a specific business exception. The *who/when/how* is
governed by [architecture/invariants.md](../architecture/invariants.md)
and [exceptions/](../exceptions/conventions.md) — this folder does not
restate it.

## Checklist

- Action has a `handle()` method.
- Action input is a data object where operation input is needed (the id
  travels in the data object, never a passed model).
- Reads go through an injected query; the action's only direct DB op is
  the write — no `Model::query()->find/where/get` inline.
- Bulk/eventless writes (`insert`/`upsert`/mass-`update`/raw) set the
  `uuid`, derived columns, and timestamps per row — the model layer is
  bypassed.
- Action shape chosen via the Decision above (single vs orchestrator).
- Transaction + invariant rules deferred to their canonical homes
  (linked above), not re-decided here.
- Controllers, commands, and jobs delegate business logic to actions.
