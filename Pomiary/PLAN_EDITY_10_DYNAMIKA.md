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
  - między twardymi cięciami ujęcia wypełnia się po kolei z `kawalki` (cyklicznie, jak dziś `k % len`);
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

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A w progach, B zaraportowane, arkusze i próbny edit ocenione przez właściciela.
- Po wdrożeniu edit z Telegrama na wzorze `0923` ma szybkie zdjęcia, przejścia, kolaż i flagę w kadrze. Każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `render: tempo cięć`
2. `render: przejścia na cięciach`
3. `render: kolaż wycinków`
4. `render: flaga w kadrze i krócej`
5. `Pomiary: pomiar dynamiki`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 10 według Pomiary/PLAN_EDITY_10_DYNAMIKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..dynamika`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_dynamika.py`: progi A, czasy B.
3. `outputs/dynamika_drop.png` i próbny edit: błysk i wstrząs na dropie, akcent wlatuje, flaga cała w kadrze i znika po 2,5 s.
4. Arkusze `outputs/porownanie_dynamika_*.png`: zdjęcia zmieniają się co uderzenie, klipy trwają dłużej, kolaże nie zasłaniają słów, plansza bez kolażu i znaku.
5. `src/render.py`: kolejność filtrów w segmencie, parametry kodowania segmentów bez zmian, warstwy bez `-loop 1 -t`, `--bez-dynamiki` odtwarza stary plan.
