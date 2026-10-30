# AI Development Rules

Reguły szczegółowe, incydenty i rozwinięcia → `docs/RULES_REFERENCE.md`.
Tu wyłącznie obowiązkowe zasady i esencja stylu pracy.

### Profil użytkownika

Jeśli istnieje `docs/USER_PROFILE.md` — czytaj na starcie sesji.
Plik gitignorowany. Szablon: `docs/USER_PROFILE.example`.

---

## 🧠 Styl pracy

### 1. Tryb pracy

AI = sparingpartner: kwestionuje założenia, wskazuje błędy, nie zgadza się bezkrytycznie.
Sesja ma jeden temat — AI sygnalizuje gdy się rozłazi albo jest za długa.
AI mówi „stop" gdy widzi problem architektoniczny zamiast obchodzić go implementacją.

---

### 1a. AI nie działa samo (obowiązkowe)

→ Zasady w globalnym `~/.claude/CLAUDE.md` § „Nie działasz sam". Obowiązują wszędzie.
Polecenie usera („zrób X") jest zgodą na X w opisanym zakresie; wybory poza zakresem
wracają jako pytanie.

→ Incydent i kontekst: docs/RULES_REFERENCE.md § 1a

---

### 2. Język

- komunikacja, issues (tytuł + treść) → **polski**
- kod, docblocki, commit messages, PR (tytuł + opis) → **angielski**
- kwoty w opisach: `600 PLN`, nie `600 zł` — guard łapie diakrytykę
- nazwy lokalne w \`backtickach\` lub "cudzysłowie" — guard je pomija

→ Rejestr wyjaśnień i guard językowy: docs/RULES_REFERENCE.md § 2, § 2a

---

### 3c. Równoległe sesje — każda we własnym worktree (obowiązkowe)

**Zasada: jedna sesja = jeden worktree.**

```bash
git worktree add ../<repo>-<temat> <branch>   # osobny katalog, ta sama historia
git worktree list                              # co jest gdzie
git worktree remove ../<repo>-<temat>          # po zmergowaniu
```

**Worktree nie wystarczy — środowisko dev ma jednego właściciela.** Sesja podnosi środowisko → zapisuje to w `temp/DEV-ENV-OWNER.md`; druga **nie restartuje cudzego kontenera**. Druga sesja pracuje bez środowiska dev.

**Kanał między sesjami: `temp/note-for-<sesja>.md`.** Przed użyciem sprawdź, że `temp/` jest w `.gitignore`.

**Po wykryciu współdzielenia katalogu AI:**

1. mówi o tym wprost
2. **nie używa `git add -A` ani `git add .`** — dodaje wyłącznie własne pliki po nazwie
3. nie przełącza brancha ani nie robi `stash`/`reset`/`restore` bez zgody usera
4. proponuje przeniesienie jednej z sesji do własnego worktree
5. przed commitem sprawdza `git diff --cached --name-only` — **każdy** plik musi należeć do jego zadania
6. **nigdy nie sprząta automatycznie** cudzych zmian

**Nie commituj w trakcie testu usera.** Gdy user testuje na instancji z tego katalogu, AI **najpierw czeka na wynik, potem commituje**. Dotyczy też `git stash`, `checkout` i `rebase`.

→ Szczegóły: docs/RULES_REFERENCE.md § 3c

---

### 3d. Środowisko uruchomieniowe — AI nigdy nie zajmuje portu usera (obowiązkowe)

**AI uruchamia własną, odizolowaną instancję** — osobny port **i** osobny katalog budowania/cache. W projekcie powinna istnieć dedykowana komenda (np. `dev:ai`).

**Twarde zasady:**

- AI **nie ubija** procesów usera — ani „na chwilę"
- AI **nie startuje** niczego na domyślnym porcie
- Twarde ubicie psuje katalog budowania → **wyczyść** przed ponownym startem
- Zatrzymanie instancji usera → **pyta i czeka na zgodę**, po wykonaniu **przywraca** stan
- **Gaszenie własnej instancji** wyłącznie po porcie (`fuser -k <port>/tcp`) albo PID. **Nigdy po nazwie/wzorcu** — hook `guard-process-kill.py` to blokuje
- Plik ze środowiskiem instancji AI nadpisuje **każdą zmienną przypiętą do domyślnego portu**, nie tylko sam port
- **Przy diagnozie zmieniaj jedną rzecz na raz**

→ Szczegóły: docs/RULES_REFERENCE.md § 3d

---

### 4a. Dokumentacja użytkownika nadąża za kodem (obowiązkowe)

Zmiana ekranu bez zmiany opisu to dokumentacja, która kłamie. Trzy warstwy, wszystkie obowiązkowe:

1. **Mapa katalog → dokument** — test pilnuje, że ścieżki istnieją i każdy obszar jest pokryty
2. **Sygnał przy edycji** — hook dopisuje do kontekstu AI, który dokument wymaga aktualizacji
3. **Guard commitu bez flagi pominięcia** — stempel „stan na dzień" = data commita

**Etykiety z konfiguracji, nie przepisane** — etykieta wpisana ręcznie w treści to błąd review.

→ Szczegóły: docs/RULES_REFERENCE.md § 4a

---

### 5a. Podgląd liczy się tą samą funkcją co wynik (obowiązkowe)

Podgląd i wynik końcowy składane **tą samą funkcją**. Osobna kopia logiki to dwa źródła prawdy.

- podgląd i wynik różnią się **danymi wejściowymi**, nigdy regułami
- przed napisaniem podglądu AI sprawdza, gdzie powstaje wynik, i wydziela czystą funkcję
- przykładowe dane też przechodzą przez prawdziwą funkcję
- gdy wynik niesie coś działającego (token, kod dostępu), przykład w podglądzie jest celowo nieważny

→ Incydent: docs/RULES_REFERENCE.md § 5a

---

### 14a. Produkcja – zgoda usera na każdą operację (obowiązkowe)

AI **nie dotyka środowiska produkcyjnego bez wyraźnej zgody usera na konkretną komendę**. **Odczyt też wymaga zgody** — produkcja trzyma realne dane osobowe.

- **Zgoda jest per operacja, nie per sesja.** Zgoda na odczyt nie jest zgodą na zapis.
- **Przed prośbą o zgodę AI pokazuje**: dokładną komendę, co zrobi, czy odwracalna, skąd backup.
- **Przy operacji destrukcyjnej** AI weryfikuje stan **odczytem tuż przed** i zatrzymuje się przy rozbieżności.
- **Guard na prodzie to nie przeszkoda do obejścia** — podaje komendę userowi.
- **Zapytanie kształtem reguły bije listę ID.**

→ Uzasadnienie: docs/RULES_REFERENCE.md § 14a

---

### 14b. Baza dev to też stan — pytaj przed dopisaniem danych (obowiązkowe)

Baza deweloperska jest **wspólnym stanem sesji i usera**. „To tylko dev" nie znosi obowiązku pytania.

- AI **nie dopisuje, nie zmienia i nie kasuje wierszy** bez zgody usera
- **Brak danych do testu to blokada** — AI mówi czego brakuje i czeka
- Dane testowe **jednoznacznie podpisane** (`TEST ...`), razem z **poleceniem kasującym**
- **„Odpal środowisko" to nie zgoda na zmianę danych**
- Dotyczy też migracji, `reset`, seedów i ręcznych `UPDATE`

→ Incydent: docs/RULES_REFERENCE.md § 14b

---

### 16b. Module closure protocol — kolejność z hard-stopem (obowiązkowe)

Każdy moduł / krok / feature przechodzi przez ten flow w **dokładnie tej kolejności**:

1. **Kod** – implementacja
2. **Testy automatyczne**
3. **Checklist testów manualnych** – w `docs/TESTING.md`
4. **🛑 HARD STOP** – *"gotowe, możesz testować — czekam na feedback"* — **AI nie idzie dalej**
5. **User testuje** wg checklisty
6. **User zgłasza błędy** → AI poprawia → powrót do 4
7. **User akceptuje**
8. AI proponuje commit + docs
9. **Commit** z flagą `[user-tested]`
10. **Pre-commit guard** → koniec

- AI **nie wolno** pominąć kroku 4
- AI **nie wolno** dodać `[user-tested]` zanim user nie potwierdził w punkcie 7
- Bypass `[skip-test-check]` — tylko docs/literówki/konfiguracja bez runtime; user akceptuje
- Branchy `docs/*`, `chore/*` — flaga niewymagana, checklist nadal obowiązkowy jeśli dotyka UI/runtime

→ Uzasadnienie: docs/RULES_REFERENCE.md § 16b

---

### 19a. Każda zmiana wizualna = audyt (obowiązkowe)

Każda zmiana widoczna na ekranie kończy się audytem RWD + dostępności (skill `audyt`) **zanim** AI powie „gotowe". Na własnej instancji, telefon + ciemny motyw zawsze, nowy dług do issue — nie naprawiaj po cichu.

→ Szczegóły: docs/RULES_REFERENCE.md § 19a

---

### 19b. Nie wynajduj koła — sprawdź, zanim stworzysz (obowiązkowe)

Rozszerza § 19 („przed nowym komponentem UI — sprawdź co istnieje"): z komponentu na cały **skill/narzędzie**, i ze „sprawdź nasz kod" na „sprawdź też **świat**".

- **Przed robotą od zera** — zanim napiszesz skill/narzędzie, sprawdź, czy istnieje dojrzały gotowiec (nasze repo i świat). Wartość w ogólnej wiedzy → bierz cudze (fork/inspiracja), swój wkład to cienka warstwa pod nasz kontekst. Wartość w naszym kontekście (nasze konta, środowisko, dane) → piszesz sam.
- **W sytuacji podbramkowej** — gdy rozmowa się nie klei i rozwiązanie nie wychodzi, powiedz „stop, zajrzę głębiej" i zrób zwiad po istniejących rozwiązaniach, zamiast brnąć w gorsze obejście. To drugi wyzwalacz „stopu" z § 1, obok problemu architektonicznego.
- **Co podnieść do wspólnego, widzi tylko góra** — że kilka projektów robi to samo, dostrzeże nadzór (jarvis), bo jako jedyny patrzy na wszystkie repo naraz.

→ Kontekst: `marketingskills` (jarvis#148) — omal nie pisaliśmy własnych skilli marketingowych, a istniał dojrzały zestaw 57k⭐ MIT.

---

## 🚫 Zakaz

- nie modyfikuj zastosowanych migracji
- nie zmieniaj scope bez akceptacji usera
- nie wdrażaj tymczasowego rozwiązania bez `TODO:` z kontekstem
- nie używaj natywnych `alert()`, `confirm()`, `prompt()` — toast, modal, dwukrokowy przycisk
- config traktuj jak na produkcji od dnia 1 (env vars / plik config / baza); **dotyczy też seedów**
- współdzielone stałe UI → dedykowany plik config; sprawdź istniejące przed zdefiniowaniem nowej

---

## 📋 Pamięć i artefakty

Feedback i preferencje → CLAUDE.md. Pamięć maszynowa = kontekst tymczasowy. Artefakty repo = source of truth.

**Gdzie żyje otwarta praca:** w projekcie na GitHubie → issues. `docs/TASKS.md` = log sesji.
Projekt bez GitHuba → `docs/TASKS.md` jako lista zadań (ADR-004).

---

## 📚 Reguły referencyjne

Pełna treść reguł → `docs/RULES_REFERENCE.md`. Ładowane gdy potrzebne, nie na starcie:

- § 2a: Rejestr wyjaśnień — tłumacz na ludzki
- § 3: Commit workflow — branch strategy, flagi, dry-run guardów, ekonomia PR
- § 4: Aktualizacja dokumentacji po kroku — co aktualizować, weryfikacja
- § 10: Kontekst projektu — co i kiedy czytać na starcie sesji
- § 13a: AI repo template — zasady pracy z szablonem
- § 13b: Pluginy — podpowiadaj raz gdy kontekst pasuje
- § 15: Wydajność — performance jako feature, mierzenie, RWD
- § 16a: Domknięcie modułu — testy i artefakty
- § 18: Review designu przed implementacją UI
- § 19: Przed nowym komponentem UI — sprawdź co istnieje
- § 20: Rozmiar komponentów (300 linii) i plików logiki (400 linii)
- § ADR: Architecture Decision Records — kiedy, struktura, weryfikacja
- § Roadmap, SETUP.md, artefakty projektu, start projektu
