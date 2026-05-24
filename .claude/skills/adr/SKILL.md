---
name: adr
description: "Architecture Decision Record generator. Invoke before writing an ADR, when making an architectural decision, choosing a technology, or documenting a non-obvious technical choice. Actions: ADR, decyzja architektoniczna, napisz ADR, udokumentuj decyzję, wybór technologii, architecture decision record."
---

# Generator ADR

Przeprowadza wywiad i generuje gotowy plik `docs/adr/ADR-NNN.md`.

## Kiedy używać

Wywołaj gdy:
- Wybierasz technologię, bibliotekę lub zewnętrzny serwis
- Decydujesz o strukturze modelu danych lub kontrakcie API
- Podejmujesz zmianę trudną do cofnięcia
- Odpowiadasz na pytanie "dlaczego tak zrobiliśmy?" po 6 miesiącach

Nie pisz ADR dla:
- Konwencji kodu → `docs/CONVENTIONS.md`
- Małych szczegółów implementacyjnych, łatwych do zmiany
- Rzeczy oczywistych z kodu

## Protokół wywiadu

Zadaj wszystkie pytania w **jednej wiadomości**, poczekaj na odpowiedzi, potem wygeneruj ADR.

```
Kilka pytań przed zapisem ADR:

1. **Jaka jest decyzja?**
   Opisz w jednym zdaniu.
   (np. "Używamy Formspree zamiast własnego backendu do obsługi formularza")

2. **Kontekst — dlaczego ta decyzja jest potrzebna?**
   Jaki problem rozwiązuje? Co by się stało bez tej decyzji?

3. **Co rozważałeś jako alternatywy?**
   Wymień 2–3 opcje które brałeś pod uwagę.

4. **Dlaczego wybrałeś właśnie to?**
   Konkretne powody: koszt, czas, team, ryzyko, technologia.

5. **Jakie są znane konsekwencje lub ograniczenia?**
   Co będzie trudniejsze? Na co uważać?
```

## Format wyjścia

```markdown
# ADR-[NNN]: [Tytuł — jedna decyzja, jedno zdanie]

**Status:** accepted
**Data:** [YYYY-MM-DD]

## Kontekst

[Dlaczego ta decyzja jest potrzebna. Jaki problem rozwiązuje.]

## Decyzja

[Co wybieramy — konkretnie, jedno–dwa zdania.]

**Uzasadnienie:**
- [Powód 1]
- [Powód 2]

## Odrzucone alternatywy

| Opcja | Dlaczego odrzucona |
|-------|--------------------|
| [A]   | [powód]            |
| [B]   | [powód]            |

## Konsekwencje

**Ułatwia:**
- [co]

**Utrudnia / wymaga uwagi:**
- [co]
```

## Numerowanie

Przed zapisem sprawdź istniejące ADR:
```bash
ls docs/adr/
```
Użyj kolejnego numeru: `ADR-001`, `ADR-002` itd.

## Zasady

- Jeden ADR = jedna decyzja — jeśli dwie decyzje są powiązane, wyjaśnij to w "Kontekst"
- "Wybraliśmy X" to za mało — zawsze wyjaśnij *dlaczego nie Y*
- Status zaczyna jako `accepted`, chyba że decyzja jest nadal otwarta (`proposed`)
- Wygeneruj treść w czacie do przeglądu, potem zapytaj "Zapisuję do `docs/adr/ADR-NNN.md`?"
- Przypomnij o stagowaniu: `git add docs/adr/ADR-NNN.md`
