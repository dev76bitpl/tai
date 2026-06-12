# Inertia page data (`*PageData` contract)

> **Applies only when the frontend is Inertia.** This is the per-page response
> contract between a Laravel controller and an Inertia page. On a non-Inertia
> stack, ignore it and follow the general response role in
> [conventions.md](conventions.md). The **frontend** side of this contract lives
> in the sibling **inertia-rules** skill (authorization, shared-data, generated
> types) — those files consume what this one defines.

A specialization of the **response role** ([conventions.md](conventions.md)): the
single typed object a controller hands to `Inertia::render`. Building-block folder
([../architecture/placement.md](../architecture/placement.md)); package mechanics
(`Optional`, mapping, `toArray`) in [spatie-laravel-data.md](spatie-laravel-data.md).

## Rule: one `*PageData` per page, the only declared prop type

A controller passes a page exactly one prop: a `*PageData` object composing the
page's data (item/collection DTOs) plus three standard concerns — `can`
(capabilities), `copy` (on-page text), and `seo` (document meta). The page
declares this one type; it never receives a loose bag of separate props.

```php
final class TeamsIndexPageData extends Data
{
    public function __construct(
        /** @var DataCollection<int, TeamData> */
        public readonly DataCollection $teams,
        public readonly TeamsIndexPageAuthorizationData $can,
        public readonly TeamsIndexPageCopyData $copy,
        public readonly PageSeoData $seo,
    ) {}
}
```

**Why:** one typed contract per page is one generated TypeScript type the page
imports (inertia-rules `types/generated`), instead of an untyped prop bag that
drifts. The page's whole surface is described by a single object.

## Rule: name page pieces `<Page><Concern>Data`

The bag and each concern are named for the page and the concern, so the surface
is self-indexing:

- `TeamsIndexPageData` — the prop bag.
- `TeamsIndexPageAuthorizationData` — `can`.
- `TeamsIndexPageCopyData` — `copy`.
- `TeamsIndexPageSeoData` — `seo`, **only** when the page needs more than the
  shared `PageSeoData` default.

## Rule: capabilities are `can`, with outcome-named fields

The capability object is exposed as `can`, and its fields are the **outcome** —
not `canX`. The frontend reads `can.createTeam`, never the stuttering
`can.canCreateTeam`. The class keeps the role name `*PageAuthorizationData`. Every
boolean comes from a policy/gate
([../security/authorization.md](../security/authorization.md)), never invented in
a controller.

```php
final class TeamsIndexPageAuthorizationData extends Data
{
    // value comes from $user->can('create', Team::class)
    public function __construct(public readonly bool $createTeam) {}
}
// frontend reads: can.createTeam
```

**Why:** the field is read on the frontend as a sentence (`can.createTeam`);
prefixing each field with `can` stutters against the `can` accessor. Only the
fields are outcome-named — the class stays `*AuthorizationData`.

## Rule: SEO/meta is a separate concern from on-page copy

`seo.title` (the document `<title>`/meta — for SERPs, the browser tab, and people
*not yet on the page*) is a different axis from `copy.title` (the visible `<h1>`,
for people *already on the page*). Model them as **separate fields even when their
values currently coincide** — "aligned but allowed to differ". Do not unify them.

- `seo` → drives the Inertia `<Head>` (title + meta).
- `copy` → drives the on-page heading and body text.

## Rule: one shared `PageSeoData` for the whole marketing attribute set

A single shared `PageSeoData` carries every SEO attribute a marketing site needs.
`title`/`description` are required; `noindex` defaults to `true` (behind-login
pages should not be indexed); every marketing field is Spatie `Optional`, so an
absent field is **omitted from the serialized payload** — an authenticated page
emits a lean `{ title, description, noindex }` while a marketing page populates
the rest. One class, no `MarketingPageSeoData` fork, no payload bloat.

```php
final class PageSeoData extends Data
{
    public function __construct(
        public readonly string $title,          // raw — NO app-name suffix (see below)
        public readonly string $description,
        public readonly bool $noindex = true,
        public readonly string|Optional $canonicalUrl = new Optional(),
        public readonly string|Optional $keywords = new Optional(),
        public readonly string|Optional $ogTitle = new Optional(),
        public readonly string|Optional $ogDescription = new Optional(),
        public readonly string|Optional $ogImageUrl = new Optional(),
        public readonly string|Optional $ogType = new Optional(),
        public readonly string|Optional $ogUrl = new Optional(),
        public readonly string|Optional $twitterCard = new Optional(),
        public readonly string|Optional $twitterSite = new Optional(),
    ) {}
}
```

**Why `Optional`, not nullable:** `Optional` removes the key from output
([spatie-laravel-data.md](spatie-laravel-data.md)), keeping the authenticated
payload `{ title, description, noindex }`; `null` would emit every key explicitly
as `null` and bloat the contract.

## Rule: the backend sends a raw title; the frontend owns the suffix

`seo.title` is the page-specific content only — `"Teams"`, not `"Teams — Trady"`.
The app-name suffix is applied once on the frontend via the Inertia
`createInertiaApp` `title` callback (inertia-rules `shared-data`). The backend
owns content; the frontend owns presentation.

## Rule: user-facing copy lives in lang files, camelCase keys

`copy`/`seo` text comes from `lang/en/<resource>.php` under `seo`/`copy`
sections, keyed in **camelCase** so the Data object maps directly. Hydrate the
copy/seo objects with `::from(__(...))` — **never** `new` with inline string
literals ([spatie-laravel-data.md](spatie-laravel-data.md): construct with
`::from`, never `new`). The PHP only *references* the copy; the lang file owns it.

```php
// Good — text lives in lang/en/teams.php; ::from maps the array onto the object
$copy = TeamsIndexPageCopyData::from(__('teams.index.copy'));
$seo  = PageSeoData::from(__('teams.index.seo'));

// Bad — copy hardcoded in PHP, and `new` bypasses ::from (the lang file is its home)
$seo  = new PageSeoData(title: 'Decisões financeiras…', description: '…', noindex: false);
$copy = new TeamsIndexPageCopyData(heroTitle: 'Decisões financeiras', /* …more literals… */);
```

**Why:** camelCase keys map straight onto camelCase Data properties — the project
sets no Spatie input name-mapping strategy, so snake_case lang keys would not map.
Hardcoding strings in PHP puts user-facing content in code — untranslatable, not
reviewable as content, and duplicated across pages; the lang file is the single
home for copy, and `::from` runs the mapping pipeline `new` skips.

## Rule: the controller assembles the `*PageData` via `::from`

A controller composes the page object from typed pieces — collection/item DTOs
from a query projection ([../queries/conventions.md](../queries/conventions.md)),
`can` from policies, `copy`/`seo` from lang — **each through `::from`** — then
hands the one object to `Inertia::render`. It authors no content and no
capability values; it references them.

```php
public function index(Request $request): Response
{
    return Inertia::render('teams/index', TeamsIndexPageData::from([
        'teams' => $this->listTeamsQuery->toDataCollection(),
        'can'   => TeamsIndexPageAuthorizationData::from([
            'createTeam' => $request->user()->can('create', Team::class),
        ]),
        'copy'  => TeamsIndexPageCopyData::from(__('teams.index.copy')),
        'seo'   => PageSeoData::from(__('teams.index.seo')),
    ]));
}
```

**Why:** the assembly is the snippet agents copy. Showing every piece built via
`::from` (DTOs, capabilities from a policy, copy/seo from lang) is what forecloses
the `new`-with-inline-literals shortcut that buries content and capability logic
in the controller.

## Edge cases

- **Page needs no special SEO.** Use the shared `PageSeoData` with just
  `title`/`description` — no per-page `*PageSeoData` subclass.
- **`noindex` enforcement.** A follow-up option is an `X-Robots-Tag` response
  header on authenticated routes instead of the per-page boolean; deferred — the
  per-page field is the current approach.
- **No models in `*PageData`.** It is a response object — carry DTOs, never
  Eloquent models ([conventions.md](conventions.md),
  [../security/output.md](../security/output.md)).

## Checklist

- A page receives exactly one `*PageData` prop composing data + `can` + `copy` +
  `seo`.
- Pieces named `<Page><Concern>Data`; a `*PageSeoData` exists only when richer
  than the shared default.
- `can` fields are outcome-named (`createTeam`), class is `*PageAuthorizationData`,
  booleans from policies/gates.
- `seo` and `copy` are separate; `seo.title` is raw (no app-name suffix).
- SEO uses the shared `PageSeoData`; marketing fields `Optional` (omitted when
  absent); `title`/`description` required, `noindex` defaults true.
- Copy/seo from `lang/en/<resource>.php`, camelCase keys, via `::from(__(...))` —
  never `new` with inline string literals.
- Controller assembles the `*PageData` via `::from` (DTOs, `can` from policy,
  `copy`/`seo` from lang); it authors no content or capability values inline.
- Frontend consumption follows the sibling inertia-rules skill (authorization,
  shared-data, generated types).
