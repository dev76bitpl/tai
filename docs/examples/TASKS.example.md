# Tasks — przykład wypełnienia

> **Wzór, nie dokument projektu.** Pokazuje, jak prowadzić `docs/TASKS.md` jako log sesji.
> Zostaje w projekcie na stałe jako odniesienie: pisz w `docs/TASKS.md`, tego pliku nie edytuj i nie usuwaj.

---

# Tasks

Ten plik jest **logiem sesji**: co się wydarzyło i dlaczego. Otwarta praca żyje w GitHub Issues
(`gh issue list`), nie tutaj — żadnych list „do zrobienia” ani backlogu. Fazy definiuje
[docs/ROADMAP.md](ROADMAP.md).

---

## Stan sesji

- 2026-03-12: **Lista zamówień da się filtrować po statusie i dacie (#14).** Po ludzku: żeby znaleźć
  zamówienie, trzeba było przewijać całą listę; teraz wyniki zawężają się od razu, także przy
  kilku filtrach naraz.
  Technicznie: parametry `status`, `from`, `to` w `GET /api/orders` (`src/app/api/orders/route.ts`),
  walidacja po stronie serwera, indeks `orders(status, created_at)` — bez niego zapytanie skanowało
  całą tabelę. Testy: `orders.filter.test.ts` (kombinacje filtrów, pusty wynik, zły zakres dat).
  Sprawdzone ręcznie na danych z produkcyjnej kopii: 12 tys. zamówień, odpowiedź poniżej 200 ms.
  Poza tematem sesji: wyszła potrzeba eksportu do CSV — świadomie odłożona, założone #19.

- 2026-03-08: **Logowanie, sesje i reset hasła działają (#7).** Po ludzku: klient loguje się
  mailem i hasłem, a zapomniane hasło resetuje linkiem z maila.
  Technicznie: sesje w bazie, nie w tokenie — decyzja i odrzucone alternatywy w ADR-002.
  Znaleziony przy okazji błąd: link resetu działał po wygaśnięciu tokenu; mały zakres, naprawiony
  w tej samej sesji, test regresji `reset.expired.test.ts`.

- 2026-03-05: **Start projektu.** Powstały `docs/PROJECT_SCOPE.md`, ADR-001 (stos) i `docs/ROADMAP.md`;
  zadania fazy 1 założone jako issues #1–#9. Sesja planistyczna, bez kodu.

---

Co ten wzór pokazuje:

- **wpis = jeden akapit na domknięty krok**, z datą i numerem issue; najnowszy na górze
- **dwie warstwy:** „po ludzku” (co użytkownik zobaczy, czym groził brak) i „technicznie”
  (pliki, funkcje, pułapki — kompletnie, żeby następna sesja nie odkrywała tego od nowa)
- **dygresje są nazwane:** co wyszło poza temat sesji i gdzie trafiło (nowe issue), a nie
  dopisane do listy w tym pliku
- **czego tu nie ma:** otwartych checkboxów, backlogu, „aktualnego fokusu” — to wszystko jest w issues
