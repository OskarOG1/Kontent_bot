# Część 5: kolorystyka jak we wzorze

**Zależy od:** części 3 (commit `bot: montaż po /gotowe`). Część 4 i 6 nie są wymagane. Zadanie 5.0 nie zależy od części 3 i można je zlecić wcześniej, jeśli analiza wzoru na serwerze okaże się za wolna (część 7, krok 8).
**Gałąź:** `kolor` od `main` (samo zadanie 5.0 zlecone wcześniej: `kopia-wzoru` od `main`).
**Efekt:** analiza dużych wzorów pracuje na lekkiej kopii obrazu (zadanie 5.0), wzór dostaje statystyki barw, a render przenosi je na materiały przez tablicę LUT o regulowanej sile. Siłę domyślną wybiera oceniający na podstawie arkuszy.
**Nowe pliki:** `src/kolor.py`, `tests/test_kolor.py`, `Pomiary/measure_kopia.py`, `Pomiary/measure_kolor.py`.
**Zmieniane:** `src/analyze.py` (lekka kopia, pole `kolorystyka`, ponowna analiza wszystkich wzorów), `tests/test_analiza.py`, `src/render.py` (LUT w przebiegu końcowym, `--sila-koloru`), `src/konfiguracja.py` (`SILA_KOLORU`), `.env.example`, `src/bot.py` (przekazanie siły), `tests/test_render.py`.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_5_KOLOR.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commit `bot: montaż po /gotowe`, a `python -m pytest -q` przechodzi; utwórz gałąź `kolor` od `main` (samo zadanie 5.0 zlecone wcześniej wymaga tylko `0e84cba`). Jeśli jest też commit `tekst: okna napisów i nakładki w renderze` (część 6), LUT musi stanąć przed nakładkami napisów. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 1 do 3 (streszczenie)
- `wzor.json` ma zarezerwowane pole `kolorystyka` (dziś `null`); `analyze.analizuj_wzor(sciezka, wzor_id)` (analyze.py:215 w `0e84cba`) woła `wykryj_ciecia` (98) na oryginale; `main` (255) przyjmuje dziś dokładnie dwa argumenty `<wejscie> <wyjscie.json>` i w tej postaci woła go bot. Prawdziwe wzory to 4K, 60 fps, około 32 s: dekodowanie pełnej rozdzielczości trwa około 36 s, a pobranie jednej klatki przez przewinięcie około 0,6 s (`ROZWOJ.md`).
- `render.py`: przebieg końcowy to jedyne miejsce kodowania wyniku; pliki w argumentach filtrów podawane względem katalogu roboczego ffmpeg, bo dwukropek w ścieżce Windows łamie składnię filtra. Sklejone segmenty (przed przebiegiem końcowym) pokazują dokładnie to, co zobaczy widz.
- `konfiguracja.wczytaj` zwraca obiekt z polami konfiguracji; bot przekazuje parametry do CLI renderu.

## Kontrakty ustalane w tej części
**`wzor.json` → `kolorystyka`**
```json
{"lab_srednia": [52.1, 6.3, 14.8], "lab_odchylenie": [21.4, 9.9, 12.2], "probki": 45}
```
Lab w jednostkach zmiennoprzecinkowych: L od 0 do 100, a i b mniej więcej od −128 do 127, liczone z sRGB. Nie w 8-bitowej skali OpenCV (tam L jest przeskalowane do 255, a do a i b dodane 128). Próbki to klatki rozłożone równo w czasie, najwyżej 60.

**Funkcje:**
- `analyze.statystyki_koloru(sciezka_wideo, liczba_probek=60) -> dict` w kształcie jak wyżej; `analizuj_wzor` wypełnia nią `kolorystyka`.
- CLI: `python src/analyze.py --wszystkie [--katalog-danych dane]` analizuje ponownie każdy wzór, który ma `zrodlo.*`, i nadpisuje jego `wzor.json` (to samo `id`). Wzory z części 2 nie mają kolorystyki, stąd ta komenda.
- `kolor.lut_transferu(zrodlo: dict, cel: dict, sila: float, rozmiar: int = 33) -> numpy.ndarray` o kształcie `(rozmiar, rozmiar, rozmiar, 3)`, wartości od 0 do 1. Dla każdego koloru: przejście do Lab, przesunięcie i przeskalowanie statystyk źródła na statystyki celu (transfer Reinharda), zmieszanie z kolorem wejściowym w proporcji `sila`, powrót do sRGB, obcięcie do zakresu. Stosunek odchyleń ograniczony do przedziału od 0,5 do 2, żeby prawie jednolity materiał nie eksplodował.
- `kolor.zapisz_cube(lut, sciezka)`: format `.cube` (`LUT_3D_SIZE`, potem wiersze „r g b”, przy czym składowa czerwona zmienia się najszybciej).
- Render: po sklejeniu segmentów liczy `statystyki_koloru` sklejonego wideo, buduje LUT do wzoru i nakłada go jako pierwszy filtr przebiegu końcowego (`lut3d`). Siła z `--sila-koloru` (domyślnie 0,6), przy sile 0 albo braku `kolorystyka` we wzorze filtra nie ma wcale. Konfiguracja: `SILA_KOLORU` w `.env`, bot przekazuje ją do CLI.

## Zadania

### [Task 5.0: Lekka kopia wzoru]
**Status 2026-09-23: niepotrzebne na dziś.** Analiza prawdziwego wzoru 4K na serwerze trwa 51 s przy progu 150 s, a pobranie 153 MB 9 s. Zadanie zostaje w planie na wypadek dłuższych wzorów albo wolniejszej maszyny.
- **Objective:** analiza dużego wzoru pracuje na zmniejszonej kopii obrazu, a dźwięk i metadane bierze z oryginału.
- **Context/Inputs:** `src/analyze.py`: `analizuj_wzor` (215) woła `wykryj_ciecia` (98) na oryginale 4K; lokalnie to 40 do 55 s, na serwerze będzie wolniej przy limicie 300 s (`LIMIT_ANALIZY_S`, bot.py:27). Z `ROZWOJ.md`: kopia 360p powstaje w około 11 s, a detekcja na niej trwa około 2 s. Nowa funkcja `analyze.lekka_kopia(sciezka, cel, wysokosc=360) -> Path`: ta sama liczba i te same czasy klatek co oryginał, bez dźwięku. `analizuj_wzor` robi kopię w katalogu tymczasowym, gdy obraz ma ponad 720 px wysokości, i na niej wykrywa cięcia (po zadaniu 5.1 także liczy kolory); `metadane` i `analizuj_rytm` dalej czytają oryginał.
- **Constraints:** cicha pomyłka to kopia z inną liczbą klatek: zgubiona albo zdublowana klatka przesuwa wszystkie następne cięcia. Testy: kopia wideo syntetycznego 1080x1920 z cięciami ma tyle samo klatek co oryginał (`ffprobe -count_frames`), a `wykryj_ciecia` na kopii i na oryginale zwraca te same czasy; to samo przy 30000/1001 fps. Pomiar `Pomiary/measure_kopia.py` na wzorach z katalogu próbek (argument, domyślnie `dane/probki/wzory/`): czas analizy z kopią i bez, odsetek cięć identycznych z dokładnością do 1 klatki, tempo bez zmian. Próg: co najmniej 95% zgodnych cięć i co najmniej 2 razy krótsza analiza na każdym wzorze.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.0 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/analyze.py, tests/generuj.py, tests/test_analiza.py. Weryfikacja: python -m pytest -q tests/test_analiza.py oraz python Pomiary/measure_kopia.py
```

### [Task 5.1: Statystyki barw wzoru]
- **Objective:** `analyze.statystyki_koloru`, pole `kolorystyka` w `wzor.json` i CLI `--wszystkie`.
- **Context/Inputs:** kontrakty powyżej; `src/analyze.py`, `tests/generuj.py` (klipy i zdjęcia o zadanym kolorze z części 3). Klatki do statystyk bierz z lekkiej kopii z zadania 5.0. Obsługa `--wszystkie` nie może zepsuć wywołania z bota `<wejscie> <wyjscie.json>`.
- **Constraints:** testy łapią dwie ciche pomyłki: skalę 8-bitową i zamianę kanałów (OpenCV czyta BGR). Wideo w jednolitej bieli daje L około 100, a i b około 0; jednolita czerwień sRGB daje około (53,2; 80,1; 67,2) z tolerancją 1. `--wszystkie` pomija wzór bez `zrodlo.*` i zachowuje jego `id`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.1 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/analyze.py i tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_kolor.py tests/test_analiza.py
```

### [Task 5.2: LUT przeniesienia barw]
- **Objective:** `src/kolor.py` z `lut_transferu` i `zapisz_cube`.
- **Context/Inputs:** kontrakt funkcji powyżej.
- **Constraints:** testy: LUT z identycznych statystyk (albo siła 0) nałożony przez ffmpeg `lut3d` na obraz z gradientem daje wynik równy wejściu z tolerancją 2 poziomów na kanał; to łapie złą kolejność osi w `.cube` (tablica z zamienionymi osiami nie jest tożsamością) oraz ścieżkę w filtrze na Windows. Źródło jednolicie szare (odchylenie bliskie 0) daje LUT bez NaN i nieskończoności, w zakresie od 0 do 1. Wzór ciepły (duże b) i materiał neutralny: średnie b materiału po LUT rośnie.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.2 z Pomiary/PLAN_EDITY_5_KOLOR.md. Weryfikacja: python -m pytest -q tests/test_kolor.py
```

### [Task 5.3: LUT w renderze]
- **Objective:** render nakłada LUT w przebiegu końcowym; siła z konfiguracji.
- **Context/Inputs:** `src/render.py` (przebieg końcowy), `src/konfiguracja.py`, `.env.example`, `src/bot.py` (wywołanie CLI renderu), `src/kolor.py`.
- **Constraints:** jedno kodowanie wyniku jak dotąd. Testy: render przy sile 0 nie ma filtra `lut3d` w poleceniu ffmpeg; przy sile 0,6 i wzorze ciepłym średnie b wyniku jest większe niż przy sile 0; wzór bez `kolorystyka` renderuje się bez błędu.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.3 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/render.py, src/kolor.py, src/konfiguracja.py, .env.example, src/bot.py, tests/test_render.py. Weryfikacja: python -m pytest -q
```

### [Task 5.4: Pomiar]
- **Objective:** `Pomiary/measure_kolor.py`, wynik w `outputs/pomiar_kolor.json` i arkusze PNG.
- **Context/Inputs:** dla każdego wzoru z `dane/probki/wzory/` i zestawu materiałów z `dane/probki/materialy/` (gdy brak: syntetyczne, barwne zdjęcia z generatora) render przy sile 0; 0,6 i 1,0. Raport: odległość ΔE76 średniej Lab wyniku od średniej wzoru dla każdej siły, różnica odchyleń, narzut czasu renderu przy sile 0,6 względem 0 w %. Arkusz na wzór: pierwszy wiersz to 4 klatki wzoru, kolejne to po 4 klatki wyniku dla każdej siły, najwyżej około 1600x1600 px: `outputs/kolor_<wzor>.png`.
- **Constraints:** próg: przy sile 0,6 ΔE mniejsze niż przy sile 0 dla każdego wzoru. Wybór siły domyślnej należy do oceniającego.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.4 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/render.py, src/kolor.py, src/analyze.py, tests/generuj.py. Weryfikacja: python Pomiary/measure_kolor.py
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar kopii: co najmniej 95% zgodnych cięć i co najmniej 2 razy krótsza analiza na każdym prawdziwym wzorze.
- Pomiar koloru: ΔE przy sile 0,6 mniejsze niż przy 0 dla każdego wzoru; arkusze powstały.
- Test ręczny (Ty): `python src/analyze.py --wszystkie`, potem ten sam projekt z `SILA_KOLORU=0` i `0,6` (w `.env` jako `0.6`); różnica widoczna, skóra i niebo nie wyglądają nienaturalnie.

## Commity
1. `analiza: lekka kopia dużych wzorów`
2. `kolor: statystyki Lab wzoru`
3. `kolor: LUT przeniesienia barw w renderze`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 5 według Pomiary/PLAN_EDITY_5_KOLOR.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie) oraz zalecana siła domyślna.
```
1. `git log --oneline main..kolor`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_kopia.py` i `python Pomiary/measure_kolor.py`: progi zgodności cięć, przyspieszenia i ΔE.
3. Arkusze `outputs/kolor_*.png`: przy której sile wynik jest najbliżej nastroju wzoru bez przebarwień.
4. `src/analyze.py`: kopia ma tyle klatek co oryginał, dźwięk i metadane idą z oryginału, jednostki Lab i kolejność kanałów. `src/kolor.py`: kolejność osi w `.cube`, ograniczenie stosunku odchyleń. `src/render.py`: LUT jako pierwszy filtr przebiegu końcowego, przed napisami, jeśli część 6 już jest.
