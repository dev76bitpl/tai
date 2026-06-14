# Pluggable / strategy (pattern)

An **optional** technique: one contract (interface), several
interchangeable implementations, selected at runtime or bound in the
container. Opted into per-case (`patterns/`, see
[../architecture/placement.md](../architecture/placement.md)) — not
mandatory.

This is a *different axis* from [pipeline](pipeline.md). A pipeline
sequences **steps** of one workflow; a strategy swaps the **implementation**
of one step. They compose — a pipeline stage may depend on a strategy —
but do not confuse them: "ordered steps" is pipeline, "this same call,
different backend" is pluggable.

## Decision: strategy interface or a plain conditional?

Default to a `match`/`if` over a concrete call. Introduce a strategy
interface only when the indirection pays for itself. Ask:

1. **Do the branches vary along the same contract** — same inputs, same
   return shape, only the *how* differs (Stripe vs PayPal capture, S3 vs
   GCS upload)? If the branches return different shapes or take different
   inputs, they are not one strategy.

2. **Is the set of implementations open or external** — will third
   parties, packages, or per-tenant config add implementations you cannot
   enumerate in one `match`? An open set wants an interface + container
   binding; a closed, stable set of two or three is fine as a `match`.

3. **Does an implementation need its own dependencies** — does a branch
   pull in an SDK client, config, or collaborators? Constructor-injected
   implementations carry their own dependencies cleanly; a fat `match`
   arm cannot.

Two or more *yes* → a strategy interface earns its place. Otherwise a
`match` in the caller (often inside an action) is clearer and cheaper.

**Why:** a strategy interface adds a contract, N classes, and a binding
to read through. That is worth it when implementations are open,
self-contained, and uniform — and pure overhead when you have two stable
branches that a `match` states in four lines.

## Rule: the contract is an interface; implementations are injected, never `new`-ed or resolved inline

Define the contract as an interface in `app/Contracts/`
([../architecture/structure.md](../architecture/structure.md) — it's a
cross-cutting contract, not a block-internal seam). Consumers depend on the
**interface**, injected via the constructor
([../architecture/dependency-injection.md](../architecture/dependency-injection.md)).
Bind the implementation in a service provider — never `new
StripeGateway(...)` or `app(PaymentGateway::class)` inside business code.

**Why:** depending on the interface is what makes the implementation
swappable — including for a fake in tests. Newing or resolving inline
nails the consumer to one concrete class and defeats the entire pattern.

```php
// Good — interface contract, injected, implementation bound in a provider
interface PaymentGateway
{
    public function capture(Money $amount, PaymentToken $token): Capture;
}

final class StripeGateway implements PaymentGateway
{
    public function __construct(
        private readonly StripeClient $stripe,
    ) {}

    public function capture(Money $amount, PaymentToken $token): Capture
    {
        // ...
    }
}

final class CapturePayment // action depends on the contract, not Stripe
{
    public function __construct(
        private readonly PaymentGateway $gateway,
    ) {}

    public function handle(CapturePaymentData $data): Capture
    {
        return $this->gateway->capture($data->amount(), $data->token());
    }
}

// AppServiceProvider::register()
$this->app->bind(PaymentGateway::class, StripeGateway::class);
```

```php
// Bad — concrete class newed inside business code; not swappable, not fakeable
final class CapturePayment
{
    public function handle(CapturePaymentData $data): Capture
    {
        return (new StripeGateway(new StripeClient(config('services.stripe.secret'))))
            ->capture($data->amount(), $data->token());
    }
}
```

## Rule: select among implementations by binding, not by branching in the consumer

When the implementation depends on context (tenant, config, request),
choose it at the **binding** — a factory closure, contextual binding, or
a manager keyed by name — so the consumer still receives one resolved
contract and never sees the branch.

**Why:** if the consumer holds every implementation and `match`es over
them, you have rebuilt the conditional you were trying to remove, plus
the interface overhead. The selection belongs at the seam where the
contract is resolved.

```php
// Good — selection lives at the binding; consumers stay branch-free
$this->app->bind(PaymentGateway::class, function (Application $app): PaymentGateway {
    return match (config('billing.gateway')) {
        'paypal' => $app->make(PayPalGateway::class),
        default  => $app->make(StripeGateway::class),
    };
});
```

## Edge cases

- **Two stable implementations, no extra deps.** A `match` in the caller
  is the right call — do not reach for an interface (Decision above).
- **Branches diverge in shape.** Different inputs or return types mean
  these are not one strategy; model them as separate actions/methods.
- **Implementation needs request-scoped data.** Bind a factory closure or
  use contextual binding; do not pass the selector down into the
  consumer.

## Checklist

- Strategy chosen via the Decision (≥2 of: uniform contract, open set,
  self-contained deps) — not reflexively for two stable branches.
- The contract is an interface; consumers depend on it via constructor
  injection.
- Implementations are bound in a service provider, never `new`-ed or
  `app()`-resolved inside business code.
- Implementation selection lives at the binding (factory/contextual/
  manager), not as a `match` inside the consumer.
- Tests bind a fake/in-memory implementation of the contract
  ([../testing/conventions.md](../testing/conventions.md)).
