# Package policy — when to reach for a package

Cross-cutting policy: the criteria for adding a third-party dependency vs
building in-house. The approved *list* lives in [catalog.md](catalog.md);
this file owns the *decision*. See
[../architecture/placement.md](../architecture/placement.md).

## Rule: never outsource the core domain

A package may handle a generic, undifferentiated concern (HTTP client,
data objects, PDF generation). It must never own your **domain logic** —
the actions, invariants, and rules that *are* the product. Those stay in
your code ([../actions/conventions.md](../actions/conventions.md),
[../architecture/invariants.md](../architecture/invariants.md)).

**Why:** the domain is the one thing no package can do for you and the one
thing you must be free to change. Outsourcing it couples your product's
core to someone else's release cadence and assumptions — the most
expensive lock-in there is.

## Decision: add a package, or build it?

Reach for a package when the concern is generic and the package is
healthy; build when it is small or close to the domain. Weigh:

1. **Is it core domain?** If yes → build it (rule above). Stop here.
2. **Maintenance / health** — active commits, recent releases, real
   adoption, compatible with the project's Laravel/PHP versions. An
   abandoned package is a liability you inherit.
3. **Scope fit** — does it do roughly what you need without dragging in a
   framework-within-the-framework? A package used for 10% of its surface
   is mostly risk.
4. **Lock-in / exit cost** — how hard to remove later? Prefer packages
   that sit behind a seam you control (next rule).
5. **Security surface** — every dependency is code running with your
   privileges. More transitive deps = more surface; weigh it.

Trivial, stable, or domain-adjacent needs (a small helper, a value object)
are cheaper to write than to depend on. A substantial generic concern with
a healthy package is cheaper to adopt than to maintain.

**Why:** a dependency is a permanent cost (upgrades, CVEs, breaking
changes), not a one-time save. The decision is whether that ongoing cost
beats owning the code — which it does for big generic concerns and does
not for small or domain-close ones.

## Decision: use the package directly, or wrap it behind a contract?

- **Directly** — framework-blessed, pervasive packages that are effectively
  part of the stack (Spatie Data, Saloon). Wrapping them buys nothing.
- **Behind a contract/service** — a package at an external boundary
  (payment gateway, SMS, search) where you may swap providers, or one
  whose API you do not want leaking through the app. Depend on an
  interface ([../patterns/pluggable.md](../patterns/pluggable.md)) and
  keep the package in one adapter.

**Why:** wrapping costs an indirection, so it should buy real
swappability or isolation. A ubiquitous stack package needs neither; a
swappable external provider needs both.

## Rule: introducing a dependency is a reviewed decision

A new package is added deliberately — justified against this Decision and
recorded in [catalog.md](catalog.md), not slipped in to solve one ticket.

**Why:** dependencies accrete silently and are far harder to remove than
to add. A moment of review at add-time is the cheapest point to say no.

## Checklist

- Core domain is built in-house, never delegated to a package.
- New dependency justified against the Decision (health, scope, lock-in,
  security) — and not a domain-adjacent thing cheaper to write.
- Pervasive stack packages used directly; external-boundary packages
  wrapped behind a contract ([../patterns/pluggable.md](../patterns/pluggable.md)).
- The choice is recorded in [catalog.md](catalog.md).
