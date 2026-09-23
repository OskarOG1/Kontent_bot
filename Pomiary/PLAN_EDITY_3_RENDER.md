# Część 3: render z jednym stałym utworem

**Status (2026-09-23):** część 7 wdrożona i zamknięta, `main` zawiera `wdroz.ps1` pakujący `main` oraz lokalny serwer Bot API; zadanie 5.0 odpada (analiza wzoru 4K na serwerze 51 s). Materiały gotowe: `dane/muzyka/staly.mp3` (164,1 BPM, to samo tempo co wzór `0915`) lokalnie i na serwerze, próbki wzorów w `dane/probki/wzory/`. Można zaczynać.

**Zależy od:** części 1 i 2 razem z poprawką `analiza: start_bpm 150 dla rytmu` (commit bazowy `0e84cba`, w `main` od PR #1, `4b929c9`) oraz części 7 z zadaniem 7.3 (lokalny serwer Bot API, scalone do `main`).
**Gałąź:** `render` od `main` (po scaleniu zadania 7.3).
**Efekt:** po `/gotowe` bot kolejkuje montaż i odsyła plik mp4 9:16, w którym cięcia wzoru padają na uderzenia stałego utworu.
**Nowe pliki:** `src/render.py`, `tests/test_render.py`, `Pomiary/measure_render.py`.
**Zmieniane:** `tests/generuj.py` (zdjęcia, klipy z obrotem, szum), `src/magazyn.py` i `tests/test_magazyn.py` (`gif` w klipach), `src/bot.py` (`/gotowe` uruchamia montaż, limit wysyłki, trzy drobne braki), `src/komunikaty.py`, `requirements.txt` (pillow, pillow-heif), `tests/test_bot.py`.
**Od właściciela:** utwór w `dane/muzyka/staly.mp3` (dowolny plik z biblioteki skopiowany pod tą nazwą, na komputerze i na serwerze); opcjonalnie próbki zdjęć i klipów w `dane/probki/materialy/` oraz wzory w `dane/probki/wzory/` (dziś leżą w `dane/wzory/Edity/`, gdzie `/status` liczy je jako wzór). Pliki ponad 20 MB (oba prawdziwe wzory 4K mają około 150 MB) nie przejdą przez Telegram bez lokalnego serwera Bot API z części 7.
**Uwaga:** najdłuższa część. Gdy sesja się rozrośnie, zadania 3.5 i 3.6 zacznij w nowej sesji z ich promptów.
**Wymaganie właściciela (dopisane 2026-09-21, po napisaniu planu):** klipy i animacje (gify) mają być cięte na krótkie wstawki, żeby dało się ich użyć w editach, zamiast jednego długiego ujęcia z jednego klipu. Realizuje to `render.wstawki` (kontrakt niżej), wywoływane przed `plan_ujec`, oraz drobna zmiana w typach klipów (`gif`). Długość wstawki i kolejność rundami potwierdził właściciel 2026-09-22.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_3_RENDER.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commit `0e84cba` (`analiza: start_bpm 150 dla rytmu`), czyli właściciel scalił `analiza-wzoru` po odbiorze części 2, a `python -m pytest -q` przechodzi w całości (62 testy po części 2, co najmniej 71 po części 7 i zadaniu 7.3). `git diff --stat 0e84cba -- src/ tests/` pokazuje, czy kotwice niżej są aktualne: niepusty wynik (np. po części 7) nie blokuje, ale wtedy szukaj po nazwach funkcji. Utwórz gałąź `render` od `main`. Jeżeli `main` nie ma `0e84cba`, zatrzymaj się i zapytaj.

## Kontrakt z części 1 i 2 (stan z `0e84cba`)
- `src/magazyn.py`: `lista_materialow` (linia 85) zwraca `{"plik": Path, "typ": "zdjecie" | "klip", "message_id": int}` w kolejności wysłania; `typ_pliku` (69) korzysta ze zbiorów `ROZSZERZENIA_ZDJECIE` i `ROZSZERZENIA_KLIP` (7 i 8); `najnowszy_wzor` (53) pomija katalogi bez `wzor.json`; `wczytaj_projekt` i `zapisz_projekt` (104 i 110, zapis atomowy).
- `wzor.json`: `zrodlo.czas_s`, `ciecia_s` (początki ujęć, pierwszy 0.0), `uderzenia_s`, `ciecia_uderzenia` (pozycje cięć w uderzeniach co 0,25, pierwsza bywa ujemna), `koniec_uderzenia`; trzy ostatnie bywają puste (wzór bez dźwięku). Prawdziwe wzory właściciela to 4K, 60 fps, około 32 s i około 150 MB.
- `src/analyze.py`: `czas_z_pozycji` (193, ekstrapolacja medianą odstępu); `analizuj_rytm` (123) dekoduje przez `zdekoduj_do_wav` (112) i liczy uderzenia ze stałą `START_BPM = 150.0` (19, decyzja właściciela pod szybkie wzory, działa też na utwór); `metadane` (74) zamienia szerokość z wysokością przy obrocie o 90 stopni; `wykryj_ciecia` (98); `uruchom_narzedzie` (26) uruchamia program z zamkniętym stdin; `zapisz_json` (247) zapisuje atomowo; wyjątek `BladAnalizy` (22). librosa i scenedetect są importowane wewnątrz funkcji, więc import `analyze` w renderze jest tani: niech tak zostanie.
- `src/bot.py`: `obsluz_cmd_gotowe` (119) czeka na pobrania (132 do 135), ustawia `stan` `w_kolejce` i odpowiada `komunikaty.projekt_w_kolejce`; tu dostaje montaż. Wzorzec zadania w tle to `obsluz_wzor_plik` (239) z `analizuj_wzor_w_tle` (216): `asyncio.Event` o nazwie `zapowiedz` gwarantuje, że odpowiedź z pozycją w kolejce przyjdzie przed wynikiem. Ścieżka skryptu liczona jak `SKRYPT_ANALIZY` (28). `efektywny_limit_mb` (36) obcina pobieranie do `LIMIT_SERWERA_TELEGRAM_MB = 20` (26); odpowiednika dla wysyłki nie ma, a `.env` właściciela ma `LIMIT_WYSYLKI_MB=200`, czego zwykłe Bot API nie przyjmie (50 MB).
- `src/kolejka.py`: `uruchom(argumenty, limit_s, katalog) -> Wynik` z polami `kod`, `stdout`, `stderr`, `czas_s`, `przekroczono_czas`; `Kolejka.dodaj(zadanie) -> pozycja`.
- `tests/generuj.py`: `klik(sciezka_wav, bpm, czas_s, pierwsze_uderzenie_s=0.0, sr=22050) -> list[float]` (zwraca czasy kliknięć), `wideo_z_cieciami(...)`, `kolor_ujecia(numer)`. `tests/pomocnicze.py`: `SesjaTestowa`, `zbuduj_bota`, `zbuduj_wiadomosc`, `zbuduj_update`, `zdjecie`, `dokument`, `klip`, `animacja`, `nazwy_wywolan`.

## Kontrakty ustalane w tej części

**`render.plan_ujec(wzor: dict, uderzenia_utworu: list[float], materialy: list[dict], fps: int, start_uderzenie: int | None = None) -> dict`**, czysta funkcja bez ffmpeg:
```json
{"fps": 30, "start_audio_s": 0.62, "liczba_klatek": 480,
 "ujecia": [{"material": "dane/projekty/.../0000000123_x.jpg", "typ": "zdjecie", "klatka_od": 0, "liczba_klatek": 15, "start_w_klipie_s": 0.0}]}
```
Zachowanie:
- Gdy wzór ma `ciecia_uderzenia`, a utwór co najmniej 2 uderzenia: s to `start_uderzenie` albo najmniejsza liczba całkowita, dla której `czas_z_pozycji(s + c_0)` jest nieujemny. Czas cięcia `t_k = czas_z_pozycji(s + c_k)`, koniec `czas_z_pozycji(s + koniec_uderzenia)`, `start_audio_s = t_0`.
- W przeciwnym razie cięcia to `ciecia_s`, koniec to `zrodlo.czas_s`, `start_audio_s = 0`.
- Granice w klatkach liczone od czasów bezwzględnych: `klatka_od_k = round((t_k − t_0) * fps)`; łączna liczba klatek tak samo z końca. Długości ujęć to różnice granic, nigdy osobno zaokrąglane długości (to się sumuje w dryf i po kilkudziesięciu cięciach obraz rozjeżdża się z rytmem).
- Ujęcia, którym po zaokrągleniu zostało 0 klatek, wypadają.
- Utwór za krótki na całe okno: `ValueError` z czytelną treścią.
- `materialy` to lista kawałków z `render.wstawki` (niżej). Ujęcie k dostaje kawałek `k mod N`. Dla kawałka klipu `start_w_klipie_s` to jego `od_s`: segment gra plik źródłowy od tego miejsca przez całą długość ujęcia, także poza `czas_s` kawałka, a zamraża ostatnią klatkę dopiero wtedy, gdy kończy się sam plik.

**`render.wstawki(materialy: list[dict], dlugosc_wstawki_s: float, minimum_s: float = 0.3) -> list[dict]`**, czysta funkcja bez ffmpeg, wywoływana przed `plan_ujec` na liście z `lista_materialow` uzupełnionej o `czas_s` klipów:
- Zdjęcia przechodzą bez zmian. Każdy klip (mp4, mov, m4v, webm, mkv, animacje z Telegrama, gify) jest dzielony od początku na kolejne wstawki po `dlugosc_wstawki_s`. Wstawka to wpis `{"plik", "typ": "klip", "message_id", "czas_s": <długość wstawki>, "od_s": <początek w pliku>}`.
- Ogon krótszy niż `minimum_s` jest doklejany do poprzedniej wstawki (ta staje się dłuższa), nie tworzy osobnej. Klip krótszy niż `dlugosc_wstawki_s` daje jedną wstawkę o swojej długości.
- Kolejność wyniku to rundy po materiałach w kolejności wysłania: w każdej rundzie każdy materiał, który ma jeszcze niewykorzystany kawałek, oddaje następny. Zdjęcie ma jeden kawałek, więc występuje tylko w pierwszej rundzie. Dzięki temu jeden klip nie wypełnia ujęć pod rząd, a wstawki jednego klipu zachowują kolejność czasową.
- Osobnej zasady przesuwania startu przy ponownym użyciu nie ma: różne fragmenty klipu to po prostu różne wstawki. Kawałek krótszy od ujęcia gra dalej z pliku źródłowego (patrz `plan_ujec`).
- `dlugosc_wstawki_s` wylicza `renderuj` jako medianę długości ujęć wzoru w sekundach, ograniczoną do 0,5 do 2,0 s (potwierdzone przez właściciela 2026-09-22).

**`render.renderuj(wzor_json: Path, katalog_projektu: Path, utwor: Path, wyjscie: Path, szerokosc=1080, wysokosc=1920, fps=30, limit_mb=50) -> dict`** oraz CLI `python src/render.py --wzor ... --projekt ... --utwor ... --wyjscie ... [--szerokosc --wysokosc --fps --limit-mb]`: kod 0, gdy powstały `wyjscie` i podsumowanie `<wyjscie bez rozszerzenia>.json`; inaczej kod różny od 0 i jedna linia na stderr. Podsumowanie:
```json
{"czas_s": 16.0, "liczba_ujec": 32, "materialy_uzyte": 12,
 "materialy_pominiete": [{"plik": "0000000130_y.mp4", "powod": "brak strumienia wideo"}],
 "rozmiar_mb": 21.4, "czas_renderu_s": 41.2, "utwor": {"plik": "staly.mp3", "start_s": 0.62}}
```
**Plik wynikowy:** H.264 High, yuv420p, stałe fps, SAR 1:1, AAC 48 kHz stereo 192 kb/s, `+faststart`, rozmiar najwyżej 0,95 limitu.
**Przebieg końcowy** to jedna funkcja w `render.py` i jedyne miejsce z ustawieniami kodowania pliku wynikowego. Części 5 i 6 dopiszą do niej filtry (najpierw LUT, potem napisy), bez drugiego kodowania. Sygnaturę ustal sam i podaj ją w raporcie.
**Izolacja wzoru:** render czyta z katalogu wzoru wyłącznie `wzor.json`; `zrodlo.*` nigdy nie jest wejściem ffmpeg.
**Pliki pośrednie:** `<projekt>/praca/`, usuwane po sukcesie, zostawiane po błędzie.

## Zadania

### [Task 3.1: Generator zdjęć i klipów]
- **Objective:** dopisz do `tests/generuj.py` funkcje `zdjecie_testowe`, `klip_testowy`, `szum`.
- **Context/Inputs:** `zdjecie_testowe(sciezka, rozmiar=(1200, 1600), orientacja_exif=1, alfa=False, kolor=None)`: w orientacji wyświetlania górna połowa czerwona, dolna niebieska (albo jednolity `kolor`); przy orientacji EXIF 6 lub 8 surowe piksele są obrócone tak, że `ImageOps.exif_transpose` przywraca czerwień na górze; `alfa=True` daje PNG z przezroczystym fragmentem. `klip_testowy(sciezka, czas_s, rozmiar=(480, 270), obrot=0, fps=30, kolor=None)`: w orientacji wyświetlania czerwień na górze; `obrot=90` zapisuje obraz obrócony z metadaną obrotu (ffmpeg od wersji 6 ma opcję wejścia `-display_rotation`, sprawdź). `szum(sciezka, czas_s, rozmiar, fps=30)`: losowy szum, czyli najgorszy przypadek dla rozmiaru pliku.
- **Constraints:** samosprawdzenie w `tests/test_render.py`: `exif_transpose` daje czerwień na górze; klatka klipu z obrotem zdekodowana przez ffmpeg ma czerwień na górze, a ffprobe pokazuje obrót.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.1 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_render.py
```

### [Task 3.2: Plan ujęć]
- **Objective:** `render.plan_ujec` i `render.wstawki` według kontraktów, z testami.
- **Context/Inputs:** kontrakty `plan_ujec` i `wstawki`; `analyze.czas_z_pozycji` z części 2.
- **Constraints:** testy, każdy łapie inną cichą pomyłkę:
  1. dryf: 64 cięcia co 0,5 uderzenia na utworze 123 BPM; każde `klatka_od` równe wartości policzonej w teście z czasów bezwzględnych, suma długości równa `liczba_klatek`;
  2. przypadek policzony ręcznie: `ciecia_uderzenia` `[-0.25, 0.75, 1.75, 2.25]`, koniec 3,75, uderzenia utworu co 0,6 s od 0,3 s; oczekiwane klatki wpisane w test;
  3. pierwsze uderzenie w 0,1 s i `c_0 = -0.25`: wybrane s daje nieujemne `start_audio_s`;
  4. wzór bez uderzeń: cięcia z `ciecia_s`, długość z `zrodlo.czas_s`;
  5. 3 materiały na 7 ujęć: kolejność 0, 1, 2, 0, 1, 2, 0;
  6. jeden klip 2,0 s przez `wstawki` z długością 0,6 s, potem `plan_ujec` na 5 ujęć po 0,6 s: starty 0; 0,6; 1,2; 0; 0,6 (ogon 0,2 s doklejony do trzeciej wstawki);
  7. dwa cięcia w tej samej klatce: ujęcie o 0 klatek wypada;
  8. za krótki utwór: `ValueError`;
  9. wstawki: klip 5,0 s przy `dlugosc_wstawki_s` 1,0 daje 5 wstawek z `od_s` 0, 1, 2, 3, 4 i `czas_s` 1,0; klip 2,2 s daje 2 wstawki (ogon 0,2 s krótszy niż `minimum_s` jest doklejony: 1,0 i 1,2); klip 0,6 s daje jedną wstawkę 0,6 s; zdjęcie przechodzi bez zmian;
  10. rundy: wysłane kolejno klip A (3 wstawki), zdjęcie Z i klip B (2 wstawki) dają A1, Z, B1, A2, B2, A3;
  11. kawałek z `od_s` 3,0 dostaje `start_w_klipie_s` 3,0 niezależnie od długości ujęcia.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.2 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/analyze.py tylko w miejscu czas_z_pozycji. Weryfikacja: python -m pytest -q tests/test_render.py
```

### [Task 3.3: Segmenty zdjęć i klipów]
- **Objective:** w `src/render.py` przygotowanie materiałów i segment wideo na każde ujęcie.
- **Context/Inputs:**
  - Zdjęcie przed użyciem: obrót według EXIF, HEIC przez pillow-heif, przezroczystość spłaszczona na czarnym tle, zmniejszenie do rozmiaru wystarczającego na kadr z zapasem na zoom; zapis do `praca/`.
  - Segment zdjęcia: wypełnienie kadru 9:16 z przycięciem środka i powolny zoom (przy parzystych ujęciach przybliżanie, przy nieparzystych oddalanie). Filtr `zoompan` przy małej rozdzielczości roboczej drga; typowe obejście to praca na większej rozdzielczości przed skalowaniem w dół.
  - Segment klipu: fragment od `start_w_klipie_s`, wypełnienie kadru z przycięciem, zamiana na docelowe fps, bez dźwięku; za krótki klip dostaje zamrożoną ostatnią klatkę.
  - Każdy segment ma dokładnie `liczba_klatek` klatek, docelowy rozmiar, SAR 1:1, te same parametry kodowania (jakość pośrednia wysoka, szybki preset), żeby dało się je skleić bez ponownego kodowania.
  - Materiał uszkodzony albo bez strumienia wideo trafia do `materialy_pominiete`; brak jakiegokolwiek dobrego materiału to błąd.
  - Gify: Telegram zwykle przysyła animacje jako mp4 (już obsługiwane), ale plik `.gif` wysłany jako dokument jest dziś ignorowany, bo `magazyn.ROZSZERZENIA_KLIP` nie zawiera `gif`. Dopisz `gif` do klipów w `src/magazyn.py` (i test `typ_pliku("a.gif", None) == "klip"`); ffmpeg czyta gif jako wideo.
  - Segment klipu z wstawki: początek w pliku to `od_s` plus `start_w_klipie_s` z planu (patrz kontrakt `render.wstawki`).
  - Wymiary liczy ffmpeg na klatkach po autorotacji; nie licz kadrowania z szerokości i wysokości z ffprobe, bo dla klipów z obrotem są zamienione.
- **Constraints:** testy w 270x480: klip z obrotem 90 daje segment z czerwienią u góry (średni kolor górnych 20% wierszy); zdjęcie z EXIF 6 tak samo; PNG z przezroczystością się renderuje; klip 0,4 s w ujęciu 1,0 s daje dokładnie 30 klatek (`ffprobe -count_frames`); zdjęcie poziome 1600x900 daje 270x480 i SAR 1:1; losowe bajty z rozszerzeniem mp4 lądują w `materialy_pominiete`, a render idzie dalej; klip z `wideo_z_cieciami` o długości 5,0 s z kolorem zmienianym co 1 s: kawałek od 3,0 w ujęciu 1,5 s zaczyna się kolorem sekundy 3 i kończy kolorem sekundy 4 (gra dalej, bez zamrożenia), a kawałek od 4,5 w ujęciu 1,0 s ma 30 klatek i kończy się kolorem sekundy 4 (zamrożenie dopiero na końcu pliku).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.3 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/render.py i tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_render.py
```

### [Task 3.4: Montaż, dźwięk, przebieg końcowy, CLI]
- **Objective:** `render.renderuj`, przebieg końcowy i CLI według kontraktu.
- **Context/Inputs:** `renderuj` najpierw uzupełnia `czas_s` klipów z ffprobe, liczy `dlugosc_wstawki_s`, wywołuje `render.wstawki`, dopiero potem `plan_ujec` na jego wyniku; w podsumowaniu `materialy_uzyte` liczy pliki źródłowe, nie wstawki. Segmenty sklejone bez ponownego kodowania; dźwięk z utworu od `start_audio_s`, długość `liczba_klatek / fps`, wyciszenie około 0,5 s na końcu. Przebieg końcowy koduje raz z limitem przepływności: CRF około 20 plus `maxrate` wyliczone z długości i limitu (miejsce na dźwięk i zapas na kontener), `bufsize` dwa razy większy. Po kodowaniu sprawdzenie ffprobe: wymiary, fps, długość z dokładnością do 1 klatki, obecność dźwięku; plik ponad limit to błąd, nigdy cicha wysyłka.
- **Constraints:** każde wejście obrazu ograniczone liczbą klatek (wejście zapętlone bez limitu koduje w nieskończoność). Pliki, które trafią do argumentów filtrów (LUT w części 5), podawaj względem katalogu roboczego ffmpeg, bo dwukropek w ścieżce Windows łamie składnię filtra. Testy w 270x480:
  1. pełny przebieg: wzór syntetyczny 120 BPM z 8 cięciami, 3 zdjęcia i 1 klip, klik 128 BPM jako utwór; długość równa `liczba_klatek / fps` z dokładnością do 1 klatki, yuv420p, SAR 1:1, jest dźwięk, jest podsumowanie JSON, katalogu `praca/` nie ma;
  2. cięcia na swoim miejscu: materiały w jednolitych, różnych kolorach; `analyze.wykryj_ciecia` na wyniku znajduje każdą granicę planu z dokładnością do 1 klatki;
  3. limit rozmiaru: klip z szumem 10 s i `--limit-mb 2` daje plik najwyżej 2 MB;
  4. usunięty `zrodlo.*` wzoru nie przeszkadza.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.4 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/render.py i tests/generuj.py. Weryfikacja: python -m pytest -q
```

### [Task 3.5: Montaż w bocie]
- **Objective:** `/gotowe` kolejkuje render i odsyła wynik jako dokument.
- **Context/Inputs:** `obsluz_cmd_gotowe` (bot.py:119) po odczekaniu na pobrania: brak wzoru daje komunikat „najpierw /wzor”, brak `dane/muzyka/staly.mp3` osobny komunikat, w obu przypadkach nic nie trafia do kolejki. Dalej: `wzor_id` do `projekt.json`, stan `w_kolejce`, odpowiedź z pozycją w kolejce, wysłana przed wynikiem tak jak przy analizie (`zapowiedz` w `obsluz_wzor_plik`, bot.py:239). Zadanie: stan `renderowanie`, wiadomość „Montuję”, `uruchom` z CLI renderu (`limit_s=900`). `--limit-mb` daje istniejąca od zadania 7.2 funkcja `efektywny_limit_wysylki_mb(konf)` w `bot.py` (50 MB bez `TELEGRAM_API_URL`, do 2000 MB z lokalnym serwerem Bot API); nie twórz jej drugi raz. Sukces: `sendDocument` z `wynik.mp4` i podpisem (długość, liczba ujęć, materiały użyte i pominięte, czas renderu), stan `gotowy`, `wynik` w `projekt.json`; `TelegramEntityTooLarge` przy wysyłce daje komunikat z rozmiarem pliku i limitem. Błąd renderu: stan `blad`, pole `blad` z pierwszą linią stderr, odpowiedź z tą linią.
  Przy okazji trzy drobne braki z testu ręcznego części 1 (`ROZWOJ.md`, „Znane problemy”): dokument nieznanego typu w trakcie zbierania dostaje komunikat zamiast ciszy (`obsluz_material`, bot.py:295 do 297); nieudane pobranie wzoru usuwa pusty katalog wzoru (`obsluz_wzor_plik`, bot.py:255 do 265); `/status` liczy tylko wzory z `wzor.json` (bot.py:184 i 185).
- **Constraints:** testy w `tests/test_bot.py` z podmienionym `uruchom`: sukces daje dokładnie jedno `sendDocument`; błąd daje komunikat i stan `blad`; brak wzoru nie dodaje zadania do kolejki; przy `limit_wysylki_mb=200` render dostaje `--limit-mb 50`, a z ustawionym `telegram_api_url` dostaje `--limit-mb 200`; PDF w trakcie zbierania daje komunikat i 0 plików; nieudane pobranie wzoru nie zostawia katalogu; `/status` nie liczy katalogu bez `wzor.json`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.5 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/bot.py, src/komunikaty.py, tests/test_bot.py, tests/pomocnicze.py. Weryfikacja: python -m pytest -q
```

### [Task 3.6: Pomiar]
- **Objective:** `Pomiary/measure_render.py`, wynik w `outputs/pomiar_render.json` i arkusze PNG.
- **Context/Inputs:** sekcja A, 1080x1920: wzór syntetyczny 20 s, 120 BPM, 40 cięć; 10 zdjęć (w tym 2 z obrotem EXIF, 1 PNG z przezroczystością, 1 HEIC), 3 klipy (w tym 1 z obrotem i 1 krótszy od ujęcia); utwór: klik 124 BPM, 60 s, jako mp3. Raport: czas renderu, sekundy renderu na sekundę wyniku, rozmiar, zgodność formatu, odsetek granic planu znalezionych w wyniku z dokładnością do 1 klatki, mediana odległości cięć od najbliższego uderzenia lub połowy uderzenia w dźwięku wyniku (uderzenia z `analizuj_rytm` na pliku wynikowym). Sekcja B: sam przebieg końcowy na 60 s szumu 1080x1920 z limitem 50 MB. Sekcja C (prawdziwe pliki), gdy jest `staly.mp3`: wzory z katalogu podanego jako argument (domyślnie `dane/probki/wzory/`), każdy analizowany raz przez `analyze.analizuj_wzor` z zapisem do `outputs/wzor_<nazwa>.json` i ponownym użyciem przy kolejnych przebiegach (wzór 4K to około minuty analizy); materiały z `dane/probki/materialy/`, a gdy ich nie ma, z najnowszego projektu w `dane/projekty/` z co najmniej 3 materiałami. Render dla każdego wzoru, czas i rozmiar, arkusz wyniku (jedna klatka ze środka każdego ujęcia, najwyżej około 1600x1600 px) `outputs/render_<wzor>.png`.
- **Constraints:** progi: A 100% granic i mediana do 20 ms, zgodność formatu pełna; B najwyżej 47,5 MB; C tylko raport.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.6 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/render.py, src/analyze.py, tests/generuj.py. Weryfikacja: python Pomiary/measure_render.py
```

### [Task 3.7: Dźwięk przycinany na wejściu, długość wyniku wymuszona]
- **Powód:** na prawdziwych danych (utwór 152 s, edit 32 s) `przebieg_koncowy` dawał plik 27,2 do 27,7 s zamiast 32 s, w każdym przebiegu inny, więc `zweryfikuj_wynik` odrzucał wynik i bot odpowiadał „Montaż nie powiódł się: Długość wyniku nie zgadza się z planem”. Test ręczny właściciela 2026-09-23 na serwerze.
- **Stan obecny i co jest złe:** `przebieg_koncowy` (`src/render.py`) podaje utwór jako drugie wejście w całości, przycina go filtrem `atrim=start=...:duration=...` z `asetpts=PTS-STARTPTS`, a długość wyjścia bierze z `-shortest`. Przy utworze wielokrotnie dłuższym od editu ffmpeg czyta dalej wejście, którego wyjście filtra już się skończyło, wypisuje „Queue input is backward in time” oraz „Non-monotonic DTS” na strumieniu dźwięku i kończy plik za wcześnie.
- **Ustalone doświadczalnie na serwerze, na tych samych plikach** (sklejony materiał `praca/polaczone.mp4` był poprawny: 960 klatek, 32,0 s):
  - sam obraz przez ten sam przebieg: 960 klatek, 32,0 s;
  - sam dźwięk z `atrim` zapisany osobno: 32,0 s;
  - obraz i dźwięk razem, `atrim` plus `-shortest`: 817, 826 i 830 klatek w kolejnych przebiegach, czyli wynik niedeterministyczny;
  - `-t` zamiast `-shortest`: obraz wraca do 960 klatek, ale dźwięk nadal ma popsute znaczniki (1481 ramek, zgłaszany czas 27,3 s);
  - okładka w mp3 (`staly.mp3` ma strumień PNG, oba utwory właściciela też) nie jest przyczyną: po jej usunięciu błąd wygląda tak samo;
  - **działa:** przycięcie utworu opcjami wejścia `-ss <start_audio_s> -t <czas_trwania_s>` przed `-i`, bez `atrim` i `asetpts`, z zachowanym `afade`: obraz 960 klatek i 32,0 s, dźwięk 32,0 s.
- **Stan docelowy:** `przebieg_koncowy` przycina utwór opcjami wejścia, filtr dźwięku zostaje tylko na wyciszenie, a długość wyjścia jest wymuszona jawnie (`-frames:v` z `liczba_klatek` albo `-t`), nie przez `-shortest`. Reszta bez zmian: to dalej jedyne miejsce kodowania wyniku, `maxrate` liczony jak dziś, segmenty i sklejanie nietknięte.
- **Przypadek cichy i test, który go łapie:** dzisiejsze testy renderu używają utworu o długości zbliżonej do editu (klik 6 s), więc odrzucany ogon jest krótki i błąd się nie pokazuje. Nowy test: pełny render z utworem wielokrotnie dłuższym od editu (np. klik 60 s przy edicie około 2 s), sprawdzający liczbę klatek wyniku co do jednej i osobno długość strumienia dźwięku z ffprobe (`stream=duration`, nie tylko `format=duration`, bo to właśnie rozjazd między nimi wyszedł na serwerze).
- **Pomiar:** `Pomiary/measure_render.py` sekcja A bez zmian, ale w raporcie dopisz długość strumienia dźwięku obok długości obrazu. Progi jak dotąd.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 3.7 z Pomiary/PLAN_EDITY_3_RENDER.md; otwórz src/render.py, tests/test_render.py, tests/generuj.py, Pomiary/measure_render.py. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisz do niego wpis po zadaniu. Weryfikacja: python -m pytest -q oraz python Pomiary/measure_render.py.
```
Commit: `render: dźwięk przycinany na wejściu i wymuszona długość wyniku`.

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar A: 100% granic, mediana do 20 ms; B najwyżej 47,5 MB.
- Test ręczny (Ty): `/wzor`, `/nowy`, 8 zdjęć i 2 klipy, `/gotowe`. Bez lokalnego serwera Bot API (część 7) każdy plik musi mieć poniżej 20 MB: wzór wyślij jako zwykłe wideo z kompresją, a jeśli dalej jest za duży, skróć go (analizie strukturę wystarczy). Plik gra na telefonie, cięcia słychać na uderzeniach, zdjęcia nie są obrócone, zoom nie drga, wstawki z klipów się przeplatają. Stały utwór analizuje ta sama funkcja z `START_BPM = 150`: jeśli cięcia wyraźnie mijają się z rytmem, zanotuj to, bo przyczyną może być tempo utworu, a nie render. Każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `testy: zdjęcia i klipy z obrotem`
2. `render: plan ujęć w rytmie utworu`
3. `render: segmenty zdjęć i klipów`
4. `render: montaż, dźwięk i limit rozmiaru`
5. `bot: montaż po /gotowe`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 3 według Pomiary/PLAN_EDITY_3_RENDER.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..render`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_render.py`, sekcje A i B wobec progów.
3. Arkusze `outputs/render_*.png`: zdjęcia w pionie, sensowne kadrowanie, brak czarnych pasów.
4. `src/render.py`: `plan_ujec` liczy granice z czasów bezwzględnych; przebieg końcowy jest jedynym miejscem kodowania wyniku, a `maxrate` wynika z długości i limitu; ffmpeg zawsze z zamkniętym stdin; każde wejście obrazu ograniczone; żadna ścieżka z katalogu wzoru poza `wzor.json` nie trafia do ffmpeg; `render.wstawki` układa kawałki rundami po materiałach. `src/bot.py`: `--limit-mb` pochodzi z `efektywny_limit_wysylki_mb`, nie wprost z konfiguracji.
5. Uwagi z testu ręcznego właściciela, jeśli są.
