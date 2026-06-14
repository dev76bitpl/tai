# Comments

Settled, codebase-wide **policy** (see [placement.md](placement.md)) for when
a comment earns its place. The default is none: names, types, casts, enums,
and value objects carry the meaning.

## Rule: comment the non-obvious WHY, never restate the code

Make the code say what it does — through names, type hints, casts, enums, and
value objects. A comment is justified only when it records a **why** the code
cannot express: a domain rule, a non-obvious trade-off, a workaround for an
upstream bug, a link to a decision record. A comment that restates mechanics
the code already states is noise — delete it and let the code speak.

**Why:** a comment that paraphrases the code beside it is a second source of
truth that drifts the moment the code changes, and a reader who catches one
stale comment stops trusting all of them. Cast names, nullable columns, and
typed properties already encode the mechanics; narrating them in prose adds
nothing and rots. Self-explanatory code keeps one source of truth.

```php
// Bad — restates what the cast, the column nullability, and the type already say
public function __construct(
    // The optional buy-target: a price the user intends to buy at.
    // Money is stored as integer minor units paired with its own
    // currency column (App\Casts\MoneyCast). Null = no target set,
    // a genuine distinct domain state, so both columns are nullable.
    public readonly ?Money $buyTarget,
) {}

// Good — the nullable Money value object and the field name carry all of it
public function __construct(
    public readonly ?Money $buyTarget,
) {}
```

The cast lives on the model/Data definition, not narrated at the use site;
`?Money` already says "optional"; `buyTarget` already says what it is.

## Edge cases

- **A genuine non-obvious why** — a regulatory constraint, a workaround for an
  upstream bug, a deliberate deviation from a rule file — keep a short comment
  stating the why and linking its source. This is the comment that earns its
  place.
- **The "why" is really a missing name** — extract a named method, value
  object, or enum case instead of commenting. A `BuyTarget` value object or a
  well-named private method beats a paragraph explaining an expression.
- **PHPDoc the type system cannot express** — generics and array shapes
  (`@param array<int, OrderLine>`, `@return Collection<int, User>`) — keep; it
  is type information tooling consumes, not narration.
- **Public-API docblocks** a package consumer reads — allowed where they
  document the contract, never internals.

## Checklist

- No comment restates what a name, type, cast, enum, or value object already
  says.
- Every surviving comment records a *why* the code cannot express, not a
  *what*.
- A comment that exists only because a name is unclear is replaced by a better
  name, method, or value object — not kept.
- PHPDoc is limited to type information the type system cannot carry, or
  public-API contract.
