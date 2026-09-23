# Część 6: tekst na ekranie

**Zależy od:** części 3 (commit `bot: montaż po /gotowe`); linie tekstu zbiera już część 1. Część 5 nie jest wymagana.
**Efekt:** linie, które właściciel wysłał jako zwykłe wiadomości w trakcie `/nowy`, pojawiają się w edicie w stylu z presetu, zmieniając się na cięciach. Wykrywanie stylu napisów we wzorze powstaje tylko jako pomiar rozpoznawczy.
**Nowe pliki:** `src/tekst.py`, `zasoby/czcionki/<czcionka>.ttf` z plikiem licencji OFL, `tests/test_tekst.py`, `Pomiary/measure_tekst.py`, opcjonalnie `Pomiary/measure_tekst_wzoru.py`.
**Zmieniane:** `src/render.py` (nakładki w przebiegu końcowym), `src/bot.py` i `src/komunikaty.py` (pomoc, liczba linii w podpisie), `requirements-test.txt` (fonttools), `tests/test_render.py`.
**Od właściciela:** akceptacja czcionki. Domyślnie Anton, a gdy nie ma polskich znaków, Oswald w grubej odmianie (obie na licencji OFL, z repozytorium google/fonts).
**Gałąź:** `tekst` od `main` po scaleniu części 3 (i 5, jeśli jest).

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 6.1 do 6.4 z Pomiary/PLAN_EDITY_6_TEKST.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Zadanie 6.5 tylko na wyraźne polecenie. Na koniec zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, poprawiony 2026-09-22 po wykonaniu części 1 i 2. Kotwice `plik:linia` pochodzą z commita `0e84cba` i mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edit wideo 9:16 z materiałów właściciela według struktury wzorcowego editu (cięcia na uderzeniach, tempo, kolorystyka, sposób podania tekstu), z muzyką z biblioteki właściciela w `dane/muzyka/` (licencja nie jest warunkiem, decyzja 6 w mapie). Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
- Środowisko: lokalnie Windows 11, Python 3.13 w `venv` repo (`venv/Scripts/python.exe`, zależności przypięte w `requirements.txt`), ffmpeg i ffprobe 8.1 w PATH, brak Dockera. Serwer: Docker (obraz Debian) na Ubuntu 22.04. Ścieżki przez pathlib, procesy jako lista argumentów, bez powłoki.
- Reguły repo:
  1. Każda zmiana ma pomiar w `Pomiary/measure_<temat>.py`, tylko tam wolno pisać komentarze. Skrypt zaczyna od `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` i zapisuje wyniki do `outputs/` po każdej sekcji.
  2. Zero komentarzy i docstringów w `src/` i `tests/`.
  3. Nazwy funkcji bez `_` na początku, nazewnictwo po polsku (moduły `bot`, `analyze`, `music`, `render` zachowują nazwy z KONTEKST).
  4. Komunikaty bota, README i commity bez myślników i półpauz wewnątrz zdań.
  5. Commity bez wzmianek o AI i bez Co-Authored-By. Każda część na własnej gałęzi (nazwa w nagłówku). Zdalne repo `origin` na GitHubie: push tylko na prośbę właściciela, a przed nim sprawdź, że `.env`, `dane/`, `outputs/` i `Pomiary/` nie są w indeksie. Na serwer kod trafia przez `wdroz.ps1`, nie przez GitHub.
  6. Każde wywołanie ffmpeg i ffprobe z zamkniętym stdin (`-nostdin` albo `stdin=DEVNULL`), inaczej proces potomny potrafi zawisnąć.
- Testy: `python -m pytest -q` z katalogu głównego, cały zestaw poniżej 60 s. Media testowe generowane w locie w małej rozdzielczości (270x480), nigdy z `dane/`.
- Dziennik `Pomiary/ROZWOJ.md`: przeczytaj na starcie (stan, znane problemy, decyzje), dopisuj wpis po każdym zadaniu, decyzji i odkryciu, bez tokenu i wartości z `.env`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`main` zawiera commit `bot: montaż po /gotowe`, a `python -m pytest -q` przechodzi; utwórz gałąź `tekst` od `main`. Jeśli jest commit `kolor: LUT przeniesienia barw w renderze` (część 5), napisy idą po LUT. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 1 do 3 (streszczenie)
- `projekt.json` → `teksty`: lista `{"message_id": int, "tekst": str}` posortowana po `message_id`; zbiera je bot w stanie `zbieram` (`obsluz_tekst`, bot.py:327 w `0e84cba`), a odpowiedź na `/gotowe` już podaje liczbę linii (`komunikaty.projekt_w_kolejce`).
- `wzor.json` → pole `tekst` zarezerwowane (dziś `null`).
- `render.plan_ujec(...)` zwraca `fps`, `liczba_klatek` i `ujecia` z `klatka_od`; przebieg końcowy w `render.py` to jedyne miejsce kodowania wyniku.

## Kontrakty ustalane w tej części
**`wzor.json` → `tekst`**: `null` albo `{"pozycja": "gora" | "srodek" | "dol", "wersaliki": true, "okna_uderzenia": null}`. W tej części analiza go nie wypełnia (miejsce na przyszłe wykrywanie). Render honoruje `pozycja` i `wersaliki`, gdy są; `okna_uderzenia` pomija.

**Funkcje:**
- `tekst.obraz_tekstu(tekst: str, szerokosc: int, wysokosc: int, styl: dict) -> PIL.Image.Image`: przezroczysty obraz RGBA na cały kadr. Preset `domyslny`: czcionka z `zasoby/czcionki/`, wersaliki, biały z czarnym obrysem, środek kadru, wielkość czytelna na telefonie; łamanie wierszy do 85% szerokości; pojedyncze słowo szersze niż kadr zmniejsza czcionkę, aż się zmieści.
- `tekst.okna_tekstow(liczba_linii: int, plan: dict) -> list[tuple[int, int]]`: przedziały klatek `[od, do)`. Edit dzielony na równe części, początek każdej przyciągnięty do najbliższego początku ujęcia; linia trwa do początku następnej, ostatnia do końca. Każda linia co najmniej 1 s; gdy się nie da, `ValueError` z najwyższą dopuszczalną liczbą linii.
- Render: dla każdej linii obraz PNG w `praca/`, nakładany w przebiegu końcowym w swoim oknie z krótkim pojawieniem i zniknięciem (kilka klatek). Kolejność filtrów: LUT (jeśli jest), potem napisy. Brak linii: przebieg końcowy bez zmian.
- Podpis wiadomości z wynikiem i `/status` pokazują liczbę linii tekstu; `/start` wyjaśnia, że zwykła wiadomość w trakcie `/nowy` to linia napisu.

## Zadania

### [Task 6.1: Czcionka i obraz napisu]
- **Objective:** `src/tekst.py` z `obraz_tekstu` oraz czcionka w `zasoby/czcionki/` z plikiem licencji.
- **Context/Inputs:** czcionkę pobierz z repozytorium google/fonts (katalog `ofl/`), dołącz jej `OFL.txt`. Napis rysuje Pillow, nie filtr `drawtext` ffmpeg: odpada wtedy cytowanie dwukropków, apostrofów i procentów w tekście oraz ścieżek czcionki na Windows.
- **Constraints:** testy (fonttools w `requirements-test.txt`): czcionka ma wszystkie znaki „ąćęłńóśźżĄĆĘŁŃÓŚŹŻ” (brak znaku daje cichy prostokąt zamiast litery); tekst `Polska: 100% 'niepodległa' \ 1918` daje obraz z niepustym kanałem alfa; słowo „Konstantynopolitańczykowianeczka” po zmniejszeniu mieści się w 90% szerokości kadru (ramka niezerowej alfy).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.1 z Pomiary/PLAN_EDITY_6_TEKST.md. Weryfikacja: python -m pytest -q tests/test_tekst.py
```

### [Task 6.2: Okna napisów i nakładki]
- **Objective:** `tekst.okna_tekstow` i nakładki w przebiegu końcowym renderu.
- **Context/Inputs:** `src/render.py` (przebieg końcowy i miejsce, gdzie render ma `plan` i `projekt.json`), `src/tekst.py`.
- **Constraints:** wejścia obrazów muszą być ograniczone długością wyniku (zapętlone wejście bez limitu koduje w nieskończoność). Testy: 3 linie na planie 32 ujęć dają 3 rozłączne okna pokrywające cały edit, każde zaczyna się na początku ujęcia; 50 linii na 5 s daje `ValueError`; pełny render w 270x480 z 3 liniami ma długość równą `liczba_klatek / fps` z dokładnością do 1 klatki i kończy się przed limitem czasu testu; render bez linii nie dodaje żadnego wejścia obrazu. Gdy część 5 jest już zrobiona: przy sile koloru 1,0 i bardzo ciepłym wzorze najjaśniejszy piksel w oknie napisu ma wszystkie kanały co najmniej 240 (napis nie przebarwiony przez LUT); bez części 5 ten test pomija się z powodem.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.2 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/render.py, src/tekst.py, tests/test_render.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```

### [Task 6.3: Bot]
- **Objective:** pomoc i liczba linii w bocie.
- **Context/Inputs:** `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`. Zmiany tylko w tekście `/start` (`komunikaty.POMOC`), w `/status` i w podpisie wyniku; odpowiedź na `/gotowe` już liczy linie.
- **Constraints:** test: projekt z 2 liniami daje podpis z liczbą 2.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.3 z Pomiary/PLAN_EDITY_6_TEKST.md. Weryfikacja: python -m pytest -q tests/test_bot.py
```

### [Task 6.4: Pomiar]
- **Objective:** `Pomiary/measure_tekst.py`, wynik w `outputs/pomiar_tekst.json` i arkusz PNG.
- **Context/Inputs:** render 1080x1920 tego samego projektu syntetycznego bez napisów i z 3 liniami (w tym jedna z polskimi znakami i jedna bardzo długa); narzut czasu renderu w %, liczba linii dopuszczalna dla wzoru 15 s i 30 s. Arkusz: po jednej klatce ze środka okna każdej linii, najwyżej około 1600x1600 px: `outputs/tekst.png`.
- **Constraints:** próg: narzut poniżej 30%; wygląd ocenia oceniający.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.4 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/render.py, src/tekst.py, tests/generuj.py. Weryfikacja: python Pomiary/measure_tekst.py
```

### [Task 6.5: Rozpoznanie napisów we wzorze (opcjonalne, sam pomiar)]
- **Objective:** `Pomiary/measure_tekst_wzoru.py`: czy da się wykryć, kiedy i gdzie wzór pokazuje napisy. Bez kodu w `src/`.
- **Context/Inputs:** klatki wzorów z `dane/probki/wzory/` co 0,25 s; detektor tekstu instalowany samym pip (np. RapidOCR z onnxruntime, sprawdź aktualną nazwę pakietu), bez rozpoznawania treści. Wynik: oś czasu okien z napisem i ich pozycja pionowa (góra, środek, dół) oraz arkusz klatek z zaznaczonymi ramkami `outputs/tekst_wzoru_<wzor>.png`.
- **Constraints:** tylko raport. Na tej podstawie oceniający zdecyduje, czy warto wypełniać pole `tekst` we wzorze w kolejnym planie.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.5 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/analyze.py tylko w miejscu metadane. Weryfikacja: python Pomiary/measure_tekst_wzoru.py
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: narzut poniżej 30%, arkusz powstał.
- Test ręczny (Ty): `/nowy`, zdjęcia, 3 linie tekstu, `/gotowe`. Napisy czytelne na telefonie, polskie litery w porządku, zmieniają się na cięciach.

## Commity
1. `tekst: czcionka i obraz napisu`
2. `tekst: okna napisów i nakładki w renderze`
3. `bot: pomoc o napisach`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 6 według Pomiary/PLAN_EDITY_6_TEKST.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie); jeśli było zadanie 6.5, także decyzja o wykrywaniu napisów we wzorze.
```
1. `git log --oneline main..tekst`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_tekst.py`, próg narzutu.
3. `outputs/tekst.png`: polskie litery, obrys, nic nie wychodzi poza kadr, długi wiersz złamany albo zmniejszony.
4. `src/render.py`: napisy po LUT, wejścia obrazów ograniczone, brak linii nie zmienia przebiegu końcowego.
5. Jeśli jest `outputs/tekst_wzoru_*.png`: czy ramki trafiają w napisy widoczne na klatkach.
