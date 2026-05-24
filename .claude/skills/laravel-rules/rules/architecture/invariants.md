# Domain invariants

Which layer owns domain invariants, and when to introduce one. Settled,
codebase-wide **policy** (see [placement.md](placement.md)). This is the
canonical home; `actions/` links here for the *who enforces* rule, and
`exceptions/` owns the *how to signal a violation* mechanics.

## Rule: actions enforce invariants

Domain invariants are enforced inside actions. Controllers, commands,
jobs, queries, and models do not enforce business invariants.

**Why:** an invariant is a guarantee about a state change, and state
changes live in actions (CQRS, see [cqrs.md](cqrs.md)). Enforcing
elsewhere splits the guarantee across layers and lets an unguarded path
violate it.

## Rule: signal violations with a specific business exception

When an invariant fails, throw a specific business exception — never a
generic `Exception`/`RuntimeException`, and never return `false`.
Naming and hierarchy mechanics live in [exceptions/](../exceptions/conventions.md).

```php
// Good
throw new DuplicateWaitlistSignupException($email);

// Bad
throw new RuntimeException('already signed up');
return false;
```

**Why:** a typed business exception lets callers handle the specific
domain failure and makes the invariant self-documenting. `false` and
generic exceptions erase what actually went wrong.

## Decision: is this rule a domain invariant?

Not every "the data must be a certain way" rule is an invariant. Three
different rules get confused, and each has a different home. Ask, in
order:

1. **Is it about the *shape* of one request's input** — required fields,
   types, formats, lengths, an email that looks like an email? → it is
   **input validation**, not an invariant. It belongs at the boundary: a
   form request for HTTP, or the data object's own construction for any
   caller (see [../data-objects/conventions.md](../data-objects/conventions.md)).
   It runs before the action and rejects malformed input.

2. **Is it a guarantee that must always hold for the domain to be valid**,
   judged against *current committed state* — "an organization has at
   most one owner", "you cannot sign up to a closed waitlist", "a refund
   never exceeds the captured amount"? → it is a **domain invariant**.
   It belongs in the action, which reads the state and throws a business
   exception on violation. Only the action can enforce it, because only
   the action sees the state at write time and owns the write.

3. **Is it a physical guarantee the database itself should refuse to
   break** — a unique index, a foreign key, NOT NULL? → it is a
   **database constraint** ([../database/schema.md](../database/schema.md)).
   It is a *backstop against races and bugs*, never the primary
   enforcement: the action still checks the invariant first and returns a
   meaningful exception, the constraint just guarantees no concurrent
   write slips through.

```
shape of one request's input?   → validation (form request / data object)
guarantee about domain state?   → invariant (action, business exception)
physical race/corruption guard? → DB constraint (backstop, not primary)
```

### One rule can need more than one layer

"A user signs up to the waitlist at most once per email" is all three:
the email *format* is validation (data object), "not already signed up"
is an invariant the action checks against current rows (throwing
`DuplicateWaitlistSignupException`), and a unique index on `email` is the
backstop that closes the race between two simultaneous requests. Layer
them; do not pick one and skip the others. The action's check gives the
caller a clear failure; the index guarantees correctness under
concurrency.

**Why this matters:** pushing an invariant down to "just a validation
rule" lets an unguarded caller (a job, a console command, a second
action) violate it. Pushing it down to "just a DB constraint" surfaces
domain failures as raw `QueryException`s with no business meaning. The
invariant's authoritative home is the action; the other layers support
it, they do not replace it.

## Checklist

- Each data rule classified: input validation, domain invariant, or DB
  constraint (decision above) — "it's a validation rule" was not used to
  skip an action-level check.
- Invariants are enforced in actions, not other layers.
- Violations throw a specific business exception (see `exceptions/`).
- No generic exceptions or `false` returns for domain failures.
- Where races matter, a DB constraint backs the action's check rather
  than replacing it.
