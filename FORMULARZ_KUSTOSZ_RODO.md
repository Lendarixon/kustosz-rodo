# Formularz zgłoszeniowy — Bielik Awards 2026 (Kategoria c: SLM <10B)

## Nazwa projektu *
Linda Kustosz RODO

## Skrócony opis projektu *
Linda Kustosz RODO to lokalny (100% offline) firewall prywatności do fizycznej anonimizacji dokumentów PDF, DOCX, TXT i skanów (OCR). Zanim pismo urzędowe (BIP), sądowe, kadrowe lub umowa opuści organizację, system oczyszcza tekst z artefaktów PDF i homoglifów, deterministycznie weryfikuje sumy kontrolne (PESEL, NIP, REGON, IBAN, dowód osobisty), a następnie wykorzystuje lokalny model SLM (<10B: wymiennie Gemma-4-E4B-it lub Bielik-4.5B-v3 w llama.cpp) do odróżnienia danych prywatnych (odmienne formy imion, nazwisk, adresy, diagnozy) od kontekstu publiczno-prawnego (sędzia, burmistrz, urząd, artykuł ustawy).

Kluczowa zasada bezpieczeństwa: model SLM nigdy nie przepisuje tekstu z pamięci — zwraca jedynie dokładne podciągi w formacie NDJSON, a fizyczne zaczernienie tekstu w PDF (`apply_redactions` w PyMuPDF) oraz podmianę w DOCX wykonuje deterministyczny kod w Pythonie z lokalnym sejfem pseudonimizacji i audytem SHA-256.

W testach na 12 polskich dokumentach (30 encji wrażliwych, 21 encji kontekstu prawnego) same reguły wykryły 33,3% danych, Bielik-4.5B-v3 osiągnął 90,0% (4,8% błędnych maskowań; ~2,9 s GPU), a domyślna Gemma-4-E4B-it osiągnęła 96,7% i 0,0% błędnych zamazań (~1,1 s GPU).

Demo (GPU T4): https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/
GitHub + instalator: https://github.com/Lendarixon/kustosz-rodo

## Szczegółowy opis projektu wraz z efektami wdrożenia *
1. KONTEKST I PROBLEM WDROŻENIOWY
Urzędy publikujące decyzje w BIP, sądy, działy kadr, kancelarie prawne oraz placówki medyczne muszą usuwać dane osobowe zgodnie z RODO (art. 25 i 32) przed publikacją lub wysłaniem dokumentów na zewnątrz. Wysłanie surowego pisma do komercyjnego API chmurowego narusza poufność jeszcze przed anonimizacją, natomiast klasyczne wyrażenia regularne zawodzą w języku polskim w dwóch miejscach naraz:
- nie rozpoznają odmienionych polskich nazwisk i adresów („Anny Zielińskiej”, „Piotra Nowaka”, „astmy oskrzelowej”),
- albo nadmiarowo zamazują osoby publiczne, nazwy sądów i podstawy prawne („Burmistrz Miasta”, „Sędzia Sądu Rejonowego”, „art. 104 KPA”), czyniąc decyzję BIP nieczytelną.
Dodatkowo zwykłe „czarne prostokąty” nakładane wizualnie w edytorach PDF nie usuwają warstwy tekstowej pod spodem — dane wciąż można skopiować lub odczytać programowo.

2. ARCHITEKTURA ROZWIĄZANIA (100% ON-DEVICE, ZERO CHMURY)
Linda Kustosz RODO łączy deterministyczną walidację z lokalnym klasyfikatorem SLM (<10B) w pięciu etapach:
1) Ekstrakcja i kanonizacja dokumentów: obsługa PDF (PyMuPDF), DOCX (python-docx), TXT oraz skanów (Tesseract OCR `pol+eng`). Moduł kanonizacji Unicode usuwa znaki zerowej szerokości, nieciągłe spacje i podstawienia homoglifów (np. cyrylica w tekście łacińskim).
2) Warstwa deterministyczna i sumy kontrolne: przed przekazaniem treści do modelu system wykrywa i waliduje matematycznie PESEL, NIP, REGON, polski IBAN i numer dowodu osobistego oraz e-mail/telefon. Poprawne identyfikatory są zastępowane tokenami (`<PESEL_1>`, `<IBAN_1>`).
3) Kontekstowy klasyfikator SLM (Gemma-4-E4B-it Q6_K / Bielik-4.5B-v3 Q6_K): uruchamiany lokalnie przez `llama.cpp` (Vulkan GPU lub CPU). Model zwraca wyłącznie strumień obiektów NDJSON z etykietami do ukrycia (`OSOBA`, `ADRES`, `WRAZLIWE`) oraz do ochrony (`URZEDNIK`, `INSTYTUCJA`, `PRZEPIS`). W przypadku modelu Bielik-4.5B wykorzystano wariant GGUF z naprawionym tokenizerem BPE.
4) Weryfikacja antyhalucynacyjna i fizyczna redakcja plików: kod w Pythonie sprawdza dosłowne wystąpienie każdego kandydata w tekście źródłowym oraz brak kolizji z listą chronioną. Następnie:
   - w plikach PDF wykonywane jest prawdziwe usunięcie znaków z warstwy tekstowej (`page.add_redact_annot` + `page.apply_redactions()` w PyMuPDF) z wygenerowaniem gotowego pliku `*_RODO.pdf`,
   - w plikach DOCX zamiany wykonywane są bezpośrednio w akapitach i tabelach z zachowaniem układu (`*_RODO.docx`),
   - aplikacja wyświetla obok siebie wizualny podgląd stron dokumentu źródłowego, dokument wynikowy z czerwonymi ramkami/zaczernieniami oraz mapę podświetleń (niebieski: reguły/sumy kontrolne, czerwony: kontekst SLM, zielony: zachowany kontekst urzędowy).
5) Tryb odwracalny i ślad audytowy: tryb „Anonimizacja BIP / Chmura” wstawia trwałe etykiety (`[OSOBA]`, `[PESEL]`), a tryb „Pseudonimizacja odwracalna” zamienia dane na tokeny `<OSOBA_1>` z lokalnym sejfem mapowań, możliwością przywrócenia oryginału po odpowiedzi zewnętrznego narzędzia oraz skrótami SHA-256 wejścia i wyjścia.

3. KONFIGURACJA, INSTALACJA I DOSTĘPNOŚĆ
Projekt zawiera automatyczny instalator (`install.bat` dla Windows oraz `install.sh` + `tools/setup_kustosz.py`), który bez ręcznej konfiguracji pobiera binaria `llama.cpp` (z obsługą GPU Vulkan lub CPU), pobiera wybrane modele GGUF z weryfikacją sumy SHA-256, konfiguruje przenośne ścieżki OCR i zapisuje profil w `%LOCALAPPDATA%\KustoszRODO\config.json`. Z poziomu interfejsu WWW (okno „Ustawienia”) użytkownik może jednym kliknięciem przełączać model (`Gemma-4-E4B-it` / `Bielik-4.5B-v3`), tryb akceleracji (`Auto GPU/CPU`) oraz liczbę wątków CPU.

4. EFEKTY WDROŻENIA, JAKOŚĆ I KPI (ZMIERZONE NA PROTOYPIE)
Projekt znajduje się na etapie kompletnego prototypu gotowego do testów lokalnych i webowych (nie wdrożono jeszcze pilotażu w zewnętrznej instytucji). Pomiar jakości i wydajności przeprowadzono na autorskim zestawie 12 polskich dokumentów testowych (decyzje BIP, wezwania sądowe, pisma kadrowe, zwolnienia lekarskie, umowy zlecenia, przypadek uszkodzony homoglifami oraz 2 dokumenty kontrolne bez danych prywatnych; łącznie 30 encji do zamazania i 21 encji urzędowo-prawnych do ochrony):
- Jakość wykrywania PII (Recall): same reguły/sumy kontrolne osiągnęły **33,3%** (10/30), **Bielik-4.5B-v3 Q6_K** osiągnął **90,0%** (27/30), a domyślna **Gemma-4-E4B-it Q6_K** osiągnęła **96,7%** (29/30 oraz 100% wykrycia wszystkich encji kontekstowych — jedynym pominiętym elementem był celowo błędny numer PESEL bez poprawnej sumy kontrolnej).
- Ochrona kontekstu urzędowego (False Redact Rate): **0,0%** błędnych zamazań (0/21) na Gemma-4-E4B-it oraz **4,8%** (1/21) na Bielik-4.5B-v3 — nazwy sądów, burmistrzów, sędziów i numery artykułów pozostają czytelne.
- Czas przetwarzania dokumentu i oszczędność czasu: średnio **1,1 s/dokument** (1137 ms) na GPU Vulkan dla Gemma-4-E4B-it i **2,9 s/dokument** (2943 ms) dla Bielik-4.5B-v3 (~29 s na samym CPU) wobec ręcznego wyszukiwania i zamazywania każdego wystąpienia w edytorze PDF/DOCX trwającego kilkanaście minut na pismo.
- Bezpieczeństwo i koszt: **0 zł** kosztów licencyjnych i API chmurowych, **0 bajtów** wysłanych poza stanowisko pracy w wersji lokalnej.

5. OGRANICZENIA
- Zestaw walidacyjny obejmuje 12 syntetycznych dokumentów; przed wdrożeniem w konkretnym urzędzie zalecane są testy na próbce z lokalnego archiwum.
- W trybie odwracalnym sejf tokenów jest utrzymywany w pamięci aktywnej sesji; trwałe archiwum mapowań między sesjami wymaga szyfrowanego magazynu po stronie odbiorcy.

6. LINKI DO PROJEKTU
- Demo interaktywne online (Modal T4 GPU): https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/
- Kod źródłowy i instalator (GitHub, Apache-2.0): https://github.com/Lendarixon/kustosz-rodo
- Prezentacja PDF online: https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/prezentacja.pdf

## Prezentacja (opcjonalnie)
https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/prezentacja.pdf
