# Authorization

Who may do what: policies, gates, and where authorization is enforced.
Cross-cutting security concern (see
[../architecture/placement.md](../architecture/placement.md)). Canonical
home for the *where* question — [http/](../http/conventions.md) defers
here.

## Rule: authorize at the boundary, not inside the action

Authorization — "may *this actor* do this?" — is enforced at the entry
boundary: a form request's `authorize()`, a policy/gate invoked in the
controller, or route middleware. The [action](../actions/conventions.md)
assumes the caller is already authorized and does not check.

**Why:** an action is transport-agnostic — the same action runs from a
console command, a job, or a test, where there is no authenticated user
to check against. Putting authorization inside it either breaks those
callers or smuggles HTTP/auth concerns into the domain. Keeping authz at
the edge means each entry point answers "who may" while the action only
answers "what happens."

## Decision: middleware, policy/gate, or form request?

- **Middleware** — coarse, route-level gates (authenticated, has role,
  subscription active). Applies before the controller for whole groups.
- **Policy / gate** — per-model, per-ability checks (`update` this
  `Organization`). The default for resource authorization; invoke via
  `$this->authorize(...)` or a form request.
- **Form request `authorize()`** — per-request checks that pair naturally
  with the request being validated, often delegating to a policy.

Pick the narrowest that fits: middleware for broad access, a policy for
"this actor on this record."

**Why:** matching the check to its scope keeps coarse rules out of every
policy and fine-grained rules out of middleware, so each lives once at the
right altitude.

## Rule: an authorization failure is not a domain invariant

A failed authorization is a `403` (`AuthorizationException`), distinct
from a domain invariant violation (a business exception, see
[../exceptions/conventions.md](../exceptions/conventions.md) and
[../architecture/invariants.md](../architecture/invariants.md)).
Authorization asks *may this actor*; an invariant asks *is this operation
valid given current state*. Do not collapse one into the other.

**Why:** they fail for different reasons and map to different responses
(403 vs the domain's status). Conflating them either leaks "forbidden" as
a domain error or hides a real authz boundary behind business logic.

## Edge cases

- **Authorization that depends on domain state** (can edit only while
  `draft`). The *gate* still lives in a policy at the boundary; the policy
  may read state to decide. If the rule is truly about the operation's
  validity rather than the actor, it is an invariant — re-check the
  Decision in [../architecture/invariants.md](../architecture/invariants.md).
- **Internal callers (jobs/commands).** They run as the system with no
  user; they are trusted by construction, so they skip authz — which is
  exactly why the action must not depend on it.

## Checklist

- Authorization enforced at the boundary (middleware / policy / form
  request), never inside actions.
- Check placed at the narrowest fitting scope (Decision above).
- Authorization failure (403) kept distinct from domain invariants
  (business exceptions).
- Policies/gates tested directly; feature tests assert forbidden access
  returns 403.
