"""Kontekstowy klasyfikator RODO oparty o lokalny model Bielik-4.5B-v3 (llama.cpp)."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

SYSTEM_PROMPT = """Jesteś lokalnym strażnikiem RODO (Kustosz RODO) dla polskich dokumentów urzędowych, sądowych i kadrowych.
Przeanalizuj tekst i wypisz encje w formacie JSON Lines (jeden obiekt JSON w każdej linii), kopiując `text` DOKŁADNIE słowo w słowo z tekstu źródłowego (w tej samej formie gramatycznej!).

Kategorie do ZAMASKOWANIA (`label`):
- `OSOBA`: imię i nazwisko osoby prywatnej (wnioskodawca, świadek, pracownik, pacjent, klient, dłużnik), bez tytułu typu "Pan/Pani/świadek".
- `ADRES`: prywatny adres zamieszkania (ulica, numer, kod, miejscowość).
- `WRAZLIWE`: dane o zdrowiu/chorobie, diagnozie lub zarobkach konkretnej osoby.

Kategorie do ZACHOWANIA (`label`):
- `URZEDNIK`: osoba pełniąca funkcję publiczną (sędzia, burmistrz, wójt, naczelnik, komornik, wojewoda) wraz z tytułem.
- `INSTYTUCJA`: nazwa sądu, urzędu, ministerstwa, firmy.
- `PRZEPIS`: numer artykułu, ustawy, sygnatura akt.

Przykład:
Tekst: "Na podst. art. 10 KPA Sędzia Jan Nowak wzywa Annę Kos (ul. Miła 2, Łódź)."
Wynik:
{"text": "art. 10 KPA", "label": "PRZEPIS", "reason": "podstawa prawna"}
{"text": "Sędzia Jan Nowak", "label": "URZEDNIK", "reason": "funkcjonariusz publiczny"}
{"text": "Annę Kos", "label": "OSOBA", "reason": "osoba prywatna"}
{"text": "ul. Miła 2, Łódź", "label": "ADRES", "reason": "adres prywatny"}

Zasady:
- Pomijaj tokeny typu <PESEL_1>, <NIP_1> — są już zamaskowane.
- Zwróć wyłącznie linie JSON, bez komentarzy."""

_REDACT_LABELS = {"OSOBA", "ADRES", "WRAZLIWE"}
_KEEP_LABELS = {"URZEDNIK", "INSTYTUCJA", "PRZEPIS"}


@dataclass
class SlmFinding:
    text: str
    kind: str
    reason: str


@dataclass
class SlmKeep:
    text: str
    role: str


@dataclass
class SlmResult:
    redact: list[SlmFinding] = field(default_factory=list)
    keep: list[SlmKeep] = field(default_factory=list)
    raw_json: str = ""
    latency_ms: int = 0


def _parse_slm_output(raw: str) -> tuple[list[SlmFinding], list[SlmKeep]]:
    redacts: list[SlmFinding] = []
    keeps: list[SlmKeep] = []
    decoder = json.JSONDecoder()
    pos = 0
    n = len(raw)

    while pos < n:
        idx = raw.find("{", pos)
        if idx == -1:
            break
        try:
            obj, end = decoder.raw_decode(raw, idx)
            pos = end
        except json.JSONDecodeError:
            pos = idx + 1
            continue
        if not isinstance(obj, dict):
            continue

        # Obsługa formatu {"redact": [...], "keep": [...]}
        if "redact" in obj or "keep" in obj:
            for item in obj.get("redact", []):
                t = (item.get("text") or "").strip()
                if t and not (t.startswith("<") and t.endswith(">")):
                    redacts.append(SlmFinding(t, item.get("type", "OSOBA"), item.get("reason", "")))
            for item in obj.get("keep", []):
                t = (item.get("text") or "").strip()
                if t:
                    keeps.append(SlmKeep(t, item.get("role", "PRZEPIS")))
            continue

        # Obsługa formatu NDJSON {"text": ..., "label"|"type"|"role": ...}
        t = (obj.get("text") or "").strip()
        if not t or (t.startswith("<") and t.endswith(">")):
            continue
        lbl = (obj.get("label") or obj.get("type") or obj.get("role") or "").upper().strip()
        if lbl in _REDACT_LABELS:
            redacts.append(SlmFinding(t, lbl, obj.get("reason", "")))
        elif lbl in _KEEP_LABELS:
            keeps.append(SlmKeep(t, lbl))

    return redacts, keeps


def classify_chunk(text: str, llama_url: str = "http://127.0.0.1:8792", timeout: int = 180) -> SlmResult:
    """Wywołuje lokalny serwer llama.cpp (Bielik-4.5B) do klasyfikacji kontekstowej RODO."""
    import time
    t0 = time.perf_counter()
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Tekst:\n{text}\nWynik:"},
        ],
        "temperature": 0.0,
        "max_tokens": 550,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    req = urllib.request.Request(
        f"{llama_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    redacts, keeps = _parse_slm_output(content)
    ms = int((time.perf_counter() - t0) * 1000)
    return SlmResult(redact=redacts, keep=keeps, raw_json=content, latency_ms=ms)
