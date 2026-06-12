# Exceptions

> **[Exception](../../LANGUAGE.md)** is defined in `LANGUAGE.md`; this file owns the grammar.

Internals of business exceptions: how they are named, shaped, and
rendered. *When* to throw one (an invariant violation) is governed by
[../architecture/invariants.md](../architecture/invariants.md); this file
owns *how* the exception is shaped. Building-block folder (internals of
one class type, see [../architecture/placement.md](../architecture/placement.md)).

## Rule: a specific business exception per failure — never a generic one

Each distinct domain failure is its own exception class, named for the
failure: `DuplicateWaitlistSignupException`, `OrganizationTierLockedException`.
Never throw a bare `Exception`/`RuntimeException`/`LogicException` for a
domain failure, and never signal one by returning `null`/`false`.

**Why:** a typed exception lets a caller catch *this* failure and react,
makes the failure self-documenting at the throw site, and gives the HTTP
boundary something specific to map. A generic exception or a `false`
return erases what went wrong and forces callers to guess.

```php
// Good — specific, catchable, self-documenting
throw DuplicateWaitlistSignupException::forEmail($email);

// Bad — generic; the caller cannot distinguish this from any other failure
throw new RuntimeException('already signed up');
return false;
```

## Rule: group a domain's failures under one base exception

Give each domain a base exception (e.g. `WaitlistException`) that its
specific exceptions extend. Callers and the exception handler can then
catch the whole domain's failures with one type when they want to, or a
specific one when they care.

**Why:** a shallow per-domain hierarchy gives two catch granularities for
free without an exception-per-method explosion. A flat sea of unrelated
exceptions forces either over-specific catches or a catch-all `Exception`.

## Rule: construct through static named factory methods — always, one way

Every business exception is built through a `static` factory named for
the scenario, with a **non-public constructor**. There is exactly one way
to construct any business exception: never `new` one directly, and never
expose a public constructor as a second path. The factory takes the
domain values; the constructor stores them as typed context and builds
the message.

**Why:** consistency. Every throw site reads the same way
(`::forEmail($email)`), the message lives in one named place instead of
being retyped at each `throw`, and a non-public constructor guarantees
there is no second, message-only way to build the same exception.
Allowing a public constructor "just for the simple cases" reintroduces
the per-exception decision and the drift this rule removes — uniformity
is the point even when a single-scenario factory merely wraps the
constructor. One class can still carry several conditions as sibling
factories (`::tierLocked($tier)`, `::slugTaken($slug)`).

```php
abstract class WaitlistException extends Exception {}

final class DuplicateWaitlistSignupException extends WaitlistException
{
    private function __construct(public readonly string $email)
    {
        parent::__construct("Email already on the waitlist: {$email}");
    }

    public static function forEmail(string $email): self
    {
        return new self($email);
    }
}
```

## Rule: carry the failure's context as typed properties

Put the data describing the failure on the exception as `readonly`
properties (the offending email, the entity id), not only in the message
string. Build the human message from them.

**Why:** a renderer, logger, or test should read structured context, not
parse a message string. Typed properties keep the failure machine-
readable end to end. (Never interpolate a secret into the message — see
[../security/secrets.md](../security/secrets.md).)

## Decision: business exception, framework exception, or validation?

Match the failure to its mechanism:

- **Structural input invalid** (missing field, bad format) → framework
  **validation** (form request / data object), which already renders 422
  — not a business exception. See [../http/conventions.md](../http/conventions.md).
- **Record not found by route binding** → let the framework's
  `ModelNotFoundException` / 404 stand; do not wrap it.
- **A domain guarantee is violated** → your **business exception**
  (this file), thrown from the action.

**Why:** reusing the framework's validation/404 machinery for structural
and routing failures keeps responses consistent for free; business
exceptions are then reserved for genuine domain failures, so catching one
always means a domain rule fired.

## Rule: map exceptions to responses at the boundary, not in the action

The action throws; it does not format an HTTP response. Mapping a
business exception to a status code happens at the HTTP boundary — via the
exception's `render()` or the central exception handler.

**Why:** the action is transport-agnostic (it may be called from a
command or job), so it must not know about HTTP. Centralizing the mapping
keeps status codes consistent and out of business code. (Boundary wiring
lives in [../http/conventions.md](../http/conventions.md).)

## Rule: the `@throws` docblock lists everything the method can throw — `Throwable` included

A method documents in `@throws` **every** exception it can emit: the
specific business exceptions it throws directly, **and** the broad
`Throwable` it propagates from a framework call annotated to throw it. The
type is imported and referenced bare, never `\Throwable`
([../architecture/imports.md](../architecture/imports.md)).

The case that bites: **`DB::transaction()` is declared `@throws Throwable`**
— it rethrows whatever the closure throws and can throw on
deadlock/rollback — so any action wrapping a transaction
([../architecture/transactions.md](../architecture/transactions.md)) can
emit `Throwable` and must say so.

```php
use Throwable;

/**
 * @throws InvitationAlreadyAcceptedException
 * @throws InvitationExpiredException
 * @throws InvitationEmailMismatchException
 * @throws Throwable                         // DB::transaction can throw
 */
public function handle(TeamInvitation $invitation, User $user): Team
{
    // ... guards throw the specific business exceptions ...
    return DB::transaction(function () use (...): Team { /* ... */ });
}
```

**Why:** `@throws` is the method's failure contract — callers, the IDE,
and a strict static analyzer (PHPStan's `@throws` checking) rely on it.
Listing the business exceptions but omitting the `Throwable` a transaction
(or other framework call) can raise is an *incomplete* contract: it reads
as "only these typed failures happen here," which is false. Other common
`Throwable` sources to declare: `DB::transaction`, a `LockTimeoutException`
from `Cache::lock`, anything the method calls whose own `@throws` is
`Throwable`.

(Pest closures that exercise such a path carry the same `@throws` block —
see [../testing/conventions.md](../testing/conventions.md).)

## Edge cases

- **Wrapping a third-party exception.** Catch the package/SDK exception at
  the service boundary and rethrow a domain exception that carries the
  cause (`previous`), so business code never catches a vendor type.
- **Exceptions are not control flow.** An empty result is a value, not an
  exception; do not use exceptions for expected, non-failure outcomes.

## Checklist

- Distinct domain failures are distinct, specifically-named exception
  classes — no generic `Exception`/`RuntimeException`, no `false`/`null`.
- Each domain's exceptions extend a single base exception.
- Constructed only via a `static` factory with a non-public constructor —
  one construction path for every business exception; no public
  constructor, no direct `new`.
- Failure context lives in `readonly` typed properties, not just the
  message; no secrets interpolated into messages.
- Structural/validation and 404 failures use framework machinery, not
  business exceptions (Decision above).
- HTTP mapping happens at the boundary; actions only throw.
- `@throws` lists every exception the method can emit, including
  `Throwable` propagated from `DB::transaction()` and similar framework
  calls; the type is imported, not `\Throwable`.
- Pest tests assert the specific exception is thrown
  (`->toThrow(DuplicateWaitlistSignupException::class)`).
