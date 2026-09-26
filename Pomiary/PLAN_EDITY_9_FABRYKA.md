# Część 9: fabryka (restart, biblioteka wzorów, warianty, partie, nakładka z kryciem, napisy w rytmie)

**Zależy od:** części 4 i 8 (wymagane). Najlepiej wykonać ją po częściach 5 i 6: wtedy parametry renderu i podpisy są kompletne. Jeśli którejś brakuje, pomijasz jej parametry (`--sila-koloru`, `--styl-tekstu`, `--pozycja-tekstu`).
**Zadania 9.5 do 9.8 (dopisane 2026-09-24):**
- 9.5 (nakładka z kryciem) wymaga tylko części 8. Można ją zrobić zaraz po scaleniu części 8, na własnej gałęzi `krycie`, przed częściami 5 i 6;
- 9.6 i 9.7 (napisy w rytmie) wymagają części 6, czyli modułu `tekst`, `tekst.oczysc`, `tekst.PRESETY` i czcionek w `zasoby/`.
- Kolejność od 2026-09-25: po scaleniu części 6 idą najpierw 9.6 do 9.8 na własnej gałęzi `rytm` od `main`, z osobnym PR-em (prompt niżej). Potem 9.1 do 9.4 na gałęzi `fabryka`.

Prompt startowy dla 9.6 do 9.8:
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 9.6, 9.7 i 9.8 z Pomiary/PLAN_EDITY_9_FABRYKA.md na gałęzi `rytm` od aktualnego `main` (przed startem `git pull`), zaczynając od „Stan wejściowy”. Zadania 9.1 do 9.5 pomiń. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
```

**Gałąź:** `fabryka` od `main` po scaleniu poprzednich części.
**Efekt:**
- bot przeżywa restart: zlecone montaże i analizy wracają do kolejki;
- wzorów jest wiele, a aktywny wybierasz z listy, z nazwami, zamiast zawsze brać najnowszy;
- jeden projekt daje kilka wariantów albo po jednym editcie na każdy wzór;
- `/ponow` montuje ostatni projekt jeszcze raz, bez ponownego wysyłania materiałów;
- nakładka bez przezroczystości i bez czarnego tła (flaga UE) idzie z kryciem 50%, jak we wzorach `0914` i `0923`;
- napisy jak we wzorze `0923`: pojedyncze słowa na kolejnych uderzeniach, ostatnie wlatuje na dropie, oraz pionowy napis pisany literami przy lewej krawędzi.

**Dlaczego:** to elementy, które zamieniają montaż pojedynczego editu w fabrykę (przegląd 2026-09-23). Dziś kolejka i stan zbierania żyją tylko w pamięci, więc restart w trakcie montażu zostawia projekt w stanie `renderowanie` bez żadnego komunikatu. Bot zna tylko najnowszy wzór, a każdy nowy edit wymaga ponownego wysłania materiałów.
**Nowe pliki:** `tests/test_fabryka.py`, `Pomiary/measure_fabryka.py`, `tests/test_rytm.py`, `Pomiary/measure_rytm.py`.
**Zmieniane:** `src/bot.py`, `src/komunikaty.py`, `src/magazyn.py`, `src/render.py`, `tests/test_bot.py`, `tests/test_magazyn.py`, `tests/test_render.py`, `tests/pomocnicze.py`.
**Od właściciela:** test ręczny z restartem kontenera w trakcie montażu. Do 9.5 klip flagi (`dane/nagrania/European Union Flag ｜EU Flag Motion Background｜ FREE 4K ANIMATION.mp4`) jako `/nakladka` albo w `dane/nakladki/domyslna.mp4`. Do 9.6 akceptacja czcionki pisanej na arkuszu.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_9_FABRYKA.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commity `bot: muzyka z biblioteki` (część 4) i `bot: nakładka i plansza wzoru` (część 8), a `python -m pytest -q` przechodzi. Zanotuj w `ROZWOJ.md`, czy są już części 5 i 6 oraz commit `render: nakładka z kryciem` (zadanie 9.5 zrobione wcześniej na gałęzi `krycie`, wtedy je pomiń). Bez części 6 wykonaj 9.1 do 9.5, a 9.6 do 9.8 odłóż. Utwórz gałąź `fabryka` od `main`. Inaczej zatrzymaj się i zapytaj.
Stan na 2026-09-25: `main` ma części 4, 8, 5 (z 5.5 i 5.6) i zadanie 9.5, a część 6 jest po odbiorze na gałęzi `tekst` i po scaleniu będzie w `main` (commit `tekst: poprawki po odbiorze`). Zadania 9.6 do 9.8 idą na gałęzi `rytm`, a nie `fabryka` (patrz nagłówek). Jeśli `main` nie ma commita `tekst: poprawki po odbiorze`, zatrzymaj się i zapytaj.

## Kontrakt z wcześniejszych części
Numery linii z `57ba8fe`, więc szukaj po nazwach.
- `src/kolejka.py`: `Kolejka` (64) trzyma zadania w `asyncio.Queue` w pamięci; `dodaj(zadanie) -> pozycja`; `uruchom(argumenty, limit_s, katalog) -> Wynik` (21).
- `src/bot.py`:
  - pamięć i uruchamianie:
    - `MemoryStorage` dla stanów rozmowy;
    - `projekt_aktywny` i `pobrania_w_toku` w słowniku dyspozytora (`utworz_dispatcher`, 488);
    - filtr właściciela na `message` i `edited_message` (490 i 491);
    - `uruchom_bota` (508);
  - montaż:
    - `renderuj_w_tle(message, katalog_projektu, wzor_json, ..., zapowiedz)` (153) odpowiada przez `message.answer` i `message.answer_document`;
    - `obsluz_cmd_gotowe` (211) bierze `magazyn.najnowszy_wzor` i dodaje jedno zadanie;
  - analiza: `analizuj_wzor_w_tle(message, zrodlo, wzor_json, zapowiedz)` (332) i `obsluz_wzor_plik` (355);
  - części 4 i 8 dokładają do CLI renderu `--muzyka`, `--nakladka` i `--plansza`, a do komend `/nakladka` i `/plansza`.
- `src/magazyn.py`:
  - `nowy_projekt` (25): `projekt.json` ze `stan` równym `zbieranie`, potem `w_kolejce`, `renderowanie`, `gotowy`, `blad` albo `anulowany`;
  - `nowy_wzor` (44), `najnowszy_wzor` (53), `wczytaj_projekt` i `zapisz_projekt` (104 i 110, zapis atomowy);
  - `plik_zasobu` (część 8).
- `src/render.py`:
  - `renderuj` tworzy `praca/` przez `mkdir(exist_ok=True)`, więc pozostałości przerwanego przebiegu zostają;
  - `wstawki` (140) układa kawałki rundami w kolejności materiałów.
- `tests/pomocnicze.py`: `SesjaTestowa` (95) obsługuje `SendMessage`, `SendDocument` i `GetFile`; `zbuduj_wiadomosc` (38), `zbuduj_update` (49).
- Część 6 (napisy w haku, stan z gałęzi `tekst`):
  - `src/tekst.py`: `PRESETY` (`szeryf`, `blok`), `POZYCJE`, `STREFA_BEZPIECZNA`, `znaki_czcionki`, `oczysc`, `wybierz_czcionke`, `obraz_tekstu(tekst, szerokosc, wysokosc, styl, dolna_granica=None)`, `okna_tekstow(liczba_linii, plan, koniec_haka_klatka)`;
  - `src/render.py`: `koniec_haka(plan, sekcje)`, `wczytaj_linie_tekstu`, `materializuj_tekst` (obraz do pliku `webm` VP9 z alfą, z dokładną liczbą klatek okna), `przygotuj_teksty(...)` zwraca listę `{plik, od_s, do_s}` i podsumowanie `teksty`;
  - `przebieg_koncowy(..., teksty=)`: napisy po nakładce, a przed znakiem wodnym, każdy jako wejście `-c:v libvpx-vp9 -i`, z przenikaniem 4 klatek;
  - konfiguracja `STYL_TEKSTU` i `POZYCJA_TEKSTU`, CLI `--styl-tekstu` i `--pozycja-tekstu`.

## Kontrakty ustalane w tej części

**Wznowienie po restarcie (9.1):**
- `bot.wznow_po_starcie(bot, konf, kolejka)`, wołane w `uruchom_bota` przed pollingiem:
  - projekty w stanie `w_kolejce` albo `renderowanie` (po `id`) dostają stan `w_kolejce` i trafiają do kolejki z tymi samymi parametrami. Wariant i wzór zapisane są w `projekt.json`, patrz 9.3. Właściciel dostaje wiadomość „Wznawiam montaż projektu <id> po restarcie.” na czat o id `konf.wlasciciel_id`;
  - katalogi w `dane/wzory/` z `zrodlo.*`, bez `wzor.json` i bez `blad.txt` wracają do analizy z wiadomością „Wznawiam analizę wzoru <id> po restarcie.”.
- Nieudana analiza zapisuje w katalogu wzoru `blad.txt` z pierwszą linią błędu, żeby wzór nie wracał w kółko. Plik czyta tylko bot, render dalej czyta z katalogu wzoru wyłącznie `wzor.json`.
- `renderuj_w_tle(bot, chat_id, ...)` i `analizuj_wzor_w_tle(bot, chat_id, ...)` wysyłają przez `bot.send_message` i `bot.send_document`, a nie przez `message.answer`. Poza tym zachowanie bez zmian: istniejące testy dostosuj, nie osłabiaj.
- `render.renderuj` usuwa `praca/` na starcie, jeśli istnieje, bo to pozostałość przerwanego przebiegu.

**Biblioteka wzorów (9.2):**
- `dane/ustawienia.json`: `{"aktywny_wzor": "<id>" | null}`, zapis atomowy.
- `magazyn.aktywny_wzor(katalog_danych) -> Path | None` zwraca `wzor.json` aktywnego wzoru, jeśli istnieje, inaczej `najnowszy_wzor`. `magazyn.ustaw_aktywny_wzor(katalog_danych, wzor_id | None)`.
- Nowo przeanalizowany wzór staje się aktywny, bo dziś też używany jest najnowszy.
- Nazwa wzoru to podpis wiadomości z wideo wzoru (pierwsze 60 znaków), zapisany jako `dane/wzory/<id>/nazwa.txt`. Bez podpisu nazwą jest `id`. `magazyn.nazwa_wzoru(katalog_wzoru) -> str`.
- `/wzory` pokazuje do 20 najnowszych wzorów z `wzor.json`:
  - każdy wiersz: nazwa, data z `id`, długość, tempo, drop, a aktywny oznaczony;
  - pod listą przyciski inline „Wybierz <nazwa>” i „Usuń <nazwa>”;
  - „Usuń” pyta jeszcze raz przyciskiem „Tak, usuń <nazwa>”. Dopiero on usuwa `dane/wzory/<id>/` razem z nakładkami i planszami tego wzoru, a gdy usunięty był aktywny, aktywny wraca do `najnowszy_wzor`.
- Filtr właściciela obejmuje też `callback_query`: przycisk naciśnięty przez obcego nie robi nic.
- `/gotowe`, `/status`, `/nakladka` i `/plansza` używają aktywnego wzoru zamiast najnowszego.

**Warianty i partie (9.3):**
- `render.uloz_wariant(materialy, wariant) -> list`, czysta funkcja:
  - dla 0 zwraca kolejność bez zmian;
  - dla `wariant >= 1` pierwszy materiał zostaje pierwszy (hak), a reszta jest tasowana przez `random.Random(wariant)`;
  - wywoływana przed `wstawki`.
- CLI renderu dostaje `--wariant` (domyślnie 0), a podsumowanie pole `"wariant"`.
- `/gotowe` bez argumentu działa jak dziś: aktywny wzór, wariant 0, wynik `wynik.mp4`.
- `/gotowe N`, gdzie N od 2 do 5, zleca N wariantów aktywnego wzoru (od 0 do N−1), każdy jako osobne zadanie w kolejce. Wyniki to `wynik_<wzor_id>_<wariant>.mp4`.
- `/gotowe wszystkie` zleca po jednym wariancie 0 na każdy wzór z `wzor.json`, najwyżej 10 najnowszych.
- Każdy wynik idzie jako dokument, a podpis zaczyna się od „Wzór <nazwa>, wariant <i>.”.
- `projekt.json` dostaje `"zadania": [{"wzor_id": "...", "wariant": 0, "stan": "w_kolejce" | "gotowy" | "blad", "wynik": null, "blad": null}]`. Wznowienie z 9.1 ponawia tylko niedokończone zadania.
- Stan projektu:
  - `gotowy`, gdy wszystkie zadania się skończyły i co najmniej jedno się udało;
  - `blad`, gdy wszystkie zawiodły;
  - w trakcie `renderowanie`.
- `/ponow [N | wszystkie]` robi to samo na ostatnim projekcie (najnowszy katalog w `dane/projekty/` w stanie `gotowy` albo `blad`), bez zbierania materiałów. Bez takiego projektu bot odpowiada komunikatem. Po zmianie nakładki, muzyki albo wzoru nie trzeba wysyłać materiałów jeszcze raz.
- Nieprawidłowy argument (np. `/gotowe 9`) daje komunikat z opisem użycia i nic nie trafia do kolejki.
- Zbieranie dalej obsługuje jeden projekt naraz (`projekt_aktywny`).

**Nakładka z kryciem (9.5):**
- Po co: nakładka we wzorach `0914` i `0923` to flaga UE (granatowe tło, żółte gwiazdy) położona z kryciem około 50%.
  - Porównanie na klatce `0914` (2026-09-24): krycie 50% daje głęboki granat i półprzezroczyste gwiazdy jak we wzorze;
  - `ekran` rozjaśnia cały kadr, bo tło flagi nie jest czarne. A `tryb_nakladki` z części 8 dałby flagę właśnie jako `ekran`.
- `render.tryb_nakladki`: po `alfa` i `zielen` tryb `ekran` tylko wtedy, gdy w pierwszej klatce co najmniej 40% pikseli jest prawie czarnych (największy kanał poniżej 40). W pozostałych przypadkach nowy tryb `"krycie"`.
- Kompozycja `krycie`: nakładka po skalowaniu cover i `fps` przechodzi przez `format=rgba,colorchannelmixer=aa=0.5`, potem `overlay` w oknie jak `alfa`. Stała `KRYCIE_NAKLADKI = 0.5`.
- Bot odpowiada „Nakładka zapisana: półprzezroczysta (krycie 50%).”.
- **Skalowanie nakładki (dopisane 2026-09-24):**
  - na serwerze leży nakładka właściciela: pierścień 12 gwiazd UE, PNG 600x600 z przezroczystością;
  - część 8 skaluje każdą nakładkę do wypełnienia kadru (cover), więc z pierścienia zostaje 6 wielkich gwiazd u góry i u dołu, a boki są ucięte (symulacja 2026-09-24). We wzorze `0921` pierścień jest cały, na środku kadru;
  - od teraz nakładka w trybie `alfa` skaluje się tak, żeby zmieścić się w całości (contain), i stoi na środku kadru;
  - tryby `krycie`, `ekran` i `zielen` dalej wypełniają kadr (cover), bo ich tło ma przykryć cały obraz.

**Napisy w rytmie, wspólne (9.6 i 9.7):**
- Kolory jak w `0923`: wypełnienie złote (233, 196, 106), obrys granatowy (24, 33, 74) grubości 0,5% wysokości kadru, cień czarny z kryciem 40% przesunięty o 0,4% wysokości.
- Treść pochodzi z wiadomości właściciela, nigdy ze wzoru (reguła 7).
- `render.uderzenia_wyniku(uderzenia_utworu, start_audio_s, liczba_klatek, fps) -> list[int]` zwraca klatki uderzeń w wyniku:
  - `round((u - start_audio_s) * fps)`, tylko z `[0, liczba_klatek)`, bez powtórzeń;
  - w trybie `dzwiek_wzoru` biorą się uderzenia wzoru minus pierwsze cięcie;
  - bez uderzeń (`bez_rytmu`) siatka co `round(fps / 2)` klatek.
- Każda warstwa to jeden klip RGBA na cały kadr (`praca/slowa.mov`, `praca/pionowo.mov`, kodek `png`). Klatki rysuje PIL i podaje przez stdin ffmpeg. W przebiegu końcowym warstwa to jedno wejście z `setpts` na swój początek i `overlay`.
- Klip warstwy ma dokładnie tyle klatek, ile trwa jej okno. Nigdy nie podawaj obrazu przez `-loop 1 -t`: takie wejście, które kończy się dużo przed końcem wyniku (tu na dropie), zawiesza przebieg końcowy na prawdziwym materiale bez błędu (znany problem 12 w `ROZWOJ.md`; napisy z części 6 przeszły z tego powodu na pliki `webm`). Testy na materiale syntetycznym tego nie łapią, łapie to dopiero pomiar 9.8.
- Kolejność warstw: materiał, nakładka, napisy linii (część 6), słowa w rytmie, napis pionowy, znak wodny (8.6).
- Bez słów i bez napisu pionowego polecenie przebiegu końcowego się nie zmienia.
- Warianty (9.3) i `/ponow` biorą te same napisy.

**Słowa w rytmie (9.6):**
- Bot:
  - `/slowa <tekst>` w trakcie zbierania zapisuje `projekt.json["slowa"]` po `tekst.oczysc`;
  - `/slowa` bez tekstu czyści pole;
  - odpowiedź: „Słowa w rytmie: N, ostatnie wchodzi na dropie.”;
  - najwyżej 12 słów. Więcej daje komunikat z limitem i nic się nie zapisuje.
- Preset `rytm` w `tekst.PRESETY`:
  - czcionka Pacifico (`ofl/pacifico`), a gdy brakuje polskiego znaku, Kaushan Script (`ofl/kaushanscript`), obie z `OFL.txt`;
  - kolory wspólne; wysokość wersalika około 5% wysokości kadru;
  - słowo szersze niż strefa bezpieczna zmniejsza się;
  - środek słowa na środku strefy w poziomie i na 50% wysokości.
- `tekst.okna_slow(liczba_slow, uderzenia, koniec_haka) -> list[tuple[int, int]]`:
  - `a` to indeks pierwszego uderzenia nie wcześniejszego niż `koniec_haka - 2`;
  - `krok` to 1, gdy mediana odstępu uderzeń ma co najmniej 0,3 s, a inaczej 2;
  - słowo `i < n - 1` zaczyna się na uderzeniu `a - krok * (n - 1 - i)` i trwa do początku następnego;
  - ostatnie słowo (akcent) zaczyna się na uderzeniu `a` i trwa `2 * krok` uderzeń; bez dalszych uderzeń trwa `fps` klatek, ale nigdy dłużej niż do końca editu;
  - gdy `a - krok * (n - 1) < 0`, rzuca `ValueError` z najwyższą liczbą słów `a // krok + 1`.
- Akcent:
  - 1,6 raza większy niż pozostałe słowa;
  - przez pierwsze 6 klatek skala maleje od 6 do 1 (`1 + 5 * (1 - k / 6) ** 2`), potem stoi, jak „EUROPE” w `0923`.
- Słowa zmieniają się twardo na uderzeniu, bez przenikania.
- Napisy linii z części 6: gdy są słowa, okno linii kończy się na początku pierwszego słowa zamiast na `koniec_haka`.
- Podsumowanie: `"slowa": {"liczba": 5, "krok": 1, "okna": [[90, 105], ...]} | null`.

**Napis pionowy (9.7):**
- Bot: `/pionowo <tekst>` zapisuje `projekt.json["pionowo"]`, najwyżej 40 znaków; `/pionowo` bez tekstu czyści pole.
- Wygląd:
  - czcionka presetu `szeryf` (Libre Baskerville Bold) w kolorach wspólnych;
  - obrót o 90° przeciwnie do ruchu wskazówek zegara, więc czyta się od dołu do góry;
  - wysokość wersalika 2,6% wysokości kadru, oś napisu na 5% szerokości, początek tekstu na 85% wysokości;
  - napis dłuższy niż 80% wysokości kadru zmniejsza czcionkę.
- `tekst.okno_pionowe(plan, liczba_znakow, fps, koniec) -> tuple[int, int, int]`, czyli (początek, koniec pisania, koniec):
  - start na `klatka_od` drugiego ujęcia planu;
  - co 2 klatki przybywa jeden znak;
  - po wypisaniu napis stoi co najmniej `fps` klatek i znika na najbliższym następnym początku ujęcia;
  - całość musi się skończyć przed `koniec`, czyli przed początkiem pierwszego słowa w rytmie albo, bez słów, przed `koniec_haka`;
  - inaczej `ValueError` z najwyższą liczbą znaków.
- Podsumowanie: `"pionowo": {"znaki": 25, "od": 60, "do": 150} | null`.

## Zadania

### [Task 9.1: Wznowienie po restarcie]
- **Objective:** `bot.wznow_po_starcie`, wysyłka przez `bot` i `chat_id`, `blad.txt` po nieudanej analizie, czyszczenie `praca/` w renderze.
- **Context/Inputs:** kontrakt 9.1; `src/bot.py` (`renderuj_w_tle`, `analizuj_wzor_w_tle`, `obsluz_wzor_plik`, `obsluz_cmd_gotowe`, `uruchom_bota`), `src/render.py` (`renderuj`), `tests/test_bot.py`, `tests/pomocnicze.py`.
- **Constraints:** testy w `tests/test_fabryka.py`:
  1. projekt w stanie `renderowanie` na dysku przy starcie: jedno zadanie w kolejce i jedna wiadomość do czatu właściciela;
  2. projekt w stanie `gotowy` pozostaje nietknięty;
  3. wzór z `zrodlo.mp4` bez `wzor.json` wraca do analizy, a wzór z `blad.txt` nie wraca;
  4. nieudana analiza zapisuje `blad.txt`;
  5. render z pozostawionym plikiem w `praca/` usuwa go i kończy się sukcesem;
  6. dotychczasowe testy montażu i analizy przechodzą po dostosowaniu do `bot` i `chat_id`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 9.1 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/bot.py, src/render.py tylko w miejscu renderuj, src/magazyn.py, tests/test_bot.py, tests/pomocnicze.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `bot: wznowienie po restarcie`

### [Task 9.2: Biblioteka wzorów]
- **Objective:** aktywny wzór, nazwy wzorów, `/wzory` z przyciskami, filtr właściciela na przyciskach.
- **Context/Inputs:** kontrakt 9.2; `src/magazyn.py`, `src/bot.py` (`utworz_dispatcher`, `zbuduj_router`, `obsluz_wzor_plik`, `obsluz_cmd_gotowe`, `obsluz_cmd_status`, komendy `/nakladka` i `/plansza`), `src/komunikaty.py` (`POMOC`, `KOMENDY`), `tests/pomocnicze.py`. `SesjaTestowa` potrzebuje obsługi `AnswerCallbackQuery` i `EditMessageText` oraz pomocnika `zbuduj_callback(dane, od_id=WLASCICIEL_ID)`.
- **Constraints:** testy:
  1. `ustawienia.json` zapisywany atomowo; `aktywny_wzor` bez ustawienia i po usunięciu aktywnego zwraca najnowszy;
  2. podpis wideo wzoru trafia do `nazwa.txt`;
  3. `/wzory` wysyła listę z klawiaturą inline;
  4. przycisk „Wybierz” ustawia aktywny wzór;
  5. „Usuń” bez potwierdzenia nic nie usuwa, a po potwierdzeniu znika katalog wzoru i jego plik w `dane/nakladki/`;
  6. przycisk od obcego nic nie zmienia;
  7. `/gotowe` przekazuje do renderu `--wzor` aktywnego wzoru, a nie najnowszego.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 9.2 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/magazyn.py, src/bot.py, src/komunikaty.py, tests/test_bot.py, tests/test_magazyn.py, tests/pomocnicze.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `bot: biblioteka wzorów`

### [Task 9.3: Warianty, partie i ponowienie]
- **Objective:** `render.uloz_wariant` i `--wariant`, `/gotowe N`, `/gotowe wszystkie`, `/ponow` i zadania w `projekt.json`.
- **Context/Inputs:** kontrakt 9.3; `src/render.py` (`wstawki`, `renderuj`, `glowna`), `src/bot.py`, `src/komunikaty.py`, `src/magazyn.py`, `tests/test_render.py`, `tests/test_bot.py`.
- **Constraints:** testy:
  1. `uloz_wariant`:
     - wariant 0 to tożsamość;
     - pierwszy materiał zawsze pierwszy;
     - ten sam wariant daje tę samą kolejność;
     - warianty 1 i 2 dają różne kolejności przy co najmniej 4 materiałach;
  2. `/gotowe 3` dodaje 3 zadania z `--wariant` 0, 1 i 2 oraz różnymi plikami wyjścia;
  3. `/gotowe wszystkie` przy dwóch wzorach dodaje 2 zadania z różnymi `--wzor`;
  4. `/gotowe 9` odpowiada opisem użycia i nie dodaje nic;
  5. `/ponow 2` po zakończonym projekcie dodaje 2 zadania bez stanu zbierania, a bez zakończonego projektu odpowiada komunikatem;
  6. stany: po trzech zadaniach, z których jedno zawiodło, stan to `gotowy` z jednym wpisem `blad`; gdy wszystkie zawiodły, stan to `blad`;
  7. wznowienie z 9.1 ponawia tylko zadania w stanie `w_kolejce`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 9.3 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/render.py, src/bot.py, src/komunikaty.py, src/magazyn.py, tests/test_render.py, tests/test_bot.py, tests/test_fabryka.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render i bot: warianty i partie`

### [Task 9.4: Pomiar]
- **Objective:** `Pomiary/measure_fabryka.py`, wynik w `outputs/pomiar_fabryka.json` i arkusze.
- **Context/Inputs:**
  - **Sekcja A:**
    - `uloz_wariant` jest powtarzalny: ten sam wariant 100 razy daje tę samą kolejność;
    - warianty się różnią: dla 12 materiałów i wariantów od 1 do 5 liczymy średni udział ujęć planu z innym materiałem niż w wariancie 0, na wzorze syntetycznym z 32 ujęciami.
  - **Sekcja B:**
    - czas renderu 3 wariantów syntetycznego projektu 1080x1920, 20 s, lokalnie, w sekundach renderu na sekundę wyniku;
    - szacunek na serwerze z proporcji do danych z `ROZWOJ.md` (141 s na edit 32 s przy 2 CPU).
  - **Sekcja C:** arkusze porównawcze wariantów 0, 1 i 2 dla jednego prawdziwego wzoru: `outputs/porownanie_fabryka_<wzor>_<wariant>.png`.
- **Constraints:** progi:
  - A: pełna powtarzalność, a średni udział innych materiałów co najmniej 50%;
  - B: tylko raport;
  - C: arkusze powstały.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 9.4 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/render.py, tests/generuj.py, Pomiary/arkusz.py, Pomiary/measure_muzyka.py jako wzór układu. Weryfikacja: python Pomiary/measure_fabryka.py
```
- **Commit:** `Pomiary: pomiar fabryki`

### [Task 9.5: Nakładka z kryciem (flaga)]
- **Objective:** tryb `krycie` w `render.tryb_nakladki` i w `przebieg_koncowy`, skalowanie contain dla trybu `alfa`, komunikat bota.
- **Kiedy:** zaraz po scaleniu części 8, na gałęzi `krycie` od `main`, osobnym PR-em. Nie czeka na części 5, 6 ani 9.1–9.4.
- **Context/Inputs:** kontrakt „Nakładka z kryciem”; `src/render.py` (`tryb_nakladki`, `przebieg_koncowy`), `src/komunikaty.py`, `tests/generuj.py` (`nakladka_testowa`), `tests/test_nakladka.py`, `tests/test_bot.py`.
- **Constraints:** testy:
  1. `nakladka_testowa(..., tryb="krycie")`: mp4 z granatowym tłem (0, 51, 153) i żółtym kwadratem w górnej połowie. `tryb_nakladki` daje `krycie`, a pliki trybów `alfa`, `zielen` i `ekran` z części 8 dalej dają swoje tryby;
  2. render z nakładką `krycie` na jednolicie niebieskim materiale: w oknie piksel równy średniej materiału i nakładki (±8), a poza oknem materiał bez zmian;
  3. bot: po wysłaniu pliku `krycie` odpowiedź zawiera „krycie 50%”;
  3a. nakładka `alfa` 600x600 (żółty pierścień na przezroczystym tle) w kadrze 270x480:
      - cały pierścień widoczny: żółte piksele przy lewej i prawej krawędzi pierścienia, w 5% do 95% szerokości;
      - środek pierścienia na środku kadru (±2 px);
      - nad i pod pierścieniem materiał bez zmian;
  4. pomiar: `python Pomiary/measure_nakladka.py` z flagą w `dane/nakladki/domyslna.mp4` daje arkusze z flagą obok wzorów `0914` i `0923`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. git pull na main, potem gałąź krycie. Wykonaj zadanie 9.5 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/render.py, src/komunikaty.py, tests/generuj.py, tests/test_nakladka.py, tests/test_bot.py. Weryfikacja: python -m pytest -q, potem python Pomiary/measure_nakladka.py.
```
- **Commit:** `render: nakładka z kryciem`

### [Task 9.6: Słowa w rytmie]
- **Objective:** `render.uderzenia_wyniku`, preset `rytm`, `tekst.okna_slow`, warstwa `praca/slowa.mov` w przebiegu końcowym, komenda `/slowa`.
- **Context/Inputs:** kontrakty „Napisy w rytmie, wspólne” i „Słowa w rytmie”; `src/tekst.py`, `src/render.py` (`renderuj`, `przebieg_koncowy`, `koniec_haka`, `przygotuj_zrodlo_dzwieku`), `src/bot.py`, `src/komunikaty.py`, `zasoby/`, `tests/generuj.py`, `tests/test_bot.py`. Nowy plik `tests/test_rytm.py`.
- **Constraints:** testy w `tests/test_rytm.py` (270x480):
  1. `uderzenia_wyniku([10.0, 10.5, 11.0, 11.5], 10.0, 60, 30)` daje `[0, 15, 30, 45]`, a pusta lista daje siatkę `[0, 15, 30, 45]`;
  2. `okna_slow(5, uderzenia co 15 klatek, 150)` daje `[(90, 105), (105, 120), (120, 135), (135, 150), (150, 180)]`;
  3. uderzenia co 8 klatek (0,27 s): `krok` 2, słowa co 16 klatek;
  4. 12 słów przy `koniec_haka` 45 i uderzeniach co 15 klatek: `ValueError` z liczbą 4;
  5. `tekst.obraz_slowa("żółć", ...)` w presecie `rytm`: są piksele złote (R > 200, G > 160, B < 140) i granatowe obrysu, a wszystkie znaki są w czcionce;
  6. pełny render z 3 słowami:
     - w środku okna każdego słowa na środku kadru są złote piksele, a poza oknami ich nie ma;
     - prostokąt złotych pikseli w pierwszej klatce akcentu jest szerszy niż w siódmej;
     - długość wyniku bez zmian;
  7. bez słów polecenie przebiegu końcowego identyczne (podmienione `uruchom_ffmpeg`);
  8. bot: `/slowa our time is now` w zbieraniu zapisuje pole i odpowiada liczbą słów; 13 słów daje komunikat z limitem, a `/slowa` czyści;
  9. słowa i linie z części 6 razem: ostatnia linia kończy się na początku pierwszego słowa.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rytm. Wykonaj zadanie 9.6 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/tekst.py, src/render.py, src/bot.py, src/komunikaty.py, tests/generuj.py, tests/test_bot.py, nowy tests/test_rytm.py. Czcionki pobierz z repozytorium google/fonts z OFL.txt, ścieżki sprawdź. Weryfikacja: python -m pytest -q
```
- **Commit:** `render i bot: słowa w rytmie`

### [Task 9.7: Napis pionowy pisany literami]
- **Objective:** `tekst.obraz_pionowy`, `tekst.okno_pionowe`, warstwa `praca/pionowo.mov`, komenda `/pionowo`.
- **Context/Inputs:** kontrakty „Napisy w rytmie, wspólne” i „Napis pionowy”; te same pliki co w 9.6.
- **Constraints:** testy w `tests/test_rytm.py`:
  1. `obraz_pionowy(tekst, k, 270, 480)`:
     - prostokąt pikseli napisu leży w 0% do 12% szerokości;
     - dolna krawędź na 85% wysokości (±1 punkt);
     - wysokość prostokąta rośnie z `k`;
  2. `okno_pionowe`:
     - początek na `klatka_od` drugiego ujęcia;
     - koniec pisania po `2 * liczba_znakow` klatkach;
     - koniec na pierwszym początku ujęcia po `koniec pisania + fps`;
     - `ValueError` z najwyższą liczbą znaków, gdy nie mieści się przed `koniec`;
  3. render:
     - klatka `początek + 2` ma mały prostokąt napisu;
     - klatka po zakończeniu pisania ma pełny;
     - po końcu nie ma napisu;
  4. bot: `/pionowo` zapisuje i czyści pole, a 41 znaków daje komunikat z limitem.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rytm. Wykonaj zadanie 9.7 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/tekst.py, src/render.py, src/bot.py, src/komunikaty.py, tests/test_rytm.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `render i bot: napis pionowy`

### [Task 9.8: Pomiar napisów w rytmie]
- **Objective:** `Pomiary/measure_rytm.py`, wynik w `outputs/pomiar_rytm.json` i arkusze.
- **Context/Inputs:** słowa „europe be like POLAND” i napis pionowy „1993 supply made in poland”, czyli hasło właściciela, a nie tekst ze wzoru.
  - **Sekcja A:** dla każdego wzoru z `dane/wzory/*.mp4` render z muzyką z biblioteki:
    - odsetek słów zaczynających się na klatce uderzenia z `uderzenia_wyniku` (±1 klatka);
    - odległość początku akcentu od początku nakładki w uderzeniach.
  - **Sekcja B:** narzut czasu procesora przebiegu końcowego (1080x1920, 20 s) ze słowami i napisem pionowym wobec przebiegu bez nich (`-benchmark`, jak w `Pomiary/measure_tekst.py`).
  - W całym pomiarze `render.uruchom_ffmpeg` podmieniony na wersję z limitem 900 s (jak `LIMIT_RENDERU_S` bota): zawieszony przebieg ma trafić do wyniku jako błąd wzoru, a pomiar ma iść dalej.
  - **Sekcja C:**
    - arkusze `outputs/porownanie_rytm_<wzor>.png`;
    - obraz `outputs/rytm_klatki.png`: klatki wyniku w chwilach słów obok klatek `0923` z 9,6, 10,3, 10,8, 11,1, 11,8 i 12,3 s, do porównania wyglądu.
- **Constraints:** progi:
  - A: 100% słów na uderzeniu, a akcent najwyżej 1 uderzenie od nakładki;
  - B: tylko raport (czas nie jest progiem, decyzja właściciela 2026-09-24);
  - A i C: żaden render nie przekroczył limitu 900 s;
  - C: pliki powstały, a werdykt wydaje właściciel.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rytm. Wykonaj zadanie 9.8 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/render.py, src/tekst.py, Pomiary/arkusz.py, Pomiary/measure_nakladka.py jako wzór układu. Weryfikacja: python Pomiary/measure_rytm.py
```
- **Commit:** `Pomiary: pomiar napisów w rytmie`

### [Task 9.9: Poprawki po odbiorze 9.6 do 9.8]
- **Objective:** wielkość napisów zgodna z planem i ze wzorem `0923`, napis pionowy mieszczący się na wszystkich 5 wzorach i montaż, który nie pada przez warstwę ozdobną.
- **Context/Inputs** (odbiór 2026-09-25 w `ROZWOJ.md`); `src/tekst.py`, `src/render.py` (`renderuj`, `przygotuj_slowa`, `przygotuj_pionowy`), `src/komunikaty.py`, `tests/test_tekst.py`, `tests/test_rytm.py`, `tests/test_bot.py`:
  1. `tekst.dopasuj_wysokosc` mierzy wysokość na „AĄŻ” razem z ogonkiem i kropką, więc prawdziwy wersalik wychodzi na 64% celu w każdym presecie. Przy 1920 px „H” ma 39 px zamiast 61 w `szeryf`, 49 zamiast 77 w `blok` i 62 zamiast 96 w `rytm`.
     - Mierz na samym „H”.
     - Właściciel zaakceptował wygląd części 6 w obecnym rozmiarze. Dlatego `szeryf` dostaje `wysokosc_wersalika` 0,020, a `blok` 0,026, co po poprawce daje te same piksele co dziś.
  2. Słowa w rytmie są około 4 razy mniejsze niż w `0923`. Tam wypełnienie słowa „our” ma 155 px wysokości przy 1920, a u nas litera „x” ma 33 px.
     - Preset `rytm` ustala wielkość po wysokości litery „x” (mierzonej na „x”): 7,5% wysokości kadru.
     - Akcent jest 1,6 raza większy i jak dotąd zmniejsza się do szerokości strefy.
     - Napis pionowy zostaje przy wersaliku 2,6%. Po poprawce 1 będzie większy niż dziś, tak jak chciał plan.
  3. `tekst.okno_pionowe`:
     - początek na `klatka_od` drugiego ujęcia. Gdy stamtąd pisanie i 1 s postoju nie mieszczą się przed `koniec`, początek na klatce 0 (we wzorze `0921` cały hak to jedno ujęcie);
     - koniec na najbliższym początku ujęcia po `koniec pisania + fps`, ale najpóźniej na `koniec`. Dziś przyciąganie do cięcia wypycha napis za `koniec` na `0922`, choć pisanie mieści się z zapasem;
     - `ValueError` tylko wtedy, gdy `koniec pisania + fps > koniec` także przy starcie od klatki 0. Komunikat podaje liczbę znaków, która naprawdę się mieści.
  4. Warstwa ozdobna nie przerywa montażu (rekomendacja z odbioru 2026-09-25, potwierdza właściciel przed startem):
     - gdy `okna_slow` albo `okno_pionowe` rzuca `ValueError`, `renderuj` montuje bez tej warstwy;
     - podsumowanie dostaje `"slowa": {"pominiete": "<komunikat>"}` albo `"pionowo": {"pominiety": "<komunikat>"}`;
     - podpis wyniku dostaje zdanie „Słowa w rytmie pominięte: w haku tego wzoru mieści się najwyżej N słów.” albo „Napis pionowy pominięty: w haku tego wzoru mieści się najwyżej N znaków.”.
- **Constraints:** testy:
  1. przy wysokości 1920 „H” presetu `szeryf` ma od 38 do 40 px, a `blok` od 48 do 50 px, więc wygląd części 6 się nie zmienia; litera „x” presetu `rytm` ma od 137 do 151 px;
  2. `okno_pionowe`:
     - na planie z jednym ujęciem w haku zaczyna od klatki 0;
     - na planie, gdzie następne cięcie po pisaniu leży za `koniec`, kończy się na `koniec`;
     - liczba z komunikatu `ValueError` przechodzi bez błędu, a o 1 większa rzuca;
  3. render z napisem pionowym, który się nie mieści: kod 0, `pominiety` w podsumowaniu i zdanie w podpisie. Tak samo dla słów, których jest więcej, niż mieści hak;
  4. pozostałe testy bez zmian w treści poza liczbami rozmiaru.
- **Pomiar:** `python Pomiary/measure_rytm.py` jeszcze raz. A i C bez błędu na wszystkich 5 wzorach, a w `outputs/rytm_klatki.png` słowa mają wielkość zbliżoną do `0923`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rytm. Wykonaj zadanie 9.9 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/tekst.py, src/render.py, src/komunikaty.py, tests/test_tekst.py, tests/test_rytm.py, tests/test_bot.py. Weryfikacja: python -m pytest -q, potem python Pomiary/measure_rytm.py. Dopisz wpis do Pomiary/ROZWOJ.md i zrób commit `tekst: rozmiar napisów i napis pionowy po odbiorze`.
```
- **Commit:** `tekst: rozmiar napisów i napis pionowy po odbiorze`

### [Task 9.10: Akcent na całą szerokość i wjazd poza kadr]
- **Objective:** ostatnie słowo w rytmie (akcent) jest większe od pozostałych i wlatuje z powiększenia także wtedy, gdy jest długie, jak „EUROPE” w `0923`.
- **Context/Inputs** (test lokalny po wdrożeniu, 2026-09-26); `src/tekst.py` (`obraz_slowa`, `skala_wjazdu_akcentu`), `src/render.py` (`przygotuj_slowa`, funkcja `klatka_dla`), `tests/test_rytm.py`:
  - dziś `obraz_slowa` zmniejsza każde słowo do szerokości strefy bezpiecznej, także akcent i klatki wjazdu. „POLAND” wielkimi literami jest szerokie, więc wychodzi niższe niż „like”, a wjazd (skala od 6 do 1) znika, bo powiększone słowo od razu kurczy się do szerokości strefy;
  - we wzorze `0923` „EUROPE” zajmuje 91% szerokości kadru (od 46 do 1031 px przy 1080), wychodząc poza strefę bezpieczną, a w pierwszych klatkach wjazdu pojedyncza litera wypełnia cały kadr.
- **Kontrakt:**
  - `obraz_slowa(tresc, szerokosc, wysokosc, akcent=False, wjazd=1.0)` zamiast parametru `skala`;
  - zwykłe słowo bez zmian: zmniejszane do szerokości strefy bezpiecznej, wyśrodkowane w strefie;
  - akcent: wielkość 1,6 raza większa od zwykłego słowa, zmniejszana najwyżej do 95% szerokości kadru (nie strefy), wyśrodkowana na środku kadru w poziomie, środek na 50% wysokości;
  - `wjazd` mnoży wielkość akcentu po dopasowaniu do szerokości i niczego już nie zmniejsza: w klatkach wjazdu słowo wychodzi poza kadr;
  - `render.przygotuj_slowa` przekazuje dla akcentu `akcent=True` i `wjazd=tekst.skala_wjazdu_akcentu(klatka - od)`.
- **Constraints:** testy w `tests/test_rytm.py` (1080x1920):
  1. akcent „POLAND” przy `wjazd=1`: ramka złotych pikseli ma szerokość od 60% do 95% kadru i jest co najmniej 1,15 raza wyższa niż ramka zwykłego słowa „POLAND”;
  2. akcent „EU” (krótki, bez limitu szerokości): wysokość ramki od 1,45 do 1,75 raza większa niż zwykłego „EU”;
  3. akcent „POLAND” przy `wjazd=6`: złote albo granatowe piksele są w pierwszej i w ostatniej kolumnie kadru;
  4. istniejący test renderu „akcent szerszy w pierwszej klatce niż w siódmej” przechodzi także dla akcentu „POLAND”.
- **Pomiar:** `python Pomiary/measure_rytm.py`. A i C bez błędu na 5 wzorach, a w `outputs/rytm_klatki.png` akcent jest większy od pozostałych słów.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Utwórz gałąź `akcent` od aktualnego `main` (przed startem `git pull`). Niezacommitowane zmiany w Pomiary/ dołącz do swojego commita, nie chowaj ich do stash. Wykonaj zadanie 9.10 z Pomiary/PLAN_EDITY_9_FABRYKA.md; otwórz src/tekst.py, src/render.py, tests/test_rytm.py. Weryfikacja: python -m pytest -q, potem python Pomiary/measure_rytm.py. Pliki robocze trzymaj poza repo. Dopisz wpis do Pomiary/ROZWOJ.md i zrób commit `tekst: akcent na całą szerokość i wjazd poza kadr`. Na koniec krótki raport.
```
- **Commit:** `tekst: akcent na całą szerokość i wjazd poza kadr`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A w progach, B zaraportowane, arkusze C powstały.
- Pomiar napisów (9.8): A w progach, B zaraportowane, arkusze C ocenione przez Ciebie. Zadania 9.5 i 9.6 do 9.8 scalone osobnymi PR-ami.
- Test ręczny (Ty) na serwerze po `wdroz.ps1`:
  - `/gotowe` na projekcie, a w trakcie montażu `docker compose restart bot`: po starcie bot pisze o wznowieniu i odsyła wynik;
  - `/wzory`: wybór i usunięcie z potwierdzeniem;
  - `/gotowe 3` daje trzy różne warianty;
  - `/ponow wszystkie` daje po editcie na każdy wzór bez ponownego wysyłania materiałów;
  - każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `bot: wznowienie po restarcie`
2. `bot: biblioteka wzorów`
3. `render i bot: warianty i partie`
4. `Pomiary: pomiar fabryki`
5. `render: nakładka z kryciem` (9.5, gałąź `krycie`)
6. `render i bot: słowa w rytmie` (9.6, gałąź `rytm`)
7. `render i bot: napis pionowy` (9.7, gałąź `rytm`)
8. `Pomiary: pomiar napisów w rytmie` (9.8, gałąź `rytm`)
9. `tekst: rozmiar napisów i napis pionowy po odbiorze` (9.9, gałąź `rytm`)
10. `tekst: akcent na całą szerokość i wjazd poza kadr` (9.10, gałąź `akcent`)

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 9 według Pomiary/PLAN_EDITY_9_FABRYKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..fabryka`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_fabryka.py`: progi A i czasy B.
3. Arkusze `outputs/porownanie_fabryka_*.png`: warianty różnią się materiałami, hak ma ten sam materiał, a struktura wzoru jest zachowana.
4. `src/bot.py`:
   - wznowienie tylko dla niedokończonych zadań;
   - wysyłka przez `bot` i `chat_id`;
   - filtr właściciela na `callback_query`;
   - usuwanie wzoru dopiero po potwierdzeniu;
   - aktywny wzór wszędzie tam, gdzie wcześniej był najnowszy.
5. `src/render.py`: `uloz_wariant` czysta i deterministyczna, `praca/` czyszczona na starcie.
6. Napisy w rytmie:
   - `python Pomiary/measure_rytm.py`;
   - `outputs/rytm_klatki.png`: styl słów bliski `0923` (złoto z granatowym obrysem, pismo odręczne, akcent wlatuje);
   - słowa na uderzeniach, akcent na dropie;
   - warstwy jako jedno wejście każda;
   - bez napisów polecenie się nie zmienia.
