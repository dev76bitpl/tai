# CQRS

The read/write boundary. Settled, codebase-wide **policy** — you never
decide "should this use CQRS?"; every class respects it (see
[placement.md](placement.md)). CQRS is a pattern by origin, but here it
is mandatory architecture, not an optional technique.

## Rule: separate writes (actions) from reads (queries)

- **Actions** contain business logic and state mutations. → `actions/`
- **Queries** contain read operations and read-specific composition. →
  `queries/`
- **Services** talk to external systems only (third-party APIs, SDKs,
  webhooks, remote data sources).

**Why:** mixing reads and writes behind one object hides intent and
makes side effects unpredictable. A caller should know from the type it
holds whether invoking it changes state.

```php
// Good — write
$user = $this->createUser->handle($createUserData);
// Good — read
$users = ($this->listUsersQuery)()->active()->get();

// Bad — a "service" that both reads and mutates domain state
$service->getOrCreateUser($email); // read or write? both?
```

Do not put state mutations in queries. Do not put internal business
workflows in services when an action is the correct home.

## Rule: reusable reads are query objects, never model scopes

Reusable read filters live in query objects under `app/Queries`, not in
Eloquent scopes. Scope mechanics live in [queries/](../queries/conventions.md);
this rule is the *boundary* — reads are explicit and traceable, with no
model-level query magic.

## Checklist

- State-changing workflows live in actions.
- Read-only operations live in queries.
- Services are used only for external integrations.
- No reusable read logic hidden in model scopes.
