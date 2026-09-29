# Część 12: styl `0923` w renderze (pasy kinowe, kolaż na spokojnym tle, efekty wzoru)

**Zależy od:** części 10 (kolaż, przejścia) i 11 (reżyser, krytyk, polecenie ze stylem `0923`).
**Gałąź:** zadania 12.1 i 12.2 zrobił Opus 2026-09-29 na `claude/jolly-cray-kzqze8` (do scalenia nowym PR, bo PR #31 jest już scalony). Zadania 12.3 do 12.7: gałąź `styl` od `main` po tym scaleniu.
**Efekt:** edity bliższe `0923` bez kopiowania jego obrazu:
- klipy z czarnymi pasami kinowymi wypełniają cały kadr (12.1);
- przejścia jak w `0923`: pionowa smuga, która znika w 7 klatkach, rozciągnięcie pikseli i najazd na każdym ujęciu, nie tylko na planszy (12.2);
- wycinki tylko na spokojnym tle (zdjęcia i klipy prawie bez ruchu), duże, przy krawędziach, w miejscach kadru z najmniejszą zajętością, także na zdjęciach (12.3);
- kolaż w rytmie `0923`: elementy co pół uderzenia, wjazd z rozmyciem ruchu, jeden duży posąg powiększany przed planszą, zwykłe zdjęcia jako kafle (12.4);
- pierścień gwiazd w haku (12.5);
- reżyser i krytyk znają nowe możliwości (12.6);
- pomiar z arkuszami i próbnymi editami (12.7).

**Dlaczego:** werdykt właściciela 2026-09-27 na próbnym edicie z AI: „dalej jest za mało dynamiczny, posągi są wstawiane bez sensu i nie na miejscu”. Decyzja z tego samego dnia: „punkt 2, zmiany do treści klipu i resztę, żeby edity bardziej przypominały edit 0923, ale go nie kopiowały bezpośrednio”. Małe zadania robi od razu Opus, resztę wykonawca. Pomiar z dziennika (2026-09-27): edit AI tnie częściej niż wzór (28 cięć wobec 18), więc różnica leży w treści kadru i w efektach, a nie w tempie cięć.

**Bez kopiowania:** z `0923` bierzemy tylko liczby: rytm, rozmiary, czasy i ruch efektów. Gwiazdy, smugi i wejścia rysuje render z tych parametrów, a obraz pochodzi z materiałów właściciela. Żadna klatka, wycinek ani dźwięk wzoru nie trafia do wyniku (reguła 7 w `CLAUDE.md`).

**Pomiar `0923` (Opus, 2026-09-27, plik 720p z gałęzi `gotowiec`, klatki co 1/30 s):**
1. Tła kolaży: flaga (0 do 0,93 s), rycina (5,87 do 9,57 s), fjord (20,57 do 21,83 s) i sztandar SPQR (23,87 do 24,77 s). Ruch tła (średnia różnica jasności klatek odległych o 5 klatek, skala szarości 90x160) wynosi 0,00 na sztandarze i 1,65 na fjordzie. Pozostałe ujęcia wzoru mają od 7,6 do 29,2. W edicie AI posągi stały na nocnej ulicy, na ulicy z ludźmi (także na twarzach) i na budynku z ruchem kamery, a sztandar SPQR, najlepsze tło w tym edicie, został bez kolażu.
2. Elementy kolażu:
   - flaga: 5 posągów;
   - rycina: 5 zdjęć jako kafle;
   - fjord: 3 wycinki i 2 kafle;
   - sztandar: 1 duży posąg.

   Elementy wchodzą co 0,13 do 0,27 s (pół uderzenia przy 131 BPM to 0,23 s). Pierwszy wchodzi od 0 do 0,5 s po cięciu.
3. Rozmiary i miejsca:
   - wycinki mają 45 do 55% wysokości kadru i 40 do 60% szerokości;
   - posąg na sztandarze ma około 100% wysokości, a jego stopy są za dolną krawędzią;
   - elementy stoją przy krawędziach i w rogach, częściowo poza kadrem, i zachodzą na siebie. Na fladze środek zostaje dla napisu;
   - kafle mają 30 do 60% szerokości i 20 do 28% wysokości. To prostokąty bez ramki w luźnej siatce w górnych dwóch trzecich kadru.
4. Wejścia: większość elementów wjeżdża od krawędzi w 2 do 3 klatek, większa niż docelowo i rozmyta ruchem, a część po prostu się pojawia. Posąg na sztandarze pomniejsza się z około 2x przez 14 klatek (0,47 s), a jego rozmycie w tym czasie słabnie.
5. Gwiazdy: 12 złotych gwiazd na okręgu od 1,27 s do cięcia w 5,87 s, czyli przez trzy ujęcia haka po planszy tytułowej.
   - Środek okręgu jest zawsze w środku kadru (0,50; 0,50), a nie na postaci.
   - Promień rośnie od 0,08 do 0,39 szerokości kadru według r(t) = 0,40 − 0,34·e^(−t/1,5 s).
   - Okrąg obraca się o 130 do 150° na sekundę.
   - Gwiazdy dochodzą po kolei w pierwszych 0,4 s.
   - Rozpiętość gwiazdy to około 0,14 promienia okręgu.
6. Przejścia:
   - na cięciu do mapy (12,93 s): pionowa smuga, która znika w 7 klatkach;
   - na wejściu ryciny (5,87 s) i napisu (0,03 do 0,17 s): pionowe smugi rozciągniętych pikseli;
   - na cięciu 0,93 s: rozmycie z zoomem.
7. Pasy kinowe: w edicie AI 8 ujęć ma pasy u góry i u dołu, każdy od 8,8 do 13,0% wysokości. W dwóch z nich pasy przykrywa w renderze wycinek albo flaga. Wzór jest pełnoekranowy.

**Nowe pliki:** `tests/test_styl.py`, `Pomiary/measure_styl.py` (oba powstają w 12.1).
**Zmieniane:**
- kod: `src/render.py`, `src/rezyser.py`, `src/konfiguracja.py`, `.env.example`, `src/bot.py` (tylko przekazanie `--bez-gwiazd`);
- testy: `tests/test_render.py`, `tests/test_dynamika.py`, `tests/test_rezyser.py`, `tests/test_konfiguracja.py`, `tests/test_bot.py`.

**Od właściciela:**
- werdykt na arkuszach i próbnych editach z pomiaru 12.7;
- zgoda na koszt części pomiaru z AI (szacunek 1,5 $);
- decyzja o scaleniu.

Prompt startowy (zadania 12.3 do 12.7 w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 12.3 do 12.7 z Pomiary/PLAN_EDITY_12_STYL.md na gałęzi `styl` od aktualnego `main` (przed startem `git pull`), zaczynając od „Stan wejściowy”. Zadania 12.1 i 12.2 są już zrobione. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Nie otwieraj `.env` i nie wypisuj klucza API nigdzie. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Część pomiaru 12.7 z AI wydaje prawdziwe pieniądze: uruchom ją tylko wtedy, gdy klucz jest ustawiony, i podaj koszt w raporcie. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan 12 pisany 2026-09-29 (Opus) po pomiarze wzoru `0923` i próbnego editu AI z 2026-09-27, reszta bloku jak w częściach 10 i 11. Kotwic `plik:linia` ten plan nie podaje, bo zadania 12.1 i 12.2 zmieniły `src/render.py`: szukaj po nazwie funkcji. Po wcześniejszych częściach mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edity wideo 9:16 na TikToka z dostarczonych materiałów. Wzorem jest gotowy edit: bot odtwarza jego strukturę i styl, a muzykę bierze z biblioteki właściciela w `dane/muzyka/`. Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
  - Edity promują czapki marki właściciela 1993 Supply (2026-09-24). Plansza końcowa pokazuje produkt albo stronę sklepu, a znak wodny marki leży na całym edicie poza planszą (wzór `0914`, zadanie 8.6).
  - Prawdziwe wzory (`0914`, `0915`, `0921`, `0922`, `0923`) mają ten sam format: hak (pierwsze 4 do 11 s, naturalne kolory, napis), drop (od niego pełnoekranowa nakładka graficzna i mocny grading), montaż i plansza końcowa około 1 s (mapa, decyzja 15). `0923` ma dodatkowo napisy słowo po słowie w rytmie (zadania 9.6 do 9.10), wycinki wskakujące na tło w rytmie (część 10) i pierścień gwiazd w środku kadru w haku (pomiar w nagłówku części 12).
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
`main` zawiera commity `render: pasy kinowe w klipach` (12.1) i `render: przejścia jak w 0923` (12.2), a `python -m pytest -q` przechodzi. Utwórz gałąź `styl` od `main`. Jeśli któregoś commita brakuje, zatrzymaj się i zapytaj.

## Kontrakt z wcześniejszych części
Szukaj po nazwach, bo numery linii się przesuwają.
- Część 10 w `src/render.py`:
  - `zmontuj` składa segmenty. Kolaż automatu wybiera `kolaz_kwalifikuje`: co drugi klip, co najmniej 1,5 s, nie na dropie, poza oknami słów;
  - `przygotuj_kolaz(wycinki_kolazu, uderzenia_lokalne, liczba_klatek, fps, szerokosc, wysokosc, wyjscie)`. Wycinek jest przycięty do kanału alfa (`wytnij_do_alfa`) i dopasowany do pola 55% na 36% (`dopasuj_do_pola_kolazu`). Stoi w stałych polach `POLA_KOLAZU` i wskakuje na kolejnych uderzeniach ze skalami `WSKOK_SKALE_KOLAZU`;
  - `segment_klipu(..., kolaz=...)` nakłada warstwę kolażu drugim wejściem i `overlay` w tym samym kodowaniu. `segment_zdjecia` kolażu nie ma;
  - `materializuj_warstwe(generator_klatek, liczba_klatek, fps, szerokosc, wysokosc, wyjscie)`;
  - `przebieg_koncowy`: każda warstwa to klip o dokładnej liczbie klatek, bez `-t`, `-loop` i `-stream_loop` (problem 13 w `ROZWOJ.md`);
  - `uderzenia_wyniku`, `koniec_haka`, `efekt_ujecia`.
- Część 11:
  - `rezyser.Ujecie` i `plan_ze_scenariusza`: ujęcie planu niesie `efekt_scenariusza` i `kolaz_scenariusza`;
  - `zastosuj_poprawki`, `rezyser.opis_montazu`, `rezyser.numeracja(materialy, wycinki)`: zwykłe materiały mają numery 0..n−1, wycinki n..n+k−1;
  - `POLECENIE_REZYSERA` z sekcją „Styl” i `POLECENIE_KRYTYKA`.
- 12.1 (Opus): `render.wykryj_kadr` i `render.filtr_kadru`. Materiał klipu ma `kadr`. `zmontuj` dostaje `kadry_klipow`, a podsumowanie ma listę `pasy`.
- 12.2 (Opus): `przejscie` w `segment_zdjecia` i `segment_klipu` przyjmuje `brak`, `smuga`, `najazd` albo `rozciagniecie`. Szczegóły w kontrakcie 12.2 niżej.

## Kontrakty ustalane w tej części

**Pasy kinowe (12.1, zrobione przez Opusa):**
- `render.wykryj_kadr(sciezka, czas_s) -> dict | None`:
  - bierze 6 klatek klipu, ze środka każdej szóstej części jego długości, przeskalowanych do szerokości 320 z zachowaniem proporcji;
  - piksel jest ciemny, gdy jego najjaśniejszy kanał RGB ma najwyżej 40. Ciemnobordowy brzeg sztandaru SPQR (57, 14, 16) nie jest pasem;
  - wiersz albo kolumna należy do pasa, gdy jasnych pikseli jest w nim najwyżej 2% we wszystkich klatkach razem. Pasy liczone są od każdej krawędzi;
  - przycina tylko parami: górę z dołem albo lewą stronę z prawą. Każdy pas z pary ma co najmniej 2% wymiaru, a po przycięciu zostaje co najmniej 50% kadru. Jednostronna ciemność (czarne tło nad postacią we wzorze) nie jest przycinana. Wykryty pas dostaje 2 wiersze zapasu (1,1% wysokości klatki 16:9), bo wiersz na granicy pasa jest mieszany i przy 1 wierszu zostawał pasek około 5 px w kadrze 1920;
  - wynik to ułamki `{"x", "y", "w", "h"}`, a bez pasów `None`.
- `render.filtr_kadru(kadr)` to `crop` z wyrażeń `iw` i `ih` postawiony przed skalowaniem „cover”. Stosują go `segment_klipu`, `statystyki_klipu` (kolor liczony bez pasów) i `rezyser.klatki_klipu` (arkusze reżysera).
- `renderuj` wykrywa kadr raz na klip, razem z `czas_s`. Podsumowanie ma listę `"pasy": [{"plik", "kadr"}]`.
- Sprawdzone na klatkach (dziennik 2026-09-29): na 28 ujęciach editu AI wykryte wszystkie 6 ujęć z odsłoniętymi pasami (9,3 do 13,0% z każdej strony, z zapasem), a na 18 ujęciach `0923` nie ma ani jednego fałszywego trafienia. Na klipie 4K HEVC wykrywanie trwa około 2,6 s.

**Przejścia (12.2, zrobione przez Opusa):**
- `smuga`: pionowa smuga, która słabnie przez 7 klatek, jak na cięciu do mapy w `0923`:
  `gblur=sigma=1:sigmaV=80:enable='lt(n,3)',gblur=sigma=1:sigmaV=35:enable='between(n,3,4)',gblur=sigma=1:sigmaV=12:enable='between(n,5,6)'`.
  Wcześniej była to stała `sigmaV=60` przez 4 klatki.
- `rozciagniecie`: wiersz kadru na 45% wysokości rozciągnięty w dół do dolnej krawędzi, z kryciem malejącym do zera przez 10 klatek:
  `split[a][b];[b]crop=W:2:0:Y,scale=W:H-Y:flags=neighbor,format=yuva420p,fade=t=out:start_frame=0:nb_frames=10:alpha=1[s];[a][s]overlay=0:Y:enable='lt(n,10)'`.
- `najazd` działa na każdym ujęciu, a nie tylko na planszy. Zoom 0,35 trwa 6 klatek (`SILA_NAJAZDU`, `KLATEK_NAJAZDU`) zamiast uderzenia 0,12, a do tego `gblur=sigma=18:enable='lt(n,3)'`.
- Kolejność filtrów bez zmian: skalowanie, zoom, `lut3d`, wstrząs, przejście, błysk.
- Automat (`efekt_ujecia`):
  - drugie ujęcie editu dostaje `najazd`, jak cięcie 0,93 s we wzorze, chyba że zaczyna się na dropie;
  - co trzecie zdjęcie po dropie dostaje na zmianę `smuga` i `rozciagniecie`, zaczynając od smugi;
  - reszta reguł części 10 zostaje.
- Schemat reżysera: `przejscie` przyjmuje `brak`, `smuga`, `najazd` albo `rozciagniecie`, a polecenie opisuje wszystkie cztery.

**Kolaż na spokojnym tle (12.3):**
- `render.klatki_tla(ujecie, sciezki_robocze, kadry_klipow, fps) -> numpy.ndarray`: 4 klatki tła ujęcia w skali szarości 90x160, kadrowane tak jak segment (pasy, potem „cover” do 9:16), bez efektów. Dla klipu to środki czterech ćwiartek fragmentu, a dla zdjęcia 4 razy jego `plik_roboczy`.
- `render.ruch_tla(klatki) -> float`: średnia bezwzględna różnica kolejnych klatek. Próg `PROG_RUCHU_KOLAZU = 5.0`, między 1,65 (fjord) a 7,6 (najspokojniejsze ujęcie wzoru bez kolażu).
- `render.mapa_zajetosci(klatki) -> numpy.ndarray` 160x90: `|dx|+|dy|` uśrednione po klatkach plus 2 razy średnia różnica kolejnych klatek, rozmyte oknem 9x9.
- `render.miejsca_kolazu(mapa, rozmiary, strona="auto") -> list[tuple[float, float]]` zwraca lewe górne rogi elementów w ułamkach kadru:
  - kandydatów jest 8: 4 rogi i środki 4 krawędzi, bez środka kadru. Element może wystawać poza kadr o 8% własnego rozmiaru;
  - elementy wybierane są po kolei, każdy na miejscu o najmniejszej średniej zajętości pod swoim prostokątem, a każde miejsce jest użyte raz;
  - `strona` (`gora`, `dol`, `lewo`, `prawo`, pole z 12.6) zawęża kandydatów do tej krawędzi i sąsiednich rogów, a `auto` ich nie zawęża.
- Rozmiary elementów:
  - wycinek ma wysokość 50% kadru, gdy elementów jest 2 lub więcej, i 60% przy jednym. Szerokość najwyżej 60% kadru, proporcje wycinka zachowane (contain);
  - kafel z 12.4 ma 45% szerokości i najwyżej 28% wysokości.
- Gdzie stoi kolaż:
  - w scenariuszu kolaż może stać na zdjęciu albo na klipie. Gdy `ruch_tla > PROG_RUCHU_KOLAZU`, kolaż odpada z ostrzeżeniem „ujęcie N: tło w ruchu (R), kolaż pominięty”;
  - automat zamiast reguły „co drugi klip”: kandydaci to ujęcia co najmniej 1,5 s, nie na dropie, nie plansza, poza oknami słów i z `ruch_tla ≤ PROG_RUCHU_KOLAZU`. Automat bierze najwyżej 3 najspokojniejsze, oddalone od siebie co najmniej o 3 s.
- Segment zdjęcia z kolażem nakłada warstwę tak samo jak `segment_klipu`: drugie wejście, `overlay`, to samo kodowanie.
- Podsumowanie `kolaze`: każdy wpis dostaje `ruch` i `miejsca`. Nowa lista `kolaze_pominiete` ma wpisy `{"ujecie", "ruch"}`.

**Kolaż w rytmie wzoru (12.4):**
- Czas wejścia:
  - elementy wchodzą co pół uderzenia; półuderzenia to uderzenia wyniku i środki między nimi;
  - pierwszy element wchodzi na pierwszym półuderzeniu co najmniej 2 klatki po początku ujęcia;
  - element, który wszedłby później niż 0,25 s przed końcem ujęcia, odpada;
  - najwyżej `LICZBA_ELEMENTOW_KOLAZU = 5` elementów.
- Wejścia (`wejscie`): `wjazd` (domyślne), `wskok` (dzisiejsze skale 0,45, 0,85, 1,12, 1,05) i `powiekszenie`:
  - `wjazd` trwa 3 klatki. Element startuje przesunięty o 35% swojego rozmiaru w stronę najbliższej krawędzi kadru i w skali 1,3, a kończy w miejscu docelowym w skali 1,0. Rozmycie ruchu to średnia 5 kopii elementu na odcinku ruchu w danej klatce (PIL, bez nowych zależności);
  - `powiekszenie` to jeden element na całe ujęcie: wysokość 95% kadru, dolna krawędź 5% poniżej kadru, środek w poziomie w miejscu z najmniejszą zajętością. Przez 14 klatek skala maleje z 2,0 do 1,0, a rozmycie Gaussa z 12 px do 0 (przy szerokości 1080, proporcjonalnie mniej przy mniejszej), łagodnie na końcu.
- Kafle: zwykłe zdjęcia w kolażu jako prostokąty, dopasowane „cover” do rozmiaru kafla, bez ramki, w pełnym kryciu. Kafle przychodzą tylko ze scenariusza (numery zdjęć w polu `kolaz`, 12.6). Automat ich nie używa.
- Automat: wejście `wjazd`, wycinki z puli jak dziś (cyklicznie), elementów tyle, ile półuderzeń mieści ujęcie, najwyżej `LICZBA_ELEMENTOW_KOLAZU`.

**Gwiazdy w haku (12.5):**
- Warstwa `gwiazdy` to klip RGBA z `materializuj_warstwe` o dokładnej liczbie klatek okna. W `przebieg_koncowy` leży nad nakładką i pod napisami. Kolejność warstw: materiał, nakładka, gwiazdy, napisy, słowa, napis pionowy, znak wodny.
- Rysunek:
  - 12 pięcioramiennych gwiazd koloru (255, 204, 0) na okręgu o środku (0,5 W; 0,5 H);
  - promień r(t) = W·(0,40 − 0,34·e^(−t/1,5)), gdzie t to sekundy od początku okna;
  - obrót 140° na sekundę zgodnie z ruchem wskazówek zegara;
  - rozpiętość gwiazdy 0,14 r, najmniej 4 px;
  - gwiazda numer k pojawia się w klatce k, więc wszystkie są po 12 klatkach (około 0,4 s).
- Okno:
  - automat: od początku drugiego ujęcia przez 4,6 s. Okno kończy się najpóźniej na początku pierwszego późniejszego ujęcia z kolażem i najpóźniej 1 uderzenie przed dropem;
  - scenariusz: od pierwszego ujęcia z `gwiazdy` do końca ostatniego z kolejnych ujęć z `gwiazdy` (12.6);
  - okno krótsze niż 1 s nie powstaje.
- Konfiguracja: `GWIAZDY_W_HAKU` (`tak` albo `nie`, domyślnie `tak`) w `.env` i `Konfiguracja`, CLI `--bez-gwiazd`, a bot przekazuje flagę. `--bez-dynamiki` też wyłącza gwiazdy.
- Podsumowanie: `"gwiazdy": {"od_s", "do_s"}` albo `null`.

**Reżyser i krytyk (12.6):**
- Nowe pola `rezyser.Ujecie`:
  - `kolaz`: najwyżej 5 numerów wycinków i zwykłych zdjęć (kafle), na zdjęciu albo na klipie;
  - `wejscie_kolazu`: `wjazd`, `wskok` albo `powiekszenie`, domyślnie `wjazd`;
  - `miejsce_kolazu`: `auto`, `gora`, `dol`, `lewo` albo `prawo`, domyślnie `auto`. To strona, po której w kadrze jest wolne tło;
  - `gwiazdy`: bool, domyślnie false.
- `plan_ze_scenariusza` i `zastosuj_poprawki` przenoszą nowe pola do ujęcia planu (`kolaz_scenariusza`, `wejscie_kolazu`, `miejsce_kolazu`, `gwiazdy`). Numer klipu w `kolaz` odpada z ostrzeżeniem.
- `POLECENIE_REZYSERA`: zdanie o stałych miejscach wycinków znika. W jego miejsce idzie opis 12.3 i 12.4:
  - render mierzy ruch tła i usuwa kolaż z tła w ruchu;
  - miejsca elementów wybiera render, a `miejsce_kolazu` wskazuje stronę bez twarzy i głównej postaci;
  - kafle to zwykłe zdjęcia;
  - otwarcie to plansza tytułowa z 3 do 5 elementami;
  - `powiekszenie` jednego posągu przed planszą;
  - `gwiazdy` na 2 do 3 ujęciach haka po otwarciu.

  Polecenie dalej nie ma zmiennych.
- `opis_montazu` podaje kolaż z elementami, wejściem, miejscami i ruchem tła, a także gwiazdy i przejście.
- `POLECENIE_KRYTYKA` sprawdza tło kolaży, rozmiary i miejsca elementów oraz pierścień gwiazd.

**Pomiar (12.7):** `Pomiary/measure_styl.py`. Sekcja A (pasy) powstała w 12.1. Zadanie 12.7 dokłada sekcje B i C (niżej).

## Zadania

### [Task 12.1: Pasy kinowe w klipach] zrobione (Opus, 2026-09-29)
- **Objective:** `wykryj_kadr`, `filtr_kadru`, przycięcie pasów w segmencie, kolorze i arkuszach reżysera, `pasy` w podsumowaniu, sekcja A pomiaru.
- **Constraints:** testy w `tests/test_styl.py`:
  1. para pasów (góra i dół) wykryta w klipie 480x270 z pasami po 35 px;
  2. jednostronna ciemność, ciemnobordowy brzeg i cały czarny klip nie są przycinane;
  3. segment klipu z pasami nie ma ciemnych wierszy przy górnej i dolnej krawędzi, a bez kadru je ma;
  4. arkusz reżysera pokazuje klip bez pasów;
  5. pełny render z klipem z pasami: kod 0 i klip na liście `pasy`.
- **Commit:** `render: pasy kinowe w klipach`

### [Task 12.2: Przejścia jak w 0923] zrobione (Opus, 2026-09-29)
- **Objective:** kontrakt „Przejścia”: nowa `smuga`, `rozciagniecie`, `najazd` na każdym ujęciu, reguły automatu, schemat i polecenie reżysera.
- **Constraints:** testy: każde przejście na zdjęciu i na klipie daje segment o właściwej liczbie klatek; `rozciagniecie` robi pionowe smugi pod linią 45% w pierwszych klatkach i znika po 10; `najazd` rozmywa pierwsze klatki; reguły automatu (drugie ujęcie, zmiana smugi i rozciągnięcia); `przejscie` w schemacie z czterema wartościami.
- **Commit:** `render: przejścia jak w 0923`

### [Task 12.3: Kolaż na spokojnym tle]
- **Objective:** kontrakt „Kolaż na spokojnym tle”: `klatki_tla`, `ruch_tla`, `mapa_zajetosci`, `miejsca_kolazu`, kolaż na zdjęciu, bramka ruchu dla scenariusza i automatu, podsumowanie.
- **Context/Inputs:** `src/render.py` (`zmontuj`, `przygotuj_kolaz`, `kolaz_kwalifikuje`, `segment_zdjecia`, `segment_klipu`, `filtr_kadru`), `tests/test_styl.py`, `tests/test_dynamika.py`, `tests/generuj.py`.
- **Constraints:** testy:
  1. `ruch_tla`: 4 takie same klatki dają 0, a klatki szumu dają więcej niż próg;
  2. `miejsca_kolazu` na klatce z szumem po lewej i gładką prawą połową stawia wszystkie elementy po prawej; `strona="gora"` daje tylko miejsca przy górnej krawędzi; element może wystawać poza kadr o 8%;
  3. kolaż ze scenariusza na klipie z szumem odpada z ostrzeżeniem, a na klipie jednolitym zostaje;
  4. kolaż na zdjęciu: w segmencie widać kolor wycinka w wybranym miejscu;
  5. automat: klip jednolity dostaje kolaż, klip z szumem nie; najwyżej 3 kolaże, co najmniej 3 s od siebie;
  6. segmenty bez kolażu mają te same polecenia ffmpeg co przed zadaniem.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź styl. Wykonaj zadanie 12.3 z Pomiary/PLAN_EDITY_12_STYL.md; otwórz src/render.py, tests/test_styl.py, tests/test_dynamika.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: kolaż na spokojnym tle`

### [Task 12.4: Kolaż w rytmie wzoru]
- **Objective:** kontrakt „Kolaż w rytmie wzoru”: półuderzenia, do 5 elementów, wejścia `wjazd`, `wskok` i `powiekszenie`, kafle ze zwykłych zdjęć.
- **Context/Inputs:** `src/render.py` (`przygotuj_kolaz`, `zmontuj`, `uderzenia_wyniku`), `tests/test_styl.py`, `tests/test_dynamika.py`.
- **Constraints:** testy:
  1. klatki wejścia elementów leżą na półuderzeniach, a żaden nie wchodzi w ostatnich 0,25 s ujęcia;
  2. `wjazd`: w pierwszej klatce element jest przesunięty w stronę najbliższej krawędzi i większy, a w czwartej stoi w miejscu docelowym;
  3. `powiekszenie`: w pierwszej klatce element ma skalę 2,0 i jest rozmyty, a w 15. ma skalę 1,0 i jest ostry;
  4. kafel: zwykłe zdjęcie w kolażu daje prostokąt w jego kolorze w miejscu kafla;
  5. najwyżej 5 elementów.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź styl. Wykonaj zadanie 12.4 z Pomiary/PLAN_EDITY_12_STYL.md; otwórz src/render.py, tests/test_styl.py, tests/test_dynamika.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: kolaż w rytmie wzoru`

### [Task 12.5: Gwiazdy w haku]
- **Objective:** kontrakt „Gwiazdy w haku”: warstwa, okno, konfiguracja, flaga w bocie, podsumowanie.
- **Context/Inputs:** `src/render.py` (`materializuj_warstwe`, `przebieg_koncowy`, `renderuj`, `glowna`), `src/konfiguracja.py`, `.env.example`, `src/bot.py` (tylko budowa polecenia renderu), `tests/test_styl.py`, `tests/test_konfiguracja.py`, `tests/test_bot.py`.
- **Constraints:** testy:
  1. klatka warstwy po 1 s ma 12 złotych plam na okręgu o środku (0,5 W; 0,5 H) i promieniu W·(0,40 − 0,34·e^(−1/1,5)) z tolerancją 5%;
  2. między sąsiednimi klatkami okrąg obraca się o 140/fps stopni z tolerancją 1°;
  3. okno automatu: start na drugim ujęciu, 4,6 s, przycięte przed dropem i przed ujęciem z kolażem;
  4. `--bez-gwiazd`, `GWIAZDY_W_HAKU=nie` i `--bez-dynamiki` dają brak warstwy i `gwiazdy: null`. `GWIAZDY_W_HAKU=moze` daje `ValueError`;
  5. w przebiegu końcowym warstwa wchodzi jako klip bez `-t`, `-loop` i `-stream_loop`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź styl. Wykonaj zadanie 12.5 z Pomiary/PLAN_EDITY_12_STYL.md; otwórz src/render.py, src/konfiguracja.py, .env.example, src/bot.py, tests/test_styl.py, tests/test_konfiguracja.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: gwiazdy w haku`

### [Task 12.6: Reżyser i krytyk znają styl 0923]
- **Objective:** kontrakt „Reżyser i krytyk”: pola schematu, przeniesienie do planu, polecenia, opis montażu.
- **Context/Inputs:** `src/rezyser.py`, `src/render.py` (`plan_ze_scenariusza`, `zastosuj_poprawki`, `zmontuj`), `tests/test_rezyser.py`.
- **Constraints:** testy:
  1. schemat wysyłany do modelu ma nowe pola z wartościami z kontraktu i nadal nie ma słów kluczowych, których structured outputs nie obsługują (test części 11);
  2. `kolaz` dłuższy niż 5 jest przycinany; numer klipu w `kolaz` odpada z ostrzeżeniem; numer zdjęcia daje kafel;
  3. polecenie reżysera nie opisuje już stałych miejsc (`POLA_KOLAZU`), a opisuje bramkę ruchu, kafle, `powiekszenie`, `miejsce_kolazu` i `gwiazdy`;
  4. `opis_montazu` ma wejście, miejsca i ruch tła kolażu oraz gwiazdy;
  5. pełny render z podmienionym `wywolaj_model`, który używa wszystkich nowych pól: kod 0.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź styl. Wykonaj zadanie 12.6 z Pomiary/PLAN_EDITY_12_STYL.md; otwórz src/rezyser.py, src/render.py, tests/test_rezyser.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `rezyser: styl 0923 w schemacie i poleceniach`

### [Task 12.7: Pomiar stylu]
- **Objective:** sekcje B i C w `Pomiary/measure_styl.py`, wynik w `outputs/pomiar_styl.json`, arkusze i próbne edity.
- **Context/Inputs:**
  - materiały jak w pomiarze 11.4 (stała próbka plus wycinki, słowa, napis pionowy, flaga, plansza, znak);
  - **Sekcja B** (5 wzorów, montaż automatyczny i z AI). Dla obu podaj:
    - kolaże: ujęcie, ruch tła, liczba elementów, wejście, miejsca;
    - pominięte kolaże;
    - okno gwiazd;
    - przejścia;
    - liczba ujęć i koszt AI.

    Montaż z AI tylko z kluczem. Przed pierwszym wywołaniem wypisz szacunek kosztu;
  - **Sekcja C:** arkusze `outputs/porownanie_styl_<wzor>_auto.png` i `outputs/porownanie_styl_<wzor>_ai.png`, do tego próbne edity `outputs/styl_0923_auto.mp4` i `outputs/styl_0923_ai.mp4`;
  - `render.uruchom_ffmpeg` z limitem 900 s na wywołanie, `--procesy N` jak w `measure_rezyser.py`.
- **Constraints:** progi:
  - B: każdy kolaż ma ruch tła najwyżej `PROG_RUCHU_KOLAZU`, żaden kolaż nie stoi na dropie, żaden render nie przekracza limitu;
  - C: pliki powstały, a werdykt wydaje właściciel.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź styl. Wykonaj zadanie 12.7 z Pomiary/PLAN_EDITY_12_STYL.md; otwórz Pomiary/measure_styl.py, Pomiary/measure_rezyser.py jako wzór układu, src/render.py, Pomiary/arkusz.py. Weryfikacja: python Pomiary/measure_styl.py
```
- **Commit:** `Pomiary: pomiar stylu`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: B w progach, a koszt AI podany w raporcie.
- Właściciel ocenił arkusze i próbne edity: wycinki stoją na spokojnym tle i nie zasłaniają twarzy, a edit przypomina `0923` rytmem i efektami, a nie treścią. Każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `render: pasy kinowe w klipach` (Opus)
2. `render: przejścia jak w 0923` (Opus)
3. `render: kolaż na spokojnym tle`
4. `render: kolaż w rytmie wzoru`
5. `render: gwiazdy w haku`
6. `rezyser: styl 0923 w schemacie i poleceniach`
7. `Pomiary: pomiar stylu`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 12 według Pomiary/PLAN_EDITY_12_STYL.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru ani `.env`. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..styl`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `outputs/pomiar_styl.json`: ruch tła każdego kolażu, pominięte kolaże, okna gwiazd, koszt. Części z AI nie uruchamiaj drugi raz bez zgody właściciela, bo kosztuje.
3. Arkusze auto i AI dla każdego wzoru obok `0923`: tło kolaży, rozmiary i miejsca elementów, pierścień gwiazd, przejścia, brak pasów.
4. `src/render.py`: bramka ruchu przed każdym kolażem, warstwa gwiazd jako klip o dokładnej liczbie klatek, nic ze wzoru w wyniku.
5. `src/rezyser.py`: nowe pola w schemacie bez niedozwolonych słów kluczowych, polecenie bez zmiennych.
