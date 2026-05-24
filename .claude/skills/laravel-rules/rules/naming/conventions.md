# Naming Rules

## Class Names

- Actions do not use the `Action` suffix.
- Action names start with the verb and then the affected subject or subjects.
- Services use the `Service` suffix.
- Queries use the `Query` suffix.
- Models do not use the `Model` suffix.
- Enums do not use the `Enum` suffix.
- Tests use the `Test` suffix.

Query names should describe the read operation, not just the aggregate. Prefer `ListUsersQuery`, `FindUserByEmailQuery`, or `ListStatisticsObservationsQuery` over broad names like `UserQuery`.

Action names must describe what the action does using a verb-first name. Put the subject or subjects after the verb.

- Orchestrator example: `RegisterOrganization`.
- Single-responsibility example: `CreateOrganization`.
- Single-responsibility example: `AttachUserToOrganization`.
- Avoid noun-only names like `OrganizationRegistration`.
- Avoid vague verbs like `HandleOrganization` or `ProcessUser`.

## Variables And Properties

Name variables and `$this` properties for the value they contain, not for how the value was obtained.

- Good: `$this->createWaitlistSignup = resolve(CreateWaitlistSignup::class);`
- Good: `$waitlistSignup = $this->createWaitlistSignup->handle($data);`
- Avoid: `$service`, `$result`, `$resolved`, `$action`, `$model` when a precise domain name is available.

For return values, use the concrete domain concept returned by the call. For actions named with verbs, the setup property may match the action class, while the handle result should match the returned model or result object.

## Examples

```php
beforeEach(function (): void {
    $this->createWaitlistSignup = resolve(CreateWaitlistSignup::class);
});

$waitlistSignup = $this->createWaitlistSignup->handle($createWaitlistSignupData);
```

Prefer domain-specific names over generic names:

- Use `$waitlistSignup`, not `$model`.
- Use `$indicatorDiscoveryResult`, not `$result`.
- Use `$ineIndicatorDataSource`, not `$service`.
