#!/usr/bin/env python3
"""Shared Polish-language detector (CLAUDE.md rule 2).

Single source of truth for "is this text Polish?", reused by:
  - guard_commit_lang.py  (commit subject, commit-msg stage)
  - check_pr_language.py   (PR title + body, CI on pull_request)

Keeping one detector avoids two drifting word lists (CLAUDE.md rule 5: extract
the shared piece once a second caller appears — that is now).
"""
import re

# Polish-specific letters (and uppercase).
POLISH_CHARS = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")

# Common Polish words / fragments — whole-word, case-insensitive, to avoid
# matching English substrings. Extend as new false-positives surface.
POLISH_WORDS = re.compile(
    r"\b("
    r"dodaj|dodano|dodać|dodaje|"
    r"usuń|usunięty|usunięto|usuwa|"
    r"zmień|zmieniony|zmieniono|zmiana|"
    r"napraw|naprawiono|naprawa|"
    r"popraw|poprawka|poprawiono|"
    r"refaktor|refaktoryzacja|"
    r"obsługa|obsłuż|"
    r"konfiguracja|konfig|"
    r"uaktualnij|aktualizacja|"
    r"weryfikacja|sprawdź|sprawdzanie|"
    r"użytkownik|użytkownicy|"
    r"nauczyciel|uczeń|szkoła|lekcja|"
    r"wsparcie|wspiera|"
    r"oraz|jest|nie|tak|gdzie|kiedy|jak|który|która|które|"
    r"przed|przez|przy|"
    r"plik|pliki|"
    r"funkcja|funkcje"
    r")\b",
    re.IGNORECASE,
)


def find_polish(text: str) -> str | None:
    """Return the first Polish character or word found, or None if the text
    looks English. Polish chars are checked first (strongest signal)."""
    char = POLISH_CHARS.search(text)
    if char:
        return char.group()
    word = POLISH_WORDS.search(text)
    if word:
        return word.group()
    return None
