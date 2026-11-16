"""Issue labels every project of the group works with — one list for the project start (and any
later check of existing repositories), so the rules and the repositories cannot drift apart (#238).

- owner, idea: the owner's queue and ideas (global CLAUDE.md)
- bug, feature, system: kind of work; open work lives in issues (global CLAUDE.md, 6.10.2026)
- urgent, high, normal, low: every new issue gets a priority (jarvis procedure, 17.10.2026)
- jarvis: orders and reminders from jarvis, the group's PM
"""

# (name, colour, description)
LABELS = [
    ("owner", "D93F0B", "Sprawa czeka na właściciela projektu"),
    ("idea", "FBCA04", "Pomysł: czeka na potwierdzenie, plan albo odrzucenie"),
    ("bug", "d73a4a", "Something isn't working"),
    ("feature", "1D76DB", "New functionality"),
    ("system", "5319E7", "Narzędzia / szablon tai — nie funkcja produktu (reguła 13a)"),
    ("urgent", "B60205", "🔴 Twardy termin albo bloker"),
    ("high", "e99d42", "🟠 Pilne"),
    ("normal", "0e8a16", "🟢 Normalne"),
    ("low", "c5def5", "⚪ Niski priorytet"),
    ("jarvis", "5319e7", "Zlecenie lub przypomnienie od jarvisa (PM)"),
]

NAMES = [name for name, _, _ in LABELS]


def missing(existing: "set[str]") -> "list[tuple[str, str, str]]":
    """Labels from LABELS that the repository does not have yet, in list order."""
    return [label for label in LABELS if label[0] not in existing]
