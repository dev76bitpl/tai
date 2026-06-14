# HTTP

Internals of the HTTP layer: controllers, form requests, output shaping,
and routing. The HTTP layer is a thin **boundary** — it translates a
request into a call on an [action](../actions/conventions.md) or
[query](../queries/conventions.md) and translates the result back. It
holds no business logic ([../architecture/cqrs.md](../architecture/cqrs.md)).
Building-block folder (see [../architecture/placement.md](../architecture/placement.md)).

## Rule: controllers are thin — validate, delegate, respond

A controller method does three things and no more: take a validated
request, call one action (writes) or query (reads), and return a
response. No domain logic, no multi-step orchestration, no direct
Eloquent writes.

**Why:** the controller is transport glue. Business logic placed here is
reachable only over HTTP — invisible to jobs and commands, and untestable
without the framework. Keeping it thin means the domain lives in actions/
queries, callable from any entry point.

```php
// Good — validate (form request), delegate (action), respond.
// One action → its own controller exposing the fitting resource verb (store).
final class RegisterOrganizationController
{
    public function __construct(
        private readonly RegisterOrganization $registerOrganization,
    ) {}

    public function store(RegisterOrganizationRequest $request): JsonResponse
    {
        $organization = $this->registerOrganization->handle(
            RegisterOrganizationData::from($request->validated()),
        );

        return OrganizationResponseData::from($organization)
            ->toResponse($request)
            ->setStatusCode(201);
    }
}
```

## Rule: a controller exposes only the seven resource methods

A controller's public methods are exactly the RESTful resource set —
`index`, `create`, `store`, `show`, `edit`, `update`, `destroy` — and
nothing else. **No custom-named action methods** (`switch`, `approve`,
`restore`), **no `__invoke`**, and **no `private`/`protected` helper
methods**. Register every controller with `Route::resource` /
`Route::apiResource`, narrowing with `->only([...])` / `->except([...])`
when it serves fewer than seven.

An action that doesn't map onto one of the seven is the signal to create a
**new controller named for that action's resource**, exposing the single
resource verb that fits — never to add a method to an existing CRUD
controller.

```php
// Bad — a custom verb bolted onto the resource controller
final class TeamController extends Controller
{
    public function switch(Request $request, Team $team, SwitchTeam $switchTeam): RedirectResponse
    { /* ... */ }   // `switch` is not one of the seven
}

// Good — the switch is its own resource; performing it is `store`
// routes/web.php
Route::resource('switch-team', SwitchTeamController::class)->only(['store']);

final class SwitchTeamController extends Controller
{
    public function store(SwitchTeamRequest $request, SwitchTeam $switchTeam): RedirectResponse
    {
        $switchTeam->handle($request->user(), $request->team());   // form request resolves the team

        return back();
    }
}
```

**Why:** the seven verbs are a closed, predictable vocabulary — every
controller reads the same way, route names generate consistently, and
there is exactly one place per resource for each operation. A custom
method (`switch`) breaks that uniformity and almost always hides a second
resource trying to exist; promoting it to its own controller names that
resource and keeps each controller a single, cohesive CRUD surface. A
`private`/`protected` method is logic that escaped the boundary — it
belongs in an [action](../actions/conventions.md), a
[query](../queries/conventions.md), or a form request (below), never as a
hidden helper on transport glue.

### Choosing the verb for a non-CRUD action

Model the action as a resource and pick the verb by HTTP semantics:

| The action… | Controller + verb |
|---|---|
| performs a one-off command / creates a selection (switch team, publish post, send invite) | `…Controller@store` — POST |
| replaces the state of an existing resource | `…Controller@update` — PUT/PATCH |
| tears something down | `…Controller@destroy` — DELETE |
| lists, shows, or renders a form | `index` / `show` / `create` / `edit` — GET |

## Rule: delegate reads to injected queries, writes to injected actions

A controller composes no Eloquent. It injects
[queries](../queries/conventions.md) for reads and
[actions](../actions/conventions.md) for writes — the same discipline
actions follow. **Route-model binding is allowed**: that is framework
resolution (with 404), not a read the controller composed.

- **List / filtered read** → an injected query projects to data objects
  (`toDataCollection()`); the controller hands them to the response.
- **Single read** → **route-model binding** resolves the model, and the
  controller projects it with `Data::from($model)` — binding already
  loaded it, so re-fetching through a `Find…Query` is waste.
- **Write** → an injected action, fed a data object built from
  `$request->validated()` (+ the route id for updates); then redirect.

```php
public function index(): Response
{
    return Inertia::render('Articles/Index', [
        'articles' => ($this->listArticles)()->published()->toDataCollection(),
    ]);
}

public function show(Article $article): Response   // route-model binding
{
    return Inertia::render('Articles/Show', ['article' => ArticleData::from($article)]);
}
```

**Why:** keeping composed reads in the query layer and writes in actions
leaves the controller as pure transport glue — no `Model::query()`, no
business logic. Route-model binding stays because it is declarative
routing/authorization input, not query composition.

## Rule: structural input validation lives in a form request

Validate the *shape* of the request (required, types, formats, lengths)
in a form request at the edge, then build the action's data object from
the validated data via [`::from()`](../data-objects/spatie-laravel-data.md).
The controller never reads raw `$request->all()`.

**Why:** validating at the boundary rejects malformed input before any
domain code runs, and a form request keeps those rules out of the
controller. Feeding the action a typed data object — never raw request
input — is also the mass-assignment guard
([../security/mass-assignment.md](../security/mass-assignment.md)).

The *layering* of checks (structural validation vs domain invariant vs DB
constraint) is governed canonically by
[../architecture/invariants.md](../architecture/invariants.md); a domain
guarantee is never enforced in a form request.

## Rule: authorize at the boundary

Authorization (may this user do this?) is enforced at the HTTP edge — a
form request's `authorize()`, a policy, or middleware — not buried in the
action. The canonical home is
[../security/authorization.md](../security/authorization.md); this folder
defers to it.

## Rule: shape output with response data objects, not raw models

Return a **response data object** (the response role in
[../data-objects/conventions.md](../data-objects/conventions.md)), built
from the model/result — never a raw model or `$model->toArray()`. The
response object defines exactly which fields leave the app.

**Why:** serializing a model leaks every column by default (including
secret-bearing ones) and couples the API to the table. An explicit
response object is the allow-list of what ships, which is also the output
-safety guard ([../security/output.md](../security/output.md)). It makes
API Resources redundant here — the data object already shapes and types
the payload.

When the frontend is **Inertia**, that response object is one per-page
`*PageData` (composing `can`/`copy`/`seo`), governed by
[../data-objects/inertia-page-data.md](../data-objects/inertia-page-data.md).

## Rule: cache data, not responses — never share-cache an authenticated response

In an authed app the default is to cache at the
[data layer](../patterns/caching.md), not to cache rendered responses.
Full-response caching (keyed by URL, replayed without running the controller) is
reserved for **public, anonymous, identical-for-every-user** responses, and is
invalidated through the same
[after-commit + version](../cache/invalidation.md) machinery. **Never** store a
personalized/authenticated response in a shared cache — it serves one user's
data to another (an output-safety failure, see
[../security/output.md](../security/output.md)).

Set cache headers deliberately even when not caching server-side, because
CDNs/proxies obey them: `Cache-Control: private` (or `no-store`) for anything
authed/personalized, `public, max-age=…` only for truly public responses, and
`ETag`/`Last-Modified` (→ `304`) for cacheable GETs. Inertia/JSON responses are
per-user — never full-response-cached.

## Rule: routes are resourceful, named, and use route-model binding

Register controllers with `Route::resource` / `Route::apiResource`, named
consistently, with implicit route-model binding for lookups. A controller
that serves fewer than seven verbs narrows with `->only([...])` /
`->except([...])` — never a hand-written route to a custom method. There
are no `Route::post('…', [C::class, 'switch'])` lines, because there are no
custom methods (rule above). Keep route files declarative — no closures
with logic; point routes at controllers.

## Edge cases

- **Multiple writes per request.** The controller still calls **one**
  orchestrator action; it does not call several actions in sequence. That
  composition (and its transaction) belongs in the action
  ([../architecture/transactions.md](../architecture/transactions.md)).
- **Partial updates (PATCH).** Use a data object with `Optional` fields so
  unset fields are skipped (see [../data-objects/spatie-laravel-data.md](../data-objects/spatie-laravel-data.md)).
- **Non-JSON responses / redirects.** Same shape — delegate, then return
  the redirect/view; the controller still holds no logic.

## Checklist

- Controller exposes only the seven resource methods — no custom-named
  methods, no `__invoke`, no `private`/`protected` methods; a non-resource
  action gets its own controller (verb chosen by HTTP semantics).
- Controller method: validated request in → one action/query → response
  out; no business logic, no raw Eloquent writes.
- Structural validation in a form request; action receives a data object
  built via `::from($request->validated())`, never raw request input.
- Authorization enforced at the boundary (defer to
  [../security/authorization.md](../security/authorization.md)).
- Output shaped by a response data object — no raw models leaking columns
  (defer to [../security/output.md](../security/output.md)).
- Routes are resourceful, named, with route-model binding; no logic in
  route files.
- HTTP tests live in `tests/Feature` ([../testing/conventions.md](../testing/conventions.md)).
