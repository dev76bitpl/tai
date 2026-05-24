# Logs

Structured logging: what to log, how to shape it, and what never to log.
Infrastructure/runtime concern (see
[../architecture/placement.md](../architecture/placement.md)).

## Rule: inject the logger; do not use the `Log` facade

Take a `LoggerInterface` via the constructor — using the `Log` contextual
attribute where a specific channel is needed — rather than calling the
`Log` facade inline. Governed by
[../architecture/dependency-injection.md](../architecture/dependency-injection.md).

**Why:** an injected logger is explicit in the dependency list and
swappable/spyable in tests, consistent with the codebase-wide
inject-don't-facade policy.

## Rule: log structured context, not interpolated strings

Pass machine-readable context as the second argument; keep the message a
short, stable, human label. Do not stuff ids and values into the message
string.

**Why:** structured context is queryable and filterable in an aggregator;
a stable message lets you group occurrences. A fully interpolated string
is neither — every occurrence looks unique and the values cannot be
indexed.

```php
// Good — stable message, structured context
$this->logger->info('organization registered', ['organization_id' => $organization->id]);

// Bad — values baked into the message; unsearchable, ungroupable
$this->logger->info("Registered organization {$organization->id} ({$organization->name})");
```

## Rule: never log secrets or PII

Do not pass credentials or PII to the logger, and never log whole request
payloads, data objects, or models that may contain them. Canonical home:
[../security/secrets.md](../security/secrets.md) — do not restate the
mechanics here.

## Decision: what is worth logging, and at what level?

Log decisions and outcomes, not narration:

- **`error`** — an unexpected failure needing attention (an integration
  call failed after retries, an invariant that should have been
  impossible).
- **`warning`** — a handled but notable condition (a retry, a fallback
  taken, a soft limit hit).
- **`info`** — significant domain outcomes worth an audit trail
  (registered, captured, cancelled).
- **`debug`** — developer detail, off in production.

Do not log inside tight loops, on every read, or to narrate ordinary
control flow.

**Why:** logs cost money and attention; signal drowns in narration. A log
line should answer "what happened and should someone care?", not trace
every step. Levels exist so production can keep the signal and drop the
noise.

## Edge cases

- **Exceptions.** Log the exception (so the trace and typed context are
  captured) rather than re-stringifying its message; let the handler
  report it once, not every layer.
- **Correlation.** Prefer pushing shared context (request/job id) onto the
  logger once over repeating it in every call.

## Checklist

- Logger injected (not the `Log` facade); channel via the `Log` attribute
  where needed.
- Stable message + structured context array — no values interpolated into
  the message.
- No secrets/PII, no whole-payload/model logging (defer to
  [../security/secrets.md](../security/secrets.md)).
- Level matches significance (Decision above); no per-iteration or
  control-flow narration.
