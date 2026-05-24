---
name: retro
description: "Project or sprint retrospective. Generates structured retro with action items saved to docs/. Invoke after a sprint, project milestone, incident, or launch. Actions: retro, retrospektywa, co poszło dobrze, co poszło źle, podsumowanie sprintu, post-mortem, co możemy poprawić."
---

# Retrospektywa

Ustrukturyzowana retro, która kończy się konkretnymi action itemami.

## Kiedy używać

Wywołaj po:
- Zakończeniu sprintu lub iteracji
- Launchu projektu lub ważnym milestone'ie
- Rozwiązaniu incydentu / problemu produkcyjnego
- Każdym okresie wartym podsumowania

## Protokół wywiadu

Zadaj wszystkie pytania w **jednej wiadomości**, poczekaj na odpowiedzi:

```
Kilka pytań do retrospektywy:

1. **Co poszło dobrze?**
   Konkretne rzeczy, nie ogólniki. Co chcemy powtórzyć?

2. **Co poszło źle lub było trudne?**
   Procesy, problemy techniczne, komunikacja, scope creep — cokolwiek.

3. **Co Cię zaskoczyło?**
   Rzeczy których nie przewidziałeś — dobre i złe.

4. **Gdybyś zaczynał od nowa — co zrobiłbyś inaczej?**
   Jedna–trzy rzeczy maksimum.

5. **Jakie są konkretne action itemy?**
   Format: [kto] robi [co] przed [kiedy]
```

## Format wyjścia

### 1. Podsumowanie (najpierw w czacie do akceptacji)

```markdown
## Retrospektywa — [projekt/sprint] — [data]

### ✅ Co poszło dobrze
- [konkret]

### ❌ Co poszło źle
- [konkret]

### 😲 Zaskoczenia
- [konkret]

### 🔄 Gdybym zaczynał od nowa
- [konkret]

### 🎯 Action items

| Co | Kto | Kiedy |
|----|-----|-------|
| [akcja] | [osoba/AI] | [data] |
```

### 2. Action items do `docs/TASKS.md`

Po akceptacji, dopisz do `docs/TASKS.md`:

```markdown
## Action items z retro [data]

- [ ] [akcja 1] — do [kiedy]
- [ ] [akcja 2] — do [kiedy]
```

## Zasady

- Action itemy muszą być konkretne i mieć termin — "poprawimy komunikację" to nie action item
- Minimum jeden action item na retro — brak oznacza, że retro nie była szczera
- Zapytaj "Zapisuję action items do `docs/TASKS.md`?" przed zapisem
- Przy incydencie: zaproponuj ADR jeśli ujawnił lukę architektoniczną
- Problemy opisuj jako kwestie systemowe/procesowe, nie ludzkie błędy
