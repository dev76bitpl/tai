# Folder Structure

Governs where application classes live on disk. This is settled,
codebase-wide **policy** (see [placement.md](placement.md)).

## Rule: keep Laravel folders flat

Use Laravel's conventional top-level folders with a flat structure. Do
not create nested domain folders.

**Why:** nesting by domain (`app/Actions/User/CreateUser.php`) forces a
taxonomy decision on every new class, fragments related code across
deep trees, and makes discovery depend on guessing the hierarchy. Clear,
verb-first class names make a flat folder self-indexing.

```php
// Good
app/Actions/CreateUser.php
app/Queries/ListUsersQuery.php

// Bad
app/Actions/User/CreateUser.php
app/Queries/User/ListUsers.php
```

Rely on class names for discoverability, not folder nesting.

## Rule: nesting is allowed only from the exception registry

A folder may nest **only** when listed below. This registry is the
single source of truth — do not invent ad-hoc nesting. To add an
exception, add it here with its justification.

| Path | Why the nesting is allowed |
|------|----------------------------|
| `app/Data/Casts/` | Spatie Laravel Data casts are a distinct, reusable mechanism, not data objects themselves; grouping keeps `app/Data/` readable. |
| `app/Data/Transformers/` | Same as casts — transformers are infrastructure for data objects, not data objects. |
| `app/Queries/Concerns/` | Query traits (`TransformsToData`) and the `ReadsRecords` typing-seam interface are reusable infrastructure *for* queries, not query classes; grouping them in `Concerns/` keeps `app/Queries/` to the queries. Block-internal seams, deliberately **not** hoisted to `app/Contracts/` (see Rule: contracts below). See [../queries/conventions.md](../queries/conventions.md). |

**Why a registry:** "flat unless justified" only holds if exceptions
are enumerated in one place. An open-ended "nest when it feels right"
rule decays back into deep trees.

## Rule: general contracts live in `app/Contracts`; block-internal seams stay with their block

A contract (interface) consumed **across** the codebase — a strategy
interface ([../patterns/pluggable.md](../patterns/pluggable.md)), a port
wrapping a package ([../packages/policy.md](../packages/policy.md)) — lives
in the flat top-level `app/Contracts/`. A contract that exists only as the
**internal seam of one building block** stays co-located with that block,
never hoisted into `app/Contracts/`: the query typing seam `ReadsRecords`
lives in `app/Queries/Concerns/` ([../queries/conventions.md](../queries/conventions.md)),
because separating it from the queries it serves buys nothing.

```php
// Good — a cross-cutting contract, flat under app/Contracts
app/Contracts/PaymentGateway.php

// Good — a query-internal seam stays with its block
app/Queries/Concerns/ReadsRecords.php

// Bad — a one-block seam hoisted into the global contracts folder
app/Contracts/ReadsRecords.php
```

**Why:** this is the placement test applied to interfaces
([placement.md](placement.md)) — a cross-block contract is shared policy and
earns a shared home; a one-block seam is internals and belongs with its
block. An `app/Contracts/` that swallows both turns every building block's
private seam into apparent public surface.

## Checklist

- `app/Actions`, `app/Queries`, `app/Services`, etc. are flat.
- New class uses a clear, verb-first or operation-specific name instead
  of a folder to disambiguate.
- Any nested path appears in the exception registry above; if not,
  flatten it or add a justified registry entry.
- General/shared contracts (strategy interfaces, package ports) live in
  flat `app/Contracts/`; a contract that is one building block's internal
  seam stays co-located (e.g. `app/Queries/Concerns/`), not in `app/Contracts/`.
