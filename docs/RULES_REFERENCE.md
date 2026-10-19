# Rules Reference

Extended details for rules in CLAUDE.md: incident descriptions, rationales,
procedures, and examples. Each section number matches its CLAUDE.md counterpart.

---

## § 1a. AI nie działa samo — incydent i kontekst

Zasada powstała po realnym zdarzeniu (2026-10-09): zewnętrzny dysk z jedynym egzemplarzem danych
przestał startować, a gdy w końcu ruszył, AI samo uruchomiło kopię ratunkową — samo uznało, co jest
ważne (zgadując po nazwach katalogów, źle), samo wybrało dysk systemowy jako cel, choć danych było
kilka razy więcej niż miejsca, i zameldowało po fakcie. User kazał kopię zatrzymać i cofnąć. Przyczyną
awarii okazały się trzy dyski zasilane z jednego przełącznika USB — AI miało tę hipotezę zapisaną, ale
nie zapytało, jak dysk jest podłączony. Nic nie zginęło poza zaufaniem, że AI pyta.

---

## § 2a. Rejestr wyjaśnień — rozwinięcie

**Instrukcja obsługi — pułapka etykiet z kodu:**
User patrzy na interfejs, AI czyta repo, i tylko AI może pomylić jedno z drugim. Etykieta wyczytana
z komponentu bywa inna niż ta wyświetlana (nagłówek sekcji podany jako nazwa zakładki, klucz
tłumaczenia zamiast przetłumaczonego tekstu, nazwa wariantu zamiast napisu na przycisku), a user nie
ma jak tego zweryfikować — więc zgaduje, co AI miało na myśli, i traci zaufanie do reszty instrukcji.

---

## § 2. Język — guard i szczegóły

**Guard językowy sprawdza znaki, nie język.** Pojedyncza litera diakrytyczna wywala build, choć zdanie jest po angielsku — najczęstszy zapalnik to **symbol waluty** (np. `600 zł` w angielskim opisie buga o płatnościach). Dlatego:

- kwoty w opisach PR pisz kodem waluty (`600 PLN`), nie symbolem lokalnym
- nazwy własne i etykiety UI w języku lokalnym → **tylko** w \`backtickach\` albo "podwójnym cudzysłowie"; te spany guard pomija
- **skanuj treść przed wysłaniem, nie po odbiciu przez CI**

---

## § 3. Commit workflow — procedury i wyjątki

### Reguła główna

**Branch strategy**: każda funkcjonalność / fix idzie na osobnym branchu, merge do main przez PR. Nigdy bezpośrednio na main.

Przed stworzeniem nowego brancha: `git pull origin main` — zawsze, bez wyjątków.

Format nazwy brancha: `feat/nazwa`, `fix/nazwa`, `docs/nazwa`.

AI proponuje nazwę brancha na początku sesji, zanim zacznie się implementacja.

Po każdym domkniętym kroku AI proponuje commit – nie czeka aż user zapyta. Commit obejmuje kod i dokumentację razem (jeden commit = domknięty krok).

Format (zawsze po angielsku):

```
type(scope): short description

- file-or-component: what changed and why
- file-or-component: what changed and why
- impact if non-obvious

[user-tested] [skip-sync]   ← flagi ZAWSZE w body, nigdy w subject
```

Dla małych zmian – sam subject, bez body. Dla dużych – body obowiązkowe.

**Flagi muszą być w body, nie w subject.** Release-please parsuje tylko subject, a nawiasy kwadratowe łamią parser.

**Protokół przed każdym commitem (obowiązkowy, bez wyjątków):**

1. `git status` → ustal co jest staged
2. Skomponuj wiadomość commita ZANIM uruchomisz `git commit` (subject ≤72 zn, body ≤100 zn/linia, flagi w body)
3. Dry-run guardów z tą wiadomością — jeden command, wszystkie guardy commit-msg naraz (komendy niżej)
4. Jeśli wszystkie `exit: 0` → jeden `git commit`, bez iteracji

**Zakaz**: `git commit` bez wcześniejszego dry-runu guardów.

Po commicie zamykającym branch AI proponuje PR (tytuł + summary + test plan). Po utworzeniu PR AI sugeruje merge i **nie przechodzi do kolejnego zadania** dopóki user nie potwierdzi merge'a. Merge należy wyłącznie do usera.

**Ekonomia PR/CI.** AI **batchuje** commity i proponuje **jeden PR per temat/sesja**. Push/PR proponuje gdy domknięta jest cała paczka albo user mówi wprost „wypychamy".

**Sprzątanie po merge'u (obowiązkowe).** Po merge: `git checkout main` → `git pull origin main` → usunięcie brancha lokalnie (`-d`) i zdalnie. Kolejne zadanie startuje z czystego maina.

### Dry-run guardów — komendy

```bash
# Windows (PowerShell) — [IO.File] unika BOM który łamie gitlint:
[IO.File]::WriteAllText("$env:TEMP\COMMIT_EDITMSG", $msg)
python3 -m pre_commit run --hook-stage commit-msg --commit-msg-filename "$env:TEMP\COMMIT_EDITMSG"

# Linux/macOS:
echo "subject\n\nbody flags" > /tmp/COMMIT_EDITMSG
COMMIT_EDITMSG=/tmp/COMMIT_EDITMSG pre-commit run --hook-stage commit-msg --commit-msg-filename /tmp/COMMIT_EDITMSG
```

**Nie używaj ręcznej listy guardów** — lista w `.pre-commit-config.yaml` jest source of truth; ręczna
lista w CLAUDE.md będzie zawsze niepełna.

### Ekonomia PR/CI — uzasadnienie

GitHub Actions ma skończony budżet minut (zwłaszcza plan Free + repo prywatne), a każdy push i PR
odpala pełne CI. Commit lokalny jest darmowy — kosztuje dopiero push + PR + CI.

### Wyjątek squash-merge

Repo squashujące PR-y tworzy w main **jeden nowy commit**, więc `git branch -d` odmówi **nawet
w pełni zmergowanego** brancha („not fully merged") — commity brancha nie są w historii main
dosłownie. W tym trybie `-d` nie zadziała jako sprzątanie. AI wtedy zbiera dowód merge: PR = `MERGED`
(`gh pr view <n> --json state`), remote brancha zniknął (auto-delete) i dociągnięty main zawiera
zmianę — **pokazuje ten dowód i proponuje `git branch -D`, ale samego force-delete nie wykonuje bez
zgody usera** (to nieodwracalna komenda, więc zostaje bramkowana potwierdzeniem, inaczej niż
bezpieczne `-d`). Bez kompletu dowodu merge — nie kasujemy w ogóle (`-d` i STOP).

---

## § 3c. Równoległe sesje — szczegóły i uzasadnienia

### Dlaczego jeden katalog to problem

Kilka sesji AI pracujących w **tym samym katalogu** dzieli jeden indeks Gita i jeden HEAD. To nie jest
niewygoda — to cicha utrata pracy:

- **`git status` nie odróżnia cudzej pracy od własnej.** Sesja, która zastaje „brudny" katalog,
  domyślnie uzna te zmiany za swoje i może je w dobrej wierze zestashować, wycofać albo wciągnąć
  do commita. To ryzyko **poprzedza** wszystkie poniższe — występuje w pierwszej minucie sesji,
  zanim ktokolwiek cokolwiek zrobi z gitem
- **zwykły commit sąsiada** sprząta pliki z Twojego `git status` między dwiema Twoimi komendami —
  bez `checkout` i bez `add -A`
- **jeden katalog = jeden HEAD.** `git checkout` w jednej sesji zabiera z katalogu
  **zacommitowaną** pracę drugiej — jej pliki siedzą na branchu, którego już tam nie ma.
  Wygląda to jak utrata pracy i kosztuje pół godziny diagnozy, mimo że nic nie zginęło.
  To najczęstszy objaw, nie `add -A`
- `git add -A` w jednej sesji **wciąga niezacommitowane pliki drugiej** do commita o zupełnie innym
  temacie — i nikt tego nie zauważa, bo commit przechodzi guardy i wygląda poprawnie
- `git stash`, `git reset` i `git restore` działają na cudzą pracę

Incydent: druga sesja przełączyła branch w trakcie pracy pierwszej, a `git add -A` o kilka minut
minęło się z pojawieniem się cudzych plików. Nic nie zginęło wyłącznie dzięki kolejności zdarzeń —
nie dzięki jakiemukolwiek zabezpieczeniu.

### Docker compose — dlaczego „inny port" nie działa

`PORT=3001 docker compose up -d` w tym samym projekcie compose nie tworzy drugiego kontenera, tylko
przestawia istniejący — czyli zabiera port pierwszej sesji. Prawdziwie osobne środowisko wymaga
osobnej nazwy projektu (`-p`), a to oznacza **osobny wolumen bazy**: pustą bazę do zaseedowania
i rozjazd treści między sesjami. Przy pracy na treści CMS to gorsze niż problem, który rozwiązujemy.

### `temp/` w `.gitignore`

> ⚠️ **Zanim użyjesz kanału, sprawdź, że `temp/` jest ignorowany:** `git check-ignore -v temp/x.md`.
> Jeśli nie jest — **najpierw dopisz `temp/` do `.gitignore`**. Nieignorowana notatka ląduje
> w `git status` sąsiada jako nieśledzony plik, czyli robi dokładnie to, przed czym ta reguła
> ostrzega: podrzuca mu cudzą zmianę, którą w dobrej wierze wciągnie do commita albo sprzątnie.
> Sprawdzone 17.08.2026: z dziewięciu repozytoriów **pięć nie miało tego wpisu**, łącznie z tym.

### Sygnały współdzielenia katalogu

Jak AI rozpoznaje, że dzieli drzewo z kimś innym (sygnały, nie domysły):

- `git branch --show-current` pokazuje branch, którego ta sesja nie tworzyła
- narzędzie zgłasza „file has been modified since read" dla pliku, którego sesja nie ruszała
- w `git status` są zmiany, których sesja nie wprowadziła
- procesy: `Get-CimInstance Win32_Process | ? { $_.Name -match 'claude' }` (ile sesji żyje) oraz
  `ls -t ~/.claude/projects/<projekt>/*.jsonl | head` (który transkrypt ruszał się przed chwilą).
  Uwaga: znaczniki czasu w transkryptach są w UTC, a `mtime` plików w czasie lokalnym — łatwo
  pomylić się o różnicę stref

### Commit a serwer dev

**Commit to też zmiana katalogu — nie w trakcie testu usera.** Instancja dev działa z tego samego
katalogu co repo, a hooki commitu (np. pre-commit) na chwilę **chowają i przywracają** niezacommitowane
pliki. Serwer z przeładowaniem na gorąco widzi to jako edycję: przebudowuje się w połowie testu, raz
na starym kodzie, raz na nowym, i odświeża otwarte karty. User widzi „zawieszone logowanie" albo
losowy błąd, którego w kodzie nie ma — a diagnoza schodzi na zły tor.

- zgłoszenie błędu w trakcie commitu AI → najpierw sprawdź log serwera pod kątem przebudowy
  („Compiled") w tej samej minucie, zanim zaczniesz szukać buga w kodzie

---

## § 3d. Środowisko uruchomieniowe — szczegóły

### Dlaczego rozdzielenie jest konieczne

To nie jest kwestia wygody, tylko poprawności: **dwie instancje tego samego serwera dzielące jeden
katalog budowania nadpisują sobie artefakty** (manifesty tras, cache kompilacji). Objaw bywa mylący —
np. **404 na stronie, która istnieje**, przy poprawnym kodzie, danych i uprawnieniach — i kieruje
diagnozę na zupełnie inny tor. Rozdzielenie katalogów usuwa przyczynę, nie objaw.

Incydent: AI kilkukrotnie ubiło serwer usera i przejęło jego port, a współdzielony katalog budowania
wygenerował serię 404, które kosztowały pół sesji diagnozy „buga", którego nie było.

### Hook guard-process-kill — szczegóły

Hook bez flagi pominięcia `.claude/hooks/guard-process-kill.py` (PreToolUse na `Bash|PowerShell`):
blokuje kill po nazwie, kill po porcie usera (`dev_user_ports` w `.claude/hooks/config.json`,
domyślnie `[3000]`) i kill z nierozwiązanym celem (podstawienie, `xargs`); przepuszcza kill po
numerze PID, po pliku `.pid` i po porcie innym niż usera. Treść w heredocach i cudzysłowach (commit
message, edycja dokumentacji) hook ignoruje — liczy się samo polecenie. Gdy serwer usera naprawdę
musi stanąć — komendę odpala user.

### Adres bazowy — pułapka

**Osobny port to nie tylko `PORT`.** Konfiguracja projektu zwykle trzyma **adres bazowy aplikacji**
przypięty do portu domyślnego — biblioteki auth, adresy powrotne (callback/redirect), webhooki,
adresy w mailach. Instancja AI startuje na własnym porcie, ale te zmienne nadal wskazują port usera,
więc adresy, które aplikacja **generuje**, prowadzą do cudzego serwera. Dlatego plik ze środowiskiem
instancji AI nadpisuje **każdą zmienną przypiętą do domyślnego portu**, nie tylko sam port.

### Mylna atrybucja 404

**Czego to nie tłumaczy — i skąd ta korekta.** Kuszące jest przypisać adresowi bazowemu każdy objaw
sieciowy, w szczególności **404 na trasie, która istnieje**. Ten objaw ma zwykle inną przyczynę:
rozjechany katalog budowania, leczony jego skasowaniem i restartem. W realnym przypadku 404 na całej
obsłudze logowania został przypisany zmiennej z adresem — bo **naprawiono dwie rzeczy naraz**,
nadpisanie zmiennej i wyczyszczenie katalogu, i nie rozdzielono, która pomogła. Ten sam objaw wrócił
tego samego dnia na instancji usera, gdzie adres bazowy był poprawny.

Stąd zasada ogólniejsza niż sam port: **przy diagnozie zmieniaj jedną rzecz na raz**, a jeśli się nie
da — **nie zapisuj przyczyny w regułach, dopóki jej nie rozdzielisz**. Błędna przyczyna w regułach
jest gorsza niż jej brak: kolejna sesja ufa opisowi, przestawia zmienną i szuka dalej, zamiast
sięgnąć po naprawę, która zajmuje dziesięć sekund.

---

## § 4. Aktualizacja dokumentacji — uzasadnienia

### Dziennik wdrożeń — dlaczego

Agent, który co tydzień pisze raport albo przegląd, zwykle nie ma pamięci między uruchomieniami:
czyta repozytorium i tyle. Bez zapisu, co z jego rekomendacji zostało wdrożone, każdy cykl zaczyna
od zera — nie rozlicza efektu poprzedniej rady, tylko wymyśla następną. Po kilku tygodniach zostaje
lista pobożnych życzeń zamiast doradztwa.

Zasada jest ogólniejsza niż jeden raport: **każdy odbiorca bez pamięci potrzebuje kanału w repo**
— cudzy agent, sesja w chmurze, nowy człowiek w projekcie. Kanałem nie może być czat ani system
zadań, do którego ten odbiorca nie ma dostępu.

### Język dwóch warstw — przykład

```
**Krok 2 — filtry w liście zamówień:**

> Po ludzku: dziś żeby znaleźć zamówienie trzeba przewijać całą listę.
> Po tej zmianie można filtrować po statusie i dacie — wyniki od razu się zawężają.

- [ ] Dodaj parametry query do endpointu...
- [ ] Update widoku listy...
```

Zasada: jeśli user po tygodniu nie rozumie co miał na myśli — opis jest zły. Pisz tak żeby rozumiał
właściciel firmy, nie programista.

---

## § 4a. Dokumentacja użytkownika — szczegóły warstw

### Trzy warstwy szczegółowo

1. **Mapa katalog → dokument** w jednym pliku konfiguracyjnym: każdy temat pomocy ma listę ścieżek kodu,
   które kształtują opisywane ekrany. Test pilnuje, że każda ścieżka istnieje i że każdy obszar aplikacji jest
   albo w temacie, albo na jawnej liście „bez dokumentu". Mapa, której nikt nie testuje, zaślepia strażnika.
2. **Sygnał przy edycji** — hook po zapisie pliku z mapy dopisuje do kontekstu AI: „ten plik opisuje temat X,
   dokument Y wymaga aktualizacji". Sygnał w kroku, w którym zmienia się kod; nie przy commicie.
3. **Guard commitu bez flagi pominięcia** — commit dotykający ścieżek tematu musi zawierać dokument ze
   stemplem „stan na dzień" równym dacie commita. Odświeżenie daty to podpis autora „przeczytałem opis
   względem tej zmiany"; refaktor też podbija datę. Nie ma `[skip-help]` — każda furtka z czasem staje się
   domyślną ścieżką. Temat bez dokumentu daje ostrzeżenie, nie blokadę, żeby nie zamrozić rozwoju obszaru.

### Incydent

Ręcznie pisana mapa ustawień przez trzy miesiące nie nadążała za ekranem, a wyszło to dopiero przy
przeglądzie pomocy, nie przy żadnej z ~60 zmian, które ją zdezaktualizowały.

---

## § 5a. Podgląd = ta sama funkcja — incydent

Podgląd umowy i jej PDF miały osobne kopie reguł wypełniania, które zdążyły się rozjechać (inny
przedstawiciel, inne dane w załącznikach, puste pole drukowane w PDF jako ramka formularza), a jedna
z trzech kopii nie była już nigdzie wywoływana.

---

## § 6. Rekomendacje — priorytety

Kolejność priorytetów przy rekomendacji technicznej (obowiązkowa):

1. kryterium akceptacji / cel produktu
2. ryzyko przepisywania i krótkiego życia rozwiązania
3. koszt utrzymania i złożoność operacyjna
4. dopiero na końcu optymalizacje typu mniej zależności / mniejszy bundle

AI nie może proponować rozwiązania "na chwilę", jeśli jest wysoka szansa, że będzie zaraz wyrzucone
i zastąpione.

---

## § 13a. AI repo template — rozwinięcia

### Szkielet ≠ dokument roboczy

Szablon też jest projektem i prowadzi własny log sesji oraz własne scenariusze — ale pod nazwą, którą
nowy projekt ma dostać pustą, może leżeć wyłącznie szkielet albo plik podmieniany przy starcie
projektu. Własne materiały szablonu idą do plików tylko-szablonowych (`docs/TEMPLATE_TESTING.md`,
`docs/adr/`) albo do `docs/TASKS.md`, który start projektu zeruje. Sprawdzian przy każdej zmianie
w `docs/`: uruchom start projektu na kopii i przeczytaj, co w niej zostało.

### Guard tylko z testem — uzasadnienie

Guard bez testu bywa fail-open (cicho przepuszcza to co miał łapać) albo martwy (nigdy się nie
odpala) — w obu przypadkach daje fałszywe poczucie ochrony, gorsze niż brak guarda.

### Rozdzielaj sesje system vs projekt — uzasadnienie

Praca nad template'm / guardami / zasadami (system) i praca nad produktem (projekt) to dwa różne
poziomy — mieszanie ich w jednej sesji rozjeżdża scope. Jedna sesja trzyma jeden poziom. Lekcja,
która wyjdzie przy pracy nad projektem a dotyczy systemu, ląduje w systemie (guard z testem lub
dokument), nie zostaje w sesji projektowej. AI sygnalizuje gdy sesja zaczyna mieszać poziomy.

### Pamięć maszynowa

Pamięć maszynowa (`~/.claude/...`) = supplement do CLAUDE.md, nie zamiennik.

---

## § 13b. Pluginy — tabela dostępnych

| Plugin | Instalacja | Trigger |
|--------|-----------|---------|
| **figma** | `claude plugin install figma@claude-plugins-official` | user wspomina Figma, design handoff, Code Connect, `use_figma`, tokeny z Figmy, generowanie kodu z framek |

Kiedy NIE podpowiadać: gdy user już ma plugin zainstalowany, gdy wyraźnie nie używa danego narzędzia,
gdy podpowiedź była już w tej sesji.

Katalog pluginów: `docs/SKILLS.md` → sekcja *Plugins*.

---

## § 14a. Produkcja — uzasadnienie

AI z dostępem do produkcji potrafi zdiagnozować buga na żywych danych w kilkanaście sekund — to jest
realna wartość i dlatego pokusa jest duża. Ale prod to jedno środowisko z realnymi ludźmi w środku,
bez „ctrl+z". Koszt jednego pytania jest zawsze niższy niż koszt jednego `DELETE` bez `WHERE`.

---

## § 14b. Baza dev — incydent

Zasada powstała po realnym zdarzeniu (2026-09-07): AI dosypało kilka testowych rekordów do bazy dev,
żeby w ogóle dało się odtworzyć zgłoszony objaw, i zameldowało to dopiero w podsumowaniu. Nic nie
zginęło, ale user dowiedział się o zmianie po fakcie — a to jest dokładnie ta kolejność, której 14a
zabrania na produkcji i której nie ma powodu tolerować na dev.

---

## § 15. Wydajność — rozwinięcia

### RWD — dlaczego mierzyć zanim napiszesz „zrobione"

Zanim oznaczysz responsywność jako sprawdzoną — w kodzie, w checklistcie testów (`docs/TESTING.md`),
czy w raporcie do usera — uruchom **pomiar responsywności** (audyt RWD przy docelowej szerokości),
nie polegaj na oglądaniu screenów ani na założeniu „reużyłem istniejący styl, pewnie gra". Dopisanie
do checklisty punktu „RWD @<szerokość> ok" bez pomiaru to deklaracja bez pokrycia — pomiar idzie
**przed** deklaracją, nie po niej. Ten sam wzorzec co reguła 16b: nie ogłaszaj zweryfikowanego bez
weryfikacji.

### Silnik audytu — historia i lekcja

Silnik mieszka **poza repo** — w skillu `audyt` (`~/.claude/skills/audyt/cli.mjs`, podpinany przez
`claude-setup/install.sh`); w projekcie trzymamy wyłącznie profil `audyt.config.mjs` i dwa wpisy
w `package.json`. **Nie kopiuj silnika do repo projektu** — właśnie z tego wzięły się cztery
rozjechane wersje, z których trzy były ślepe na kontrast i na paski przyklejone do krawędzi.

### Złota zasada — pełne sformułowanie

Mierz zanim optymalizujesz; bez danych = bez optymalizacji kosztem czytelności. Przy każdej
optymalizacji lub refaktorze: uszereguj możliwe ruchy wg ROI, wykonaj **najtańsze i najbezpieczniejsze
najpierw**, zmierz efekt na realnych danych, dopiero potem decyduj o ruchu ryzykownym lub kosztownym —
albo odłóż go z uzasadnieniem. Nie forsuj ryzykownego/zablokowanego kroku dla maksymalnego zysku;
często dwa tanie ruchy dają większość korzyści bez długu. Diagnozuj z dowodów, nie z teorii — przy
problemie zbierz dane (logi, runy, pomiary) zanim postawisz hipotezę.

---

## § 16a. Domknięcie modułu — rozwinięcia

### Mocki vs realny przebieg

Nowa ścieżka zapisu/odczytu do bazy → jeden realny przebieg na dev przed „gotowe", nie tylko zielone
testy na mockach. Mock ukrywa błędy warstwy DB (deserializacja typów, ograniczenia unikalności,
wartości enum, raw SQL). Zielony mock = logika OK; realny przebieg = baza faktycznie przyjmuje zapis.
Pominięcie tego = zrzucenie wykrycia błędu na usera w runtime (AI jest jedynym autorem kodu — nie ma
reviewera, więc to AI łapie błąd przed userem, nie po nim).

---

## § 16b. Module closure protocol — uzasadnienie

Kompensuje obserwowany pattern "AI pisze kod → proponuje commit → user nigdy nie zdążył przetestować
→ błąd w produkcji". Hard stop po kroku 4 daje userowi czas na sparingowanie z gotowym artefaktem
zanim wpadnie do historii.

---

## § 17a. Zamykaj wątki — przykłady

**Kiedy odkładanie jest ok:**
- feature wyraźnie wykracza poza scope bieżącej sesji/brancha
- user sam decyduje "odkładamy"
- zadanie zależy od czegoś co jeszcze nie istnieje

**Kiedy nie jest ok:**
- AI widzi małe powiązane zadanie i "żeby nie przedłużać" milczy lub proponuje "zrobimy później"
- user pyta o dynamiczne dane, AI odpowiada "logo można dodać w kolejnym kroku"
- sesja ma otwarty branch z powiązanym kodem i AI nie zaproponuje domknięcia

---

## § 19. Nowy komponent UI — przykłady grep

```bash
grep -r "cursor-pointer" src/app --include="*.tsx" -l   # jak projekt robi cursor
grep -r "Tooltip" src/ --include="*.tsx" -l              # czy tooltip jest już używany
grep -r "title=" src/app --include="*.tsx" | head -5     # czy jest natywny title
```

---

## § 19a. Każda zmiana wizualna = audyt — szczegóły i incydent

### Rozwinięte punkty operacyjne

- audyt na **własnej instancji AI** (reguła 3d), na danych, na których element naprawdę się pojawia
  (np. dokument z kwotą, okienko otwarte kliknięciem); trasy zależne od konkretnych rekordów → profil
  tymczasowy w katalogu roboczym sesji, bez zmian w `audyt.config.mjs` projektu
- telefon i ciemny motyw (jeśli projekt go ma) zawsze; przy okienkach i długich formularzach także
  **niski ekran (~640 px)** — typowa wysokość profilu nie pokaże okna uciętego u góry i u dołu
- w raporcie AI rozdziela: **co wprowadziła ta zmiana** (naprawia od razu) i **co było wcześniej**
  (mówi wprost, nie naprawia po cichu, dług trafia do issue)
- usterkę widoczną na zrzucie usera, której audyt nie złapał, AI zgłasza jako **lukę silnika** (nowy
  detektor ze stroną-atrapą w samoteście), zamiast poprzestać na poprawce w projekcie

### Incydent

AI dołożyło kolorowe ramki, przełącznik z ostrzeżeniem i ramkę podsumowania w okienku wysyłki — bez
audytu. User dopiero zrzutem z telefonu pokazał okienko ucięte z obu stron (wspólny komponent okna
bez limitu wysokości, więc problem dotyczył każdego długiego okna w aplikacji), a audyt zlecony po
fakcie znalazł jeszcze kontrast 2,3:1 na nowym przycisku i zlewające się ramki. Każda z tych usterek
była do złapania jednym przebiegiem przed oddaniem.

---

## § ADR. Weryfikacja założeń — rozwinięcie

ADR często opiera decyzję na założeniu. Trzeba rozróżnić dwa typy, bo pomylenie ich kładzie cały ADR:

1. **Założenie o obecnym zachowaniu systemu** ("system robi X", "alokacja dzieje się przy zapisie",
   "ten endpoint zawsze waliduje Y") — AI **musi zweryfikować w kodzie i podać `file:line`** że to
   faktycznie egzekwowane. Jeśli kod tego nie pilnuje: albo guard w tym samym kroku, albo **jawne
   oznaczenie w ADR jako „założenie nieegzekwowane = ryzyko"**. Zapisanie zachowania kodu jako faktu
   bez weryfikacji to błąd — założenie którego kod nie gwarantuje to nie fundament, to nadzieja
   zapisana w dokumencie.
2. **Założenie o przyszłym zachowaniu człowieka / biznesu** ("owner rozliczy przed zamknięciem",
   "porzucenia z długiem są rzadkie") — tego nie da się zweryfikować kodem, więc legalnie odkłada się
   z logiem (reguła 17).

Failure mode do unikania: potraktowanie typu 1 jak typu 2 — odpuszczenie weryfikacji kodowej tam
gdzie była obowiązkowa. Skutek: decyzja produktowa stoi na zachowaniu, którego implementacja nie
wymusza, a bug wypływa dopiero gdy ktoś trafi na ścieżkę łamiącą założenie.

---

## § 4. Aktualizacja dokumentacji — reguła główna

Po każdym domkniętym kroku AI proponuje aktualizację dokumentacji — nie czeka aż user zapyta.

Co aktualizować:

- **issue zadania** – odhaczyć domknięty krok; praca spoza scope → nowe issue
- **docs/TASKS.md** – log sesji: co się wydarzyło i dlaczego
- **docs/SETUP.md** – nowe komendy, pułapki, "done when"
- **docs/ROADMAP.md** – ukończona faza, zmiana zakresu
- **docs/CONVENTIONS.md** – nowa konwencja kodu
- **docs/UI_GUIDELINES.md** – nowy wzorzec UI, komponent, stan
- **docs/adr/** – nowa decyzja architektoniczna
- **docs/TESTING.md** – nowy krytyczny flow
- **docs/DELIVERY_CHECKLIST.md** – zmiana standardu domykania
- **dziennik wdrożeń** – zmiana z obszaru cyklicznego agenta doradczego

Kolejność: kod + dokumentacja razem w jednym commicie na końcu kroku.

**Język dokumentacji — zasada dwóch warstw:**

1. **Warstwa ludzka** — potocznie, co user zobaczy / czym grozi brak. **Zwięzła**.
2. **Warstwa techniczna** — pliki, funkcje, `file:line`, root-cause. **Kompletna maszynowo**.

Po każdym kroku AI proponuje też **checklistę testów manualnych** (happy path + edge case'y).

**Weryfikacja mechaniczna przed edycją dokumentacji** (obowiązkowe):

- Nowy plik w `docs/` → nazwa wg konwencji, wpis do README.md, link z domu
- Przed zmianą **README.md** → `ls docs/` i zestawienie z tabelą
- Przed zmianą **docs/ROADMAP.md** → porównaj statusy faz ze stanem issues
- Przed zmianą **docs/TASKS.md** → dopisz do "Stan sesji" co ukończono

---

## § 10. Kontekst projektu — co i kiedy sprawdzać

Na początku sesji AI czyta selektywnie — na podstawie tematu:

- **CLAUDE.md** → zawsze
- **docs/TASKS.md** → zawsze (log sesji)
- **otwarte issues** (`gh issue list`) → zawsze
- **docs/AI_TEMPLATE_NOTES.md** → zawsze
- **docs/PROJECT_SCOPE.md** → gdy dotyczy zakresu/nowej funkcjonalności
- **docs/ROADMAP.md** → gdy dotyczy planowania
- **docs/adr/** → gdy dotyczy architektury
- **docs/CONVENTIONS.md** → gdy dotyczy kodu
- **docs/UI_GUIDELINES.md** → gdy dotyczy UI
- **docs/** → sprawdź co istnieje — lista rośnie
- **docs/SETUP.md** → gdy dotyczy środowiska
- **docs/TESTING.md** → gdy dotyczy testowania
- **docs/GUARDS.md** → gdy dotyczy strażników/hooków/startu
- **docs/examples/** → przed napisaniem SETUP, TASKS, ROADMAP lub ADR

---

## § 18. Review designu przed implementacją UI

Przed napisaniem kodu nowego ekranu/flow UI, AI opisuje proponowany flow i czeka na akceptację.

Dotyczy nowych ekranów. Nie dotyczy drobnych zmian (nowa kolumna, nowe pole).

Format: Flow → skąd wchodzi → co widzi → co robi → efekt → pytanie.

---

## § 19. Przed nowym komponentem UI — reguła główna

Przed napisaniem nowego komponentu UI:

1. **Sprawdź `src/components/ui/`** — jeśli komponent istnieje, użyj go
2. **Grep po wzorcu w kodzie** — znajdź istniejące użycie i naśladuj

**Twarde zasady:**
- `title=""` → nigdy; zawsze `<Tooltip>` z design systemu
- `cursor-pointer` → zawsze na klikalnych elementach
- Nowy pakiet npm → najpierw sprawdź bibliotekę komponentów w projekcie

---

## § 20. Rozmiar komponentów i plików logiki

**Komponent UI: max 300 linii.** Powyżej — wyciągnij sub-komponenty, hooki, helpery.

**Plik logiki: max 400 linii.** Powyżej — podziel po domenie lub flow.

**Wyjątek:** pliki danych (stałe, szablony, mapowania) — bez limitu.

Przed dużym komponentem — zaplanuj podział z góry. Istniejące pliki ponad limit — AI sygnalizuje dług.

---

## § ADR. Architecture Decision Records — pełne zasady

AI wykrywa momenty decyzji architektonicznych i proponuje ADR. Numeruje sekwencyjnie: ADR-001, ADR-002...

### Kiedy pisać ADR

ADR dokumentuje **każdą decyzję której uzasadnienie nie jest oczywiste z kodu** — techniczną, architektoniczną i biznesową. Jeśli pojawia się wybór modelu/technologii, zmiana flow/API, decyzja o bezpieczeństwie, coś trudnego do odwrócenia, decyzja biznesowa, nieoczywisty wniosek z sesji → ADR.

**Zasada:** jeśli AI musi wyjaśniać "dlaczego tak zrobiliśmy" — brakowało ADR-a.

### Backfill starych decyzji

Pytanie "dlaczego X działa tak" bez ADR → AI **natychmiast proponuje ADR**.

### Kiedy NIE pisać ADR

- konwencje kodu → docs/CONVENTIONS.md
- małe decyzje → komentarz lub log sesji
- rzeczy łatwo odwracalne bez migracji

### Struktura ADR

Tytuł, Status (proposed/accepted/deprecated), Kontekst, Decyzje i uzasadnienia, Konsekwencje.

---

## § Roadmap

AI proponuje roadmapę jeśli nie istnieje, flaguje pracę poza kolejnością, aktualizuje docs/ROADMAP.md.

Trigger: brak roadmapy, zmiana scope, ukończona faza, nowe wymagania.

Struktura: Faza N — cel, zakres, done when, zależności.

---

## § SETUP.md

Obowiązkowy w każdym projekcie. Zawiera: wymagania z wersjami, kroki instalacji, pułapki, "done when". AI aktualizuje natychmiast przy nowym problemie środowiskowym.

---

## § Artefakty projektu

### Główne artefakty

docs/PROJECT_SCOPE.md, CLAUDE.md, docs/adr/, docs/CONVENTIONS.md, docs/UI_GUIDELINES.md, docs/ROADMAP.md, GitHub Issues, docs/TASKS.md, docs/SETUP.md, docs/TESTING.md, docs/GUARDS.md, docs/GUARDS_TESTING.md, docs/examples/, docs/DELIVERY_CHECKLIST.md, dziennik wdrożeń, README.md.

### Rola AI

- wykrywa brakujące elementy i proponuje ich utworzenie
- tworzy artefakty tylko gdy potrzebne, aktualizuje zamiast duplikować
- wykrywa niespójności między artefaktami i sygnalizuje wprost
- preferencja/feedback → proponuje zapis do CLAUDE.md
- **zanim napisze SETUP, TASKS, ROADMAP lub ADR — czyta wzór w `docs/examples/`**

### Kolejność tworzenia

1. docs/PROJECT_SCOPE.md → 2. ADR-001 → 3. docs/ROADMAP.md → 4. kolejne ADR → 5. issues + docs/TASKS.md → 6. docs/CONVENTIONS.md → 7. docs/SETUP.md → 8. README.md

---

## § Start projektu

Brakuje artefaktów → AI proponuje: 1. docs/PROJECT_SCOPE.md, 2. ADR-001, 3. docs/ROADMAP.md (v0).

AI nie przechodzi do implementacji bez PROJECT_SCOPE i ADR-001.

Gotowość: PROJECT_SCOPE zaakceptowany, ADR-001, ROADMAP z aktualną fazą, issues bieżącej fazy.

---

## § Zasada nadrzędna

```
CLAUDE.md        = jak pracujemy
docs/PROJECT_SCOPE.md = co budujemy
ADR              = dlaczego tak, a nie inaczej
```

AI musi rozróżniać wszystkie trzy poziomy — nie mylić zasad pracy z logiką biznesową, ani logiki z uzasadnieniem decyzji architektonicznych.
