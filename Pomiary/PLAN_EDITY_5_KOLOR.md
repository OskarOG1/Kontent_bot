# Część 5: kolorystyka wzoru na sekcję

**Zależy od:**
- części 8 (commit `Pomiary: pomiar nakładki`): `sekcje` we wzorze i plansza w renderze;
- części 4: `numer_wzoru` w planie, `analyze.py --wszystkie`, `Pomiary/arkusz.py`.

Część 6 nie jest wymagana.
**Gałąź:** `kolor` od `main` po scaleniu części 8.
**Efekt:** analiza zapisuje statystyki barw każdego ujęcia wzoru. Render przenosi na każdy segment kolorystykę sekcji wzoru, w której ten segment leży (hak albo montaż), przez tablicę LUT nakładaną w jedynym kodowaniu segmentu. Siłę domyślną wybiera oceniający na arkuszach.
**Dlaczego na sekcję (przegląd 2026-09-23):** w `0915` i `0922` hak jest ciepły i naturalny, a montaż po dropie niebieski. Jedna średnia całego wzoru dałaby kolor, którego nie ma w żadnym jego ujęciu. LUT na segment wyrównuje przy okazji materiały między sobą, bo każdy ma własne statystyki źródłowe.
**Zadanie 5.0 (lekka kopia wzoru) zdjęte:** analiza 4K na serwerze trwa 51 s przy progu 150 s (mapa, decyzja 18).
**Nowe pliki:** `src/kolor.py`, `tests/test_kolor.py`, `Pomiary/measure_kolor.py`.
**Zmieniane:** `src/analyze.py`, `tests/test_analiza.py`, `src/render.py`, `tests/test_render.py`, `src/konfiguracja.py`, `tests/test_konfiguracja.py`, `.env.example`, `src/bot.py`, `tests/test_bot.py`.
**Od właściciela:** po wdrożeniu `docker compose exec bot python src/analyze.py --wszystkie` na serwerze i ewentualnie `SILA_KOLORU` w `.env` serwera.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_5_KOLOR.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Na koniec uruchom pomiar i zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, przepisany 2026-09-23 po przeglądzie prawdziwych wzorów (`ROZWOJ.md`, wpisy „przegląd planów 4 do 6” i „przepisanie planów 4 do 9”). Kotwice `plik:linia` pochodzą z commita `57ba8fe` (stan po części 3 i zadaniu 3.7). Po wcześniejszych częściach mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edity wideo 9:16 na TikToka z dostarczonych materiałów. Wzorem jest gotowy edit: bot odtwarza jego strukturę i styl, a muzykę bierze z biblioteki właściciela w `dane/muzyka/`. Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
  - Prawdziwe wzory (`0915`, `0921`, `0922`) mają ten sam format: hak (pierwsze 4 do 11 s, naturalne kolory, napis), drop (od niego pełnoekranowa nakładka graficzna i mocny grading), montaż i plansza końcowa około 1 s (mapa, decyzja 15).
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
  - Arkusz powstaje dla każdego wzoru z `dane/probki/wzory/`, na materiałach z `dane/probki/materialy/`; gdy ich brak, na barwnych zdjęciach z generatora.
  - Oceniający wydaje werdykt na arkuszu, a progi liczbowe są dodatkiem.
  - Wzór ogląda się tylko w `outputs/`, nic z niego nie trafia do wyniku bota.
- Dziennik `Pomiary/ROZWOJ.md`: przeczytaj na starcie (stan, znane problemy, decyzje), dopisuj wpis po każdym zadaniu, decyzji i odkryciu, bez tokenu i wartości z `.env`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`main` zawiera commit `Pomiary: pomiar nakładki` (część 8 po odbiorze i scaleniu), a `python -m pytest -q` przechodzi. Utwórz gałąź `kolor` od `main`. Jeżeli jest już część 6 (commit `tekst: napisy w haku w renderze`), nic w przebiegu końcowym się nie zmienia, bo kolor idzie do segmentów. Jeśli `main` nie ma części 8, zatrzymaj się i zapytaj.

## Kontrakt z części 1 do 4 i 8
Numery linii z `57ba8fe`, więc szukaj po nazwach.
- `wzor.json` w wersji 3:
  - `ciecia_s` (początki ujęć, pierwszy 0.0), `zrodlo.czas_s`;
  - `sekcje: {drop_s, drop_ujecie, koniec_haka_uderzenia} | null`;
  - zarezerwowane `kolorystyka: null`.
- `analyze.analizuj_wzor` (215) woła `wykryj_ciecia` (98) na oryginale 4K; samo dekodowanie pełnej rozdzielczości trwa lokalnie około 36 s, a cała analiza na serwerze 51 s.
- `render.py`:
  - `uruchom_ffmpeg(argumenty)` (24) bez katalogu roboczego;
  - segmenty `segment_zdjecia` (72), `segment_klipu` (92) i `segment_planszy` (część 8), wszystkie kodowane `PARAMETRY_KODOWANIA_SEGMENTU` (21);
  - `przygotuj_zdjecie` (41) zapisuje PNG w `praca/`;
  - plan ma w każdym ujęciu `numer_wzoru`;
  - przebieg końcowy ma nakładkę (część 8) i jest jedynym kodowaniem wyniku.
- `konfiguracja.Konfiguracja` (konfiguracja.py:10) i `wczytaj` (19); `.env.example`.
- `bot.renderuj_w_tle` składa argumenty CLI renderu.

## Kontrakty ustalane w tej części

**`wzor.json` → `kolorystyka`** (`WERSJA_WZORU = 4`):
```json
{"probki_na_s": 10,
 "ujecia": [{"lab_srednia": [52.1, 6.3, 14.8], "lab_odchylenie": [21.4, 9.9, 12.2], "probki": 12}]}
```
- Jeden wpis na każde ujęcie wzoru, więc `len(ujecia) == len(ciecia_s)`.
- Lab zmiennoprzecinkowy liczony ze sRGB (D65): L od 0 do 100, a oraz b mniej więcej od −128 do 127. To nie jest 8-bitowa skala OpenCV, w której L przeskalowano do 255, a do a i b dodano 128.

**Próbkowanie wzoru bez spowalniania analizy:**
- `analyze.uruchom_probkowanie(sciezka, cel: Path) -> subprocess.Popen` uruchamia ffmpeg z `-vf fps=10,scale=135:240 -f rawvideo -pix_fmt rgb24 <cel>` (stdin i stdout zamknięte, stderr do pliku tymczasowego).
- `analizuj_wzor` startuje próbkowanie przed `wykryj_ciecia`, a czeka na nie po wykryciu cięć (limit 300 s). Dwa dekodowania idą równolegle, a nie po kolei.
- `analyze.statystyki_koloru(plik_probek, ciecia_s, czas_s, szerokosc=135, wysokosc=240, probki_na_s=10) -> dict`:
  - klatka `k` ma czas `k / 10` i należy do ujęcia `j`, gdy `ciecia_s[j] <= t < ciecia_s[j+1]`;
  - statystyki ujęcia to średnia i odchylenie każdego kanału Lab po wszystkich pikselach jego klatek;
  - ujęcie bez klatki (krótsze niż 0,1 s) dostaje statystyki najbliższej w czasie klatki i `probki: 0`.
- **Próg z pomiaru:** analiza prawdziwego wzoru 4K z próbkowaniem trwa najwyżej 1,3 raza dłużej niż bez niego. Przy przekroczeniu zgłoś w raporcie, nie zgaduj obejścia.

**`src/kolor.py`:**
- `rgb_do_lab(tablica) -> numpy.ndarray` i `lab_do_rgb(tablica)`:
  - wejście RGB uint8 albo float 0..1, sRGB z krzywą gamma, biel D65;
  - wyjście float;
  - dokładność sprawdzana na bieli i czystej czerwieni.
- `statystyki_obrazu(tablica_rgb) -> dict` zwraca `lab_srednia` i `lab_odchylenie`.
- `cel_sekcji(kolorystyka, sekcje, numer_wzoru) -> dict`: łączne statystyki ujęć sekcji, do której należy `numer_wzoru`.
  - Hak to ujęcia o numerze mniejszym niż `drop_ujecie`, montaż to ujęcia od `drop_ujecie`.
  - Ostatnie ujęcie wzoru nigdy nie wchodzi do statystyk, bo we wzorach to plansza.
  - Bez `sekcje` jest jedna sekcja: wszystkie ujęcia oprócz ostatniego.
  - Ujęcia z `probki: 0` są pomijane. Sekcja bez użytecznych ujęć bierze statystyki całości.
  - Łączenie: średnia ważona liczbą próbek; odchylenie to `sqrt(ważona średnia (odchylenie_j² + (srednia_j − srednia)²))`.
- `lut_transferu(zrodlo, cel, sila, rozmiar=33) -> numpy.ndarray` o kształcie `(rozmiar, rozmiar, rozmiar, 3)`, wartości od 0 do 1. Dla każdego koloru siatki:
  1. przejście do Lab;
  2. przesunięcie i przeskalowanie statystyk źródła na statystyki celu (transfer Reinharda); stosunek odchyleń ograniczony do przedziału 0,5 do 2, żeby prawie jednolity materiał nie eksplodował;
  3. zmieszanie z kolorem wejściowym w proporcji `sila`;
  4. powrót do sRGB i obcięcie do zakresu.
- `zapisz_cube(lut, sciezka)`: format `.cube` (`LUT_3D_SIZE`, potem wiersze „r g b”, w których składowa czerwona zmienia się najszybciej).

**Render:**
- Każdy segment oprócz planszy dostaje kolor. Źródłem są statystyki materiału takiego, jaki wchodzi do segmentu:
  - zdjęcie: przygotowany PNG po tym samym kadrowaniu 9:16, zmniejszony do 270x480 (PIL);
  - klip: 3 klatki z 25, 50 i 75% zakresu czasu segmentu, przez ffmpeg z tym samym skalowaniem i kadrowaniem, w 135x240.
- Cel to `kolor.cel_sekcji` dla `numer_wzoru` ujęcia.
- LUT zapisywany jako `praca/lut_<indeks>.cube`, a filtr `lut3d=lut_<indeks>.cube` stoi na końcu łańcucha segmentu (po skalowaniu do rozmiaru wyniku, przed `setsar`), w jego jedynym kodowaniu.
- ffmpeg uruchamiany z katalogiem roboczym `praca/`, a ścieżka LUT podawana względnie, bo dwukropek w ścieżce Windows łamie składnię filtra. `uruchom_ffmpeg(argumenty, katalog=None)` dostaje katalog roboczy, a `renderuj` na starcie zamienia ścieżki wejść i wyjścia na bezwzględne (`resolve()`).
- Bez zmian zostają: nakładka i napisy (przebieg końcowy), plansza.
- Siła 0 albo `kolorystyka: null` we wzorze oznacza brak `lut3d` wszędzie i brak liczenia statystyk: polecenia segmentów są identyczne jak przed tą częścią.
- `--sila-koloru` domyślnie 0,6. Podsumowanie dostaje `"kolor": {"sila": 0.6, "sekcje": true} | null`.
- `SILA_KOLORU` w `.env` (domyślnie 0.6; przecinek też jest akceptowany), `Konfiguracja.sila_koloru: float = 0.6`, `.env.example`. Wartość spoza przedziału 0 do 1 daje `ValueError` przy starcie. Bot przekazuje `--sila-koloru`.

## Zadania

### [Task 5.1: Statystyki barw ujęć wzoru]
- **Objective:** `kolor.rgb_do_lab`, `kolor.lab_do_rgb`, `kolor.statystyki_obrazu`, `analyze.uruchom_probkowanie`, `analyze.statystyki_koloru`, pole `kolorystyka` i `WERSJA_WZORU = 4`.
- **Context/Inputs:** kontrakty `kolorystyka` i próbkowania; `src/analyze.py` (`analizuj_wzor`, `wykryj_ciecia`, `WERSJA_WZORU`); `tests/generuj.py` (`wideo_z_cieciami`, `klip_testowy` z kolorem). `--wszystkie` z części 4 dokłada `kolorystyka` do istniejących wzorów bez zmian w CLI.
- **Constraints:** testy (`tests/test_kolor.py`, `tests/test_analiza.py`) łapią skalę 8-bitową i zamianę kanałów:
  1. wideo w jednolitej bieli daje L około 100, a a i b około 0 (tolerancja 1);
  2. jednolita czerwień sRGB daje około (53,2; 80,1; 67,2) z tolerancją 1;
  3. wideo z dwoma ujęciami, pomarańczowym i niebieskim, daje 2 wpisy: pierwszy z b > 20, drugi z b < −20;
  4. liczba wpisów równa się `len(ciecia_s)`;
  5. ujęcie krótsze niż 0,1 s ma `probki: 0` i statystyki najbliższej klatki;
  6. wywołanie z bota z dwoma argumentami działa, a `--wszystkie` daje `wersja: 4` z `kolorystyka`;
  7. proces próbkowania nie zostaje po analizie, także gdy analiza rzuci wyjątek (test z podmienionym `wykryj_ciecia`).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.1 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/analyze.py, tests/generuj.py, tests/test_analiza.py. Weryfikacja: python -m pytest -q tests/test_kolor.py tests/test_analiza.py
```
- **Commit:** `kolor: statystyki Lab ujęć wzoru`

### [Task 5.2: LUT przeniesienia barw]
- **Objective:** `kolor.cel_sekcji`, `kolor.lut_transferu`, `kolor.zapisz_cube`.
- **Context/Inputs:** kontrakty `src/kolor.py`.
- **Constraints:** testy w `tests/test_kolor.py`:
  1. LUT z identycznych statystyk (albo przy sile 0) nałożony przez ffmpeg `lut3d` na obraz z gradientem daje wynik równy wejściu z tolerancją 2 poziomów na kanał. Łapie to złą kolejność osi w `.cube` (tablica z zamienionymi osiami nie jest tożsamością) i ścieżkę w filtrze na Windows (ffmpeg z katalogiem roboczym, ścieżka względna);
  2. źródło jednolicie szare (odchylenie bliskie 0) daje LUT bez NaN i nieskończoności, w zakresie od 0 do 1;
  3. cel ciepły (duże b) i neutralny materiał: średnie b materiału po LUT rośnie;
  4. `cel_sekcji`:
     - hak i montaż liczone osobno;
     - ostatnie ujęcie pominięte;
     - bez `sekcje` wszystkie ujęcia oprócz ostatniego;
     - łączne odchylenie zgodne z przypadkiem policzonym ręcznie (dwa ujęcia o różnych średnich).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.2 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/kolor.py i tests/test_kolor.py. Weryfikacja: python -m pytest -q tests/test_kolor.py
```
- **Commit:** `kolor: LUT przeniesienia barw`

### [Task 5.3: Kolor w segmentach]
- **Objective:** render nakłada LUT na każdy segment oprócz planszy; siła z konfiguracji.
- **Context/Inputs:** kontrakt „Render”; `src/render.py` (`uruchom_ffmpeg`, `segment_zdjecia`, `segment_klipu`, `segment_planszy`, pętla segmentów w `renderuj`, `glowna`), `src/kolor.py`, `src/konfiguracja.py`, `.env.example`, `src/bot.py` (`renderuj_w_tle`).
- **Constraints:** nadal jedno kodowanie na segment i jedno kodowanie wyniku. Testy:
  1. przy sile 0 żadne polecenie ffmpeg nie ma `lut3d` (podmienione `uruchom_ffmpeg` zbiera polecenia);
  2. wzór z `kolorystyka`, w której hak ma b +30, a montaż b −30, szare materiały, siła 1,0: średnie b klatki ujęcia z haka jest większe niż +10, a z montażu mniejsze niż −10;
  3. plansza zachowuje swój kolor (±6 poziomów) przy sile 1,0;
  4. wzór bez `kolorystyka` renderuje się bez błędu i bez `lut3d`;
  5. `SILA_KOLORU`: `0.6` i `0,6` dają 0,6, a `1.5` daje `ValueError`;
  6. bot przekazuje `--sila-koloru` z konfiguracji.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.3 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/render.py, src/kolor.py, src/konfiguracja.py, .env.example, src/bot.py, tests/test_render.py, tests/test_konfiguracja.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: kolor wzoru na segment`

### [Task 5.4: Pomiar]
- **Objective:** `Pomiary/measure_kolor.py`, wynik w `outputs/pomiar_kolor.json` i arkusze.
- **Context/Inputs:**
  - **Sekcja A** (syntetyczna):
    - wzór dwusekcyjny (ciepły hak, niebieski montaż, plansza), barwne materiały z generatora;
    - ΔE76 między średnią Lab każdej sekcji wyniku a celem tej sekcji, przy sile 0, 0,6 i 1,0;
    - osobno dla celu na sekcję i celu z całości (`cel_sekcji` bez `sekcje`).
  - **Sekcja B** (prawdziwe wzory z `dane/probki/wzory/`, cache analizy w wersji 4 w `outputs/wzor_<nazwa>.json`):
    - te same miary na materiałach z `dane/probki/materialy/`;
    - narzut czasu renderu przy sile 0,6 wobec 0, w procentach;
    - czas analizy wzoru 4K z próbkowaniem i bez.
  - **Sekcja C:** arkusze `outputs/porownanie_kolor_<wzor>_<sila>.png` dla sił 0, 0,6 i 1,0.
- **Constraints:** progi:
  - przy sile 0,6 ΔE na sekcję mniejsze niż przy sile 0, w każdej sekcji każdego wzoru;
  - analiza z próbkowaniem najwyżej 1,3 raza dłuższa;
  - reszta to raport. Wybór siły domyślnej należy do oceniającego.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 5.4 z Pomiary/PLAN_EDITY_5_KOLOR.md; otwórz src/render.py, src/kolor.py, src/analyze.py, tests/generuj.py, Pomiary/arkusz.py, Pomiary/measure_muzyka.py jako wzór układu. Weryfikacja: python Pomiary/measure_kolor.py
```
- **Commit:** `Pomiary: pomiar koloru`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: ΔE przy sile 0,6 mniejsze niż przy 0 w każdej sekcji każdego wzoru, analiza najwyżej 1,3 raza dłuższa, arkusze powstały.
- Wdrożenie (Ty): `wdroz.ps1`, potem na serwerze `docker compose exec bot python src/analyze.py --wszystkie`.
- Test ręczny (Ty):
  - ten sam projekt renderowany dwa razy z CLI na serwerze, z `--sila-koloru 0` i `0.6`: `docker compose exec bot python src/render.py --wzor ... --projekt ... --muzyka dane/muzyka --wyjscie ... --sila-koloru 0.6`, tak jak przy teście zadania 3.7;
  - hak w kolorach haka wzoru, montaż w kolorach montażu, skóra i niebo nie wyglądają nienaturalnie, plansza bez zmian;
  - każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `kolor: statystyki Lab ujęć wzoru`
2. `kolor: LUT przeniesienia barw`
3. `render: kolor wzoru na segment`
4. `Pomiary: pomiar koloru`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 5 według Pomiary/PLAN_EDITY_5_KOLOR.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie) oraz zalecana siła domyślna.
```
1. `git log --oneline main..kolor`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_kolor.py`: progi ΔE i czasu analizy; porównanie celu na sekcję z celem z całości.
3. Arkusze `outputs/porownanie_kolor_*.png`: przy której sile wynik jest najbliżej nastroju wzoru bez przebarwień, czy hak i montaż różnią się tak jak we wzorze, czy plansza jest nietknięta.
4. `src/analyze.py`: próbkowanie równolegle z wykrywaniem cięć i zawsze zakończone; jednostki Lab i kolejność kanałów.
5. `src/kolor.py`: kolejność osi w `.cube`, ograniczenie stosunku odchyleń, pominięcie ostatniego ujęcia w `cel_sekcji`.
6. `src/render.py`:
   - `lut3d` tylko w segmentach i bez drugiego kodowania;
   - plansza bez LUT;
   - ścieżka LUT względna;
   - przy sile 0 polecenia bez zmian.
