# Delivery Checklist

Standard domknięcia każdego kroku przed commitem.

---

## Kod

- [ ] `npm run lint` — brak błędów
- [ ] `npm run test` — wszystkie testy przechodzą
- [ ] `tsc --noEmit` — brak błędów typów
- [ ] brak `console.log`, `alert()`, `confirm()`, `prompt()`
- [ ] brak hardcoded wartości (sekrety, URL-e, dane środowiskowe)

## Testy

- [ ] testy jednostkowe dla nowej logiki domenowej
- [ ] testy integracyjne dla krytycznych flow (happy path + główny błąd)
- [ ] manualna weryfikacja happy path w przeglądarce

## Dokumentacja

- [ ] `docs/TASKS.md` — odhaczyć ukończone, dodać nowe
- [ ] `docs/ROADMAP.md` — zaktualizować status fazy jeśli dotyczy
- [ ] `docs/SETUP.md` — nowe komendy / pułapki jeśli dotyczy
- [ ] `docs/adr/` — nowy ADR jeśli była decyzja architektoniczna

## Commit

- [ ] format: `type(scope): description`
- [ ] kod + dokumentacja w jednym commicie
