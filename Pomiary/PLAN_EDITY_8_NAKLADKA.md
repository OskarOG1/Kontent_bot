# Część 8: drop, nakładka i plansza końcowa

**Zależy od:** części 4 (commit `Pomiary: pomiar muzyki i arkusz porównawczy`). Z części 4 potrzebne są:
- `wzor.json` w wersji 2 z `energia_uderzen`;
- `plan_ujec` z polem `numer_wzoru`;
- `analyze.py --wszystkie`;
- `Pomiary/arkusz.py`.

**Gałąź:** `nakladka` od `main` po scaleniu części 4.
**Efekt:** analiza zapisuje we wzorze moment dropu, czyli koniec haka. Render nakłada Twoją nakładkę graficzną od dropu do planszy, a ostatnie ujęcie zastępuje Twoją planszą końcową. Nakładkę i planszę wysyłasz botowi, każdą przypisaną do wzoru.
**Dlaczego (przegląd 2026-09-23):** wszystkie trzy wzory mają od dropu pełnoekranową nakładkę (gwiazdy), a na końcu planszę z produktem, około 1 s. Nakładki ani planszy ze wzoru kopiować nie wolno (reguła 7), więc to Twoje własne pliki. Drop wyznacza też sekcje, na których stoją części 5 (kolor) i 6 (napisy).
**Nowe pliki:** `tests/test_nakladka.py`, `Pomiary/measure_nakladka.py`.
**Zmieniane:** `src/analyze.py`, `tests/test_analiza.py`, `src/render.py`, `tests/test_render.py`, `tests/generuj.py`, `src/magazyn.py`, `tests/test_magazyn.py`, `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`.
**Od właściciela:**
- pliki nakładek i plansz: np. nakładka gwiazd na zielonym albo czarnym tle, albo z przezroczystością, oraz plansza jako obraz 9:16;
- ocena dropu na arkuszach;
- po wdrożeniu na serwerze `docker compose exec bot python src/analyze.py --wszystkie`.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_8_NAKLADKA.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commit `Pomiary: pomiar muzyki i arkusz porównawczy` (część 4 po odbiorze i scaleniu), a `python -m pytest -q` przechodzi. Utwórz gałąź `nakladka` od `main`. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 3 i 4
Numery linii z `57ba8fe` (przed częścią 4), więc szukaj po nazwach.
- `wzor.json` w wersji 2: `ciecia_s`, `ciecia_uderzenia`, `uderzenia_s`, `energia_uderzen` (RMS między kolejnymi uderzeniami), `zrodlo.czas_s`; pola rytmu bywają `null`.
- `analyze.analizuj_wzor` (215) składa `wzor.json`, a `analyze.py --wszystkie` przelicza wszystkie wzory.
- `render.plan_ujec` zwraca `ujecia` z polami `material`, `typ`, `klatka_od`, `liczba_klatek`, `start_w_klipie_s`, `numer_wzoru`, oraz `fps` i `liczba_klatek` całości.
- `render.przebieg_koncowy(polaczone_wideo, utwor, start_audio_s, liczba_klatek, fps, wyjscie, limit_mb)` (244):
  - `-filter_complex` z `[0:v]setsar=1[v]` i `[1:a]afade...[a]`, utwór przycięty opcjami wejścia;
  - to jedyne kodowanie wyniku.
- Segmenty w `render.py`:
  - `PARAMETRY_KODOWANIA_SEGMENTU` (21);
  - `przygotuj_zdjecie` (41): EXIF, HEIC, przezroczystość na czarne;
  - `segment_zdjecia` (72) i `segment_klipu` (92): `tpad` zamraża ostatnią klatkę;
  - pętla segmentów w `renderuj` (354 do 361).
- `src/magazyn.py`: `najnowszy_wzor` (53), `ROZSZERZENIA_ZDJECIE` i `ROZSZERZENIA_KLIP` (7 i 8), `typ_pliku` (69).
- `src/bot.py`:
  - `Stany` (41);
  - `obsluz_cmd_wzor` (139);
  - `renderuj_w_tle` (153), które przekazuje argumenty CLI renderu;
  - `obsluz_cmd_status` (283);
  - `podsumuj_wzor` (320);
  - `obsluz_wzor_plik` (355): wzorzec pobrania dokumentu przez `pobierz_plik` (114) z limitem `efektywny_limit_mb` (46);
  - rejestracja handlerów w `zbuduj_router` (472).
- `src/komunikaty.py`: `POMOC` (1), `KOMENDY` (10), `podsumowanie_wzoru` (71), `BRAK_WZORU` (35).

## Kontrakty ustalane w tej części

**`wzor.json` → `sekcje`** (`WERSJA_WZORU = 3`):
```json
{"drop_s": 7.25, "drop_ujecie": 9, "koniec_haka_uderzenia": 19.75}
```
`analyze.wykryj_drop(uderzenia_s, energia_uderzen, ciecia_s, ciecia_uderzenia, czas_s) -> dict | None`:
- **Przedział szukania:** uderzenia `i` od 8 do ostatniego z czasem nie większym niż `czas_s / 2`. Hak jest na początku, a drugi drop pod koniec wzoru nie może wygrać. Poprawka po odbiorze (2026-09-24, zadanie 8.5): wcześniej od 4, ale pierwszy odcinek energii zaczyna się po pierwszym kliku, więc stała głośność dawała przy `i = 4` wynik 0,114 średniej.
- **Wynik uderzenia:** `srednia(E[i:i+8]) − srednia(E[i−8:i])`. Okna są przycinane do dostępnych danych, ale każde musi mieć co najmniej 4 wartości.
- **Wybór:** wygrywa najwyższy wynik, a przy remisie najwcześniejsze uderzenie.
- **Brak dropu:** zwraca `None`, gdy nie ma rytmu, jest mniej niż 16 uderzeń albo najwyższy wynik jest mniejszy niż `PROG_DROPU = 0.1` średniej energii. Poprawka po odbiorze (zadanie 8.5): przy 0,2 wzór `0921` (wynik 0,129 średniej) nie miał dropu i nakładka szła od pierwszej klatki. Stała głośność przy szukaniu od 8 daje najwyżej 0,065.
- **Przyciągnięcie do cięcia:** czas uderzenia przyciąga się do najbliższego cięcia z `ciecia_s` o indeksie co najmniej 1, o ile leży w granicy 1 s. Inaczej brane jest pierwsze cięcie po tym czasie.
- **Pola wyniku:** `drop_s` to czas wybranego cięcia, `drop_ujecie` jego indeks, a `koniec_haka_uderzenia` jego pozycja z `ciecia_uderzenia` (albo `null`).
- `analizuj_wzor` wypełnia `sekcje` (bez dropu: `null`), a `--wszystkie` dokłada pole do istniejących wzorów.
- **Referencja z arkuszy (4 klatki na sekundę, przybliżona, ±0,5 s):** `0915` około 7,2 s, `0921` około 5,5 s, `0922` około 11,0 s, a od 2026-09-24 także `0914` około 8,5 s i `0923` około 11,2 s. Reguła z zadania 8.5 daje na nich 7,30, 5,40, 10,97, 8,50 i 11,23 s. W `0915` i `0922` od tego momentu zmienia się kolor i wchodzi nakładka, w `0921` wchodzi nakładka.

**Nakładka:**
- `render.tryb_nakladki(sciezka) -> str`:
  - `"alfa"`, gdy plik ma kanał przezroczystości:
    - `pix_fmt` z ffprobe ma składową alfa (np. `rgba`, `yuva420p`, `argb`, `ya8`);
    - albo strumień VP9 ma znacznik `alpha_mode` równy 1 (wtedy dekodowanie przez `-c:v libvpx-vp9` przed `-i`, bo domyślny dekoder gubi alfę);
    - PNG i GIF sprawdza PIL (tryb z alfą albo `transparency`);
  - `"zielen"`, gdy w pierwszej klatce co najmniej 30% pikseli jest bliskich czystej zieleni (G > 150, R < 100, B < 100);
  - w pozostałych przypadkach `"ekran"`, czyli czarne tło i mieszanie typu screen.
- **Okno czasowe:** od `klatka_od` pierwszego ujęcia planu z `numer_wzoru >= drop_ujecie` do `klatka_od` ujęcia planszy albo, bez planszy, do końca editu. Początek okna to `render.koniec_haka(plan, sekcje)` (zadanie 8.5), więc bez `sekcje` nakładka zaczyna się na 40% editu, a nie na pierwszej klatce. Gdy okno ma mniej niż 1 klatkę, render idzie bez nakładki, a podsumowanie ma `nakladka: null`.
- **Kompozycja w `przebieg_koncowy`** (dalej jedyne kodowanie wyniku):
  - nakładka jest kolejnym wejściem, zapętlonym (`-stream_loop -1`, dla obrazu `-loop 1`) i ograniczonym `-t` długością okna;
  - w filtrze: skalowanie typu cover do rozmiaru wyniku, `fps` wyniku i przesunięcie na początek okna;
  - `alfa`: `overlay` włączony tylko w oknie;
  - `zielen`: `colorkey=0x00FF00:0.3:0.1`, potem `overlay`;
  - `ekran`: `blend=all_mode=screen`. Jeżeli `blend` nie przyjmuje `enable`, dopełnij nakładkę czarnymi klatkami poza oknem, bo screen z czernią nic nie zmienia.
    - Poprawka po odbiorze (zadanie 8.5): oba wejścia `blend` w `format=gbrp`, a po `blend` `scale=out_range=tv,format=yuv420p`. Wynik całego editu zostaje w ograniczonym zakresie, jak w pozostałych trybach. Wersja z `scale=out_range=full` dawała `yuvj420p` z `color_range=pc` na cały edit.
- **Kolejność warstw obrazu od tej części:** materiał (segmenty, od części 5 z kolorem), potem nakładka, potem napisy (część 6), a na wierzchu znak wodny (zadanie 8.6).

**Plansza:**
- `render.segment_planszy(sciezka, wyjscie, liczba_klatek, fps, szerokosc, wysokosc)`:
  - obraz albo klip (od 0 s, bez dźwięku) w całości w kadrze (contain), na tle z tego samego obrazu powiększonego do cover i rozmytego (`boxblur`), bez zoomu;
  - dokładnie `liczba_klatek` klatek, SAR 1:1, `PARAMETRY_KODOWANIA_SEGMENTU`;
  - klip krótszy od ujęcia zamraża ostatnią klatkę;
  - obraz przechodzi najpierw przez `przygotuj_zdjecie`.
- Plansza zastępuje segment ostatniego ujęcia planu: materiał przypisany do tego ujęcia nie jest renderowany. W planie z jednym ujęciem plansza nie jest używana, co widać w podsumowaniu.
- Plansza nie dostaje koloru (część 5) ani nakładki.

**Pliki właściciela:**
- `dane/nakladki/<wzor_id>.<ext>` i `dane/plansze/<wzor_id>.<ext>`, z zapasowym `domyslna.<ext>` w tych samych katalogach.
- `magazyn.plik_zasobu(katalog_danych, rodzaj, wzor_id) -> Path | None`, gdzie `rodzaj` to `"nakladki"` albo `"plansze"`:
  - najpierw plik wzoru, potem `domyslna.*`, inaczej `None`;
  - przy kilku plikach o tej samej nazwie wygrywa najnowszy (czas modyfikacji).
- Rozszerzenia nakładek: `webm`, `mov`, `mp4`, `png`, `gif`. Plansze: rozszerzenia zdjęć i klipów z `magazyn`.

**Render:**
- `renderuj(..., nakladka: Path | None = None, plansza: Path | None = None)` i CLI `--nakladka`, `--plansza`.
- Podsumowanie dostaje:
  - `"nakladka": {"plik": "...", "tryb": "alfa", "od_s": 7.25, "do_s": 31.0} | null`;
  - `"plansza": "<nazwa>" | null`;
  - `"drop_s": 7.25 | null`, czyli czas dropu w wyniku: `klatka_od / fps` ujęcia dropu.
- Bez nakładki i planszy polecenie ffmpeg przebiegu końcowego jest identyczne jak dotąd, bez żadnego dodatkowego wejścia.

**Bot:**
- **`/nakladka`:**
  - przechodzi do nowego stanu `Stany.czekam_na_nakladke` i odpowiada: „Wyślij nakładkę jako plik: webm albo mov z przezroczystością, png, albo mp4 na zielonym lub czarnym tle. Będzie użyta dla wzoru <id>.”;
  - dokument z obsługiwanym rozszerzeniem zapisuje się jako `dane/nakladki/<wzor_id>.<ext>` przez `pobierz_plik`; wcześniejsze pliki tego wzoru w `dane/nakladki/` są usuwane;
  - odpowiedź podaje wykryty tryb: „Nakładka zapisana: przezroczystość.”, „zielone tło.” albo „czarne tło.”;
  - zdjęcie albo wideo wysłane nie jako plik traci przezroczystość, więc bot prosi o wysłanie jako plik;
  - bez wzoru odpowiada `BRAK_WZORU`.
- **`/nakladka usun`:** usuwa pliki wzoru i potwierdza.
- **`/plansza` i `/plansza usun`:** działają tak samo, stan `Stany.czekam_na_plansze`; plansza może przyjść też jako zdjęcie.
- **Który wzór:** `magazyn.najnowszy_wzor` (część 9 zamieni go na aktywny wzór), a `wzor_id` to nazwa jego katalogu.
- **Montaż:** `renderuj_w_tle` przekazuje `--nakladka` i `--plansza`, gdy `magazyn.plik_zasobu` coś znajdzie.
- **Komunikaty:**
  - podsumowanie wzoru po analizie dostaje „drop w 7,3 s (ujęcie 9)” albo „bez dropu”;
  - `/status` dostaje wiersz „Wzór <id>: nakładka tak, plansza nie.”;
  - `POMOC` i `KOMENDY` opisują nowe komendy.

## Zadania

### [Task 8.1: Drop w analizie]
- **Objective:** `analyze.wykryj_drop`, pole `sekcje`, `WERSJA_WZORU = 3`.
- **Context/Inputs:** kontrakt `sekcje`; `src/analyze.py` (`analizuj_wzor`, `analizuj_dzwiek`, `WERSJA_WZORU`); `tests/generuj.py` (`klik` i `melodia` z parametrem `glosnosc`, `wideo_z_cieciami` z `dzwiek`).
- **Constraints:** testy w `tests/test_analiza.py`:
  1. wideo 30 s z cięciami co 1 s i dźwiękiem: klik 150 BPM z `glosnosc=[(0, 0.15), (9, 1.0)]` daje `drop_s` 9.0 i `drop_ujecie` 9. Poprawka w zadaniu 8.5: przy 120 BPM wygrywa uderzenie 8,503 s, bo uderzenia wypadają kilka ms po kliku i odcinek przed 9 s łapie początek głośnego kliku. Wtedy 9,0 wychodzi z zapasem 3 ms;
  2. ten sam układ ze skokiem głośności w 22 s (druga połowa) i bez innego skoku: `sekcje: null`;
  3. stała głośność: `sekcje: null`;
  4. wideo bez dźwięku: `sekcje: null`;
  5. klik 150 BPM ze skokiem w 8,9 s (`glosnosc=[(0, 0.15), (8.9, 1.0)]`, pierwsze głośne uderzenie około 9,2 s) przy cięciach co 1 s: `drop_s` 9.0 i `drop_ujecie` 9, czyli najbliższe cięcie, a nie pierwsze po uderzeniu. Poprawka 2026-09-23: wcześniejszy wariant (120 BPM, skok w 9,4 s) dawał uderzenie 9,501 s, prawie dokładnie w połowie między cięciami 9 i 10, więc wynik zależał od milisekund i wychodził 10,0;
  6. `wersja: 3`, a `--wszystkie` dokłada `sekcje` do istniejącego wzoru.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 8.1 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/analyze.py, tests/generuj.py, tests/test_analiza.py. Weryfikacja: python -m pytest -q tests/test_analiza.py
```
- **Commit:** `analiza: drop wzoru`

### [Task 8.2: Nakładka i plansza w renderze]
- **Objective:** `render.tryb_nakladki`, `render.segment_planszy`, nakładka w `przebieg_koncowy`, parametry `renderuj` i CLI.
- **Context/Inputs:**
  - kontrakty nakładki, planszy i renderu;
  - `src/render.py` (`przebieg_koncowy`, `renderuj`, `glowna`, `przygotuj_zdjecie`, `segment_klipu`);
  - do `tests/generuj.py` dopisz `nakladka_testowa(sciezka, czas_s, tryb, rozmiar=(270, 480), fps=30)`:
    - `alfa`: mov z kodekiem `png` i `rgba`, górna połowa nieprzezroczysta czerwona, dolna przezroczysta;
    - `zielen`: mp4, górna połowa czerwona, dolna czysta zieleń;
    - `ekran`: mp4, górna połowa biała, dolna czarna;
    - `png`: statyczny PNG z alfą w układzie jak `alfa`.
- **Constraints:** testy w `tests/test_nakladka.py`, 270x480:
  1. `tryb_nakladki` dla czterech plików z generatora daje `alfa`, `zielen`, `ekran` i `alfa`;
  2. nakładka `alfa`:
     - render ze wzorem, którego `sekcje.drop_ujecie` to 2 z 4 ujęć, materiały jednolicie niebieskie;
     - w klatkach ze środka ujęć 0 i 1 górne 20% jest niebieskie;
     - w klatkach ujęć 2 i 3 górne 20% jest czerwone;
     - dół jest zawsze niebieski;
     - długość wyniku bez zmian (do 1 klatki);
  3. nakładka `zielen`: dół jest niebieski, nie zielony;
  4. nakładka `ekran`: góra biała, dół niebieski bez zmian (±6 poziomów);
  5. plansza (zdjęcie zielone 1600x900) z nakładką `alfa`: ostatnie ujęcie ma zieleń na środku kadru i nie ma czerwieni u góry (okno nakładki kończy się przed planszą), a liczba klatek wyniku się nie zmienia;
  6. nakładka 0,5 s przy oknie 2 s zapętla się, a render kończy się w limicie czasu testu;
  7. bez nakładki i planszy polecenie przebiegu końcowego ma dokładnie dwa wejścia (sprawdzone przez podmienione `uruchom_ffmpeg`);
  8. wzór bez `sekcje`: nakładka od pierwszej klatki. Zmienione w zadaniu 8.5: od `koniec_haka`, czyli 40% editu.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 8.2 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/render.py, tests/generuj.py, tests/test_render.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: nakładka i plansza końcowa`

### [Task 8.3: Bot]
- **Objective:** `magazyn.plik_zasobu`, komendy `/nakladka` i `/plansza`, przekazanie plików do renderu, drop w podsumowaniu wzoru i w `/status`.
- **Context/Inputs:** kontrakty „Pliki właściciela” i „Bot”; `src/magazyn.py`, `src/bot.py`, `src/komunikaty.py`, `tests/test_bot.py`, `tests/pomocnicze.py`, `tests/test_magazyn.py`. Tryb nakładki wykrywany jest na zapisanym pliku, więc w testach pobieranie zapisuje prawdziwy plik z generatora.
- **Constraints:** testy:
  1. `magazyn.plik_zasobu`: plik wzoru ma pierwszeństwo przed `domyslna`, przy dwóch rozszerzeniach wygrywa nowszy, a bez plików zwraca `None`;
  2. `/nakladka` i dokument png zapisują `dane/nakladki/<id>.png`, a odpowiedź podaje tryb; drugi plik zastępuje pierwszy;
  3. `/nakladka usun` usuwa plik;
  4. zdjęcie w stanie `czekam_na_nakladke` daje prośbę o plik;
  5. bez wzoru odpowiedź to `BRAK_WZORU`;
  6. `/plansza` przyjmuje zdjęcie;
  7. render (podmienione `uruchom`) dostaje `--nakladka` i `--plansza`, gdy pliki są, a bez nich żadnego z tych argumentów;
  8. podsumowanie wzoru z `sekcje` zawiera „drop w”, a `/status` pokazuje nakładkę i planszę.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 8.3 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/magazyn.py, src/bot.py, src/komunikaty.py, src/render.py tylko w miejscu tryb_nakladki, tests/test_bot.py, tests/pomocnicze.py, tests/test_magazyn.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `bot: nakładka i plansza wzoru`

### [Task 8.4: Pomiar]
- **Objective:** `Pomiary/measure_nakladka.py`, wynik w `outputs/pomiar_nakladka.json` i arkusze.
- **Context/Inputs:**
  - **Sekcja A:** drop na prawdziwych wzorach z `dane/wzory/*.mp4` wobec referencji z kontraktu. Wzory bez referencji tylko w raporcie, do oceny na arkuszu. Cache analizy w `outputs/wzor_<nazwa>.json`, starszą wersję przelicz.
  - **Sekcja B:** narzut czasu przebiegu końcowego (1080x1920, 20 s) z nakładką w każdym trybie wobec przebiegu bez nakładki, w procentach.
  - **Sekcja C:** dla każdego wzoru render z nakładką i planszą oraz arkusz `outputs/porownanie_nakladka_<wzor>.png`:
    - nakładka z `dane/nakladki/domyslna.*`, a gdy jej brak, syntetyczne żółte gwiazdy pięcioramienne na przezroczystym tle (mov z kodekiem `png`, generowane w pomiarze);
    - plansza z `dane/plansze/domyslna.*` albo syntetyczna jednobarwna z napisem „KONIEC” rysowanym przez PIL.
- **Constraints:** progi:
  - A: drop w granicy 0,5 s od referencji dla wszystkich 5 wzorów (po zadaniu 8.5; wcześniej 2 z 3);
  - B: narzut najwyżej 40% w każdym trybie. Po zadaniu 8.5 każdy tryb i baza po 3 przebiegi na przemian, liczona mediana, bo pojedyncze przebiegi na laptopie różniły się nawet 2 do 3 razy;
  - C: arkusze powstały.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 8.4 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/render.py, src/analyze.py, tests/generuj.py, Pomiary/arkusz.py, Pomiary/measure_muzyka.py jako wzór układu. Weryfikacja: python Pomiary/measure_nakladka.py
```
- **Commit:** `Pomiary: pomiar nakładki`

### [Task 8.5: Poprawki po odbiorze (2026-09-24)]
- **Objective:** cztery poprawki z odbioru PR #9 na tej samej gałęzi `nakladka`, każda z własnym testem, potem pomiar 8.4 na prawdziwych wzorach.
- **Dlaczego (liczby z odbioru):**
  - `wykryj_drop` na zapisanych analizach trzech wzorów: `0915` 7,30 s i `0922` 10,97 s trafiają w referencję, ale `0921` daje `None`. Jego najlepszy wynik to 0,129 średniej energii, przy progu 0,2. Bez `sekcje` nakładka szła od pierwszej klatki, więc przykrywała cały hak.
  - Przy szukaniu od 8. uderzenia i progu 0,1 wychodzi 7,30 s, 5,40 s i 10,97 s, czyli 3 z 3 w granicy 0,5 s. Stała głośność daje wtedy najwyżej 0,065, a skok w drugiej połowie 0,009.
  - Tryb `ekran` kodował cały edit jako `yuvj420p` z `color_range=pc`, bo po `blend` stało `scale=out_range=full`.
  - `/nakladka` albo `/plansza` w trakcie zbierania materiałów kończą się `state.clear()`. To kasuje `projekt_id`, więc potem `/gotowe` odpowiada `BRAK_STANU`.
  - Stary plik nakładki albo planszy był usuwany przed pobraniem nowego, więc nieudane pobranie zostawiało wzór bez niego.
- **Context/Inputs:** kontrakty „sekcje”, „Nakładka” i „Bot” (z dopiskami „poprawka po odbiorze”); `src/analyze.py` (`wykryj_drop`), `src/render.py` (`przebieg_koncowy`, `okno_nakladki`, `renderuj`, `zweryfikuj_wynik`), `src/bot.py` (`obsluz_nakladka_dokument`, `obsluz_plansza_zalacznik`, `obsluz_wzor_plik`, `usun_pliki_zasobu`), `tests/test_analiza.py`, `tests/test_nakladka.py`, `tests/test_bot.py`, `tests/generuj.py`, `Pomiary/measure_nakladka.py`.
- **Zmiany:**
  1. **Analiza:**
     - stała `PROG_DROPU = 0.1`, szukanie od uderzenia 8;
     - test 1 z zadania 8.1 na 150 BPM zamiast 120.
  2. **`render.koniec_haka(plan, sekcje) -> int`:** kontrakt przeniesiony z części 6, gdzie był `tekst.koniec_haka`. Część 6 użyje tej funkcji.
     - z `sekcje`: `klatka_od` pierwszego ujęcia z `numer_wzoru >= drop_ujecie`, a gdy takiego nie ma, reguła jak bez sekcji;
     - bez `sekcje`: 40% `liczba_klatek`, przyciągnięte do najbliższego początku ujęcia;
     - wynik zawsze co najmniej `fps` i najwyżej `liczba_klatek`;
     - `okno_nakladki` bierze z niej początek okna;
     - gdy okno ma mniej niż 1 klatkę, nakładka nie jest dodawana i podsumowanie ma `nakladka: null`.
  3. **Tryb `ekran`:**
     - oba wejścia `blend` w `format=gbrp`, a po `blend` `scale=out_range=tv,format=yuv420p`, bez `scale=out_range=full`;
     - `zweryfikuj_wynik` odrzuca wynik, którego `pix_fmt` nie jest `yuv420p`.
  4. **Bot:**
     - po zapisaniu nakładki, planszy albo wzoru: gdy dane stanu mają `projekt_id`, bot wraca do `Stany.zbieram` z tym samym `projekt_id`, a inaczej `state.clear()`. Dotyczy to też `obsluz_wzor_plik`, który ma ten sam błąd od części 1;
     - nowy plik pobiera się najpierw pod docelową nazwą, a dopiero potem usuwa się pozostałe pliki `<wzor_id>.*` tego rodzaju, poza właśnie pobranym.
  5. **Pomiar:**
     - `Pomiary/measure_nakladka.py` z progami z kontraktu 8.4 po tej zmianie: A 3 z 3, B jako mediana z 3 przebiegów na przemian;
     - ścieżki w `Pomiary/measure_nakladka.py` według nowego układu `dane/` z bloku WSPÓLNE: wzory `dane/wzory/*.mp4`, próbka materiałów z biblioteki, plansza z `dane/promocyjne/`;
     - uruchomienie na wzorach z `dane/wzory/*.mp4`. Gdy nie ma tam `0915.mp4`, `0921.mp4` i `0922.mp4`, zatrzymaj się i zapytaj właściciela, zamiast pomijać sekcje A i C.
- **Constraints:** testy:
  1. `tests/test_analiza.py`: klik 150 BPM z `glosnosc=[(0, 0.85), (9, 1.0)]` (wynik około 0,15 średniej, przy starym progu byłoby `None`) daje `drop_s` 9.0 i `drop_ujecie` 9. Testy 2 do 5 z zadania 8.1 przechodzą bez zmian.
  2. `koniec_haka`:
     - plan 10 ujęć po 30 klatek bez `sekcje` daje 120 (40% z 300, najbliższy początek ujęcia);
     - z `sekcje.drop_ujecie` 3 daje 90;
     - z `drop_ujecie` większym niż każdy `numer_wzoru` wraca do reguły 40%.
  3. `tests/test_nakladka.py`, test 8 z zadania 8.2: wzór bez `sekcje` i nakładka `alfa` dają czyste klatki przed `koniec_haka` i czerwień u góry od `koniec_haka`.
  4. Nakładka `ekran` (test 4 z 8.2):
     - `pix_fmt` wyniku to `yuv420p`, a `color_range` nie jest `pc`;
     - góra biała (każdy kanał co najmniej 250), dół niebieski bez zmian (±6).
  5. `tests/test_bot.py`:
     - `/nowy`, zdjęcie, `/nakladka`, dokument png, `/gotowe`: render trafia do kolejki z `--nakladka`, projekt ma 1 materiał;
     - to samo z `/plansza` i z `/wzor`;
     - pobieranie nakładki kończy się wyjątkiem: poprzedni plik `dane/nakladki/<id>.png` zostaje.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź nakladka. Wykonaj zadanie 8.5 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/analyze.py, src/render.py, src/bot.py, tests/test_analiza.py, tests/test_nakladka.py, tests/test_bot.py, tests/generuj.py, Pomiary/measure_nakladka.py. Po każdej z czterech zmian: python -m pytest -q i commit o nazwie z zadania. Na koniec python Pomiary/measure_nakladka.py (sekcje A i C na prawdziwych wzorach) i krótki raport.
```
- **Commity:** `analiza: próg i przedział dropu`, `render: koniec haka i zakres kolorów nakładki`, `bot: stan projektu po nakładce i planszy`, `Pomiary: pomiar nakładki po poprawkach`.

### [Task 8.6: Znak wodny marki (wymaganie właściciela 2026-09-24)]
- **Po co:** edity promują czapki 1993 Supply. Wzór `0914` (edit właściciela) ma znak wodny „1993 Supply” przez cały edit poza planszą. Plik znaku leży w `dane/promocyjne/1993supply_watermark.png` (610x170, biały napis z alfą 234).
- **Pomiar znaku we wzorze `0914`** (klatka 12 s):
  - nieprzezroczysty obszar ma 51% szerokości kadru, środek w poziomie na 50%, a środek w pionie na 80% wysokości;
  - jasność napisu na ciemnym tle to około 160, więc krycie wynikowe około 0,6;
  - 80% leży poniżej strefy bezpiecznej z części 6 (78%), ale tak robi wzór właściciela, więc zostaje;
  - na planszy końcowej znaku nie ma.
- **Kontrakt:**
  - plik `dane/znak_wodny.png`, jeden dla wszystkich wzorów;
  - bot: `/znak` przyjmuje PNG jako plik, a `/znak usun` go usuwa. Przy renderze `renderuj_w_tle` przekazuje `--znak`, gdy plik istnieje;
  - `renderuj(..., znak: Path | None = None)` i CLI `--znak`;
  - w `przebieg_koncowy` znak to kolejne wejście `-loop 1 -t <długość okna>`. Skalowanie liczy się z prostokąta nieprzezroczystych pikseli (PIL `getbbox` na kanale alfa), tak żeby miał 51% szerokości wyniku i leżał według pomiaru. Mnożnik krycia `KRYCIE_ZNAKU = 0.65` na kanale alfa (0,92 z pliku razy 0,65 daje około 0,6);
  - okno: od klatki 0 do początku planszy, a bez planszy do końca;
  - kolejność warstw: materiał, nakładka, napisy (część 6), znak wodny na wierzchu;
  - bez znaku polecenie przebiegu końcowego się nie zmienia;
  - podsumowanie ma `"znak": true | false`, a `/status` pokazuje „Znak wodny: tak” albo „nie”.
- **Context/Inputs:** `src/render.py` (`przebieg_koncowy`, `renderuj`, `glowna`), `src/bot.py`, `src/komunikaty.py`, `tests/test_nakladka.py`, `tests/test_bot.py`, `tests/generuj.py`, `Pomiary/measure_nakladka.py`.
- **Constraints:** testy:
  1. render 270x480 ze znakiem (biały prostokąt z alfą 255 w PNG 200x50) na czarnych materiałach:
     - w środku obszaru znaku jasność 140 do 175 (krycie 0,65);
     - poza obszarem czerń;
     - obszar leży w pasie 76% do 84% wysokości, a szerokość to 51% ±2 punkty;
  2. z planszą: w ostatnim ujęciu znaku nie ma;
  3. z nakładką `alfa`: w oknie nakładki znak jest widoczny na niej, czyli leży nad nią;
  4. bez znaku: polecenie przebiegu końcowego identyczne jak przed tym zadaniem (podmienione `uruchom_ffmpeg`);
  5. bot: `/znak` z dokumentem PNG zapisuje `dane/znak_wodny.png`, a render dostaje `--znak`; `/znak usun` usuwa plik; bez pliku renderu nie ma `--znak`.
  - Pomiar: w sekcji C arkusze powstają ze znakiem z `dane/znak_wodny.png`, a gdy go nie ma, z `dane/promocyjne/1993supply_watermark.png`. Wynik obok `0914` na arkuszu to werdykt właściciela.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź nakladka, po zadaniu 8.5. Wykonaj zadanie 8.6 z Pomiary/PLAN_EDITY_8_NAKLADKA.md; otwórz src/render.py, src/bot.py, src/komunikaty.py, tests/test_nakladka.py, tests/test_bot.py, tests/generuj.py, Pomiary/measure_nakladka.py. Weryfikacja: python -m pytest -q, potem python Pomiary/measure_nakladka.py.
```
- **Commit:** `render i bot: znak wodny marki`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Zadania 8.5 i 8.6 wykonane, pomiar powtórzony na wzorach z `dane/wzory/*.mp4`.
- Pomiar: A i B w progach, arkusze C powstały.
- Wdrożenie (Ty): `wdroz.ps1`, potem na serwerze `docker compose exec bot python src/analyze.py --wszystkie`.
- Test ręczny (Ty):
  - `/nakladka` z Twoim plikiem, `/plansza` z obrazem, potem `/nowy`, materiały i `/gotowe`;
  - hak jest czysty, nakładka wchodzi na dropie i trzyma się do planszy, a plansza jest na końcu i nie jest przycięta;
  - każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `analiza: drop wzoru`
2. `render: nakładka i plansza końcowa`
3. `bot: nakładka i plansza wzoru`
4. `Pomiary: pomiar nakładki`
5. `analiza: próg i przedział dropu` (8.5)
6. `render: koniec haka i zakres kolorów nakładki` (8.5)
7. `bot: stan projektu po nakładce i planszy` (8.5)
8. `Pomiary: pomiar nakładki po poprawkach` (8.5)
9. `render i bot: znak wodny marki` (8.6)

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 8 według Pomiary/PLAN_EDITY_8_NAKLADKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..nakladka`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_nakladka.py`: drop wobec referencji, narzut czasu.
3. Arkusze `outputs/porownanie_nakladka_*.png`:
   - nakładka w wyniku wchodzi w tej samej kolumnie co we wzorze;
   - hak jest czysty;
   - plansza zajmuje ostatnie ujęcie i nie ma na niej nakładki.
4. `src/analyze.py`: `wykryj_drop` szuka tylko w pierwszej połowie wzoru i przyciąga drop do cięcia.
5. `src/render.py`:
   - przebieg końcowy nadal jest jedynym kodowaniem wyniku;
   - wejście nakładki jest zapętlone i ograniczone;
   - bez nakładki polecenie się nie zmienia;
   - plansza nie dostaje nakładki.
6. `src/bot.py`: pliki trafiają do `dane/nakladki/` i `dane/plansze/`, nigdy do katalogu wzoru.
