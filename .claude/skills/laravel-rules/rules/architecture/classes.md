# Classes & strict types

Two baseline declarations every PHP file and class carries. Settled,
codebase-wide **policy** (see [placement.md](placement.md)).

## Rule: every PHP file declares `strict_types`

`declare(strict_types=1);` is the first statement in every PHP file —
after `<?php`, before the namespace.

**Why:** without it, PHP silently coerces scalars at call boundaries — a
`"1"` becomes `1`, a `1.9` truncates to `1`, a bool slips into an int
parameter — so a type mismatch produces wrong data instead of an error.
Strict types turn that into a `TypeError` at the boundary, where it
belongs. One line per file makes the type hints the rest of these rules
rely on actually load-bearing.

```php
<?php

declare(strict_types=1);

namespace App\Actions;
```

## Rule: classes are `final` by default

Every class is `final` unless it is *explicitly* designed for extension —
which, in this codebase, means an `abstract` base. There is no third
category: a class is either `final` or `abstract`, never a concrete class
left open "just in case."

**Why:** `final` makes inheritance a deliberate, opt-in decision instead
of an accident. It frees you to change a class's internals without fear of
a hidden subclass depending on them (the fragile-base-class problem), and
it pushes the composition these rules already assume — actions inject
actions, services wrap connectors, behavior is shared via
[traits/contracts](../patterns/pluggable.md), not inheritance. Leaving
classes open invites the inheritance trees this architecture avoids.

```php
// Good — concrete class is final
final class CreateOrganization { /* ... */ }

// Good — a base meant for extension is abstract, not final
abstract class WaitlistException extends Exception {}

// Bad — concrete class left open with no reason
class CreateOrganization { /* ... */ }
```

## Rule: prefer composition over inheritance

Reuse and extend behavior by **composing** — injecting a collaborator,
wrapping it, applying a trait, or depending on a contract — never by
subclassing one of your own concrete classes. When you want to build on a
class's behavior, inject it and add around it; don't extend it. This is
the principle `final`-by-default exists to enforce.

**Why:** inheritance is the most rigid form of reuse — a subclass binds to
its parent's internals and to a single axis of variation, and a change to
the parent silently reshapes every child (the fragile-base-class problem).
Composition keeps each unit small, swappable, and testable alone: an
orchestrator [action](../actions/conventions.md) *injects* the actions it
coordinates, a service *wraps* a connector, shared behavior is a trait or
a [contract + in-memory impl](../patterns/pluggable.md). Reaching for
`extends` to share code is what produces the inheritance trees this
architecture avoids.

```php
// Good — compose: the orchestrator injects what it coordinates
final class RegisterOrganization
{
    public function __construct(
        private readonly CreateOrganization $createOrganization,
        private readonly AttachUserToOrganization $attachUserToOrganization,
    ) {}
}

// Bad — inherit to reuse: couples to CreateOrganization's internals
final class RegisterOrganization extends CreateOrganization { /* ... */ }
```

**This is not "never extend anything."** Extending a **framework base
designed for it** is correct and expected — `Data` (Spatie), `Model`
(Eloquent), `Request`/`Connector` (Saloon), `Exception`. The rule forbids
building inheritance among **your own** classes to share code, not using a
package's intended extension point.

## Edge cases

- **Abstract base classes** (e.g. the per-domain base exception in
  [../exceptions/conventions.md](../exceptions/conventions.md)) are
  `abstract` — extension is their purpose. They are the only non-`final`
  classes.
- **Models, data objects, actions, queries, jobs, controllers** — all
  `final`. This codebase has no model inheritance; reuse is via traits and
  composition, which `final` does not block.
- **Testing.** `final` does not impede testing here: the project doubles
  collaborators with **contracts + in-memory implementations**, not by
  subclassing/mocking concretes ([../testing/conventions.md](../testing/conventions.md)).
  "I need to extend it to test it" is a signal to extract an interface
  ([../patterns/pluggable.md](../patterns/pluggable.md)), not to drop
  `final`.
- **Need to extend a class you own?** Prefer composition or a shared
  contract. Drop `final` only when you deliberately design and document the
  extension point — at which point the base is usually `abstract`.

## Checklist

- Every PHP file opens with `declare(strict_types=1);` (before the
  namespace).
- Every concrete class is `final`; the only non-`final` classes are
  `abstract` bases designed for extension.
- Reuse achieved via composition / traits / contracts, not by leaving
  classes open.
- A "need to subclass to test" urge resolved by extracting a contract, not
  by removing `final`.
