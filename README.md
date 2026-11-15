# Linda Kustosz RODO

**Lokalny (100% offline) firewall prywatności RODO dla polskich dokumentów PDF, DOCX, TXT i skanów.**

- **Demo online (Modal T4 GPU):** https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run
- **Prezentacja projektu (PDF):** https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/prezentacja.pdf
- **Kod i instalator:** https://github.com/Lendarixon/kustosz-rodo

---

## Co robi Kustosz RODO

Zanim dokument trafi do BIP, kontrahenta albo zewnętrznego narzędzia AI, Kustosz RODO na Twoim komputerze:
1. **Czyści artefakty PDF/OCR** (`kustosz/canonical.py` — znaki zerowej szerokości, nietypowe spacje, homoglify).
2. **Wykrywa i waliduje sumy kontrolne** (`kustosz/pii.py` — `PESEL`, `NIP`, `REGON`, `IBAN`, `dowód osobisty`, e-mail, telefon) jeszcze przed przekazaniem tekstu do modelu.
3. **Rozróżnia kontekst prawny za pomocą SLM `<10B`** (`kustosz/slm_ner.py` — **Gemma-4-E4B-it** lub **Bielik-4.5B-v3** w `llama.cpp`):
   - maskuje dane prywatne w dowolnym przypadku gramatycznym (`OSOBA`: świadek, wnioskodawca, pacjent, pracownik; `ADRES`; `WRAZLIWE`: diagnozy);
   - **zachowuje kontekst publiczny i prawny** (`URZEDNIK`: sędzia, burmistrz, wójt; `INSTYTUCJA`: sądy, urzędy; `PRZEPIS`: `art. 104 KPA`, `art. 92 KP`).
4. **Nigdy nie przepisuje tekstu z pamięci** — model zwraca wyłącznie podciągi NDJSON, a Python weryfikuje ich dokładną obecność w dokumencie i wykonuje **fizyczną redakcję pliku**:
   - w **PDF** (`PyMuPDF` `apply_redactions()`) trwale usuwa tekst ze strumienia PDF i nakłada czarne paski / tokeny;
   - w **DOCX** podmienia dane w akapitach i tabelach z zachowaniem formatowania.
5. **Obsługuje pseudonimizację odwracalną** (`<OSOBA_1>`, `<PESEL_1>`) z lokalnym sejfem oraz generuje skróty audytowe **SHA-256**.

---

## Instalacja jednym poleceniem (Windows / Linux)

Wymagany Python 3.10+. Instalator automatycznie pobiera zależności, serwer `llama.cpp` (Vulkan GPU / CPU) oraz model `gemma-4-E4B-it-Q6_K.gguf` z weryfikacją SHA-256, po czym zapisuje domyślną konfigurację w `%LOCALAPPDATA%\KustoszRODO\config.json`.

**Windows:**
```bat
git clone https://github.com/Lendarixon/kustosz-rodo.git
cd kustosz-rodo
install.bat
```
*(Opcjonalnie z dodatkowym modelem Bielik-4.5B: `install.bat --with-bielik`)*

**Linux / macOS:**
```bash
git clone https://github.com/Lendarixon/kustosz-rodo.git
cd kustosz-rodo
chmod +x install.sh && ./install.sh
```

Po instalacji uruchamiaj przez `start.bat` lub `python app.py` (otworzy `http://127.0.0.1:8791/`). Przycisk **Ustawienia** w prawym górnym rogu pozwala przełączać model (`Gemma-4-E4B` / `Bielik-4.5B`), tryb `GPU Vulkan / CPU` i liczbę wątków.

---

## Zmienne środowiskowe (opcjonalne)

- `KUSTOSZ_MODEL=gemma|bielik` — wybór silnika SLM
- `KUSTOSZ_CPU=1` — wymuszenie trybu CPU
- `KUSTOSZ_PORT=8791` — port interfejsu WWW
- `KUSTOSZ_GGUF=...` — własna ścieżka do pliku `.gguf`
- `KUSTOSZ_NO_BROWSER=1` — uruchomienie bez automatycznego otwierania przeglądarki

---

## Wyniki ewaluacji (12 polskich dokumentów: 30 PII + 21 chronionych encji kontekstu)

| Konfiguracja | Wykryte PII (Recall) | Błędne zamazania kontekstu | Czas / dokument |
|---|---|---|---|
| Tylko reguły + sumy kontrolne | 33,3% (10/30) | 0,0% (0/21) | < 1 ms |
| **Kustosz + Bielik-4.5B-v3 Q6_K** | 90,0% (27/30) | 4,8% (1/21) | 2,9 s (GPU) / 29,0 s (CPU) |
| **Kustosz + Gemma-4-E4B-it Q6_K** | **96,7% (29/30)** | **0,0% (0/21)** | **1,1 s (GPU)** |

Testy jednostkowe i benchmark:
```bash
python -m pytest -q
python bench/eval_rodo.py
```

## Licencja

Kod aplikacji: **Apache-2.0** ([LICENSE](LICENSE)). Zewnętrzne modele zachowują własne licencje (Gemma License / Apache-2.0 dla Bielik-4.5B-v3).
