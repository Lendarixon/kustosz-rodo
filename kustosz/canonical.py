"""Normalizacja Unicode i czyszczenie artefaktów PDF/OCR (homoglify, znaki zerowej szerokości)."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad\u180e\u2061\u2062\u2063\u2064"), None)
_ODD_SPACES = {ord(c): " " for c in "\u00a0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000"}
_FULLWIDTH = {cp: cp - 0xFEE0 for cp in range(0xFF01, 0xFF5F)}

_TO_LATIN = dict(zip(
    "аеорсухіјѕԁԛԝӏАВЕКМНОРСТХІЈЅԚԜοαενιρτυχκΑΒΕΖΗΙΚΜΝΟΡΤΥΧУ",
    "aeopcyxijsdqwlABEKMHOPCTXIJSQWoaeviptuxkABEZHIKMNOPTYXY",
))
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r" +([,.;:!?])")


def _script(ch: str) -> str | None:
    if "a" <= ch.lower() <= "z":
        return "LATIN"
    name = unicodedata.name(ch, "")
    for s in ("CYRILLIC", "LATIN", "GREEK"):
        if name.startswith(s):
            return s
    return None


def _fix_word(word: str) -> str:
    scripts = [s for ch in word if (s := _script(ch))]
    if not scripts:
        return word
    n_lat = scripts.count("LATIN")
    n_cyr = scripts.count("CYRILLIC")
    n_grk = scripts.count("GREEK")
    if n_lat and (n_cyr or n_grk):
        return "".join(_TO_LATIN.get(ch, ch) for ch in word)
    if n_cyr and not n_grk and all(ch in _TO_LATIN for ch in word):
        return "".join(_TO_LATIN[ch] for ch in word)
    return word


@dataclass
class CanonResult:
    text: str
    changed: bool = False
    counts: dict[str, int] = field(default_factory=dict)


def canonicalize(text: str) -> CanonResult:
    """Czyści znaki zerowej szerokości, nietypowe spacje i homoglify z PDF/kopiowania."""
    if not text:
        return CanonResult(text or "")
    counts: dict[str, int] = {}
    t = text.translate(_ZERO_WIDTH)
    if len(text) != len(t):
        counts["zero_width"] = len(text) - len(t)
    t2 = t.translate(_ODD_SPACES).translate(_FULLWIDTH)
    odd = sum(a != b for a, b in zip(t, t2))
    if odd:
        counts["odd_spaces"] = odd
    t = t2

    n_homo = 0

    def repl(m: re.Match) -> str:
        nonlocal n_homo
        w = m.group(0)
        f = _fix_word(w)
        if f != w:
            n_homo += 1
        return f

    t = _WORD.sub(repl, t)
    if n_homo:
        counts["homoglyphs"] = n_homo

    lines = t.split("\n")
    fixed = [_SPACE_BEFORE_PUNCT.sub(r"\1", _MULTI_SPACE.sub(" ", ln)) for ln in lines]
    n_space = sum(a != b for a, b in zip(lines, fixed))
    if n_space and (counts or len(_MULTI_SPACE.findall(t)) + len(_SPACE_BEFORE_PUNCT.findall(t)) >= 5):
        t = "\n".join(fixed)
        counts["extra_spaces"] = n_space

    return CanonResult(t, t != text, counts)
