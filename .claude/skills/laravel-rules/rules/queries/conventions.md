# Query Rules

> **[Query](../../LANGUAGE.md)** is defined in `LANGUAGE.md`; this file owns the grammar.

Queries are the **read side** of CQRS: fluent, read-only query objects in
flat `app/Queries`, `Query`-suffixed, `final`, `declare(strict_types=1)`
([../architecture/classes.md](../architecture/classes.md)). They are the
**only** place Eloquent reads are composed — actions and controllers
*inject* queries and never compose reads inline.

## Rule: a query is a fluent, read-only object initialised in `__invoke()`

`__invoke()` initialises the builder and returns a clone; filter methods
mutate the builder and return `$this`; terminal methods read. No
`handle()` (that belongs to [actions](../actions/conventions.md)). A query
never mutates state and never calls external services.

```php
/** @use QueriesRecords<Article> */
final class FindArticleQuery
{
    use QueriesRecords;

    public function __invoke(): self
    {
        $this->builder = Article::query();

        return clone $this;
    }

    public function forSlug(string $slug): self
    {
        $this->builder->where('slug', $slug);

        return $this;
    }
}
```

Reusable read filters live here, **never** as model scopes
([../models/conventions.md](../models/conventions.md)). Use model
arguments when the caller already holds the model; scalars for external
identifiers/value filters.

## Rule: terminals come from the generic `QueriesRecords` trait

The terminal reads (`builder/count/exists/first/firstOrFail/get`) are
identical across every query, so they are composed in via a trait — reuse
by composition, not a base class ([../architecture/classes.md](../architecture/classes.md))
— made generic over the model with PHPStan `@template` so returns are
typed per query.

```php
// app/Queries/Concerns/QueriesRecords.php
/** @template TModel of Model */
trait QueriesRecords
{
    /** @var Builder<TModel> */
    private Builder $builder;

    /** @return Builder<TModel> */
    public function builder(): Builder { return $this->builder; }
    public function count(): int { return $this->builder->count(); }
    public function exists(): bool { return $this->builder->exists(); }
    /** @return TModel|null */
    public function first(): ?Model { return $this->builder->first(); }
    /** @return TModel */
    public function firstOrFail(): Model { return $this->builder->firstOrFail(); }
    /** @return Collection<int, TModel> */
    public function get(): Collection { return $this->builder->get(); }
}
```

**Why:** every query needs the same terminals; a generic trait gives them
once with correct per-model typing (`first(): Article`,
`get(): Collection<Article>`), instead of copying six methods into every
query or reaching for a base class.

## Decision: return a model or a data object?

The consumer's side of the CQRS line decides:

- **Write path** — a consumer that will *mutate* (an
  [action](../actions/conventions.md) loading the aggregate to write) →
  use a **terminal** → get the **model**.
- **Read / response path** — a consumer feeding presentation
  (controller → Inertia/JSON) → use a **projection** → get a **`Data`
  object**. A raw model must never cross to a response
  ([../security/output.md](../security/output.md)).

**Why:** the action needs Eloquent to act on; the response must not carry
a mutable, lazy-loading, column-leaking model. The same query can offer
both — a terminal for writes, a projection for reads — and the consumer
picks.

## Rule: projection is the generic `TransformsToData` trait → `toData()`

A query that feeds the read path adds the projection trait, generic over
the model **and** the target `Data` class. The query supplies the
single-item `toData()`; the trait provides `toDataCollection()`. Because
the trait calls `get()`, it requires the terminal contract — so a
**projecting** query also implements `ReadsRecords` (a pure model-returning
query does not).

```php
// app/Queries/Concerns/ReadsRecords.php — the terminal contract (typing seam)
/** @template TModel of Model */
interface ReadsRecords
{
    /** @return Builder<TModel> */ public function builder(): Builder;
    public function count(): int;
    public function exists(): bool;
    /** @return TModel|null */ public function first(): ?Model;
    /** @return TModel */ public function firstOrFail(): Model;
    /** @return Collection<int, TModel> */ public function get(): Collection;
}

// app/Queries/Concerns/TransformsToData.php
/**
 * @template TModel of Model
 * @template TData of Data
 * @phpstan-require-implements ReadsRecords<TModel>
 */
trait TransformsToData
{
    /** @param TModel $model @return TData */
    abstract public function toData(Model $model): Data;

    /** @return SupportCollection<int, TData> */
    public function toDataCollection(): SupportCollection
    {
        return $this->get()->map(fn (Model $model) => $this->toData($model));
    }
}

// a projecting query wires all three
/**
 * @implements ReadsRecords<Article>
 * @use QueriesRecords<Article>
 * @use TransformsToData<Article, ArticleData>
 */
final class ListArticlesQuery implements ReadsRecords
{
    use QueriesRecords;
    use TransformsToData;

    public function __invoke(): self { $this->builder = Article::query(); return clone $this; }
    public function published(): self { $this->builder->where('published', true); return $this; }

    /** @param Article $model */
    public function toData(Model $model): ArticleData
    {
        return ArticleData::from($model);
    }
}
```

**Why an interface, used only when projecting:** `TransformsToData` calls
`$this->get()` but does not declare it; `@phpstan-require-implements`
types that call without redeclaring `get()` (which would cause an
abstract-vs-concrete trait collision). A pure model query skips the
interface and the projection trait entirely.

There is **no `toResult`/result-object** concept — a query projects to a
Spatie `Data` object, the cross-layer read contract
([../data-objects/conventions.md](../data-objects/conventions.md)).

## Call sites

```php
($q)()->forId($id)->firstOrFail();        // model — write path (an action)
($q)()->published()->toDataCollection();  // Collection<ArticleData> — read/response path
```

## Boundaries

- Queries never mutate state and never call external services.
- The **only** place composed Eloquent reads live; actions and
  controllers inject queries rather than writing `Model::query()->...`.
- Consumers: actions (reads), controllers (reads), jobs.
- A **cached** read is not a cache call inside the query — it is a `*CacheQuery`
  **decorator** over it ([../cache/reads.md](../cache/reads.md)). Populating the
  cache on a miss is allowed there (transparent derived state); the query itself
  still never mutates **domain** state.

## Tests

Query tests live in `tests/Unit/Queries` and resolve the query in
`beforeEach()`. Cover every filter, terminal, ordering rule, empty state,
and the `toData()` / `toDataCollection()` projection.

## Checklist

- Query is `final`, `strict_types`, `Query`-suffixed, in flat `app/Queries`;
  initialised in `__invoke()` with a clone; filters return `$this`.
- Terminals come from `QueriesRecords<TModel>` (generic trait), not copied
  or inherited.
- Return shape follows CQRS: terminal → model (write path); projection →
  `Data` (read/response path).
- Projection uses `TransformsToData<TModel, TData>` with a single-item
  `toData()`; the query implements `ReadsRecords` only when it projects.
- No model scopes; reusable read filters are query methods.
- No `toResult`/result objects — project to a Spatie `Data` object.
- Tests cover filters, terminals, ordering, empty state, and projection.
