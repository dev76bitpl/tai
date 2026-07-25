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

- **Jednostką rozliczeniową jest JOB, zaokrąglany w górę do pełnej minuty** — to dominuje rachunek, zanim zaczniesz optymalizować cokolwiek innego. Job pracujący 19 s kosztuje minutę. Pięć 45-sekundowych jobów kosztuje 5 minut; ta sama praca w jednym jobie kosztuje 4. **Zmierzone na realnym repo:** 487 minut faktycznej pracy → 779 minut naliczonych, czyli **37% rachunku to samo zaokrąglanie**. W drugim repo z tej rodziny 152 z 227 minut to joby wykonujące po ~15 s pracy. Wniosek: **domyślnie dokładaj KROK do istniejącego joba, nie nowy job.**
- **Najpierw dwa ruchy, które nie kosztują ani sekundy oczekiwania** — zrób je zawsze, zanim w ogóle zaczniesz rozważać strukturę jobów: (1) zdejmij CI z `push: main`, (2) każde sprawdzenie krótsze niż minuta wciągnij jako **krok do joba spoza ścieżki krytycznej** (guardy, skan lockfile'a, drobne walidacje) zamiast dawać mu własny job. Skaner pracujący 8 s we własnym jobie kosztuje tyle samo co minuta builda. Te dwa ruchy potrafią zdjąć ponad połowę rachunku bez żadnego kompromisu.
- **Scalanie równoległych nóg w jeden job to dopiero trzeci ruch — i on JUŻ kosztuje czas** — wall-clock przestaje być najdłuższą nogą, a staje się sumą kroków, i pierwszy błąd zatrzymuje resztę (tracisz „wszystkie trzy wyniki naraz"). Zysk: `npm ci` raz zamiast raz na nogę + jedna zaokrąglona minuta zamiast trzech. **Nie ma tu domyślnej odpowiedzi — policz obie strony i zapytaj właściciela.** Realny przykład z projektu: scalenie oszczędzało ~190 min/mies., ale wydłużało czekanie na każdym PR z ~2 do ~4-5 min; właściciel odrzucił, bo po dwóch darmowych ruchach rachunek i tak mieścił się w limicie. Jeśli zostawiasz równoległość: `strategy.matrix` z `{name, cmd}` + `fail-fast: false`, build osobnym jobem (najdłuższa noga — obok matrycy nie wydłuża wall-clocku, doklejony do niej wydłuża).
- **CI na `push: main` po merge'u to duplikat wyniku z PR-a** — ten sam commit, ten sam rezultat, drugi rachunek. Zmierzone: **połowa** rachunku repo. Domyślnie trigger tylko `pull_request`; workflow releasowy zostaje na `push: main`, bo bez tego nie ma wersjonowania. Przyjmowane ryzyko: gdy `main` ruszy się między zielonym PR-em a merge'em, konflikt semantyczny wjedzie niesprawdzony — małe przy jednym utrzymującym, rośnie z liczbą równoległych PR-ów.
- **Job wyzwalany osobnym zdarzeniem ma podłogę 1 minuty** — np. check języka PR-a odpalany na `edited` robi 7 s pracy i kosztuje minutę za każdą edycję opisu. Scalenie go z CI oszczędza minuty, ale gubi ponowne sprawdzenie po poprawce opisu (CI domyślnie nie słucha `edited`). Świadomy wybór, nie oczywistość.
- **Diagnoza zużycia: licz z czasów jobów, nie z API rachunku** — endpoint `/actions/runs/{id}/timing` potrafi zwracać `billable.total_ms: 0` na kontach osobistych, a `/settings/billing` wymaga scope'u `user`, którego token zwykle nie ma. Wiarygodna metoda: `/actions/runs/{id}/jobs`, różnica `completed_at − started_at`, **każdy job zaokrąglony w górę do minuty**. Uwaga na artefakt: gdy minuty się skończą, joby kończą się po ~2 s z `conclusion: failure` i **zerową liczbą kroków** — to nie awaria kodu i tego nie wolno wliczać do zużycia (filtruj po `steps > 0`).
- **Cache katalogu cache build-toola między runami** — `setup-*` cache'uje zwykle tylko menedżer pakietów (`~/.npm`, `~/.cache/pip`), nie cache samego builda (`.next/cache`, `target/`, `build/`, `.gradle/`…). Bez tego build leci od zera za każdym runem. `actions/cache` na katalogu cache build-toola z `restore-keys` na same zależności → build inkrementalny nawet gdy źródła się zmieniły. **Zysk widać dopiero od 2. runu** (1. populuje cache) — nie myl braku przyspieszenia na 1. runie z brakiem działania.
- **Po zrównolegleniu krytyczną ścieżką jest najdłuższy job (zwykle build)** — reszta kończy wcześniej i nie wpływa już na wall-clock. Dalsze skracanie = przyspieszenie tego jednego joba (szybszy bundler/kompilator), nie kolejne tasowanie struktury.

## CI — skanery bezpieczeństwa

Trzy warstwy skanowania w CI, każda łapie inną klasę problemu:

- **Sekrety** (np. gitleaks) — zwykle już pokryte: hook pre-commit odpalany server-side w jobie `guards` skanuje całe drzewo. Nie duplikuj osobnym jobem.
- **SAST — własny kod** (np. semgrep z regułami pod stack) — szuka wzorców podatności w kodzie który sam piszesz (injection, XSS, brak walidacji). **Blokujący**: findings w twoim kodzie zawsze da się naprawić, więc czerwony build jest akcjonowalny. False-positive wyciszaj inline z komentarzem i uzasadnieniem (audit trail, jak bypass guarda) — nie luzuj całej reguły.
- **CVE zależności** (np. skaner lockfile'a przeciwko bazie znanych dziur) — sprawdza cudze biblioteki które shippujesz. **Raportujący na start** (`continue-on-error`): CVE w niezałatywalnej transitive zależności nie może blokować każdego merge'a. Gdy poznasz realny stosunek sygnał/szum — możesz zacisnąć do blokującego.

**Pułapka raportującego skanera**: narzędzie zwykle kończy kodem ≠0 gdy **cokolwiek** znajdzie, co maluje czerwoną adnotację „exit code 1" na każdym PR z zaakceptowanym/niezałatywalnym CVE — fałszywy alarm mimo `continue-on-error`. Obsłuż kod wyjścia jawnie: pochłoń „znaleziono podatność" (oczekiwany przypadek raportowania), ale **przepuść realny błąd narzędzia** (np. nieudane pobranie/parsowanie binarki) — inaczej po cichu chowasz awarię skanera. Findings zostają w logu joba niezależnie.

**Nie ufaj automatycznemu „fix" na ślepo**: menedżer pakietów potrafi zaproponować jako naprawę **downgrade** kluczowej zależności, żeby dopiąć graf ograniczeń — co cofa łatkę bezpieczeństwa. Czytaj co narzędzie faktycznie zmienia. Major-bump zależności przez CVE weryfikuj przez breaking-changes vs realne użycie (mała powierzchnia użycia = niskie ryzyko mimo majora).

---

## Topologia domen / hostów — wzorce

Gdy produkt ma jednocześnie publiczną twarz (marketing/sprzedaż) i zalogowaną aplikację, albo gdy jest jednym z wielu produktów jednej marki — topologia hostów to decyzja architektoniczna (ADR), nie detal DNS. Ustala się ją raz, bo determinuje auth, cookie i routing.

- **Rozdziel warstwy hostem: marketing (indeksowany) osobno od aplikacji (noindex)** — publiczna strona sprzedażowa musi być w indeksie wyszukiwarki, zalogowana apka z danymi użytkowników nie może. Jeden host nie może być naraz `index` i `noindex`. Rozdzielenie subdomeną (marketing na jednym hoście, apka na drugim) rozwiązuje to u źródła i pozwala niezależnie deployować. **Pułapka:** globalny `noindex` w root layoucie apki obejmuje KAŻDĄ trasę — landing dodany jako route w tej samej apce odziedziczy noindex; marketing musi być osobnym deploymentem.
- **Marka z wieloma produktami → namespace hostów per produkt** — `<produkt>.marka.tld` (marketing) + `panel.<produkt>.marka.tld` (apka). Płaski wspólny host apki (`panel.marka.tld`) staje się dwuznaczny przy drugim produkcie („panel czego?"). Namespace per produkt skaluje się bez przemianowań przy każdym kolejnym produkcie.
- **SSO między subdomenami: dedykowany host tożsamości + redirect, NIE współdzielone cookie na domenie-matce** — cookie sesji ustawione na `.marka.tld` leci do wszystkich subdomen (też tych bez uprawnień) → wektor przejęcia sesji, plus łamie się o restrykcje third-party cookies w przeglądarkach. Wzorzec: osobny host auth (`konto.`/`auth.`/`accounts.`) trzyma sesję u siebie, aplikacje dostają tokeny przez OIDC redirect. Zarezerwuj ten host wcześnie, nawet jeśli SSO budujesz później. To typowy błąd amatorski — parent-cookie „bo działa lokalnie".
- **Nazwa hosta apki jest user-facing — dobierz do odbiorcy, nie do konwencji deweloperskiej** — host, który użytkownik widzi przy logowaniu, komunikuje. Międzynarodowa/deweloperska konwencja (`app.`) nie zawsze jest najczytelniejsza dla nietechnicznego, lokalnego odbiorcy — sprawdź rodzimą konwencję rynku zanim zaklepiesz. Obie mogą być technicznie równorzędne; wygrywa rozpoznawalność u odbiorcy.
- **Przy zmianie hosta rozróżnij env wypalany w build od czytanego w runtime** — zmienne inline'owane do bundla klienta na buildzie (prefiks typu `NEXT_PUBLIC_*` w Next i analogiczne w innych frameworkach) NIE zmienią się po samym restarcie procesu — wymagają rebuildu. Env czytany server-side w runtime wystarczy restartem. Przenosząc apkę na nowy host sprawdź które zmienne są które, inaczej część linków/URL-i (maile, kody QR, absolutne adresy) niesie stary host mimo „zmienionego env".
- **Redirect starego hosta: 302 gdy host ma zmienić przeznaczenie, 301 gdy znika na stałe** — 301 (permanent) keszuje się trwale w przeglądarkach. Jeśli stary host ma później służyć czemu innemu (klasyk: apka przenosi się na nowy host, a stary staje się landing page), zakeszowany 301 będzie kierował userów w złe miejsce jeszcze długo po zmianie. Użyj 302, gdy przeznaczenie hosta jeszcze się zmieni.

---

## Topologia środowisk (prod / staging / demo na współdzielonej infrze) — wzorce

Gdy kilka środowisk tego samego produktu (produkcja + staging + demo) żyje na jednej maszynie, sposób ich współistnienia to decyzja architektoniczna (ADR), nie improwizacja przy pierwszym `deploy`. Ustala się ją zanim postawi się drugą instancję — inaczej druga koliduje z pierwszą.

- **Pełna izolacja, nic współdzielonego** — każde środowisko ma własną bazę, własny proces, własny port, własny plik konfiguracji, własny katalog. NIE współdziel bazy ani sieci między środowiskami. Powód podwójny: (1) build/migracja na staging **nie może** tknąć produkcji (to cały sens stagingu — siatka przed dotknięciem żywych danych), (2) wspólna baza przecieka żywe dane (PII) do środowiska nieprodukcyjnego. „Kompletna samodzielna kopia" bije „prod, ale z paroma rzeczami wspólnymi".
- **Deterministyczny schemat nazw/portów — wyprowadzany z nazwy środowiska** — port, nazwa procesu, katalog, subdomena, nazwa kontenera powstają mechanicznie z nazwy środowiska (`app` / `app-staging` / `app-demo`, porty `3000/3001/3002`, itd.). Wtedy postawienie N-tej instancji to podstawienie wartości do schematu, nie projektowanie od zera. Eliminuje klasę błędów „druga instancja nadpisała pierwszą".
- **Zaszyty na sztywno port/nazwa procesu = blokada wielu instancji** — jeden hardcodowany port albo nazwa procesu w skrypcie deployu i w celach cronów sprawia, że druga instancja zderza się z pierwszą (kolizja portu, procesu, kontenera). Sparametryzuj wszystkie wartości zależne od środowiska (env-derived) ZANIM postawisz drugą instancję — to prerekwzyt, nie „poprawimy później".
- **Środowiska nieprodukcyjne na danych syntetycznych, nie na zrzucie proda** — seed syntetyczny trzyma żywe PII wyłącznie na produkcji (RODO/prywatność). Test „czy migracja przejdzie" wystarcza na **strukturze** — realnego wolumenu potrzebuje dopiero test wydajności, którego zwykle na staging nie robisz. Zanonimizowany zrzut proda = niepotrzebny pipeline anonimizacji + ryzyko wycieku; odkładaj go aż pojawi się realna potrzeba testu na wolumenie.
- **SMTP w próżnię (sink) na nieprodukcyjnych** — instancja nieprodukcyjna z produkcyjnym SMTP zacznie **wysyłać realne maile z syntetycznych zdarzeń**: zaplanowane zadania (przypomnienia, alerty) odpalają się same i uderzą w prawdziwą skrzynkę. Mail sink / wyłączona wysyłka to twardy warunek postawienia takiego środowiska, nie opcja. Ta sama logika dotyczy każdego wychodzącego kanału (SMS, webhooki, płatności) — nieprodukcyjne środowisko celuje w atrapę.
- **Staging ma wartość tylko gdy jest wierną próbą wdrożenia** — musi używać tej samej ścieżki deployu i tej samej struktury konfiguracji co prod (parametryzowanej env). Staging, który deployuje się inaczej niż prod, nie dowodzi niczego o prodzie. Kolejność w CD: zmiana najpierw na staging, zielono → dopiero prod.
- **Nieprodukcyjne instancje nie potrzebują backupów** — dane są zbywalne (syntetyczne, resetowane). Backup/retencję konfiguruj tylko na produkcji; instancja demo bywa dodatkowo czyszczona cyklicznym resetem do stanu pokazowego.
- **Środowisko to nie tenant** — wiele środowisk (izolowane instancje tego samego produktu) to inny wymiar niż wielu najemców w jednej instancji (multi-tenancy). Nie mieszaj tych decyzji: adresowanie tenanta (subdomena vs ścieżka) jest ortogonalne do topologii środowisk.

---

<!-- Dodawaj nowe sekcje gdy pojawi się universalny wzorzec z projektu. -->
<!-- Nie dodawaj tu wzorców domenowych (konkretny framework, biblioteka, biznes). -->
