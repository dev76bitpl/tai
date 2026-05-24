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

**Why a registry:** "flat unless justified" only holds if exceptions
are enumerated in one place. An open-ended "nest when it feels right"
rule decays back into deep trees.

## Checklist

- `app/Actions`, `app/Queries`, `app/Services`, etc. are flat.
- New class uses a clear, verb-first or operation-specific name instead
  of a folder to disambiguate.
- Any nested path appears in the exception registry above; if not,
  flatten it or add a justified registry entry.
