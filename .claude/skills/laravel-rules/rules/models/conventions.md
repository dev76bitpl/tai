# Model Rules

> **[Model](../../LANGUAGE.md)** is defined in `LANGUAGE.md`; this file owns the grammar.

## Creation

Always create new models with Artisan and include the related factory, migration, and seeder:

```bash
php artisan make:model ModelName -fms --no-interaction
```

Use the concrete model name, for example:

```bash
php artisan make:model WaitlistSignup -fms --no-interaction
```

Do not manually create model, migration, factory, or seeder files when Artisan can generate the correct structure.

## Casts

Every Eloquent model must cast every persisted attribute in `casts(): array`, including:

- Primary keys and foreign keys.
- Strings, decimals, booleans, integers, enums, and nullable attributes.
- `created_at`, `updated_at`, and other date/time columns.

Do not rely on Laravel's implicit timestamp casts when editing or creating a model. Keep casts explicit and complete.

Date/time columns use the **immutable** cast types (`immutable_datetime` / `immutable_date`), never the mutable `datetime` / `date` casts — see [../architecture/dates.md](../architecture/dates.md).

## Property Annotations

Every model carries a class-level docblock annotating **every** attribute and relation it exposes as `@property-read` — persisted columns, casts, accessors, appended values, and relations alike. Never `@property`. The annotated type matches the cast: a nullable column is `?T`, an enum cast is the enum type, an `immutable_datetime` column is `CarbonImmutable`.

```php
/**
 * @property-read string $id
 * @property-read string $email
 * @property-read ?string $name
 * @property-read WaitlistStatus $status
 * @property-read CarbonImmutable $created_at
 * @property-read CarbonImmutable $updated_at
 * @property-read Organization $organization
 */
final class WaitlistSignup extends Model
{
    // ...
}
```

**Why:** Eloquent attributes are magic — they are not declared PHP properties, so without the docblock the IDE and PHPStan cannot see them: every `$model->email` is an unchecked guess, and a typo or a renamed column fails silently at runtime instead of at analysis time. Marking them all `@property-read` adds the second guarantee — attributes are **read** off a model, never mutated by direct assignment (`$model->email = …`); writes go through actions and mass-assignment arrays (`create`/`update`/`fill`), consistent with CQRS ([../architecture/cqrs.md](../architecture/cqrs.md)). Static analysis then flags a stray in-place write as well as an unknown attribute. Keep the block complete and in sync with the casts.

## Scopes

Never implement Eloquent scopes on models. Model scopes hide query behavior behind Laravel magic and make it harder to understand what is being called and when.

Put reusable read filters and query composition in query objects under `app/Queries` instead.

## Deletes

Never use the `SoftDeletes` trait. Deletes are hard deletes — the row is
actually removed.

Soft deletes keep "deleted" rows in the table forever, which is a GDPR /
right-to-erasure liability (personal data you believe is gone is still
stored) and a steady source of stale data and surprising query results.
They also add a global scope — the same Eloquent magic the **Scopes** rule
above rejects — and complicate unique constraints.

If you need to retain a record of what existed, use an append-only history
table ([../database/history.md](../database/history.md)), not a
`deleted_at` flag. When deleting a parent, delete its children explicitly
first, inside one transaction ([../architecture/transactions.md](../architecture/transactions.md));
constrained foreign keys ([../database/migrations.md](../database/migrations.md))
make a forgotten child throw rather than leave orphaned personal data
behind.

## Tests

Every model must have a unit test that verifies its array shape:

```php
test('to array', function (): void {
    $model = SomeModel::factory()->create()->refresh();

    expect(array_keys($model->toArray()))
        ->toBe([
            'id',
            'name',
            'created_at',
            'updated_at',
        ]);
});
```

The expected array keys should match the public serialized shape, including hidden attributes and appended values when applicable.

## Checklist

- Create new models with `php artisan make:model ModelName -fms --no-interaction`.
- Cast all persisted columns explicitly.
- Include enum casts for enum-backed columns.
- Include decimal precision in decimal casts.
- Include timestamp casts rather than relying on Laravel defaults; date/datetime columns use the `immutable_*` casts.
- Annotate every attribute and relation in the model's class docblock as `@property-read` (never `@property`), with types matching the casts.
- Do not add local or global model scopes.
- Do not use the `SoftDeletes` trait; deletes are hard deletes (retain
  history via an append-only table, not `deleted_at`).
- Add or update a `to array` test for every model touched.
