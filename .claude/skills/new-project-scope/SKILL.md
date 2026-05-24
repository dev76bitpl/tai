---
name: new-project-scope
description: "Project intake wizard. Guides user through 6 questions and generates docs/PROJECT_SCOPE.md + proposes ADR-001. Invoke at project start when PROJECT_SCOPE.md does not exist. Actions: new project, start project, define scope, create scope, what are we building, project setup, /scope."
---

# New Project Scope Wizard

Generates `docs/PROJECT_SCOPE.md` and proposes `ADR-001` from a short interview.

## When to Use

Invoke this skill when:
- Starting a new project and `docs/PROJECT_SCOPE.md` does not exist
- User types `/scope` or says "co budujemy" / "nowy projekt" / "zacznijmy od scope"
- User describes a product idea and expects a structured output

Do NOT invoke when `docs/PROJECT_SCOPE.md` already exists — edit it directly instead.

## Interview Protocol

Run the interview as **one message with all questions listed**, not one-by-one.
Wait for the user's answers, then generate the output in a single follow-up.

### Questions to ask (in Polish)

```
Zanim wygeneruję PROJECT_SCOPE.md, potrzebuję 6 odpowiedzi:

1. **Co budujemy?**
   Opisz produkt jednym zdaniem. (np. "Landing page kursu maturalnego", "SaaS do zarządzania zleceniami serwisowymi")

2. **Dla kogo?**
   Kim jest główny użytkownik? Co robi dziś bez tego produktu?

3. **Jaki jest cel #1?**
   Co musi się stać, żebyś powiedział "to działa"? (jedna konkretna rzecz)

4. **Co NIE wchodzi w zakres?**
   Wymień 2–3 rzeczy, których celowo nie budujemy w tej wersji.

5. **Stack i środowisko?**
   Technologia (np. Next.js + Postgres, HTML/Tailwind, WordPress), hosting, czy jest gotowe repo?

6. **Deadline i kontekst?**
   Kiedy musi działać? Czy jest jakiś zewnętrzny driver (launch, klient, event)?
```

## Output Format

After receiving answers, generate two artifacts:

### Artifact 1 — `docs/PROJECT_SCOPE.md`

```markdown
# Project Scope

## Produkt

[Jedno zdanie co to jest]

## Użytkownicy

**Główny użytkownik:** [kim jest]
**Kontekst użycia:** [co robi dziś bez produktu, jak produkt to zmienia]

## Cel #1

[Jedno zdanie — co musi być prawdą żeby projekt był sukcesem]

## Zakres MVP

### W zakresie
- [bullet: konkretna funkcjonalność]
- [bullet: ...]

### Poza zakresem (świadoma decyzja)
- [bullet: co nie wchodzi i dlaczego]
- [bullet: ...]

## Stack

| Warstwa       | Technologia              |
|---------------|--------------------------|
| Frontend      | [...]                    |
| Backend       | [...] lub brak           |
| Baza danych   | [...] lub brak           |
| Hosting       | [...]                    |
| CI/CD         | [...] lub do ustalenia   |

## Timeline

**Deadline:** [data lub "brak twardego deadlinu"]
**Driver:** [dlaczego ten termin / co się stanie jeśli się nie zdąży]

## Definicja "done" dla MVP

- [ ] [weryfikowalne kryterium 1]
- [ ] [weryfikowalne kryterium 2]
- [ ] [weryfikowalne kryterium 3]
```

### Artifact 2 — Proposed ADR-001

After generating PROJECT_SCOPE.md, immediately propose ADR-001 with this structure:

```markdown
# ADR-001: [Główna decyzja techniczna — zwykle wybór stacku lub architektury]

**Status:** proposed
**Data:** [today]

## Kontekst

[Dlaczego ta decyzja jest potrzebna — jaki problem rozwiązuje]

## Decyzja

[Co wybieramy i dlaczego — konkretnie]

## Odrzucone alternatywy

- **[Alternatywa A]** — [dlaczego nie]
- **[Alternatywa B]** — [dlaczego nie]

## Konsekwencje

- [Co to oznacza dla projektu — ograniczenia, zależności, co pilnować]
```

## Rules

- Generate PROJECT_SCOPE.md content directly in the chat first — let the user review before writing to file
- Ask "Zapisuję do `docs/PROJECT_SCOPE.md`?" before using the Write tool
- Use today's date in ADR-001 header
- Keep scope tight — if user lists 10 features, push back: "To brzmi jak 3 projekty. Co jest absolutnym minimum na start?"
- "Done when" criteria must be verifiable (observable behavior, not "działa")
- After writing the file, remind user to also stage it before the first commit: `git add docs/PROJECT_SCOPE.md docs/adr/ADR-001.md`
