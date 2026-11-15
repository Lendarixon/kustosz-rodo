"""Główny potok anonimizacji: kanonizacja -> walidacja sum kontrolnych -> Bielik-4.5B -> raport."""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field

from .canonical import canonicalize
from .pii import PiiSpan, find_deterministic
from .slm_ner import SlmKeep, classify_chunk


@dataclass
class RedactionItem:
    start: int
    end: int
    kind: str
    original: str
    token: str
    source: str  # "deterministic" | "bielik-4.5b"
    reason: str


@dataclass
class PipelineReport:
    original_text: str
    canonical_text: str
    masked_text: str
    mode: str  # "irreversible" | "reversible"
    canon_counts: dict[str, int] = field(default_factory=dict)
    redactions: list[RedactionItem] = field(default_factory=list)
    kept: list[SlmKeep] = field(default_factory=list)
    vault: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    doc_sha256: str = ""
    masked_sha256: str = ""
    slm_latency_ms: int = 0
    highlighted_html: str = ""


def _chunk_text(text: str, max_chars: int = 1800) -> list[tuple[int, str]]:
    """Dzieli tekst na fragmenty po akapitach, zwracając (offset, fragment)."""
    if len(text) <= max_chars:
        return [(0, text)]
    chunks: list[tuple[int, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        end = min(pos + max_chars, n)
        if end < n:
            split_at = text.rfind("\n\n", pos + 400, end)
            if split_at == -1:
                split_at = text.rfind("\n", pos + 400, end)
            if split_at == -1:
                split_at = text.rfind(". ", pos + 400, end)
                if split_at != -1:
                    split_at += 1
            if split_at > pos:
                end = split_at
        chunks.append((pos, text[pos:end]))
        pos = end
    return chunks


def _apply_pre_mask(text: str, spans: list[PiiSpan]) -> tuple[str, list[tuple[int, int, str]]]:
    """Podmienia deterministyczne PII na <TYP_N> przed wysłaniem do SLM."""
    out = []
    pos = 0
    counters: dict[str, int] = {}
    token_map: list[tuple[int, int, str]] = []
    for s in spans:
        out.append(text[pos:s.start])
        counters[s.kind] = counters.get(s.kind, 0) + 1
        tok = f"<{s.kind}_{counters[s.kind]}>"
        out.append(tok)
        token_map.append((s.start, s.end, tok))
        pos = s.end
    out.append(text[pos:])
    return "".join(out), token_map


def _build_highlighted_html(text: str, redactions: list[RedactionItem], kept: list[SlmKeep]) -> str:
    """Buduje podgląd HTML: czerwony = zamaskowane SLM, niebieski = deterministyczne PII, zielony = zachowany kontekst."""
    events: list[tuple[int, int, str, str]] = []
    for r in redactions:
        cls = "pii-det" if r.source == "deterministic" else "pii-slm"
        tip = f"{r.kind} ({r.source}): {r.reason}"
        events.append((r.start, r.end, cls, tip))

    for k in kept:
        if len(k.text) < 3:
            continue
        for m in re.finditer(re.escape(k.text), text):
            a, b = m.start(), m.end()
            if not any(not (b <= ra or a >= rb) for ra, rb, _, _ in events):
                events.append((a, b, "pii-keep", f"Zachowano ({k.role})"))

    events.sort(key=lambda e: (e[0], -(e[1] - e[0])))
    filtered = []
    last = -1
    for e in events:
        if e[0] >= last:
            filtered.append(e)
            last = e[1]

    parts = []
    pos = 0
    for a, b, cls, tip in filtered:
        parts.append(html.escape(text[pos:a]))
        parts.append(f'<mark class="{cls}" title="{html.escape(tip)}">{html.escape(text[a:b])}</mark>')
        pos = b
    parts.append(html.escape(text[pos:]))
    return "".join(parts).replace("\n", "<br>")


def restore_text(masked_text: str, vault: dict[str, str]) -> str:
    """Odwraca pseudonimizację używając lokalnego sejfu tokenów."""
    res = masked_text
    for tok, orig in vault.items():
        res = res.replace(tok, orig)
    return res


def run_pipeline(
    raw_text: str,
    mode: str = "irreversible",
    use_slm: bool = True,
    llama_url: str = "http://127.0.0.1:8792",
) -> PipelineReport:
    """Wykonuje pełną anonimizację / pseudonimizację dokumentu."""
    canon = canonicalize(raw_text)
    text = canon.text
    det_spans = find_deterministic(text)

    slm_spans: list[PiiSpan] = []
    kept_all: list[SlmKeep] = []
    slm_ms = 0

    if use_slm and text.strip():
        # Pre-maskujemy deterministyczne PII, mapujemy indeksy na oryginalny `text`
        # Prościej: uruchamiamy SLM na oryginalnych chunkach? Nie — lepiej na pre-maskowanych,
        # a znalezione podciągi SLM dopasowujemy bezpośrednio w `text` (poza det_spans).
        pre_text, _ = _apply_pre_mask(text, det_spans)
        seen_keep: set[tuple[str, str]] = set()
        for _, chunk in _chunk_text(pre_text):
            if not chunk.strip():
                continue
            res = classify_chunk(chunk, llama_url=llama_url)
            slm_ms += res.latency_ms
            for k in res.keep:
                key = (k.text, k.role)
                if key not in seen_keep:
                    seen_keep.add(key)
                    kept_all.append(k)
            keep_texts = {k.text.lower() for k in res.keep}
            for f in res.redact:
                if len(f.text) < 3 or f.text.lower() in keep_texts:
                    continue
                for m in re.finditer(re.escape(f.text), text):
                    a, b = m.start(), m.end()
                    if any(not (b <= d.start or a >= d.end) for d in det_spans):
                        continue
                    slm_spans.append(PiiSpan(a, b, f.kind, text[a:b], source="bielik-4.5b", reason=f.reason))

    all_spans = det_spans + slm_spans
    all_spans.sort(key=lambda s: (s.start, 0 if s.source == "deterministic" else 1, -(s.end - s.start)))

    merged: list[PiiSpan] = []
    last = -1
    for s in all_spans:
        if s.start >= last:
            merged.append(s)
            last = s.end

    # Budowa wyniku i sejfu
    counters: dict[str, int] = {}
    val_to_tok: dict[tuple[str, str], str] = {}
    vault: dict[str, str] = {}
    redactions: list[RedactionItem] = []
    counts: dict[str, int] = {}
    out_parts: list[str] = []
    pos = 0

    for s in merged:
        out_parts.append(text[pos:s.start])
        counts[s.kind] = counts.get(s.kind, 0) + 1
        if mode == "reversible":
            key = (s.kind, s.value)
            if key not in val_to_tok:
                counters[s.kind] = counters.get(s.kind, 0) + 1
                tok = f"<{s.kind}_{counters[s.kind]}>"
                val_to_tok[key] = tok
                vault[tok] = s.value
            tok = val_to_tok[key]
        else:
            tok = f"[{s.kind}]"
        out_parts.append(tok)
        redactions.append(RedactionItem(s.start, s.end, s.kind, s.value, tok, s.source, s.reason))
        pos = s.end
    out_parts.append(text[pos:])
    masked_text = "".join(out_parts)

    return PipelineReport(
        original_text=raw_text,
        canonical_text=text,
        masked_text=masked_text,
        mode=mode,
        canon_counts=canon.counts,
        redactions=redactions,
        kept=kept_all,
        vault=vault,
        counts=counts,
        doc_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        masked_sha256=hashlib.sha256(masked_text.encode("utf-8")).hexdigest(),
        slm_latency_ms=slm_ms,
        highlighted_html=_build_highlighted_html(text, redactions, kept_all),
    )
