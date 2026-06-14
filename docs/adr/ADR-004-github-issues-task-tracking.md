# ADR-004 — Śledzenie zadań i roadmapy w GitHub Issues/Projects zamiast markdown w repo

**Status:** accepted (wykonanie odłożone — patrz „Konsekwencje / Timing")
**Data:** 2026-06-11

## Korekta 2026-06-14 — wynik pilotażu: board zdegradowany do opcjonalnego

Pierwszy pilotaż wykonania tej decyzji w realnym projekcie (model 1 właściciel + AI)
podważył **§2 w części dotyczącej boardu jako widoku statusu**:

- Kanban (kolumny Pomysł / Do zrobienia / W toku) ma sens, gdy zespół koordynuje
  kto-co-trzyma. W modelu 1 właściciel + AI nikt na tablicę nie patrzy — sygnał startu
  zadania to sesja, sygnał końca to merge PR-a.
- Oczekiwany „automatyczny postęp na tablicy" **nie istnieje out-of-the-box**: kolumna
  statusu nie przesuwa się sama z brancha/PR-a. Dobudowa takiego automatu dla projektu
  jednoosobowego = przerost (reguła 5/17), niewarte.
- Faktyczną potrzebę właściciela („wejść, zobaczyć czy projekt jest na czas") pokrywa
  **strona Milestones**: faza + termin + pasek postępu (% zamkniętych issues), wypełniany
  automatycznie merge'em PR-ów. Board dat w ogóle nie pokazuje — stąd częsta pomyłka
  „dashboard nic nie daje" (patrzenie na zły ekran).

**Zmiana:**

- **Widok statusu = strona Milestones**, nie board. Board Projects staje się *opcjonalny*
  (kto chce kanban — proszę bardzo), przestaje być wymaganym elementem wzorca i źródłem
  oglądu dla właściciela.
- §4: oś czasu faz opiera się na **milestones** (termin + auto-postęp), nie na widoku
  „Roadmap" tablicy Projects.
- **Kolumna „Up next"** (uporządkowana kolejność wykonania — lek na dryf rekomendacji,
  §2 / wada 3) **zostaje**, ale jako mechanizm **niezweryfikowany pilotażem**: wymaga
  własnego sprawdzenia w kolejnym projekcie zanim uznamy ją za udowodnioną. Kolejność
  wykonania ≠ dashboard statusu — to osobny argument, którego ten pilotaż nie testował.
- Ewentualny generowany `STATUS.md` (skrypt ciągnie dane z `gh` → jedna strona ze zbiorczym
  „semaforem on-track") to kandydat na przyszłość **tylko jeśli** milestones okażą się
  niewystarczające — nie buduje się go na zapas.

Reszta decyzji (Issues = dane, `Closes #N` = stan z faktów, milestones = fazy, markdown
fallback) stoi bez zmian — pilotaż jej nie podważył.

---

## Kontekst

Wzorzec trzyma backlog i plan prac w plikach markdown w repo: `docs/TASKS.md`
(bieżące zadania, dwie warstwy opisu — ludzka + `↳ tech:`) i `docs/ROADMAP.md`
(fazy). Pilnują ich guardy pre-commit (`docs/TASKS.md` musi być w commicie przy
zmianach, statusy faz spójne z zadaniami).

Założeniem było: jeden plik, czytelny dla właściciela, wersjonowany z kodem,
darmowy do czytania dla AI w kontekście sesji. W praktyce, gdy projekt rośnie,
ten model degraduje się w sposób, który uderza w jego własny cel:

1. **Płaski plik nie skaluje się jako widok.** Po ~30 zadaniach `TASKS.md` to
   ściana kilkuset linii. Brak sortowania, filtra po priorytecie, kolumn statusu.
   Właściciel — dla którego ten plik miał być czytelny — nie potrafi z niego
   jednym rzutem oka odpowiedzieć „co jest w MVP, co poza, jaka ważność". Priorytet
   (np. emoji 🔴🟡🟢) jest zatopiony w prozie, nie jest polem po którym da się
   filtrować.

2. **Markdown nie trzyma stanu — wymaga ręcznej higieny.** „Zrobione" usuwa się
   ręcznie z pliku. To znaczy, że poprawność listy zależy od tego, czy ktoś (AI lub
   człowiek) pamiętał wykreślić linię. Obserwowany efekt: porządkujemy plik, a po
   kilku sesjach znów jest rozjechany. Stan listy nie wynika z faktów systemu, tylko
   z dyscypliny edycji.

3. **Brak jednej kolejności rodzi dryf rekomendacji.** Gdy wiele zadań ma ten sam
   priorytet i żadnej kolejności między sobą, pytanie „co następne" jest obiektywnie
   niejednoznaczne. AI streszczające taką listę z sesji na sesję daje różne
   odpowiedzi — każda „poprawna", żadna stabilna. Co gorsza, AI bywa skłonne
   streszczać listę z pamięci zamiast czytać priorytety mechanicznie, przez co gubi
   pojedyncze zadania. Człowiek, widząc że nawet AI się gubi, traci zaufanie do listy.

4. **Sztuczny rozdział od miejsca pracy.** PR-y, kod, review i CI żyją na GitHub.
   Taski w osobnym pliku markdown to drugi, niespięty rejestr. Zadanie i PR który je
   realizuje nie są powiązane — zamknięcie zadania to osobna, ręczna czynność.

Wspólny korzeń wad 1–3: markdown to **format danych**, użyty jako **narzędzie
zarządzania**. Daje wersjonowanie i dwie warstwy opisu, ale nie daje widoku,
wymuszonego stanu ani uporządkowania — a to one decydują o kontroli właściciela i
o tym, czy AI nie dryfuje.

---

## Decyzje i uzasadnienia

### 1. Zadania = GitHub Issues; priorytet i klasa pracy jako etykiety

Każde zadanie to issue. Priorytet (`P0`/`P1`/`P2` lub `🔴`/`🟡`/`🟢`) oraz klasa
(`MVP` / `post-MVP`) to **etykiety** — pola pierwszej klasy, po których filtruje się
i grupuje. Dwuwarstwowy opis zostaje: warstwa ludzka w treści issue na górze, warstwa
techniczna (`pliki`, `file:line`, root-cause, pułapki) w sekcji `## tech` niżej.
Spójność formatu pilnuje **Issue Template** (`.github/ISSUE_TEMPLATE/task.yml`).

**Dlaczego:** zachowuje to, co w markdown było dobre (dwie warstwy, opis czytelny dla
właściciela + kompletny maszynowo dla AI), a dokłada to, czego brakowało — priorytet i
klasa jako filtrowalne pola, nie emoji w prozie. Issue Template wymusza format bez
guarda na pliku.

### 2. Widok = GitHub Project (tablica); jedna uporządkowana kolumna „Up next"

> **Korekta 2026-06-14:** board jako widok *statusu* zdegradowany do opcjonalnego —
> widok statusu dla właściciela = strona **Milestones**. Kolumna „Up next" zostaje, lecz
> niezweryfikowana pilotażem. Patrz blok „Korekta" na górze ADR.

Tablica Projects jest **widokiem** (status jako kolumny: Pomysł / Do zrobienia / W toku,
grupowanie po priorytecie, filtry, drag&drop). Właściciel steruje nią kliknięciem —
nie edycją pliku. Obowiązkowo istnieje **jedna uporządkowana lista „Up next"**: ranking
zadań w kolejności wykonania. „Co następne" się **czyta z góry kolumny**, nie wymyśla.

**Dlaczego:** to wprost adresuje wadę 1 (widok, kontrola właściciela) i wadę 3 (dryf
rekomendacji — bo kolejność jest jawna i pojedyncza, nie domyślana). Podział „Issues =
dane, Project = widok" jest naturalny: AI i człowiek piszą do Issues, człowiek
kształtuje widok.

### 3. Stan wynika z faktów, nie z higieny: auto-zamykanie przez PR

PR linkuje się z issue przez `Closes #N`. Merge **sam** zamyka zadanie. Żadnego ręcznego
usuwania „zrobione". Powiązanie zadanie↔PR jest trwałe i widoczne.

**Dlaczego:** kasuje całą klasę „lista rozjechana, bo ktoś nie wykreślił linii" (wada 2).
Stan backlogu staje się pochodną gita, a nie pamięci edytora. Spina też wadę 4 — zadanie
i jego realizacja są jednym wątkiem.

### 4. Roadmapa = Milestones (widok „Roadmap" Projects opcjonalny)

> **Korekta 2026-06-14:** oś czasu faz opiera się na **milestones** (termin + auto-postęp).
> Widok „Roadmap" tablicy Projects jest opcjonalny, nie obowiązkowy.

Fazy roadmapy → **milestones** (zadanie należy do fazy przez przypisanie do milestone),
a oś czasu faz → strona Milestones (termin + % zamkniętych zadań). `docs/ROADMAP.md`
przestaje być źródłem prawdy o statusie faz.

**Dlaczego:** milestone daje to, czego markdownowa roadmapa nie dawała — automatyczny
postęp fazy (% zamkniętych zadań) i wymuszone powiązanie zadanie↔faza, zamiast ręcznie
utrzymywanej spójności pilnowanej guardem.

### 5. Los plików markdown i guardów

`docs/TASKS.md` i `docs/ROADMAP.md` zostają zredukowane do **cienkiego wskaźnika**
(jedno zdanie: „backlog żyje w GitHub Issues/Projects — link") albo usunięte. Guardy
przyspawane do `docs/TASKS.md` (obecność w commicie, spójność faz) zostają **usunięte
lub przepięte** — ich funkcja (wymuszenie aktualizacji backlogu przy zmianie) przechodzi
na konwencję `Closes #N` w PR.

**Dlaczego:** dwa źródła prawdy (plik + Issues) to gwarantowany rozjazd. Guard pilnujący
nieaktualnego nośnika to dług. Cienki wskaźnik zostaje tylko po to, by ktoś czytający repo
trafił do właściwego miejsca.

### 6. Markdown pozostaje fallbackiem dla projektów bez GitHub

Projekt nieoparty o GitHub (lub zbyt mały, by zakładać Project) zostaje przy
`docs/TASKS.md`. Wzorzec dostarcza **oba** scaffoldy: pliki markdown **oraz**
`.github/ISSUE_TEMPLATE/` + dokument konfiguracji Projects. `new-project.py` pyta którego
trybu użyć (lub wykrywa remote GitHub).

**Dlaczego:** decyzja jest słuszna gdy kod i PR-y już są na GitHub (wada 4 znika tylko
wtedy). Narzucanie Issues projektowi spoza GitHub dokładałoby integrację bez korzyści —
to byłby koszt pod wymaganie którego nie ma.

---

## Odrzucone alternatywy

| Opcja | Dlaczego odrzucona |
|-------|--------------------|
| Zostać przy markdown (status quo) | Zawodzi własny cel — nieczytelny dla właściciela po ~30 zadaniach, nie trzyma stanu, rozjeżdża się mimo porządkowania. Gdy format wielokrotnie nie spełnia głównego zadania, kosmetyka nie wystarcza. |
| Markdown + sama lepsza dyscyplina AI | Nie naprawia braku widoku ani uporządkowania — opiera całą poprawność na dyscyplinie AI, która obserwowalnie zawodzi (gubienie zadań, dryf). Narzędzie ma wymuszać, nie liczyć na pamięć. |
| Zewnętrzne narzędzie (Linear / Jira / Notion) | Kolejny system poza miejscem gdzie żyją kod i PR-y; brak natywnego `Closes #N`; dodatkowa integracja i koszt utrzymania. GitHub wygrywa, bo praca już tam jest. |
| Hybryda: markdown źródłem, Issues lustrem (lub odwrotnie) | Dwa źródła prawdy = gwarantowany rozjazd i podwójna higiena. Sprzeczne z „jedno źródło prawdy", które było celem. |

---

## Konsekwencje

**Ułatwia:**
- Właściciel odzyskuje widok i kontrolę: priorytet/klasa/status jako pola Issues i filtry —
  odpowiedź „co MVP / co poza" jednym filtrem; status faz na stronie **Milestones**
  (termin + auto-postęp). Board/drag&drop opcjonalne (patrz Korekta 2026-06-14).
- Stan backlogu wynika z faktów (merge zamyka issue), nie z ręcznej higieny — znika
  klasa „lista się rozjechała".
- Jedna kolumna „Up next" usuwa dryf rekomendacji — kolejność jest czytana, nie wymyślana.
- Zadanie i jego PR to jeden powiązany wątek; koniec sztucznego rozdziału backlog↔kod.

**Utrudnia / wymaga uwagi:**
- **Timing wykonania.** Decyzja jest `accepted`, ale migracja w trwającym projekcie to
  zmiana procesu — odkłada się ją na granicę bezpieczną dla projektu (np. po zamknięciu
  bieżącej fazy/MVP), nie wykonuje w środku krytycznej pracy. Sam ADR nie zmienia
  niczego w działającym repo do momentu migracji.
- **AI czyta backlog przez `gh` CLI**, nie darmowym odczytem pliku w kontekście — to
  realny koszt tokenów/tool-calli na sesję. Akceptowalny wobec zysku na poprawności i
  kontroli; do złagodzenia przez czytanie tylko widoku „Up next", nie całego backlogu.
- **Utrata dostępu offline** do listy zadań (markdown działał bez sieci).
- **Migracja treści** istniejących zadań → Issues (skryptowalne przez `gh issue create`).
- **Praca w guardach i scaffoldach wzorca:** Issue Template, dokument konfiguracji
  Projects, tryb wyboru w `new-project.py`, usunięcie/przepięcie guardów `TASKS.md`.
  Każdy nowy/zmieniony guard wchodzi z testem (blokuje gdy ma, przepuszcza resztę).
- **Dualizm w samym wzorcu:** wzorzec utrzymuje oba tryby (markdown fallback + Issues)
  — więcej powierzchni do utrzymania, świadomy koszt za uniwersalność.
