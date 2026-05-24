# Events (guardrail)

Internals of event classes and listeners — framed as a **guardrail**.
This project avoids an event/listener architecture. Events are a special
case with two narrow justifications; everywhere else, side effects are
explicit. *When and from where* an event (if used) is emitted — after
commit, from an action — is governed by
[../architecture/transactions.md](../architecture/transactions.md).
Building-block folder (see [../architecture/placement.md](../architecture/placement.md)).

## Rule: default to actions and jobs, not events

Do not reach for events to wire up side effects. Express them directly:

- **A required step** (the operation depends on it finishing) → the
  orchestrator [action](../actions/conventions.md) calls the next action.
  Explicit, traceable, ordered.
- **Slow or external work** (email, third-party API, outbound publish) →
  a [job](../jobs/conventions.md) dispatched from the action, after commit.

**Why:** an event/listener layer scatters "what happens when X" across
invisible listeners. A reader of the action cannot see what fires; a
listener can fail silently and break the operation; ordering between
listeners is implicit; and the indirection is the prime source of
unintended side effects — the risk this project avoids at all cost. An
explicit call or a dispatched job keeps the whole behavior in front of
you.

## Decision: is an event actually justified?

Only two cases justify emitting an event. If neither holds, use an action
or a job (rule above).

1. **A reusable package offering extension points.** You are building a
   package and want the host application to extend behavior *without*
   modifying your code. Events are the package's public extension API.
   Then **document each event thoroughly** — name, payload, exactly when
   it fires, after-commit semantics, and any ordering guarantees — because
   it is now part of your public contract.

2. **Event-bus integration (Kafka and similar).** And even here, check
   that you need an event at all: a single outbound publish is just a
   **job that sends the payload to the bus** — explicit and simpler. Reach
   for a Laravel event only when you genuinely need in-process fan-out to
   several independent consumers, not for one outbound write.

**Why:** both cases are about a boundary you do not control — a host app
(case 1) or another system (case 2). Inside your own application you own
every call site, so the indirection buys nothing and costs traceability.
The bus caveat matters because "we use Kafka" is not itself a reason for
Laravel events; the job already crosses the boundary.

## Rule: if you do emit an event, it is an immutable past-tense fact

A justified event records something that **already happened**, named in
the past tense (`OrganizationRegistered`), with a `readonly` payload that
carries IDs and scalars — not Eloquent models (queue-safe; see
[../data-objects/serialization.md](../data-objects/serialization.md)).

```php
final class OrganizationRegistered
{
    public function __construct(
        public readonly string $organizationId,
    ) {}
}
```

## Rule: listeners are thin and delegate to actions

A listener translates the event and calls an
[action](../actions/conventions.md); it holds no business logic. Slow or
external listeners implement `ShouldQueue` and run after commit
([../architecture/transactions.md](../architecture/transactions.md)),
within the [queue rules](../queues/conventions.md).

**Why:** business logic reachable only by firing an event is untestable on
its own and invisible to a reader of the action — the same reason jobs
stay thin.

## Edge cases

- **Ordered reactions.** If two reactions must happen in a set order, they
  are not independent — make them explicit steps in the action, never two
  racing listeners.
- **Eloquent model events** (`created`, `updated`, …). Reacting to these
  is the observer anti-pattern — see the guardrail in
  [../observers/conventions.md](../observers/conventions.md).

## Checklist

- Side effects expressed as actions (required steps) or jobs (async/
  external) — not events — unless a Decision case applies.
- An emitted event is justified by case 1 (package extension point) or
  case 2 (event bus, and a job genuinely won't do).
- Package-extension events are documented as public contract.
- Any event is past-tense, `readonly`, carries IDs/scalars — no models.
- Listeners are thin, delegate to actions, and queue when slow/external.
- Emission timing/origin deferred to
  [../architecture/transactions.md](../architecture/transactions.md).
