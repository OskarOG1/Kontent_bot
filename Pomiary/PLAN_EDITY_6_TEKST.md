# Część 6: napisy w haku

**Zależy od:**
- części 8 (commit `Pomiary: pomiar nakładki`): `sekcje` we wzorze, nakładka w przebiegu końcowym;
- części 4: `numer_wzoru` w planie, `Pomiary/arkusz.py`.

Linie tekstu zbiera już część 1. Część 5 nie jest wymagana.
**Gałąź:** `tekst` od `main` po scaleniu części 8 (i 5, jeśli jest).
**Efekt:** linie, które przyszły jako zwykłe wiadomości w trakcie `/nowy`, pojawiają się w haku editu, przed dropem, jedna po drugiej. Styl jak we wzorach: szeryfowy biały napis z cieniem w dolnej części kadru, w strefie bezpiecznej TikToka. Emoji i inne znaki, których czcionka nie ma, są usuwane i liczone w podpisie.
**Dlaczego (przegląd 2026-09-23):** we wszystkich trzech wzorach napisy są tylko w haku:
- `0921`: od 0,75 do 3,75 s;
- `0915`: około 6 do 7 s;
- `0922`: około 8 do 11 s.

Wszędzie to szeryfowa biała czcionka na wysokości 50 do 77% kadru. Poprzednia wersja planu rozkładała napisy równo na cały edit czcionką Anton i nie znała emoji ani stref bezpiecznych.
**Nowe pliki:** `src/tekst.py`, `zasoby/czcionki/` (pliki czcionek z `OFL.txt` każdej), `tests/test_tekst.py`, `Pomiary/measure_tekst.py`, opcjonalnie `Pomiary/measure_tekst_wzoru.py`.
**Zmieniane:** `src/render.py`, `tests/test_render.py`, `src/konfiguracja.py`, `tests/test_konfiguracja.py`, `.env.example`, `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`, `requirements.txt` (fonttools).
**Od właściciela:** akceptacja czcionki na arkuszu `outputs/tekst.png`: domyślna szeryfowa, zapasowa blokowa.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 6.1 do 6.4 z Pomiary/PLAN_EDITY_6_TEKST.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Zadanie 6.5 tylko na wyraźne polecenie. Na koniec zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, przepisany 2026-09-23 po przeglądzie prawdziwych wzorów (`ROZWOJ.md`, wpisy „przegląd planów 4 do 6” i „przepisanie planów 4 do 9”). Kotwice `plik:linia` pochodzą z commita `57ba8fe` (stan po części 3 i zadaniu 3.7). Po wcześniejszych częściach mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edity wideo 9:16 na TikToka z dostarczonych materiałów. Wzorem jest gotowy edit: bot odtwarza jego strukturę i styl, a muzykę bierze z biblioteki właściciela w `dane/muzyka/`. Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
  - Edity promują czapki marki właściciela 1993 Supply (2026-09-24). Plansza końcowa pokazuje produkt albo stronę sklepu, a znak wodny marki leży na całym edicie poza planszą (wzór `0914`, zadanie 8.6).
  - Prawdziwe wzory (`0914`, `0915`, `0921`, `0922`, `0923`) mają ten sam format: hak (pierwsze 4 do 11 s, naturalne kolory, napis), drop (od niego pełnoekranowa nakładka graficzna i mocny grading), montaż i plansza końcowa około 1 s (mapa, decyzja 15). `0923` ma dodatkowo napisy słowo po słowie w rytmie i gwiazdy wokół postaci przed dropem, czego plany nie odtwarzają.
  - Biblioteka muzyki to dźwięki samych wzorów (decyzja 14).
- Środowisko:
  - lokalnie: Windows 11, Python 3.13 w `venv` repo (`venv/Scripts/python.exe`, zależności przypięte w `requirements.txt`), ffmpeg i ffprobe 8.1 w PATH, brak Dockera;
  - serwer: Docker (obraz Debian, ffmpeg 7.1) na Ubuntu 24.04, bot z limitem 2 CPU i 3 GB;
  - ścieżki przez pathlib, procesy jako lista argumentów, bez powłoki.
- Reguły repo:
  1. Każda zmiana ma pomiar w `Pomiary/measure_<temat>.py`. Tylko tam i w `Pomiary/arkusz.py` wolno pisać komentarze. Skrypt zaczyna od `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` i zapisuje wyniki do `outputs/` po każdej sekcji.
  2. Zero komentarzy i docstringów w `src/` i `tests/`.
  3. Nazwy funkcji bez `_` na początku, nazewnictwo po polsku (moduły `bot`, `analyze`, `music`, `render` zachowują swoje nazwy).
  4. Komunikaty bota, README i commity bez myślników i półpauz wewnątrz zdań.
  5. Commity i gałęzie:
     - commity bez wzmianek o AI i bez Co-Authored-By;
     - każda część na własnej gałęzi (nazwa w nagłówku) od aktualnego `main` (przed startem `git pull`);
     - zdalne repo `origin` na GitHubie: push tylko na prośbę właściciela, a przed nim sprawdź, że `.env`, `dane/` i `outputs/` nie są w indeksie;
     - `Pomiary/` jest w repozytorium (decyzja właściciela 2026-09-23): zmiany planów, pomiarów i dziennika commituj razem z zadaniem;
     - na serwer kod trafia przez `wdroz.ps1`, nie przez GitHub.
  6. Każde wywołanie ffmpeg i ffprobe z zamkniętym stdin (`-nostdin` albo `stdin=DEVNULL`), inaczej proces potomny potrafi zawisnąć.
- Testy: `python -m pytest -q` z katalogu głównego. Czas całego zestawu podaj w raporcie, ale nie jest progiem (decyzja właściciela 2026-09-23): nie skracaj testów kosztem tego, co sprawdzają. Media testowe generowane w locie w małej rozdzielczości (270x480), nigdy z `dane/`.
- Arkusz porównawczy (decyzja 17): pomiar każdej części kończy się arkuszem `outputs/porownanie_<czesc>_<wzor>.png` z `Pomiary/arkusz.py` (powstaje w zadaniu 4.4).
  - Układ `dane/` od 2026-09-24 (katalogu `dane/probki/` już nie ma):
    - wzory do pomiaru to pliki `dane/wzory/*.mp4` leżące bezpośrednio w katalogu. Podkatalogi `dane/wzory/<id>/` to wzory zapisane przez bota, pomiar ich nie bierze;
    - biblioteka właściciela: `dane/zdjęcia/`, `dane/nagrania/` (klipy 4K, razem około 11 GB), `dane/zdjęcia_bez_tła/` (PNG z przezroczystością) i `dane/promocyjne/` (produkt i znak wodny);
    - bot tych katalogów nie czyta, bo materiały dostaje przez Telegram.
  - Arkusz powstaje dla każdego wzoru z `dane/wzory/*.mp4`. Materiały do niego to stała próbka, wybierana po nazwie:
    - pierwsze 8 plików z `dane/zdjęcia/`;
    - pierwsze 4 z `dane/nagrania/`;
    - pierwsze 2 z przezroczystością z `dane/zdjęcia_bez_tła/`;
    - jeden katalog projektu na cały przebieg pomiaru (twarde dowiązania, a gdy się nie da, kopie), usuwany na końcu;
    - gdy katalogów brak, barwne zdjęcia z generatora.
  - Plansza w pomiarze: `dane/plansze/domyslna.*`, inaczej pierwszy plik bez przezroczystości z `dane/promocyjne/`, inaczej syntetyczna.
  - Oceniający wydaje werdykt na arkuszu, a progi liczbowe są dodatkiem.
  - Wzór ogląda się tylko w `outputs/`, nic z niego nie trafia do wyniku bota.
- Dziennik `Pomiary/ROZWOJ.md`: przeczytaj na starcie (stan, znane problemy, decyzje), dopisuj wpis po każdym zadaniu, decyzji i odkryciu, bez tokenu i wartości z `.env`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`main` zawiera commit `Pomiary: pomiar nakładki` (część 8 po odbiorze i scaleniu), a `python -m pytest -q` przechodzi. Utwórz gałąź `tekst` od `main`. Jeżeli jest już część 5, kolor siedzi w segmentach i napisów nie dotyczy. Jeśli `main` nie ma części 8, zatrzymaj się i zapytaj.

## Kontrakt z wcześniejszych części
Numery linii z `57ba8fe`, więc szukaj po nazwach.
- `projekt.json` → `teksty`: lista `{"message_id": int, "tekst": str}` posortowana po `message_id`. Zbiera ją bot w stanie zbierania (`obsluz_tekst`, bot.py:446), a odpowiedź na `/gotowe` już podaje liczbę linii (`komunikaty.projekt_w_kolejce`, komunikaty.py:84).
- `wzor.json`:
  - `sekcje: {drop_s, drop_ujecie, koniec_haka_uderzenia} | null` (część 8);
  - zarezerwowane `tekst: null`.
- Render:
  - `plan_ujec` zwraca `fps`, `liczba_klatek` i `ujecia` z `klatka_od`, `liczba_klatek`, `numer_wzoru`;
  - `przebieg_koncowy` to jedyne kodowanie wyniku i ma już nakładkę z części 8;
  - `renderuj` ma katalog projektu.
- `src/komunikaty.py`: `POMOC` (1), `podsumowanie_renderu` (95), `status_projektu` (104).
- `src/bot.py`: `obsluz_cmd_status` (283), `renderuj_w_tle` (153).
- `src/konfiguracja.py`: `Konfiguracja` (10), `wczytaj` (19).
- `zasoby/` jest kopiowany do obrazu Dockera wzorcem `zasob[y]/` (część 7).

## Kontrakty ustalane w tej części

**Presety (`tekst.PRESETY`):**
- `szeryf` (domyślny):
  - czcionka: Libre Baskerville w grubości Bold z repozytorium google/fonts (`ofl/librebaskerville`); gdy brakuje któregoś z polskich znaków, Noto Serif Bold (`ofl/notoserif`);
  - wygląd: biały napis, miękki cień (czarny, krycie 60%, przesunięty o 0,6% wysokości kadru, rozmyty), bez wersalików;
  - wielkość: wysokość wersalika około 3,2% wysokości kadru, czyli około 60 px przy 1920.
- `blok`:
  - czcionka: Anton (`ofl/anton`); gdy brakuje polskich znaków, Oswald Bold (`ofl/oswald`);
  - wygląd: biały z czarnym obrysem grubości 0,4% wysokości kadru, wersaliki;
  - wielkość: wysokość wersalika około 4% wysokości kadru.
- Jeśli repozytorium ma tylko czcionkę zmienną, ustaw grubość przez `set_variation_by_name` albo `set_variation_by_axes` w Pillow i sprawdź to testem. Do każdej czcionki dołącz jej `OFL.txt`. Sprawdź aktualne ścieżki w repozytorium, nie zgaduj.

**Pozycja i strefa bezpieczna:**
- Pozycja `gora` stawia środek bloku napisu na 22% wysokości, `srodek` na 50%, `dol` (domyślna) na 70%.
- Strefa bezpieczna TikToka: blok mieści się w poziomie między 8% a 85% szerokości (prawy margines jest większy przez przyciski) i w pionie między 12% a 78% wysokości.
- Wiersze łamane do szerokości strefy, blok wyśrodkowany poziomo w strefie.
- Pojedyncze słowo szersze niż strefa zmniejsza czcionkę, aż się zmieści.
- Blok, który po złamaniu wychodzi poza strefę w pionie, przesuwa się do jej wnętrza.

**`src/tekst.py`:**
- `znaki_czcionki(sciezka) -> set[int]`: znaki z tablicy `cmap` przez fontTools. `fonttools` przechodzi z `requirements-test.txt` do `requirements.txt`, przypięty.
- `oczysc(tekst, znaki) -> tuple[str, int]`:
  - usuwa znaki spoza czcionki (emoji, selektory wariantu, łączniki ZWJ, symbole), poza spacją;
  - zwija wielokrotne spacje i obcina brzegi;
  - zwraca tekst i liczbę usuniętych znaków;
  - linia pusta po oczyszczeniu wypada.
- `obraz_tekstu(tekst, szerokosc, wysokosc, styl) -> PIL.Image.Image`:
  - przezroczysty obraz RGBA na cały kadr;
  - `styl` to `{"preset": "szeryf" | "blok", "pozycja": "gora" | "srodek" | "dol", "wersaliki": bool | None}`, gdzie `None` bierze wersaliki z presetu.
- `okna_tekstow(liczba_linii, plan, koniec_haka_klatka) -> list[tuple[int, int]]` zwraca przedziały klatek `[od, do)`:
  - okno napisów to `[0, koniec_haka_klatka)`, a linie dzielą je po równo;
  - początek każdej linii poza pierwszą przyciąga się do najbliższego początku ujęcia planu, jeśli leży w granicy 8 klatek;
  - linia trwa do początku następnej, a ostatnia do końca okna;
  - każda linia trwa co najmniej `fps` klatek (1 s). Gdy okno jest za krótkie, jego koniec przesuwa się kolejno na początki następnych ujęć (w montaż), aż linie się zmieszczą;
  - gdy nie mieści ich cały edit, funkcja rzuca `ValueError` z najwyższą dopuszczalną liczbą linii.
- `render.koniec_haka(plan, sekcje) -> int` powstaje w części 8 (zadanie 8.5, poprawka po odbiorze 2026-09-24). Nakładka zaczyna się w tym samym miejscu, więc tu jej nie definiuj, tylko jej użyj:
  - z sekcjami: `klatka_od` pierwszego ujęcia planu z `numer_wzoru >= drop_ujecie`;
  - bez sekcji: 40% `liczba_klatek`, przyciągnięte do najbliższego początku ujęcia;
  - w obu przypadkach co najmniej `fps` klatek.

**Render:**
- Teksty czytane z `projekt.json` w katalogu projektu i oczyszczone przez `oczysc`.
- Dla każdej linii obraz PNG w `praca/`, nakładany w przebiegu końcowym po nakładce z części 8, a przed znakiem wodnym z zadania 8.6, w swoim oknie, z pojawieniem i zniknięciem (przenikanie przez 4 klatki).
- Gdy jest znak wodny (pas 76% do 84% wysokości), dolna krawędź bloku napisów leży najwyżej na 75% wysokości.
- Wejścia obrazów zapętlone i ograniczone długością wyniku (`-loop 1 -t`).
- Brak linii oznacza przebieg końcowy bez zmian.
- CLI `--styl-tekstu szeryf|blok` i `--pozycja-tekstu gora|srodek|dol`. Pole `tekst` we wzorze (`pozycja`, `wersaliki`) ma pierwszeństwo, gdy jest.
- Podsumowanie dostaje `"teksty": {"linie": 3, "usuniete_znaki": 2, "okna": [[0, 45], [45, 90], [90, 120]]}`.

**Konfiguracja:** `STYL_TEKSTU` (domyślnie `szeryf`) i `POZYCJA_TEKSTU` (domyślnie `dol`) w `.env`, w `Konfiguracja` i w `.env.example`. Nieznana wartość daje `ValueError` przy starcie. Bot przekazuje obie do CLI renderu.

**Bot:**
- `/start` (`komunikaty.POMOC`) wyjaśnia, że zwykła wiadomość w trakcie `/nowy` to linia napisu w haku editu.
- Podpis wyniku podaje liczbę linii, a gdy coś usunięto, dodaje „usunięte znaki bez czcionki: 2 (np. emoji)”.
- `/status` przy zbieranym projekcie podaje liczbę linii.

## Zadania

### [Task 6.1: Czcionki i obraz napisu]
- **Objective:** `src/tekst.py` z `PRESETY`, `znaki_czcionki`, `oczysc`, `obraz_tekstu` oraz czcionki w `zasoby/czcionki/` z licencjami.
- **Context/Inputs:** kontrakty presetów, pozycji i `src/tekst.py`. Czcionki z repozytorium google/fonts (katalog `ofl/`). Napis rysuje Pillow, nie filtr `drawtext` ffmpeg: odpada wtedy cytowanie dwukropków, apostrofów i procentów w tekście oraz ścieżek czcionki na Windows.
- **Constraints:** testy w `tests/test_tekst.py`:
  1. czcionki obu presetów mają wszystkie znaki „ąćęłńóśźżĄĆĘŁŃÓŚŹŻ” (brak znaku daje cichy prostokąt zamiast litery);
  2. tekst `Polska: 100% 'niepodległa' \ 1918` daje obraz z niepustym kanałem alfa;
  3. słowo „Konstantynopolitańczykowianeczka” mieści się w szerokości strefy bezpiecznej (ramka niezerowej alfy);
  4. dla każdej pozycji i obu presetów ramka niezerowej alfy (z cieniem i obrysem) leży w strefie bezpiecznej;
  5. `oczysc("Siema 🔥🔥 ziomek ✨", znaki_szeryfu)` daje `("Siema ziomek", 3)`;
  6. preset `szeryf` nie zmienia wielkości liter, `blok` daje wersaliki.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.1 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz requirements.txt i requirements-test.txt. Weryfikacja: python -m pytest -q tests/test_tekst.py
```
- **Commit:** `tekst: czcionki i obraz napisu`

### [Task 6.2: Okna w haku i nakładanie w renderze]
- **Objective:** `tekst.okna_tekstow` i napisy w przebiegu końcowym, z końcem haka z `render.koniec_haka` (część 8).
- **Context/Inputs:** kontrakty `okna_tekstow`, `koniec_haka` i „Render”; `src/render.py` (`przebieg_koncowy`, `renderuj`, `glowna`), `src/tekst.py`, `tests/generuj.py` (`nakladka_testowa` z części 8).
- **Constraints:** wejścia obrazów muszą być ograniczone długością wyniku, bo zapętlone wejście bez limitu koduje w nieskończoność. Testy:
  1. 3 linie na planie 32 ujęć z hakiem kończącym się na ujęciu 8: 3 rozłączne okna w `[0, koniec_haka)`, a początki drugiej i trzeciej linii przyciągnięte do początków ujęć w granicy 8 klatek;
  2. hak z jednego ujęcia 4 s przy 30 fps i 3 linie: okna 0 do 40, 40 do 80 i 80 do 120;
  3. 5 linii w haku 3 s: okno rozszerza się o kolejne ujęcia, a każda linia ma co najmniej 30 klatek;
  4. 50 linii na edicie 5 s: `ValueError` z najwyższą liczbą linii;
  5. bez `sekcje`: okna napisów kończą się w `render.koniec_haka`, czyli na 40% editu;
  6. pełny render 270x480 z 3 liniami:
     - długość równa `liczba_klatek / fps` z dokładnością do 1 klatki;
     - w oknie linii w obszarze napisu są białe piksele, a poza oknem nie ma;
  7. napis nad nakładką:
     - wzór z `sekcje.drop_ujecie` 1 i ujęciami po 15 klatek, więc `koniec_haka` to 30 (minimum `fps`), a od klatki 30 nakładka `alfa` zakrywa górną połowę czerwienią;
     - dwie linie u góry: okno rozszerza się do 60 klatek, więc druga linia (30 do 60) leży na nakładce;
     - w klatce 45 najjaśniejszy piksel w obszarze napisu ma wszystkie kanały co najmniej 240. Od zadania 8.5 nakładka nie leci od pierwszej klatki, więc napis spotyka ją tylko wtedy, gdy okno wychodzi poza hak;
  8. render bez linii: polecenie przebiegu końcowego identyczne jak bez tej części (podmienione `uruchom_ffmpeg`).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.2 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/render.py, src/tekst.py, tests/test_render.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `tekst: napisy w haku w renderze`

### [Task 6.3: Konfiguracja i bot]
- **Objective:** `STYL_TEKSTU` i `POZYCJA_TEKSTU`, pomoc, liczba linii w `/status` i w podpisie wyniku.
- **Context/Inputs:** kontrakty „Konfiguracja” i „Bot”; `src/konfiguracja.py`, `.env.example`, `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`, `tests/test_konfiguracja.py`.
- **Constraints:** testy:
  1. projekt z 2 liniami daje podpis z liczbą 2, a podsumowanie z `usuniete_znaki: 1` daje wzmiankę o usuniętych znakach;
  2. `/status` przy zbieraniu podaje liczbę linii;
  3. `POMOC` wspomina o napisach;
  4. `STYL_TEKSTU=kursywa` daje `ValueError`;
  5. bot przekazuje `--styl-tekstu` i `--pozycja-tekstu` z konfiguracji.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.3 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/konfiguracja.py, .env.example, src/bot.py, src/komunikaty.py, tests/test_bot.py, tests/test_konfiguracja.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `bot: napisy w haku`

### [Task 6.4: Pomiar]
- **Objective:** `Pomiary/measure_tekst.py`, wynik w `outputs/pomiar_tekst.json` i arkusze.
- **Context/Inputs:**
  - render 1080x1920 tego samego syntetycznego projektu bez napisów i z 3 liniami (jedna z polskimi znakami, jedna bardzo długa, jedna z emoji), dla obu presetów;
  - raport: narzut czasu renderu w procentach i najwyższa liczba linii dla haków prawdziwych wzorów (z cache `outputs/wzor_<nazwa>.json`);
  - arkusz `outputs/tekst.png` z jedną klatką ze środka okna każdej linii, dla obu presetów obok siebie, najwyżej około 1600x1600 px;
  - arkusze porównawcze `outputs/porownanie_tekst_<wzor>.png` z 2 liniami.
- **Constraints:** próg: narzut poniżej 30%. Wygląd ocenia oceniający i właściciel.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.4 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/render.py, src/tekst.py, tests/generuj.py, Pomiary/arkusz.py, Pomiary/measure_muzyka.py jako wzór układu. Weryfikacja: python Pomiary/measure_tekst.py
```
- **Commit:** `Pomiary: pomiar napisów`

### [Task 6.5: Rozpoznanie napisów we wzorze (opcjonalne, sam pomiar)]
- **Objective:** `Pomiary/measure_tekst_wzoru.py`: kiedy i gdzie wzór pokazuje napisy. Bez kodu w `src/`.
- **Context/Inputs:**
  - klatki wzorów z `dane/wzory/*.mp4` co 0,25 s;
  - detektor tekstu instalowany samym pip (np. RapidOCR z onnxruntime, sprawdź aktualną nazwę pakietu), bez rozpoznawania treści;
  - wynik: oś czasu okien z napisem, ich pozycja pionowa w procentach wysokości i położenie wobec `sekcje.drop_s`, plus arkusz klatek z zaznaczonymi ramkami `outputs/tekst_wzoru_<wzor>.png`.
- **Constraints:** tylko raport. Na tej podstawie oceniający zdecyduje, czy warto wypełniać pole `tekst` we wzorze automatycznie (pozycja) i czy reguła „napisy w haku” trzyma się na nowych wzorach.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 6.5 z Pomiary/PLAN_EDITY_6_TEKST.md; otwórz src/analyze.py tylko w miejscu metadane. Weryfikacja: python Pomiary/measure_tekst_wzoru.py
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: narzut poniżej 30%, arkusze powstały, czcionka zaakceptowana przez właściciela.
- Test ręczny (Ty):
  - `/nowy`, zdjęcia, 2 do 3 linie tekstu (jedna z emoji), `/gotowe`;
  - napisy są tylko w haku, czytelne na telefonie, nie wchodzą pod przyciski TikToka, polskie litery są w porządku, a emoji zniknęły z wzmianką w podpisie;
  - każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `tekst: czcionki i obraz napisu`
2. `tekst: napisy w haku w renderze`
3. `bot: napisy w haku`
4. `Pomiary: pomiar napisów`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 6 według Pomiary/PLAN_EDITY_6_TEKST.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie); jeśli było zadanie 6.5, także decyzja o wykrywaniu napisów we wzorze.
```
1. `git log --oneline main..tekst`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_tekst.py`: próg narzutu.
3. `outputs/tekst.png`: polskie litery, cień i obrys, nic nie wychodzi poza strefę bezpieczną, długi wiersz złamany albo zmniejszony.
4. Arkusze `outputs/porownanie_tekst_*.png`: napisy w wyniku są w tej samej części editu co we wzorze (hak) i na podobnej wysokości.
5. `src/render.py`:
   - napisy po nakładce, a przed znakiem wodnym, i nad jego pasem;
   - wejścia obrazów ograniczone;
   - brak linii nie zmienia przebiegu końcowego.
6. Jeśli jest `outputs/tekst_wzoru_*.png`: czy ramki trafiają w napisy widoczne na klatkach.
