---
name: deploy
description: "Pre-deployment checklist. Invoke before any production deploy, release, push to main, or go-live. Actions: deploy, release, wdrożenie, deploy na produkcję, wypuść wersję, go live, ship, publish, przed launchem."
---

# Checklist przed deployem

Weryfikacja przed wdrożeniem. Łapie rzeczy które bolą o 23:00.

## Kiedy używać

Wywołaj przed:
- Wypchnięciem na produkcję / merge do main
- Pierwszym deployem nowego projektu
- Deployem po większej zmianie (migracja DB, nowe env var, nowa integracja)

## Checklist

### 1. Kod
- [ ] Wszystkie testy przechodzą lokalnie
- [ ] Brak `console.log`, `debugger`, `dd()`, `die()` w kodzie
- [ ] Brak hardcoded sekretów, tokenów, haseł
- [ ] Feature branch zmergowany do main przez PR (nie push bezpośrednio na main)
- [ ] CHANGELOG zaktualizowany (jeśli projekt go używa)

### 2. Środowisko
- [ ] Wszystkie wymagane env vars ustawione w środowisku produkcyjnym
- [ ] Env vars zweryfikowane względem `.env.example` — brak brakujących kluczy
- [ ] Zewnętrzne API / webhooki wskazują na produkcję (nie sandbox)
- [ ] Poprawny connection string do produkcyjnej bazy

### 3. Baza danych
- [ ] Wszystkie migracje uruchomione (lub zaplanowane przed startem aplikacji)
- [ ] Migracja przetestowana na kopii produkcyjnych danych (jeśli ryzykowna)
- [ ] Backup zrobiony przed deployem (jeśli migracja jest destruktywna)

### 4. Infrastruktura
- [ ] DNS poprawny (rekord A, CNAME, zweryfikowany w panelu hostingu)
- [ ] Certyfikat SSL ważny i nie wygasa w ciągu 30 dni
- [ ] Cache CDN wyczyszczony (jeśli zmieniły się statyczne zasoby)

### 5. Plan cofnięcia
- [ ] Znany poprzedni tag / commit: `git log --oneline -5`
- [ ] Komenda do rollbacku znana: `git revert` / redeploy poprzedniego taga
- [ ] Jeśli migracja DB — wiadomo jak ją cofnąć (albo świadomie akceptujesz że jest jednostronna)
- [ ] Zespół poinformowany jeśli deploy dotyka współdzielonych systemów

### 6. Weryfikacja po deployemie
- [ ] Aplikacja ładuje się w przeglądarce
- [ ] Krytyczna ścieżka działa: logowanie / główna akcja / wysyłka formularza
- [ ] Brak błędów 5xx w logach przez pierwsze 5 minut
- [ ] Monitoring / alerty aktywne (jeśli skonfigurowane)

## Format raportu

```
## Gotowość do deploymentu

✅ Gotowe / ⚠️ Znalezione blokery

### Blokery (muszą być naprawione przed deployem)
- [pozycja]

### Ostrzeżenia (można deployować, ale obserwować)
- [pozycja]

### Zweryfikowane
- [liczba] pozycji sprawdzonych, wszystko OK
```

## Zasady

- Nigdy nie pomijaj sekcji 5 (plan cofnięcia) — "będzie OK" to nie plan
- Jeśli znaleziono bloker: zatrzymaj się, napraw, uruchom checklist od początku
- Pierwszy deploy projektu: pełna checklist, nawet jeśli wydaje się nadmiarowa
