# Placement — what goes where

The rule that decides which folder a rule belongs in. Read this before
adding any new rule to the skill. A good placement decision keeps each
concern in exactly one canonical home, so rules never drift across files.

## The placement test

Ask, in order:

1. **Is it the internals of one class type?** (the shape of an action's
   `handle()`, how a model casts attributes, the fluent shape of a query
   object) → it lives in **that building block's folder** (`actions/`,
   `models/`, `queries/`, …).

2. **Otherwise — is it a settled global rule the whole codebase obeys?**
   (CQRS, inject-don't-facade, flat folders, fire side effects only
   after commit) → it lives in **`architecture/`** as policy. You never
   re-decide it per class; it is already decided.

3. **Otherwise — is it an optional technique you choose per case?**
   (structure a workflow as a pipeline, make an implementation
   swappable/pluggable) → it lives in **`patterns/`** as a toolbox entry,
   written mostly as a *Decision* (when to reach for it) plus mechanics.

If none fit, it is probably infrastructure/runtime (`database/`,
`queues/`, `logs/`) or discipline (`testing/`).

## The two axes that make this unambiguous

Most confusion comes from the word "pattern." Almost everything has
pattern lineage (CQRS, query objects, value objects, actions). Lineage
does **not** decide placement. Two axes do:

- **Internals of one block vs. relationship across blocks.** Axis 1.
  Internals → block folder. Cross-block → architecture or patterns.
- **Mandatory-global vs. optional-per-case.** Axis 2, applied to the
  cross-block things. Decided once for the whole project → `architecture/`
  (policy). Chosen each time you write code → `patterns/` (technique).

| Concern | Pattern lineage? | Home | Why |
|---------|------------------|------|-----|
| CQRS | yes | `architecture/cqrs.md` | mandatory, codebase-wide |
| DI over facades | — | `architecture/dependency-injection.md` | mandatory, codebase-wide |
| Flat folders, after-commit | — | `architecture/` | mandatory, codebase-wide |
| Pipeline | yes | `patterns/pipeline.md` | opted into per workflow |
| Pluggable / strategy | yes | `patterns/pluggable.md` | opted into per case |
| `handle()` shape, casts, query shape | yes | building-block folder | internals of one type |

So: **CQRS is a pattern by origin, but in this project it is settled
mandatory policy — its home is `architecture/`.** Pipeline is a pattern
you opt into — its home is `patterns/`.

## Canonical home + link-only stubs

A cross-cutting rule has exactly **one** canonical home. Other folders
that touch it carry a one-line stub that **links** to the home — they
never restate the rule.

> Example: "dispatch jobs only from actions, only after commit" lives in
> [transactions.md](transactions.md). `jobs/conventions.md` and
> `actions/conventions.md` link to it; they do not re-explain it.

**Why:** a rule stated in three files is a rule that will eventually
contradict itself in two of them.

The same discipline governs **definitions**: the meaning of a
building-block term (what an Action *is*, what to call it, what not to)
lives once in [../../LANGUAGE.md](../../LANGUAGE.md). Rule files carry the
*grammar* — the `handle()` shape, the suffix rule — and link-stub to the
definition; they never redefine the term.

## Checklist

- New rule placed by running the test above (internals → architecture →
  patterns).
- "It's a pattern" was not used as a placement reason — the
  mandatory-vs-optional axis was.
- The rule has one canonical home; every other mention is a link-stub.
- A building-block term is *defined* once in `LANGUAGE.md`; rule files
  link-stub to the definition rather than restating it.
