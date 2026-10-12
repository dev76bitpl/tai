"""Personal-data detector used by the pre-commit guard (guard_pii.py); importable on its
own, e.g. by a scheduled repo scan. Polish context: the formats below are Polish. Personal
data of real people must never land in a repository.

Detects, per line of text:
  - PESEL (11 digits with a valid checksum)
  - Polish bank account / IBAN (26 digits, optional PL, valid mod-97)
  - Polish mobile numbers (+48 or written as xxx xxx xxx / xxx-xxx-xxx, first digit 4-8);
    obvious non-phones (000 000 000, 255 255 255, parts of longer numbers) are ignored
  - e-mail addresses on public mail providers (gmail, wp, onet, o2, interia, ...);
    company and example domains are not personal data in this sense
  - names from a local list (~/.config/76bit/pii-names.txt, one name per line), if present.
    The list stays on the machine and is never committed.

Public company contact data (the office phone number on every website) is not personal data:
list such values in ~/.config/76bit/pii-public.txt (one per line, digits or e-mail).

A line containing the marker `pii-ok` is skipped (documented fake data, fixtures).
Found values are always reported masked, never in full.

The kind labels returned by scan_line ("PESEL", "bank account", "phone", "private e-mail",
"listed name") are a contract: callers may store them (e.g. in allowlist keys), so renaming
one requires rewriting such stored keys in the same step.
"""
import os
import re
from pathlib import Path

MARKER = "pii-ok"
NAMES_FILE = Path(os.environ.get("PII_NAMES_FILE", Path.home() / ".config" / "76bit" / "pii-names.txt"))
PUBLIC_FILE = Path(os.environ.get("PII_PUBLIC_FILE", Path.home() / ".config" / "76bit" / "pii-public.txt"))

PUBLIC_MAIL = (
    "gmail.com", "googlemail.com", "wp.pl", "o2.pl", "onet.pl", "onet.eu", "op.pl", "interia.pl",
    "interia.eu", "poczta.fm", "tlen.pl", "gazeta.pl", "vp.pl", "outlook.com", "hotmail.com",
    "live.com", "icloud.com", "me.com", "yahoo.com", "proton.me", "protonmail.com",
)

PESEL_RE = re.compile(r"(?<!\d)(\d{11})(?!\d)")
ACCOUNT_RE = re.compile(r"(?<![\dA-Z])(?:PL\s?)?(\d{2}(?:[ ]?\d{4}){6})(?!\d)")
PHONE_RE = re.compile(r"(?<![\d+.,])(?:\+48[ -]?[4-8]\d{2}[ -]?\d{3}[ -]?\d{3}|[4-8]\d{2}[ -]\d{3}[ -]\d{3})(?![\d.,-])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def mask(value: str) -> str:
    v = value.strip()
    if len(v) <= 4:
        return "*" * len(v)
    return v[:2] + "*" * (len(v) - 4) + v[-2:]


def pesel_ok(d: str) -> bool:
    w = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    s = sum(int(d[i]) * w[i] for i in range(10))
    if (10 - s % 10) % 10 != int(d[10]):
        return False
    month = int(d[2:4]) % 20
    return 1 <= month <= 12 and 1 <= int(d[4:6]) <= 31


def account_ok(digits: str) -> bool:
    d = re.sub(r"\D", "", digits)
    if len(d) != 26:
        return False
    rearranged = d[2:] + "2521" + d[:2]  # "PL" -> 25 21
    return int(rearranged) % 97 == 1


def _public():
    try:
        vals = PUBLIC_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out = set()
    for v in vals:
        v = v.strip().lower()
        if v and not v.startswith("#"):
            out.add(v if "@" in v else re.sub(r"\D", "", v)[-9:])
    return out


PUBLIC = _public()


def load_names():
    try:
        names = [n.strip() for n in NAMES_FILE.read_text(encoding="utf-8").splitlines()]
    except OSError:
        return []
    return [n for n in names if len(n) >= 3 and not n.startswith("#")]


def scan_line(line: str, names=()):
    """Return a list of (kind, masked_value) found in one line."""
    if MARKER in line:
        return []
    found = []
    for m in PESEL_RE.finditer(line):
        if pesel_ok(m.group(1)):
            found.append(("PESEL", mask(m.group(1))))
    for m in ACCOUNT_RE.finditer(line):
        if account_ok(m.group(1)):
            found.append(("bank account", mask(m.group(1))))
    for m in PHONE_RE.finditer(line):
        digits = re.sub(r"\D", "", m.group(0))[-9:]
        if len(set(digits[3:])) == 1 or digits in PUBLIC:
            continue  # 600 000 000 style placeholders, company numbers
        found.append(("phone", mask(m.group(0))))
    for m in EMAIL_RE.finditer(line):
        if m.group(1).lower() in PUBLIC_MAIL and m.group(0).lower() not in PUBLIC:
            found.append(("private e-mail", mask(m.group(0))))
    low = line.lower()
    for n in names:
        if re.search(r"(?<!\w)" + re.escape(n.lower()) + r"(?!\w)", low):
            found.append(("listed name", mask(n)))
    return found
