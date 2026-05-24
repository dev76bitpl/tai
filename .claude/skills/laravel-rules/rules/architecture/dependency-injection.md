# Dependency Injection

How classes obtain their dependencies. Settled, codebase-wide **policy**
(see [placement.md](placement.md)).

## Rule: inject dependencies, don't reach for facades

Prefer constructor and method injection over facades. Use a facade only
when a Laravel testing fake or framework convention makes it the
clearest option.

**Why:** injected dependencies are explicit in the signature, trivially
substitutable in tests (bind an in-memory implementation), and make a
class's collaborators visible. Facades hide dependencies behind static
calls and global state.

```php
// Good
public function __construct(private CreateUser $createUser) {}

// Avoid
$user = app(CreateUser::class)->handle($data); // hidden dependency
```

## Rule: use contextual attributes for config and contextual values

Use Laravel contextual attributes for scalar configuration, named
drivers, and contextual dependencies before writing manual bindings.

```php
use Illuminate\Container\Attributes\Config;

final class ImportIneIndicatorObservations
{
    public function __construct(
        #[Config('services.ine.base_url')]
        private readonly string $baseUrl,
    ) {}
}
```

Prefer built-in attributes — `Config`, `Storage`, `Cache`, `DB`, `Log`,
`Give`, `Tag`, `Context`, `RouteParameter`, `CurrentUser` — before
hand-writing contextual bindings.

**Why:** attributes keep the dependency declarative and at the
injection site, instead of scattering binding logic across service
providers.

## Checklist

- Dependencies are injected, not resolved via facades or `app()`.
- Scalar config/contextual values use built-in contextual attributes
  where one fits.
- Manual container bindings are a last resort.
