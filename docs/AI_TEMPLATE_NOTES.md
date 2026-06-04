# AI Template Notes

Wnioski z praktyki pracy z AI — wyłącznie wzorce universalne, niezależne od domeny.
Każdy nowy projekt dokłada tu swoje obserwacje. Sekcje domenowe nie trafiają tu — idą do `docs/CONVENTIONS.md` lub `docs/UI_GUIDELINES.md` projektu.

---

## Praca z AI — meta-zasady

- **Po 2-3 nieudanych iteracjach — zatrzymaj się i zapytaj o cel, nie proponuj kolejnej wariacji** — jeśli kolejne próby dają wynik "nadal nie to", problem nie leży w implementacji tylko w niejasnym celu. AI powinno powiedzieć wprost: "coś jest nie tak z kierunkiem — powiedz mi co ten element ma robić dla odbiorcy" i poczekać na odpowiedź. Kontynuowanie iteracji bez tego to przepalanie tokenów i czasu.
- **AI jest bezstanowy — system ma NIE ufać AI** — co nie jest utrwalone w repo (kod, guard z testem, dokument), znika między sesjami. Liczenie na to, że AI "zapamięta" intencję albo "zrozumie" jak ma być, to bug projektu, nie cecha. Każda lekcja musi wylądować w artefakcie egzekwowalnym albo dokumencie — nigdy "w głowie AI". Jeśli jedyne miejsce gdzie żyje zasada to kontekst sesji, ta zasada nie istnieje.
- **Guardy bywają fail-open albo martwe — user wciąż jest realnym guardem** — guardy pisze ten sam AI, który pod presją tnie zakręty, więc bywają dziurawe: przepuszczają to co miały łapać (fail-open) albo nigdy się nie odpalają (martwe). Dopóki guard nie ma testu dowodzącego że działa, ostatnią linią obrony jest człowiek czytający diff. AI nie traktuje "guard przeszedł" jako dowodu poprawności — tylko jako brak złapanego naruszenia.
- **Wzorzec/template = produkt; projekty = miejsca gdzie wychodzą jego błędy** — gdy wzorzec zawiedzie w realnej pracy, naprawiasz go u źródła (w template/guardzie z testem), nie tylko lokalnie. Lekcja zatrzymana w projekcie zostaje "w głowie" = nigdzie; przeniesiona do guarda z testem pracuje za Ciebie w każdym kolejnym projekcie.

---

## Guard system — infrastruktura

- **`exit(2)` blokuje, `exit(1)` nie** — PreToolUse hook musi wyjść z kodem 2 żeby zablokować tool use. Exit 1 (np. unhandled exception w Pythonie) nie blokuje — narzędzie wykona się normalnie.
- **Komunikat blokujący idzie przez `stderr`, nie `stdout`** — Claude Code wyświetla `stderr` jako powód blokady. Print na `stdout` w blokującym hooku znika.
- **CWD hooka = CWD basha który go triggeruje** — nie ma stałego CWD dla hooków; jeśli użytkownik/AI zrobi `cd podkatalog`, hooki uruchomią się z tego podkatalogu. Rozwiązanie: każdy skrypt hooka na starcie wywołuje `git rev-parse --show-toplevel` i robi `os.chdir()` do roota projektu.
- **Ścieżki w `settings.json` są relatywne do CWD w momencie wykonania** — jeśli CWD = projekt root, użyj `.claude/hooks/skrypt.py`; jeśli CWD = `.claude/hooks/`, użyj `skrypt.py`. Nie zakładaj stałego CWD.
- **Hookom dane przychodzą przez stdin jako JSON** — format: `{"tool_name": "Bash", "tool_input": {"command": "..."}, "cwd": "...", ...}`. Komenda do sprawdzenia: `data["tool_input"]["command"]`.
- **Na Windows wymuś utf-8 na stdout/stderr każdego skryptu hooka** — domyślny `cp1250` wywala `print` z emoji lub znakami PL (`UnicodeEncodeError`), co potrafi zabić wątek czytający output i zostawić proces w niespójnym stanie. Na starcie skryptu: `sys.stdout.reconfigure(encoding="utf-8")` i to samo dla `stderr`. Dotyczy też pomocniczych skryptów (`scripts/*.py`), nie tylko hooków.
- **Guard czytający commit message musi być fail-closed** — gdy nie potrafi odczytać wiadomości albo flag (bo przyszły inną drogą niż guard zakłada), domyślnie BLOKUJE, nie przepuszcza. Guard parsujący tylko jeden sposób przekazania wiadomości (`-m`) cicho puszcza commit zrobiony inaczej (`-F`, heredoc, here-string) — to fail-open. Czytaj wiadomość ze wszystkich realnych źródeł, a w razie wątpliwości blokuj; fałszywy alarm jest tańszy niż cichy bypass.

---

<!-- Dodawaj nowe sekcje gdy pojawi się universalny wzorzec z projektu. -->
<!-- Nie dodawaj tu wzorców domenowych (konkretny framework, biblioteka, biznes). -->
