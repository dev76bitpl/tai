---
name: debug
description: "Systematic debugging protocol. Invoke when stuck on a bug, unexpected behavior, error, or when random attempts haven't worked. Actions: debug, fix bug, nie działa, błąd, error, exception, coś się psuje, dlaczego to nie działa, szukam buga."
---

# Protokół debugowania

Systematyczne podejście do znajdowania i naprawiania bugów. Zatrzymuje spiralę "próbuję czegoś losowego".

## Kiedy używać

Wywołaj gdy:
- Bug istnieje, ale przyczyna jest niejasna
- Wypróbowano 2+ poprawek i żadna nie zadziałała
- Komunikat błędu nie wskazuje oczywistej przyczyny
- Zachowanie jest niespójne lub trudne do odtworzenia

## Protokół

### Krok 1 — Odtwórz

Zanim dotkniesz kodu:
- Czy możesz odtworzyć bug niezawodnie? Jeśli nie — znajdź warunek który go wywołuje
- Jaki jest **dokładny** komunikat błędu lub niepoprawne zachowanie?
- Jakie jest **oczekiwane** zachowanie?
- Kiedy się zaczął? Ostatni działający commit: `git bisect` jeśli niejasne

**Czerwona flaga:** Naprawianie buga którego nie możesz odtworzyć to zgadywanie, nie debugowanie.

### Krok 2 — Izoluj

Zawęź *gdzie* jest problem:

1. Jakie jest najmniejsze wejście które wywołuje buga?
2. Która warstwa nie działa — UI, API, logika biznesowa, baza, zewnętrzny serwis?
3. Dodaj tymczasowe logi na granicach, żeby zobaczyć co płynie w i z modułu
4. Zakomentuj / wyłącz części żeby znaleźć minimalny przypadek który nie działa

**Cel:** Jedna funkcja, jeden moduł, jedno zapytanie — nie "gdzieś w aplikacji".

### Krok 3 — Sformułuj hipotezy

Zanim napiszesz cokolwiek, wymień 2–3 konkretne hipotezy:

```
Hipoteza A: [konkretna rzecz która może powodować problem]
Hipoteza B: [alternatywna przyczyna]
Hipoteza C: [mniej prawdopodobna, ale warta sprawdzenia]
```

Uszereguj według prawdopodobieństwa. Testuj najpierw najbardziej prawdopodobną.

**Czerwona flaga:** "Myślę że może chodzić o..." bez uzasadnienia *dlaczego* → wróć do kroku 2.

### Krok 4 — Zweryfikuj hipotezę

Dla każdej hipotezy:
- Co byś zaobserwował gdyby hipoteza była prawdą?
- Dodaj celowy log / asercję / breakpoint żeby potwierdzić lub zaprzeczyć
- Jeszcze nie naprawiaj — najpierw potwierdź przyczynę

**Naprawiaj dopiero gdy możesz powiedzieć:** "Wiem że bug jest w X, bo widzę Y w logach."

### Krok 5 — Napraw

Po potwierdzeniu przyczyny:
- Zrób minimalną zmianę która naprawia przyczynę, nie symptom
- Nie refaktoruj otaczającego kodu przy okazji
- Dodaj test który wykryłby tego buga

### Krok 6 — Zweryfikuj naprawę

- Czy bug nadal się pojawia po naprawie? (nie powinien)
- Czy istniejące testy przechodzą?
- Czy są powiązane ścieżki które mogły być dotknięte?

## Format raportu

```
## Raport buga

**Symptom:** [co zaobserwował użytkownik/system]
**Przyczyna:** [rzeczywista przyczyna — jedno zdanie]
**Naprawa:** [co zostało zmienione]
**Test dodany:** tak / nie — [dlaczego nie, jeśli nie]
**Powiązane ryzyka:** [co jeszcze może nie działać]
```

## Zasady

- Nigdy nie pomijaj kroku 1 (odtworzenie) — naprawienie nieotwarzalnego buga to szczęście, nie inżynieria
- Po 2 nieudanych hipotezach: wróć do kroku 2 i izoluj głębiej
- Opieraj się pokusie refaktorowania przy debugowaniu — zmienia dwie rzeczy na raz
- Jeśli naprawa to "nie wiem dlaczego to działa" — to nie jest naprawa, to workaround; udokumentuj to
