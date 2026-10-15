# ADR-006 — Dołączenie do projektu przez doctor, aktualizacja z szablonu skryptem z podglądem

**Status:** accepted
**Data:** 2026-10-14

## Kontekst

Projekt z szablonu przeżywa trzy sytuacje. Tylko pierwsza jest dziś obsłużona porządnie:

1. **Nowy projekt** — `new-project.py --init` i prowadzone kroki startu (ADR-005).
2. **Dołączenie do istniejącego projektu** (nowa osoba, nowy komputer, powrót po czasie) —
   `scripts/doctor.py` sprawdza środowisko i przy brakach podaje polecenie naprawcze
   (np. `scripts/doctor.py:166` — `pre-commit install …`, `scripts/doctor.py:209` — `pytest`),
   ale README projektu o nim nie mówi: `README_SCAFFOLD` w `scripts/new_project_data.py:30`
   nie wspomina doctora. Kto sklonował projekt, nie wie, że strażnicy i hooki nie są podpięte.
3. **Wciągnięcie poprawek z szablonu** — działa tylko dla skilli: `update-skills.py --sync`
   kopiuje `SYNC_PATHS` (`scripts/update-skills.py:295`: manifest, `.claude/skills`, sam skrypt,
   `.gitleaksignore`), a hook startu sesji robi to automatycznie
   (`.claude/hooks/session-context.py`, `check_template_skills_sync`). Strażnicy commita
   (`scripts/dev-guards/`), hooki Claude Code (`.claude/hooks/`), skrypty startu i doctor oraz
   `docs/GUARDS.md` i `docs/GUARDS_TESTING.md` są przenoszone ręcznie, plik po pliku.
   Hook startu sesji porównuje wprawdzie `.claude/hooks/*.py` z szablonem (`check_template_sync`,
   `session-context.py:128`), ale z **katalogiem roboczym** klona szablonu, więc widzi także
   niewydane zmiany — tę samą klasę błędu #179 usunął przy skillach. Sam porównuje tylko hooki
   i nie podpowiada, co zrobić.

Skutek: projekty starzeją się po cichu. Poprawka strażnika w szablonie (np. #181, #185, #193)
nie dociera do projektów, które powstały wcześniej, i nikt o tym nie wie.

## Decyzje i uzasadnienia

1. **Dołączenie do projektu zaczyna się od doctora.** README projektu (`README_SCAFFOLD`)
   mówi wprost: po sklonowaniu uruchom `python3 scripts/doctor.py` i wykonaj polecenia, które
   poda. Każdy brak w raporcie doctora ma polecenie naprawcze. Bez `--fix` — doctor wskazuje,
   człowiek wykonuje. Dlaczego: doctor już umie prawie wszystko, brakuje drogowskazu;
   `--fix` dopiero wtedy, gdy ręczne polecenia okażą się realnym kłopotem (reguła 17).

2. **Aktualizacja z szablonu to skrypt `scripts/update-from-template.py` z podglądem.**
   Domyślnie pokazuje, które pliki należące do szablonu różnią się od wydanej wersji;
   kopiuje dopiero po `--apply`. Dlaczego: ręczne przenoszenie plik po pliku się nie dzieje,
   a ciche nadpisywanie zmienia zachowanie strażników bez wiedzy człowieka.
   Odrzucone: sam opis przebiegu w dokumentacji — nikt go nie wykonuje, dowodem jest stan
   projektów sprzed #181.

3. **Źródłem jest wydany `main` szablonu, nie jego katalog roboczy** — ten sam mechanizm co
   skille (`released_snapshot()` w `update-skills.py`, #179). Dlaczego: niewydana praca
   w szablonie nie może wyciekać do projektów (incydent z 13.10, #179).

4. **Lista plików należących do szablonu jest jawna i w jednym miejscu** (strażnicy commita,
   hooki Claude Code, skrypty startu i doctor, `docs/GUARDS.md`, `docs/GUARDS_TESTING.md`).
   Pliki wyłącznie szablonowe (`TEMPLATE_ONLY_SCRIPTS`, `docs/TEMPLATE_TESTING.md`) i pliki
   projektu (`config.json`, `docs/*` poza powyższymi) nie są na niej nigdy. Test pilnuje, że
   każdy plik z listy istnieje w szablonie.

5. **Plik zmieniony w projekcie nie jest nadpisywany.** Skrypt rozpoznaje go (treść nie
   odpowiada żadnej wydanej wersji szablonu) i wymienia jako „zmieniony lokalnie — porównaj
   ręcznie”. Dlaczego: lokalna zmiana bywa świadomym odejściem (ADR-002, `[skip-sync]`);
   nadpisanie jej to utrata pracy.

6. **`CLAUDE.md` tylko porównywany, nigdy podmieniany.** Skrypt pokazuje sekcje, które
   w szablonie są nowe albo inne. Dlaczego: plik miesza reguły ogólne z regułami projektu,
   a podział na sekcje nie jest egzekwowany kodem — automatyczne scalanie byłoby zgadywaniem.

7. **Hook startu sesji tylko informuje.** Zastępuje dzisiejsze porównanie samych hooków
   (`check_template_sync`) porównaniem całej listy z decyzji 4 wobec wydanego `main` i mówi
   jednym zdaniem: „szablon ma zmiany w N plikach → `python3 scripts/update-from-template.py`”.
   Niczego nie kopiuje. Dlaczego inaczej niż skille (te hook synchronizuje sam): skill dodaje
   wiedzę, strażnik zmienia to, co blokuje commit — taka zmiana wymaga decyzji człowieka.

8. **O automatycznym sprawdzaniu decyduje szablon, jednym przełącznikiem.** Klucz w
   `.claude/hooks/config.json` szablonu, czytany z wydanego `main` klonu (jak w decyzji 3).
   Włączony: hook startu sesji w każdym projekcie sam dociąga `main` szablonu (`git fetch`
   w klonie, najwyżej raz na dobę, z limitem czasu; bez sieci porównuje z tym, co klon ma)
   i porównuje. Wyłączony: hook nie sprawdza nic, zostaje ręczne uruchomienie skryptu.
   Projekt nie ma własnego przełącznika. Dlaczego: decyzja właściciela — sprawdzanie ma
   zależeć od szablonu, włączane raz dla wszystkich projektów, a nie projekt po projekcie.
   Odrzucone: przełącznik na komputerze (`~/.config/76bit/`) — trzeba by go ustawiać na
   każdej maszynie; pobieranie przy każdej sesji — każdy start czekałby na sieć.

9. **Dwie paczki.** Najpierw decyzja 1 (mała, od razu przydatna), potem decyzje 2–8.

## Konsekwencje

- Poprawki strażników docierają do starszych projektów przy najbliższej sesji jako
  podpowiedź, a nie po przypadkowym odkryciu.
- Każdy nowy plik szablonu, który ma jechać do projektów, trzeba dopisać do listy
  z decyzji 4 — inaczej aktualizacja go nie zobaczy (test pilnuje tylko istnienia).
- Projekty sprzed tego ADR dostają `update-from-template.py` razem z synchronizacją skilli
  (`update-skills.py --sync`, który hook startu sesji uruchamia sam). To jedyny plik szablonu
  podmieniany bez pytania — wolno, bo sam niczego nie zmienia bez `--apply` (decyzja właściciela
  z 2026-10-14). Skrypt nie ogłasza się sam w starym projekcie: hook sprzed ADR-006 o nim nie wie,
  więc pierwsze `--apply` uruchamia człowiek (README, sekcja „Istniejący projekt”).
  Sprostowanie (2026-10-15, #201, próba kursu): w starym projekcie to wymaga **dwóch** przebiegów
  `update-skills.py --sync --apply` — pierwszy podmienia sam skrypt synchronizacji (stary nie zna
  `update-from-template.py`), dopiero drugi dokłada aktualizację. Samo `update-skills.py` bez `--sync` nie robi
  nic ze skryptami szablonu. Kolejność kroków: README, „Poprawki z szablonu”.
- Synchronizacja skilli stosuje tę samą regułę co aktualizacja plików (#201, decyzja właściciela 2026-10-15):
  skill z plikiem, którego treści nie było w żadnej wersji szablonu, jest „zmieniony lokalnie” — nie jest
  nadpisywany ani przy ręcznym `--sync --apply`, ani przy automatycznej synchronizacji na starcie sesji; hook
  zgłasza go do porównania zamiast „Pobrano”. Do rozpoznania potrzebna jest historia szablonu: lokalny klon ją
  ma, klon z adresu jest pobierany bez zawartości plików (`--filter=blob:none`), ale z historią. Szablon bez
  historii (zwykły katalog) — jak dotąd, każda różnica to „do aktualizacji”. Stary `update-skills.py` w projekcie
  tej reguły nie zna, więc pierwszy przebieg wciąż może nadpisać — stąd obowiązkowy podgląd.
- Podgląd `update-from-template.py` sprawdza polecenia lintu i testów z `config.json` projektu **wydanymi**
  strażnikami (nie kopią w projekcie, która może być sprzed #185) i ostrzega, gdy któreś zablokuje każdy commit.
- Lista plików szablonu to `template-files.json` w korzeniu szablonu, czytany z wydanego `main`
  (test pilnuje, że każdy wzorzec trafia w istniejący plik i że skrypty startu na nią nie trafiają).
- Hook startu sesji działa tylko z lokalnym klonem szablonu: przełącznika nie da się odczytać
  z samego adresu bez klonowania przy każdej sesji. Projekt znający szablon tylko z adresu
  uruchamia skrypt ręcznie — skrypt klonuje wtedy szablon bez treści plików (`--filter=blob:none`),
  więc rozpoznaje „zmieniony lokalnie” tak samo jak przy klonie.
- Data ostatniego pobrania leży w katalogu Gita klonu szablonu (`ai-template-last-fetch`), więc
  jeden klon pobiera raz na dobę niezależnie od liczby projektów.
