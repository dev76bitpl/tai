"""Texts handed to Claude Code by the project-start steps (scripts/project-setup.py).

Data, not logic: what the AI is asked to do at each stage. Stays in the project together with
project-setup.py.
"""

# The single word that triggers the scope wizard (skill new-project-scope).
SCOPE_PROMPT = "scope"

# Heading the design stage must leave in docs/UI_GUIDELINES.md — project-setup.py looks for it
# to tell "the project has its visual direction written down" from the template's generic file.
DESIGN_HEADING = "## Kierunek wizualny projektu"
MOCKUPS_DIR = "mockups/propozycje"

_DESIGN_WITH_IMPECCABLE = f"""2. W projekcie jest zainstalowany skill impeccable — prowadź pracę NIM, od początku, a nie dopiero
   na końcu. Wczytaj go teraz, zanim cokolwiek zaprojektujesz.
   - impeccable wymaga pliku PRODUCT.md. Zrób jego start (init) na podstawie briefu z
     docs/PROJECT_SCOPE.md: odpowiedzi bierz z briefu, mnie pytaj tylko o to, czego w briefie nie ma.
   - Kierunki wyglądu projektuj jego metodą (shape / craft), a przed pokazaniem mi przepuść makiety
     przez jego krytykę (critique) i detektor — i popraw to, co znajdą.
   - Niezależnie od tego, gdzie impeccable domyślnie zapisuje pliki, makiety mają trafić do
     {MOCKUPS_DIR}/ (punkt 3). Jego własne pliki robocze (PRODUCT.md, .impeccable/) zostają tam,
     gdzie je tworzy.
   - design-taste-frontend i ui-ux-pro-max traktuj jako pomoc tam, gdzie pasują (strony i landingi;
     panele i produkty z wieloma ekranami). Powiedz mi jednym zdaniem, czym pracujesz."""

_DESIGN_WITHOUT_IMPECCABLE = """2. Użyj skilli do projektowania dostępnych w projekcie i dobierz sposób pracy do TEGO projektu:
   design-taste-frontend sprawdza się przy stronach, landingach i portfolio; ui-ux-pro-max przy
   panelach, tabelach i produktach z wieloma ekranami. Wczytaj wybrany skill, zanim cokolwiek
   zaprojektujesz. Nie stosuj wszystkiego naraz: wybierz, co pasuje, i powiedz mi jednym zdaniem,
   czym pracujesz i dlaczego. Jeśli żadnego z nich nie ma w projekcie, powiedz mi to wprost."""


def design_prompt(impeccable: bool) -> str:
    """The design task. With impeccable installed in the project it leads the work from the start —
    left as "use it if present", Claude reached for it only when the user asked."""
    how = _DESIGN_WITH_IMPECCABLE if impeccable else _DESIGN_WITHOUT_IMPECCABLE
    return f"""Przygotuj szablon graficzny tego projektu.

1. Przeczytaj brief w docs/PROJECT_SCOPE.md i ADR-001 w docs/adr/ (stos). Jeśli briefu nie ma,
   powiedz mi to i zapytaj, co budujemy — nie zgaduj.
{how}
3. Zaproponuj dwa wyraźnie różne kierunki wyglądu, każdy w wersji jasnej i ciemnej, jako
   samodzielne pliki HTML w katalogu {MOCKUPS_DIR}/ w głównym katalogu projektu:
   kierunek-1-jasna.html, kierunek-1-ciemna.html, kierunek-2-jasna.html, kierunek-2-ciemna.html
   oraz index.html z odnośnikami do nich. Nigdzie indziej — skrypt startu szuka ich właśnie tam.
   Makieta to najważniejszy ekran z briefu, z prawdziwą treścią z briefu — bez lorem ipsum.
4. Powiedz mi, jak otworzyć makiety w przeglądarce, i zadaj jedno pytanie: który kierunek wybieram.
5. Po moim wyborze zapisz zasady w docs/UI_GUIDELINES.md, w nowej sekcji
   „{DESIGN_HEADING}”: kolory jako tokeny, typografia, odstępy, kluczowe komponenty,
   zasady dla trybu jasnego i ciemnego. Reszty pliku nie usuwaj.
6. Na końcu powiedz mi, żebym wyszedł z Claude Code (/exit): skrypt startu projektu czeka za tą
   sesją i sprawdzi, czy makiety i zasady powstały.
"""


def help_prompt(title: str, command: str, code: int, output: str, resume: str) -> str:
    tail = "\n".join(output.strip().splitlines()[-30:])[-3000:]
    return (
        f"Krok startu projektu „{title}” nie powiódł się.\n"
        f"Polecenie: {command}\n"
        f"Kod wyjścia: {code}\n"
        f"Końcówka wyniku:\n{tail or '(brak wyniku)'}\n\n"
        "Pomóż mi to naprawić. Gdy będzie naprawione, powiedz mi, żebym wyszedł z Claude Code — "
        f"skrypt startu zapyta wtedy, czy ponowić krok (albo później: {resume})."
    )
