# Część 9: fabryka (restart, biblioteka wzorów, warianty, partie)

**Zależy od:** części 4 i 8 (wymagane). Najlepiej wykonać ją po częściach 5 i 6: wtedy parametry renderu i podpisy są kompletne. Jeśli którejś brakuje, pomijasz jej parametry (`--sila-koloru`, `--styl-tekstu`, `--pozycja-tekstu`).
**Gałąź:** `fabryka` od `main` po scaleniu poprzednich części.
**Efekt:**
- bot przeżywa restart: zlecone montaże i analizy wracają do kolejki;
- wzorów jest wiele, a aktywny wybierasz z listy, z nazwami, zamiast zawsze brać najnowszy;
- jeden projekt daje kilka wariantów albo po jednym editcie na każdy wzór;
- `/ponow` montuje ostatni projekt jeszcze raz, bez ponownego wysyłania materiałów.

**Dlaczego:** to elementy, które zamieniają montaż pojedynczego editu w fabrykę (przegląd 2026-09-23). Dziś kolejka i stan zbierania żyją tylko w pamięci, więc restart w trakcie montażu zostawia projekt w stanie `renderowanie` bez żadnego komunikatu. Bot zna tylko najnowszy wzór, a każdy nowy edit wymaga ponownego wysłania materiałów.
**Nowe pliki:** `tests/test_fabryka.py`, `Pomiary/measure_fabryka.py`.
**Zmieniane:** `src/bot.py`, `src/komunikaty.py`, `src/magazyn.py`, `src/render.py`, `tests/test_bot.py`, `tests/test_magazyn.py`, `tests/test_render.py`, `tests/pomocnicze.py`.
**Od właściciela:** nic. Test ręczny z restartem kontenera w trakcie montażu.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_9_FABRYKA.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej w zadaniu. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commity `bot: muzyka z biblioteki` (część 4) i `bot: nakładka i plansza wzoru` (część 8), a `python -m pytest -q` przechodzi. Zanotuj w `ROZWOJ.md`, czy są już części 5 i 6. Utwórz gałąź `fabryka` od `main`. Inaczej zatrzymaj się i zapytaj.

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

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar: A w progach, B zaraportowane, arkusze C powstały.
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
