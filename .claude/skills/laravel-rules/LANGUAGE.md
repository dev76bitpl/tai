# Language

The vocabulary this skill reasons in. These are the **building-block class
types** a Laravel codebase is made of — the words you use when you name a
file, a variable, or a PR. Use them exactly; reach for the listed term
before inventing a synonym, and never use an `_Avoid_` alias.

This file is the **canonical home for each term's definition** (the *what*
and its aliases). The `rules/` files own the *grammar* — the `handle()`
shape, the suffix rule, the cast discipline — and link back here for the
definition rather than restating it
([rules/architecture/placement.md](rules/architecture/placement.md)).

Two distinct vocabularies are in play, and they must not blur:

- **This file (`LANGUAGE.md`)** names the **architecture** — Action, Query,
  Data object. It ships with the skill and is the same in every project.
- **The product's own language** names the **domain** — Signup, Invoice,
  Vehicle — and differs per project.

So you write *"the `CreateSignup` **action**"* — `Signup` is the domain term,
`action` from here. Domain naming is governed by
[rules/naming/conventions.md](rules/naming/conventions.md).

## Terms

Each term is defined once below — what it **is**, the rule file that owns
its *grammar*, and the `_Avoid_` aliases never to use for it.

| Term | Definition (what it *is*) | Grammar | `_Avoid_` |
|---|---|---|---|
| **Action** | A class encapsulating one business operation / state mutation, exposing a single `handle()`. The **write** side of CQRS; named verb-first (`CreateOrganization`). | [actions](rules/actions/conventions.md) | service, handler, manager, processor; an `Action` suffix |
| **Query** | A fluent, read-only object composing Eloquent reads, initialised in `__invoke()`, `Query`-suffixed. The **read** side of CQRS — the only place reads are composed. | [queries](rules/queries/conventions.md) | repository, finder, fetcher, reader; "query" for the raw Eloquent builder |
| **Service** | A class that talks to **external systems only** (APIs, SDKs, webhooks, remote sources). `Service`-suffixed. Not a home for in-app logic — that is an Action. | [cqrs](rules/architecture/cqrs.md) | "service" for in-app business logic; manager, helper, gateway |
| **Model** | An Eloquent record mapping to a table — persistence + relationships, no workflows. No `Model` suffix; named for the concrete thing (`WaitlistSignup`). | [models](rules/models/conventions.md) | entity, record; a `Model` suffix |
| **Data object** | An immutable, typed shape travelling between layers (HTTP → action → job → response), enforced by the analyzer. Spatie laravel-data. Serializes to a `*Data` type at the Inertia seam → frontend *generated type* (**inertia-rules**). | [data-objects](rules/data-objects/conventions.md) | array, payload, params, struct; a Model where a typed cross-layer shape belongs |
| **Value object** | A small, `readonly`, self-validating type modelling a *value with rules* (`Money`, `Email`), compared by contents, not identity. Cannot exist invalid. | [value-objects](rules/value-objects/conventions.md) | a bare scalar where rules apply; an Enum (closed set, not open value) |
| **Enum** | A **backed** PHP enum (string by default) modelling a *fixed, closed set*. No `Enum` suffix. | [enums](rules/enums/conventions.md) | a pure/unbacked enum; a constants class; an `Enum` suffix |
| **Exception** | A **specific** business exception, one per distinct domain failure, named for it (`DuplicateWaitlistSignupException`). | [exceptions](rules/exceptions/conventions.md) | a bare `Exception`/`RuntimeException`/`LogicException` for a domain failure; `null`/`false` to signal failure |
| **Job** | A queued-execution wrapper with no business logic — injects an Action and calls its `handle()`. | [jobs](rules/jobs/conventions.md) | business logic in a job; "task", "worker" |
| **Event** · **Observer** *(guardrails)* | **Discouraged.** Event only as a package extension point / event-bus message; Observer only for pure attribute derivation. Side effects → Action (required step) or Job (async/external). | [events](rules/events/conventions.md), [observers](rules/observers/conventions.md) | events/observers as the default way to wire side effects |

## Relationships

- **CQRS** is the spine: **Action** writes, **Query** reads, **Service**
  reaches outside. A caller knows from the type it holds whether invoking it
  changes state.
- An **Action** takes a **Data object** in and returns a **Model** or
  **Data object**; it enforces invariants by throwing a specific
  **Exception**.
- A **Job** holds no logic — it dispatches an **Action**.
- A **Model** casts attributes to **Value objects** and **Enums**.
- A **Data object** is the layer-crossing shape; at the Inertia boundary it
  becomes a frontend **generated type** (defined by **inertia-rules**).

## Rejected framings

- **"Service" as the home for business logic** (the generic Laravel "service
  layer"). Here business logic is an **Action**; "service" is reserved for
  the external-systems boundary.
- **Suffixing for its own sake** (`CreateOrganizationAction`,
  `WaitlistSignupModel`). Actions and Models carry no type suffix; the
  folder and shape already say what they are. Only Query/Service/Test do.
