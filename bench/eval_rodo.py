"""Ewaluacja Kustosz RODO (Regex-only vs Regex + Bielik-4.5B) na 20 polskich przypadkach."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import start_llama, stop_llama
from kustosz.pipeline import run_pipeline

CASES = [
    {
        "id": "bip_1",
        "cat": "BIP",
        "text": "Na podstawie art. 104 KPA Burmistrz Oleśnicy Janusz Kowalczyk po wniosku Anny Zielińskiej (PESEL 90010100191, zam. ul. Słoneczna 14/3, Oleśnica) odmawia zasiłku.",
        "must_mask": ["Anny Zielińskiej", "90010100191", "ul. Słoneczna 14/3, Oleśnica"],
        "must_keep": ["art. 104 KPA", "Burmistrz Oleśnicy"],
    },
    {
        "id": "sad_1",
        "cat": "Sąd",
        "text": "Sąd Rejonowy we Wrocławiu, sygn. II C 418/26. Sędzia Katarzyna Majewska wzywa świadka Piotra Nowaka, zam. al. Hallera 88 m. 12, Wrocław, na podstawie art. 258 KPC.",
        "must_mask": ["Piotra Nowaka", "al. Hallera 88 m. 12, Wrocław"],
        "must_keep": ["art. 258 KPC", "Sąd Rejonowy we Wrocławiu", "Sędzia Katarzyna Majewska"],
    },
    {
        "id": "kadry_1",
        "cat": "Kadry",
        "text": "Pracownik Tomasz Wiśniewski (PESEL 85051200238, konto PL61109010140000071219812874, e-mail t.wisniewski@poczta.pl) przebywa na zwolnieniu z powodu astmy oskrzelowej wg art. 92 KP.",
        "must_mask": ["Tomasz Wiśniewski", "85051200238", "PL61109010140000071219812874", "t.wisniewski@poczta.pl", "astmy oskrzelowej"],
        "must_keep": ["art. 92 KP"],
    },
    {
        "id": "umowa_1",
        "cat": "Umowa",
        "text": "Zleceniodawca: Alfa Sp. z o.o., NIP 5260250995. Zleceniobiorca: Marek Kamiński, tel. +48 601 202 303, zam. ul. Polna 5, 00-001 Warszawa. Wynagrodzenie wg art. 734 KC.",
        "must_mask": ["Marek Kamiński", "+48 601 202 303", "ul. Polna 5, 00-001 Warszawa"],
        "must_keep": ["art. 734 KC"],
    },
    {
        "id": "homo_1",
        "cat": "Brudny PDF",
        "text": "Wnioskodawca M\u200bаrek Кowаlski (PESEL 90010100191) złożył skargę na podstawie art. 227 KPA do Wojewody Dolnośląskiego.",
        "must_mask": ["Marek Kowalski", "90010100191"],
        "must_keep": ["art. 227 KPA", "Wojewody Dolnośląskiego"],
    },
    {
        "id": "med_1",
        "cat": "Medycyna",
        "text": "Pacjentka Ewa Dąbrowska, zam. ul. Krótka 7, Kraków, zgłosiła się z rozpoznaniem cukrzycy typu 2. Konsultacja zgodna z art. 31 ustawy o zawodach lekarza.",
        "must_mask": ["Ewa Dąbrowska", "ul. Krótka 7, Kraków", "cukrzycy typu 2"],
        "must_keep": ["art. 31"],
    },
    {
        "id": "komornik_1",
        "cat": "Egzekucja",
        "text": "Komornik Sądowy przy Sądzie Rejonowym w Poznaniu Janusz Rybak prowadzi egzekucję wobec dłużnika Adama Kaczmarka (PESEL 78030400154) na podst. art. 796 KPC.",
        "must_mask": ["Adama Kaczmarka", "78030400154"],
        "must_keep": ["art. 796 KPC", "Sądzie Rejonowym w Poznaniu"],
    },
    {
        "id": "neg_1",
        "cat": "Kontrola negatywna",
        "text": "Zgodnie z art. 154 § 1 Kodeksu pracy wymiar urlopu wynosi 20 dni albo 26 dni. Uchwała Rady Ministrów nr 12/2025 z dnia 10 stycznia 2025 r.",
        "must_mask": [],
        "must_keep": ["art. 154 § 1 Kodeksu pracy", "Rady Ministrów"],
    },
    {
        "id": "neg_2",
        "cat": "Kontrola negatywna",
        "text": "Ministerstwo Cyfryzacji oraz Prezes Urzędu Ochrony Danych Osobowych przypominają o art. 25 i art. 32 RODO. Numer sprawy nie zawiera PESEL: 12345678901.",
        "must_mask": [],
        "must_keep": ["Ministerstwo Cyfryzacji", "art. 25", "art. 32 RODO", "12345678901"],
    },
    {
        "id": "hr_2",
        "cat": "Kadry",
        "text": "Upoważniam pracownika Karolinę Mazur (tel. 500-600-700, e-mail k.mazur@firma.pl) do odbioru akt osobowych Pani Magdaleny Wójcik, zam. ul. Leśna 9, Gdańsk.",
        "must_mask": ["Karolinę Mazur", "500-600-700", "k.mazur@firma.pl", "Magdaleny Wójcik", "ul. Leśna 9, Gdańsk"],
        "must_keep": [],
    },
    {
        "id": "bip_2",
        "cat": "BIP",
        "text": "Wójt Gminy Kobierzyce Ryszard Pacholik umarza postępowanie z wniosku Pana Krzysztofa Lisieckiego, zam. ul. Kwiatowa 2, Kobierzyce, na podstawie art. 105 § 1 KPA.",
        "must_mask": ["Krzysztofa Lisieckiego", "ul. Kwiatowa 2, Kobierzyce"],
        "must_keep": ["art. 105 § 1 KPA", "Wójt Gminy Kobierzyce"],
    },
    {
        "id": "bank_1",
        "cat": "Finanse",
        "text": "Klientka Zofia Pawłowska (REGON 123456785, konto PL61109010140000071219812874) złożyła reklamację w trybie art. 6 ustawy o rozpatrywaniu reklamacji.",
        "must_mask": ["Zofia Pawłowska", "123456785", "PL61109010140000071219812874"],
        "must_keep": ["art. 6"],
    },
]


def eval_mode(use_slm: bool) -> dict:
    total_mask = 0
    hit_mask = 0
    total_keep = 0
    broken_keep = 0
    latencies = []
    details = []

    for c in CASES:
        t0 = time.perf_counter()
        rep = run_pipeline(c["text"], mode="irreversible", use_slm=use_slm)
        dt = int((time.perf_counter() - t0) * 1000)
        latencies.append(dt)
        out = rep.masked_text

        for m in c["must_mask"]:
            total_mask += 1
            if m not in out:
                hit_mask += 1
            else:
                details.append(f"[{c['id']}] MISSED MASK: {m}")

        for k in c["must_keep"]:
            total_keep += 1
            if k not in out:
                broken_keep += 1
                details.append(f"[{c['id']}] FALSE REDACT: {k}")

    recall = hit_mask / total_mask if total_mask else 1.0
    false_redact = broken_keep / total_keep if total_keep else 0.0
    avg_ms = sum(latencies) / len(latencies)
    return {
        "use_slm": use_slm,
        "cases": len(CASES),
        "mask_hit": hit_mask,
        "mask_total": total_mask,
        "recall": round(recall * 100, 1),
        "false_redact": broken_keep,
        "keep_total": total_keep,
        "false_redact_rate": round(false_redact * 100, 1),
        "avg_ms": round(avg_ms),
        "details": details,
    }


def main():
    print("1) Test Regex-only...")
    r_only = eval_mode(use_slm=False)
    print(json.dumps({k: v for k, v in r_only.items() if k != "details"}, ensure_ascii=False))

    print("2) Uruchamiam Bielik-4.5B...")
    start_llama()
    try:
        r_slm = eval_mode(use_slm=True)
    finally:
        stop_llama()

    print(json.dumps({k: v for k, v in r_slm.items() if k != "details"}, ensure_ascii=False))
    out_path = Path(__file__).resolve().parent / "eval_report.json"
    out_path.write_text(json.dumps({"regex_only": r_only, "bielik_4_5b": r_slm}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Zapisano raport: {out_path}")
    if r_slm["details"]:
        print("Uwagi:")
        for d in r_slm["details"]:
            print(" -", d)


if __name__ == "__main__":
    main()
