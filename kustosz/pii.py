"""Deterministyczne wykrywanie i pseudonimizacja polskich danych z walidacją sum kontrolnych."""
from __future__ import annotations

import re
from dataclasses import dataclass

_PESEL = re.compile(r"(?<!\d)(\d{11})(?!\d)")
_NIP = re.compile(r"(?<![\d-])(\d{3}-?\d{3}-?\d{2}-?\d{2}|\d{3}-?\d{2}-?\d{2}-?\d{3})(?![\d-])")
_REGON = re.compile(r"(?<!\d)(\d{9}|\d{14})(?!\d)")
_IBAN = re.compile(r"\b(?:PL)?\s?(\d{2}(?:\s?\d{4}){6})\b")
_DOWOD = re.compile(r"\b([A-Z]{3}\s?\d{6})\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?<!\d)(?:\+48[\s-]?)?(?:\d{3}[\s-]?\d{3}[\s-]?\d{3})(?!\d)")


def _digits(s: str) -> list[int]:
    return [int(c) for c in s if c.isdigit()]


def pesel_ok(s: str) -> bool:
    d = _digits(s)
    if len(d) != 11:
        return False
    w = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    c = (10 - sum(a * b for a, b in zip(d, w)) % 10) % 10
    month = d[2] * 10 + d[3]
    return c == d[10] and (month % 20) in range(1, 13)


def nip_ok(s: str) -> bool:
    d = _digits(s)
    if len(d) != 10:
        return False
    w = [6, 5, 7, 2, 3, 4, 5, 6, 7]
    c = sum(a * b for a, b in zip(d, w)) % 11
    return c != 10 and c == d[9]


def regon_ok(s: str) -> bool:
    d = _digits(s)
    if len(d) == 9:
        w = [8, 9, 2, 3, 4, 5, 6, 7]
    elif len(d) == 14:
        w = [2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8]
    else:
        return False
    c = sum(a * b for a, b in zip(d, w)) % 11 % 10
    return c == d[-1]


def iban_ok(s: str) -> bool:
    d = "".join(c for c in s if c.isdigit())
    if len(d) != 26:
        return False
    num = d[2:] + "2521" + d[:2]
    return int(num) % 97 == 1


def dowod_ok(s: str) -> bool:
    s = s.replace(" ", "")
    if len(s) != 9:
        return False
    val = [ord(c) - 55 for c in s[:3]] + [int(c) for c in s[3:]]
    w = [7, 3, 1, 0, 7, 3, 1, 7, 3]
    return sum(a * b for a, b in zip(val, w)) % 10 == val[3]


@dataclass
class PiiSpan:
    start: int
    end: int
    kind: str
    value: str
    source: str = "deterministic"
    reason: str = "walidacja sumy kontrolnej / wzorca"


def find_deterministic(text: str) -> list[PiiSpan]:
    """Zwraca nienakładające się wykryte identyfikatory w tekście."""
    spans: list[PiiSpan] = []
    for m in _IBAN.finditer(text):
        if iban_ok(m.group(1)):
            spans.append(PiiSpan(m.start(), m.end(), "IBAN", m.group(0)))
    for m in _PESEL.finditer(text):
        if pesel_ok(m.group(1)):
            spans.append(PiiSpan(m.start(1), m.end(1), "PESEL", m.group(1)))
    for m in _NIP.finditer(text):
        if nip_ok(m.group(1)):
            spans.append(PiiSpan(m.start(1), m.end(1), "NIP", m.group(1)))
    for m in _REGON.finditer(text):
        if regon_ok(m.group(1)):
            spans.append(PiiSpan(m.start(1), m.end(1), "REGON", m.group(1)))
    for m in _DOWOD.finditer(text):
        if dowod_ok(m.group(1)):
            spans.append(PiiSpan(m.start(1), m.end(1), "DOWOD", m.group(1)))
    for m in _EMAIL.finditer(text):
        spans.append(PiiSpan(m.start(), m.end(), "EMAIL", m.group(0), reason="wzorzec e-mail"))
    for m in _PHONE.finditer(text):
        spans.append(PiiSpan(m.start(), m.end(), "TELEFON", m.group(0), reason="wzorzec telefonu"))

    spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
    out: list[PiiSpan] = []
    last = -1
    for s in spans:
        if s.start >= last:
            out.append(s)
            last = s.end
    return out
