# Pipeline (pattern)

An **optional** composition technique: a workflow expressed as ordered,
swappable stages threading a mutable *traveller* through, each stage
doing one step and enriching the traveller before passing it on. Opted
into per-case (`patterns/`, see
[../architecture/placement.md](../architecture/placement.md)) — it is not
mandatory and it is **not an action kind**. A pipeline is how an
[orchestrator action](../actions/conventions.md) may structure its
internals; the action still owns the write and the transaction.

## Decision: pipeline or inline steps?

This is the heart of the file. Default to inline steps inside the
orchestrator. Reach for a pipeline only when the workflow has earned it.
Ask:

1. **Are the steps reorderable or conditional at runtime** — does the set
   or order of steps change by tenant, plan, feature flag, or input? If
   the steps are a fixed straight line that never varies, inline calls
   are clearer.

2. **Do steps need to be added/removed without touching the others** — is
   this a workflow you expect to grow new stages (enrichment,
   compliance, scoring) over time? A pipeline lets you register a stage
   without editing the orchestrator body.

3. **Are stages worth testing in isolation** — is each step substantial
   enough that testing it independently of the whole workflow pays off?

If you answered yes to **two or more**, a pipeline earns its indirection.
One yes (or none) → inline steps in the orchestrator; a pipeline would be
ceremony hiding a simple sequence.

**Why:** a pipeline trades a readable top-to-bottom method for a
registry of stages and a threaded traveller. That trade is worth it when
the workflow is genuinely variable or extensible, and a net loss when it
is a fixed three-step sequence — you pay the indirection and gain
nothing.

## Rule: inject the pipeline; never resolve it from the container

The `Pipeline` is a constructor dependency, like any other collaborator
(see [../architecture/dependency-injection.md](../architecture/dependency-injection.md)).
Do not reach for `app(Pipeline::class)` or the `Pipeline` facade inside
`handle()`.

**Why:** injecting it keeps the action's dependencies explicit and the
pipeline swappable in tests, consistent with the codebase-wide
inject-don't-facade policy.

## Rule: stages wrap actions — never make an action pipeline-aware

A stage is a thin adapter. It knows about the traveller and `$next`; it
delegates the actual work to an injected [action](../actions/conventions.md).
The action keeps its plain contract — `handle(Data): Result` — and never
learns it is inside a pipeline.

Do **not** build a dual-mode class that is both an action and a stage by
giving it a nullable `Closure $next = null` and branching on it. That
class has two contracts (`handle(Data): Result` *and*
`handle(Traveller, Closure): Traveller`), so it has none; its input and
return collapse to `mixed`, and the typed seam is gone.

**Why:** an action you can run standalone *and* reuse as a stage is the
real goal — and wrapping delivers it. The action stays pure, runnable in
isolation, and testable alone; the stage adapts it into the pipeline's
traveller/`$next` contract. A ~6-line adapter per stage is the price, and
it is far cheaper than the lost type coverage and the "am I in a
pipeline?" branch a merged class carries.

## Rule: the traveller is a dedicated mutable state object — not a data or value object

The object threaded through the stages is a *traveller*: a purpose-built
mutable state object that accumulates results as it moves down the line.
Each stage fills in the fields it produces (the created model, a computed
total) and returns it for the next stage.

It is **not** a data object and **not** a value object. Those are
immutable by rule ([../data-objects/conventions.md](../data-objects/conventions.md),
[../value-objects/conventions.md](../value-objects/conventions.md)) and
cannot carry forward state a later stage adds. Instead, the traveller
*holds* the immutable input data object (read-only) plus mutable slots
the stages populate. Back each slot with a nullable property the stages
set, and expose a non-null typed accessor the orchestrator reads — so a
stage that forgot to populate it fails loudly instead of leaking `null`.

**Why:** the whole point of a pipeline is that each stage contributes
something the next stage builds on. An immutable payload would force
every stage to clone-and-replace, defeating the threading; a mutable
traveller models "work in progress" directly. Keeping it a distinct
type — rather than reusing the input data object — preserves the
immutability rule for real data/value objects and makes the
"accumulating state" nature explicit.

## Rule: type the flow end to end — no `mixed` leaks

A stage's `handle()` returns the traveller, annotates `$next` as a
`Closure(Traveller): Traveller`, and the orchestrator closes the pipe
with `->then()` returning the concrete result type. Do not return `mixed`
from a stage or call `->thenReturn()` and dereference an untyped value.

**Why:** the stages are the workflow's seams; if they are typed, a static
analyzer catches a stage that reads a field the previous stage never set,
or returns the wrong shape. `mixed` at the seam erases exactly the
guarantees the pipeline exists to make checkable.

```php
// Good — mutable traveller seeded by the immutable input data object;
// each stage wraps a pure action; every seam is typed; result is non-null
final class RegisterOrganizationState
{
    public ?Organization $organization = null;

    public function __construct(
        public readonly RegisterOrganizationData $data, // immutable input
    ) {}

    public function organization(): Organization
    {
        return $this->organization
            ?? throw new LogicException('Organization stage did not run.');
    }
}

final class RegisterOrganization
{
    public function __construct(
        private readonly Pipeline $pipeline,
    ) {}

    public function handle(RegisterOrganizationData $data): Organization
    {
        return DB::transaction(fn (): Organization =>
            $this->pipeline
                ->send(new RegisterOrganizationState($data))
                ->through($this->stages())
                ->then(fn (RegisterOrganizationState $state): Organization => $state->organization())
        );
    }

    /** @return list<class-string> */
    private function stages(): array
    {
        return [
            CreateOrganizationStage::class,
            AttachOwnerStage::class,
            SeedDefaultRolesStage::class,
        ];
    }
}

final class CreateOrganizationStage
{
    // wraps the pure CreateOrganization action — the action stays
    // pipeline-unaware and runnable on its own
    public function __construct(
        private readonly CreateOrganization $createOrganization,
    ) {}

    /**
     * @param  Closure(RegisterOrganizationState): RegisterOrganizationState  $next
     */
    public function handle(RegisterOrganizationState $state, Closure $next): RegisterOrganizationState
    {
        $state->organization = $this->createOrganization->handle($state->data->organization());

        return $next($state); // later stages read $state->organization()
    }
}
```

```php
// Bad — dual-mode action with a nullable closure: two contracts, mixed
// in and out, pipeline-aware action, dead typed seam
final class CreateOrganization
{
    public function handle(mixed $input, ?Closure $next = null): mixed
    {
        $organization = /* ... */;

        return $next === null ? $organization : $next($input); // which am I?
    }
}
```

## Edge cases

- **Branching, not linear.** A pipeline is a straight line. If steps fan
  out or merge, it is the wrong shape — use an orchestrator with explicit
  branching, or model it as separate actions.
- **A stage needs to short-circuit.** Throw a business exception (the
  transaction rolls back) rather than returning a sentinel; do not let a
  stage silently return without calling `$next` unless "stop here" is a
  designed, documented outcome.
- **Side effects.** Stages stay write-only within the transaction; jobs
  and events fire from the orchestrator after commit
  ([../architecture/transactions.md](../architecture/transactions.md)),
  never inside a stage.

## Checklist

- Pipeline chosen via the Decision (≥2 of: reorderable/conditional,
  extensible, isolately testable) — not because "it's a pattern".
- `Pipeline` is injected via the constructor, not resolved from the
  container or the facade.
- Stages are declared in a method (e.g. `stages()`), not duplicated inline.
- Each stage wraps a pure action; no action carries a nullable `$next` or
  knows it is in a pipeline.
- The traveller is a dedicated mutable state object holding the immutable
  input — not a data object or value object pressed into service.
- Traveller slots are read through non-null typed accessors that throw if
  a stage skipped its job.
- Stage `handle()` returns the traveller, `$next` is annotated
  `Closure(Traveller): Traveller`, and the orchestrator closes with
  `->then()` — no `mixed` at any seam.
- No stage dispatches jobs or emits events; the orchestrator does, after
  commit.
- The orchestrator action still owns the transaction and the write.
- Each stage has its own test; the assembled pipeline has a workflow test.
