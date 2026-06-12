# AI Template Notes

Wnioski z praktyki pracy z AI — wyłącznie wzorce universalne, niezależne od domeny.
Każdy nowy projekt dokłada tu swoje obserwacje. Sekcje domenowe nie trafiają tu — idą do `docs/CONVENTIONS.md` lub `docs/UI_GUIDELINES.md` projektu.

---

## Praca z AI — meta-zasady

- **Po 2-3 nieudanych iteracjach — zatrzymaj się i zapytaj o cel, nie proponuj kolejnej wariacji** — jeśli kolejne próby dają wynik "nadal nie to", problem nie leży w implementacji tylko w niejasnym celu. AI powinno powiedzieć wprost: "coś jest nie tak z kierunkiem — powiedz mi co ten element ma robić dla odbiorcy" i poczekać na odpowiedź. Kontynuowanie iteracji bez tego to przepalanie tokenów i czasu.
- **AI jest bezstanowy — system ma NIE ufać AI** — co nie jest utrwalone w repo (kod, guard z testem, dokument), znika między sesjami. Liczenie na to, że AI "zapamięta" intencję albo "zrozumie" jak ma być, to bug projektu, nie cecha. Każda lekcja musi wylądować w artefakcie egzekwowalnym albo dokumencie — nigdy "w głowie AI". Jeśli jedyne miejsce gdzie żyje zasada to kontekst sesji, ta zasada nie istnieje.
- **Guardy bywają fail-open albo martwe — user wciąż jest realnym guardem** — guardy pisze ten sam AI, który pod presją tnie zakręty, więc bywają dziurawe: przepuszczają to co miały łapać (fail-open) albo nigdy się nie odpalają (martwe). Dopóki guard nie ma testu dowodzącego że działa, ostatnią linią obrony jest człowiek czytający diff. AI nie traktuje "guard przeszedł" jako dowodu poprawności — tylko jako brak złapanego naruszenia.
- **Wzorzec/template = produkt; projekty = miejsca gdzie wychodzą jego błędy** — gdy wzorzec zawiedzie w realnej pracy, naprawiasz go u źródła (w template/guardzie z testem), nie tylko lokalnie. Lekcja zatrzymana w projekcie zostaje "w głowie" = nigdzie; przeniesiona do guarda z testem pracuje za Ciebie w każdym kolejnym projekcie.
- **Nowy UI nie startuje od estetyki „AI-default" — zakotwicz w specyfice biznesu** — galerie i generatory UI zbiegają do średniej z treningu (Linear-look, gradient mesh, bento z katalogu), więc start od „ładnego wzorca z galerii" daje wynik nie do odróżnienia od tysiąca innych. Wyróżnienie bierze się z konkretu projektu (motyw, branża, lokalność, głos odbiorcy), nie z trendu. Praktycznie: zakotwicz kierunek w biznesie zanim zaczniesz, dopcham JEDEN kierunek do końca zamiast rozdawać kilka powierzchownych szkiców, i mów wprost gdy coś pachnie AI-średnią — to sygnał do cofnięcia, nie do kolejnej skórki.

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

## SEO / znajdowalność — wzorce z buildu

- **Treść renderowana po stronie klienta = pusta strona dla crawlera** — jeśli sekcje powstają w przeglądarce (`fetch()` + `innerHTML`, hydracja SPA, cokolwiek zależnego od JS), surowy HTML, który crawler dostaje jako pierwszy, jest pusty. Googlebot renderuje JS, ale z opóźnieniem i zawodnie — zabójcze dla świeżej domeny w piaskownicy. Pre-render / SSG / SSR tak, żeby treść była w HTML. Diagnoza jednym strzałem: `curl -s URL | grep "fragment widocznej treści"` → 0 trafień = crawler nie widzi nic. To pierwsza rzecz do sprawdzenia przy SEO, przed strojeniem tagów.
- **Jedno źródło prawdy dla domeny** — domena pojawia się w `og:url`, `og:image`, linii `Sitemap:` w robots.txt i w każdym `<loc>` sitemapy. Przepisywana ręcznie w czterech miejscach — rozjedzie się. Trzymaj ją w jednej wartości configu (`baseUrl`) i generuj wszystkie cztery na buildzie. Generowanie robots/sitemap na buildzie (zamiast ręcznych plików statycznych) trzyma też `lastmod` uczciwym — wyprowadź go z daty zmiany treści (np. `git log -1 --format=%cs -- <plik z treścią>`), nie z czasu deployu.
- **Testuj output SEO, nie intencję** — tanie guardy regresji łapiące powyższe bugi: (1) surowy zbudowany HTML zawiera reprezentatywną treść body (to `curl|grep` z punktu 1, jako asercja); (2) host w `og:url` == host w `<loc>` sitemapy == host w `Sitemap:` robots (brak driftu); (3) JSON-LD danych strukturalnych parsuje się, a `<` jest zescape'owany (`<`), żeby nie wyłamał się z `<script>`.

---

## CI — wydajność pipeline'u

- **Niezależne checki w równoległych jobach, nie sekwencyjnie w jednym** — lint, test, typecheck i build nie zależą od siebie. W jednym jobie wall-clock = suma; w osobnych jobach = najdłuższy leg. Realnie skraca oczekiwanie na PR (obserwowane ~o 1/3–1/2). Koszt: każdy job powtarza setup (checkout + instalacja zależności) → więcej minut runnera. Świadomy trade-off: szybszy feedback loop vs zużycie minut — wart na aktywnym repo, mniej gdy minuty są limitowane.
- **Identyczne checki przez `strategy.matrix`, nie copy-paste jobów** — test/lint/typecheck mają ten sam setup, różni je tylko końcowa komenda. Matrix z `{name, cmd}` + `fail-fast: false` (żeby jeden czerwony leg nie ubił feedbacku z reszty). Build zwykle osobnym jobem, bo niesie własny cache.
- **Cache katalogu cache build-toola między runami** — `setup-*` cache'uje zwykle tylko menedżer pakietów (`~/.npm`, `~/.cache/pip`), nie cache samego builda (`.next/cache`, `target/`, `build/`, `.gradle/`…). Bez tego build leci od zera za każdym runem. `actions/cache` na katalogu cache build-toola z `restore-keys` na same zależności → build inkrementalny nawet gdy źródła się zmieniły. **Zysk widać dopiero od 2. runu** (1. populuje cache) — nie myl braku przyspieszenia na 1. runie z brakiem działania.
- **Po zrównolegleniu krytyczną ścieżką jest najdłuższy job (zwykle build)** — reszta kończy wcześniej i nie wpływa już na wall-clock. Dalsze skracanie = przyspieszenie tego jednego joba (szybszy bundler/kompilator), nie kolejne tasowanie struktury.

---

<!-- Dodawaj nowe sekcje gdy pojawi się universalny wzorzec z projektu. -->
<!-- Nie dodawaj tu wzorców domenowych (konkretny framework, biblioteka, biznes). -->
