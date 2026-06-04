# ADR-002 — Sync wzorca: blokada-potwierdzenie zamiast lokalnego porównania; jeden kanoniczny config hooków

**Status:** accepted
**Data:** 2026-06-04

---

## Kontekst

Wzorzec (ten repozytorium) jest kopiowany do projektów. Gdy w projekcie zmienia się
**uniwersalna** reguła `CLAUDE.md`, musi wrócić do wzorca (reguła 13a) — inaczej kolejne
projekty dziedziczą starą wersję. Pilnuje tego guard sync. Zastany stan ma trzy wady:

1. **Guard sync zależy od lokalnego klona wzorca.** Mechanizm: `git diff` na `CLAUDE.md`
   w lokalnym katalogu wskazanym przez `ai_template_path`. Wymaga, by oba repo były na
   jednym dysku i edytowane w tej samej sesji. Nowy developer (albo właściciel na nowym
   kompie) klonuje *projekt*, nie wzorzec — nie ma wzorca lokalnie i nie pomyśli, żeby go
   sklonować. Bez ścieżki guard **po cichu nic nie robi** → ochrona domyślnie wyłączona dla
   wszystkich, którzy ręcznie jej nie skonfigurowali. Cichy guard jest gorszy niż brak
   guarda — daje fałszywe poczucie pilnowania.

2. **`ai_template_path` bywa URL-em.** `create_config_json` domyślnie wpisuje URL remote
   ("żeby działało między maszynami"). Ale wszyscy konsumenci wymagają lokalnego katalogu
   (`is_dir()`, `git diff` w drzewie). URL → guard cicho odpuszcza. Plus **bug A**: w
   `--init` `create_config_json(root, root)` wpisuje remote *projektu* jako ścieżkę wzorca.

3. **Config rozjechany na dwa pliki.** `scripts/dev-guards/stack.py` czyta
   `.pre-commit-hooks.config.json` (nie istnieje, nikt go nie tworzy), a
   `.claude/hooks/stack.py` + `doctor.py` + `session-context.py` czytają
   `.claude/hooks/config.json`. Guardy wpięte w pre-commit (sync, lint, test, adr_patterns)
   czytają nieistniejący plik → w nowych projektach martwe.

Wady 1 i 2 mają wspólny korzeń: `ai_template_path` (lokalna ścieżka) traktowany jako
*fundament* ochrony, a nie da się go niezawodnie mieć na każdej maszynie. Decyzja przenosi
ciężar z porównania plików na świadomą decyzję przy commicie.

---

## Decyzje i uzasadnienia

### 1. Guard sync = blokada-potwierdzenie, domyślnie włączona, bez lokalnego klona

Gdy `CLAUDE.md` jest staged, guard **zawsze** wymaga świadomej decyzji: albo zmiana jest
projektowa / już zsynchronizowana → `[skip-sync]` w body, albo uniwersalna → przenieś do
wzorca. Nie ma trybu "cicho przepuść bo brak ścieżki".

**Dlaczego:** działa dla każdego, zero setupu, bez sieci, bez lokalnego klona wzorca.
Odwraca zepsuty domyślny stan (cichy skip przy braku ścieżki) na "enforce przez
potwierdzenie". Realna wartość guarda zawsze leżała w wymuszeniu świadomej decyzji —
porównanie plików było słabym bonusem (sprawdzało tylko "czy plik wzorca ruszony", nie
"czy poprawnie zsynchronizowany").

### 2. `ai_template_path` = opcjonalny bonus dla maintainera, nie fundament

Jeśli ścieżka jest ustawiona i wskazuje realny lokalny klon wzorca → guard **dodatkowo**
sam zweryfikuje przez `git diff` (mniej `[skip-sync]` do klikania). Jeśli jej nie ma / jest
URL-em / wskazuje nieistniejący katalog → guard spada do trybu z punktu 1 (**potwierdzenie,
nie cichy skip**).

**Dlaczego:** zachowuje wygodę dla osoby utrzymującej wzorzec (ma wzorzec lokalnie), nie
karząc reszty. Wartość-URL i błędna ścieżka stają się **nieszkodliwe** — degradują się do
trybu pytania, zamiast wyłączać ochronę.

### 3. `--init` nie wpisuje już ścieżki wzorca (kasuje bug A)

`create_config_json` przestaje preferować URL i przestaje auto-ustawiać `ai_template_path`
— zostaje placeholder z `.example`. Maintainer ustawia lokalną ścieżkę u siebie, jeśli chce
auto-weryfikacji.

**Dlaczego:** skoro ścieżka jest opcjonalna, generator nie ma czego sensownie wpisać
(projekt nie wie, gdzie user trzyma klon wzorca). Bug A znika, bo `ai_template_path`
przestaje być load-bearing. Mniej kodu (`_git_remote_url` znika z tej ścieżki).

### 4. Jeden kanoniczny plik configu: `.claude/hooks/config.json`

`scripts/dev-guards/stack.py` przestawiony na `.claude/hooks/config.json`;
`.pre-commit-hooks.config.json` znika z kodu. Oba `stack.py` i oba guardy sync czytają jedno
źródło (`lint`, `test`, `adr_patterns`, `repos`, opcjonalnie `ai_template_path`).

**Dlaczego:** `.claude/hooks/config.json` już jest faktycznym centrum (ma `.example`, tworzy
go `new-project.py`, czyta doctor i session-context). `.pre-commit-hooks.config.json` to
sierota bez producenta. Plik zostaje **commitowalny** — niesie współdzielone klucze
projektowe; `ai_template_path`, jeśli ktoś wpisze lokalną ścieżkę, na innej maszynie po
prostu nie istnieje → degraduje się do trybu potwierdzenia (punkt 2), więc nie szkodzi.
Gitignore niepotrzebny.

### 5. Flaga `is_template` dla samego wzorca

We wzorcu nie ma wzorca "wyżej" — guard nie ma czego pilnować. Wzorzec dostaje committowany
`.claude/hooks/config.json` z `"is_template": true`; guard widząc tę flagę → no-op dla sync.
Projekty tej flagi nie mają.

**Dlaczego:** bez tego guard we wzorcu blokowałby każdą edycję `CLAUDE.md`, pytając o sync do
nieistniejącego nadrzędnego wzorca.

### 6. Reset `docs/adr/` przy tworzeniu projektu

Własne ADR-y wzorca (ADR-002+) opisują wewnętrzną mechanikę wzorca — projekt nie ma w nich
interesu. `new-project.py --init` resetuje cały `docs/adr/` (stan końcowy: pusty katalog
z `.gitkeep`), analogicznie do `reset_versioning` (zrzuca CHANGELOG wzorca) i
`fresh_git_history`. Tryb kopiowania już tworzy pusty `docs/adr/`, więc tam wycieku nie ma.

**Dlaczego:** `docs/adr/` we wzorcu pełni dwie role — scaffold dla projektu **oraz** dom na
własne decyzje wzorca. Bez resetu ADR-y wzorca wyciekają do każdego projektu. Reset hurtowy
(zamiast wykreślania plików po nazwie) jest spójny z istniejącą filozofią "projekt = czysty
start".

---

## Odrzucone alternatywy

| Opcja | Dlaczego odrzucona |
|-------|--------------------|
| Lokalna ścieżka jako wymóg (pierwotny kierunek) | Nikt nie ma wzorca na dysku → guard domyślnie śpi; fałszywe poczucie ochrony |
| Guard ściąga wzorzec z URL przy commicie i porównuje | Sieć przy każdym commicie, wolny pierwszy raz, wymaga przepisania logiki (porównanie do zdalnego repo to inny algorytm niż lokalny diff) — dużo budowy, mała przewaga nad trybem potwierdzenia |
| Kanoniczny `.pre-commit-hooks.config.json` | Sierota bez producenta; trzeba by dorobić generację, example, czytanie w doctor/session-context |
| Gitignore `config.json` + tylko `.example` | Niepotrzebne, bo błędna `ai_template_path` degraduje się bezpiecznie; gitignore odebrałby współdzielenie `lint`/`test`/`adr_patterns` |
| `doctor --fix` / skrypt migracyjny | YAGNI — po zmianie istniejące projekty działają (degradacja do potwierdzenia), migracja to zwykły update plików guarda |
| Osobny katalog na wewnętrzne ADR-y wzorca (`docs/adr-internal/`) | Dwa katalogi ADR to zamęt; reset całego `docs/adr/` przy init jest prostszy i zgodny z filozofią "czysty start" |

---

## Konsekwencje

**Ułatwia:**
- Guard sync działa dla każdego od pierwszego commita, bez setupu i bez lokalnego wzorca.
- Znikają trzy problemy naraz: URL, bug A, ręczna migracja ścieżki — przestają być
  load-bearing.
- Jedno źródło configu — ożywają martwe pre-commitowe guardy lint/test/adr/sync w nowych
  projektach.
- Mniej kodu niż wariant "URL-aware + fix bug A".

**Utrudnia / wymaga uwagi:**
- Każda zmiana `CLAUDE.md` bez ustawionej lokalnej ścieżki wymaga jawnego `[skip-sync]` (dla
  zmian projektowych) — świadomy koszt, taki jest cel.
- Guard nie *weryfikuje* już realnie synchronizacji, gdy ścieżka nie jest ustawiona — opiera
  się na dyscyplinie (potwierdzenie). Akceptowalne: główny edytor `CLAUDE.md` to AI, a
  blokada zmusza je do zatrzymania i decyzji.
- Dwa guardy sync (pre-commit + Claude hook) zostają — oba przechodzą na tryb potwierdzenia
  i czytają ten sam plik; świadomy defense-in-depth.
- Migracja istniejących projektów: zaktualizować pliki guarda + `stack.py` do nowej wersji.
  Funkcjonalnie nie pilne — stary błędny `ai_template_path` po zmianie degraduje się
  bezpiecznie.
- `new-project.py --init` resetuje `docs/adr/` hurtowo — przy dodawaniu nowych własnych
  ADR-ów wzorca nie trzeba już pamiętać o `TEMPLATE_META`.
- Każdy guard, który tu powstanie/zmieni się, wchodzi z testem dowodzącym: (1) blokuje gdy
  ma blokować, (2) przepuszcza resztę.
