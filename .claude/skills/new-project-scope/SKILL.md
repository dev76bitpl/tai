---
name: new-project-scope
description: "Wizard inicjalizacji projektu. Prowadzi interaktywny wywiad (pytania po jednym, z dopytaniem), generuje docs/PROJECT_SCOPE.md + ADR-001 i ustawia stos projektu dla strażników commita. Uruchom gdy użytkownik napisze: scope, zdefiniuj scope, nowy projekt, co budujemy, zacznijmy projekt, zakres projektu, project scope."
---

# New Project Scope Wizard

Generates `docs/PROJECT_SCOPE.md`, proposes `ADR-001` and sets the project's stack for the commit guards — all from one interactive interview.

## When to Use

Invoke this skill when:
- Starting a new project that has no brief yet (see the three states below)
- User types `/scope` or says "co budujemy" / "nowy projekt" / "zacznijmy od scope"
- `new-project.py` started this session with the single word `scope`
- User describes a product idea and expects a structured output

First check which state `docs/PROJECT_SCOPE.md` is in — a project starts either from zero or
with a brief already written:

| State of `docs/PROJECT_SCOPE.md` | What to do |
|---|---|
| Missing | Run the interview |
| Template skeleton — still contains the line "sekcje są scaffoldem" | Same as missing: run the interview and **replace** the skeleton |
| Filled with the project's own content | Do NOT interview again and do not overwrite it. Read its stack section and do only Artifact 3 (stack for the commit guards). To change the brief, edit the file directly |

## Interview Protocol

Run the interview **interactively: one question at a time**. Ask, wait for the answer, react to
it, then ask the next one. Never send the whole list in one message — a wall of six questions
gets six thin answers.

- Use the interactive question tool (`AskUserQuestion`) when it is available: one question per
  call, a few ready options where the choice is closed, free text always possible. Without the
  tool, ask in plain chat — still one question per message.
- Start with one line saying how it will go, e.g. "Zadam kilka pytań po kolei — zwykle sześć,
  czasem mniej, czasem dopytam."
- All questions in Polish.

### Default topics (six — a starting point, not a quota)

Go through them in this order, skipping any the user has already answered (in their opening
message, or visibly in the repo — e.g. do not ask whether a repository exists when it does):

1. **Co budujemy?** — produkt jednym zdaniem (np. "Landing page kursu maturalnego", "SaaS do zarządzania zleceniami serwisowymi")
2. **Dla kogo?** — kim jest główny użytkownik i co robi dziś bez tego produktu
3. **Jaki jest cel #1?** — jedna konkretna rzecz, po której powiesz "to działa"
4. **Co NIE wchodzi w zakres?** — 2–3 rzeczy, których celowo nie budujemy w tej wersji
5. **Stack i środowisko?** — technologia, hosting. Offer the stacks from `python3 scripts/set-stack.py --list` as options (plus "inny / jeszcze nie wiem"); the answer also drives Artifact 3
6. **Deadline i kontekst?** — kiedy musi działać i czy jest zewnętrzny powód terminu (launch, klient, wydarzenie)

### Follow-up questions (dopytanie)

The six topics rarely cover a real project. Dig where the brief would otherwise contain a guess:

- **Right after an answer**, when it is vague ("coś jak sklep"), too broad (ten features for an
  MVP), or contradicts an earlier one — ask one follow-up before moving to the next topic.
- **After the default topics**, ask about whatever this particular project still leaves open.
  Typical gaps: roles and who may do what; the core entity the system revolves around; payments
  and other integrations; where the content or data comes from; languages; personal data and
  legal constraints; how the goal will be measured.
- **Ask only what changes the brief.** If the answer would not alter any section of
  PROJECT_SCOPE.md or ADR-001, do not ask.
- **Fewer than six is fine** when the user's opening message already covered the topics.
- **Do not interrogate.** At most two follow-ups per topic. When the user says "nie wiem" or
  "wystarczy", write the point into the brief as "do ustalenia" instead of pressing.

Stop when every section of the brief can be written without inventing anything. Say so in one
line ("Mam komplet — N pytań") and move to the output.

## Output Format

After receiving answers, generate two artifacts and set the stack (Artifact 3):

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

### Artifact 3 — stack for the commit guards

The answer to question 5 decides where the commit guards look for code and which platform
ADR patterns are active. The user is never asked about directories and never edits the config
by hand — you set it from their stack answer:

1. Map the answer to one name from the table (`python3 scripts/set-stack.py --list` prints it):

   | Answer mentions | Stack |
   |---|---|
   | Next.js, React, Node, TypeScript, Vue, Svelte | `node` |
   | Laravel | `laravel` |
   | Symfony | `symfony` |
   | WordPress, WooCommerce | `wordpress` |
   | PrestaShop | `prestashop` |
   | Magento | `magento` |
   | Python, Django, FastAPI, Flask | `python` |
   | Go | `go` |
   | Rails, Ruby | `rails` |
   | anything else, static HTML, SaaS platform (e.g. Shoper), undecided | `inny` |

2. Say in one line what you are about to set and ask, e.g. "Ustawiam strażników pod Laravel
   (kod w `app/`) — ok?" — together with the question about writing PROJECT_SCOPE.md.
3. After "tak" run `python3 scripts/set-stack.py <stack>` and show its output. It writes
   `src_dirs` and the platform ADR group into `.claude/hooks/config.json`.
4. If the project keeps its code elsewhere than the table assumes (the user said so, or the
   repo already shows it), run the script first and then correct `src_dirs` in
   `.claude/hooks/config.json` — tell the user which directories you set and why.

Running the script again with another stack is safe: it switches the previous platform group off.

If `scripts/set-stack.py` does not exist (a project started before this script was added to the
template), do not improvise the config by hand: skip this artifact and tell the user in one
line that the guards stay on their defaults until the script is copied from the template.

## Rules

- Generate PROJECT_SCOPE.md content directly in the chat first — let the user review before writing to file
- Ask "Zapisuję do `docs/PROJECT_SCOPE.md`?" before using the Write tool
- Use today's date in ADR-001 header
- Keep scope tight — if user lists 10 features, push back: "To brzmi jak 3 projekty. Co jest absolutnym minimum na start?"
- "Done when" criteria must be verifiable (observable behavior, not "działa")
- After writing the files, remind user to also stage them before the first commit: `git add docs/PROJECT_SCOPE.md docs/adr/ADR-001.md .claude/hooks/config.json`
- Do not ask the user where the code lives — derive it from the stack answer (Artifact 3)
