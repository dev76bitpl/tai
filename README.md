# AI Project Template

Gotowy fundament do pracy z AI w projekcie. Klonujesz, wypełniasz domeną, zaczynasz.

---

## Co zawiera

| Plik | Opis |
|---|---|
| `CLAUDE.md` | Zasady pracy AI — jak się komunikujemy, commit workflow, zakazy, zasady kodu |
| `PROJECT_SCOPE.md` | Zakres systemu — co budujemy, dla kogo, po co |
| `docs/TASKS.md` | Bieżące zadania + log sesji |
| `docs/ROADMAP.md` | Kolejność faz i kryteria ukończenia |
| `docs/CONVENTIONS.md` | Konwencje kodu — naming, wzorce, error handling |
| `docs/UI_GUIDELINES.md` | Standardy UI — komponenty, layout, formularze, stany |
| `docs/SETUP.md` | Instrukcja środowiska deweloperskiego |
| `docs/TESTING.md` | Checklisty testów manualnych dla krytycznych flow |
| `docs/DELIVERY_CHECKLIST.md` | Standard domknięcia kroku |
| `docs/adr/` | Architecture Decision Records |
| `docs/AI_TEMPLATE_NOTES.md` | Zbierane dobre praktyki pracy z AI |

---

## Jak używać

1. Sklonuj repo
2. Wypełnij `PROJECT_SCOPE.md` — co budujesz, dla kogo, po co
3. Przejrzyj `CLAUDE.md` — dostosuj do swojego projektu (usuń przykłady domenowe)
4. Stwórz `ADR-001` w `docs/adr/` — kierunek techniczny systemu
5. Uzupełnij `docs/ROADMAP.md` — fazy i kolejność
6. Zacznij `docs/TASKS.md` od zadań fazy 1

---

## Filozofia

```
CLAUDE.md             = jak pracujemy
PROJECT_SCOPE.md      = co budujemy
docs/adr/             = dlaczego tak, a nie inaczej
```

AI czyta te pliki na początku każdej sesji. Im lepiej wypełnione, tym mniej wyjaśniania — więcej robienia.

---

## Jak ten template ewoluuje

Template jest żywy — rośnie razem z projektami które z niego korzystają.

Gdy w projekcie pojawia się zasada, wzorzec lub rozwiązanie które wygląda na uniwersalne:
1. AI wykrywa to w trakcie sesji i proponuje userowi sync do template
2. User + AI wspólnie decydują czy to faktycznie uniwersalne (nie domenowe)
3. Jeśli tak — AI edytuje pliki template w tej samej sesji i commituje

Zasada: wzorzec trafia tu bez nazwy projektu źródłowego. Template jest czysty — zero referencji do konkretnych domen.
