# Część 10: dynamika (tempo cięć, przejścia, kolaż wycinków, flaga w kadrze)

**Zależy od:** części 9 w całości (zadania 9.1 do 9.4 scalone). Zadanie 9.3 dokłada `uloz_wariant` przed `wstawki`, a 9.1 czyszczenie `praca/`, czyli te same miejsca `render.renderuj`, które zmienia ta część.
**Gałąź:** `dynamika` od `main` po scaleniu `fabryka`.
**Efekt:** edity są „dopaminowe”, jak Twój wzór `0923`:
- zdjęcia zmieniają się co uderzenie, a klipy trwają 2 do 3,2 s;
- każde cięcie ma uderzenie zoomem, klipy wchodzą z błyskiem, a drop ma mocny błysk i wstrząs kadru;
- w montażu co trzecie zdjęcie wchodzi z pionową smugą, a plansza z najazdem;
- na co drugim klipie wskakują na kolejnych uderzeniach wycinki (zdjęcia z przezroczystością) i zostają do końca ujęcia, czyli „kilka zdjęć naraz”;
- flaga w trybie `krycie` mieści się cała w kadrze i trwa 2,5 s od dropu.

**Dlaczego (Twoje uwagi z 2026-09-26 do editu pokazowego na `0923`):**
- „zbyt wolno się zmieniają klatki, te edity muszą być mocno dopaminowe”;
- „zdjęcia powinny się zmieniać szybko a filmiki trwać trochę dłużej”, „niektóre filmiki są zbyt krótkie”;
- „nie ma w tym przejść żadnych, nie ma edycji”;
- „gwiazdki wylatują poza ekran”;
- „tak samo jak w tym najnowszym edicie powinno być kilka zdjęć naraz”.

Dziś render bierze cięcia wzoru 1:1, więc zdjęcie potrafi stać 3,7 s, a klip 0,9 s. Nie ma żadnych efektów na cięciach, bo mapa miała je poza zakresem. Wycinki stoją jako osobne ujęcia na czarnym tle, a flaga (16:9, skalowana „cover”) ucina krąg gwiazd po bokach i leży na całym montażu.

**Prototyp (Opus, 2026-09-26, kopia kodu poza repo, `ROZWOJ.md`):** ten sam projekt na `0923` dał 25 ujęć zamiast 18 i 22 materiały zamiast 17. Render trwał 146 s. Kontrakty niżej pochodzą z prototypu. Przejście „smuga” i „najazd” są dopisane po obejrzeniu `0923` i w prototypie ich nie było.
**Nowe pliki:** `tests/test_dynamika.py`, `Pomiary/measure_dynamika.py`.
**Zmieniane:** `src/render.py`, `tests/test_render.py`, `tests/test_nakladka.py`, `tests/generuj.py`, `src/konfiguracja.py`, `.env.example`, `tests/test_konfiguracja.py`, `src/bot.py` (tylko przekazanie parametru), `src/komunikaty.py` (podpis).
**Od właściciela:** ocena arkuszy i próbnego editu, który pomiar wysyła do `outputs/`.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 10.1 do 10.5 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md na gałęzi `dynamika` od aktualnego `main` (przed startem `git pull`), zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plany 10 i 11 pisane 2026-09-26 (Opus) po edicie pokazowym na `0923` i prototypie dynamiki, reszta bloku jak w częściach 4 do 9. Kotwice `plik:linia` pochodzą z `main` na `2330115` (po zadaniu 9.10). Po wcześniejszych częściach mogą się przesunąć: wtedy szukaj po nazwie funkcji. Jeżeli nazwy lub kontrakty nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu oraz `Pomiary/ROZWOJ.md`, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edity wideo 9:16 na TikToka z dostarczonych materiałów. Wzorem jest gotowy edit: bot odtwarza jego strukturę i styl, a muzykę bierze z biblioteki właściciela w `dane/muzyka/`. Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
  - Edity promują czapki marki właściciela 1993 Supply (2026-09-24). Plansza końcowa pokazuje produkt albo stronę sklepu, a znak wodny marki leży na całym edicie poza planszą (wzór `0914`, zadanie 8.6).
  - Prawdziwe wzory (`0914`, `0915`, `0921`, `0922`, `0923`) mają ten sam format: hak (pierwsze 4 do 11 s, naturalne kolory, napis), drop (od niego pełnoekranowa nakładka graficzna i mocny grading), montaż i plansza końcowa około 1 s (mapa, decyzja 15). `0923` ma dodatkowo napisy słowo po słowie w rytmie (zadania 9.6 do 9.10), wycinki wskakujące na tło w rytmie (część 10) i gwiazdy wokół postaci przed dropem.
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
`main` zawiera commit `Pomiary: pomiar fabryki` (zadanie 9.4) i commit `tekst: akcent na całą szerokość i wjazd poza kadr` (9.10), a `python -m pytest -q` przechodzi. Utwórz gałąź `dynamika` od `main`. Jeśli któregoś commita brakuje, zatrzymaj się i zapytaj.

## Kontrakt z wcześniejszych części
Numery linii z `main` po zadaniu 9.10 (`2330115`). Po części 9 mogą się przesunąć, więc szukaj po nazwach.
- `src/render.py`:
  - `wstawki(materialy, dlugosc_wstawki_s)` (345) tnie klipy na kawałki od początku klipu i układa je rundami. `renderuj` (896) liczy dziś `dlugosc_wstawki_s = min(2.0, max(0.5, mediana ujęć wzoru))`;
  - `plan_ujec(...)` (381) zwraca `{fps, start_audio_s, liczba_klatek, ujecia}`, a ujęcie ma `material`, `typ`, `klatka_od`, `liczba_klatek`, `start_w_klipie_s` i `numer_wzoru`. Jedno ujęcie wzoru to dziś jedno ujęcie wyniku;
  - `koniec_haka(plan, sekcje)` (657) to klatka dropu (pierwsze ujęcie z `numer_wzoru >= drop_ujecie`);
  - `uderzenia_wyniku(uderzenia_utworu, start_audio_s, liczba_klatek, fps)` (755) zwraca klatki uderzeń w wyniku;
  - `wyrazenie_zoom` i `segment_zdjecia`: Ken Burns przez `zoompan` na obrazie 2x (`MNOZNIK_ROBOCZY_ZOOM`), zoom do `ZOOM_MAKSYMALNY` 1,12, bez `x` i `y`, więc zakotwiczony w lewym górnym rogu;
  - `segment_klipu`: skalowanie „cover”, `fps`, `tpad` (klip za krótki dostaje zamrożoną ostatnią klatkę), potem `lut3d`;
  - `ma_alfa_z_pil(sciezka)` (228) rozpoznaje zdjęcie z przezroczystością. `przygotuj_zdjecie` spłaszcza je na czarne tło;
  - `materializuj_warstwe(generator_klatek, liczba_klatek, fps, szerokosc, wysokosc, wyjscie)` (726) zapisuje klatki PIL RGBA do klipu `png` w `.mov` (zadanie 9.6);
  - `przebieg_koncowy`, tryb `krycie`: `scale ... force_original_aspect_ratio=increase, crop`, potem `colorchannelmixer=aa=KRYCIE_NAKLADKI`;
  - `okno_nakladki(wzor, plan, plansza_uzyta)` (670): od dropu do planszy;
  - okna słów w rytmie z `przygotuj_slowa` (zadanie 9.6) i napis pionowy z `przygotuj_pionowy` (9.7) czytają `plan`, więc działają na nowym planie bez zmian.
- Zadanie 9.3: `uloz_wariant(materialy, wariant)` przed `wstawki` i `--wariant` w CLI.
- Zasada z 9.6 i problemu 12 w `ROZWOJ.md`: nowa warstwa to klip z dokładną liczbą klatek, nigdy obraz przez `-loop 1 -t` w przebiegu końcowym.

## Kontrakty ustalane w tej części

**Tempo cięć (10.1):**
- Stałe w `render.py`: `TEMPO_ZDJECIA_MIN_S = 0.30`, `TEMPO_KLIPU_MIN_S = 2.0`, `TEMPO_KLIPU_MAX_S = 3.2`, `DLUGOSC_WSTAWKI_S = 3.5` (zamiast mediany ujęć wzoru, bo kawałek klipu musi wystarczyć na najdłuższe ujęcie klipu).
- `render.rozdziel_wycinki(materialy) -> tuple[list, list]` zwraca (zwykłe, wycinki): wycinki to zdjęcia z przezroczystością. Wycinki nie wchodzą do kolejki ujęć, tylko do kolaży (10.3). Gdy wszystkie materiały są wycinkami, wszystkie idą do kolejki jak dziś.
- `render.rozloz_tempo(plan, wzor, uderzenia, kawalki, fps) -> dict`, gdzie `uderzenia` to wynik `uderzenia_wyniku`:
  - twarde cięcia: 0, klatka dropu (`koniec_haka`, gdy wzór ma `sekcje`), początek ostatniego ujęcia wzoru (plansza) i koniec editu;
  - między twardymi cięciami ujęcia wypełnia się po kolei z `kawalki` (cyklicznie, jak dziś `k % len`, z wyjątkiem z zadania 10.9);
  - zdjęcie trwa do pierwszego uderzenia nie wcześniejszego niż `pozycja + 0.30 s`, a gdy go nie ma, do twardego cięcia;
  - klip kończy się na pierwszym cięciu wzoru w oknie `[pozycja + 2.0 s, pozycja + 3.2 s]`, a gdy go nie ma, na pierwszym uderzeniu w tym oknie, a gdy i go nie ma, po 2,0 s. Nigdy za twardym cięciem;
  - reszta krótsza niż 0,30 s przed twardym cięciem dokleja się do poprzedniego ujęcia;
  - odcinek planszy to jedno ujęcie, jak dziś;
  - każde ujęcie dostaje `numer_wzoru` ujęcia wzoru, w którym się zaczyna. Kolor na sekcję, koniec haka, napisy i nakładka działają bez zmian.
- `renderuj` woła `rozloz_tempo` zaraz po `plan_ujec`. CLI `--bez-dynamiki` wyłącza tempo, przejścia i kolaże (plan i polecenia jak przed tą częścią). Pomiar używa go jako punktu odniesienia.
- Podsumowanie dostaje `"dynamika": {"ujecia": 25, "mediana_zdjecia_s": 0.46, "mediana_klipu_s": 2.5, "wycinki": 10}`.

**Przejścia na cięciach (10.2):**
- `render.efekt_ujecia(ujecie, indeks, klatka_dropu, licznik_zdjec_montazu) -> dict` z kluczami `uderzenie` (bool), `blysk_s` (float), `wstrzas` (bool), `przejscie` (`"brak"`, `"smuga"` albo `"najazd"`):
  - każde ujęcie poza planszą: `uderzenie`;
  - początek klipu: `blysk_s` 0,10;
  - ujęcie zaczynające się na dropie: `blysk_s` 0,30 i `wstrzas`;
  - co trzecie zdjęcie po dropie: `przejscie` `"smuga"`;
  - plansza: tylko `przejscie` `"najazd"`.
- Wszystko w jedynym kodowaniu segmentu, w tej kolejności: skalowanie, zoom (Ken Burns razem z uderzeniem), `lut3d`, wstrząs, przejście, błysk. Filtry sprawdzone w prototypie na ffmpeg 8.1. Na ffmpeg 7.1 z serwera sprawdź je testem na 270x480:
  - uderzenie w zdjęciu: Ken Burns liczony wprost z numeru klatki zamiast rekurencyjnego `zoom+krok`, razy uderzenie, z kotwicą na środku kadru: `zoompan=z='(1+K*on)*(1+0.12*pow(max(0,1-on/5),2))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=...` (dla ujęć nieparzystych `ZOOM_MAKSYMALNY-K*on`);
  - uderzenie w klipie: po przycięciu `zoompan=z='1+0.12*pow(max(0,1-on/5),2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=WxH:fps=F`;
  - wstrząs: `scale=trunc(iw*1.08/2)*2:trunc(ih*1.08/2)*2,crop=W:H:x='(iw-ow)/2+((iw-ow)/2)*sin(n*2.1)*max(0,1-n/15)':y='(ih-oh)/2+((ih-oh)/2)*cos(n*1.7)*max(0,1-n/15)'`;
  - smuga: `gblur=sigma=1:sigmaV=60:enable='lt(n,4)'` (pionowe rozmycie przez 4 klatki, jak w `0923`);
  - najazd: uderzenie mocniejsze (0,35 zamiast 0,12, przez 6 klatek) i `gblur=sigma=18:enable='lt(n,3)'`;
  - błysk: `fade=t=in:st=0:d=<blysk_s>:color=white`.
- Wyjście segmentu ma te same parametry kodowania co dziś (`PARAMETRY_KODOWANIA_SEGMENTU`), bo segmenty łączy `concat -c copy`.
- Zmiana kotwicy Ken Burnsa z lewego górnego rogu na środek jest zamierzona.

**Kolaż wycinków (10.3):**
- Kolaż dostaje co drugi klip (licząc klipy od początku planu), gdy ujęcie trwa co najmniej 1,5 s, nie zaczyna się na dropie, nie jest planszą i nie nachodzi na okna słów w rytmie (`slowa.okna` z 9.6). Wymaga co najmniej jednego wycinka.
- W jednym kolażu są najwyżej 3 wycinki, brane po kolei z puli (cyklicznie, w kolejności `message_id`). Każdy wskakuje na kolejnym uderzeniu wewnątrz ujęcia, od pierwszego uderzenia po jego początku, i zostaje do końca ujęcia.
- Wycinek przycięty do ramki kanału alfa i dopasowany (contain) do pola 55% szerokości na 36% wysokości kadru. Środki pól po kolei: (30%, 30%), (70%, 47%), (38%, 66%).
- Wskok: skala w kolejnych klatkach od pojawienia to 0,45, 0,85, 1,12, 1,05, a potem 1,0.
- Warstwa kolażu to klip RGBA z `materializuj_warstwe` o długości ujęcia, nakładany na segment przez `overlay` w tym samym kodowaniu (drugie wejście polecenia segmentu) albo w jednym dodatkowym kodowaniu z tymi samymi parametrami.
- Wycinki nie dostają LUT (jak dziś zdjęcia z przezroczystością).
- Podsumowanie: `"kolaze": [{"ujecie": 3, "wycinki": ["m621.png", ...]}]`.

**Flaga w kadrze (10.4):**
- Tryb `krycie`: krótszy bok nakładki skalowany do szerokości kadru, środek przycięty do szerokości kadru, a górę i dół dopełnia jednolity kolor. To średni kolor górnych i dolnych 5% wierszy pierwszej klatki nakładki (`render.kolor_brzegu`). Filtr z prototypu: `scale='if(gt(iw,ih),-2,W)':'if(gt(iw,ih),W,-2)',crop='min(iw,W)':'min(ih,H)',pad=W:H:(ow-iw)/2:(oh-ih)/2:color=0xRRGGBB`. Nakładka pionowa (9:16) wychodzi tak samo jak dziś.
- Długość: tryb `krycie` trwa `DLUGOSC_NAKLADKI_KRYCIE_S` od dropu (domyślnie 2,5, w `.env` i `Konfiguracja`, a 0 oznacza do planszy jak dziś). Tryby `alfa`, `zielen` i `ekran` bez zmian (do planszy), bo pierścień na `0915` został zaakceptowany w tej postaci.
- Bot przekazuje `--dlugosc-nakladki-krycie` z konfiguracji.

## Zadania

### [Task 10.1: Tempo cięć]
- **Objective:** `rozdziel_wycinki`, `rozloz_tempo`, `DLUGOSC_WSTAWKI_S`, CLI `--bez-dynamiki`, podsumowanie `dynamika`.
- **Context/Inputs:** kontrakt „Tempo cięć”; `src/render.py` (`wstawki`, `plan_ujec`, `koniec_haka`, `uderzenia_wyniku`, `renderuj`, `glowna`), `tests/test_render.py`, `tests/generuj.py`. Nowy plik `tests/test_dynamika.py`.
- **Constraints:** testy w `tests/test_dynamika.py` na planach syntetycznych (bez ffmpeg, poza testem 7):
  1. uderzenia co 15 klatek (120 BPM przy 30 fps), same zdjęcia: każde ujęcie poza planszą i ostatnim przed twardym cięciem ma 15 klatek;
  2. same klipy: każde ujęcie klipu ma od 60 do 96 klatek, chyba że kończy się na twardym cięciu;
  3. wzór z `sekcje`: jedno ujęcie zaczyna się dokładnie na klatce dropu, a żadne go nie przecina;
  4. ostatnie ujęcie zaczyna się na początku ostatniego ujęcia wzoru i jest jedno;
  5. suma długości równa `liczba_klatek`, `numer_wzoru` niemalejące i zgodne z ujęciem wzoru, w którym ujęcie się zaczyna;
  6. `rozdziel_wycinki`: zdjęcie z przezroczystością idzie do wycinków, a gdy są same wycinki, wszystkie idą do kolejki;
  7. pełny render 270x480 z 4 zdjęciami i 1 klipem: długość bez zmian, więcej ujęć niż ujęć wzoru, `--bez-dynamiki` daje liczbę ujęć równą liczbie ujęć wzoru;
  8. istniejące testy renderu przechodzą. Tam, gdzie sprawdzają układ ujęć 1:1 ze wzorem, dodaj `--bez-dynamiki` (albo parametr funkcji), nie osłabiaj ich treści.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.1 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_render.py, tests/generuj.py, nowy tests/test_dynamika.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: tempo cięć`

### [Task 10.2: Przejścia na cięciach]
- **Objective:** `efekt_ujecia`, efekty w `segment_zdjecia`, `segment_klipu` i `segment_planszy`.
- **Context/Inputs:** kontrakt „Przejścia na cięciach”; `src/render.py` (`wyrazenie_zoom`, `segment_zdjecia`, `segment_klipu`, `segment_planszy`, pętla segmentów w `renderuj`), `tests/test_dynamika.py`, `tests/generuj.py`.
- **Constraints:** testy (270x480, obrazy testowe z wyraźnym wzorem, np. szachownica z generatora):
  1. uderzenie: w klatce 0 segmentu ze zdjęciem krawędź szachownicy w środkowym pasie leży dalej od środka niż w klatce 8 (zoom maleje), a w klatce 8 i 20 różnica jest mała (sam Ken Burns);
  2. błysk: średnia jasność klatki 0 segmentu klipu z `blysk_s` 0,10 ponad 200, a klatki 6 równa segmentowi bez błysku (±5);
  3. wstrząs: na nieruchomym zdjęciu przesunięcie treści między klatką 2 a 5 różne od zera, a po klatce 15 zero;
  4. smuga: klatka 1 ma mniejszą ostrość w pionie (suma różnic między wierszami) niż klatka 6;
  5. plansza z najazdem: klatka 0 bardziej rozmyta niż klatka 8;
  6. `efekt_ujecia` na planie z dropem: drop ma błysk 0,30 i wstrząs, klipy 0,10, co trzecie zdjęcie po dropie smugę, plansza najazd;
  7. `--bez-dynamiki`: polecenia segmentów bez tych filtrów.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.2 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_dynamika.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: przejścia na cięciach`

### [Task 10.3: Kolaż wycinków]
- **Objective:** wycinki wskakujące na klipach tła, w rytmie.
- **Context/Inputs:** kontrakt „Kolaż wycinków”; `src/render.py` (`materializuj_warstwe`, `rozdziel_wycinki`, pętla segmentów, `przygotuj_slowa`), `tests/test_dynamika.py`, `tests/generuj.py` (dopisz generator PNG z przezroczystością, jeśli go nie ma).
- **Constraints:** testy:
  1. kolaż na klipie 90 klatek z uderzeniami co 15: przed pierwszym uderzeniem w polu pierwszego wycinka jest tło, po 5 klatkach od uderzenia jest wycinek, a po trzech uderzeniach są trzy;
  2. rozmiar wycinka w klatce 2 od pojawienia jest większy niż w klatce 5 (wskok);
  3. kolaż tylko na co drugim klipie, nie na dropie, nie na planszy i nie w oknach słów;
  4. bez wycinków render bez kolaży i bez błędu;
  5. wycinek nigdy nie jest osobnym ujęciem, gdy są zwykłe materiały.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.3 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_dynamika.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: kolaż wycinków`

### [Task 10.4: Flaga w kadrze]
- **Objective:** `kolor_brzegu`, nowe skalowanie trybu `krycie`, `DLUGOSC_NAKLADKI_KRYCIE_S`.
- **Context/Inputs:** kontrakt „Flaga w kadrze”; `src/render.py` (`przebieg_koncowy`, `okno_nakladki`, `renderuj`, `glowna`), `src/konfiguracja.py`, `.env.example`, `src/bot.py` (`renderuj_w_tle`), `tests/test_nakladka.py`, `tests/test_konfiguracja.py`, `tests/test_bot.py`.
- **Constraints:** testy:
  1. nakładka 16:9 w `krycie` z czerwonymi znacznikami przy lewej i prawej krawędzi środkowego kwadratu: oba znaczniki widać w kadrze 9:16;
  2. pas nad i pod nakładką ma kolor brzegu nakładki (±10 w każdym kanale, przed kryciem);
  3. nakładka pionowa 9:16 wychodzi tak samo jak przed zmianą (piksel ±3);
  4. `krycie` znika po 2,5 s od dropu, a przy `DLUGOSC_NAKLADKI_KRYCIE_S=0` trwa do planszy; tryb `alfa` bez zmian;
  5. bot przekazuje `--dlugosc-nakladki-krycie`, a zła wartość w `.env` daje `ValueError`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.4 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, src/konfiguracja.py, .env.example, src/bot.py, tests/test_nakladka.py, tests/test_konfiguracja.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: flaga w kadrze i krócej`

### [Task 10.5: Pomiar]
- **Objective:** `Pomiary/measure_dynamika.py`, wynik w `outputs/pomiar_dynamika.json`, arkusze i próbny edit.
- **Context/Inputs:**
  - materiały: stała próbka z bloku WSPÓLNE oraz wszystkie wycinki z `dane/zdjęcia_bez_tła/`. Słowa „europe be like POLAND”, napis pionowy „1993 supply made in poland”, flaga z `dane/nakladki/domyslna.mp4`, plansza i znak wodny jak w pomiarach 9.8;
  - **Sekcja A** (5 wzorów z `dane/wzory/*.mp4`): liczba ujęć i użytych materiałów z dynamiką i z `--bez-dynamiki`, mediana długości ujęcia zdjęcia i klipu, liczba kolaży i wycinków;
  - **Sekcja B:** narzut czasu procesora z dynamiką wobec `--bez-dynamiki` na jednym wzorze (tylko raport);
  - **Sekcja C:** arkusze `outputs/porownanie_dynamika_<wzor>.png`, `outputs/dynamika_drop.png` (klatki od 10 przed do 20 po dropie `0923`, co 2 klatki: błysk, wstrząs, akcent, flaga) oraz próbny edit `outputs/dynamika_0923.mp4` dla właściciela;
  - `render.uruchom_ffmpeg` podmieniony na wersję z limitem 900 s, jak w `measure_rytm.py`.
- **Constraints:** progi:
  - A: na każdym wzorze mediana ujęcia zdjęcia od 0,3 do 0,7 s, mediana klipu od 2,0 do 3,2 s, ujęć więcej niż z `--bez-dynamiki`, a żaden wycinek nie stoi jako osobne ujęcie;
  - A i C: żaden render nie przekroczył limitu 900 s;
  - B: tylko raport;
  - C: pliki powstały, werdykt wydaje właściciel.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.5 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, Pomiary/arkusz.py, Pomiary/measure_rytm.py jako wzór układu. Weryfikacja: python Pomiary/measure_dynamika.py
```
- **Commit:** `Pomiary: pomiar dynamiki`

## Poprawki po odbiorze (2026-09-26, Opus)
Kod 10.1 do 10.4 jest zgodny z kontraktami, a testy przechodzą: 350 z 350. Pomiar 10.5 wykazał dwa błędy, które wymagają poprawki przed scaleniem, a arkusz dropu trzeci. Wszystkie trzy wynikają z planu, nie z wykonania. Poprawki idą na tej samej gałęzi `dynamika`, zadania 10.6 do 10.8.

Prompt startowy poprawek (jedna sesja):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 10.6 do 10.8 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md na istniejącej gałęzi `dynamika`, zaczynając od sekcji „Poprawki po odbiorze”. Na starcie przeczytaj Pomiary/ROZWOJ.md (problem 13 i wpis „odbiór 10.1 do 10.5”) i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
```

**Przeplot zdjęć i klipów (10.6):**
- Skąd: `wstawki` układa kolejkę rundami. W pierwszej rundzie jest każdy materiał raz, w następnych już tylko dalsze kawałki klipów. `rozloz_tempo` bierze z tej kolejki po kolei, więc zdjęcia po 0,3 do 0,5 s kończą się w pierwszych sekundach editu.
  - Na 5 wzorach pomiaru montaż po dropie składa się z samych klipów: 0% zdjęć i do 10 klipów pod rząd, razem 18 do 21 ujęć.
  - Wzór `0915` ma 31 cięć. Stąd niespełniony próg „więcej ujęć niż bez dynamiki”.
- Stała `ZDJEC_MIEDZY_KLIPAMI = 3`.
- `render.przeplot(kawalki, zdjec_miedzy_klipami=ZDJEC_MIEDZY_KLIPAMI) -> list[dict]`:
  - pierwszy element (hak z `uloz_wariant`) zostaje pierwszy, także gdy jest klipem, i się nie powtarza;
  - z reszty zdjęcia i kawałki klipów zachowują swoją kolejność z `kawalki`. Kawałki klipów idą więc rundami, na przemian z różnych klipów;
  - wynik: hak, a potem na każdy kawałek klipu seria `zdjec_miedzy_klipami` zdjęć i ten kawałek. Zdjęcia biorą się po kolei, a po ostatnim znowu od pierwszego zdjęcia reszty;
  - zdjęcie reszty, które po ostatnim kawałku klipu nie wystąpiło ani razu, dopisuje się na koniec;
  - gdy reszta nie ma zdjęć albo nie ma klipów, lista zostaje bez zmian;
  - elementy to te same słowniki co w `kawalki`, bez nowych kluczy.
- `renderuj` bez `--bez-dynamiki`: `kawalki = przeplot(wstawki(zwykle, DLUGOSC_WSTAWKI_S))`, reszta bez zmian. Z `--bez-dynamiki` bez zmian.
- Symulacja na samych planach (Opus, próbka z pomiaru 10.5, 5 wzorów):
  - 28 do 38 ujęć zamiast 18 do 21;
  - po dropie 72 do 79% zdjęć, nigdy dwa klipy pod rząd;
  - to samo zdjęcie 3 do 4 razy w editcie, mediany zdjęcia i klipu bez zmian;
  - przy 2 zdjęciach na klip 23 do 35 ujęć.

**Warstwy przebiegu końcowego jako klipy (10.7):**
- Skąd: problem 13 w `ROZWOJ.md` (przyczynę ustalono przy odbiorze). Przebieg końcowy wisi, a czas procesora stoi, gdy flaga `krycie` wchodzi jako wideo ucięte opcją `-t`, a `polaczone.mp4` ma określoną treść:
  - wystarczą 2 wejścia, `polaczone.mp4` z montażu `--bez-dynamiki` na `0923` i flaga z `-t 2.5`. Wisi za każdym razem, także bez dźwięku, napisów i znaku oraz bez `-stream_loop`;
  - to samo polecenie z `polaczone.mp4` z montażu z dynamiką przechodzi, a przy tej samej luce do końca editu. Teoria luki z 10.5 odpada;
  - flaga wstępnie zapisana do klipu 75 klatek, bez `-t`, przechodzi na obu. Pełny montaż z tą zmianą przechodzi na `0914`, `0921`, `0922` i `0923` (w pomiarze 10.5 wszystkie cztery wisiały);
  - skoro wynik zależy od treści, wzory, które dziś przechodzą, mogą zawisnąć na innych materiałach, także z dynamiką.
- Zasada (rozszerza problem 12): w przebiegu końcowym każde wejście poza `polaczone.mp4` i dźwiękiem to plik o dokładnie takiej liczbie klatek, jaką ma jego okno, bez `-t`, `-loop` i `-stream_loop`. Tak działają już napisy, słowa i napis pionowy.
- `render.materializuj_nakladke(nakladka, tryb, liczba_klatek, fps, szerokosc, wysokosc, katalog) -> Path` to osobny proces ffmpeg z jednym wejściem:
  - opcje wejścia: `-stream_loop -1`, a dla VP9 z alfą `-c:v libvpx-vp9` przed `-i`;
  - przygotowanie trybu jak dziś w `przebieg_koncowy`, potem `-frames:v liczba_klatek`;
  - `krycie` (skalowanie, przycięcie, dopełnienie kolorem brzegu) i `ekran` (skalowanie cover): wynik `libx264`, `yuv420p`, `-crf 12`, bez alfy, w `katalog/nakladka.mp4`. Krycie 0,5 i `blend` zostają w przebiegu końcowym;
  - `alfa` i `zielen` (z `colorkey`): wynik z alfą, `png` w `katalog/nakladka.mov`, jak w `materializuj_warstwe`.
- Znak wodny: skalowanie i krycie jak dziś, zapisane osobnym procesem ffmpeg z jednym wejściem (`-loop 1 -i znak`, `-frames:v` liczba klatek okna znaku) do `katalog/znak.mov` (`png`).
- `przebieg_koncowy` przed złożeniem polecenia sam materializuje nakładkę i znak do katalogu `polaczone_wideo`, więc wywołania się nie zmieniają. W poleceniu warstwy tylko przesuwa `setpts=PTS+od/TB`. Przed żadnym `-i` poza dźwiękiem nie ma `-t`, `-loop` ani `-stream_loop`.
- Flaga w kadrze, poprawka 10.4. W `krycie` dla nakładki szerszej niż wysoka krótszy bok skaluje się do `SKALA_NAKLADKI_KRYCIE = 0.85` szerokości kadru zamiast do pełnej. Nakładka pionowa bez zmian.
  - Na `domyslna.mp4` krąg gwiazd ma 58% szerokości źródła, czyli 104% jego wysokości. Przy pełnej skali skrajne gwiazdy wychodzą za lewą i prawą krawędź kadru (`outputs/dynamika_drop.png`).
  - Przy 0,85 mieszczą się z zapasem około 5% szerokości. Dolne gwiazdy ucina już samo źródło.

**Pomiar ponownie (10.8):** `measure_dynamika.py` bez pamięci wyników (każdy przebieg renderuje od nowa, bo czas nie ma znaczenia). Progi A:
- mediany jak w 10.5;
- ujęć nie mniej niż ujęć wzoru (liczba z `--bez-dynamiki`);
- po dropie, bez planszy, co najmniej 50% ujęć to zdjęcia i nigdy dwa klipy pod rząd;
- żaden wycinek jako osobne ujęcie;
- oba tryby na wszystkich 5 wzorach bez przekroczenia limitu.

### [Task 10.6: Przeplot zdjęć i klipów]
- **Objective:** `przeplot`, `ZDJEC_MIEDZY_KLIPAMI`, wpięcie w `renderuj`.
- **Context/Inputs:** kontrakt „Przeplot zdjęć i klipów”; `src/render.py` (`wstawki`, `rozloz_tempo`, `renderuj`), `tests/test_dynamika.py`, `tests/generuj.py`.
- **Constraints:** testy w `tests/test_dynamika.py`:
  1. 8 zdjęć (hak jest zdjęciem) i 2 klipy po 3 kawałki: pierwszy element to hak, a między każdymi dwoma kawałkami klipów są dokładnie 3 zdjęcia. Każdy kawałek i każde zdjęcie reszty występuje, a hak raz;
  2. hak jest klipem: zostaje pierwszy, a jego dalsze kawałki są w kolejce jak inne;
  3. same zdjęcia albo same klipy: lista bez zmian;
  4. 2 zdjęcia i 3 kawałki: zdjęcia powtarzają się po kolei;
  5. pełny render 270x480 z dynamiką na wzorze z dropem, 6 zdjęć i 2 klipy po 8 s. Po dropie, bez planszy, żadne dwa ujęcia klipów nie stoją obok siebie, a zdjęcia to co najmniej połowa ujęć;
  6. istniejące testy przechodzą, w tym test poleceń `--bez-dynamiki`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.6 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_dynamika.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: przeplot zdjęć i klipów`

### [Task 10.7: Warstwy przebiegu końcowego jako klipy]
- **Objective:** `materializuj_nakladke`, znak wodny jako klip, `przebieg_koncowy` bez `-t`, `-loop` i `-stream_loop` na warstwach, `SKALA_NAKLADKI_KRYCIE`.
- **Context/Inputs:** kontrakt „Warstwy przebiegu końcowego jako klipy”; problem 13 w `ROZWOJ.md`; `src/render.py` (`przebieg_koncowy`, `kolor_brzegu`, `strumien_wideo_nakladki`, `wymaga_dekodera_vp9_alfa`, `wymiary_i_pozycja_znaku`, `materializuj_warstwe`), `tests/test_nakladka.py`, `tests/generuj.py`.
- **Constraints:** testy w `tests/test_nakladka.py`:
  1. dla każdego trybu (`alfa` z PNG, `alfa` z VP9 z alfą, `zielen`, `ekran`, `krycie`) razem ze znakiem wodnym. Polecenie przebiegu końcowego (podmienione `render.uruchom_ffmpeg`, które zapisuje argumenty i woła oryginał) nie ma `-t`, `-loop` ani `-stream_loop` przed żadnym `-i` poza dźwiękiem. Klip nakładki i klip znaku mają tyle klatek, ile ich okna (`ffprobe -count_frames`);
  2. istniejące testy pikselowe nakładek, znaku i napisu nad nakładką przechodzą bez zmiany treści asercji;
  3. `krycie` z nakładką 16:9 ze znacznikami na 20% i 80% szerokości źródła: oba znaczniki widać w kadrze 9:16. Przy dzisiejszej pełnej skali oba wypadają poza kadr, więc test łapie brak `SKALA_NAKLADKI_KRYCIE`;
  4. testy 10.4 (znaczniki w środkowym kwadracie, kolor pasa, nakładka pionowa bez zmian, 2,5 s i 0) przechodzą.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.7 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_nakladka.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: warstwy przebiegu końcowego jako klipy`

### [Task 10.8: Pomiar ponownie]
- **Objective:** pomiar 10.5 bez pamięci wyników, z nowymi progami, nowe arkusze i próbny edit.
- **Context/Inputs:** kontrakt „Pomiar ponownie”; `Pomiary/measure_dynamika.py`. Materiały i sekcje jak w 10.5, a dodatkowo:
  - w sekcji A na każdy wzór udział zdjęć po dropie i najdłuższa seria klipów;
  - w sekcji B czas procesora z dynamiką i bez niej na pierwszym wzorze, z obu świeżych przebiegów.
- **Constraints:** progi z kontraktu „Pomiar ponownie”. B tylko raport. C: pliki powstały, werdykt wydaje właściciel.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.8 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz Pomiary/measure_dynamika.py, src/render.py. Weryfikacja: python Pomiary/measure_dynamika.py
```
- **Commit:** `Pomiary: pomiar dynamiki po poprawkach`

## Poprawki po ocenie 10.6 do 10.8 (2026-09-27)
Kod 10.6 i 10.7 jest zgodny z kontraktami, a testy przechodzą: 357 z 357 (sprawdzone ponownie na ffmpeg 6.1.1). Ocena wykazała problemy, z których część poprawiają zadania 10.9 do 10.11 na gałęzi `dynamika`, przed pomiarem 10.8 u właściciela. Reszta czeka na decyzję właściciela.
- **Kolejka po zawinięciu (luka planu, nie wykonania).** `rozloz_tempo` bierze `kawalki` w kółko od haka. Gdy hak i ostatni element kolejki są kawałkami klipów, po zawinięciu stoją dwa klipy pod rząd. Symulacja na samych planach (wzór 28 s, 18 ujęć, drop na ujęciu 6, plansza 1 s, 164 BPM):
  - hak zdjęcie, 8 zdjęć i 4 klipy po 12 s (jak próbka pomiaru): 78% zdjęć po dropie, najdłuższa seria klipów 1;
  - hak klip 7 s, 3 zdjęcia i drugi klip 7 s (kolejka 13 elementów): seria 2;
  - hak klip 10 s i 5 zdjęć (kolejka 9 elementów): seria 2, raz ten sam klip dwa razy pod rząd.
  Próbka pomiaru ma hak zdjęcie, więc pomiar tego nie złapie. Zadanie 10.9.
- `przeplot`: dopisywanie nieużytych zdjęć na koniec nie ma testu. Po usunięciu tej gałęzi kodu 5 z 5 testów przeplotu dalej przechodzi. Zadanie 10.9.
- **Pomiar B zaniża koszt dynamiki.** Kolaże, słowa i napis pionowy zapisuje `materializuj_warstwe` własnym `Popen`, więc jej ffmpeg nie wchodzi do sumy `-benchmark` ani pod limit 900 s. Czasu procesora Pythona (klatki PIL) pomiar nie liczy, choć blok WSPÓLNE każe `time.process_time()`. Zadanie 10.10.
- **Pomiar A** nie wymaga udanego renderu wszystkich wzorów: błąd inny niż przekroczenie limitu po cichu usuwa wzór z progów. Wyniki zapisuje dopiero po wszystkich 10 renderach, a reguła 1 każe po każdej sekcji. Zadanie 10.10.
- **Koszt nakładki `alfa` po 10.7 jest niezmierzony.** Nakładka `alfa` idzie teraz do klipu PNG 1080x1920. Na syntetycznym pierścieniu 600 klatek to 11 MB i około 30 s procesora (maszyna obciążona testami). Pomiar bierze tylko flagę (`krycie`). Zadanie 10.10.
- Reguły repo: komentarze w `tests/test_nakladka.py` (reguła 2) i nazwy z `_` w `Pomiary/measure_dynamika.py` (reguła 3). Zadania 10.10 i 10.11.
- Test skali z 10.7 używa nakładki 2:1 ze znacznikami na 21,5% i 75,5% szerokości zamiast 16:9 z 20% i 80%, a odstępstwo nie jest zapisane. Geometria z planu działa: przy skali 0,85 test przechodzi, przy 1,0 pada. Zadanie 10.11.
- Dziennik po 10.6 do 10.8: nieaktualne „Stan”, problem 13 („naprawiony” bez odtworzenia błędu) i „Następne kroki”. Poprawione razem z tym planem.
- **Do decyzji właściciela:**
  - PR #21 scalił 10.1 do 10.5 do `main` 2026-09-26 o 22:38 UTC, zanim powstały commity 10.6 do 10.8. `main` ma więc problem 13, flagę poza kadrem i same klipy po dropie. Poprawki wejdą nowym PR po pomiarze i odbiorze. Jeśli `main` jest już na serwerze, problem 13 grozi tam zawieszeniem renderu z flagą `krycie`;
  - commity 10.6 do 10.8 mają autora „Claude” i stopkę Co-Authored-By (reguła 5). Przepisanie wymaga force-push na `dynamika`;
  - pomiar 10.8 nie był uruchomiony na prawdziwym `dane/` (sesja w chmurze bez biblioteki), więc naprawa problemu 13 jest w kodzie, ale nie jest potwierdzona.

Prompt startowy poprawek (jedna sesja):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 10.9 do 10.11 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md na istniejącej gałęzi `dynamika`, zaczynając od sekcji „Poprawki po ocenie 10.6 do 10.8”. Na starcie przeczytaj Pomiary/ROZWOJ.md (wpis „ocena 10.6 do 10.8”) i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
```

**Kolejka bez dwóch klipów pod rząd (10.9):**
- `rozloz_tempo` bierze elementy `kawalki` po kolei i w kółko jak dotąd, z jednym wyjątkiem. Gdy hak (`kawalki[0]`) i ostatni element kolejki są kawałkami klipów, po wyczerpaniu kolejki wraca do drugiego elementu, a nie do haka. Hak jest wtedy w editcie raz, a po ostatnim klipie kolejki wchodzi pierwsze zdjęcie przeplotu.
- Gdy hak albo ostatni element jest zdjęciem, zawinięcie bez zmian: przy małej liczbie materiałów zdjęcia dalej się przeplatają.
- `--bez-dynamiki` bez zmian, bo nie woła `rozloz_tempo`.

**Pełny czas procesora i komplet wzorów w pomiarze (10.10):**
- B: czas procesora renderu to suma trzech części, podawanych osobno i razem dla obu trybów:
  - `-benchmark` procesów ffmpeg z `render.uruchom_ffmpeg` (jak dziś);
  - `-benchmark` procesów ffmpeg z `render.materializuj_warstwe`, podmienionej w pomiarze na wersję z tymi samymi argumentami, `-benchmark`, logiem ffmpeg w pliku tymczasowym (nie w potoku, który może się zapełnić) i limitem 900 s;
  - `time.process_time()` procesu Pythona na czas `render.renderuj`.
- Narzut liczy się z sumy. Indeks muzyki (`music.indeksuj`) powstaje raz przed sekcją A, żeby analiza nowych utworów nie weszła do pierwszego renderu. Poza sumą zostają krótkie wywołania ffprobe i próbkowanie koloru (`subprocess.run` w `render.py`), obecne w obu trybach.
- B, dodatkowo (tylko raport): koszt `render.materializuj_nakladke` dla każdej nakładki z `dane/nakladki/` i dla syntetycznego pierścienia z `generuj.pierscien_testowy` (1080x1080). Okno każdej nakładki to `okno_nakladki` jej trybu na planie pierwszego wzoru. W wyniku tryb, okno, liczba klatek, czas procesora i rozmiar pliku.
- A: nowy próg `wszystkie_wzory_w_obu_trybach`: każdy wzór z `dane/wzory/*.mp4` wyrenderowany z dynamiką i bez niej, bez błędu. W wyniku `liczba_wzorow`.
- A, B i C zapisywane do `outputs/pomiar_dynamika.json` po każdym wzorze (z `"w_toku": true`), a na końcu ostatecznie.
- Nazwy w skrypcie bez `_` na początku.

### [Task 10.9: Kolejka bez dwóch klipów pod rząd]
- **Objective:** wyjątek zawinięcia w `rozloz_tempo` i test dopisywania nieużytych zdjęć w `przeplot`.
- **Context/Inputs:** kontrakt „Kolejka bez dwóch klipów pod rząd”; `src/render.py` (`rozloz_tempo`, `przeplot`, `wstawki`), `tests/test_dynamika.py`.
- **Constraints:** testy w `tests/test_dynamika.py` na planach syntetycznych, bez ffmpeg:
  1. hak klip 7 s, 3 zdjęcia i drugi klip 7 s, kolejka z `przeplot(wstawki(...))`, wzór 28 s z dropem, uderzenia co 11 klatek: w całym planie poza planszą żadne dwa klipy nie stoją obok siebie, a kawałek haka (materiał i `start_w_klipie_s`) występuje raz. Bez poprawki test pada;
  2. hak zdjęcie i dwa zdjęcia: po wyczerpaniu kolejki wraca hak (materiały po kolei z0, z1, z2, z0);
  3. `przeplot` z hakiem, 7 zdjęciami reszty i jednym kawałkiem klipu: hak, 3 zdjęcia, klip, a potem 4 nieużyte zdjęcia w kolejności;
  4. istniejące testy przechodzą.
- **Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.9 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz src/render.py, tests/test_dynamika.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render: kolejka bez dwóch klipów pod rząd`

### [Task 10.10: Pełny czas procesora i komplet wzorów w pomiarze]
- **Objective:** zmiany z kontraktu „Pełny czas procesora i komplet wzorów w pomiarze” w `Pomiary/measure_dynamika.py`.
- **Context/Inputs:** kontrakt; `Pomiary/measure_dynamika.py`, `src/render.py` (`materializuj_warstwe`, `materializuj_nakladke`, `okno_nakladki`, `tryb_nakladki`), `src/music.py` (`indeksuj`), `tests/generuj.py` (`pierscien_testowy`).
- **Constraints:**
  - weryfikacja na syntetycznym `dane/` w kopii repo poza repo (wzory i utwory z generatora, zdjęcia, klipy, wycinki, flaga 16:9, plansza, znak): skrypt kończy się kodem 0. A ma wpis dla każdego wzoru (liczby ujęć w obu trybach, udział zdjęć po dropie, najdłuższa seria klipów), B trzy części czasu dla obu trybów i koszt nakładek, C arkusze, a plik wyników istnieje już po pierwszym wzorze;
  - u właściciela `python Pomiary/measure_dynamika.py` na prawdziwym `dane/`: progi z kontraktu „Pomiar ponownie” i nowy próg `wszystkie_wzory_w_obu_trybach`.
- **Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.10 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz Pomiary/measure_dynamika.py, src/render.py, src/music.py, tests/generuj.py. Weryfikacja: python Pomiary/measure_dynamika.py
```
- **Commit:** `Pomiary: pełny czas procesora i komplet wzorów`

### [Task 10.11: Test skali jak w planie i testy bez komentarzy]
- **Objective:** test skali z 10.7 na geometrii z planu i `tests/test_nakladka.py` bez komentarzy.
- **Context/Inputs:** `tests/test_nakladka.py` (`test_nakladka_krycie_skala_miesci_znaczniki_blisko_krawedzi_zrodla`, `test_warstwy_przebiegu_koncowego_jako_klipy_bez_t_loop_stream_loop`).
- **Constraints:**
  1. test skali na nakładce 16:9 (640x360) ze znacznikami od 20% i 80% szerokości źródła: przechodzi przy `SKALA_NAKLADKI_KRYCIE = 0.85`, a pada przy 1,0;
  2. w pliku nie ma komentarzy, a treść asercji się nie zmienia;
  3. `python -m pytest -q` przechodzi.
- **Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź dynamika. Wykonaj zadanie 10.11 z Pomiary/PLAN_EDITY_10_DYNAMIKA.md; otwórz tests/test_nakladka.py, src/render.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `testy: skala flagi jak w planie i bez komentarzy`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A w progach (także `wszystkie_wzory_w_obu_trybach` z 10.10), B zaraportowane, arkusze i próbny edit ocenione przez właściciela.
- Zadania 10.6 do 10.11 w `main` nowym PR, bo PR #21 wniósł tylko 10.1 do 10.5.
- Po wdrożeniu edit z Telegrama na wzorze `0923` ma szybkie zdjęcia, przejścia, kolaż i flagę w kadrze. Każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `render: tempo cięć`
2. `render: przejścia na cięciach`
3. `render: kolaż wycinków`
4. `render: flaga w kadrze i krócej`
5. `Pomiary: pomiar dynamiki`
6. `render: przeplot zdjęć i klipów`
7. `render: warstwy przebiegu końcowego jako klipy`
8. `Pomiary: pomiar dynamiki po poprawkach`
9. `render: kolejka bez dwóch klipów pod rząd`
10. `Pomiary: pełny czas procesora i komplet wzorów`
11. `testy: skala flagi jak w planie i bez komentarzy`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 10 według Pomiary/PLAN_EDITY_10_DYNAMIKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..dynamika`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_dynamika.py`: progi A, czasy B.
3. `outputs/dynamika_drop.png` i próbny edit: błysk i wstrząs na dropie, akcent wlatuje, flaga cała w kadrze i znika po 2,5 s.
4. Arkusze `outputs/porownanie_dynamika_*.png`: zdjęcia zmieniają się co uderzenie, klipy trwają dłużej, kolaże nie zasłaniają słów, plansza bez kolażu i znaku.
5. `src/render.py`: kolejność filtrów w segmencie, parametry kodowania segmentów bez zmian, warstwy bez `-loop 1 -t`, `--bez-dynamiki` odtwarza stary plan.
6. Po poprawkach 10.6 do 10.8: w przebiegu końcowym przed żadnym `-i` poza dźwiękiem nie ma `-t`, `-loop` ani `-stream_loop`. Na arkuszach zdjęcia są także po dropie, między klipami. Na arkuszu dropu flaga ma wszystkie boczne gwiazdy w kadrze.
7. Po poprawkach 10.9 do 10.11: testy kolejki z hakiem klipem, test skali na geometrii z planu, `tests/` bez komentarzy. W `outputs/pomiar_dynamika.json` B ma trzy części czasu dla obu trybów i koszt nakładek, A próg `wszystkie_wzory_w_obu_trybach`.
