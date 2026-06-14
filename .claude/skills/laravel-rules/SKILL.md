---
name: laravel-rules
description: Applies Francisco Barrento's Laravel, Pest, model, and naming conventions that override generic Laravel guidance. Use when writing, editing, reviewing, or refactoring Laravel PHP code in this project — actions, queries, models, data/value objects, migrations, jobs, events, HTTP, and Pest tests.
license: MIT
metadata:
  author: Francisco Barrento
---

# FBarrento Laravel Rules

## STOP — how this skill works

This file is a ROUTER, not the rules. Reading it does NOT mean you have
"applied the skill." The actual rules live in `rules/**/*.md` and are NOT in
your context yet.

Before you write or edit ANY class you MUST, in order:

1. Identify the building block you are touching (Action, Query, Model, Data
   object, Value object, Enum, Exception, Job, …).
2. Open and READ IN FULL the matching rule file(s) from the Routing Table
   below. The table gives pointers only — never rule content. You cannot
   satisfy a rule you have not read.
3. Before emitting any code in your reply, output a line:
   `Rules consulted: <comma-separated relative paths of every rule file you read>`
   If that line would be empty, you are NOT ready to write code — return to
   step 2.
4. After writing the class, re-read the `## Checklist` section of each rule
   file you used and confirm every item against your code. Report any item
   you cannot satisfy instead of silently skipping it.

Hard rules:
- Do not work from memory, from the Routing Table labels, or from a single
  nearby example. Nearby code may itself violate these rules.
- If you are about to create or edit a class without the governing rule file
  in context, STOP and read it first.
- This applies to EVERY agent: orchestrators, sub-agents, and you. A sub-agent
  that writes code must perform steps 1–4 itself; it may not assume the
  orchestrator did.

Higher priority than `.agents/skills/laravel-best-practices` when both
apply. Use Laravel and Pest documentation for API syntax; use these
files for project code shape.

## Glossary

The building-block vocabulary this skill reasons in — Action, Query,
Service, Model, Data object, Value object, Enum, Exception, Job — is
defined once in [LANGUAGE.md](LANGUAGE.md). Use those terms exactly; rule
files carry the grammar and link back to the definition. Name the
**architecture** from `LANGUAGE.md`; name the **domain** from the product's
own language (see [naming](rules/naming/conventions.md)).

## Placement test (read before adding a rule)

Each rule has one canonical home, decided by
[rules/architecture/placement.md](rules/architecture/placement.md):

1. **Internals of one class type?** → that building-block folder.
2. **A settled global rule the whole codebase obeys?** → `architecture/`.
3. **An optional technique chosen per case?** → `patterns/`.

"It's a pattern" is never a placement reason — CQRS is a pattern but is
mandatory policy (`architecture/`); pipeline is a pattern you opt into
(`patterns/`). Cross-cutting rules live in one home; other folders
link-stub to it, never restate.

Each rule file follows: **Rule → Why → Good/Bad → Edge cases →
Checklist**, with a **Decision** section where a rule is a choice.

## Routing Table

The right column is a POINTER. It tells you which file applies — never what the
rule says. You must open the file.

| You are touching… | Read (in full) |
|---|---|
| An Action class | `rules/actions/conventions.md` |
| A Query class | `rules/queries/conventions.md` |
| A Model | `rules/models/conventions.md` |
| A Data object | `rules/data-objects/conventions.md`, `rules/data-objects/spatie-laravel-data.md`, `rules/data-objects/serialization.md` |
| Inertia page data | `rules/data-objects/inertia-page-data.md` |
| A Value object | `rules/value-objects/conventions.md` |
| An Enum | `rules/enums/conventions.md` |
| An Exception | `rules/exceptions/conventions.md` |
| A Job | `rules/jobs/conventions.md` |
| An Event | `rules/events/conventions.md` |
| An Observer | `rules/observers/conventions.md` |
| Controllers / HTTP / form requests | `rules/http/conventions.md` |
| A migration or DB schema | `rules/database/migrations.md`, `rules/database/schema.md` |
| DB performance / indexes / N+1 | `rules/database/performance.md` |
| Large / high-volume tables | `rules/database/large-tables.md` |
| Append-only history tables | `rules/database/history.md` |
| Engine-specific DB work | `rules/database/mysql.md` or `rules/database/postgres.md` |
| Queues / queued work | `rules/queues/conventions.md` |
| Caching (any) | `rules/patterns/caching.md`, then `rules/cache/conventions.md` |
| Cache reads | `rules/cache/reads.md` |
| Cache invalidation | `rules/cache/invalidation.md` |
| Write-behind counters | `rules/cache/write-behind.md` |
| Logging | `rules/logs/conventions.md` |
| Anything touching secrets | `rules/security/secrets.md` |
| Authorization | `rules/security/authorization.md` |
| Mass assignment | `rules/security/mass-assignment.md` |
| Output / response shaping | `rules/security/output.md` |
| Naming a class or variable | `rules/naming/conventions.md` |
| Adding or choosing a package | `rules/packages/policy.md`, `rules/packages/catalog.md` |
| Writing Pest tests | `rules/testing/conventions.md` |
| Writing `arch()` tests | `rules/testing/architecture.md` |
| The pipeline pattern | `rules/patterns/pipeline.md` |
| The pluggable / strategy pattern | `rules/patterns/pluggable.md` |
| Class shape / final / strict types | `rules/architecture/classes.md` |
| Comments / when to comment | `rules/architecture/comments.md` |
| Where a class should live | `rules/architecture/placement.md`, `rules/architecture/structure.md` |
| Read vs write separation | `rules/architecture/cqrs.md` |
| Dependency injection | `rules/architecture/dependency-injection.md` |
| Imports / FQCN | `rules/architecture/imports.md` |
| Creating classes via artisan | `rules/architecture/scaffolding.md` |
| Transaction boundaries | `rules/architecture/transactions.md` |
| Enforcing invariants | `rules/architecture/invariants.md` |
| Dates / Carbon | `rules/architecture/dates.md` |

Building-block vocabulary (Action, Query, Model, …) is defined in
[LANGUAGE.md](LANGUAGE.md). Use those terms exactly.

## How to apply

1. Read any relevant `docs/adr/` before touching code. Name architecture
   terms from `LANGUAGE.md` — never an `_Avoid_` alias — and domain terms
   from the product's own language.
2. Follow the STOP gate at the top of this file. It is not optional.
3. Run the Placement Test before adding a NEW rule; give it one canonical home.
4. When rules conflict, this skill wins over `.agents/skills/laravel-best-practices`.
5. Verify Laravel/Pest API syntax with `search-docs` before using framework APIs.

## Enforcement is mechanical

Mechanically checkable rules in this skill MUST be backed by committed Pest
`arch()` tests in the consuming project (see `rules/testing/architecture.md`).
An agent that ignores a rule then produces a red `php artisan test` and must
fix it. Before considering a backend change done, run the test suite.

Minimum `arch()` coverage every consuming project should commit:
- All app classes are `final` (except `abstract` bases).
- `declare(strict_types=1)` in every PHP file.
- `App\Actions\*` does not depend on the Eloquent query builder directly.
- Models define no query scopes.
- Naming conventions per `rules/naming/conventions.md`.
