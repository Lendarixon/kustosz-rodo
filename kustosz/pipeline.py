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
    """Buduje podgląd HTML: czerwony = zamaskowane SLM, niebieski = deterministyczne PII, bursztynowy = własne reguły, zielony = zachowany kontekst."""
    events: list[tuple[int, int, str, str]] = []
    for r in redactions:
        if r.source == "deterministic":
            cls = "pii-det"
        elif r.source == "user":
            cls = "pii-user"
        else:
            cls = "pii-slm"
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


def _format_token(
    kind: str,
    value: str,
    mode: str,
    mask_style: str,
    custom_text: str,
    kind_replacements: dict[str, str],
    counters: dict[str, int],
    val_to_tok: dict[tuple[str, str], str],
    vault: dict[str, str],
) -> str:
    if mode == "reversible":
        key = (kind, value)
        if key not in val_to_tok:
            counters[kind] = counters.get(kind, 0) + 1
            tok = f"<{kind}_{counters[kind]}>"
            val_to_tok[key] = tok
            vault[tok] = value
        return val_to_tok[key]

    override = (kind_replacements.get(kind) or "").strip()
    if override:
        return override.replace("{TYP}", kind)
    if mask_style == "blocks":
        return "█" * min(max(len(value), 4), 14)
    if mask_style == "stars":
        return "*" * min(max(len(value), 4), 14)
    if mask_style == "custom" and custom_text.strip():
        return custom_text.strip().replace("{TYP}", kind)
    return f"[{kind}]"


def run_pipeline(
    raw_text: str,
    mode: str = "irreversible",
    use_slm: bool = True,
    llama_url: str = "http://127.0.0.1:8792",
    mask_style: str = "label",
    custom_text: str = "",
    enabled_kinds: list[str] | set[str] | None = None,
    custom_mask: list[str] | None = None,
    custom_keep: list[str] | None = None,
    kind_replacements: dict[str, str] | None = None,
) -> PipelineReport:
    """Wykonuje pełną anonimizację / pseudonimizację dokumentu."""
    canon = canonicalize(raw_text)
    text = canon.text
    det_spans = find_deterministic(text)

    enabled_set = {k.upper() for k in enabled_kinds} if enabled_kinds is not None else None
    keep_custom = {p.strip().lower() for p in (custom_keep or []) if p and p.strip()}
    mask_custom = [p.strip() for p in (custom_mask or []) if p and p.strip()]
    repl_map = {k.upper(): v for k, v in (kind_replacements or {}).items()}

    slm_spans: list[PiiSpan] = []
    kept_all: list[SlmKeep] = []
    slm_ms = 0

    if use_slm and text.strip():
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

    for term in keep_custom:
        kept_all.append(SlmKeep(term, "WYJATEK"))

    user_spans: list[PiiSpan] = []
    for term in mask_custom:
        for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            user_spans.append(PiiSpan(m.start(), m.end(), "WLASNE", text[m.start():m.end()], source="user", reason="reguła użytkownika"))

    def _allowed(s: PiiSpan) -> bool:
        val_low = s.value.strip().lower()
        if any(val_low == k or (len(k) >= 3 and k in val_low) for k in keep_custom):
            return False
        if s.source == "user":
            return True
        if enabled_set is not None and s.kind.upper() not in enabled_set:
            return False
        return True

    all_spans = [s for s in (user_spans + det_spans + slm_spans) if _allowed(s)]
    all_spans.sort(key=lambda s: (s.start, {"user": 0, "deterministic": 1}.get(s.source, 2), -(s.end - s.start)))

    merged: list[PiiSpan] = []
    last = -1
    for s in all_spans:
        if s.start >= last:
            merged.append(s)
            last = s.end

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
        tok = _format_token(s.kind, s.value, mode, mask_style, custom_text, repl_map, counters, val_to_tok, vault)
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
