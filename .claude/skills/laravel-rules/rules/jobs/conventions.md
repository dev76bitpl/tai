# Job Rules

## Purpose

Jobs orchestrate queued execution only. They must not contain business logic.

If a job needs to perform a business operation, inject the relevant action and call its `handle()` method from the job handler.

```php
final class ImportIndicatorObservationsJob implements ShouldQueue
{
    public function handle(ImportIndicatorObservations $importIndicatorObservations): void
    {
        $importIndicatorObservations->handle($this->indicatorObservationQueryData);
    }
}
```

## Dispatching

Dispatch timing and origin are governed by
[architecture/transactions.md](../architecture/transactions.md): jobs are
dispatched **only from actions**, and **only after commit**. This folder
does not restate those rules — see the canonical home.

## Checklist

- Job contains no business logic.
- Job delegates business operations to actions.
- Job dependencies are injected through `handle()` or the constructor.
- Dispatch origin/timing deferred to architecture/transactions.md.
