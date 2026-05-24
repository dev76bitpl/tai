---
name: symfony
description: "Symfony application development: DDD/CQRS architecture, Messenger, API Platform, Doctrine, services & DI, forms, security, console commands, best practices. Invoke when working on Symfony project. Actions: symfony, architektura symfony, messenger, api platform, doctrine symfony, ddd symfony, cqrs symfony, symfony service, symfony event, symfony form."
---

# Symfony Development

Przewodnik po budowaniu aplikacji Symfony zgodnie z DDD/CQRS, Messenger i API Platform.

## Kiedy używać

Wywołaj gdy:
- Projektujesz lub implementujesz warstwową architekturę DDD w Symfony
- Używasz Symfony Messenger (komendy, zdarzenia, kolejki)
- Budujesz API z API Platform
- Pracujesz z Doctrine ORM (encje, repozytoria, migracje)
- Piszesz serwisy, command handlers, event listeners
- Konfigurujesz DI Container, tagi, compiler passes

## Architektura warstwowa (DDD)

```
src/
  Domain/           # logika biznesowa — bez zależności od frameworka
    Model/          # encje, agregaty, Value Objects
    Repository/     # interfejsy repozytoriów
    Event/          # zdarzenia domenowe
    Exception/      # wyjątki domenowe
  Application/      # use-casy, komendy, zapytania, handlery
    Command/
    Query/
    Handler/
    DTO/
  Infrastructure/   # implementacje: Doctrine, HTTP, queue, cache
    Repository/     # implementacje interfejsów z Domain
    Persistence/    # mapowania Doctrine
  Presentation/     # kontrolery, formy, API resource
    Controller/
    Form/
    ApiResource/
```

## Value Objects

```php
final readonly class Email
{
    public function __construct(public readonly string $value)
    {
        if (!filter_var($value, FILTER_VALIDATE_EMAIL)) {
            throw new \InvalidArgumentException("Invalid email: $value");
        }
    }

    public function equals(self $other): bool
    {
        return $this->value === $other->value;
    }
}
```

```php
final readonly class Money
{
    public function __construct(
        public readonly int $amount,    // grosze/centy
        public readonly string $currency
    ) {
        if ($amount < 0) {
            throw new \InvalidArgumentException('Amount cannot be negative');
        }
    }

    public function add(self $other): self
    {
        if ($this->currency !== $other->currency) {
            throw new \LogicException('Cannot add different currencies');
        }
        return new self($this->amount + $other->amount, $this->currency);
    }
}
```

## Repository — interfejs w Domain, implementacja w Infrastructure

```php
// Domain/Repository/UserRepositoryInterface.php
interface UserRepositoryInterface
{
    public function findById(UserId $id): ?User;
    public function findByEmail(Email $email): ?User;
    public function save(User $user): void;
    public function remove(User $user): void;
}

// Infrastructure/Repository/DoctrineUserRepository.php
final class DoctrineUserRepository implements UserRepositoryInterface
{
    public function __construct(private readonly EntityManagerInterface $em) {}

    public function findById(UserId $id): ?User
    {
        return $this->em->find(User::class, $id->value);
    }

    public function save(User $user): void
    {
        $this->em->persist($user);
        $this->em->flush();
    }
}
```

## CQRS — Command + Handler

```php
// Application/Command/RegisterUser.php
final readonly class RegisterUser
{
    public function __construct(
        public readonly string $email,
        public readonly string $name,
        public readonly string $password,
    ) {}
}

// Application/Handler/RegisterUserHandler.php
final readonly class RegisterUserHandler
{
    public function __construct(
        private readonly UserRepositoryInterface $users,
        private readonly PasswordHasherInterface $hasher,
        private readonly ClockInterface $clock,
    ) {}

    public function __invoke(RegisterUser $command): void
    {
        $email = new Email($command->email);

        if ($this->users->findByEmail($email) !== null) {
            throw new UserAlreadyExistsException($email);
        }

        $user = User::register(
            id: UserId::generate(),
            email: $email,
            name: $command->name,
            hashedPassword: $this->hasher->hash($command->password),
            registeredAt: $this->clock->now(),
        );

        $this->users->save($user);
    }
}
```

## Symfony Messenger

### Konfiguracja

```yaml
# config/packages/messenger.yaml
framework:
    messenger:
        transports:
            async:
                dsn: '%env(MESSENGER_TRANSPORT_DSN)%'
                retry_strategy:
                    max_retries: 3
                    delay: 1000
                    multiplier: 2
        routing:
            App\Application\Command\RegisterUser: async
            App\Application\Event\UserRegistered: async
        failure_transport: failed
```

### Command Bus vs Event Bus

```php
// Komenda — jeden handler, synchroniczna lub async
$commandBus->dispatch(new RegisterUser($email, $name, $password));

// Zdarzenie domenowe — wiele handlerów, async
$eventBus->dispatch(new UserRegistered($userId, $email));
```

```php
// Handler zdarzenia
final class SendWelcomeEmailOnUserRegistered
{
    public function __construct(private readonly MailerInterface $mailer) {}

    public function __invoke(UserRegistered $event): void
    {
        $this->mailer->send(/* ... */);
    }
}
```

### Zasady Messenger

- Przekazuj ID encji, nie encje — encja może się zmienić zanim handler wykona
- Handlery muszą być idempotentne — wiadomość może przyjść dwa razy
- Zdarzenia wersjonuj gdy je kolejkujesz (`UserRegisteredV2`)
- Nie odwołuj się do stanu aplikacji sprzed dispatchu — handler działa asynchronicznie

## API Platform

### State Provider (odczyt)

```php
#[ApiResource(
    operations: [new Get()],
    provider: UserProvider::class,
)]
final class UserResource
{
    public function __construct(
        public readonly string $id,
        public readonly string $email,
        public readonly string $name,
    ) {}
}
```

```php
final class UserProvider implements ProviderInterface
{
    public function __construct(
        private readonly UserRepositoryInterface $users,
        private readonly UserResourceMapper $mapper,
    ) {}

    public function provide(Operation $operation, array $uriVariables = [], array $context = []): ?UserResource
    {
        $user = $this->users->findById(new UserId($uriVariables['id']));
        return $user ? $this->mapper->toResource($user) : null;
    }
}
```

### State Processor (zapis)

```php
final class CreateUserProcessor implements ProcessorInterface
{
    public function __construct(private readonly MessageBusInterface $bus) {}

    public function process(mixed $data, Operation $operation, array $uriVariables = [], array $context = []): UserResource
    {
        $this->bus->dispatch(new RegisterUser($data->email, $data->name, $data->password));
        return new UserResource(/* ... */);
    }
}
```

## Doctrine — encja z UUID

```php
#[ORM\Entity]
#[ORM\Table(name: 'users')]
class User
{
    #[ORM\Id]
    #[ORM\Column(type: 'uuid')]
    private string $id;

    #[ORM\Column(type: 'string', unique: true)]
    private string $email;

    #[ORM\Column(name: 'created_at')]
    private \DateTimeImmutable $createdAt;

    public static function register(UserId $id, Email $email, string $hashedPassword, \DateTimeImmutable $registeredAt): self
    {
        $user = new self();
        $user->id = $id->value;
        $user->email = $email->value;
        $user->hashedPassword = $hashedPassword;
        $user->createdAt = $registeredAt;
        return $user;
    }
}
```

## Dependency Injection

```yaml
# config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true

    App\:
        resource: '../src/'
        exclude:
            - '../src/Domain/Model/'
            - '../src/Kernel.php'

    # Bind interfejs do implementacji
    App\Domain\Repository\UserRepositoryInterface:
        class: App\Infrastructure\Repository\DoctrineUserRepository
```

```php
// Tagi dla wielu implementacji (Strategy/Chain of Responsibility)
#[AsTaggedItem('notification.channel')]
final class EmailNotificationChannel implements NotificationChannelInterface {}

#[AsTaggedItem('notification.channel')]
final class SmsNotificationChannel implements NotificationChannelInterface {}
```

## Zdarzenia domenowe — dyspatch po flush

```php
final class User
{
    private array $domainEvents = [];

    public static function register(/* ... */): self
    {
        $user = new self(/* ... */);
        $user->domainEvents[] = new UserRegistered($user->id);
        return $user;
    }

    public function pullDomainEvents(): array
    {
        $events = $this->domainEvents;
        $this->domainEvents = [];
        return $events;
    }
}

// Doctrine Listener — dispatchuje zdarzenia po flush
final class DomainEventDispatcher implements EventSubscriberInterface
{
    public function __construct(private readonly EventBusInterface $bus) {}

    public static function getSubscribedEvents(): array
    {
        return [Events::postFlush => 'onPostFlush'];
    }

    public function onPostFlush(PostFlushEventArgs $args): void
    {
        foreach ($args->getObjectManager()->getUnitOfWork()->getIdentityMap() as $entities) {
            foreach ($entities as $entity) {
                if (!method_exists($entity, 'pullDomainEvents')) continue;
                foreach ($entity->pullDomainEvents() as $event) {
                    $this->bus->dispatch($event);
                }
            }
        }
    }
}
```

## Console Command

```php
#[AsCommand(name: 'app:users:send-report', description: 'Send weekly user report')]
final class SendUserReportCommand extends Command
{
    public function __construct(private readonly MessageBusInterface $bus)
    {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addOption('dry-run', null, InputOption::VALUE_NONE, 'Do not actually send');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);

        if ($input->getOption('dry-run')) {
            $io->note('Dry run — nothing sent');
            return Command::SUCCESS;
        }

        $this->bus->dispatch(new SendUserReport());
        $io->success('Report dispatched');
        return Command::SUCCESS;
    }
}
```

## Migracje Doctrine

```bash
# Wygeneruj migrację na podstawie różnicy encji
php bin/console doctrine:migrations:diff

# Wykonaj migracje
php bin/console doctrine:migrations:migrate

# Status migracji
php bin/console doctrine:migrations:status

# NIGDY nie edytuj wykonanej migracji — stwórz nową
```

## Bezpieczeństwo

```php
// Voter — autoryzacja zasobu
final class UserVoter extends Voter
{
    protected function supports(string $attribute, mixed $subject): bool
    {
        return in_array($attribute, ['USER_EDIT', 'USER_DELETE'])
            && $subject instanceof User;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $currentUser = $token->getUser();
        return match ($attribute) {
            'USER_EDIT'   => $subject->getId() === $currentUser->getId(),
            'USER_DELETE' => $this->security->isGranted('ROLE_ADMIN'),
            default       => false,
        };
    }
}
```

```php
// W kontrolerze
$this->denyAccessUnlessGranted('USER_EDIT', $user);
```

## Anti-patterns — czego unikać

| Anti-pattern | Zamiast tego |
|-------------|-------------|
| Logika biznesowa w kontrolerze | Przenieś do Command + Handler |
| `$em->flush()` wewnątrz encji | Flush tylko w repozytoriach / serwisach aplikacyjnych |
| Dostęp do `Request` w serwisach domenowych | Mapuj do DTO w kontrolerze, przekazuj DTO |
| Zdarzenia dispatchowane przed `flush()` | Dispatch po `postFlush` (Doctrine listener) |
| Jedna duża klasa `AppService` | Osobne handlery per use-case |
| Bezpośrednie `new` na serwisach | Wstrzykiwanie przez konstruktor |
| `$request->get()` bez walidacji | FormType lub DTO z walidacją |

## Checklist przed wdrożeniem

- [ ] `APP_ENV=prod`, `APP_DEBUG=false` w `.env.local.php`
- [ ] Cache ciepły: `php bin/console cache:warmup --env=prod`
- [ ] Migracje wykonane: `php bin/console doctrine:migrations:migrate --no-interaction`
- [ ] Brak `var_dump`, `dd()`, `dump()` w kodzie produkcyjnym
- [ ] Secrets w `.env.local` / Symfony Secrets Vault — nie w repozytorium
- [ ] PHPStan (poziom 8+) bez błędów
- [ ] Testy jednostkowe handlerów przechodzą
- [ ] Retry strategy skonfigurowany dla async transportów
- [ ] Failed transport skonfigurowany (nie `null`)

## Przydatne komendy

```bash
# DI — sprawdź co jest zaresjestrowane
php bin/console debug:container UserRepository
php bin/console debug:autowiring

# Routing
php bin/console debug:router
php bin/console router:match /api/users/1

# Messenger
php bin/console messenger:consume async --limit=10
php bin/console messenger:failed:show
php bin/console messenger:failed:retry

# Cache
php bin/console cache:clear
php bin/console cache:warmup

# Doctrine
php bin/console doctrine:schema:validate
php bin/console doctrine:migrations:list
```
