# Część 4: dźwięk wzoru i biblioteka muzyki

**Zależy od:** części 3 z naprawą 3.7 (`main` po PR #5, commit `e16c604` `render: dźwięk przycinany na wejściu i wymuszona długość wyniku`).
**Gałąź:** `muzyka` od `main`.
**Efekt:** render sam wybiera utwór z `dane/muzyka/`. Gdy biblioteka ma utwór, który gra we wzorze, render rozpoznaje go po odcisku dźwięku i montuje na tym samym fragmencie: cięcia wypadają w tych samych momentach utworu co we wzorze, więc drop wzoru trafia w drop utworu. Gdy takiego utworu nie ma, render wybiera utwór o najbliższym tempie (z uwzględnieniem oktawy) i fragment, którego przebieg głośności najlepiej pasuje do wzoru. Podpis wyniku mówi, jaki to utwór i od której sekundy.
**Tryb `dzwiek_wzoru` wyłączony decyzją właściciela 2026-09-23 (zadanie 4.2, `ROZWOJ.md`):** na prawdziwej bibliotece (dwa utwory hardstyle) rozpoznanie po chromie nie odróżnia niezawodnie właściwego utworu od drugiego, nawet po separacji harmoniczno-perkusyjnej. `music.dopasuj_odcisk` i `music.wybierz_mnoznik`/`dopasuj_po_dzwieku` zostają w kodzie i mają testy jednostkowe (działają poprawnie na syntetycznych, wyraźnie różnych nagraniach), ale `wybierz_utwor` nigdy nie wchodzi w tryb `dzwiek_wzoru`: każdy wzór z tempem idzie od razu w tryb `tempo`. Renderu dla `0915`/`0922` należy się spodziewać w trybie `tempo`, nie `dzwiek_wzoru`; referencje 40,36 s / 23,29 s w tym pliku i w zadaniu 4.4 (sekcja B) są nieaktualne, dopóki tryb nie wróci.
**Dlaczego tak (przegląd 2026-09-23, `ROZWOJ.md`):** `0915` to „Hot N Cold (Hardstyle)” od 40,36 s, a `0922` to „Ex's And Oh's (Hardstyle)” od 23,29 s (korelacja chromy 0,78 i 0,81, inne pary najwyżej 0,12). `0921` nie ma utworu w bibliotece. Reguła „najmocniejszy fragment” z poprzedniej wersji planu chybiała: w `0915` o 3 uderzenia, a w `0922` okno wzoru było dopiero 158. z 347. Z kolei `start_bpm=120` dawał dla „Ex's And Oh's” 88,3 zamiast 175,2 BPM. Dzisiejszy render bierze najwcześniejsze uderzenie, więc edit do `0915` idzie na intro utworu, a wzór leży od 40 s.
**Nowe pliki:** `src/music.py`, `tests/test_muzyka.py`, `Pomiary/measure_muzyka.py`, `Pomiary/arkusz.py`.
**Zmieniane:** `src/analyze.py`, `tests/test_analiza.py`, `tests/generuj.py`, `src/render.py`, `tests/test_render.py`, `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`.
**Od właściciela:**
- przed startem `git pull` na `main`, bo lokalny `main` bywa za `origin/main`;
- w `dane/muzyka/` dźwięki wzorów, które mają być obsłużone: najlepiej pełne utwory w tej samej wersji i tempie co na TikToku. Nazwy plików bez dopisku „ (1)”, bo nazwa trafia do podpisu. Ta sama zawartość na serwerze (`scp -r dane/muzyka root@<adres>:/opt/edity-bot/dane/`, właściciel plików UID 1000);
- przykładowe zdjęcia i klipy w `dane/probki/materialy/` (np. dzisiejsze `dane/zdjęcia/` i `dane/gify/`), potrzebne do arkuszy porównawczych.

**Poza zakresem:**
- `licencje.csv` i dane licencji w podpisie (odłożone, decyzja 6 w mapie);
- dźwięk przyspieszony („sped up”) albo w innej tonacji niż plik w bibliotece: odcisk wtedy nie pasuje i działa dobór po tempie.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_4_MUZYKA.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Na koniec uruchom pomiar i zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, przepisany 2026-09-23 po przeglądzie prawdziwych wzorów (`ROZWOJ.md`, wpisy „przegląd planów 4 do 6” i „przepisanie planów 4 do 9”). Kotwice `plik:linia` pochodzą z commita `57ba8fe` (stan po części 3 i zadaniu 3.7). Po wcześniejszych częściach mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edity wideo 9:16 na TikToka z dostarczonych materiałów. Wzorem jest gotowy edit: bot odtwarza jego strukturę i styl, a muzykę bierze z biblioteki właściciela w `dane/muzyka/`. Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
  - Edity promują czapki marki właściciela 1993 Supply (2026-09-24). Plansza końcowa pokazuje produkt albo stronę sklepu, a znak wodny marki leży na całym edicie poza planszą (wzór `0914`, zadanie 8.6).
  - Prawdziwe wzory (`0914`, `0915`, `0921`, `0922`, `0923`) mają ten sam format: hak (pierwsze 4 do 11 s, naturalne kolory, napis), drop (od niego pełnoekranowa nakładka graficzna i mocny grading), montaż i plansza końcowa około 1 s (mapa, decyzja 15). `0923` ma dodatkowo napisy słowo po słowie w rytmie i gwiazdy wokół postaci przed dropem, czego plany nie odtwarzają.
  - Biblioteka muzyki to dźwięki samych wzorów (decyzja 14).
- Środowisko:
  - lokalnie: Windows 11, Python 3.13 w `venv` repo (`venv/Scripts/python.exe`, zależności przypięte w `requirements.txt`), ffmpeg i ffprobe 8.1 w PATH, brak Dockera;
  - serwer: Docker (obraz Debian, ffmpeg 7.1) na Ubuntu 24.04, bot z limitem 2 CPU i 5 GB (od 2026-09-24, wcześniej 3 GB; serwer ma 7,6 GB);
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
- Czas w pomiarach (od 2026-09-24):
  - na laptopie czas zegara skacze 2 do 3 razy między przebiegami. Pomiar B części 8 dał przebieg z nakładką o 45% szybszy niż bez niej;
  - progi narzutu licz z czasu procesora: w ffmpeg flaga `-benchmark` i suma `utime` oraz `stime` z linii `bench:` (w pomiarze podmień `render.uruchom_ffmpeg`), a w Pythonie `time.process_time()`;
  - gdzie czasu procesora nie da się zebrać, bierz medianę z 5 przebiegów na przemian. Próg oceniaj tylko wtedy, gdy rozrzut przebiegów bazowych jest poniżej 20%, a inaczej wpisz „niepewny” zamiast „w progu”;
  - czas zegara podawaj w raporcie.
- Dziennik `Pomiary/ROZWOJ.md`: przeczytaj na starcie (stan, znane problemy, decyzje), dopisuj wpis po każdym zadaniu, decyzji i odkryciu, bez tokenu i wartości z `.env`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`main` zawiera commit `e16c604`, a `python -m pytest -q` przechodzi w całości (liczbę testów zanotuj w `ROZWOJ.md` jako punkt wyjścia). `git diff --stat 57ba8fe -- src/ tests/` pokazuje, czy kotwice niżej są aktualne. Utwórz gałąź `muzyka` od `main`. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 2 i 3 (stan z `57ba8fe`)
- `src/analyze.py`:
  - `START_BPM = 150.0` (19), `WERSJA_WZORU = 1` (13);
  - `zdekoduj_do_wav(sciezka, cel)` (112) dekoduje do WAV mono 22050 Hz (`CZESTOTLIWOSC_ANALIZY`);
  - `analizuj_rytm(sciezka) -> (tempo_bpm | None, uderzenia_s)` (123) woła `warnings.filterwarnings("ignore")` dla całego procesu, potem `beat_track` z krokiem 128 i `doprecyzuj_uderzenia` (150);
  - `czas_z_pozycji` (193) ekstrapoluje medianą odstępu;
  - `analizuj_wzor(sciezka, wzor_id)` (215) zwraca `wersja`, `id`, `zrodlo`, `ciecia_s`, `tempo_bpm`, `uderzenia_s`, `ciecia_uderzenia`, `koniec_uderzenia`, `kolorystyka: null`, `tekst: null`;
  - `zapisz_json` (247) zapisuje atomowo;
  - `main(argv)` (255) przyjmuje dokładnie `<wejscie> <wyjscie.json>` i tak woła go bot (`analizuj_wzor_w_tle`, bot.py:332).
- `src/render.py`:
  - `plan_ujec(wzor, uderzenia_utworu, materialy, fps, start_uderzenie=None)` (176) ma gałąź z uderzeniami (183 do 188) i gałąź bez rytmu z `ciecia_s` (189 i 190);
  - `znajdz_start_uderzenia` (129) bierze najwcześniejsze uderzenie;
  - `renderuj(wzor_json, katalog_projektu, utwor, wyjscie, ...)` (300) woła `analyze.analizuj_rytm(utwor)` (342) i liczy `dlugosc_wstawki_s` z planu wstępnego (344 do 347), a podsumowanie ma `utwor: {plik, start_s}` (379);
  - `przebieg_koncowy` (244) przycina utwór opcjami wejścia `-ss` i `-t` (261);
  - CLI `glowna` (390) wymaga `--utwor`.
- `src/bot.py`:
  - `renderuj_w_tle` (153) przekazuje `--utwor`;
  - `obsluz_cmd_gotowe` (211) odmawia bez `dane/muzyka/staly.mp3` (241 do 244, `komunikaty.BRAK_UTWORU`);
  - `obsluz_cmd_status` (283).
- `src/komunikaty.py`: `podsumowanie_renderu` (95), `status_kolejki` (108), `BRAK_UTWORU` (37).
- `tests/generuj.py`:
  - `klik(sciezka_wav, bpm, czas_s, pierwsze_uderzenie_s=0.0, sr=22050)` (25);
  - `wideo_z_cieciami(sciezka, ciecia_s, czas_s, fps=30, rozmiar=(270, 480), bpm=None, pierwsze_uderzenie_s=0.0, blyski_s=())` (62): dźwięk tylko jako klik przy podanym `bpm`.

## Kontrakty ustalane w tej części

**`analyze.analizuj_dzwiek(sciezka) -> dict | None`**: dekoduje jeden raz przez `zdekoduj_do_wav` i z jednego sygnału liczy wszystko:
```json
{"czas_s": 151.8, "tempo_bpm": 164.1, "uderzenia_s": [1.46, 1.83],
 "energia_uderzen": [0.071],
 "odcisk": {"krok_chroma_s": 0.09288, "chroma": [[0.12, 0.0, 0.4, 0.1, 0.0, 0.0, 0.9, 1.0, 0.2, 0.0, 0.1, 0.3]],
            "krok_obwiedni_s": 0.01161, "obwiednia": [0.3, 0.5]}}
```
- Zwraca `None`, gdy pliku nie da się zdekodować jako dźwięk albo sygnał jest krótszy niż 1 s.
- Tempo i uderzenia liczone jak dziś w `analizuj_rytm`, z `START_BPM = 150` dla wszystkiego, wzorów i utworów (decyzja 11), bez parametru `start_bpm`. Gdy tracker nic nie znajdzie, `tempo_bpm` to `null`, a `uderzenia_s` i `energia_uderzen` to `[]`; odcisk powstaje mimo to.
- `energia_uderzen[i]` to RMS sygnału między uderzeniem i oraz i+1, więc lista jest o jeden krótsza od `uderzenia_s`.
- `odcisk.chroma` to `librosa.feature.chroma_stft` z `hop_length=2048`, czyli krok 2048/22050 s: jeden wiersz 12 wartości na ramkę, zaokrąglone do 4 miejsc.
- `odcisk.obwiednia` to `librosa.onset.onset_strength` z `hop_length=256`, zaokrąglona do 4 miejsc.
- Wszystkie liczby to `float` Pythona.
- `analizuj_rytm(sciezka)` zostaje z tą samą sygnaturą i wynikiem, ale jako nakładka na `analizuj_dzwiek`. Dotychczasowe testy analizy przechodzą bez zmian.
- Ostrzeżenia librosy wyciszane tylko w bloku `warnings.catch_warnings()` wokół jej wywołań, nie w całym procesie (znany problem 0e).

**`wzor.json` w wersji 2** (`WERSJA_WZORU = 2`):
- dochodzą `energia_uderzen` (dla uderzeń wzoru, `null` bez rytmu) i `odcisk_dzwieku` (pole `odcisk` z `analizuj_dzwiek`, `null` bez dźwięku);
- `analizuj_wzor` wywołuje `analizuj_dzwiek` jeden raz, zamiast `analizuj_rytm`;
- plik rośnie do około 200 KB i to jest w porządku;
- render dalej czyta z katalogu wzoru wyłącznie `wzor.json`. Odcisk to dane wyliczone, a nie dźwięk: nie da się z niego odtworzyć dźwięku wzoru.

**CLI `python src/analyze.py --wszystkie [--katalog-danych dane]`**:
- dla każdego katalogu `<katalog-danych>/wzory/<id>/` z plikiem `zrodlo.*` analizuje wzór od nowa i nadpisuje `wzor.json` (to samo `id`);
- katalog bez `zrodlo.*` pomija z linią w logu;
- na koniec drukuje liczby przeliczonych, pominiętych i błędów;
- kod 0, gdy nie było błędów;
- wywołanie z dwoma argumentami (bot) działa bez zmian;
- na serwerze uruchamiane po wdrożeniu każdej części, która zmienia `wzor.json`: `docker compose exec bot python src/analyze.py --wszystkie` (około minuty na wzór 4K).

**`dane/muzyka/indeks.json`** (wersja 2; wcześniejszego formatu nie ma, więc bez migracji):
```json
{"wersja": 2, "utwory": [{"plik": "Hot N Cold (Hardstyle).mp3", "rozmiar": 5374087, "zmieniony": 1758650000.0,
  "czas_s": 151.8, "tempo_bpm": 164.1, "uderzenia_s": [1.46], "energia_uderzen": [], "odcisk": {"krok_chroma_s": 0.09288}}]}
```
Wpis to wynik `analizuj_dzwiek` plus `plik`, `rozmiar` i `zmieniony` (czas modyfikacji). Indeks ma około 300 KB na utwór, więc przy 15 utworach kilka MB, a wczytanie trwa poniżej sekundy.

**`src/music.py`**:
- `ROZSZERZENIA_MUZYKI = {"mp3", "wav", "m4a", "ogg", "flac", "mp4"}`.
- `pliki_muzyki(katalog) -> list[Path]`: pliki z tymi rozszerzeniami, posortowane po nazwie, bez `indeks.json`.
- `indeksuj(katalog) -> tuple[dict, int]` zwraca indeks i liczbę przeanalizowanych plików:
  - analizuje nowe i zmienione pliki (inny rozmiar albo czas modyfikacji);
  - usuwa wpisy plików skasowanych;
  - plik bez dźwięku (np. mp4 bez ścieżki audio, `analizuj_dzwiek` daje `None`) pomija z ostrzeżeniem w logu, a reszta indeksu powstaje normalnie;
  - zapisuje przez `analyze.zapisz_json`.
- `dopasuj_odcisk(odcisk_wzoru, odcisk_utworu) -> tuple[float, float] | None` zwraca `(zgodnosc, przesuniecie_s)`, a `None`, gdy wzór jest dłuższy niż utwór:
  - zgrubnie: dla każdego przesunięcia `o` (w ramkach chromy) od 0 do `len(chroma_utworu) − len(chroma_wzoru)` liczy współczynnik korelacji Pearsona między chromą wzoru a oknem utworu. Obie tablice przed porównaniem są normalizowane: od każdego z 12 pasm odejmuje się jego średnią w obrębie okna, całość dzieli przez odchylenie, a potem się ją spłaszcza. Wygrywa najlepsze `o`, a przy remisie najmniejsze;
  - dokładnie: w oknie ±0,2 s wokół wyniku zgrubnego liczy Pearsona obwiedni wzoru i utworu po przesunięciach co jedną ramkę obwiedni. `przesuniecie_s` to najlepsze z nich, a `zgodnosc` to wartość zgrubna (z chromy);
  - obie liczby zaokrąglone do 3 miejsc.
- `PROG_ZGODNOSCI = 0.5`: na prawdziwych danych pary pasujące mają 0,78 i 0,81, a niepasujące najwyżej 0,12.
- `wybierz_utwor(wzor, indeks) -> dict`:
```json
{"plik": "Hot N Cold (Hardstyle).mp3", "tryb": "dzwiek_wzoru", "zgodnosc": 0.78, "przesuniecie_s": 40.36,
 "tempo_bpm": 164.1, "mnoznik": 1.0, "uderzenia_s": [1.46], "start_uderzenie": null, "odleglosc_bpm": 0.0}
```
  Zasady po kolei:
  1. `dzwiek_wzoru`:
     - dotyczy wzoru z `odcisk_dzwieku`: dla każdego utworu liczy `dopasuj_odcisk`;
     - najwyższa zgodność co najmniej `PROG_ZGODNOSCI` wygrywa, a przy remisie pierwszy alfabetycznie;
     - wynik ma `przesuniecie_s`, `uderzenia_s` utworu bez zmian (tylko do raportu), `start_uderzenie: null` i `mnoznik: 1.0`;
     - `odleglosc_bpm` liczona jak w trybie tempa, gdy oba tempa są znane, inaczej `null`.
  2. `tempo`: gdy wzór ma `tempo_bpm` i `ciecia_uderzenia`, a żaden utwór nie przeszedł progu zgodności (albo wzór nie ma odcisku).
     - Warunki kandydata: ma znane tempo i mieści całe okno wzoru na swojej siatce uderzeń. Musi istnieć całkowite `s`, dla którego `czas_z_pozycji(s + c_0)` jest nieujemny, a `s + koniec_uderzenia` nie przekracza ostatniego indeksu uderzeń, więc na końcu nie ma ekstrapolacji.
     - Odległość: odległość tempa `b` od tempa wzoru `T` to minimum z `|b − T|`, `|2b − T|` i `|b/2 − T|`.
     - Mnożnik 2 zagęszcza siatkę: dodaje środki między uderzeniami, a energia połówki jest równa energii uderzenia. Mnożnik 0,5 bierze co drugie uderzenie od indeksu 0, a energia to średnia dwóch.
     - `uderzenia_s` w wyniku są już po tej korekcie i idą prosto do `plan_ujec`.
     - Wybór: wygrywa najmniejsza odległość, a przy remisie pierwszy alfabetycznie.
     - `start_uderzenie`: dopuszczalne `s`, dla którego profil energii utworu na uderzeniach `s + j` najlepiej koreluje (Pearson) z profilem energii wzoru na uderzeniach `j`. Liczą się wszystkie `j` z okna wzoru (od `floor(c_0)` do `ceil(koniec_uderzenia) − 1`), które mają energię po obu stronach. Przy remisie albo stałym profilu wygrywa najmniejsze `s`. Dzięki temu cichy hak wzoru trafia w cichy fragment utworu, a drop w drop, zamiast brać po prostu najgłośniejsze okno.
  3. `bez_rytmu`: wzór bez tempa i bez pasującego odcisku dostaje pierwszy alfabetycznie utwór nie krótszy niż wzór, z `mnoznik: 1.0`, `start_uderzenie: null` i `przesuniecie_s: 0.0`.
  4. Brak kandydata: `ValueError` z liczbą odrzuconych z każdego powodu, np. „Brak pasującego utworu: bez tempa 1, za krótkie 2”.

  Wynik jest deterministyczny: dwa wywołania na tych samych danych dają identyczny słownik.
- CLI:
  - `python src/music.py indeksuj [--katalog dane/muzyka]` drukuje tabelę (plik, czas, tempo, liczba uderzeń) i liczbę przeanalizowanych plików;
  - `python src/music.py wybierz --wzor <wzor.json> [--katalog dane/muzyka]` drukuje wybór (`uderzenia_s` jako liczbę elementów) i zgodność wzoru z każdym utworem.

**`render.plan_ujec(wzor, uderzenia_utworu, materialy, fps, start_uderzenie=None, przesuniecie_s=None)`**:
- Nowy parametr `przesuniecie_s`: gdy nie jest `None`, cięcia to `ciecia_s` wzoru, a koniec to `zrodlo.czas_s`. `start_audio_s = przesuniecie_s`, więc edit ma dokładnie długość i czasy cięć wzoru, a dźwięk leci od tego miejsca utworu. W przeciwnym razie zachowanie jak dziś.
- Każde ujęcie dostaje pole `numer_wzoru`: indeks cięcia wzoru, od którego się zaczyna (0 dla pierwszego). Ujęcia o 0 klatkach wypadają jak dziś, więc `numer_wzoru` może przeskoczyć. Części 8 i 5 mapują po nim sekcje i kolor.

**Render**: `renderuj(wzor_json, katalog_projektu, utwor: Path | None, wyjscie, szerokosc=1080, wysokosc=1920, fps=30, limit_mb=50, muzyka: Path | None = None)`:
- `utwor` podany: zachowanie jak dziś (`analizuj_rytm`, `plan_ujec` po uderzeniach od najwcześniejszego uderzenia), tryb `staly`. Z tej ścieżki korzysta `Pomiary/measure_render.py`.
- `utwor` pusty, a `muzyka` podana:
  - najpierw `music.indeksuj(muzyka)` i `music.wybierz_utwor(wzor, indeks)`;
  - potem `plan_ujec`: z `przesuniecie_s` w trybie `dzwiek_wzoru`, z `uderzenia_s` i `start_uderzenie` wyboru w trybie `tempo`, a bez rytmu w trybie `bez_rytmu`;
  - dźwięk z `muzyka / wybor["plik"]`;
  - plan wstępny do `dlugosc_wstawki_s` liczony tak samo jak plan właściwy.
- Oba puste: błąd „Brak utworu i katalogu muzyki”.
- Podsumowanie: `"utwor": {"plik": "...", "tryb": "dzwiek_wzoru" | "tempo" | "bez_rytmu" | "staly", "zgodnosc": 0.78 | null, "start_s": 40.36, "tempo_bpm": 164.1 | null, "mnoznik": 1.0}`.
- CLI: `--utwor` opcjonalny, nowy `--muzyka`. Bez obu kod 1 i jedna linia na stderr.

**Bot**:
- `renderuj_w_tle` przekazuje `--muzyka <katalog_danych>/muzyka` zamiast `--utwor`.
- `obsluz_cmd_gotowe` zamiast `staly.mp3` sprawdza, czy `music.pliki_muzyki` coś zwraca. Gdy nie, odpowiada `komunikaty.BRAK_MUZYKI` („Biblioteka muzyki jest pusta. Dodaj utwory do dane/muzyka.”) i nic nie trafia do kolejki. `BRAK_UTWORU` znika.
- Podpis wyniku (`komunikaty.podsumowanie_renderu`) dostaje drugą linię z nazwą pliku bez rozszerzenia, zależnie od trybu:
  - „Muzyka: Hot N Cold (Hardstyle), dźwięk wzoru od 40,4 s.”;
  - „Muzyka: X, dobór po tempie 164,1 BPM, od 12,3 s.”;
  - „Muzyka: X, od początku.”.
- `/status` dostaje wiersz „Muzyka: N utworów.”, liczony przez `music.pliki_muzyki`, bez analizy.
- Pierwszy montaż po dodaniu utworów buduje indeks (około 10 s na utwór w limicie 900 s). Na serwerze można go zbudować wcześniej: `docker compose exec bot python src/music.py indeksuj`.

**`Pomiary/arkusz.py`** (decyzja 17): `arkusz_porownawczy(wzor: Path, wynik: Path, cel: Path, klatek_na_s: float = 2.0, kolumny: int = 16, komorka=(108, 192)) -> Path`:
- N = `ceil(dłuższy czas × klatek_na_s)`;
- z każdego pliku N klatek równo rozłożonych w jego czasie: jedno wywołanie ffmpeg na plik z filtrem `fps=N/<czas pliku>`, skalowanie do komórki, klatki rawvideo do numpy;
- układ: wiersz wzoru, pod nim wiersz wyniku z tych samych ułamków długości, cienka jasna linia między parami;
- dla 32 s przy 2 klatkach na sekundę daje to 4 pary wierszy po 16 komórek, 1728x1536 px;
- używany przez pomiary części 4, 8, 5, 6 i 9.

## Zadania

### [Task 4.1: Analiza dźwięku i odcisk]
- **Objective:** `analyze.analizuj_dzwiek`, `wzor.json` w wersji 2, CLI `--wszystkie` i generator melodii.
- **Context/Inputs:**
  - kontrakty wyżej;
  - `src/analyze.py`: `zdekoduj_do_wav` (112), `analizuj_rytm` (123), `doprecyzuj_uderzenia` (150), `analizuj_wzor` (215), `main` (255);
  - `tests/generuj.py`: `klik` (25), `wideo_z_cieciami` (62);
  - nowe w generatorze:
    - `melodia(sciezka_wav, bpm, czas_s, ziarno=0, sr=22050, glosnosc=None) -> list[float]`: na każde uderzenie ton sinusoidalny o wysokości losowanej przez `numpy.random.default_rng(ziarno)` z 24 półtonów (dwie oktawy od 220 Hz), trwający pół uderzenia z obwiednią wykładniczą. Do tego klik na uderzeniu, żeby tracker znalazł tempo. `glosnosc` to lista par (od sekundy, mnożnik amplitudy), domyślnie stała. Funkcja zwraca czasy uderzeń;
    - ten sam parametr `glosnosc=None` w `klik`, bez zmiany domyślnego zachowania;
    - `wideo_z_cieciami(..., dzwiek: Path | None = None)`: gdy podany, plik WAV jest ścieżką dźwiękową zamiast kliku (`bpm` wtedy ignorowane).
- **Constraints:** dotychczasowe testy analizy przechodzą bez zmian. Nowe testy w `tests/test_analiza.py`:
  1. melodia 20 s: `odcisk.chroma` ma liczbę wierszy w granicy 2 od 20/0,09288, każdy po 12 wartości, a `obwiednia` w granicy 2 od 20/0,01161; wszystkie liczby to `float` Pythona;
  2. `energia_uderzen` jest o jeden krótsza od `uderzenia_s`; melodia z `glosnosc=[(0, 0.1), (10, 1.0)]` ma średnią energię uderzeń po 10 s co najmniej 5 razy większą niż przed;
  3. wideo bez dźwięku: `analizuj_dzwiek` daje `None`, a `analizuj_wzor` daje `odcisk_dzwieku: null` i `energia_uderzen: null`;
  4. `analizuj_wzor` na wideo z melodią daje `wersja: 2` i oba nowe pola;
  5. `--wszystkie` na katalogu danych z dwoma wzorami (jeden z `zrodlo.mp4`, drugi tylko z `wzor.json`): pierwszy przeliczony z tym samym `id` i `wersja: 2`, drugi nietknięty, kod 0;
  6. `warnings.filters` po `analizuj_rytm` jest taki sam jak przed wywołaniem.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.1 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/analyze.py, tests/generuj.py, tests/test_analiza.py. Weryfikacja: python -m pytest -q tests/test_analiza.py
```
- **Commit:** `analiza: odcisk dźwięku i energia uderzeń`

### [Task 4.2: Biblioteka i rozpoznanie dźwięku wzoru]
- **Objective:** `src/music.py` z `ROZSZERZENIA_MUZYKI`, `pliki_muzyki`, `indeksuj`, `dopasuj_odcisk`, `PROG_ZGODNOSCI`, `wybierz_utwor` i CLI.
- **Context/Inputs:** kontrakty wyżej; `analyze.analizuj_dzwiek`, `analyze.czas_z_pozycji` (193), `analyze.zapisz_json` (247); generator z zadania 4.1.
- **Constraints:** testy w `tests/test_muzyka.py`:
  1. rozpoznanie:
     - biblioteka: melodia A (ziarno 1) i melodia B (ziarno 2), obie 20 s przy 120 BPM;
     - wzór: odcisk fragmentu A od 7,3 s długości 6 s (fragment wycięty z WAV w teście);
     - oczekiwane: `wybierz_utwor` daje plik A, tryb `dzwiek_wzoru`, `przesuniecie_s` w granicy 0,015 s od 7,3 i zgodność co najmniej 0,8; zgodność z B poniżej 0,3;
  2. fragment melodii C (ziarno 3, spoza biblioteki) ma zgodność poniżej progu z A i B, więc wybór przechodzi do trybu `tempo`;
  3. wzór dłuższy niż utwór: `dopasuj_odcisk` daje `None`;
  4. tryb tempa (wzory z `odcisk_dzwieku: null`):
     - wzór 140 BPM, w bibliotece klik 70 BPM: mnożnik 2, dwa razy więcej uderzeń (z dokładnością do 1), odległość 0;
     - klik 128 BPM przy wzorze 64 BPM: mnożnik 0,5;
  5. profil energii zamiast najgłośniejszego okna:
     - utwór: klik 60 s przy 120 BPM z `glosnosc=[(0, 0.1), (30, 1.0)]`;
     - wzór: klik 16 s przy 120 BPM z `glosnosc=[(0, 0.1), (8, 1.0)]` i `odcisk_dzwieku: null`;
     - oczekiwane: `czas_z_pozycji(start_uderzenie + c_0, uderzenia_s)` wypada w granicy 1 uderzenia od 22 s (skok wzoru w 8 s trafia w skok utworu w 30 s), a nie po 30 s;
  6. dwa utwory w tej samej odległości tempa: wygrywa pierwszy alfabetycznie;
  7. brak kandydata: `ValueError` z liczbą odrzuconych z każdego powodu;
  8. `indeksuj`:
     - drugi przebieg bez zmian w katalogu analizuje 0 plików;
     - zmiana czasu modyfikacji jednego pliku daje 1;
     - skasowany plik znika z indeksu;
     - mp4 bez dźwięku jest pominięty (indeks zawiera tylko klik);
     - wszystkie liczby w indeksie to typy wbudowane;
  9. dwa wywołania `wybierz_utwor` na tych samych danych dają identyczny wynik.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.2 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/analyze.py tylko w miejscach analizuj_dzwiek, czas_z_pozycji i zapisz_json oraz tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_muzyka.py
```
- **Commit:** `muzyka: biblioteka i rozpoznanie dźwięku wzoru`

### [Task 4.3: Render i bot]
- **Objective:** render bez `--utwor` wybiera utwór z biblioteki, a bot przestaje wymagać `staly.mp3`.
- **Context/Inputs:**
  - kontrakty `plan_ujec`, `renderuj` i bota wyżej;
  - `src/render.py`: `plan_ujec` (176), `renderuj` (300), `glowna` (390);
  - `src/bot.py`: `renderuj_w_tle` (153), `obsluz_cmd_gotowe` (211, sprawdzenie utworu 241 do 244), `obsluz_cmd_status` (283);
  - `src/komunikaty.py`: `BRAK_UTWORU` (37), `podsumowanie_renderu` (95), `status_kolejki` (108).
- **Constraints:** `--utwor` działa jak dotąd: istniejące testy renderu i `Pomiary/measure_render.py` bez zmian. Testy:
  1. `plan_ujec` z `przesuniecie_s=5.0` na wzorze z `ciecia_s` [0, 0.9, 2.1] i `zrodlo.czas_s` 3.0, przy 30 fps:
     - granice klatek 0, 27 i 63, `liczba_klatek` 90, `start_audio_s` 5.0;
     - ujęcia mają `numer_wzoru` 0, 1 i 2;
     - przy dwóch cięciach w tej samej klatce `numer_wzoru` przeskakuje;
  2. pełny render bez `--utwor` (270x480):
     - biblioteka: melodia A (20 s) i B;
     - wzór: wideo z 4 cięciami i dźwiękiem fragmentu A od 7,3 s długości 6 s;
     - materiały w jednolitych, różnych kolorach (jak test 2 z części 3);
     - oczekiwane: podsumowanie ma `tryb: "dzwiek_wzoru"` i `start_s` w granicy 0,015 s od 7,3, a `analyze.wykryj_ciecia` na wyniku znajduje każde cięcie wzoru (`ciecia_s`) z dokładnością do 1 klatki;
  3. tryby i błędy renderu:
     - render bez `--utwor` na bibliotece bez pasującego dźwięku daje `tryb: "tempo"`;
     - bez `--utwor` i bez `--muzyka`: kod 1 i jedna linia na stderr;
  4. bot z podmienionym `uruchom`:
     - przekazuje `--muzyka`, a nie `--utwor`;
     - pusta `dane/muzyka/` daje `BRAK_MUZYKI` i nie dodaje zadania;
     - podpis zawiera nazwę utworu bez rozszerzenia i „dźwięk wzoru od”;
     - `/status` pokazuje liczbę utworów.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.3 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/render.py, src/music.py, src/bot.py, src/komunikaty.py, tests/test_render.py, tests/test_bot.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commity:** `render: utwór z biblioteki i dźwięk wzoru`, potem `bot: muzyka z biblioteki`

### [Task 4.4: Pomiar i arkusz porównawczy]
- **Objective:** `Pomiary/arkusz.py` i `Pomiary/measure_muzyka.py`, wynik w `outputs/pomiar_muzyka.json`.
- **Context/Inputs:**
  - **Sekcja A** (syntetyczna):
    - 10 melodii 60 s (ziarna od 1 do 10) w bibliotece tymczasowej, z każdej 3 fragmenty (10, 20 i 30 s) z losowym przesunięciem (stałe ziarno pomiaru);
    - raport: liczba błędnie rozpoznanych utworów, maksymalny i medianowy błąd przesunięcia w ms, najniższa zgodność pary pasującej i najwyższa niepasującej;
    - kliki od 60 do 180 BPM co 10: błąd tempa w procentach po uwzględnieniu oktawy.
  - **Sekcja B** (prawdziwe pliki, gdy są `dane/muzyka/` i `dane/probki/wzory/`):
    - czas indeksowania biblioteki;
    - tabela utworów: czas, tempo, liczba uderzeń;
    - macierz zgodności wzór na utwór;
    - dla każdego wzoru wybór: tryb, plik, przesunięcie, tempo, mnożnik;
    - porównanie z referencją z przeglądu: `0915` to Hot N Cold od 40,36 s, `0922` to Ex's And Oh's od 23,29 s, `0921` w trybie `tempo`. Nazwy plików mogą mieć dopisek „ (1)”, więc porównuj po początku nazwy;
    - analizę wzoru trzymaj w cache `outputs/wzor_<nazwa>.json`: wersja 2 liczona raz i używana ponownie, a starszy cache przeliczony (wzór 4K to około minuty analizy).
  - **Sekcja C:** dwa przebiegi doboru dla każdego wzoru dają to samo.
  - **Sekcja D:**
    - dla każdego wzoru render bez `--utwor` (1080x1920) na materiałach z `dane/probki/materialy/`; gdy ich brak, na 8 barwnych zdjęciach z `zdjecie_testowe`;
    - arkusz `outputs/porownanie_muzyka_<wzor>.png` przez `arkusz_porownawczy`.
- **Constraints:** progi:
  - A: 0 błędnie rozpoznanych, błąd przesunięcia najwyżej 15 ms, błąd tempa najwyżej 2%;
  - B: referencje zgodne (plik i przesunięcie ±0,05 s);
  - C: identyczność;
  - D: arkusze powstały.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.4 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/music.py, src/render.py, src/analyze.py, tests/generuj.py oraz Pomiary/measure_render.py jako wzór układu skryptu pomiaru. Weryfikacja: python Pomiary/measure_muzyka.py
```
- **Commit:** `Pomiary: pomiar muzyki i arkusz porównawczy`

### [Task 4.5: Pamięć analizy utworu (po teście ręcznym części 8, 2026-09-24)]
- **Po co:**
  - Na serwerze montaż kończył się kodem -9. Log jądra: `Memory cgroup out of memory: Killed process (python) anon-rss:2962848kB`, czyli zabity został `render.py`, a nie ffmpeg.
  - `render.py` sam indeksuje bibliotekę (`przygotuj_zrodlo_dzwieku`, potem `music.indeksuj`, potem `analyze.analizuj_dzwiek`). Po wgraniu nowych utworów analizuje je w pierwszym montażu.
  - Pomiar lokalny szczytu pamięci `analizuj_dzwiek` (2026-09-24, Opus): utwory 2,5 min około 2,8 do 3,0 GB, a `L_amour toujours` (4 min 11 s) około 4,0 GB. Szczyt rośnie z długością utworu, więc podniesiony limit 5 GB nie wystarczy dla dłuższego utworu.
  - **Źródło:** szacowanie tempa wewnątrz `librosa.beat.beat_track`. Liczy tempogram (okno 384) na całej obwiedni z krokiem 128 naraz. Po kolei w jednym procesie dla 4-minutowego utworu: wczytanie 201 MB, obwiednia 666 MB, `beat_track` 3031 MB, reszta już bez wzrostu.
  - Nakładka i znak wodny z części 8 nie mają z tym związku.
- **Kontrakt:**
  - `analyze.tempogram_sredni(obwiednia, sr) -> numpy.ndarray` o kształcie `(OKNO_TEMPOGRAMU, 1)`:
    - średnia po czasie z `librosa.feature.tempogram(onset_envelope=..., sr=sr, hop_length=KROK_ROZKLADU, win_length=OKNO_TEMPOGRAMU)`;
    - liczona kawałkami po `KAWALEK_TEMPOGRAMU = 4096` klatek obwiedni, z zakładką `OKNO_TEMPOGRAMU // 2` z każdej strony, którą się odcina przed sumowaniem;
    - `OKNO_TEMPOGRAMU = 384`.
  - `analizuj_dzwiek`:
    - tempo z `librosa.feature.tempo(tg=tempogram_sredni(...), sr=sr, hop_length=KROK_ROZKLADU, start_bpm=START_BPM)`;
    - potem `librosa.beat.beat_track(onset_envelope=..., bpm=<to tempo>, trim=False, units="time", ...)` bez własnego szacowania tempa;
    - reszta funkcji bez zmian.
  - **Sprawdzone prototypem (librosa 1.0.0) na 5 utworach z `dane/muzyka/` i 5 wzorach z `dane/wzory/`:**
    - tempo identyczne, uderzenia identyczne (0 różnic);
    - szczyt kroku rytmu przy 4-minutowym utworze 2871 MB, po zmianie 507 MB, a analiza jest szybsza (14,8 s wobec 8,7 s);
    - przy wzorach 32 s: 397 MB wobec 112 MB.
- **Context/Inputs:** `src/analyze.py` (`analizuj_dzwiek`, stałe na górze), `tests/test_analiza.py`, `tests/generuj.py` (`melodia`, `klik`). Gałąź `pamiec` od `main` (po części 8).
- **Constraints:** testy w `tests/test_analiza.py`:
  1. `tempogram_sredni` na sztucznej obwiedni 10 000 klatek (kilka kawałków) równa się `librosa.feature.tempogram(...).mean(axis=1)` (`numpy.allclose`, `rtol=1e-6`);
  2. wszystkie dotychczasowe testy rytmu i analizy przechodzą bez zmian;
  3. szczyt pamięci przez `tracemalloc` przy `analizuj_dzwiek` na melodii 120 s jest poniżej 600 MB. Najpierw sprawdź, że ten test nie przechodzi na starym kodzie (zapisz obie liczby w `ROZWOJ.md`). Jeśli `tracemalloc` nie widzi alokacji numpy, zastąp go pomiarem szczytu procesu w podprocesie i opisz to w dzienniku.
- **Pomiar:** `Pomiary/measure_pamiec.py`, wynik w `outputs/pomiar_pamiec.json`.
  - **Sekcja A:** każdy plik z `dane/muzyka/` i `dane/wzory/*.mp4`:
    - tempo i uderzenia starą drogą (`beat_track` bez `bpm`, wywołany w pomiarze) wobec nowej;
    - szczyt pamięci analizy, każdy plik w osobnym podprocesie. Na Windows `PeakWorkingSetSize` z `GetProcessMemoryInfo` przez ctypes, na Linuksie `resource.getrusage(...).ru_maxrss`.
  - **Sekcja B:** szczyt pamięci procesu `render.py` przy pełnym montażu 1080x1920:
    - pusty indeks biblioteki w katalogu tymczasowym z kopią `dane/muzyka/`, więc render indeksuje wszystkie utwory;
    - z nakładką, planszą i znakiem wodnym.
  - **Progi:**
    - A: tempo i uderzenia identyczne dla 100% plików, a szczyt analizy najdłuższego utworu najwyżej 1 GB;
    - B: szczyt najwyżej 2 GB.
- **Po wdrożeniu (Ty):**
  - indeksu nie trzeba przeliczać, bo wynik analizy jest identyczny;
  - limit `mem_limit: "5g"` może zostać, a wrócić do `3g` po sprawdzeniu `docker stats` przy montażu z nowym utworem w bibliotece.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. git pull na main, potem gałąź pamiec. Wykonaj zadanie 4.5 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/analyze.py, tests/test_analiza.py, tests/generuj.py, Pomiary/measure_muzyka.py jako wzór układu pomiaru. Weryfikacja: python -m pytest -q, potem python Pomiary/measure_pamiec.py. Commity: analiza: tempo liczone kawałkami, Pomiary: pomiar pamięci analizy.
```
- **Commity:** `analiza: tempo liczone kawałkami`, `Pomiary: pomiar pamięci analizy`.

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A, B i C w progach, arkusze D powstały.
- Wdrożenie (Ty): `wdroz.ps1`, potem na serwerze `docker compose exec bot python src/analyze.py --wszystkie` i `docker compose exec bot python src/music.py indeksuj`.
- Test ręczny (Ty):
  - `/nowy`, kilka materiałów i `/gotowe` przy najnowszym wzorze `0915` (albo `0922`, jeśli wyślesz go przez `/wzor`);
  - podpis mówi „dźwięk wzoru od 40,4 s” (albo 23,3 s), a drop wzoru słychać w tym samym miejscu editu co we wzorze;
  - wzór bez utworu w bibliotece (`0921`) dostaje dobór po tempie;
  - każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `analiza: odcisk dźwięku i energia uderzeń`
2. `muzyka: biblioteka i rozpoznanie dźwięku wzoru`
3. `render: utwór z biblioteki i dźwięk wzoru`
4. `bot: muzyka z biblioteki`
5. `Pomiary: pomiar muzyki i arkusz porównawczy`
6. `analiza: tempo liczone kawałkami` (4.5, gałąź `pamiec`)
7. `Pomiary: pomiar pamięci analizy` (4.5)

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 4 według Pomiary/PLAN_EDITY_4_MUZYKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..muzyka`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_muzyka.py`: sekcje A, B i C wobec progów. Na macierzy zgodności sprawdź, czy próg 0,5 ma zapas po obu stronach.
3. Arkusze `outputs/porownanie_muzyka_*.png`: w `0915` i `0922` cięcia wyniku wypadają w tych samych kolumnach co cięcia wzoru (tryb dźwięku wzoru odtwarza czasy cięć), a długość wyniku równa się długości wzoru.
4. `src/music.py`: normalizacja okna w korelacji chromy, doprecyzowanie na obwiedni, kolejność trybów, warunek mieszczenia okna, korelacja profilu energii w trybie tempa, remisy.
5. `src/analyze.py`: jedno dekodowanie w `analizuj_dzwiek`, `warnings` tylko w bloku, `--wszystkie` nie psuje wywołania z bota.
6. `src/render.py`: `przesuniecie_s` i `numer_wzoru` w `plan_ujec`, ścieżka `--utwor` bez zmian.
7. `src/bot.py`: `--muzyka` i brak wymogu `staly.mp3`.
