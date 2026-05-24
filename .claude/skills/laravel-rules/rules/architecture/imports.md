# Imports

Settled, codebase-wide **policy** (see [placement.md](placement.md)) for
how classes and symbols are referenced in code.

## Rule: always import; never use an inline leading-backslash FQCN

Reference every class, interface, enum, function, and attribute by its
short name, brought in with a `use` statement at the top of the file —
including global-namespace symbols. Never write a leading-backslash FQCN
inline.

**Why:** imports give one place to see a file's dependencies, keep call
sites short and readable, and let tooling track usage. Inline
`\Fully\Qualified\Names` scatter the dependency surface through the body
and read as noise.

```php
// Good — imported, short name at the use site
use Illuminate\Support\Collection;
use SensitiveParameter;

public function login(#[SensitiveParameter] string $password): Collection { /* ... */ }

// Bad — inline leading-backslash FQCN
public function login(#[\SensitiveParameter] string $password): \Illuminate\Support\Collection { /* ... */ }
```

This applies equally to **global** symbols — `use SensitiveParameter;`,
`use Throwable;`, `use Closure;` — not just namespaced ones.

## Edge cases

- **Name collision** (two classes, same short name) → import one, alias
  the other with `use X as Y;`. Still no inline FQCN.
- **Single dynamic reference** (`::class` in a string-keyed map) → still
  import and use `Class::class`.

## Checklist

- Every class/interface/enum/attribute/function is imported via `use`.
- No leading-backslash FQCN anywhere in the body or signatures.
- Global symbols (`Throwable`, `Closure`, `SensitiveParameter`) imported too.
- Collisions resolved with `use ... as ...`, not inline FQCN.
