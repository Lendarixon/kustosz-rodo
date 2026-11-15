=== Nazwa projektu ===
Linda Kustosz RODO - lokalny strażnik kontekstowej anonimizacji PDF, DOCX i skanów

=== Skrócony opis projektu ===
Linda Kustosz RODO to działający w 100% lokalnie (bez internetu i chmury) strażnik prywatności dla urzędów, sądów, kadr, kancelarii i przychodni. Wrzucasz PDF, DOCX, TXT albo skan, a program przed wysyłką do BIP, kontrahenta czy chmury AI fizycznie usuwa dane osobowe z dokumentu.

Najważniejsza zasada: mały model językowy (SLM <10B: Gemma-4-E4B albo Bielik-4.5B-v3 w llama.cpp) nigdy nie przepisuje tekstu z pamięci. Zamiast tego działa jak precyzyjny klasyfikator: odróżnia dane prywatne w polskiej odmianie ("Anny Zielińskiej", "astmy oskrzelowej", prywatne adresy) od kontekstu publiczno-prawnego ("Burmistrz Miasta", "Sędzia Sądu Rejonowego", "art. 104 KPA"), którego nie wolno zamazać. Wcześniej kod oczyszcza tekst z artefaktów PDF i weryfikuje sumy kontrolne (PESEL, NIP, REGON, IBAN, dowód osobisty). Samą redakcję wykonuje deterministyczny Python - w PDF fizycznie usuwa tekst przez PyMuPDF, a w DOCX podmienia go w akapitach i tabelach. W opcjach wybierasz, co konkretnie i na co zamienić: czarne bloki (██████), etykiety ([OSOBA]), gwiazdki, własny tekst albo odwracalne tokeny <OSOBA_1> z lokalnym sejfem i audytem SHA-256.

Na 12 polskich dokumentach testowych (30 encji wrażliwych + 21 chronionych) same reguły wykryły 33,3%, Bielik-4.5B podniósł wynik do 90,0% (ok. 2,9 s GPU), a domyślna Gemma-4-E4B osiągnęła 96,7% i 0,0% błędnych zamazań (ok. 1,1 s GPU).

=== Szczegółowy opis projektu wraz z efektami wdrożenia ===
SKĄD POMYSŁ
W urzędzie (BIP), sądzie, dziale kadr czy kancelarii codziennie trzeba usuwać dane osobowe (RODO art. 25 i 32) z pism, decyzji i umów. Wysłanie dokumentu do płatnego API w chmurze łamie RODO jeszcze przed anonimizacją. Z kolei zwykłe wyrażenia regularne w języku polskim nie radzą sobie z dwoma rzeczami naraz:
- przepuszczają odmienione imiona, nazwiska, prywatne adresy i diagnozy ("Piotra Nowaka", "ul. Polna 5", "cukrzycy typu 2"),
- potrafią zamazać nazwisko sędziego, burmistrza, nazwę urzędu albo numer artykułu ustawy, psując dokument do publikacji w BIP.
Ponadto zwykłe "czarne prostokąty" w edytorach PDF często tylko zakrywają tekst wizualnie, a dane da się skopiować spod spodu. Chciałem zrobić narzędzie, które uruchamia się jednym kliknięciem na komputerze biurowym i rozwiązuje oba problemy naraz.

JAK TO DZIAŁA
1. Ekstrakcja i czyszczenie dokumentów: obsługa PDF (PyMuPDF), DOCX (python-docx), TXT oraz skanów (Tesseract OCR pol+eng). Moduł kanonizacji Unicode usuwa znaki zerowej szerokości, nietypowe spacje i podmiany homoglifów (np. cyrylica wstawiona zamiast łacińskich liter w "brudnych" PDF-ach).
2. Walidacja sum kontrolnych: przed wysłaniem treści do modelu program sprawdza matematycznie PESEL, NIP, REGON, polski IBAN, dowód osobisty oraz e-mail i telefon. Wykryte identyfikatory zamienia na bezpieczne tokeny (<PESEL_1>, <IBAN_1>).
3. Klasyfikator kontekstowy SLM (<10B): lokalny serwer llama.cpp (Gemma-4-E4B-it Q6_K domyślnie albo Bielik-4.5B-v3.0-Instruct Q6_K z naprawionym tokenizerem do wyboru w ustawieniach; Vulkan GPU lub CPU). Model zwraca wyłącznie obiekty NDJSON z podziałem na dane do ukrycia (OSOBA, ADRES, WRAZLIWE) i dane do zachowania (URZEDNIK, INSTYTUCJA, PRZEPIS).
4. Ochrona przed halucynacjami i prawdziwa redakcja plików: Python sprawdza, czy wskazany podciąg istnieje dosłownie w tekście i nie należy do kategorii chronionych. W plikach PDF wykonuje fizyczną redakcję strumienia (add_redact_annot + apply_redactions w PyMuPDF, wynik *_RODO.pdf), w DOCX podmienia treść z zachowaniem układu (*_RODO.docx), a w UI pokazuje obok siebie oryginalny dokument, wersję wynikową oraz mapę różnic (niebieski: sumy kontrolne, czerwony: kontekst SLM, zielony: zachowany kontekst).
5. Konfiguracja "co i na co zamieniać": użytkownik wybiera tryb nieodwracalny lub odwracalną pseudonimizację (<OSOBA_1> z lokalnym sejfem przywracania). W ustawieniach może dokładnie określić:
- na co zamieniać: etykiety RODO ([OSOBA], [PESEL]), czarne bloki (██████ - pełne czarne paski w PDF), gwiazdki (maskowanie znakami *) albo własny tekst i szablon (np. [USUNIETO:{TYP}], osobno dla każdej kategorii),
- co konkretnie zamieniać: włącznik dla każdej kategorii (OSOBA, ADRES, WRAZLIWE, PESEL, NIP, REGON, IBAN, DOWOD, EMAIL, TELEFON), listę fraz "Zawsze zamaskuj" oraz listę "Nigdy nie zamazuj" (np. nazwa własnej firmy).
6. Instalacja i konfiguracja: projekt ma instalator (install.bat / install.sh) pobierający binaria llama.cpp i modele GGUF z weryfikacją SHA-256 oraz panel Ustawienia zapisujący profil w %LOCALAPPDATA%\KustoszRODO\config.json.

EFEKTY
To wczesny prototyp wdrożeniowy - nie ma jeszcze pilotażu u zewnętrznego klienta, więc nie podaję wymyślonych oszczędności w firmie. Zamiast tego zmierzyłem jakość i szybkość na zestawie 12 polskich dokumentów testowych (decyzje BIP, wezwania sądowe, pisma kadrowe, zwolnienia lekarskie, umowy zlecenia, tekst z homoglifami oraz 2 kontrole negatywne z samymi przepisami i urzędami; łącznie 30 encji do ukrycia i 21 elementów kontekstu urzędowego do ochrony):
- Same wyrażenia regularne i sumy kontrolne: 33,3% wykrytych danych (10/30), 0,0% nadmiarowych maskowań (0/21).
- Kustosz RODO + Bielik-4.5B-v3 Q6_K (z naprawionym tokenizerem): 90,0% wykrytych danych (27/30), 4,8% nadmiarowych maskowań (1/21), średnio 2,9 s na dokument (GPU Vulkan) oraz 29,0 s na samym CPU (17,9-38,0 s).
- Kustosz RODO + Gemma-4-E4B-it Q6_K (domyślnie): 96,7% wykrytych danych (29/30; 100% wykrycia encji kontekstowych - jedyny pominięty element to celowo niepoprawny PESEL ze złą sumą kontrolną), 0,0% nadmiarowych maskowań (0/21), średnio 1,1 s na dokument (1137 ms, GPU Vulkan).
- Koszt API i ruchu do chmury: 0 zł i 0 bajtów wysłanych poza stanowisko pracy. Ręczne szukanie i zaczernianie danych w kilkustronicowym piśmie zajmuje kilkanaście minut; prototyp wykonuje analizę i redakcję PDF/DOCX w ok. 1-3 sekundy na GPU.

DLACZEGO SLM (<10B) I WKŁAD DLA BIELIKA
Bez małego modelu językowego (<10B) klasyczne reguły widzą tylko jedną trzecią danych osobowych w polskich pismach, a przy próbie dopisania kolejnych reguł niszczą sygnatury i nazwiska urzędników. Modele 4-4.5B działają lokalnie na sprzęcie biurowym i rozwiązują problem kontekstu. Dla Bielik-4.5B-v3 wykorzystaliśmy wersję GGUF z poprawionymi metadanymi tokenizera BPE (zgłoszoną wcześniej społeczności: 0/41 -> 41/41 zdań zgodnych z oryginałem). Oba modele (Gemma-4-E4B i Bielik-4.5B) można przełączać w jednym kliknięciu w Ustawieniach.

OGRANICZENIA
- Zestaw testowy obejmuje 12 syntetycznych dokumentów; przed wdrożeniem w konkretnym urzędzie lub kancelarii potrzebne są testy na próbce z lokalnego archiwum.
- W trybie odwracalnym sejf tokenów działa w pamięci aktywnej sesji; trwałe archiwum mapowań między sesjami wymaga szyfrowanego magazynu na dysku odbiorcy.
- W przypadku Bielika-4.5B zdarzają się pojedyncze niedopasowania odmienionych nazwisk (3/30) lub 1 błędne trafienie kontekstowe (1/21).

LINKI
Demo na żywo (Modal T4 GPU): https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/
Kod i instalator (GitHub, Apache-2.0): https://github.com/Lendarixon/kustosz-rodo
Prezentacja PDF: https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/prezentacja.pdf

=== Prezentacja (opcjonalnie) ===
https://ninjagovlad--kustosz-rodo-demo-kustoszservice-web.us-east.modal.run/prezentacja.pdf
