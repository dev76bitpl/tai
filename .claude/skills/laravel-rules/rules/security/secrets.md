# Secrets & sensitive data

Canonical home for handling credentials and PII: keeping them out of
logs, stack traces, serialized payloads, and responses. Cross-cutting
policy — `logs/`, `data-objects/serialization`, `http/`, and integration
code link here rather than restating.

## Rule: mark secret parameters with `#[SensitiveParameter]`

Any function parameter holding a credential or PII — token, password,
API key, secret, card number — is annotated `#[SensitiveParameter]`.

**Why:** PHP redacts a sensitive parameter's value from stack traces and
exception backtraces. Without it, one uncaught exception in a method that
takes a token writes that token into your logs, error tracker, and any
trace that leaves the box. The attribute is the single cheapest leak
guard there is.

```php
use SensitiveParameter; // always import — never inline `\SensitiveParameter`

// Good — value never appears in a trace if this throws
public function authenticate(
    string $username,
    #[SensitiveParameter] string $password,
): Session {
    // ...
}

// Bad — a throw here puts the raw token in every stack trace
public function withToken(string $token): self { /* ... */ }
```

## Decision: when is `#[SensitiveParameter]` required vs optional?

- **Required** — the parameter holds a secret or PII that would be
  damaging in a log: passwords, API tokens/keys, OAuth access/refresh
  tokens, client secrets, card/bank numbers, government IDs.
- **Optional / skip** — non-sensitive scalars (ids, names, counts,
  enums). Annotating everything dilutes the signal.

Rule of thumb: *if seeing this value in a production stack trace would
require a rotation or an incident, mark it.*

## Rule: never log secrets or PII

Do not pass secrets to the logger, and do not log whole request payloads,
data objects, or models that may contain them. Log identifiers and
outcomes, not credentials.

**Why:** logs fan out to files, aggregators, and third parties, and they
persist far longer than a request. A logged secret is a leaked secret.

```php
// Bad
Log::info('login', ['credentials' => $request->all()]);
// Good
Log::info('login attempt', ['user_id' => $user->id]);
```

## Rule: keep secrets out of serialized payloads

A secret must not ride along in a queued job payload or a cached value
(both hit Redis/DB in the clear). Carry an identifier and re-resolve the
secret at use time. Queue-boundary mechanics:
[../data-objects/serialization.md](../data-objects/serialization.md).

## Rule: secrets come from config, never hardcoded

Read secrets from `config()` backed by env, never literals in code or
committed files. Inject via the `Config` contextual attribute
([../architecture/dependency-injection.md](../architecture/dependency-injection.md)).

## Rule: secrets inside data objects are wrapped, not raw strings

A secret carried by a [data object](../data-objects/conventions.md) is
not a bare `string`. Stack three guards, because each covers a different
leak path:

1. **Wrap the secret in a value object** (`Secret` / `HiddenString`) that
   redacts itself on `__toString`, `jsonSerialize`, and `toArray`. This
   is the guard that survives serialization and logging — the value can
   only escape through an explicit `->reveal()`. Lives in
   [../value-objects/conventions.md](../value-objects/conventions.md).
2. **Mark the promoted constructor parameter** `#[SensitiveParameter]` —
   it works on promoted DTO params and redacts the value from any
   construction-time stack trace.
3. **Unwrap only at the boundary.** The action receives the DTO (not a
   raw secret), and calls `->reveal()` only when handing the value to the
   downstream call — whose raw-string parameter is itself marked
   `#[SensitiveParameter]`.

```php
use SensitiveParameter;

final class Secret
{
    public function __construct(#[SensitiveParameter] private readonly string $value) {}
    public function reveal(): string { return $this->value; }
    public function __toString(): string { return '***'; }
    public function jsonSerialize(): string { return '***'; }
}

final class CreateUserData extends Data
{
    public function __construct(
        public readonly string $email,
        #[SensitiveParameter] public readonly Secret $password,
    ) {}
}
```

**Why each layer:** `#[SensitiveParameter]` only redacts *stack traces* —
a DTO that holds a raw secret still leaks it through `toArray()`, JSON,
and queued payloads. The value object closes those paths centrally
(stronger than a Spatie output transformer, which only guards
`toArray()`). And the secret-bearing DTO still must not ride in a job
payload — carry an id and re-resolve (see
[../data-objects/serialization.md](../data-objects/serialization.md)).

## Edge cases

- **Logging a DTO that has a secret field.** Don't rely on memory — give
  the field a redacting cast/serializer so it can never serialize raw.
- **Exception messages.** Don't interpolate a secret into a message
  string; `#[SensitiveParameter]` covers the trace, not a string you
  built yourself.
- **App-side vs HTTP-fixture redaction.** This file is app-side. Recorded
  HTTP-fixture redaction for Saloon lives in the
  `saloon-laravel-integration` skill — related, not the same home.

## Checklist

- Secret/PII parameters annotated `#[SensitiveParameter]` (Decision above).
- No secrets passed to the logger; no whole-payload/model logging.
- Secrets not carried in job payloads or cache — id + re-resolve.
- Secrets read from config/env, never hardcoded.
- Secret-bearing fields never serialize raw (redacting cast).
