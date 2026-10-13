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

- `scripts/dev-guards/guard_tests_with_src.py:41` `get_src_dirs()` czyta `src_dirs`, przy wartości
  nieużywalnej wraca do `src`; `:50` `is_test_file()`; `:59` `is_source_file()`
- `scripts/dev-guards/stack.py:151` `get_adr_patterns()` bierze tylko `adr_patterns` — klucz
  `_adr_patterns_optional` jest dla strażnika niewidoczny
- `scripts/set-stack.py:43` `apply_stack()` nie usuwa grup z katalogu i przy zmianie stosu
  wyłącza poprzednią grupę
- `scripts/project-setup.py:99` `scope_is_filled()`, `:197` `STEPS` (brief ostatni)

**Założenia nieegzekwowane = ryzyko:**

- to, że kreator po wywiadzie faktycznie uruchomi `set-stack.py`, wynika z instrukcji dla AI
  (`.claude/skills/new-project-scope/SKILL.md`, „Artifact 3”), nie z kodu; test pilnuje tylko
  sformułowań. Projekt, w którym wywiad się nie odbył, zostaje na ustawieniach domyślnych
- katalogi w tabeli stosów dla WordPressa, PrestaShop, Magento, Go i Rails pochodzą z wiedzy
  ogólnej, nie z pomiaru na projektach; projekt o innym układzie poprawia `src_dirs` sam

**Wymaga uwagi:**

- projekty postawione wcześniej mają stare wzorce platform we własnym `config.json`
- synchronizacja z szablonu nie przenosi `scripts/`, więc starszy projekt nie dostanie
  `set-stack.py` (skill to przewiduje i pomija krok)
- po wyjściu z Claude Code użytkownik nie wraca do kroków startu (#180)
