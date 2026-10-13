# ADR-005 — Stos projektu ustala wywiad o zakresie, a z niego wynikają ustawienia strażników

**Status:** accepted
**Data:** 2026-10-13

## Kontekst

Strażnicy commita stosowali do każdego projektu wzorce jednego stosu:

- wzorce „to wygląda na decyzję architektoniczną” dla WordPressa, PrestaShop i Magento były
  aktywne wszędzie — projekt bez sklepu dostawał blokadę „nowy moduł PrestaShop” za katalog `modules/`
- strażnik „kod wymaga testów” znał tylko nazwy testów z JavaScriptu i tylko katalog `src/`

Fałszywy alarm uczy sięgać po flagę pominięcia, a wtedy strażnik przestaje chronić. Ustawienia
dało się poprawić ręcznie w `config.json`, ale nikt tego nie robił: plik powstawał automatycznie
przy starcie projektu. Start projektu i wywiad o zakresie były dwoma niepowiązanymi krokami,
a kreator zakresu według własnej instrukcji nie powinien ruszać po `--init` (plik zakresu
istniał zawsze, jako szkielet).

## Decyzje i uzasadnienia

1. **Wzorce platform są nieaktywne, dopóki projekt nie jest na tej platformie.**
   `config.json.example` trzyma je w `_adr_patterns_optional`; aktywne są tylko ogólne.
   Dlaczego: strażnik krzyczący bez powodu szkodzi bardziej niż brak wzorca przez pierwszy dzień.
2. **Testy rozpoznaje wbudowana lista konwencji wszystkich stosów**, bez konfiguracji.
   Dlaczego: nazwy są jednoznaczne i zgodne z `docs/CONVENTIONS.md`; nie ma projektu, który
   potrzebuje własnego nazewnictwa.
3. **Katalogi kodu (`src_dirs`) i grupę wzorców platformy ustawia jedna nazwa stosu**
   (`scripts/set-stack.py`, tabela `STACK_PRESETS`). Człowiek nie jest pytany o katalogi
   i nie edytuje pliku ręcznie.
4. **Stos pada w wywiadzie o zakresie, nie przy `--init`.** Po wywiadzie kreator uruchamia
   `set-stack.py`. Dlaczego: przy `--init` nikt jeszcze nie przemyślał projektu, a pytanie
   o stos i tak pada w wywiadzie, gdzie decyzja trafia do ADR-001. `--init --stack` zostaje
   dla kogoś, kto stos już zna.
5. **Start projektu to prowadzone kroki w skrypcie, który zostaje w projekcie**
   (`scripts/project-setup.py`): krok zrobiony jest pomijany, nieudany proponuje pomoc AI
   z poleceniem i błędem, bez terminala drukowana jest sama lista.
   Dlaczego: lista do przepisania zostawiała użytkownika samego z błędem; skrypt startu kasuje
   sam siebie, więc kroków nie dało się w nim wznowić.
6. **Szkielet `docs/PROJECT_SCOPE.md` z szablonu liczy się jak brak briefu**; własna treść
   oznacza „brief jest” i wywiad jest pomijany.

7. **Claude Code jest uruchamiany jako proces potomny, a skrypt sprawdza wynik po powrocie**
   (uzupełnienie z 2026-10-13, #180). Po wywiadzie: własna treść briefu, klucz `stack`
   w `config.json`, ADR-001 — każdy punkt osobno; po pomocy AI przy nieudanym kroku: pytanie
   o ponowienie; na końcu podsumowanie. Dlaczego: pierwsza wersja zastępowała proces skryptu
   (`os.execvp`), więc po wyjściu z Claude Code użytkownik tracił kontakt z krokami, a nikt
   nie sprawdzał, czy wywiad cokolwiek zostawił. Sprawdzenie zamienia część założenia
   „kreator uruchomi `set-stack.py`” z nadziei w fakt widoczny dla użytkownika.

8. **Projekt wybiera, które grupy skilli ma; niewybrane są usuwane i wyłączone z synchronizacji**
   (uzupełnienie z 2026-10-13, #183). `scripts/select-skills.py` trzyma tabelę grup i propozycje
   według stosu; wybór zapisuje w `skills-manifest.json` (`skill_groups`, `excluded_skills`).
   Krok „Skille” idzie po briefie, bo stos podpowiada wybór. Dlaczego: szablon wysyłał każdemu
   projektowi komplet skilli wszystkich technologii, a krok „Skille” tylko je odświeżał —
   wybór bez usunięcia nie zmniejszał szumu, a usunięcie bez wyłączenia cofała najbliższa
   synchronizacja. Odrzucone: wybór tylko „co odświeżyć” (niczego nie zmienia w projekcie).

9. **Start projektu proponuje szablon graficzny; skille do projektowania są vendored z publicznych
   źródeł, a `impeccable` zostaje poza szablonem** (uzupełnienie z 2026-10-13, #184). Krok po briefie
   uruchamia Claude Code z zadaniem: dwa kierunki wyglądu, każdy jasny i ciemny, jako makiety
   w `mockups/propozycje/`, po wyborze zasady w `docs/UI_GUIDELINES.md`. Zadanie nie wskazuje
   jednego skilla — Claude dobiera sposób pracy do projektu. Dlaczego bez `impeccable` w szablonie:
   skan bezpieczeństwa `update-skills.py` zatrzymał instalację na zbundlowanych skryptach
   (ok. 2 MB cudzego kodu, którego nikt nie przejrzał); guard nie jest przeszkodą do obejścia,
   więc skill instaluje się osobno w projekcie, który go chce: krok pyta o to z domyślną
   odpowiedzią „nie” i na wyraźne „tak” uruchamia instalator z `--scope=project --no-hooks`
   (bez `--no-hooks` instalator dopisuje własny hook do `.claude/settings.local.json`, gdzie
   mieszkają strażnicy — według jego README; nie uruchamialiśmy go). Kolejność kroków: brief →
   skille → szablon graficzny. Pierwsza wersja miała skille na końcu (żeby szablon graficzny na
   pewno miał skille do projektowania), ale próba na żywo pokazała, że wywiad i projektowanie
   odbywały się wtedy w projekcie z kompletem zbędnych skilli; krok szablonu ostrzega teraz,
   gdy grupa „Projektowanie wyglądu” została odrzucona.

10. **Kreator ustawia w repo na GitHubie to, co instrukcja nazywa blokującym — po jednym pytaniu,
    a uprawnienia automatów tylko projektom z automatem wydań** (uzupełnienie z 2026-10-13, #186).
    Kasowanie gałęzi po scaleniu jest proponowane zawsze. Zapis do repo i zatwierdzanie pull
    requestów przez automaty GitHuba to szersze uprawnienie, niż ma świeże repo, więc krok
    proponuje je tylko wtedy, gdy projekt ma `.github/workflows/release-please*.yml` — bez nich
    automat wydań pada po każdym scaleniu do `main`. Gdy GitHub odmówi, krok pokazuje polecenia
    i start idzie dalej. `npm run doctor` ostrzega według tej samej reguły. Dlaczego: kto przechodzi
    start kreatorem, nie zagląda do kroku 1 instrukcji — pominięto go w co najmniej trzech projektach.
    Odrzucone: ustawiać oba zawsze (uprawnienia bez potrzeby); lista do wyboru (decyzja właściciela:
    jedno pytanie tak/nie).

## Odrzucone alternatywy

| Opcja | Dlaczego odrzucona |
|---|---|
| Wykrywanie platformy przy commicie po plikach projektu | najwięcej kodu i własne fałszywe trafienia |
| Pytanie o katalogi kodu | człowiek myśli stosem, nie katalogami; decyzja właściciela |
| Parametr stosu „php” / „node” | Laravel trzyma kod w `app/`, Symfony w `src/` — lista musi być na poziomie frameworka |
| Pytanie o stos w `--init` | pada dwa razy i za wcześnie |
| Szersza domyślna lista katalogów (`src`, `app`, `lib`) | istniejące projekty dostałyby nowe blokady po synchronizacji |
| Lista wzorców testów w konfiguracji | kolejna rzecz do wypełnienia bez przypadku użycia |

## Konsekwencje

**Zweryfikowane w kodzie (stan gałęzi z tą decyzją):**

- `.claude/hooks/session-context.py` `_local_desynced()` i `scripts/update-skills.py`
  `sync_from_template()` pomijają nazwy z `excluded_skills`
- `scripts/dev-guards/guard_tests_with_src.py:41` `get_src_dirs()` czyta `src_dirs`, przy wartości
  nieużywalnej wraca do `src`; `:50` `is_test_file()`; `:59` `is_source_file()`
- `scripts/dev-guards/stack.py:151` `get_adr_patterns()` bierze tylko `adr_patterns` — klucz
  `_adr_patterns_optional` jest dla strażnika niewidoczny
- `scripts/set-stack.py:43` `apply_stack()` nie usuwa grup z katalogu i przy zmianie stosu
  wyłącza poprzednią grupę
- `scripts/project-setup.py`: `scope_is_filled()`, `STEPS` (brief ostatni)

**Założenia nieegzekwowane = ryzyko:**

- to, że kreator po wywiadzie faktycznie uruchomi `set-stack.py`, wynika z instrukcji dla AI
  (`.claude/skills/new-project-scope/SKILL.md`, „Artifact 3”), nie z kodu; test pilnuje tylko
  sformułowań. Projekt, w którym wywiad się nie odbył, zostaje na ustawieniach domyślnych.
  Łagodzi to decyzja 7: skrypt startu po powrocie z wywiadu pokazuje `✗` przy nieustawionym stosie
- katalogi w tabeli stosów dla WordPressa, PrestaShop, Magento, Go i Rails pochodzą z wiedzy
  ogólnej, nie z pomiaru na projektach; projekt o innym układzie poprawia `src_dirs` sam

**Wymaga uwagi:**

- projekty postawione wcześniej mają stare wzorce platform we własnym `config.json`
- synchronizacja z szablonu nie przenosi `scripts/`, więc starszy projekt nie dostanie
  `set-stack.py` (skill to przewiduje i pomija krok)
