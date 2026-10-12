# Tasks

Ten plik jest **logiem sesji**: co się wydarzyło i dlaczego. Otwarta praca szablonu żyje
w GitHub Issues (`gh issue list`), nie tutaj. Fazy definiuje [docs/ROADMAP.md](ROADMAP.md).

---

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
