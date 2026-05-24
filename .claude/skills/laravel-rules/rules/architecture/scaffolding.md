# Scaffolding (artisan make)

How files get created. Settled, codebase-wide **policy** (see
[placement.md](placement.md)): every class/file is generated with
`php artisan make:*`, never hand-authored from scratch.

## Rule: create every class with `php artisan make:*`

Reach for the matching artisan generator before writing a new class,
migration, test, or config. Don't hand-create the file.

**Why:** the generator places the file at the right path with the right
namespace, base class, and imports, and keeps structure consistent across
the codebase. Hand-authoring drifts on namespace/location/boilerplate and
misses the stub's wiring. It also surfaces the *correct* tool — a Spatie
data object is `make:data`, an enum is `make:enum`, a contract is
`make:interface` — instead of a generic file you then have to shape.

## Rule: customize the stubs so generated files already conform

Publish the stubs (`php artisan stub:publish`) and edit them so generated
output already carries `declare(strict_types=1);` and `final` per
[classes.md](classes.md) — Laravel's default stubs include **neither**.

**Why:** `classes.md` mandates strict types + `final`, which the default
stubs omit. The choice is: hand-fix every generated file (drift, missed
files) or fix it once in the stub. Fix the stub — then `make:*` output is
conformant by construction, and the generator rule above stays friction-
free.

## Catalog: concept → command

| Building block | Command |
|---|---|
| Action / Query / Service | `make:class` (e.g. `make:class Actions/CreateOrganization`) |
| Data object | `make:data` (Spatie) |
| Value object | `make:class` |
| Enum | `make:enum` |
| Exception | `make:exception` |
| Interface / contract | `make:interface` |
| Trait | `make:trait` |
| Model (+ factory, migration, seeder) | `make:model -fms` (see [../models/conventions.md](../models/conventions.md)) |
| Migration / Factory / Seeder | `make:migration` / `make:factory` / `make:seeder` |
| Job | `make:job` |
| Controller / Form request | `make:controller` / `make:request` |
| Middleware / Policy | `make:middleware` / `make:policy` |
| Notification / Mail | `make:notification` / `make:mail` |
| Command / Cast / Rule | `make:command` / `make:cast` / `make:rule` |
| Provider / Config | `make:provider` / `make:config` |
| Test | `make:test --pest` (then mirror structure, [../testing/conventions.md](../testing/conventions.md)) |
| MCP server/tool/resource/prompt | `make:mcp-server` / `make:mcp-tool` / `make:mcp-resource` / `make:mcp-prompt` |
| cache / queue / session / notifications tables | `make:cache-table` / `make:queue-table` / `make:session-table` / `make:notifications-table` |

There is no dedicated generator for Actions/Queries/Value objects — use
`make:class` with the target path; the name follows
[../naming/conventions.md](../naming/conventions.md) and the role follows
[cqrs.md](cqrs.md).

## Generators this codebase does *not* use

- **`make:scope`** — model scopes are forbidden; reusable reads are query
  objects ([../queries/conventions.md](../queries/conventions.md)).
- **`make:event` / `make:listener` / `make:observer`** — events and
  observers are guardrails, not defaults; prefer actions/jobs. Generate
  these only in the narrow justified cases
  ([../events/conventions.md](../events/conventions.md),
  [../observers/conventions.md](../observers/conventions.md)).

## Edge cases

- **After generating**, the file already conforms *if* stubs are
  customized; otherwise apply `final` + `strict_types` + import rules
  ([classes.md](classes.md), [imports.md](imports.md)) before writing
  logic.
- **`make:test`** generates a PHPUnit-shaped class by default — use
  `--pest` and the `test()` / structure-mirror conventions
  ([../testing/conventions.md](../testing/conventions.md)).

## Checklist

- New class/migration/test/config created via `php artisan make:*`, not by
  hand.
- The *specific* generator used (`make:data`/`make:enum`/`make:interface`/
  …), not a generic file, where one exists.
- Stubs published and customized so output has `declare(strict_types=1)` +
  `final`.
- No `make:scope`; `make:event`/`make:listener`/`make:observer` only in
  the justified guardrail cases.
- Generated file conforms to `classes.md`/`imports.md` before logic is
  added.
