# Część 2: analiza wzoru

**Status 2026-09-22:** wykonana (commity `4e3c6ed`, `4e7c576`) plus decyzja właściciela `START_BPM = 150` (`0e84cba`, scalone do `main` w PR #1, `4b929c9`); 62 testy, pomiar A w progach, pomiar B na dwóch prawdziwych wzorach 4K z `dane/wzory/Edity/`. Odbiór 2026-09-22 (Opus): OK, domyślny ContentDetector potwierdzony, szczegóły w `ROZWOJ.md`.
**Zależy od:** części 1 (commit `bot: dostęp właściciela, wzór i materiały`).
**Efekt:** po `/wzor` i wysłaniu mp4 bot w tle analizuje wzór, zapisuje `wzor.json` (cięcia, tempo, uderzenia, cięcia w jednostkach uderzeń) i odpisuje podsumowaniem.
**Nowe pliki:** `src/analyze.py`, `tests/generuj.py`, `tests/test_analiza.py`, `Pomiary/measure_analiza.py`.
**Zmieniane:** `src/bot.py` (plik wzoru idzie do analizy), `src/magazyn.py` (dopisz `najnowszy_wzor`), `src/komunikaty.py`, `requirements.txt`, `tests/test_bot.py`.
**Od właściciela:** 3 do 5 wzorów mp4 w `dane/probki/wzory/`, tylko do pomiaru.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_2_ANALIZA.md, zaczynając od „Stan wejściowy”. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Na koniec uruchom pomiar i zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, zanim powstał kod. Jeżeli nazwy lub kontrakty z poprzednich części nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edit wideo 9:16 z materiałów właściciela według struktury wzorcowego editu (cięcia na uderzeniach, tempo, kolorystyka, sposób podania tekstu), z muzyką z biblioteki właściciela w `dane/muzyka/` (licencja nie jest warunkiem, decyzja 6 w mapie). Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
- Środowisko: lokalnie Windows 11, Python 3.13, ffmpeg i ffprobe 8.1 w PATH, brak Dockera. Serwer: Docker (obraz Debian) na Ubuntu 22.04. Ścieżki przez pathlib, procesy jako lista argumentów, bez powłoki.
- Reguły repo:
  1. Każda zmiana ma pomiar w `Pomiary/measure_<temat>.py`, tylko tam wolno pisać komentarze. Skrypt zaczyna od `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` i zapisuje wyniki do `outputs/` po każdej sekcji.
  2. Zero komentarzy i docstringów w `src/` i `tests/`.
  3. Nazwy funkcji bez `_` na początku, nazewnictwo po polsku (moduły `bot`, `analyze`, `music`, `render` zachowują nazwy z KONTEKST).
  4. Komunikaty bota, README i commity bez myślników i półpauz wewnątrz zdań.
  5. Commity bez wzmianek o AI i bez Co-Authored-By. Zdalne repo `origin` na GitHubie (dodane po części 1): push tylko na prośbę właściciela, a przed nim sprawdź, że `.env`, `dane/`, `outputs/` i `Pomiary/` nie są w indeksie.
  6. Każde wywołanie ffmpeg i ffprobe z zamkniętym stdin (`-nostdin` albo `stdin=DEVNULL`), inaczej proces potomny potrafi zawisnąć.
- Testy: `python -m pytest -q` z katalogu głównego, cały zestaw poniżej 60 s. Media testowe generowane w locie w małej rozdzielczości (270x480), nigdy z `dane/`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`git log --oneline` zawiera commit `bot: dostęp właściciela, wzór i materiały`, a `python -m pytest -q` przechodzi. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 1 (streszczenie)
- `magazyn.nowy_wzor(katalog_danych) -> Path` tworzy `dane/wzory/<id>/`, bot zapisuje tam `zrodlo.<ext>`.
- `kolejka.uruchom(argumenty, limit_s, katalog) -> Wynik` (async, pola `kod`, `stdout`, `stderr`, `czas_s`, `przekroczono_czas`), `Kolejka.dodaj(zadanie) -> pozycja`.
- `bot.utworz_dispatcher(konf, kolejka)`; komunikaty w `src/komunikaty.py`; testy bota korzystają z fałszywej sesji z `tests/pomocnicze.py`.

## Kontrakt ustalany: wzor.json (wersja 1)
```json
{"wersja": 1, "id": "20260921_153012",
 "zrodlo": {"czas_s": 15.03, "szerokosc": 1080, "wysokosc": 1920, "fps": 30.0, "ma_dzwiek": true},
 "ciecia_s": [0.0, 0.533, 1.067],
 "tempo_bpm": 120.2,
 "uderzenia_s": [0.121, 0.62],
 "ciecia_uderzenia": [-0.25, 0.75, 1.75],
 "koniec_uderzenia": 29.75,
 "kolorystyka": null, "tekst": null}
```
- `ciecia_s`: początki ujęć; pierwszy to 0.0, ściśle rosnące, wszystkie mniejsze od `czas_s`.
- `uderzenia_s`: czasy uderzeń na osi czasu dźwięku zdekodowanego przez ffmpeg. Pusta lista przy braku dźwięku albo mniej niż 2 wykrytych uderzeniach; wtedy `tempo_bpm`, `ciecia_uderzenia` i `koniec_uderzenia` mają wartość `null`.
- Pozycja czasu t w uderzeniach: między uderzeniem i oraz i+1 to `i + (t − b_i) / (b_{i+1} − b_i)`; przed pierwszym i po ostatnim uderzeniu ekstrapolacja medianą odstępu. `ciecia_uderzenia` to pozycje cięć zaokrąglone do 0,25, bez duplikatów po zaokrągleniu (zostaje pierwszy). `koniec_uderzenia` to pozycja `czas_s` zaokrąglona tak samo.
- `kolorystyka` i `tekst` są zarezerwowane dla części 5 i 6.
- Wszystkie liczby to zwykłe liczby JSON, nie typy numpy; czasy z dokładnością do 1 ms.

**Funkcje** (korzystają z nich części 3 do 6):
- `analyze.metadane(sciezka) -> dict` z kluczami jak w `zrodlo`.
- `analyze.analizuj_rytm(sciezka) -> tuple[float | None, list[float]]`: przyjmuje dowolny plik z dźwiękiem; ffmpeg dekoduje go do WAV mono 22050 Hz i dopiero ten plik czyta librosa.
- `analyze.wykryj_ciecia(sciezka, min_klatek: int = 3) -> list[float]`.
- `analyze.pozycja_w_uderzeniach(t, uderzenia) -> float` i odwrotna `analyze.czas_z_pozycji(p, uderzenia) -> float`, z tą samą ekstrapolacją.
- `analyze.kwantyzuj(pozycje, krok=0.25) -> list[float]`.
- `analyze.analizuj_wzor(sciezka, wzor_id) -> dict`.
- CLI `python src/analyze.py <wejscie> <wyjscie.json>`: kod 0 i plik JSON; plik bez strumienia wideo daje kod różny od 0 i jedną linię na stderr.
- `magazyn.najnowszy_wzor(katalog_danych) -> Path | None`: `wzor.json` najnowszego wzoru; katalogi bez `wzor.json` pomijane.
- `tests/generuj.py`: `wideo_z_cieciami(sciezka, ciecia_s, czas_s, fps=30, rozmiar=(270, 480), bpm=None, pierwsze_uderzenie_s=0.0, blyski_s=())` oraz `klik(sciezka_wav, bpm, czas_s, pierwsze_uderzenie_s=0.0, sr=22050)`.

## Zadania

### [Task 2.1: Generator mediów testowych]
- **Objective:** `tests/generuj.py` z `wideo_z_cieciami` i `klik`.
- **Context/Inputs:** ujęcia w kolorach daleko od siebie w odcieniu, cięcie dokładnie w klatce `round(t*fps)`. Przy `bpm` ścieżka kliknięć zakodowana w AAC, bez `bpm` plik nie ma ścieżki dźwięku. `blyski_s` podmienia pojedyncze klatki w tych chwilach na białe. Klatki najprościej podać ffmpegowi jako surowe dane z numpy.
- **Constraints:** samosprawdzenie w `tests/test_analiza.py`: liczba klatek (`ffprobe -count_frames`) równa `round(czas_s*fps)`; plik z `bpm` ma strumień audio, bez `bpm` go nie ma; pierwsze kliknięcie w WAV zaczyna się w `pierwsze_uderzenie_s` z dokładnością do 1 ms.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 2.1 z Pomiary/PLAN_EDITY_2_ANALIZA.md. Weryfikacja: python -m pytest -q tests/test_analiza.py
```

### [Task 2.2: Cięcia i rytm]
- **Objective:** w `src/analyze.py` funkcje `metadane`, `wykryj_ciecia`, `analizuj_rytm`, `pozycja_w_uderzeniach`, `czas_z_pozycji`, `kwantyzuj` z testami.
- **Context/Inputs:** do `requirements.txt` dochodzą `scenedetect[opencv-headless]` (`ContentDetector`), librosa, numpy, soundfile. fps z pola `r_frame_rate` ffprobe. Na Pythonie 3.13 import librosa może wymagać pakietów `standard-aifc` i `standard-sunau` (niepewne, zależy od wersji).
- **Constraints:** każdy punkt to test w `tests/test_analiza.py`:
  1. ujęcia po 4 i 6 klatek: wszystkie cięcia znalezione z dokładnością do 1 klatki. PySceneDetect 0.6 ma domyślnie `min_scene_len=15` i po cichu skleja szybkie cięcia, stąd parametr `min_klatek`.
  2. pojedyncza biała klatka między ujęciami nie tworzy osobnego ujęcia.
  3. wideo 30000/1001 fps: cięcia w sekundach poprawne z dokładnością do 1 klatki (fps jako ułamek).
  4. tempo i uderzenia to `float` Pythona; librosa potrafi zwrócić tempo jako tablicę numpy.
  5. oś czasu: klik 120 BPM z pierwszym uderzeniem w 0,5 s zakodowany raz do mp3, raz do mp4 z AAC; mediana odległości wykrytych uderzeń od najbliższego kliknięcia do 15 ms w obu plikach. Dlatego dekodujemy zawsze ffmpegiem: render tnie dźwięk ffmpegiem, więc osie czasu muszą być te same, a dekodery mp3 różnie traktują opóźnienie kodera (około 25 ms).
  6. kliki 90, 120 i 150 BPM: tempo z błędem do 2% po uwzględnieniu oktawy (x2, x0,5), co najmniej 90% kliknięć ma wykryte uderzenie w promieniu 35 ms.
  7. `czas_z_pozycji(pozycja_w_uderzeniach(t))` zwraca t z błędem poniżej 1e-6 dla t przed pierwszym uderzeniem, pomiędzy i po ostatnim, przy nierównych odstępach.
  8. `kwantyzuj([1.0, 1.05, 2.0])` daje `[1.0, 2.0]`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 2.2 z Pomiary/PLAN_EDITY_2_ANALIZA.md; otwórz tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_analiza.py
```

### [Task 2.3: Szablon wzoru i CLI]
- **Objective:** `analizuj_wzor`, CLI w `src/analyze.py` i `magazyn.najnowszy_wzor`.
- **Context/Inputs:** kontrakt `wzor.json` powyżej; `src/magazyn.py` z części 1.
- **Constraints:** testy: wzór syntetyczny 120 BPM z cięciem na każde uderzenie daje `ciecia_uderzenia` o kolejnych różnicach 1,0; wideo bez dźwięku daje `null` w trzech polach rytmu i kod 0; `json.loads` pliku zwraca wyłącznie typy wbudowane; CLI na pliku tekstowym kończy się kodem różnym od 0 i jedną linią na stderr; `najnowszy_wzor` pomija katalog bez `wzor.json`, a bez wzorów zwraca `None`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 2.3 z Pomiary/PLAN_EDITY_2_ANALIZA.md; otwórz src/analyze.py, src/magazyn.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```

### [Task 2.4: Analiza w bocie]
- **Objective:** po zapisaniu `zrodlo.<ext>` bot kolejkuje analizę i odpisuje podsumowaniem.
- **Context/Inputs:** zadanie woła `kolejka.uruchom([sys.executable, <src>/analyze.py, zrodlo, wzor.json], limit_s=300)`; ścieżkę do `analyze.py` licz od pliku `bot.py`, nie od bieżącego katalogu. Przy dodaniu odpowiedź „Analizuję wzór”, z pozycją w kolejce, gdy większa niż 1. Sukces: czas wzoru, liczba ujęć, średnia długość ujęcia, tempo albo informacja o braku dźwięku, liczby z przecinkiem. Błąd: pierwsza linia stderr; przekroczony czas: osobny komunikat; `zrodlo` zostaje w obu przypadkach.
- **Constraints:** testy w `tests/test_bot.py` z podmienionym `uruchom`: wersja zapisująca przygotowany JSON daje jedną odpowiedź z liczbą ujęć; wersja z błędem daje komunikat z treścią błędu; `/status` dostaje odpowiedź, gdy analiza jeszcze trwa (podmienione `uruchom` czeka na `asyncio.Event`).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 2.4 z Pomiary/PLAN_EDITY_2_ANALIZA.md; otwórz src/bot.py, src/komunikaty.py, tests/test_bot.py, tests/pomocnicze.py. Weryfikacja: python -m pytest -q
```

### [Task 2.5: Pomiar]
- **Objective:** `Pomiary/measure_analiza.py`, wynik w `outputs/pomiar_analiza.json` i arkusze PNG.
- **Context/Inputs:** sekcja A (syntetyczna): tempo 70, 90, 110, 128, 150, 170 BPM razy trzy układy cięć (co uderzenie, co pół uderzenia, mieszany z ujęciami po 4 klatki). Raport: czułość i precyzja cięć przy tolerancji 1 klatki, błąd tempa w % po uwzględnieniu oktawy, liczba pomyłek o oktawę. Sekcja B (realna): każdy plik z `dane/probki/wzory/` (brak plików: sekcja pominięta z komunikatem), osobno dla `wykryj_ciecia` i dla `AdaptiveDetector` z parametrami domyślnymi. Raport: liczba cięć, mediana długości ujęcia, odsetek cięć w promieniu 40 ms od uderzenia albo połowy uderzenia, czas analizy. Arkusz na wzór i detektor: wiersz to ujęcie, kolumny to pierwsza, środkowa i ostatnia klatka; jeden obraz najwyżej około 1600x1600 px, żeby oceniający obejrzał go jednym odczytem (więcej ujęć, kolejne arkusze): `outputs/arkusz_<wzor>_<detektor>_<n>.png`.
- **Constraints:** progi: A 100% cięć i błąd tempa do 2% po uwzględnieniu oktawy dla wszystkich temp; B tylko raport, ocenia oceniający na arkuszach.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 2.5 z Pomiary/PLAN_EDITY_2_ANALIZA.md; otwórz src/analyze.py i tests/generuj.py. Weryfikacja: python Pomiary/measure_analiza.py
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar A: 100% cięć, tempo z błędem do 2% po uwzględnieniu oktawy. Pomiar B: arkusze powstały dla każdego wzoru i obu detektorów.
- Test ręczny (Ty): `/wzor` i prawdziwy wzór; podsumowanie przychodzi w mniej niż minutę, liczba ujęć i tempo wyglądają rozsądnie.

## Commity
1. `analiza: metadane, cięcia, rytm i szablon wzoru`
2. `bot: analiza wzoru w kolejce`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 2 według Pomiary/PLAN_EDITY_2_ANALIZA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie) oraz decyzja, który detektor zostaje domyślny.
```
1. `git log --oneline -6` i `git log --oneline main..analiza-wzoru`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md` (w tym pomyłka tempa 3:2 i decyzja `START_BPM = 150`).
2. `outputs/pomiar_analiza.json`: sekcja A wobec progów, sekcja B dla dwóch wzorów. Pełny przebieg `python Pomiary/measure_analiza.py dane/wzory/Edity` trwa około 6 minut, uruchamiaj go tylko przy wątpliwości.
3. Dwa arkusze tego samego wzoru (ContentDetector i AdaptiveDetector). Wiersz, którego pierwsza i ostatnia klatka pokazują różne sceny, to przegapione cięcie. Wiersz nie do odróżnienia od sąsiada to fałszywe cięcie. Na tej podstawie wybierz detektor.
4. `src/analyze.py`: wartość `min_klatek`, dekodowanie ffmpegiem przed librosą, doprecyzowanie uderzeń (`doprecyzuj_uderzenia`), ekstrapolacja medianą odstępu, typy w JSON, a także czy `START_BPM = 150` nie psuje wolnych temp (sekcja A ma przypadek 70 BPM).
