# Package catalog — which packages to use

The project's approved packages per concern. Reach for a catalogued
package before evaluating alternatives; add or change entries through the
[policy.md](policy.md) Decision. This is a living reference — keep it in
sync as choices are made.

## Approved packages

| Concern | Package | Why | Notes |
|---------|---------|-----|-------|
| Data objects / DTOs | `spatie/laravel-data` | Typed payloads, casting, mapping, request hydration | Used directly. Mechanics: [../data-objects/spatie-laravel-data.md](../data-objects/spatie-laravel-data.md) |
| Outbound HTTP integrations | `saloonphp/saloon` (+ `saloonphp/laravel-plugin`) | Structured API integrations as connectors/requests | Wrap behind a service/contract. See the `saloon-integration` and `saloon-laravel-integration` skills |
| Testing | `pestphp/pest` | Expressive test syntax, the project's test runner | Used directly. Conventions: [../testing/conventions.md](../testing/conventions.md) |
| Queue monitoring | `laravel/horizon` | Redis queue dashboard, worker pools, metrics | Where Redis is the queue driver; see [../queues/conventions.md](../queues/conventions.md) |

> Add a row only after the package clears the [policy.md](policy.md)
> Decision (core-domain check, health, scope, lock-in, security), and
> record *why* — the rationale is the point of the catalog.

## Disallowed / discouraged

Record here any package deliberately rejected and the reason, so the
decision is not relitigated each time someone reaches for it. (None
recorded yet — add as decisions are made.)

A standing example from elsewhere in the skill: do **not** adopt a package
to own domain logic — actions and invariants stay in-house
([policy.md](policy.md)).

## Checklist

- The concern has a catalogued package; it is used before alternatives
  are evaluated.
- A new entry was justified via [policy.md](policy.md) and carries its
  rationale.
- Rejected packages are recorded with the reason.
