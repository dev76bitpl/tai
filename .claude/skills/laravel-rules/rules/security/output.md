# Output safety

Preventing sensitive or unsafe data from leaving the app: response
shaping, secret-bearing columns, and escaping. Cross-cutting security
concern (see [../architecture/placement.md](../architecture/placement.md)).
Secret *mechanics* are canonical in [secrets.md](secrets.md); this file
owns the output boundary.

## Rule: responses go through a response data object — never a raw model

The intended API output is a **response data object** (the response role
in [../data-objects/conventions.md](../data-objects/conventions.md)),
built from the model/result. Never return a raw model, `$model->toArray()`,
or a collection of models. Same rule as
[../http/conventions.md](../http/conventions.md), from the security side.

**Why:** serializing a model exposes *every* column by default —
including ones added later — and couples the API to the table. A response
object is an explicit allow-list of what ships: adding a column to a
table never silently widens a response.

## Rule: keep `$hidden` (and a redacting cast) on secret/PII columns anyway

Even with response objects, secret-bearing columns (`password`,
`remember_token`, tokens, PII) stay in the model's `$hidden`, and ideally
are a redacting cast / `Secret` value object
([../value-objects/conventions.md](../value-objects/conventions.md)).

**Why:** unlike a write, which has *one* controlled path, a model leaks
out through *many* accidental paths — a stray `return $model`, an
auto-loaded relation embedded in a response, `Log::info(['user' => $user])`,
`dd()`, an exception serializing its context, a package that JSON-encodes
the model. The response object only covers the *intended* response, not
the accidents. A leaked credential is silent and asymmetrically costly
(rotation/incident), so this cheap always-on backstop is worth keeping —
this is the one place the output guard is **not** redundant with the data
object (contrast `$fillable` in [mass-assignment.md](mass-assignment.md)).
The redacting cast is the strongest form: it protects *every* path, not
just model serialization.

```php
// Defense in depth on the model
protected $hidden = ['password', 'remember_token', 'api_token'];
```

> Non-secret fields do **not** need `$hidden` — the response object is the
> single source of truth for them, and a second list only drifts. Keep
> `$hidden` specifically for secrets/PII.

## Rule: never disable output escaping for untrusted content

Rendered output relies on Blade's automatic escaping (`{{ }}`). Do not use
the raw directive (`{!! !!}`) for any value derived from user input or
external data.

**Why:** `{!! !!}` injects unescaped HTML — a stored-XSS vector the moment
user-influenced data flows through it. Escaping is the default for a
reason; opt out only for content you fully control and trust.

## Edge cases

- **Embedded relations.** A response object that nests a related record
  must nest *its* response object, not the raw related model — otherwise
  the nested model leaks its columns.
- **Error responses.** Map business exceptions to a safe message/status at
  the boundary ([../exceptions/conventions.md](../exceptions/conventions.md));
  never echo raw exception messages or stack traces to clients.
- **Where the response object is built.** A list/filtered read is projected
  by the query itself (`toDataCollection()`); a single route-bound model is
  projected by the controller (`Data::from($model)`). Either way a `Data`
  object leaves the app, never the model — see
  [../queries/conventions.md](../queries/conventions.md) and
  [../http/conventions.md](../http/conventions.md).

## Checklist

- Responses are response data objects, never raw models / `toArray()` /
  model collections; nested relations use their own response objects.
- Secret/PII columns kept in `$hidden` (and ideally a redacting cast per
  [secrets.md](secrets.md)); non-secret fields rely on the response object.
- No `{!! !!}` on user-influenced or external content.
- Error responses expose safe messages only — no raw exception text or
  traces.
- A test asserts the response shape excludes sensitive fields.
