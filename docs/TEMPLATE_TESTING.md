# Testy ręczne szablonu

Scenariusze dla narzędzi, które istnieją **tylko w szablonie** i znikają przy starcie projektu
(`scripts/new-project.py`). Ten plik nie trafia do projektów — `--init` go usuwa. Scenariusze
strażników i narzędzi, które jadą do projektu, są w [docs/GUARDS_TESTING.md](GUARDS_TESTING.md).

---

### Scenariusz 10c — prowadzony start projektu

Na świeżej kopii szablonu **poza** repo szablonu (w samym szablonie tylko `--dry-run`):

- [ ] `python3 scripts/new-project.py --init` w terminalu → baner „Przygotowanie projektu”, sprzątanie z nagłówkami, potem baner „Start projektu” i osiem kroków z paskiem postępu: Git, repo, ustawienia repo, etykiety, kontrola środowiska, brief, skille, szablon graficzny
- [ ] `git branch --show-current` → `main`, także na maszynie bez `init.defaultBranch`
- [ ] Krok „Repo na GitHubie”: Enter → pominięty; adres → `git remote -v` pokazuje `origin`; `wlasciciel/nazwa` → repo powstaje na GitHubie, nic nie jest wypychane
- [ ] Krok „Etykiety zgłoszeń”: bez repo → pominięty z wyjaśnieniem; z repo podpiętym przez alias SSH (adres bez `github.com`) → proponuje założenie `owner` i `idea`
- [ ] Krok „Kontrola środowiska” → raport `doctor`; przy czerwonym raporcie pytanie „Poprosić Claude o pomoc z tym krokiem?”, a po powrocie „Ponowić ten krok teraz?”
- [ ] Krok „Brief projektu”: „tak” → Claude Code startuje i prowadzi wywiad po jednym pytaniu; po `/exit` wracasz do kroków i widzisz trzy `✓` (brief, stos, ADR-001)
- [ ] Wyjście z Claude Code w połowie wywiadu → `✗` przy brakujących punktach i pytanie „Wrócić do Claude Code i dokończyć?”
- [ ] Na końcu „Podsumowanie” ze znakiem przy każdym kroku i lista „Co dalej”; przy nieudanym kroku „Start niedokończony” z poleceniem wznowienia
- [ ] `python3 scripts/project-setup.py` uruchomiony ponownie → kroki zrobione są pomijane
- [ ] `python3 scripts/new-project.py --init < /dev/null` (bez terminala) → żadnego pytania, sama lista kroków; wynik przekierowany do pliku nie zawiera kodów kolorów

### Scenariusz 10j — co zostaje w dokumentach po starcie projektu

Na świeżej kopii szablonu poza repo, po `python3 scripts/new-project.py --init`:

- [ ] `docs/examples/` istnieje i ma cztery wzory (`SETUP`, `TASKS`, `ROADMAP`, `ADR-001`) oraz `README.md`
- [ ] `docs/TASKS.md` to kilkanaście linii: nagłówek, zdanie o logu sesji, pusta sekcja „Stan sesji” — żadnych wpisów szablonu
- [ ] `docs/SETUP.md` i `docs/TESTING.md` to szkielety do wypełnienia; nie ma w nich scenariuszy ani opisu strażników
- [ ] `docs/GUARDS.md` i `docs/GUARDS_TESTING.md` są w projekcie; `docs/TEMPLATE_TESTING.md` i ADR-y szablonu zniknęły
- [ ] `npm run doctor` i `python3 -m pytest -q` w nowym projekcie przechodzą
- [ ] Przeczytaj listę plików w `docs/` i zadaj pytanie o każdy: czy to dokument tego projektu, wzór, czy opis narzędzi — jeśli żadne z trzech, start projektu zostawił coś, czego nie powinien
