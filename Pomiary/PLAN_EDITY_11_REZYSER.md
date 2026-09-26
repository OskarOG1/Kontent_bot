# Część 11: reżyser i krytyk AI

**Zależy od:** części 10 (tempo, przejścia, kolaż). Reżyser wybiera z efektów, które daje część 10, więc bez niej nie ma czym sterować.
**Gałąź:** `rezyser` od `main` po scaleniu `dynamika`.
**Efekt:**
- **Reżyser przed montażem.** Claude dostaje podgląd materiałów projektu (arkusze miniatur zdjęć, klatki z klipów i wycinki), opis wzoru (hak, drop, uderzenia, plansza) i listę efektów z części 10. Zwraca scenariusz: kolejność ujęć, długość w uderzeniach, fragment każdego klipu, efekt na każdym cięciu i kolaże. Render montuje według scenariusza. Robi więc to, co Opus robił ręcznie przy edicie pokazowym 2026-09-26: wybiera otwarcie haku i dobre fragmenty długich klipów.
- **Krytyk po montażu.** Claude ogląda arkusz klatek gotowego editu obok wzoru i daje ocenę od 1 do 10 z listą poprawek. Przy ocenie poniżej progu render robi jedną poprawioną wersję.
- Bez klucza, po błędzie API, po odmowie albo przy nieprawidłowym scenariuszu montaż idzie automatycznie jak w części 10. Podpis mówi wtedy, dlaczego.

**Dlaczego:** Twój pomysł z 2026-09-26: „dodać AI żeby ulepszało na końcu edity albo wymyślało scenariusz z tymi edycjami”. Automat z części 10 układa materiały w kolejności wysłania i bierze klipy od początku. Nie widzi, co jest na zdjęciu ani która scena w klipie jest dobra.
**Model:** `claude-opus-5` (Claude Opus 5, 5 $ za milion tokenów wejścia i 25 $ za milion wyjścia; cennik z 2026-06-24 według narzędzia `claude-api`). Widzi obrazy, odpowiada w zadanym schemacie JSON i dobrze planuje. Zmiana modelu idzie przez `MODEL_AI` w `.env`, bez zmian w kodzie.
**Szacunek kosztu:**
- reżyser: około 15 tys. tokenów wejścia (3 do 4 arkusze obrazów i opis wzoru) i 4 do 8 tys. wyjścia, czyli 0,15 do 0,30 $;
- krytyk: około 8 tys. wejścia i 2 do 4 tys. wyjścia, czyli 0,05 do 0,15 $;
- razem z jedną poprawką poniżej 0,50 $ za edit.

Pomiar 11.4 sprawdza to na prawdziwych wywołaniach.
**Nowe pliki:** `src/rezyser.py`, `tests/test_rezyser.py`, `Pomiary/measure_rezyser.py`.
**Zmieniane:** `src/render.py`, `src/konfiguracja.py`, `.env.example`, `src/bot.py`, `src/komunikaty.py`, `tests/test_render.py`, `tests/test_konfiguracja.py`, `tests/test_bot.py`, `requirements.txt` (pakiet `anthropic`).
**Od właściciela:**
- klucz API Anthropic w `.env` na serwerze (`ANTHROPIC_API_KEY=...`) i, na czas pomiaru 11.4, w lokalnym `.env`. Klucz wpisujesz tylko tam: nie wklejaj go do czatu ani do plików w repo;
- zgoda na koszt pomiaru 11.4 (szacunek do 5 $);
- ocena editów z reżyserem wobec automatycznych.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania 11.1 do 11.4 z Pomiary/PLAN_EDITY_11_REZYSER.md na gałęzi `rezyser` od aktualnego `main` (przed startem `git pull`), zaczynając od „Stan wejściowy”. Przed pisaniem kodu, który woła API Claude, wczytaj skill `claude-api` i trzymaj się jego wskazówek dla Pythona. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Nie otwieraj `.env` i nie wypisuj klucza API nigdzie. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Pomiar 11.4 wydaje prawdziwe pieniądze: uruchom go tylko wtedy, gdy klucz jest ustawiony, i podaj koszt w raporcie. Pliki robocze trzymaj poza repo. Na koniec zdaj krótki raport.
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
`main` zawiera commit `Pomiary: pomiar dynamiki` (część 10 po odbiorze i scaleniu), a `python -m pytest -q` przechodzi. Utwórz gałąź `rezyser` od `main`. Jeśli commita brakuje, zatrzymaj się i zapytaj.

## Kontrakt z wcześniejszych części
Szukaj po nazwach, bo numery linii przesuną się po części 10.
- Część 10 w `src/render.py`:
  - `rozdziel_wycinki(materialy)`, `rozloz_tempo(plan, wzor, uderzenia, kawalki, fps)`, `efekt_ujecia(...)` (klucze `uderzenie`, `blysk_s`, `wstrzas`, `przejscie`);
  - kolaż z puli wycinków (najwyżej 3 na ujęcie, wskok na uderzeniach);
  - CLI `--bez-dynamiki`, podsumowanie `dynamika` i `kolaze`.
- `render.uderzenia_wyniku`, `render.koniec_haka`, okna słów (`przygotuj_slowa`) i napisu pionowego (`przygotuj_pionowy`).
- `render.przygotuj_materialy`: zdjęcia mają `plik_roboczy`, klipy `czas_s`.
- `Pomiary/arkusz.py`: `arkusz_porownawczy(wzor, wynik, cel)`.
- Bot: `renderuj_w_tle` przekazuje parametry z `Konfiguracja` do CLI renderu i wysyła podsumowanie przez `komunikaty.podsumowanie_renderu`. `LIMIT_RENDERU_S` 900 s zabija render razem z procesami potomnymi.

## Kontrakty ustalane w tej części

**Konfiguracja (11.1):**
- `.env` i `Konfiguracja`:
  - `ANTHROPIC_API_KEY`: pusta albo brak oznacza AI wyłączone. Klucz czyta SDK ze środowiska. Nie trafia do logów, podsumowań, komunikatów ani wyjątków;
  - `MODEL_AI` (domyślnie `claude-opus-5`);
  - `AI_REZYSER` i `AI_KRYTYK` (`tak` albo `nie`, domyślnie `tak`);
  - `PROG_OCENY_AI` (domyślnie 7, od 1 do 10).
- Bot przekazuje do renderu `--ai` tylko wtedy, gdy klucz jest ustawiony i choć jeden z kroków jest włączony. Do tego `--model-ai`, `--bez-rezysera`, `--bez-krytyka` i `--prog-oceny-ai`. Render bierze klucz ze środowiska procesu, które dziedziczy po bocie (kontener dostaje `.env`).
- `LIMIT_RENDERU_S` rośnie z 900 do 1800 s, bo krytyk może zlecić drugi montaż (limity podnosimy, gdy praca się do nich zbliża, decyzja 18).
- `/status` pokazuje linię „AI: włączone (claude-opus-5)” albo „AI: wyłączone (brak klucza)”.
- `requirements.txt`: `anthropic` przypięty do aktualnej wersji (sprawdź `pip index versions anthropic`).

**Wywołanie modelu (`src/rezyser.py`, 11.1):**
- Jedna funkcja `wywolaj_model(klient, model, tresc, schemat) -> tuple[dict | None, dict]` zwraca (odpowiedź zgodną ze schematem albo `None`, zużycie `{"wejscie": int, "wyjscie": int, "powod": str | None}`). Testy podmieniają `klient`, więc bez sieci.
- Żądanie:
  - `thinking={"type": "adaptive"}`, `output_config={"effort": "high", "format": {"type": "json_schema", "schema": ...}}`;
  - odmowy przez parametr `fallbacks="default"` z nagłówkiem beta `server-side-fallback-2026-07-01` (ścieżka `client.beta.messages`). Kształt żądania sprawdź w skillu `claude-api` przed napisaniem kodu;
  - obrazy jako bloki `image` w base64 (JPEG), tekst po obrazach;
  - `max_tokens` 16000.
- `stop_reason` różny od `end_turn` (w tym `refusal` i `max_tokens`), wyjątek SDK, JSON niezgodny ze schematem albo brak klucza: wynik `None` i powód w zużyciu. Montaż idzie wtedy automatycznie.
- Koszt: `koszt_usd(model, wejscie, wyjscie)` z tabeli cen w module (`claude-opus-5`: 5 i 25 $ za milion tokenów). Nieznany model daje `None`.

**Materiały dla reżysera (11.1):**
- `arkusze_materialow(materialy, wycinki, katalog_pracy) -> list[Path]`, obrazy JPEG, dłuższy bok najwyżej 1568 px:
  - zdjęcia: siatka miniatur 9:16 z numerem materiału w rogu (numer to indeks w liście materiałów projektu);
  - klipy: na każdy klip pasek 6 klatek w równych odstępach, podpisanych numerem klipu i sekundą;
  - wycinki: siatka na szachownicy, żeby było widać przezroczystość.
- `opis_wzoru(wzor, plan, uderzenia, okna_tekstow) -> str` to zwięzły JSON: długość, fps, klatki uderzeń, klatka dropu, początek planszy, granice ujęć wzoru, okna napisów, słów i napisu pionowego. Do tego lista materiałów (numer, typ, długość klipu).

**Scenariusz (11.2):**
- Schemat (Pydantic w `rezyser.py`, z niego JSON Schema do `output_config`):
  - `Ujecie`: `material` (int, numer zwykłego materiału), `od_s` (float, początek fragmentu klipu, dla zdjęcia 0), `uderzenia` (int od 1 do 8), `uderzenie` (bool), `blysk_s` (0, 0,1 albo 0,3), `wstrzas` (bool), `przejscie` (`brak`, `smuga` albo `najazd`), `kolaz` (lista najwyżej 3 numerów wycinków);
  - `Scenariusz`: `ujecia` (lista), `uzasadnienie` (najwyżej 300 znaków).
- Polecenie dla modelu jest stałe (w module, bez zmiennych wewnątrz, żeby cache promptu działał). Mówi, czym jest edit (promocja czapek 1993 Supply, format wzoru: hak, drop, montaż, plansza) i jakie są reguły części 10:
  - zdjęcia 1 do 2 uderzeń;
  - klipy 4 do 7 uderzeń, fragment z najlepszą akcją;
  - najmocniejszy materiał na otwarcie haku i na drop;
  - kolaże na klipach tła;
  - nic ze wzoru nie trafia do wyniku.
- `plan_ze_scenariusza(scenariusz, plan, kawalki_wedlug_numeru, uderzenia, fps, wzor) -> tuple[dict, list[str]]` układa ujęcia po kolei od klatki 0:
  - długość ujęcia to jego liczba uderzeń od początku;
  - twarde cięcia z części 10 (drop, plansza) ucinają ujęcie, a następne zaczyna się na twardym cięciu;
  - gdy scenariusz się skończy przed planszą, resztę wypełnia `rozloz_tempo` pozostałymi materiałami. Nadmiar ujęć odpada;
  - `od_s` przycięte do `[0, czas_klipu - dlugosc]`;
  - nieznany numer, wycinek jako ujęcie albo zdjęcie z `od_s` różnym od 0 pomija ujęcie z ostrzeżeniem;
  - zwraca plan i listę ostrzeżeń.
- Efekty i kolaże ze scenariusza zastępują te z `efekt_ujecia` i z reguły „co drugi klip”. Drop dostaje błysk 0,3 i wstrząs zawsze, nawet gdy scenariusz ich nie ma.
- `scenariusz.json` z ostrzeżeniami zapisuje się w katalogu projektu (`scenariusz_<wzor>_<wariant>.json`), żeby dało się go przejrzeć.

**Krytyk (11.3):**
- Wejście: arkusz klatek wyniku (2 klatki na sekundę) nad arkuszem wzoru, jak `arkusz_porownawczy`, plus lista ujęć planu z czasami, efektami i numerami materiałów.
- Schemat `Ocena`: `ocena` (int od 1 do 10), `mocne` (najwyżej 3 krótkie punkty), `poprawki` (lista `{"ujecie": int, "problem": str, "zmiana": Ujecie}`).
- Gdy `ocena < PROG_OCENY_AI` i są poprawki: podmień wskazane ujęcia w scenariuszu i zmontuj raz jeszcze. Druga ocena tylko do podpisu, bez trzeciego montażu. Bez reżysera (automat) krytyk działa tak samo, a jego poprawki zamieniają automatyczny plan w scenariusz.
- Wynik: lepsza z dwóch wersji według ocen krytyka, przy remisie druga.

**Podsumowanie i podpis:**
- `"ai": {"model", "rezyser": bool, "ocena": int | None, "ocena_przed": int | None, "poprawka": bool, "ostrzezenia": [...], "tokeny_wejscia", "tokeny_wyjscia", "koszt_usd", "powod_pominiecia": str | None}`.
- Podpis dostaje linię „Scenariusz AI, ocena 8/10 (po poprawce)” albo „Scenariusz automatyczny: <powód>”, gdy AI było włączone, ale krok się nie udał. Bez AI podpis bez zmian.

## Zadania

### [Task 11.1: Konfiguracja, wywołanie modelu i arkusze materiałów]
- **Objective:** konfiguracja AI, `rezyser.wywolaj_model`, `koszt_usd`, `arkusze_materialow`, `opis_wzoru`, linia AI w `/status`, `anthropic` w `requirements.txt`.
- **Context/Inputs:** kontrakty „Konfiguracja”, „Wywołanie modelu” i „Materiały dla reżysera”; `src/konfiguracja.py`, `.env.example`, `src/bot.py` (`renderuj_w_tle`, `obsluz_cmd_status`, `LIMIT_RENDERU_S`), `src/komunikaty.py`, `requirements.txt`, `tests/test_konfiguracja.py`, `tests/test_bot.py`. Nowe `src/rezyser.py` i `tests/test_rezyser.py`.
- **Constraints:** testy bez sieci (klient podmieniony obiektem testowym):
  1. poprawna odpowiedź JSON daje słownik i zużycie z `usage`, a odpowiedź z `stop_reason` `refusal` albo `max_tokens`, wyjątek klienta lub JSON niezgodny ze schematem dają `None` z powodem;
  2. żądanie ma `thinking` adaptive, `output_config` z `effort` i schematem, `fallbacks` `default` z nagłówkiem beta, obrazy przed tekstem;
  3. `koszt_usd("claude-opus-5", 15000, 6000)` daje 0,225;
  4. arkusze: żaden obraz nie ma boku ponad 1568 px, numerów na arkuszach jest tyle, ile materiałów, a klip ma 6 klatek;
  5. brak `ANTHROPIC_API_KEY`: bot nie przekazuje `--ai`, a `/status` mówi „wyłączone (brak klucza)”. Z kluczem testowym `--ai` i `--model-ai` są w poleceniu. Wartość klucza nie pojawia się w żadnym komunikacie ani w poleceniu renderu;
  6. `AI_REZYSER=moze` daje `ValueError`.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rezyser. Wczytaj skill claude-api (Python). Wykonaj zadanie 11.1 z Pomiary/PLAN_EDITY_11_REZYSER.md; otwórz src/konfiguracja.py, .env.example, src/bot.py, src/komunikaty.py, requirements.txt, tests/test_konfiguracja.py, tests/test_bot.py, nowe src/rezyser.py i tests/test_rezyser.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `rezyser: konfiguracja i wywołanie modelu`

### [Task 11.2: Scenariusz reżysera w renderze]
- **Objective:** schemat `Scenariusz`, stałe polecenie, `plan_ze_scenariusza`, wpięcie w `renderuj` pod flagą `--ai`, zapis `scenariusz_*.json`, podsumowanie `ai`.
- **Context/Inputs:** kontrakt „Scenariusz”; `src/rezyser.py`, `src/render.py` (`renderuj`, `glowna`, funkcje części 10), `tests/test_rezyser.py`, `tests/test_render.py`, `tests/generuj.py`.
- **Constraints:** testy:
  1. scenariusz z 3 zdjęciami po 1 uderzeniu i klipem na 5 uderzeń: długości w klatkach zgodne z uderzeniami, `od_s` klipu przeniesione do `start_w_klipie_s`;
  2. ujęcie przechodzące przez drop zostaje ucięte na dropie, a następne zaczyna się na dropie;
  3. za krótki scenariusz: reszta z `rozloz_tempo`, suma klatek równa `liczba_klatek`. Za długi: nadmiar odpada;
  4. nieznany numer, wycinek jako ujęcie albo `od_s` dalej niż klip pozwala: pominięcie albo przycięcie z ostrzeżeniem, bez wyjątku;
  5. efekty i kolaże ze scenariusza trafiają do segmentów, a drop zawsze ma błysk 0,3 i wstrząs;
  6. pełny render 270x480 z podmienionym `wywolaj_model`: kod 0, `scenariusz_*.json` w katalogu projektu, `ai.rezyser` true. Z `wywolaj_model` zwracającym `None`: render automatyczny i `powod_pominiecia` w podsumowaniu;
  7. bez `--ai` polecenia ffmpeg identyczne jak przed tą częścią.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rezyser. Wczytaj skill claude-api (Python). Wykonaj zadanie 11.2 z Pomiary/PLAN_EDITY_11_REZYSER.md; otwórz src/rezyser.py, src/render.py, tests/test_rezyser.py, tests/test_render.py, tests/generuj.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `rezyser: scenariusz w renderze`

### [Task 11.3: Krytyk i jedna poprawka]
- **Objective:** schemat `Ocena`, arkusz dla krytyka, podmiana ujęć, drugi montaż, wybór lepszej wersji, podpis.
- **Context/Inputs:** kontrakt „Krytyk” i „Podsumowanie i podpis”; `src/rezyser.py`, `src/render.py`, `src/komunikaty.py`, `Pomiary/arkusz.py` (tylko jako wzór układu arkusza, bez importu z `src/`), `tests/test_rezyser.py`, `tests/test_bot.py`.
- **Constraints:** testy:
  1. ocena 5 z poprawką ujęcia 2: drugi montaż z podmienionym ujęciem, `poprawka` true, `ocena_przed` 5;
  2. ocena 8: bez drugiego montażu;
  3. druga ocena niższa niż pierwsza: wynikiem zostaje pierwsza wersja;
  4. najwyżej jeden dodatkowy montaż, także gdy druga ocena jest niska;
  5. krytyk bez reżysera: poprawki zamieniają plan automatyczny w scenariusz;
  6. podpis: „Scenariusz AI, ocena 8/10 (po poprawce)” i „Scenariusz automatyczny: brak odpowiedzi modelu”.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rezyser. Wczytaj skill claude-api (Python). Wykonaj zadanie 11.3 z Pomiary/PLAN_EDITY_11_REZYSER.md; otwórz src/rezyser.py, src/render.py, src/komunikaty.py, Pomiary/arkusz.py, tests/test_rezyser.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```
- **Commit:** `rezyser: krytyk i poprawka`

### [Task 11.4: Pomiar na prawdziwym modelu]
- **Objective:** `Pomiary/measure_rezyser.py`, wynik w `outputs/pomiar_rezyser.json`, arkusze i próbny edit.
- **Context/Inputs:**
  - materiały jak w pomiarze części 10 (stała próbka plus wycinki, słowa, napis pionowy, flaga, plansza, znak);
  - bez `ANTHROPIC_API_KEY` w środowisku pomiar zapisuje `{"pominiety": "brak klucza"}` i kończy się kodem 0;
  - przed pierwszym wywołaniem wypisz szacunek kosztu z `koszt_usd` dla przewidywanych tokenów;
  - **Sekcja A** (5 wzorów): montaż automatyczny i montaż z AI. Dla obu: ocena krytyka (automat też oceniany, dla porównania), liczba ujęć, użyte materiały, liczba ostrzeżeń scenariusza, tokeny, koszt, czas zegara;
  - **Sekcja C:** `outputs/porownanie_rezyser_<wzor>_auto.png` i `outputs/porownanie_rezyser_<wzor>_ai.png`, do tego próbny edit `outputs/rezyser_0923.mp4`;
  - `render.uruchom_ffmpeg` z limitem 900 s na wywołanie.
- **Constraints:** progi:
  - A: scenariusz poprawny (bez przejścia na automat) na co najmniej 4 z 5 wzorów, koszt jednego editu z AI poniżej 1 $;
  - C: pliki powstały, a werdykt wydaje właściciel. Ocena krytyka to tylko dodatek, bo model ocenia sam siebie.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot, gałąź rezyser. Wykonaj zadanie 11.4 z Pomiary/PLAN_EDITY_11_REZYSER.md; otwórz src/rezyser.py, src/render.py, Pomiary/arkusz.py, Pomiary/measure_dynamika.py jako wzór układu. Weryfikacja: python Pomiary/measure_rezyser.py
```
- **Commit:** `Pomiary: pomiar reżysera`

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A w progach, łączny koszt pomiaru w raporcie, arkusze i próbny edit ocenione przez właściciela.
- Po wdrożeniu z kluczem na serwerze podpis editu z Telegrama ma linię o scenariuszu AI, a `/status` pokazuje AI włączone. Każde odstępstwo zapisz jednym zdaniem w `ROZWOJ.md`.

## Commity
1. `rezyser: konfiguracja i wywołanie modelu`
2. `rezyser: scenariusz w renderze`
3. `rezyser: krytyk i poprawka`
4. `Pomiary: pomiar reżysera`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 11 według Pomiary/PLAN_EDITY_11_REZYSER.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru ani `.env`. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..rezyser`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `outputs/pomiar_rezyser.json`: odsetek poprawnych scenariuszy, koszt na edit, oceny krytyka. Pomiaru nie uruchamiaj drugi raz bez zgody właściciela, bo kosztuje.
3. Arkusze auto i AI dla każdego wzoru: czy AI wybiera lepsze otwarcie, fragmenty klipów i kolaże.
4. `src/rezyser.py`: żądanie zgodne z kontraktem (model z `.env`, adaptive, schemat, fallbacks), klucz nigdzie nie wypisywany, każdy błąd kończy się automatem, a nie przerwanym montażem.
5. `src/render.py`: bez `--ai` polecenia bez zmian, najwyżej jeden dodatkowy montaż.
