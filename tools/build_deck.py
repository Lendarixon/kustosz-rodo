"""Generuje 7-slajdową prezentację PDF (16:9) dla Kustosz RODO za pomocą headless Brave."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "tools" / "_deck.html"
PDF_PATH = ROOT / "Kustosz_RODO_Prezentacja.pdf"
BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")

DECK_HTML = r"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Linda Kustosz RODO — Prezentacja</title>
<style>
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  background: #0a0c11;
  color: #eceff4;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.slide {
  width: 1280px;
  height: 720px;
  padding: 54px 68px;
  position: relative;
  overflow: hidden;
  page-break-after: always;
  background:
    radial-gradient(780px 440px at 90% -10%, rgba(47,111,230,0.22), transparent 65%),
    radial-gradient(640px 400px at -5% 110%, rgba(47,191,143,0.12), transparent 65%),
    #0a0c11;
  display: flex;
  flex-direction: column;
}
.slide:last-child { page-break-after: auto; }
.tag {
  display: inline-block;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #5b8ff0;
  background: rgba(47,111,230,0.16);
  border: 1px solid rgba(91,143,240,0.35);
  padding: 6px 14px;
  border-radius: 999px;
  align-self: flex-start;
  margin-bottom: 18px;
}
h1 { font-size: 56px; font-weight: 300; line-height: 1.1; margin: 0 0 18px; letter-spacing: -0.02em; }
h1 b { font-weight: 600; color: #5b8ff0; }
h2 { font-size: 36px; font-weight: 500; margin: 0 0 24px; letter-spacing: -0.01em; }
p.lead { font-size: 22px; color: #b4bac6; line-height: 1.5; max-width: 960px; margin: 0 0 28px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; flex: 1; align-items: stretch; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; flex: 1; align-items: stretch; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-top: 8px; }
.card {
  background: rgba(20,23,31,0.85);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px;
  padding: 24px 26px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.card.hi { border-color: rgba(91,143,240,0.5); background: rgba(47,111,230,0.1); }
.card.ok { border-color: rgba(47,191,143,0.45); background: rgba(47,191,143,0.08); }
.card h3 { margin: 0; font-size: 20px; color: #ffffff; }
.card p, .card li { margin: 0; font-size: 16.5px; color: #b4bac6; line-height: 1.5; }
.card ul { margin: 6px 0 0 18px; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.stat { font-size: 46px; font-weight: 700; color: #5b8ff0; line-height: 1.1; }
.stat.ok { color: #2fbf8f; }
.step-num { font-size: 13px; font-weight: 700; color: #5b8ff0; text-transform: uppercase; letter-spacing: 0.06em; }
table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 18px; }
th, td { padding: 15px 18px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
th { color: #8e97a8; font-weight: 600; font-size: 15px; text-transform: uppercase; letter-spacing: 0.04em; }
tr.best td { background: rgba(47,191,143,0.1); color: #ffffff; font-weight: 600; }
.pill-row { display: flex; gap: 14px; flex-wrap: wrap; margin-top: auto; }
.link-box {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 22px;
  border-radius: 12px;
  background: rgba(47,111,230,0.18);
  border: 1px solid rgba(91,143,240,0.5);
  color: #9fc0ff;
  text-decoration: none;
  font-size: 18px;
  font-weight: 600;
}
.link-box.green { background: rgba(47,191,143,0.15); border-color: rgba(47,191,143,0.5); color: #7ef0c7; }
.foot {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex;
  justify-content: space-between;
  font-size: 13.5px;
  color: #8e97a8;
}
code { font-family: Consolas, monospace; background: rgba(255,255,255,0.08); padding: 2px 7px; border-radius: 5px; color: #dbeafe; }
</style>
</head>
<body>

<!-- SLAJD 1 -->
<section class="slide">
  <span class="tag">Bielik Awards 2026 · Kategoria: Najlepsze użycie modelu SLM (&lt;10B)</span>
  <h1>Linda <b>Kustosz RODO</b></h1>
  <p class="lead">
    Lokalny (100% offline) firewall prywatności RODO dla polskich dokumentów PDF, DOCX i skanów.
    Rozróżnia dane osób prywatnych od kontekstu publicznego i prawnego, fizycznie wycina tekst z PDF i zachowuje pełną kontrolę on-device.
  </p>
  <div class="grid3" style="max-height:190px;flex:0;">
    <div class="card hi"><div class="stat">96,7%</div><p>wykrytych danych wrażliwych (100% kontekstowych encji RODO)</p></div>
    <div class="card ok"><div class="stat ok">0,0%</div><p>błędnych zamazań sędziów, urzędów i artykułów ustaw</p></div>
    <div class="card"><div class="stat">1,1 s</div><p>czas analizy dokumentu (Gemma-4-E4B, 0 zł kosztów chmury)</p></div>
  </div>
  <div class="pill-row" style="margin-top:26px;">
    <a class="link-box green" href="https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run">Demo online (Modal T4): ninjagovlad--kustosz-rodo-demo…modal.run</a>
    <a class="link-box" href="https://github.com/Lendarixon/kustosz-rodo">GitHub + Instalator: github.com/Lendarixon/kustosz-rodo</a>
  </div>
  <div class="foot"><span>Linda Kustosz RODO · Open Source (Apache-2.0)</span><span>Slajd 1 / 7</span></div>
</section>

<!-- SLAJD 2 -->
<section class="slide">
  <span class="tag">Problem w organizacjach</span>
  <h2>Dlaczego chmura i zwykłe reguły nie wystarczają?</h2>
  <div class="grid2">
    <div class="card">
      <h3>1. Bariera RODO (art. 25 i 32)</h3>
      <ul>
        <li>Urzędy (BIP), sądy, kadry, przychodnie i kancelarie codziennie muszą anonimizować decyzje, wezwania, umowy i zwolnienia przed publikacją lub wysyłką.</li>
        <li>Wysłanie surowego dokumentu do chmurowego LLM (ChatGPT, Copilot) samo w sobie narusza tajemnicę zawodową i RODO.</li>
        <li>Brak lokalnych narzędzi z obsługą polskich plików PDF/DOCX i zachowaniem formatowania.</li>
      </ul>
    </div>
    <div class="card hi">
      <h3>2. Porażka zwykłych regexów i prostego NER</h3>
      <ul>
        <li>Wyrażenia regularne wykrywają jedynie <b>33,3%</b> danych (PESEL, NIP, IBAN, e-mail), ale są ślepe na polską fleksję (<i>„Panią Annę Zielińską”</i>) i prywatne adresy.</li>
        <li>Klasyczny NER zamazuje <b>wszystkie</b> nazwiska jak leci — niszcząc w BIP nazwisko sędziego, burmistrza albo pełnomocnika publicznego.</li>
        <li>Proste reguły nie rozpoznają też nieformalnych danych wrażliwych, np. diagnoz medycznych w pismach kadrowych.</li>
      </ul>
    </div>
  </div>
  <div class="foot"><span>Kontekst wdrożenia: BIP, kancelarie, kadry, sądy</span><span>Slajd 2 / 7</span></div>
</section>

<!-- SLAJD 3 -->
<section class="slide">
  <span class="tag">Architektura on-device</span>
  <h2>4-warstwowy potok bez wychodzenia danych poza komputer</h2>
  <div class="grid4" style="flex:1;">
    <div class="card">
      <span class="step-num">Warstwa 1</span>
      <h3>Ekstrakcja i kanonizacja</h3>
      <p>Odczyt PDF (PyMuPDF), DOCX, TXT oraz skanów (Tesseract OCR <code>pol+eng</code>). Czyszczenie znaków zerowej szerokości i homogliów z uszkodzonych PDF.</p>
    </div>
    <div class="card">
      <span class="step-num">Warstwa 2</span>
      <h3>Sumy kontrolne</h3>
      <p>Deterministyczna walidacja <code>PESEL</code>, <code>NIP</code>, <code>REGON</code>, <code>IBAN</code>, dowodu osobistego, e-mail i telefonu. Pre-maskowanie przed przekazaniem do SLM.</p>
    </div>
    <div class="card hi">
      <span class="step-num">Warstwa 3</span>
      <h3>Klasyfikator SLM (&lt;10B)</h3>
      <p>Lokalny <b>Gemma-4-E4B-it</b> lub <b>Bielik-4.5B-v3</b> w <code>llama.cpp</code> rozdziela prywatne <code>OSOBA / ADRES / WRAZLIWE</code> od publicznych <code>URZEDNIK / INSTYTUCJA / PRZEPIS</code>.</p>
    </div>
    <div class="card ok">
      <span class="step-num">Warstwa 4</span>
      <h3>Fizyczna redakcja i Sejf</h3>
      <p><code>apply_redactions()</code> trwale usuwa tekst ze strumienia PDF; w DOCX podmienia treść w tabelach i akapitach. Tryb odwracalny + audyt SHA-256.</p>
    </div>
  </div>
  <div class="foot"><span>Zero ruchu sieciowego po instalacji · pełna praca offline</span><span>Slajd 3 / 7</span></div>
</section>

<!-- SLAJD 4 -->
<section class="slide">
  <span class="tag">Bezpieczeństwo i brak halucynacji</span>
  <h2>SLM jako precyzyjny wskaźnik, nie edytor tekstu</h2>
  <div class="grid2">
    <div class="card">
      <h3>Dlaczego model nie przepisuje dokumentu?</h3>
      <ul>
        <li>Pozwolenie małemu modelowi na przepisanie całej umowy lub decyzji grozi zmianą kwoty, daty albo paragrafu.</li>
        <li>W Kustosz RODO model SLM zwraca <b>wyłącznie strukturę NDJSON</b> z dokładnymi podciągami do ukrycia lub zachowania.</li>
        <li>Kod w Pythonie sprawdza, czy wskazany fragment istnieje <b>dosłownie</b> w tekście źródłowym i nie koliduje z listą <code>keep</code> (urzędnicy, przepisy).</li>
      </ul>
    </div>
    <div class="card ok">
      <h3>Prawdziwa redakcja pliku + Sejf kancelarii</h3>
      <ul>
        <li><b>Tryb BIP / Chmura:</b> fizyczne usunięcie danych z warstwy tekstowej PDF (czarne paski) lub <code>[OSOBA]</code> w DOCX.</li>
        <li><b>Tryb Odwracalny (Pseudonimizacja):</b> zamiana na spójne tokeny <code>&lt;OSOBA_1&gt;</code>, <code>&lt;PESEL_1&gt;</code> z lokalną tabelą mapowań, co pozwala bezpiecznie przekazać tekst np. do analizy i przywrócić oryginał po powrocie.</li>
        <li><b>Audyt:</b> podgląd kolorowy decyzji (Suma / SLM / Zachowano) oraz skróty <code>SHA-256</code> wejścia i wyjścia.</li>
      </ul>
    </div>
  </div>
  <div class="foot"><span>Ochrona integralności treści prawnej</span><span>Slajd 4 / 7</span></div>
</section>

<!-- SLAJD 5 -->
<section class="slide">
  <span class="tag">Ewaluacja i porównanie SLM</span>
  <h2>Wyniki na 12 polskich dokumentach (30 PII + 21 encji kontekstu)</h2>
  <div class="card" style="flex:1;justify-content:center;">
    <table>
      <thead>
        <tr>
          <th>Konfiguracja potoku</th>
          <th>Wykryte PII (Recall)</th>
          <th>Błędne zamazania kontekstu</th>
          <th>Czas / dokument</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Tylko wyrażenia regularne + sumy kontrolne</td>
          <td>33,3% (10 / 30)</td>
          <td>0,0% (0 / 21)</td>
          <td>&lt; 1 ms</td>
        </tr>
        <tr>
          <td>Kustosz RODO + <b>Bielik-4.5B-v3 Q6_K</b> (naprawiony tokenizer)</td>
          <td>90,0% (27 / 30)</td>
          <td>4,8% (1 / 21)</td>
          <td>2,9 s (GPU Vulkan) · 29,0 s (CPU)</td>
        </tr>
        <tr class="best">
          <td>Kustosz RODO + <b>Gemma-4-E4B-it Q6_K</b> (domyślny)</td>
          <td>96,7% (29 / 30)</td>
          <td>0,0% (0 / 21)</td>
          <td>1,1 s (GPU Vulkan)</td>
        </tr>
      </tbody>
    </table>
    <p style="margin-top:20px;font-size:16px;color:#b4bac6;">
      * Jedyny nieoznaczony element u Gemmy (<code>85051200238</code>) był celowo niepoprawnym numerem PESEL niespełniającym sumy kontrolnej —
      skuteczność wykrywania kontekstowych danych osobowych (imiona w odmianie, adresy, diagnozy) wyniosła <b>100%</b> przy zerowych stratach na artykułach ustaw i nazwiskach sędziów/urzędników.
    </p>
  </div>
  <div class="foot"><span>Reprodukowalny skrypt ewaluacji: bench/eval_rodo.py</span><span>Slajd 5 / 7</span></div>
</section>

<!-- SLAJD 6 -->
<section class="slide">
  <span class="tag">Dojrzałość i łatwość wdrożenia</span>
  <h2>Gotowy instalator jednym kliknięciem i ustawienia</h2>
  <div class="grid2">
    <div class="card">
      <h3>Wdrożenie lokalne (Windows / Linux)</h3>
      <ul>
        <li>Skrypt <code>install.bat</code> / <code>install.sh</code> automatycznie pobiera zależności Pythona, najnowszą binarkę <code>llama.cpp</code> (Vulkan GPU / CPU) oraz model <code>Gemma-4-E4B-it-Q6_K.gguf</code> z weryfikacją sumy <b>SHA-256</b>.</li>
        <li>Konfiguracja zapisuje się w <code>%LOCALAPPDATA%\KustoszRODO\config.json</code> i jest dostępna z poziomu okna <b>Ustawienia</b> w interfejsie WWW (wybór modelu Gemma/Bielik, GPU/CPU, wątki).</li>
        <li>Wbudowane 4 gotowe polskie dokumenty testowe (<code>decyzja_BIP.pdf</code>, <code>zwolnienie_kadry.docx</code>, <code>wezwanie_sad.pdf</code>, <code>umowa_zlecenie.docx</code>).</li>
      </ul>
    </div>
    <div class="card hi">
      <h3>Uczciwe ograniczenia i dalsze kroki</h3>
      <ul>
        <li><b>Status:</b> działający prototyp z publicznym demem i instalatorem — bez wdrożenia produkcyjnego u zewnętrznego klienta (KPI organizacyjne do zebrania w pilotażu).</li>
        <li><b>Wydajność CPU:</b> na laptopie bez karty graficznej pełna analiza trwa ok. 20–35 s/dokument; na karcie GPU 1–3 s.</li>
        <li><b>Kierunek rozwoju:</b> szyfrowany magazyn lokalnego sejfu na dysku oraz lekka LoRA pod specyficzne rejestry (KRS, księgi wieczyste).</li>
      </ul>
    </div>
  </div>
  <div class="foot"><span>Licencja kodu: Apache-2.0 · Zero opłat API</span><span>Slajd 6 / 7</span></div>
</section>

<!-- SLAJD 7 -->
<section class="slide">
  <span class="tag">Sprawdź na żywo</span>
  <h2>Linki do dema i repozytorium</h2>
  <p class="lead">
    Cały projekt jest publiczny, gotowy do przetestowania w przeglądarce (Modal T4 GPU) oraz do uruchomienia lokalnie na własnym komputerze jednym poleceniem.
  </p>
  <div class="grid2" style="max-height:260px;flex:0;">
    <div class="card ok">
      <h3>Publiczne demo produktu (Modal T4)</h3>
      <p>Wgraj własny plik PDF / DOCX lub kliknij jeden z 4 polskich dokumentów przykładowych i pobierz zanonimizowany plik:</p>
      <a class="link-box green" style="margin-top:auto;" href="https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run">
        Otwórz demo Kustosz RODO →
      </a>
    </div>
    <div class="card hi">
      <h3>Kod źródłowy, testy i instalator (GitHub)</h3>
      <p>Pełny kod w Pythonie, skrypt instalacyjny <code>install.bat</code>, testy jednostkowe <code>pytest</code> oraz benchmark <code>eval_rodo.py</code>:</p>
      <a class="link-box" style="margin-top:auto;" href="https://github.com/Lendarixon/kustosz-rodo">
        github.com/Lendarixon/kustosz-rodo →
      </a>
    </div>
  </div>
  <div class="foot"><span>Dziękujemy za uwagę · Bielik Awards 2026</span><span>Slajd 7 / 7</span></div>
</section>

</body>
</html>
"""


def main():
    HTML_PATH.write_text(DECK_HTML, encoding="utf-8")
    subprocess.run([
        str(BRAVE),
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH.as_uri(),
    ], check=True)
    HTML_PATH.unlink(missing_ok=True)
    print("Wygenerowano:", PDF_PATH, PDF_PATH.stat().st_size, "bajtów")


if __name__ == "__main__":
    main()
