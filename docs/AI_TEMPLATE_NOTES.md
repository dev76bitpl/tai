# AI Template Notes

Wnioski z praktyki pracy z AI — wyłącznie wzorce universalne, niezależne od domeny.
Każdy nowy projekt dokłada tu swoje obserwacje. Sekcje domenowe nie trafiają tu — idą do `docs/CONVENTIONS.md` lub `docs/UI_GUIDELINES.md` projektu.

---

## Praca z AI — meta-zasady

- **Po 2-3 nieudanych iteracjach — zatrzymaj się i zapytaj o cel, nie proponuj kolejnej wariacji** — jeśli kolejne próby dają wynik "nadal nie to", problem nie leży w implementacji tylko w niejasnym celu. AI powinno powiedzieć wprost: "coś jest nie tak z kierunkiem — powiedz mi co ten element ma robić dla odbiorcy" i poczekać na odpowiedź. Kontynuowanie iteracji bez tego to przepalanie tokenów i czasu.

---

## Guard system — infrastruktura

- **`exit(2)` blokuje, `exit(1)` nie** — PreToolUse hook musi wyjść z kodem 2 żeby zablokować tool use. Exit 1 (np. unhandled exception w Pythonie) nie blokuje — narzędzie wykona się normalnie.
- **Komunikat blokujący idzie przez `stderr`, nie `stdout`** — Claude Code wyświetla `stderr` jako powód blokady. Print na `stdout` w blokującym hooku znika.
- **CWD hooka = CWD basha który go triggeruje** — nie ma stałego CWD dla hooków; jeśli użytkownik/AI zrobi `cd podkatalog`, hooki uruchomią się z tego podkatalogu. Rozwiązanie: każdy skrypt hooka na starcie wywołuje `git rev-parse --show-toplevel` i robi `os.chdir()` do roota projektu.
- **Ścieżki w `settings.json` są relatywne do CWD w momencie wykonania** — jeśli CWD = projekt root, użyj `.claude/hooks/skrypt.py`; jeśli CWD = `.claude/hooks/`, użyj `skrypt.py`. Nie zakładaj stałego CWD.
- **Hookom dane przychodzą przez stdin jako JSON** — format: `{"tool_name": "Bash", "tool_input": {"command": "..."}, "cwd": "...", ...}`. Komenda do sprawdzenia: `data["tool_input"]["command"]`.

---

<!-- Dodawaj nowe sekcje gdy pojawi się universalny wzorzec z projektu. -->
<!-- Nie dodawaj tu wzorców domenowych (konkretny framework, biblioteka, biznes). -->
