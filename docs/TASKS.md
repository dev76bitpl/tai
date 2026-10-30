# Tasks

Ten plik jest **logiem sesji**: co się wydarzyło i dlaczego. Otwarta praca szablonu żyje
w GitHub Issues (`gh issue list`), nie tutaj. Fazy definiuje [docs/ROADMAP.md](ROADMAP.md).

---

## Stan sesji

- 2026-10-31 **#216 reguła „łap pomysły właściciela"** — nowa linia w sekcji „Pamięć
  i artefakty" CLAUDE.md: właściciel wpada na pomysły całą dobę (szczyt weekend), rzucony
  pomysł traktujemy jako do zapisania (issue `idea`), nie do przegadania na śmierć. Globalnie,
  wiąże każdą sesję. Powód: pomysły rzucone mimochodem przepadają. Hierarchia jarvis => tai
  => reszta: decyzja u góry, kodeks w tai, projekty dziedziczą.
- 2026-10-18 **template_update_check = true** — przywrócenie powiadomienia o aktualizacjach
  szablonu na starcie sesji w projektach. Flaga była wyłączona od PR #200 (15.10).
- 2026-10-18 **#206 CLAUDE.md slim** — przeniesienie szczegółów (incydenty, uzasadnienia,
  procedury, przykłady) z CLAUDE.md do nowego `docs/RULES_REFERENCE.md`. Wynik: 71k → 30k znaków
  (limit 40k), 38 reguł bez zmian, 20 odnośników do reference. README zaktualizowany.

## Aktualny fokus

- [x] **Strażnik danych osobowych `guard-pii`** (2026-10-02, na prośbę właściciela):
      blokuje commit, który dodaje PESEL (z sumą kontrolną), numer konta (mod 97), telefon,
      prywatny e-mail (gmail, wp, onet…) albo nazwisko z lokalnej listy
      `~/.config/76bit/pii-names.txt` (lista nigdy nie trafia do repo). Wartości w komunikacie
      zamaskowane. Dane testowe: `pii-ok` w linii. Powód: dane prawdziwej osoby mogą trafić do
      repozytorium niezauważone, a z historii Gita nie da się ich już wygodnie usunąć.
      Gdy strażnik nie umie odczytać zmian, blokuje commit (nie przepuszcza po cichu); pliki
      z polskimi znakami lub spacją w nazwie są skanowane jak każde inne. Detektor
      `scripts/dev-guards/pii.py` da się zaimportować osobno, np. do cyklicznego skanu repo.
      Projekty dostaną strażnika przy najbliższej synchronizacji z szablonem.
      Obsługa (lista nazwisk, dane testowe, fałszywy alarm): `docs/SETUP.md`, sekcja o `guard-pii`;
      test ręczny: `docs/TESTING.md`, scenariusz 11a.
- [x] **`guard-pii` po angielsku** (2026-10-12, #145): komunikat blokady i nazwy rodzajów danych
      (`bank account`, `phone`, `private e-mail`, `listed name`) po angielsku, w stylu pozostałych
      strażników (`❌ [BLOCK] ...`, na stderr).
      > Po ludzku: strażnik mówi teraz tym samym językiem co reszta. Uwaga przy wdrożeniu: skan
      > zapisujący nazwę rodzaju w kluczach listy wyjątków przestaje rozpoznawać stare klucze —
      > listę trzeba przepisać raz, w tym samym momencie (komenda w `docs/SETUP.md`).
- [x] CI: pakiet testów repo odpalany na PR (`pytest` jako **krok** w istniejącym jobie
      `checks`, nie osobny job — job jest rozliczany w górę do pełnej minuty, a ten już
      instaluje Pythona, więc krok nie dokłada ani jednej naliczonej minuty). Wcześniej
      `SKIP: guard-lint,guard-tests` wyłączał guardy w mirrorze, a `checks-stack`, który
      miał je zastąpić, został zakomentowanym szablonem — 182 testy nie były bramkowane
      nigdzie. Przegląd 16 projektów: `SKIP` jest wszędzie i jest celowy (5 projektów
      dokłada własny krok z testami, m.in. `domeny.bydgoszcz.com` z wypełnionym
      `checks-stack`), a z pozostałych 11 tylko `tai` i `skolaro` mają realne testy

- [x] `config.json`: `lint` i `test` wskazane jawnie (`compileall`, `pytest`) — repo jest
      pythonowe, ale ma `package.json` (doctor, setup-hooks), więc autodetekcja stacku
      wybierała node i guardy odpalały `npm run lint` / `npm run test`, których nie ma.
      Skutek był dotąd taki, że guardów nie dało się używać lokalnie: `.git/hooks` w klonie
      był pusty, a `pre-commit install` blokował każdy commit. CI tego nie łapało, bo mirror
      ustawia `SKIP: guard-lint,guard-tests`, a `checks-stack` jest zakomentowany

- [x] `stack.py`: ścieżka do template rozstrzygana warstwowo (`$AI_TEMPLATE_PATH` >
      `config.local.json` > `config.json` > autodetekcja klona obok > publiczny URL) — wcześniej
      `ai_template_path` istniało tylko w commitowanym `config.json`, więc każdy nowy klon
      wymagał wklejenia ścieżki z konkretnej maszyny i ta ścieżka wjeżdżała do repo; jeden
      `export` w `~/.bashrc` obsługuje teraz wszystkie projekty, a bez niego działa URL.
      Autodetekcja rozpoznaje klon po markerze `is_template`, nigdy po nazwie katalogu —
      repo zostało przemianowane `ai` → `tai` i dopasowanie po nazwie rozwala się przy
      każdej takiej zmianie (wyszło z projektu, w którym obok siebie stały dwa klony)

- [x] `CLAUDE.md` 4: dziennik wdrożeń dla cyklicznego agenta doradczego — agent bez pamięci
      między uruchomieniami (raport tygodniowy, przegląd) czyta wyłącznie repo, więc bez zapisu
      „co z jego rad zostało wdrożone" każdy cykl zaczyna od zera i wymyśla nową radę zamiast
      rozliczyć poprzednią; wiersz w tym samym commicie co zmiana, data = dzień wdrożenia
      (skutek widać z opóźnieniem), tylko produkcja. Wyszło z projektu, w którym cotygodniowy
      raport analityki trzy razy z rzędu nie wiedział o własnych wdrożonych rekomendacjach
- [x] `update-skills`: klucze manifestu cross-platform (`rel.as_posix()`)
- [x] `new-project --init`: reset wersjonowania (usuwa CHANGELOG, manifest → 0.0.0)
- [x] `new-project --init`: świeży git + automatyczny init commit (`--no-git` opt-out)
- [x] `new-project --init`: auto-instalacja guardów (pre-commit + commit-msg)
- [x] `guard-ai-template`: fail-closed + czyta wiadomość z `-F`/heredoc (koniec cichego
      bypassu przez `git commit -F`; flagi `[no-template]`/`[template-done]` czytane też z pliku)
- [x] `session-context` + `update-skills`: wymuszenie utf-8 (koniec crashy cp1250 na Windows)
- [x] skille `copywriting` + `cro` zwendorowane do template'u (manifest + `.claude/skills/` + `docs/SKILLS.md`)
- [x] `CLAUDE.md` 3d — korekta: 404 na istniejącej trasie to katalog budowania, nie adres bazowy;
      przy okazji zasada „zmieniaj jedną rzecz na raz, inaczej nie zapisuj przyczyny w regułach"
- [x] `CLAUDE.md` 2a: instrukcja obsługi aplikacji prowadzi tym, co user widzi na ekranie
      (adres, układ), nigdy etykietami wyczytanymi z kodu — user nie ma jak ich zweryfikować
- [x] `CLAUDE.md` 3d: instancja AI nadpisuje **każdą** zmienną przypiętą do domyślnego portu
      (adres bazowy, callbacki, webhooki), nie tylko `PORT` — inaczej AI nie zaloguje się do
      własnej instancji i oddaje pracę, której nie uruchomiło
- [x] durable lessons: wnioski (bezstanowość AI, guardy fail-open, template=produkt) →
      `docs/AI_TEMPLATE_NOTES.md`; zasady (guard tylko z testem, rozdziel sesje system/projekt)
      → `CLAUDE.md` reguła 13a; lekcje praktyczne (utf-8 w hookach, guard fail-closed) → NOTES

- [x] **Narzędzie audytu RWD i UX — jeden silnik dla wszystkich projektów (2026-09-18)**

  > Po ludzku: skrypt, który mierzy, czy interfejs nie rozjeżdża się na telefonie i czy da się go
  > obsłużyć, żył w czterech projektach w czterech wersjach — każda ślepa na co innego. Teraz jest
  > jeden, wspólny. W projekcie zostaje sama kartka z adresem i listą ekranów do zmierzenia.

  - **Rozstrzygnięcie:** silnik (pomiary, detektory, raport) mieszka w skillu `audyt`
    w `76bit/claude-setup`, a `install.sh` podpina go symlinkiem do `~/.claude/skills/audyt` —
    dzięki temu jest widoczny z każdego projektu bez kopiowania czegokolwiek do repo. W repo
    projektu zostaje sam profil `audyt.config.mjs`: adres bazowy, nazwy zmiennych z danymi
    logowania, lista tras, kliknięcia otwierające szuflady.
  - **Komendy w projekcie:** `npm run audit:rwd` (rozjazd układu) i `npm run audit:uix`
    (dostępność i użyteczność). Oba wskazują ten sam plik i różnią się flagą — kolejne rodzaje
    audytu (`--seo`, `--perf`) wchodzą jako **tryby silnika**, nie jako nowe skille.
  - **Odrzucone i dlaczego:** `grupavist/claude-skills` (kandydat z pierwotnej notatki) — to zbiór
    skillów tematycznych, a narzędzie mierzące należy do zestawu roboczego · dystrybucja przez ten
    szablon — roznosiłaby kopie zamiast likwidować rozjazd · paczka npm — wersjonowanie narzędzia
    pomiarowego kosztuje więcej, niż daje.
  - **Wdrożone w:** `cdue-elearning`, `skolaro` (ADR-071), `new.cdue.edu.pl` (ADR-052).
    Pełne uzasadnienie: `cdue-elearning/docs/adr/ADR-057-shared-rwd-audit-engine.md`.
  - **Czego szablon nie roznosi i nie powinien:** samego silnika. Rolą szablonu jest **wskazać,
    gdzie on jest** (reguła 15) — nie trzymać własnej kopii. Stąd łatka w `CLAUDE.md`: reguła
    „RWD: zmierz zanim napiszesz «zrobione»" żądała pomiaru i nie nazywała narzędzia — wymóg
    bez wskazówki, skąd wziąć narzędzie, rodzi czwartą ręczną kopię.

---

## Backlog — przeniesiony do issues (2026-10-12)

> Po ludzku: lista rzeczy do zrobienia nie jest już prowadzona w tym pliku. Każde zadanie ma
> swoje issue, a tu zostaje tylko ślad, dokąd trafiło.

- martwy `script_integrity` w `skills-manifest.json` → #154
- `new-project.py --init`: dokumenty-szkielety wyglądają jak gotowa instrukcja → #155
- jeden punkt wejścia: dołączenie do projektu i aktualizacja z szablonu → #156
- narzędzia szablonu do prowadzenia zadań w issues (ADR-004) → #157; reguły w `CLAUDE.md` → #131
- `NameError` w `.claude/hooks/guard-template-sync.py` → #140

Zamknięte bez issue jako nieaktualne:

- `session-context.py` podpowiadał URL jako `ai_template_path` — podpowiedź mówi już o lokalnej
  ścieżce
- uprawnienie Actions do tworzenia PR-ów — opisane w `docs/SETUP.md` (ustawienia repozytorium)
- lekki tor dla zmian trywialnych — zastąpiony regułą 1a w `CLAUDE.md` (AI pyta przed każdym
  ruchem), decyzja właściciela 2026-10-12

Historia (zrobione przed przejściem):

- [x] **Config canonicalizacja `ai_template_path`** — ✅ KROK 2 zrobiony (ADR-002);
      pozostaje KROK 3: migracja projektu pochodnego (osobna sesja projektowa, Zasada B →
      `docs/MAINTAINER_BACKLOG.local.md`)

  > Po ludzku: guard, który pilnuje, by zmiany reguł wracały do wzorca, był w nowych
  > projektach martwy (czytał nieistniejący plik) i wymagał, żeby każdy miał wzorzec
  > na dysku. Po zmianie guard działa dla każdego od pierwszego commita, bez setupu.

  Decyzja: ADR-002 — sync = blokada-potwierdzenie (nie lokalne porównanie); lokalna
  ścieżka `ai_template_path` opcjonalna; jeden kanoniczny config `.claude/hooks/config.json`.
  Inkrementy KROK 2:
  - [x] **A** — `new-project.py`: `reset_adr_dir` czyści `docs/adr/` przy `--init`
        (ADR-y wzorca nie wyciekają do projektów; decyzja 6) + testy
  - [x] **B** — `create_config_json`: usunięty `_git_remote_url`, nie auto-ustawia
        `ai_template_path` (zostaje placeholder; kasuje błąd A; decyzja 3) + test
  - [x] **C** — `scripts/dev-guards/stack.py` `CONFIG_PATH` → `.claude/hooks/config.json`;
        wyczyszczone wszystkie ślady `.pre-commit-hooks.config.json` (decyzja 4)
  - [x] **D** — oba guardy sync przepisane na tryb potwierdzenia
        (`scripts/dev-guards/guard_template_sync.py` + `.claude/hooks/guard-template-sync.py`):
        brak klona/URL/zła ścieżka → blokada-ack na CLAUDE.md zamiast cichego skipu;
        ścieżka do lokalnego klona → auto-weryfikacja (decyzja 1+2) + 23 testy
  - [x] **E** — `tai/.claude/hooks/config.json` z `is_template: true`; oba guardy no-op
        sync we wzorcu (decyzja 5)

---

## Stan sesji

- 2026-10-15: **Aktualizacja starszego projektu: poprawna instrukcja, skille zmienione lokalnie nietknięte (#201).**
  Po ludzku: zgłoszenie kursu (cdue-ai-dev-course#23). Instrukcja mówiła, że wystarczy `update-skills.py` — nie
  wystarczy; trzeba dwa razy `--sync --apply`, potem `update-from-template.py`. Synchronizacja skilli (także ta
  automatyczna na starcie sesji) kasowała poprawki zrobione w projekcie — teraz je pomija i zgłasza do porównania
  (decyzja właściciela). Podgląd aktualizacji ostrzega o poleceniu lintu/testów, które po aktualizacji zablokuje
  każdy commit. Technicznie: `update-skills.py` `skill_history()` / `skill_state()` (blob id po `hashlib`, ta sama
  reguła co `update-from-template.py`), linia `LOCAL_SKILLS_LINE` czytana przez `session-context.py`; klon z adresu
  `--filter=blob:none` zamiast `--depth=1`; `update-from-template.py` `blocking_guard_commands()` ładuje WYDANY
  `scripts/dev-guards/stack.py`. README, GUARDS, ADR-006 (sprostowanie), scenariusz 10l. Pakiet 920/920; próba
  sesji na kopii z prawdziwym klonem tai (oba scenariusze + hook). Dług: `update-skills.py` 640 linii.

- 2026-10-15: **Przełącznik `template_update_check` w szablonie wyłączony (#156).** Po ludzku: decyzja właściciela
  po scaleniu #199 — projekty nie pokazują na starcie sesji linii „Szablon ma zmiany…”; aktualizację uruchamia się
  ręcznie (`python3 scripts/update-from-template.py`). Włączenie: `true` w `.claude/hooks/config.json` szablonu.

- 2026-10-15: **Aktualizacja projektu z szablonu jednym skryptem z podglądem (#156, paczka 2, ADR-006).**
  Po ludzku: poprawki strażników i hooków docierały do projektów tylko wtedy, gdy ktoś pamiętał, żeby je
  przenieść. Teraz `python3 scripts/update-from-template.py` pokazuje, które pliki szablonu są w projekcie
  starsze, które nowe, a które zmienione lokalnie; `--apply` kopiuje tylko dwie pierwsze grupy, pliku
  zmienionego w projekcie nie rusza, a `CLAUDE.md` tylko porównuje po sekcjach. Gdy w szablonie włączony jest
  przełącznik `template_update_check`, pierwsza wiadomość sesji pokazuje w terminalu jedną linię „Szablon ma
  zmiany…” (projekt z lokalnym klonem szablonu, `git fetch` najwyżej raz na dobę).
  Technicznie: lista plików w `template-files.json` (czytana z `origin/main` szablonu, więc nowy wpis działa
  i w starszej kopii skryptu); stan pliku po blob hash w historii `git log --raw`; adres URL → klon
  `--filter=blob:none`. `session-context.py` ładuje `session_notice()` ze skryptu projektu i oddaje linię jako
  `systemMessage` (zwykłe wyjście `UserPromptSubmit` widzi tylko model — wyszło w teście właściciela).
  Skrypt jedzie do projektów przez `update-skills.py` (`SYNC_PATHS`); stary projekt dostaje go dopiero przy
  drugiej synchronizacji skilli, bo pierwsza podmienia sam `update-skills.py`. Dług: `session-context.py`
  (439 linii) i `update-skills.py` (585) ponad limitem 400. Scenariusz 10l; próba właściciela na kopii OK.

- 2026-10-14: **Dołączenie do projektu zaczyna się od doctora; ADR-006 o aktualizacji z szablonu (#156, paczka 1).**
  Po ludzku: kto sklonował projekt, nie wiedział, że strażnicy i hooki nie działają na jego komputerze. README
  projektu ma teraz sekcję „Po sklonowaniu” z `python3 scripts/doctor.py`, a każdy wiersz raportu z problemem
  podaje polecenie naprawcze (dołożone przy 7 komunikatach; brak `settings.local.json` naprawia jedno polecenie
  `sed` zamiast „skopiuj i podmień”). Test AST w `tests/test_doctor.py` pilnuje podpowiedzi przy każdym
  `fail()`/`warn()`. ADR-006 (accepted) opisuje całość #156: skrypt `update-from-template.py` z podglądem,
  źródło `origin/main`, pliki zmienione lokalnie i `CLAUDE.md` nie nadpisywane, hook startu sesji tylko informuje,
  a automatyczne sprawdzanie włącza przełącznik w `config.json` szablonu (decyzja właściciela). Paczka 2 osobno.
  Scenariusz 10k w `docs/GUARDS_TESTING.md`. Próba właściciela na kopii: trzy punkty 10k OK.

- 2026-10-14: **Synchronizacja skilli bierze szablon ze scalonego `main`, nie z katalogu roboczego (#179).**
  Po ludzku: projekt z lokalnym klonem szablonu dociągał skille w takim stanie, w jakim klon akurat był
  — z gałęzi w toku, razem z niezacommitowanymi zmianami. 13.10 robocza wersja skilla trafiła tak do innego
  projektu. Teraz źródłem jest zawsze `origin/main` klonu; nowa wersja dociera do projektów po `git pull`
  w szablonie. Decyzja właściciela (rekomendacja sesji; odrzucone: odmowa synchronizacji poza czystym `main`
  — stałaby przy każdej pracy w katalogu szablonu).
  Technicznie: `scripts/update-skills.py` `released_snapshot()` — `git archive origin/main` tylko ścieżek, które
  czyta synchronizacja (`SYNC_PATHS`), do katalogu tymczasowego; `--sync` używa go dla klona Git (zwykły
  katalog bez `.git` — jak dotąd). `.claude/hooks/session-context.py` porównuje z tą samą migawką, ładując
  regułę z projektowego `update-skills.py` (jedno źródło; starszy skrypt bez reguły → dotychczasowe
  zachowanie do najbliższej synchronizacji, która go podmienia). README i `docs/GUARDS.md`. Testy na prawdziwych
  repo: klon na gałęzi ze zmienionym skillem → projekt nie widzi zmiany; różnica w `main` → synchronizacja.
  Koszt na wiadomość: ok. 50 ms przy lokalnym klonie.

- 2026-10-14: **Akcje GitHuba na Node 24 (#87).**
  Po ludzku: GitHub od czerwca uruchamia stare akcje na Node 24 na siłę i przy każdym przebiegu
  wypisuje ostrzeżenie; wydania i strażnicy działały, ale na czas pożyczony. Podbite do wersji, które
  same deklarują Node 24 — także we wzorze `ci.yml`, który nowe projekty dostają z szablonu.
  Technicznie: `release-please-action` v4 → v5, `checkout` v4 → v6, `setup-python` v5 → v6, `cache` v4 → v5
  (`using: node24` sprawdzone w `action.yml` każdej wersji). Odczyt przed zmianą: przebiegi release-please
  zielone, aktualizują PR #94; ostrzeżenie „Node.js 20 is deprecated” w `Release Please` i `Guards`.
  Kopie `checkout@v4` w przykładach vendored skilla `php-modernization` nieruszone (cudzy skill).

- 2026-10-14: **Ustawiony stos decyduje o poleceniach strażników; projekt zakłada się tylko klonem (#193, #127).**
  Po ludzku: po wywiadzie, w którym projekt wybrał np. Pythona, strażnicy lintu i testów dalej
  ostrzegali o `npm run lint`, bo szablon przynosi własny `package.json` — zgłosił to kurs (lekcja M4).
  Teraz ustawiony stos wygrywa z plikami. Drugie: tryb „skopiuj szablon do katalogu” zakładał projekt bez
  `.gitignore` i bez strażników commita — klucz API mógł trafić do repo. Właściciel zdecydował tryb
  usunąć; polecenie z katalogiem mówi teraz, jak zrobić to klonem.
  Technicznie: `scripts/dev-guards/stack.py` `CONFIGURED_STACKS` + `configured_stack()`, `detect_stack()`
  najpierw czyta `stack` z konfiguracji; doctor pisze `(stack: python)`. `new-project.py` bez trybu
  `<dest>` (kod 2 + instrukcja klonu), z `new_project_data.py` znikają `COPY_*` i martwy szkielet
  ROADMAP. GUARDS (tabela poleceń), GUARDS_TESTING 10h, ADR-005 decyzja 13, ADR-002 §6. Testy: 4 w
  `test_stack_commands.py` (w tym zgodność z tabelą `set-stack.py`), 2 w `test_new_project.py`.
  Dołożone po próbie właściciela (za jego zgodą): #141 — pierwsza wiadomość w każdym nowym projekcie
  kończyła się błędem hooka (`session-context.py` używał `datetime` bez importu; test w
  `.claude/hooks/tests/test_session_context_staleness.py`, czerwony na starym kodzie). „Co dalej” każe
  zakładać gałąź i commitować tylko wtedy, gdy start zostawił zmiany (`git status --porcelain`), a nie
  przy samym pominiętym briefie.

- 2026-10-14: **Start projektu nie zostawia setek plików na `main`; podpowiedź skilli pod stos wraca po wywiadzie (#177, #190).**
  Po ludzku: krok „Skille” proponował pobranie nowszych wersji skilli z sieci — na świeżym `main` zostawało
  ok. 130 zmienionych plików, których nie dało się tam zacommitować. Teraz krok tylko wybiera grupy, a
  aktualizacja to utrzymanie, na gałęzi roboczej. Druga rzecz: kto przeszedł krok skilli przed wywiadem,
  tracił na stałe propozycję pod stos — wybór „wszystkie” bez stosu już się nie zapisuje. Obie decyzje
  właściciela (rekomendacje sesji). Zgłoszenia od kursu.
  Technicznie: `project-setup.py` `step_skills()` bez `update-skills.py --apply`; `what_is_left()` podaje
  `git switch -c chore/project-start`, gdy brief, skille albo szablon graficzny coś zmieniły;
  `select-skills.py` `is_provisional()` — pierwszy wybór, brak stosu, wszystkie grupy → bez zapisu
  (`--all` i wybór zawężony zapisują się jak dotąd). README, `docs/SKILLS.md`, `docs/GUARDS.md`, ADR-005
  decyzja 12, scenariusz 10e w `docs/GUARDS_TESTING.md`. Pakiet 870/870; próba właściciela na kopii:
  start bez briefu → nic na `main`, wybór niezapisany; po `scope` wróciła propozycja dla stosu.

- 2026-10-13: **Nowy projekt dostaje wzory i puste szkielety zamiast dokumentów roboczych szablonu (#124, #155).**
  Po ludzku: start projektu kasował wypełnione przykłady w pierwszej sekundzie, zanim ktokolwiek mógł
  się na nich wzorować, a zostawiał w projekcie ponad 600 linii logu sesji samego szablonu i ponad
  200 linii jego scenariuszy testów. Wzór logu sesji uczył do tego prowadzenia backlogu, którego
  zasady zabraniają od 12.10. Zauważył to właściciel, pytając, po co są pliki przykładowe — obie
  sesje pracujące nad startem projektu oglądały listę usuwanych plików wielokrotnie i jej nie
  zakwestionowały.
  Przyczyna jest jedna: szablon prowadzi własne dokumenty robocze pod nazwami, które nowy projekt
  ma dostać puste. Teraz pod taką nazwą leży szkielet albo plik podmieniany przy starcie, a zasada
  jest w `CLAUDE.md` (13a) razem ze sprawdzianem: uruchom start na kopii i przeczytaj, co zostało.
  Technicznie: przykłady przeniesione do `docs/examples/` (zostają w projekcie; `README.md` z opisem;
  `TASKS.example.md` przepisany na log sesji), usunięte z `TEMPLATE_META`. `--init` podmienia
  `docs/TASKS.md` na szkielet z `SCAFFOLD_DOCS` (`INIT_SKELETONS`); szkielet poprawiony także dla
  trybu kopiowania, który kopiuje też `docs/examples/`, `GUARDS.md`, `GUARDS_TESTING.md`.
  `docs/TESTING.md` → szkielet; scenariusze strażników w `docs/GUARDS_TESTING.md` (jadą do projektu),
  scenariusze samego szablonu w `docs/TEMPLATE_TESTING.md` (usuwany przy starcie). `docs/SETUP.md` →
  szkielet (126 linii zamiast 513); opis strażników i narzędzi AI w nowym `docs/GUARDS.md`, z nazwanymi
  sekcjami zamiast numerów kroków. Komunikaty skryptów odsyłają do sekcji `docs/GUARDS.md`;
  `tests/test_line_endings.py` sprawdza, że każda taka sekcja istnieje i że nie wraca odesłanie do
  numeru kroku. Strażnicy `guard-testing-checklist` i `guard_testing_md` uznają dowolny
  `docs/*TESTING*.md`. `CLAUDE.md`: reguła czytania wzoru przed pisaniem dokumentu, nowe artefakty.
  Sprawdzone: 869 testów; prawdziwy start na kopii poza repo i przegląd każdego pliku w `docs/`
  (w nowym projekcie przechodzi też doctor i 481 testów strażników).
  Zostaje: `docs/GUARDS.md` opisuje prowadzony start od `new-project.py`, którego w projekcie już
  nie ma; `docs/SKILLS.md` wymienia wszystkie skille niezależnie od wyboru (#183).

- 2026-10-13: **Końce linii są ustawione w każdym klonie i w każdym nowym projekcie (#187, #173, #174).**
  Po ludzku: szablon nie miał pliku ustalającego końce linii, a jedyną ochronę ustawiał
  `npm install`, którego prowadzony start nie uruchamia. Na Windows kończy się to setkami
  „zmienionych” plików bez zmiany treści i strażnikiem odbijającym commity. Teraz reguła jest
  w repo, start projektu ustawia też ustawienie lokalne, a doctor pokazuje, czy ochrona jest.
  Technicznie: nowy `.gitattributes` (`* text=auto eol=lf`, CRLF dla `*.bat` / `*.cmd`, typy
  binarne) — w repo nie było plików CRLF, `git add --renormalize .` niczego nie zmienia.
  `scripts/new_project_git.py` `fresh_git_history()` i krok „Repozytorium Git”
  w `scripts/project-setup.py` ustawiają `core.autocrlf=input`. `scripts/doctor.py`
  `check_line_endings()` w „Repository state”. `scripts/setup-hooks.mjs`: komentarz o
  `.gitattributes` jest wreszcie prawdziwy. #174: odesłanie „step 12” → krok 7, przy braku Node
  → tabela wymagań; `tests/test_line_endings.py` sprawdza, że każde odesłanie do kroku
  `docs/SETUP.md` w komunikatach skryptów wskazuje istniejący krok.
  Sprawdzone: 805 testów; `--init` na kopii z pustą konfiguracją Gita; próba właściciela.
  Nie sprawdzone: skutek na Windows (praca w WSL). Tryb kopiowania do nowego katalogu nadal nie
  przenosi plików kropkowych (#127).

- 2026-10-13: **Strażnicy lintu i testów w nowym projekcie przestali udawać, że coś sprawdzają (#185).**
  Po ludzku: świeży projekt dziedziczył z przykładu polecenia dla PHP. Bez `composer` strażnik
  wypisywał ostrzeżenie, którego nikt nie widział, i przepuszczał każdy commit — raport środowiska
  był zielony, a lint i testy nie chodziły nigdy. Teraz polecenie wynika z tego, co naprawdę jest
  w projekcie, a strażnik, który nie ma czym sprawdzić, mówi to przy każdym commicie i w doctorze.
  Decyzje właściciela: polecenia z wykrywania po plikach projektu (nie z wyboru stosu, bo są sprawą
  projektu); polecenie wpisane przez projekt i niedostępne = blokada, wykryte automatycznie
  i jeszcze nieustawione = głośne ostrzeżenie (blokada zawsze zatrzymałaby pierwszy commit świeżego
  projektu).
  Technicznie: `scripts/dev-guards/stack.py` — `get_cmd(kind)` zwraca też, czy polecenie jest
  jawne; `why_unavailable()` liczy jako niedostępne także brak skryptu w `package.json` /
  `composer.json` (wcześniej `npm run lint` bez skryptu kończyło się błędem npm = blokadą);
  `guard_command()` wspólne dla `guard_lint.py` i `guard_tests.py`; `doctor_lines()` dla doctora.
  `.pre-commit-config.yaml`: `verbose: true` na obu strażnikach (bez tego ostrzeżenie chowa się za
  „Passed”) i nazwy bez „auto-detected”. `.claude/hooks/config.json.example`: bez `lint` / `test`.
  `scripts/doctor.py`: linie „Lint/Test guard runs / checks nothing / BLOCKS every commit”;
  sprawdzenia warstwy Claude Code przeniesione do `scripts/doctor_checks.py` (limit długości pliku).
  Testy: `test_guard_lint.py`, `test_guard_tests.py`, nowy `test_stack_commands.py`,
  `tests/test_new_project.py`; scenariusz 10h; ADR-005 decyzja 11.
  Sprawdzone: 780 testów; scenariusz ze zgłoszenia odtworzony na świeżym projekcie poza repo.
  Skutek dla projektów już postawionych: mają w `config.json` odziedziczone `composer lint` /
  `composer test` — po przejęciu nowych strażników dostaną blokadę, dopóki ich nie usuną albo nie
  zastąpią własnymi.

- 2026-10-13: **Kreator startu ustawia w repo na GitHubie to, co instrukcja nazywa blokującym (#186).**
  Po ludzku: start projektu zakładał repo i na tym kończył. Dwa ustawienia z kroku 1 instrukcji
  (kasowanie gałęzi po scaleniu, uprawnienia automatów GitHuba) zostawały w stanie domyślnym, bo
  kto idzie przez kreator, nie zagląda do instrukcji — a bez drugiego automat wydań pada po każdym
  scaleniu do `main`. Teraz krok mówi, czego brakuje, pyta raz i ustawia; doctor ostrzega o tym
  w projektach postawionych wcześniej.
  Decyzje właściciela: jedno pytanie tak/nie zamiast listy do wyboru; uprawnienia automatów
  proponowane tylko wtedy, gdy projekt ma automat wydań — to szersze uprawnienie, niż ma świeże repo.
  Technicznie: nowy `scripts/repo_settings.py` — `repo_slug()` (pyta `gh repo view`, więc działa
  z aliasem SSH), `read_state()` (`delete_branch_on_merge`, `actions/permissions/workflow`),
  `missing()` (reguła: `.github/workflows/release-please*.y*ml`), `apply()`, `step()` i
  `doctor_check()`; moduł nie uruchamia procesów sam, dostaje `run` od wywołującego.
  `scripts/project-setup.py`: krok „Ustawienia repo” zaraz po kroku repo (osiem kroków); odmowa
  GitHuba nie zatrzymuje startu — pokazuje polecenia `gh api`. `scripts/doctor.py`: linia
  w „Repository state”, nigdy nie czerwieni raportu. Testy w `tests/test_project_setup.py`
  i `tests/test_doctor.py`; `docs/SETUP.md` krok 1 i tabela kroków, scenariusz 10g, ADR-005 decyzja 10.
  Sprawdzone: 762 testy; odczyt stanu na prawdziwym GitHubie; ustawianie — próba właściciela na
  repozytorium próbnym.
  Wyszło przy okazji, nieruszone: doctor uruchomiony w osobnym katalogu roboczym Gita zgłasza brak
  hooków (`.git` jest tam plikiem, nie katalogiem).

- 2026-10-13: **Start projektu: kreator wraca do kroków, projekt wybiera skille, dochodzi szablon graficzny (#180, #183, #184).**
  Po ludzku: (1) po wyjściu z Claude Code użytkownik wraca do kroków startu zamiast do pustego
  terminala, skrypt sprawdza, co wywiad naprawdę zostawił, a na końcu jest podsumowanie; całość
  dostała czytelny wygląd z kolorami i paskiem postępu; (2) projekt zostawia sobie tylko potrzebne
  grupy skilli — reszta znika i nie wraca przy synchronizacji z szablonu; (3) po briefie i wyborze
  skilli start proponuje szablon graficzny: dwa kierunki wyglądu jako makiety i zasady, których
  trzymają się kolejne ekrany.
  Decyzje właściciela (w kolejności; kilka zmieniało poprzednią wersję): przebieg powrotu i sprawdzeń;
  „bardziej przyjazne, kolorki” i spójny wygląd także dla części sprzątającej; wybór skilli w pełnej
  wersji (usuwanie + wyłączenie z synchronizacji), z propozycją według stosu; skille do projektowania
  z publicznych źródeł, nie z prywatnej konfiguracji; krok nie wskazuje jednego skilla; `impeccable`
  poza szablonem, z pytaniem o instalację domyślnie „nie”; kolejność brief → skille → szablon
  graficzny (pierwsza wersja miała skille na końcu i próba pokazała komplet zbędnych skilli podczas
  wywiadu i projektowania).
  Technicznie: `scripts/project-setup.py` — `start_claude()` przez `subprocess.call` (SIGINT
  ignorowany w rodzicu na czas sesji) zamiast `os.execvp`; `claude_stage()` wspólne dla briefu
  i szablonu graficznego (pytanie → Claude Code → sprawdzenie → ewentualny powrót); `handle_failure()`
  zwraca decyzję o ponowieniu; `run_steps()` zbiera wyniki do podsumowania; `confirm(default=)`;
  `offer_impeccable()` (`npx impeccable install --providers=claude --scope=project --no-hooks`).
  Nowe pliki: `scripts/start_ui.py` (kolory tylko na terminalu, `NO_COLOR` / `FORCE_COLOR`, baner,
  pasek postępu, podsumowanie), `scripts/start_checks.py` (`scope_is_filled`, `brief_checks`,
  `design_checks`), `scripts/start_prompts.py` (zadania dla Claude Code; `design_prompt(impeccable)`),
  `scripts/select-skills.py` (8 grup, `STACK_DEFAULTS`, `apply_selection()` usuwa katalogi i wpisy,
  zapisuje `skill_groups` + `excluded_skills`). `scripts/set-stack.py` zapisuje klucz `stack`.
  `.claude/hooks/session-context.py` `_local_desynced()` i `scripts/update-skills.py`
  `sync_from_template()` pomijają `excluded_skills`. Krok etykiet rozpoznaje GitHuba przez
  `gh repo view`, nie po `github.com` w adresie (alias SSH gubił repo — znalezione w próbie).
  Vendored: `design-taste-frontend`, `redesign-existing-projects` (`Leonxlnx/taste-skill`, MIT).
  `impeccable` zatrzymany przez skan bezpieczeństwa `update-skills.py` (zbundlowane skrypty) —
  nie obchodzony, opisany w `docs/SKILLS.md`. ADR-005: decyzje 7–9.
  Sprawdzone: 748 testów; pełne próby w pseudo-terminalu z atrapą `claude`; cztery próby właściciela
  na żywo na kopii poza repo (ostatnia z `impeccable`: `PRODUCT.md`, makiety, zasady wyglądu).
  Znane ograniczenia: pięć katalogów skilli jakości stron leży poza manifestem i wybór ich nie
  rusza (#183); synchronizacja nadal czyta katalog roboczy klona szablonu (#179) — projekt
  próbny testowany z gałęzi dostał starsze `update-skills.py` i skill wywiadu z `main`.

- 2026-10-13: **`new-project.py` podzielony, decyzje paczki zapisane w ADR-005.** Po ludzku: skrypt startu
  projektu urósł do 548 linii przy limicie 400 dla plików logiki — właściciel uznał to za błąd do
  naprawy od razu. Teraz ma 371. Decyzje z całej paczki (stos z wywiadu ustawia strażników, wzorce
  platform do włączenia, prowadzony start) dostały ADR, żeby za pół roku nie trzeba było ich odtwarzać.
  Technicznie: dane (`COPY_*`, `SCAFFOLD_DOCS`, `README_SCAFFOLD`, `TEMPLATE_META`) →
  `scripts/new_project_data.py`; kroki Gita (`fresh_git_history`, `install_guards`,
  `_resolve_pre_commit`) i pomocnicze `log` / `warn` → `scripts/new_project_git.py`. Oba pliki są
  tylko-szablonowe jak sam skrypt: lista `TEMPLATE_ONLY_SCRIPTS` steruje usuwaniem przy `--init`
  i pomijaniem w trybie kopiowania. Testy: lista zgodna z dyskiem, `--init` usuwa całą trójkę
  i zostawia `set-stack.py` / `project-setup.py`, limit 400 linii dla plików logiki. Próba `--init`
  na kopii poza repo: gałąź `main`, strażnicy, w `scripts/` brak plików startowych.
  `docs/adr/ADR-005-stack-from-scope-interview.md`, odesłanie w `docs/SETUP.md` krok 8b.

- 2026-10-13: **Testy uruchamiane przy commicie nie sięgają już do prawdziwego repozytorium (#181).**
  Po ludzku: pierwszy commit z osobnego katalogu roboczego (worktree) uszkodził repo — główny katalog
  przestał działać z Gitem, a w indeksie pojawiły się pliki, których nikt nie dodawał. Nic nie zginęło,
  naprawa zajęła dwa polecenia, ale szablon sam każe pracować w worktree, więc trzymanie się reguły
  psuło repo. Teraz pakiet testów jest od tego odcięty.
  Technicznie: `guard-tests` uruchamia pakiet z hooka, a Git przekazuje hookom `GIT_INDEX_FILE` i —
  w worktree — `GIT_DIR` prawdziwego repo. Testy wołające `git init` / `git add` w katalogach
  tymczasowych działały przez to na prawdziwym repozytorium (`core.bare = true`, pliki testowe
  w indeksie). Czyszczenie było punktowe (`harness.clean_env`); `test_guard_pii.py`
  i `test_guard_tasks_staged.py` wołały Gita bez niego. Poprawka: `conftest.py` w `tests/`,
  `.claude/hooks/tests/` i `scripts/dev-guards/tests/` z ustawieniem `autouse`, które przed każdym
  testem usuwa wszystkie zmienne `GIT_*`; w każdym katalogu test izolacji. Dowód na repozytorium-atrapie
  z worktree (hook `pre-commit` uruchamiający pakiet): przed 12 czerwonych i uszkodzona atrapa, po 661
  zielonych i atrapa nietknięta. Pułapka opisana w `docs/AI_TEMPLATE_NOTES.md`.

- 2026-10-13: **Start projektu prowadzi przez kroki, a strażnicy dopasowują się do stosu (#134, #165, #178, #171, #172).**
  Po ludzku: (1) projekt bez sklepu przestał dostawać blokadę „nowy moduł PrestaShop” — wzorce platform są
  w konfiguracji nieaktywne, dopóki projekt nie jest na tej platformie; (2) strażnik „kod wymaga testów”
  rozpoznaje testy Pythona, PHP, Ruby i Go, a nie tylko JavaScript, i sprawdza katalogi kodu właściwe dla
  stosu; (3) nikt nie ustawia tego ręcznie — stos pada w wywiadzie o zakresie i z niego wynika reszta;
  (4) start projektu to kroki z pytaniami i wynikiem, a przy błędzie propozycja pomocy AI; (5) projekt
  zawsze startuje na gałęzi `main`, a README nie każe już kasować świeżo zainstalowanych strażników.
  Decyzje właściciela (w tej kolejności, każda zmieniała poprzednią wersję): wzorce platform wyłączone do
  włączenia; wbudowana lista wzorców testów; katalogi kodu ustawiane przy starcie, nie ręcznie; pytanie
  o stos, nie o katalogi; pytanie o stos w wywiadzie scope, nie w `--init`; start i wywiad powiązane
  pytaniem „ustalamy brief?”; lista kroków jako prowadzone kroki z pomocą AI; do kroków dołożone
  założenie repo na GitHubie i etykiety `owner` / `idea`; wywiad interaktywny, sześć tematów domyślnych
  plus dopytanie.
  Technicznie: `.claude/hooks/config.json.example` — `adr_patterns` tylko ogólne, grupy platform
  w `_adr_patterns_optional`, nowy klucz `src_dirs`. `scripts/dev-guards/guard_tests_with_src.py` —
  `is_test_file()` z listą konwencji wszystkich stosów, katalogi z `src_dirs` (domyślnie `src`), dopasowanie
  po segmencie ścieżki. Nowy `scripts/set-stack.py` — tabela `STACK_PRESETS` (10 stosów), `apply_stack()`
  ustawia `src_dirs` i kopiuje grupę platformy do `adr_patterns`; ponowne uruchomienie z innym stosem
  wyłącza poprzednią grupę. Nowy `scripts/project-setup.py` — kroki: repozytorium Git, repo na GitHubie
  (`git remote add` albo `gh repo create`, bez `push`), etykiety, skille, doctor, brief; krok zrobiony jest
  pomijany, `StepFailed` → propozycja uruchomienia Claude Code z poleceniem i błędem; bez terminala tylko
  lista. `scripts/new-project.py` — `git init -b main`, opcjonalne `--stack`, po sprzątaniu `os.execv` do
  `project-setup.py`. Skill `new-project-scope` — trzy stany `docs/PROJECT_SCOPE.md` (brak / szkielet
  z szablonu / własna treść; wcześniej instrukcja zabraniała wywiadu, gdy plik istnieje, a po `--init`
  istnieje zawsze), wywiad po jednym pytaniu z dopytaniem, „Artifact 3” uruchamia `set-stack.py`.
  Testy: `tests/test_set_stack.py`, `tests/test_project_setup.py`, rozszerzone `test_new_project.py`,
  `test_guard_adr.py`, `test_guard_tests_with_src.py`; próba `--init` na kopii poza repo (gałąź `main`
  przy pustej konfiguracji Gita, strażnicy zainstalowani, przekazanie do kroków).
  Znane ograniczenia: po wyjściu z Claude Code nie ma powrotu do kroków (`os.execvp`) → #180; projekty
  już postawione mają stare wzorce platform we własnym `config.json`; synchronizacja z szablonu nie
  przenosi `scripts/`, więc starszy projekt nie dostanie `set-stack.py` (skill to przewiduje);
  `scripts/new-project.py` ma 548 linii (limit 400).
  Poza tematem, wyszło w trakcie: synchronizacja skilli w projektach czyta katalog roboczy klona szablonu,
  także z gałęzi w toku → #179; od tej chwili praca nad szablonem idzie w osobnym worktree.
  Kolejność commitów na gałęzi: najpierw izolacja testów (#181), dopiero potem ta paczka — bez #181
  commit z worktree uszkadzał repozytorium, więc paczki nie dało się bezpiecznie zapisać.

- 2026-10-13: **Plik ustawień per maszyna działa dla obu warstw strażników (#152), a instrukcja
  przestała kazać commitować ścieżkę z własnego komputera (#153).** Po ludzku: strażnicy mają
  plik wspólny (`config.json`, w repo) i plik jednej maszyny (`config.local.json`, poza repo),
  który ma nadpisywać wspólny. Respektowały go tylko hooki Claude Code; strażnicy commita
  i `npm run doctor` po cichu go pomijali. Teraz wszyscy czytają tak samo. Instrukcja instalacji
  twierdziła do tego, że wspólny plik jest poza Gitem, i kazała wpisać do niego lokalną ścieżkę —
  trafiłaby do commita.
  Decyzja właściciela: wspólne zachowanie zamiast zapisu „plik lokalny tylko dla hooków”. Znany
  koszt: plikiem lokalnym da się na jednej maszynie podmienić komendę `lint` / `test` i w repo
  tego nie widać (to samo robi dziś `--no-verify`); SETUP mówi, żeby trzymać tam ścieżki i porty.
  Technicznie: `scripts/dev-guards/stack.py` `load_config()` nakłada `config.local.json` na
  `config.json` (to samo co `.claude/hooks/stack.py`; nieczytelny plik lokalny jest pomijany).
  `scripts/doctor.py` `check_claude_template_path()`: kolejność `$AI_TEMPLATE_PATH` >
  `config.local.json` > `config.json`, w komunikacie źródło (`from ...`); adres zdalny (domyślny
  w `config.json.example`) nie jest już zgłaszany jako nieistniejąca ścieżka; przy `is_template`
  komunikat „This repo is the AI template”. Testy: `test_guard_lint.py` (+3), `test_guard_adr.py`
  (+1) — strażnik jako osobny proces, trzy czerwone na starym loaderze; `tests/test_doctor.py` (+8).
  `docs/SETUP.md` krok 8b przepisany (tabela dwóch plików), komentarze w `config.json.example`.
  Wyszło przy okazji: `guard-ai-template` blokuje commity w samym szablonie, bo nie czyta
  `is_template` (#170) — commity tej nocy szły z `[no-template]` za zgodą właściciela.

- 2026-10-13: **`npm run doctor` widzi, czy hooki Claude Code są podpięte, i czy jest `pytest` (#150, #162).**
  Po ludzku: raport środowiska świecił cały na zielono, choć hooki zatrzymujące polecenia AI mogły
  w ogóle nie działać na danej maszynie — sprawdzał tylko warstwę commita. Teraz ma osobną sekcję
  „Claude Code hooks”: brak pliku ustawień to ostrzeżenie, niepodmieniony znacznik `INTERPRETER`
  albo zepsuty plik to błąd (każdy hook wywala się przy starcie), strażnik obecny w repo, a
  niepodpięty — ostrzeżenie z nazwą. Do tego ostrzeżenie o braku `pytest` z poleceniem naprawczym.
  Progi wybrał właściciel: błąd w doctorze znaczy „środowisko niezdatne”, a brak pliku u kogoś,
  kto nie używa Claude Code, tym nie jest.
  Technicznie: `scripts/doctor.py` — `check_claude_hooks()` (czyta `.claude/settings.local.json`,
  zbiera wszystkie pola `command` z sekcji `hooks`, znacznik szuka tylko w poleceniach, nie
  w `_readme`; strażnik liczy się jako podpięty także wtedy, gdy uruchamia go wspólny
  `.claude/settings.json`; porównanie z `.claude/hooks/guard-*.py`) i `check_pytest()`
  (`sys.executable -m pytest --version`; wariant dla Ubuntu 24.04+ / PEP 668 w podpowiedzi).
  Testy: `tests/test_doctor.py` (13), w `tests/test_new_project.py` dwa testy pilnujące decyzji
  z #162 — `--init` usuwa `tests/`, a `.claude/hooks/tests/`, `scripts/dev-guards/tests/`
  i `pytest.ini` zostają. `docs/SETUP.md`: tabela komunikatów w kroku 8a i akapit o projekcie
  o innym stosie (przy commicie test własnego strażnika nie rusza sam, pilnuje go krok
  `Run tests` w `guards.yml`; sprawdzone, że `pytest` pomija nieistniejący katalog z `testpaths`).
  Wyszło przy okazji: w samym repo szablonu na maszynie właściciela pliku ustawień nie było —
  doctor pokazał to pierwszym przebiegiem.

- 2026-10-12: **Skan sekretów w CI naprawdę skanuje (#136).** Po ludzku: krok w CI, który miał
  łapać klucze i hasła wrzucone do repo, świecił na zielono bez względu na zawartość — patrzył
  tylko na pliki przygotowane do commita, a w CI takich nie ma. Lokalnie przy commicie działał.
  Teraz CI skanuje całe repo osobnym krokiem i czerwieni się na znalezisku; lukę dziedziczył
  każdy projekt startujący z szablonu.
  Technicznie: hook `gitleaks` to `gitleaks protect --staged`, a `pre-commit run --all-files`
  w checkoucie CI ma pusty indeks. W `.github/workflows/guards.yml` hook trafił do `SKIP`,
  a za nim doszedł krok `Scan working tree for secrets (gitleaks)`: obraz
  `zricethezav/gitleaks:v8.21.2`, `detect --no-git --source=. --redact --verbose`, repo
  montowane tylko do odczytu. Wersja obrazu = `rev` hooka w `.pre-commit-config.yaml`; źródło
  względne (`-w /repo` + `--source=.`), bo przy bezwzględnym wpis w `.gitleaksignore` przestaje
  pasować. Pilnuje tego `tests/test_ci_secret_scan.py` (5 testów, 4 czerwone na starym
  workflow). Poprawione też: komentarz w `.github/workflows/ci.yml` i punkt „Sekrety” w
  `docs/AI_TEMPLATE_NOTES.md` (oba twierdziły, że hook skanuje całe drzewo). Sprawdzone lokalnie:
  drzewo szablonu 0 znalezisk, katalog próbny z fałszywym kluczem AWS → kod wyjścia 1.
  Zgłoszenie podawało `ci.yml` — po podziale CI (#148) krok mieszka w `guards.yml`.

- 2026-10-12: **Każdy strażnik ma test, który uruchamia go naprawdę (#139).** Po ludzku: reguła
  „żaden strażnik bez testu” była dotąd spełniona dla 4 z 16; teraz dla wszystkich 17 (4 hooki,
  12 strażników commita, sprawdzenie języka PR), a nowy strażnik bez testu wywala pakiet, więc
  pokrycie nie cofnie się po cichu. Testy uruchamiają strażnika jako osobny proces w tymczasowym
  repozytorium i sprawdzają dokładny kod wyjścia; próba „strażnik zawsze przepuszcza” wywala plik
  testów każdego z 17.
  Technicznie: testy strażników commita przeniesione z `tests/` do `scripts/dev-guards/tests/`
  (decyzja #162), `test_resolve_template_path.py` do `.claude/hooks/tests/`; wspólne narzędzia
  `harness.py` / `hook_harness.py` (kopiują strażników do tymczasowego repo, bo ci czytają
  `config.json` względem własnego pliku; czyszczą zmienne `GIT_*`, bo pakiet sam biega z hooka
  pre-commit). Nowe pliki: `test_guard_{adr,commit_lang,lint,tests,tests_with_src,testing_md,typecheck,user_tested}.py`,
  `test_check_pr_language.py`, `test_guard_ai_template.py`, `test_guard_testing_checklist.py`,
  `test_every_guard_has_tests.py`, `test_every_hook_has_tests.py`. `guard_template_sync` i
  `guard_release_tag` miały testy tylko na atrapach — sprawdzenie pokrycia to wyłapało, dostały
  testy całej drogi (fałszywe `gh` na `PATH`).
  Dziury znalezione i naprawione przy okazji (małe, zgodą właściciela): (1) `read_commit_msg()`
  zwracał `""`, gdy nie dostał albo nie odczytał pliku wiadomości — `guard_user_tested`
  i `guard_commit_lang` wtedy przepuszczały; teraz blokada; (2) `get_staged_files()` zwracał `[]`,
  gdy `git` zawiódł — teraz blokada; (3) `get_current_branch()` (i odpowiednik w hooku
  `guard-testing-checklist`) używał `git rev-parse --abbrev-ref HEAD`, które pada na gałęzi bez
  commitów, a pusty wynik znaczył „pomiń” — pierwszy commit na `feat/*` / `fix/*` w nowym repo
  omijał `[user-tested]` i checklistę; teraz `git branch --show-current`; (4) hook
  `guard-testing-checklist` szukał `[skip-test-check]` tylko w poleceniu, nie w pliku `-F`;
  (5) `check_pr_language.py` przechodził przy pustym `PR_TITLE` (workflow nic nie przekazał).
  Znane, nieruszone: `guard_tests_with_src` rozpoznaje testy tylko po `.test.` / `.spec.` /
  `__tests__` i tylko kod w `src/` (projekt w Pythonie z `tests/test_x.py` dostaje fałszywą blokadę,
  kod poza `src/` nie jest sprawdzany) → #165; `guard_template_sync` (commit) czyta ścieżkę szablonu
  tylko z `config.json`, bez warstw z hooka → #166. Pakiet: 497 testów, ok. 25 s (było 310, ok. 8 s).
- 2026-10-12: **Hooki blokują, gdy nie odczytają własnego wejścia; strażnik rozjazdu z szablonem
  przestał się wywalać (#137, #140).** Po ludzku: cztery strażniki działające przed poleceniem
  powłoki przepuszczały wszystko, gdy dostały coś, czego nie umiały odczytać — a strażnik, który
  przepuszcza, wygląda tak samo jak ten, który nic nie znalazł. Teraz w takiej sytuacji blokują
  i mówią, że nie sprawdziły. Strażnik rozjazdu z szablonem wywalał się dokładnie wtedy, gdy rozjazd
  znalazł, więc commit przechodził; teraz blokuje.
  Technicznie: `.claude/hooks/stack.py` — `parse_hook_input()` (trzy wyniki: polecenie / inne
  narzędzie niż `Bash`/`PowerShell` / nieczytelne) i `read_command()` (kod 2 z komunikatem przy
  nieczytelnym, kod 0 dla innego narzędzia); stdin czytany jako bajty UTF-8. Cztery kopie
  `get_command()` (`except Exception: return ""`) usunięte z `guard-process-kill`,
  `guard-template-sync`, `guard-ai-template`, `guard-testing-checklist`. Puste wejście = nieczytelne
  (decyzja właściciela; hook PreToolUse zawsze dostaje dane). Wejście bez `tool_name`, ale
  z poleceniem, jest czytane — tak hook karmi się ręcznie. #140: `guard-template-sync.py`,
  komunikat blokady używał niezdefiniowanego `template_path` (`NameError`, kod 1 = brak blokady).
  Testy: `.claude/hooks/tests/test_hook_input.py` (granica wejścia, każdy z czterech hooków jako
  osobny proces), `test_guard_process_kill.py` (+ testy całej drogi), `test_guard_template_sync_hook.py`
  (+ gałąź „klon istnieje” na tymczasowym projekcie). Próba psucia: zamiana kodu blokady 2→1 i 2→0
  wywala testy całej drogi, a testy samego `verdict()` zostają zielone.
  Poza głównym tematem, decyzją właściciela (#162): testy strażników mieszkają obok strażników,
  żeby jechały z nimi do nowego projektu — `.claude/hooks/tests/` (dwa pliki przeniesione z `tests/`),
  `pytest.ini` z `testpaths`, bo pytest pomija katalogi z kropką. Testy strażników commita
  przeniesie #139. `suggest-pr` i `session-context` mają ten sam `except`, ale niczego nie blokują —
  nieruszone.
- 2026-10-12: **Reguły szablonu mówią to samo co praktyka: praca w issues, plik jako log (#131).**
  Po ludzku: nowy projekt z szablonu nie startuje już ze sprzecznością „zasady każą prowadzić
  zadania w pliku, a pracujemy w issues”. `CLAUDE.md`: nowy akapit „Gdzie żyje otwarta praca”
  w regule 4 i 12 poprawionych odesłań (reguły 4, 10, 16a, 19a, lista artefaktów, kolejność
  tworzenia, „Aktualizacja”, „Kiedy NIE pisać ADR”, „Start projektu”); dwie warstwy opisu dotyczą
  treści issue. Projekt bez GitHuba zostaje przy pliku jako liście zadań (ADR-004 §6).
  `scripts/dev-guards/guard_tasks_staged.py`: komunikat mówi o wpisie w logu sesji, nie o liście
  zadań; dopisany test `tests/test_guard_tasks_staged.py` (6 przypadków, uruchamia skrypt
  w prawdziwym repo i sprawdza kod wyjścia; celowo zepsuty strażnik wywala 4 z 6) — to też jedna
  pozycja z #139. ADR-004: korekta §5 — plik zostaje jako log sesji, strażnik zostaje.
  Znana słabość strażnika, nieruszona: dopasowuje nazwę pliku jako fragment ścieżki. Poza zakresem:
  wzmianki o pliku zadań w `README.md`, `docs/SETUP.md`, `scripts/new-project.py` (#157, #124).
- 2026-10-12: **Issues po polsku — reguła 2 w `CLAUDE.md` (#131, pierwszy krok).** Po ludzku: zadania
  i sprawy do decyzji czyta właściciel, więc mają być w języku, w którym rozmawiamy; dotąd reguła
  kazała pisać je po angielsku i przeczyła praktyce. Kod, opisy commitów i PR zostają po angielsku
  (pilnuje ich strażnik języka). Decyzja właściciela 2026-10-12. Pozostałe kroki #131 (odesłania do
  `docs/TASKS.md` w regułach 4, 10, 16a, komunikat `guard-tasks-staged`) nieruszone.
- 2026-10-12: **Otwarta praca przeniesiona do issues (#158).** Po ludzku: lista zadań szablonu jest
  teraz w jednym miejscu, na GitHubie, a ten plik jest tylko dziennikiem. Z 8 otwartych pozycji
  backlogu 4 dostały issues (#154–#157), 1 była już w #140, 3 zamknięte jako nieaktualne (lista
  w sekcji „Backlog” wyżej). Usunięta sekcja „Następna sesja” — opisywała zadanie zrobione
  w czerwcu (ADR-002). W `docs/ROADMAP.md` nic do przeniesienia: oba checkboxy to pola szkieletu.
  Przy okazji, na polecenie właściciela, 13 otwartych issues przetłumaczonych na polski.
- 2026-10-12: **CI rozdzielone na strażników i ciężkie sprawdzenia (#148, gałąź
  `ci/148-docs-only-split`).** Po ludzku: w nowym projekcie poprawka samej dokumentacji nie odpala już
  testów, builda i skanu kodu — idą tylko lekkie strażniki. Zamyka wpis z backlogu „PR czysto
  dokumentacyjny nie powinien palić pełnego CI”. `guards.yml`: całe dotychczasowe zadanie `checks`
  przeniesione 1:1 (pre-commit, opisy commitów, testy szablonu), każdy PR, bez filtra. `ci.yml`: sam
  wzór (matryca stosu, build, SAST) z `paths-ignore` na `docs/**` i `**/*.md` oraz zaślepką
  `if: false`, bo plik bez joba jest nieważny. Świadomie inaczej niż podział 1:1 znany z projektów:
  testy szablonu trwają 2 s, osobny job kosztowałby drugą naliczoną minutę na każdym PR z kodem,
  a `.claude/**` nie może być pomijane, bo testy czytają stamtąd hooki. Brak wymaganych checków na
  `main`, więc pominięty workflow nie blokuje merge'a. Do potwierdzenia na pierwszym PR: zaślepka
  nie startuje runnera; na pierwszym PR dokumentacyjnym: idą tylko `Guards` i `PR language`.
- 2026-09-28: **`update-skills.py` bez `--apply` przestał zapisywać manifest.** Po ludzku: sprawdzenie
  „tylko pokaż, co jest do aktualizacji" zostawiało zmieniony `skills-manifest.json`, który w projekcie
  potrafił wjechać do zupełnie innego commita. Przyczyna: `check_skill()` stempluje `checked`
  każdemu skillowi, a `main()` zapisywał manifest bezwarunkowo. Teraz zapis tylko przy `--apply`;
  test w `tests/test_update_skills.py` (dry-run i `--scan-only` nie ruszają pliku, `--apply` pisze).
  Przy okazji: `--scan-only` nie zmienia niczego w działaniu względem zwykłego dry-runu (flaga nie jest
  nigdzie czytana). Naprawione w tym samym commicie: 3 testy `test_guard_template_sync_hook.py` padały
  na maszynie z ustawionym `$AI_TEMPLATE_PATH` (od #123 wygrywa z configiem) i blokowały każdy commit;
  fixture w testach czyści zmienną.

- 2026-09-04: **`npm run doctor` przestał straszyć brakującym `py`.** Po ludzku: po każdym
  czerwonym raporcie doktora na Linuksie/WSL na końcu wyskakiwało `py: not found`, jakby brakowało
  narzędzia — nic nie brakowało, komunikat był fałszywy; na Windows ten sam błąd wypisywał raport
  dwa razy. Przyczyna: `python3 scripts/doctor.py || py scripts/doctor.py` — doctor kończy się
  kodem 1 celowo (znalazł problem), a `||` brał to za brak interpretera i odpalał windowsowy
  launcher. Technicznie: nowy `scripts/doctor.mjs` sprawdza, który interpreter odpowiada na
  `--version` (Windows: `py`, `python`, `python3`; reszta: `python3`, `python`), odpala doctor raz
  i oddaje jego kod wyjścia bez zmian; brak Pythona = jeden jasny komunikat. Test
  `tests/test_doctor_launcher.py` podstawia fałszywy `python3` (raport czerwony i zielony) oraz
  pusty PATH. `new-project.py` kopiuje cały `scripts/`, więc nowe projekty dostają wrapper
  automatycznie; istniejące projekty dociągają go ręcznie (plik + jedna linia w `package.json`).
  Pierwszy raz wdrożone w projekcie produkcyjnym (PR #201 tam), stąd przeniesione do template'u.

- 2026-06-24: **Lektor „Gotowe" + nazwa projektu — przeniesiony do template'u (branch
  `docs/speak-tts-announcer`).** Po ludzku: po skończonej turze komputer mówi „Gotowe" i nazwę
  projektu, w którym pracujesz — przydatne przy kilku otwartych naraz. Wariant usera (głos Paulina,
  fraza PL) był tylko w globalnym `~/.claude/settings.json`; do repo trafił uniwersalny rdzeń, nie
  żywy hook (reguła 13a — personalny hook narzucałby głos każdemu klonowi). Technicznie:
  `docs/SETUP.md` krok 8d — przełącznik `tts.on`→`speak.on`, Windows używa głosu „Microsoft Paulina
  Desktop" (try/catch fallback) + fraza „Gotowe.", oba warianty (Win + mac/linux) doklejają nazwę
  folderu roboczego (`Split-Path -Leaf $PWD` / `basename $PWD`) — tytułu okna Claude hooki nie widzą.
  Nowe `.claude/commands/speak-on.md` + `speak-off.md` (tworzą/usuwają `~/.claude/speak.on`) jadą
  z klonem, ale mówiący hook zostaje per-maszyna (do wklejenia z SETUP 8d). Globalny `settings.json`
  usera zaktualizowany przy okazji (poza repo). User przetestował lektora na żywo.

- 2026-06-14: **ADR-004 korekta — board zdegradowany do opcjonalnego (wynik pilotażu).**
  Pierwszy pilotaż wykonania metody Issues/Projects w projekcie pochodnym (model 1 właściciel
  + AI) obalił §2 w części „board = widok statusu": kanban bez wartości dla solo (nikt nie
  patrzy — start to sesja, koniec to merge PR-a), oczekiwany auto-postęp na tablicy nie
  istnieje OOTB (dobudowa = przerost, reguła 5/17), a realną potrzebę („czy projekt na czas")
  pokrywa strona Milestones (termin + % zamkniętych). Korekta: blok „Korekta 2026-06-14"
  + wskaźniki w §2/§4/Konsekwencjach — widok statusu = Milestones, board opcjonalny, widok
  „Roadmap" Projects opcjonalny. Kolumna „Up next" zostaje, ale oznaczona jako
  niezweryfikowana pilotażem (kolejność wykonania ≠ dashboard statusu — osobny argument,
  którego pilotaż nie testował; do sprawdzenia w kolejnym projekcie). Reszta decyzji
  (Issues=dane, `Closes #N`, milestones, markdown fallback) bez zmian. Branch
  `docs/adr-004-board-optional`.
- 2026-06-14: **scrub nazw projektów pochodnych z logu (reguła 13a).** Log tai przeciekał
  nazwami konkretnych projektów — proweniencja („wykryte w X") i operacyjne TODO. Rozdział:
  czysta proweniencja → „projekt pochodny" (zero straty); operacyjne TODO związane z nazwanym
  projektem (migracja KROK 3 config-canonicalizacji; pilot wykonania metody TAIGA + kryterium
  oceny) → prywatny, gitignorowany `docs/MAINTAINER_BACKLOG.local.md`. Zasada: generyczna metoda
  i lekcja zostają w commitowanym logu, projektowe wykonanie wychodzi. Atrybucja vendoringu
  (`coreyhaines31/marketingskills`) zostaje — to wymagane źródło zewnętrznego kodu, nie
  proweniencja. `.gitignore`: `docs/*.local.md`. Branch `chore/scrub-project-names`.
- 2026-06-14: `.gitignore` — dodany `.claude/hooks/.sync-hash`. To per-klon stan synchronizacji
  z template'em (`session-context.py` zapisuje hash HEAD template'u po auto-syncu, żeby przy
  starcie sesji wykryć drift). Nie jest współdzielonym baseline'em — gdyby był commitowany, stan
  synchronizacji jednego klonu nadpisywałby inny i każdy sync robiłby śmieciowy diff; dotąd wisiał
  jako untracked w każdym klonie. Branch `chore/gitignore-sync-hash`. Pochodne projekty dostaną
  wpis przez sync.
- 2026-06-14: nowa reguła workflow w `CLAUDE.md` §3 — **sprzątanie brancha po merge'u**. Po
  potwierdzeniu merge'a przez usera AI od razu proponuje i wykonuje `checkout main` → `pull` →
  usunięcie zmergowanego brancha (lokalnie `git branch -d` + zdalnie); kolejne zadanie startuje
  z czystego, dociągniętego maina. Trigger = zmergowany PR, nie „koniec sesji"; `git branch -d`
  (nie `-D`) odmawia skasowania niezmergowanej pracy, więc in-flight branche są bezpieczne.
  Feedback wykryty w sesji projektowej pochodnej (stale branch po merge'u PR + niedociągnięty
  lokalny main) — lekcja systemowa, więc ląduje w template (reguła 13a), nie w projekcie. Branch
  `docs/branch-cleanup-rule`. Pochodne projekty dostaną regułę przez sync skilli/CLAUDE.md.
- 2026-06-13: fix `guard-template-sync` (hook) — czytał `[skip-sync]` tylko z komendy, więc
  `git commit -F <plik>` z flagą w pliku był wadliwie blokowany (wykryte przy domykaniu commita
  w projekcie pochodnym na Windows/PowerShell, gdzie wieloliniowy message idzie przez plik). Bliźniaczy
  `guard-ai-template` umiał czytać `-F` od 2026-06-04, ale template-sync przeoczono. Fix:
  ekstrakcja wiadomości (`-m`/heredoc/here-string/`-F`) wyniesiona do współdzielonego
  `get_commit_message()` w `.claude/hooks/stack.py`; oba hooki jej używają (koniec dwóch kopii
  regexa); bypass sprawdza `haystack = command + message`. Testy: `-F` z flagą przepuszcza,
  `-F` bez flagi nadal blokuje (brak cichego bypassu) — 115/115 suite. Branch
  `fix/template-sync-read-file`. Efekt w projektach pochodnych: fix wsiąknie przez sync skilli.
- 2026-06-07: nowa sekcja „SEO / znajdowalność — wzorce z buildu" w `docs/AI_TEMPLATE_NOTES.md`.
  Lekcja z projektu pochodnego (cel: znajdowalność): trzy uniwersalne wzorce — (1) treść
  renderowana po stronie klienta = pusta strona dla crawlera → pre-render/SSG, diagnoza `curl|grep`;
  (2) jedno źródło domeny (`baseUrl`) → og/robots/sitemap generowane na buildzie, `lastmod` z daty
  zmiany treści nie deployu; (3) testuj output SEO (surowy HTML ma treść, host spójny w og/robots/
  sitemap, JSON-LD parsuje się i `<` zescape'owany). **Forma:** świadomie NIE w skillu `seo` — ten
  jest vendored (zewnętrzna referencja); lekcja z praktyki idzie do tai-owned `AI_TEMPLATE_NOTES.md`
  (ładowany na starcie każdej sesji). Bez testu — to wiedza, nie guard (13a). Branch
  `docs/seo-build-time-patterns` z main.

- 2026-06-04: dopisana uniwersalna meta-zasada do `docs/AI_TEMPLATE_NOTES.md` (sekcja
  „Praca z AI — meta-zasady"): nowy UI nie startuje od estetyki „AI-default", zakotwicz
  w specyfice biznesu, dopcham jeden kierunek do końca, sygnalizuj gdy coś pachnie
  AI-średnią. Lekcja wyciągnięta z sesji designu w projekcie pochodnym (5 makiet hero →
  pierwsze szkice były generyczne; user złapał regresję do średniej). Część user-specific
  została w pamięci maszynowej projektu, do template'u trafił tylko uniwersalny rdzeń
  (reguła 13a). Branch `docs/ui-anti-ai-default`.
- 2026-06-04: Config canonicalizacja KROK 2 KOMPLETNY (branch `feat/config-canonical-template-sync`).
  ADR-002 accepted. A: `reset_adr_dir` czyści `docs/adr/` przy init. B: `create_config_json`
  bez `_git_remote_url`, zostawia placeholder (bug A skasowany). C: `dev-guards/stack.py`
  `CONFIG_PATH` → `.claude/hooks/config.json`, wyczyszczone ślady `.pre-commit-hooks.config.json`.
  D: oba guardy sync (pre-commit + Claude hook) na tryb potwierdzenia — brak klona/URL/zła ścieżka
  → blokada-ack na CLAUDE.md (koniec cichego skipu); klon → auto-weryfikacja. E: `tai/.claude/hooks/
  config.json` z `is_template: true` → guardy no-op we wzorcu. Testy: 111/111 (nowe
  `test_guard_template_sync` 16, `_hook` 7). **KROK 3 (migracja projektu pochodnego) → prywatny
  backlog** — szczegóły projektowe poza commitowanym logiem template'u (`docs/MAINTAINER_BACKLOG.local.md`;
  reguła 13a; Zasada B).
- 2026-06-04: durable lessons utrwalone (branch `docs/durable-ai-lessons`). Wnioski 1–3
  (bezstanowość AI → system nie ufa AI; guardy bywają fail-open/martwe → user realnym
  guardem; template=produkt) → `docs/AI_TEMPLATE_NOTES.md`. Zasady A/B (guard tylko z
  testem; rozdziel sesje system/projekt) → `CLAUDE.md` reguła 13a. Lekcje praktyczne
  (utf-8 na stdout/stderr hooków, guard commit-msg fail-closed) → sekcja guard w NOTES.
  Items 4–6 hardeningu domknięte poza canonicalizacją `ai_template_path` (osobna sesja
  z ADR — patrz „Następna sesja" + backlog).
- 2026-06-04: zwendorowano skille `copywriting` + `cro` z coreyhaines31/marketingskills
  (commit `7f4af1ea`) — wpisy w `skills-manifest.json`, pobrane przez `update-skills.py
  --apply` (skan bezpieczeństwa czysty), wiersze w obu tabelach `docs/SKILLS.md`. Branch
  `feat/vendor-marketing-skills` z main. Item 5 z listy hardeningu 4–6 domknięty. Przy
  okazji wykryto martwy `script_integrity` (→ backlog).
- 2026-06-04: hardening hooków (branch `fix/template-hardening`). Wykryte podczas pracy
  w projekcie pochodnym: (1) `guard-ai-template` puszczał commit przy `git commit -F`
  bo `extract_commit_type` parsował tylko `-m` → cichy bypass; przepisany na fail-closed
  + czytanie wiadomości/flag z pliku `-F`, heredoc, here-string; gdy nie umie odczytać
  wiadomości → blok. Dodatkowo blokuje przy każdym tknięciu plików template'owych (dowolny
  typ), nie tylko feat/fix/docs/refactor. (2) `session-context._remote_head_hash` —
  `ls-remote` bez `encoding=utf-8` → wyjątek w wątku readera na Windows (cp1250); dodano
  `encoding="utf-8", errors="replace"`. (3) `update-skills.py` — brak `stdout.reconfigure`
  → crash przy emoji w `print` na cp1250; dodano reconfigure jak w `stack.py`/`session-context`.
  Przetestowane ręcznie (guard: 5 scenariuszy exit-code; update-skills: emoji print bez crashu).
  Items 4–6 (guard-template-sync URL, skille copywriting/cro do manifestu, AI_TEMPLATE_NOTES)
  odłożone — item 4 łączy się z backlogiem „Config canonicalizacja ai_template_path (+ADR)".
- 2026-06-03: fix `update-skills` — `collect_files` używał `str(rel)` (backslashe na
  Windows → rozjazd manifestu między OS). Zmiana na `rel.as_posix()`; 2 wcześniej
  czerwone testy `TestCollectFiles` zielone, 35/35 modułu. Branch `fix/update-skills-path-separator`.
  Wykryto przy okazji: config canonicalizacja (backlog) + błąd A/Q2 w `new-project` (fokus).
- 2026-06-03: `new-project.py` domknięty dla trybu `--init` — reset wersjonowania
  + fresh git + init commit + instalacja guardów. 29/29 testów modułu, 2× e2e na
  realnym klonie. Powiązany fix `update-skills` (posix paths) → PR #54. Config
  canonicalizacja + błąd A świadomie odłożone na osobną sesję z ADR (backlog).
- 2026-07-25: **Odwrócona domyślna rekomendacja CI — jeden job zamiast równoległych
  (branch `chore/ci-cost-model`, #104).** Powód z pomiaru: trzy projekty na tym template'cie
  wyczerpały wspólny darmowy limit 2000 min GitHub Actions w połowie miesiąca (lipiec: skolaro 986,
  cdue 779, cdue-elearning 227 = 1992). Template zalecał „niezależne checki w równoległych jobach",
  co pomijało jednostkę rozliczeniową: **Actions nalicza każdy JOB w górę do pełnej minuty** —
  zmierzone 487 min pracy → 779 min naliczonych (37% to zaokrąglanie), a w drugim repo 152 z 227 min
  to joby robiące po ~15 s. Do tego `push: main` po merge'u = duplikat wyniku z PR-a (połowa rachunku).
  Zmiana: `AI_TEMPLATE_NOTES` → jeden job domyślnie, zrównoleglenie jako świadomy wyjątek gdy minut
  jest w nadmiarze; dopisana metoda pomiaru (API rachunku bywa zerowe/bez scope'u — licz z czasów
  jobów, filtruj joby z 0 kroków = te które nie wystartowały z braku minut). `ci.yml`: trigger tylko
  `pull_request`, scaffold checków jako kroki w jobie `checks`, osobny job tylko dla skanera we
  własnym kontenerze. Wdrożenia w projektach = osobne PR-y (cdue #327).
- 2026-07-25 (cd.): **Korekta rekomendacji CI — nie „jeden job domyślnie", tylko trzy ruchy w kolejności
  ROI (#104).** Pierwsza wersja tej zmiany ustawiała jeden sekwencyjny job jako domyślny; właściciel
  odrzucił to w projekcie, bo wydłużało oczekiwanie na PR z ~2 do ~4-5 min. Wniosek dla template'u jest
  inny niż pierwotny: **dwa pierwsze ruchy są darmowe czasowo i robimy je zawsze** (zdjęcie CI z
  `push: main`; każde sprawdzenie krótsze niż minuta jako krok w jobie spoza ścieżki krytycznej —
  skaner pracujący 8 s w osobnym jobie kosztuje tyle co minuta builda). **Trzeci ruch — scalenie
  równoległych nóg — JUŻ kosztuje czas i nie ma domyślnej odpowiedzi**: policz obie strony i zapytaj
  właściciela. `ci.yml`: scaffold matrycy i builda wrócił jako opcja obok, z ceną obu stron w komentarzu;
  skan CVE opisany jako krok, nie job. Zostaje reguła zaokrąglania i metoda pomiaru (API rachunku bywa
  zerowe; licz z czasów jobów, odrzuć joby z 0 kroków = te które nie wystartowały z braku minut).
