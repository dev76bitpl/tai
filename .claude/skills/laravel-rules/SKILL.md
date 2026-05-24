---
name: laravel-rules
description: Applies Francisco Barrento's Laravel, Pest, model, and naming conventions that override generic Laravel guidance. Use when writing, editing, reviewing, or refactoring Laravel PHP code in this project — actions, queries, models, data/value objects, migrations, jobs, events, HTTP, and Pest tests.
license: MIT
metadata:
  author: Francisco Barrento
---

# FBarrento Laravel Rules

Higher priority than `.agents/skills/laravel-best-practices` when both
apply. Use Laravel and Pest documentation for API syntax; use these
files for project code shape.

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

## Rule index

**Architecture** (mandatory, codebase-wide policy)
- [architecture/placement.md](rules/architecture/placement.md) — what goes where.
- [architecture/structure.md](rules/architecture/structure.md) — flat folders + nesting-exception registry.
- [architecture/cqrs.md](rules/architecture/cqrs.md) — actions write, queries read, services for external.
- [architecture/dependency-injection.md](rules/architecture/dependency-injection.md) — inject over facades; contextual attributes.
- [architecture/imports.md](rules/architecture/imports.md) — always import; no inline leading-backslash FQCN.
- [architecture/classes.md](rules/architecture/classes.md) — `declare(strict_types=1)` per file; classes `final` by default (only `abstract` bases aren't); prefer composition over inheritance.
- [architecture/scaffolding.md](rules/architecture/scaffolding.md) — always create classes via `php artisan make:*`; customize stubs for strict-types/`final`; concept→command catalog.
- [architecture/transactions.md](rules/architecture/transactions.md) — transaction boundaries; after-commit; dispatch jobs only from actions.
- [architecture/invariants.md](rules/architecture/invariants.md) — actions enforce invariants; throw specific business exceptions.
- [architecture/dates.md](rules/architecture/dates.md) — dates are always `CarbonImmutable`; global `Date::use`, `immutable_*` casts, reassign transforms.

**Patterns** (optional techniques)
- [patterns/pipeline.md](rules/patterns/pipeline.md) — staged, swappable workflows; stages wrap actions.
- [patterns/pluggable.md](rules/patterns/pluggable.md) — strategy / swappable impls; one interface, bound selection.

**Building blocks** (internals of one class type)
- [actions/conventions.md](rules/actions/conventions.md) — `handle()`, data-object inputs, simple-vs-orchestrator.
- [queries/conventions.md](rules/queries/conventions.md) — fluent read-only query objects; generic `QueriesRecords`/`ProjectsRecords` traits; model on write path, `toData()` on read path.
- [models/conventions.md](rules/models/conventions.md) — explicit casts, no scopes, no soft deletes, to-array test.
- [data-objects/conventions.md](rules/data-objects/conventions.md) — immutable typed payloads; create/update/response roles.
  - [data-objects/spatie-laravel-data.md](rules/data-objects/spatie-laravel-data.md) — `Optional`, mapping, casts/transformers, `toArray()` in actions.
  - [data-objects/serialization.md](rules/data-objects/serialization.md) — queue boundary; IDs not models; plain-DTO escape hatch.
- [value-objects/conventions.md](rules/value-objects/conventions.md) — immutable, self-validating, value equality; vs scalar/enum/data.
- [enums/conventions.md](rules/enums/conventions.md) — string-backed, no `Enum` suffix, model cast, thin (pure-of-case behavior).
- [exceptions/conventions.md](rules/exceptions/conventions.md) — specific business exceptions; static factory construction; map at boundary.
- [jobs/conventions.md](rules/jobs/conventions.md) — no business logic; inject actions.
- [events/conventions.md](rules/events/conventions.md) — guardrail: avoid events; actions/jobs instead; only for package extension points or event bus.
- [observers/conventions.md](rules/observers/conventions.md) — guardrail: no side effects in observers; actions/jobs instead; pure attribute derivation only.
- [http/conventions.md](rules/http/conventions.md) — thin controllers; form-request validation; response data objects for output.

**Infrastructure / runtime**
- [database/migrations.md](rules/database/migrations.md) — ordered-UUID PK, forward-only, always-constrained FKs, no cascades/defaults/DB-enums/soft-deletes.
- [database/schema.md](rules/database/schema.md) — portable types, NOT NULL default, constraints back invariants, money as integer cents.
- [database/performance.md](rules/database/performance.md) — index real patterns, no N+1, bound large reads.
- [database/large-tables.md](rules/database/large-tables.md) — online schema changes at scale; split add/backfill/constrain; lock timeouts.
- [database/history.md](rules/database/history.md) — append-only history is source of truth; latest-query indexing; order by date/ordered-id.
- [database/mysql.md](rules/database/mysql.md) · [database/postgres.md](rules/database/postgres.md) — engine specifics (charset/JSON/indexes/locking/online-DDL).
- [queues/conventions.md](rules/queues/conventions.md) — after_commit config, queue-name enum, profile-based organization, retries/failed jobs.
- [logs/conventions.md](rules/logs/conventions.md) — injected logger, structured context, level discipline; never log secrets.

**Security** (cross-cutting domain)
- [security/secrets.md](rules/security/secrets.md) — `#[\SensitiveParameter]`, never-log-secrets (canonical), config/serialization.
- [security/authorization.md](rules/security/authorization.md) — authorize at the boundary, not in actions; authz vs invariant.
- [security/mass-assignment.md](rules/security/mass-assignment.md) — data object is the allow-list; unguarded ok with an enforced boundary.
- [security/output.md](rules/security/output.md) — response data objects; keep `$hidden`/redacting cast for secrets.

**Cross-cutting**
- [naming/conventions.md](rules/naming/conventions.md) — class + variable naming.
- [packages/policy.md](rules/packages/policy.md) — never outsource the domain; add/build & wrap Decisions.
- [packages/catalog.md](rules/packages/catalog.md) — approved packages per concern (Spatie Data, Saloon, Pest, Horizon).

**Discipline**
- [testing/conventions.md](rules/testing/conventions.md) — Pest `test()`, `->and()`, structure mirror, in-memory services.

## How to apply

1. Identify the touched area and read the matching leaf file before editing.
2. Run the placement test before adding a *new* rule; put it in one home.
3. When rules conflict, this skill wins over `.agents/skills/laravel-best-practices`.
4. Check nearby files for current patterns, but do not copy ones that violate these rules.
5. Verify Laravel API syntax with `search-docs` before using framework APIs or attributes.
