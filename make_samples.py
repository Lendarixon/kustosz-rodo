"""Generuje realistyczne polskie dokumenty PDF i DOCX do testów Kustosz RODO."""
from __future__ import annotations

from pathlib import Path
import docx
import fitz

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"


def _make_pdf(filename: str, title: str, subtitle: str, paragraphs: list[str], footer: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    page.insert_font(fontname="ar", fontfile=FONT_REG)
    page.insert_font(fontname="arb", fontfile=FONT_BOLD)

    y = 56
    page.insert_text((50, y), subtitle, fontname="ar", fontsize=10, color=(0.35, 0.38, 0.45))
    y += 24
    page.insert_text((50, y), title, fontname="arb", fontsize=16, color=(0.08, 0.1, 0.16))
    y += 12
    page.draw_line((50, y), (545, y), color=(0.2, 0.4, 0.8), width=1.2)
    y += 26

    for p in paragraphs:
        rect = fitz.Rect(50, y, 545, y + 180)
        rc = page.insert_textbox(rect, p, fontname="ar", fontsize=11, lineheight=1.45, color=(0.1, 0.1, 0.12))
        # Przybliżona wysokość zajęta przez akapit
        lines = max(1, len(p) // 75 + p.count("\n") + 1)
        y += lines * 17 + 12

    page.draw_line((50, 770), (545, 770), color=(0.8, 0.82, 0.86), width=0.8)
    page.insert_text((50, 790), footer, fontname="ar", fontsize=9.5, color=(0.4, 0.42, 0.48))
    doc.save(SAMPLES_DIR / filename)


def _make_docx_hr(filename: str) -> None:
    doc = docx.Document()
    doc.add_heading("NOTATKA KADROWA — ZUS / ZWOLNIENIE LEKARSKIE", level=1)
    doc.add_paragraph("Wrocław, dnia 12 listopada 2026 r. | Znak sprawy: KAD/2026/114")
    doc.add_paragraph(
        "Dział Kadr informuje, że poniżej wskazany pracownik przebywa na zwolnieniu lekarskim "
        "z powodu ostrego zapalenia oskrzeli oraz powikłań oddechowych od dnia 02.11.2026 r. "
        "Podstawa naliczenia wynagrodzenia chorobowego: art. 92 Kodeksu pracy."
    )
    tbl = doc.add_table(rows=5, cols=2)
    tbl.style = "Table Grid"
    rows = [
        ("Pracownik", "Tomasz Wiśniewski"),
        ("PESEL", "85051200234"),
        ("Rachunek bankowy (IBAN)", "PL61109010140000071219812874"),
        ("Kontakt prywatny", "t.wisniewski@poczta.pl, tel. +48 600 700 800"),
        ("Adres zamieszkania", "ul. Grabiszyńska 45/8, 53-501 Wrocław"),
    ]
    for i, (k, v) in enumerate(rows):
        tbl.cell(i, 0).text = k
        tbl.cell(i, 1).text = v
    doc.add_paragraph("")
    doc.add_paragraph("Zatwierdził: Kierownik Działu Kadr, Urząd Miejski we Wrocławiu.")
    doc.save(SAMPLES_DIR / filename)


def _make_docx_contract(filename: str) -> None:
    doc = docx.Document()
    doc.add_heading("UMOWA ZLECENIE nr 18/2026", level=1)
    doc.add_paragraph("Zawarta w Warszawie w dniu 10 października 2026 r. na podstawie art. 734 Kodeksu cywilnego.")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.style = "Table Grid"
    tbl.cell(0, 0).text = "Zleceniodawca"
    tbl.cell(0, 1).text = "Alfa Sp. z o.o., ul. Marszałkowska 10, Warszawa, NIP 5260250995"
    tbl.cell(1, 0).text = "Zleceniobiorca"
    tbl.cell(1, 1).text = "Marek Kamiński, dowód ABC 123456, zam. ul. Polna 5, 00-001 Warszawa"
    doc.add_paragraph("")
    doc.add_paragraph(
        "§ 1. Zleceniobiorca zobowiązuje się do wykonania audytu dokumentacji technicznej. "
        "Wynagrodzenie wynosi 4500 zł brutto i zostanie wypłacone na wskazany rachunek po odbiorze prac."
    )
    doc.save(SAMPLES_DIR / filename)


def main():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    _make_pdf(
        "decyzja_BIP.pdf",
        "DECYZJA ADMINISTRACYJNA nr 42/2026",
        "Urząd Miasta Oleśnicy · Biuletyn Informacji Publicznej · Wersja przed anonimizacją",
        [
            "Oleśnica, dnia 14 listopada 2026 r.\nZnak sprawy: OPS.4120.42.2026",
            "Na podstawie art. 104 Kodeksu postępowania administracyjnego oraz art. 39 ustawy o pomocy społecznej, "
            "Burmistrz Miasta Oleśnicy Janusz Marek Kowalczyk, po rozpatrzeniu wniosku złożonego przez Panią Annę Zielińską "
            "(PESEL 90010100191, zam. ul. Słoneczna 14/3, 56-400 Oleśnica, tel. 601 202 303),",
            "ORZEKA:\nOdmawia się przyznania zasiłku celowego wnioskodawczyni z uwagi na przekroczenie kryterium dochodowego.",
            "UZASADNIENIE:\nW toku postępowania ustalono, że Pani Anna Zielińska zamieszkuje pod adresem ul. Słoneczna 14/3, 56-400 Oleśnica. "
            "Od niniejszej decyzji służy odwołanie do Samorządowego Kolegium Odwoławczego we Wrocławiu w terminie 14 dni (art. 129 KPA).",
        ],
        "Podpisano elektronicznie: Burmistrz Miasta Oleśnicy Janusz Marek Kowalczyk",
    )
    _make_pdf(
        "wezwanie_sad.pdf",
        "WEZWANIE NA ROZPRAWĘ (SYGN. AKT II C 418/26)",
        "Sąd Rejonowy dla Wrocławia-Śródmieścia · II Wydział Cywilny",
        [
            "Wrocław, dnia 10 listopada 2026 r.",
            "Sąd Rejonowy dla Wrocławia-Śródmieścia, Sędzia Katarzyna Majewska, na podstawie art. 258 Kodeksu postępowania cywilnego "
            "wzywa Pana Piotra Nowaka (zam. al. Hallera 88 m. 12, 53-324 Wrocław, tel. 502 303 404) do osobistego stawiennictwa w charakterze świadka.",
            "Termin posiedzenia wyznaczono na dzień 20 listopada 2026 r. o godz. 10:30 w sali nr 14 budynku Sądu przy ul. Podwale 30.",
            "Pouczenie: Nieusprawiedliwione niestawiennictwo świadka może skutkować nałożeniem grzywny zgodnie z art. 274 KPC.",
        ],
        "Zarządzenie wydał: Sędzia Katarzyna Majewska · Sąd Rejonowy dla Wrocławia-Śródmieścia",
    )
    _make_docx_hr("zwolnienie_kadry.docx")
    _make_docx_contract("umowa_zlecenie.docx")
    print("Wygenerowano 4 dokumenty w:", SAMPLES_DIR)


if __name__ == "__main__":
    main()
