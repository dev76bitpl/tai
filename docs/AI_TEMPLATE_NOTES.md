# AI Template Notes

Dobre praktyki zebrane w trakcie pracy z AI. Aktualizowane na bieżąco — każda generyczna zasada niezależna od domeny trafia tutaj.

---

## Zasady pracy z AI (CLAUDE.md)

- **Zakaz `alert()/confirm()/prompt()`** — błędy inline lub dwukrokowy przycisk; `confirm()` = stan "potwierdź?" → akcja. Natywne dialogi JS łamią UX i są niekontrolowalne.
- **Zakaz hardcoded wartości** — config od dnia 1, nawet na dev; seed czyta z env, nie hardkoduje slugów/nazw/haseł.
- **Branch + PR workflow** — każda zmiana na osobnym branchu (`feat/`, `fix/`, `docs/`), merge przez PR; AI proponuje nazwę brancha na starcie sesji.
- **Off-plan digressions** — każde wyjście poza główny temat sesji notować w "Stan sesji" w TASKS.md z dopiskiem dlaczego; pozwala odróżnić cel sesji od dygresji.
- **Testy razem z kodem** — nie po fakcie; moduł bez testów nie jest domknięty.
- **Commit po każdym domkniętym kroku** — AI proponuje commit bez czekania na pytanie usera.

---

## Architektura / struktura projektu

- **Konfigurowalność przez JSON settings** — opcje formularzy (listy wyboru, parametry operacyjne) żyją w tabeli tenant/config jako JSON, nie w hardcoded tablicach; zmienialne bez migracji schematu.
- **Seed idempotentny z merge defaultów** — `upsert` + post-merge brakujących kluczy; nowe defaults trafiają do istniejących rekordów bez nadpisywania customizacji użytkownika.
- **`.env` vs `.env.local`** — narzędzia infrastrukturalne (Docker Compose) czytają `.env`, framework aplikacyjny (Next.js, Prisma) czyta `.env.local`; osobne pliki, osobne odpowiedzialności.

---

## Nawigacja / UX

- **Breadcrumbs od początku** — każdy widok szczegółowy potrzebuje breadcrumb i/lub "Wróć"; trudno dorobić globalnie po fakcie.
- **Spójność kolorów statusów** — jedno mapowanie (`getStatusMeta`) podpięte wszędzie: kalendarz, modal, dashboard, tabele; nie duplikować per-widok.
- **Dwukrokowy przycisk zamiast confirm()** — pierwsze kliknięcie = stan "potwierdź?", drugie = akcja; bezpieczny, sterowalny, zgodny z design systemem.
- **Audyt hardcoded opcji formularzy** — periodycznie sprawdzaj czy selekty/dropdowny nie używają hardcoded tablic zamiast czytać z konfiguracji per-tenant.

---

## Dokumentacja

- **CLAUDE.md** — zasady pracy AI, nie logika biznesowa; source of truth dla każdej maszyny i każdego developera.
- **ADR** — każda nieodwracalna decyzja architektoniczna dostaje ADR; bez tego "dlaczego tak" ginie po pierwszej rotacji w zespole.
- **TASKS.md jako log sesji** — "Stan sesji" na dole TASKS.md = historia co kiedy i dlaczego; nieocenione przy wznowieniu po przerwie lub zmianie maszyny.
- **SETUP.md z pułapkami** — nie tylko "jak zainstalować" ale "co poszło nie tak i jak naprawić"; pisać z rzeczywistych problemów, nie z wyobraźni.
