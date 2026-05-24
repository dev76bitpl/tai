# Dates are immutable

Every date/time value in the app is a `CarbonImmutable`, never a mutable
`Carbon`. Settled, codebase-wide **policy** (see [placement.md](placement.md)).
This is the canonical home; `models/` links here for the cast types.

## Rule: set the global date class to `CarbonImmutable`

Register the immutable date class once in `AppServiceProvider::boot()`, so
`now()`, `today()`, `Date::parse()`, and Eloquent date casts all return
immutable instances by default.

```php
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\Date;

public function boot(): void
{
    Date::use(CarbonImmutable::class);
}
```

**Why:** setting the default at the root means a value is immutable even
when someone forgets to reach for `CarbonImmutable` explicitly — there is
no mutable path left to fall back into. Without it, `now()` keeps returning
mutable `Carbon` and the foot-gun below reappears anywhere a developer
trusts the default.

## Rule: cast model dates with the immutable cast types

Cast every date/time column with `immutable_datetime` / `immutable_date`
(or `immutable_custom_datetime:<format>`) — never the mutable `datetime` /
`date` casts. Casts stay explicit and complete
([../models/conventions.md](../models/conventions.md)).

```php
protected function casts(): array
{
    return [
        'created_at'   => 'immutable_datetime',
        'updated_at'   => 'immutable_datetime',
        'published_at' => 'immutable_datetime',
        'birthday'     => 'immutable_date',
    ];
}
```

**Why:** the cast type is the contract for what comes off a model. Naming
it `immutable_*` keeps the guarantee local to the model even if the global
default is ever changed, and makes "this attribute is immutable" readable
at the cast site rather than implied from a provider.

## Rule: type and pass dates as `CarbonImmutable`

Type-hint date parameters, properties, and return types as
`CarbonImmutable` — in action/query signatures, in data objects, and in
value objects. This is the same immutability the skill already mandates for
those shapes ([../data-objects/conventions.md](../data-objects/conventions.md),
[../value-objects/conventions.md](../value-objects/conventions.md)), applied
to the date itself.

```php
public function __construct(
    public readonly CarbonImmutable $publishAt,
) {}
```

## Rule: reassign the result of a date transform

Immutable transforms return a **new** instance — assign it back. Calling a
mutator and discarding the result is a no-op.

```php
// Good — the transform returns a new instance
$deadline = $deadline->addDays(7);

// Bad — discards the returned instance; the value is unchanged
$deadline->addDays(7);
```

**Why (the whole point):** mutable `Carbon` is a shared-reference foot-gun.
`$b = $a; $b->addDay();` also moves `$a`; passing a `Carbon` into a method
that calls `->startOfDay()` silently rewrites the caller's value. Immutable
dates make a date a *value* — every transform yields a new instance, so it
is safe to pass across layers and compare, and a stray transform can never
mutate something it doesn't own.

## Checklist

- `Date::use(CarbonImmutable::class)` is set in `AppServiceProvider::boot()`.
- Model date columns use `immutable_datetime` / `immutable_date` casts,
  never the mutable `datetime` / `date` casts.
- Date parameters, properties, and returns are typed `CarbonImmutable`,
  never `Carbon`.
- Date transforms reassign the returned instance (`$d = $d->addDay()`),
  never call a mutator for effect.
