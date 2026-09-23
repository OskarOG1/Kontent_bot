# Część 4: biblioteka muzyki i dobór po tempie

**Zależy od:** części 3 (commit `bot: montaż po /gotowe`).
**Efekt:** render sam wybiera z `dane/muzyka/` utwór o tempie najbliższym wzorowi (z uwzględnieniem oktawy) i jego najmocniejszy fragment; licencja nie jest warunkiem doboru (edity trafiają na TikTok, decyzja właściciela 2026-09-22, `PLAN_EDITY_0_MAPA.md` decyzja 6). Gdy utwór ma wpis w `licencje.csv`, podpis wiadomości z wynikiem dostaje dane licencji do wklejenia pod postem; bez wpisu podpis pomija tę linię.
**Nowe pliki:** `src/music.py`, `tests/test_muzyka.py`, `Pomiary/measure_muzyka.py`.
**Zmieniane:** `src/render.py` (utwór opcjonalny), `src/analyze.py` (parametr `start_bpm` w `analizuj_rytm`), `src/bot.py`, `src/komunikaty.py`, `tests/generuj.py` (głośność kliku), `tests/test_render.py`, `tests/test_bot.py`.
**Od właściciela:** 5 do 15 utworów w `dane/muzyka/`; `dane/muzyka/licencje.csv` opcjonalny, tylko dla utworów, które mają dostać podpis z tytułem i autorem.
**Gałąź:** `muzyka` od `main` po scaleniu części 3.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_4_MUZYKA.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Na koniec uruchom pomiar i zdaj krótki raport.
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
`main` zawiera commit `bot: montaż po /gotowe` (część 3 po odbiorze i scaleniu), a `python -m pytest -q` przechodzi. Utwórz gałąź `muzyka` od `main`. Inaczej zatrzymaj się i zapytaj.

## Kontrakt z części 2 i 3 (streszczenie)
- `analyze.analizuj_rytm(sciezka) -> (tempo_bpm | None, uderzenia_s)` (analyze.py:123 w `0e84cba`): dekoduje przez `analyze.zdekoduj_do_wav(sciezka, cel)` (112) do WAV mono 22050 Hz (`CZESTOTLIWOSC_ANALIZY`), liczy uderzenia ze stałą `START_BPM = 150.0` (dobraną pod szybkie wzory, patrz `ROZWOJ.md`) i doprecyzowuje je na obwiedni (`doprecyzuj_uderzenia`). `analyze.czas_z_pozycji(p, uderzenia)`.
- `wzor.json`: `tempo_bpm`, `ciecia_uderzenia` (pierwsza pozycja `c_0` bywa ujemna), `koniec_uderzenia`, `zrodlo.czas_s`; pola rytmu bywają puste.
- `render.plan_ujec(wzor, uderzenia_utworu, materialy, fps, start_uderzenie=None)`; `render.renderuj(...)` i CLI z wymaganym dziś `--utwor`; podsumowanie JSON ma pole `utwor` z `plik` i `start_s`.
- Bot przekazuje dziś `--utwor dane/muzyka/staly.mp3` i odmawia montażu bez tego pliku.

## Kontrakty ustalane w tej części

**`dane/muzyka/licencje.csv`** (opcjonalny, tylko dla podpisu): nagłówek `plik;tytul;autor;zrodlo;licencja;podpis`. Separator `;` albo `,` (wykrywany), UTF-8 z BOM albo bez, bo plik będzie edytowany w Excelu. `podpis` to gotowy tekst pod post, może być pusty. Brak pliku albo brak wpisu dla utworu nie wyklucza go z doboru, tylko pomija dane licencji w podpisie.

**`dane/muzyka/indeks.json`**
```json
{"wersja": 1, "utwory": [{"plik": "epic_01.mp3", "rozmiar": 4812345, "zmieniony": 1758450000.0,
  "czas_s": 142.3, "tempo_bpm": 128.1, "uderzenia_s": [0.42, 0.89], "energia_uderzen": [0.071]}]}
```
`energia_uderzen[i]` to RMS dźwięku między uderzeniem i oraz i+1, więc lista jest o jeden krótsza od `uderzenia_s`. Liczona z tego samego WAV co uderzenia (`analyze.zdekoduj_do_wav`). Dane licencji nie trafiają do indeksu, czyta się je przy każdym doborze, więc poprawka w CSV działa od razu.

**Funkcje:**
- `analyze.analizuj_rytm(sciezka, start_bpm: float = START_BPM)`: nowy parametr opcjonalny; wywołania bez niego działają jak dotąd, więc wzory zostają przy 150. Indeks muzyki liczy tempo z `start_bpm=120`, bo utwory nie muszą być szybkie, a 150 przyciąga pomyłki 3:2; pomiar B pokaże, czy to słuszne.
- `music.indeksuj(katalog: Path) -> dict`: analizuje nowe i zmienione pliki (inny rozmiar albo czas modyfikacji), usuwa wpisy plików skasowanych, zapisuje indeks atomowo. Przyjmuje mp3, wav, m4a, ogg, flac oraz mp4 (ścieżka dźwiękowa z wideo, np. dźwięk zapisany z TikToka jak `MR.mp4`, który już leży w bibliotece). Plik bez ścieżki dźwiękowej pomija z ostrzeżeniem w logu, a reszta indeksu powstaje normalnie (test: katalog z mp4 bez dźwięku i jednym klikiem mp3 daje indeks z samym klikiem).
- `music.wczytaj_licencje(katalog: Path) -> dict[str, dict]`, klucz to nazwa pliku.
- `music.wybierz_utwor(wzor: dict, indeks: dict, licencje: dict) -> dict`:
```json
{"plik": "epic_01.mp3", "mnoznik": 2.0, "uderzenia_s": [0.42, 0.655, 0.89], "start_uderzenie": 17, "odleglosc_bpm": 0.8,
 "licencja": {"tytul": "Epic 01", "autor": "Autor", "licencja": "CC BY 4.0", "podpis": "Muzyka: ..."}}
```
Pole `licencja` jest `null`, gdy utwór nie ma wpisu w `licencje.csv` (brak pliku CSV liczy się jak brak wpisu dla każdego utworu).

Zasady:
  - Kandydat ma znane tempo i mieści całe okno wzoru na siatce uderzeń bez ekstrapolacji na końcu. Wpis w `licencje.csv` nie jest warunkiem.
  - Odległość tempa `b` od tempa wzoru `T` to minimum z `|b − T|`, `|2b − T|`, `|b/2 − T|`. Mnożnik 2 zagęszcza siatkę (środki między uderzeniami; energia połówki równa energii uderzenia), mnożnik 0,5 bierze co drugie uderzenie od indeksu 0. `uderzenia_s` w wyniku są już po tej korekcie i idą prosto do `plan_ujec`.
  - `start_uderzenie`: s z najwyższą średnią energią uderzeń w oknie od `s + c_0` do `s + koniec_uderzenia`, przy warunku nieujemnego `czas_z_pozycji(s + c_0)`. Remis: najmniejsze s.
  - Remis odległości: pierwszy alfabetycznie. Wzór bez tempa: pierwszy alfabetycznie kandydat nie krótszy niż wzór, mnożnik 1, `start_uderzenie` puste.
  - Brak kandydata: `ValueError` z liczbą odrzuconych z każdego powodu (brak tempa, za krótki).
- CLI: `python src/music.py indeksuj [--katalog dane/muzyka]` drukuje tabelę (plik, czas, tempo, licencja tak albo nie) i liczbę przeanalizowanych plików; `python src/music.py wybierz --wzor <wzor.json> [--katalog ...]` drukuje wybór.
- Render: `--utwor` staje się opcjonalny; bez niego render wywołuje `indeksuj` i `wybierz_utwor` dla katalogu z nowego parametru `--muzyka`. Pole `utwor` podsumowania dostaje `tytul`, `autor`, `licencja`, `podpis`, `tempo_bpm`, `mnoznik`, `start_s`.

## Zadania

### [Task 4.1: Indeks i licencje]
- **Objective:** `music.indeksuj`, `music.wczytaj_licencje`, CLI `indeksuj`, parametr głośności kliku w generatorze.
- **Context/Inputs:** kontrakty powyżej; `src/analyze.py` (`zdekoduj_do_wav` i `analizuj_rytm`, do której dochodzi parametr `start_bpm`). Przy okazji: `warnings.filterwarnings("ignore")` na początku `analizuj_rytm` wycisza ostrzeżenia w całym procesie, także w testach; zawęź to do bloku `warnings.catch_warnings()` wokół wywołań librosy (`ROZWOJ.md`, „Znane problemy” 0e). Do `tests/generuj.py` dopisz opcjonalny parametr `klik(..., glosnosc=None)`: lista par (od sekundy, mnożnik amplitudy); domyślne zachowanie bez zmian.
- **Constraints:** `analizuj_rytm` bez nowego parametru działa jak dotąd (dotychczasowe testy analizy bez zmian). Testy: CSV z BOM, średnikami i polskimi znakami czyta się poprawnie, wersja z przecinkami też; drugi `indeksuj` bez zmian w katalogu analizuje 0 plików, zmiana czasu modyfikacji jednego pliku daje 1; skasowany plik znika z indeksu; wszystkie liczby w indeksie to typy wbudowane.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.1 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/analyze.py i tests/generuj.py. Weryfikacja: python -m pytest -q tests/test_muzyka.py
```

### [Task 4.2: Dobór utworu]
- **Objective:** `music.wybierz_utwor` i CLI `wybierz`.
- **Context/Inputs:** zasady z kontraktu; `analyze.czas_z_pozycji`.
- **Constraints:** testy: utwór 70 BPM przy wzorze 140 dostaje mnożnik 2, dwa razy więcej uderzeń (z dokładnością do 1) i odległość 0; utwór 128 przy wzorze 64 dostaje mnożnik 0,5; klik 60 s z mnożnikiem głośności 0,1 do 30 s i 1,0 dalej, wzór na 16 uderzeń: start wypada po 30 s; dwa utwory w tej samej odległości: wygrywa pierwszy alfabetycznie; brak kandydata: `ValueError` z powodami; dwa wywołania na tych samych danych dają identyczny wynik.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.2 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/music.py i src/analyze.py tylko w miejscu czas_z_pozycji. Weryfikacja: python -m pytest -q tests/test_muzyka.py
```

### [Task 4.3: Render i bot]
- **Objective:** render bez `--utwor` bierze utwór z biblioteki; bot pokazuje licencję w podpisie, gdy jest.
- **Context/Inputs:** `src/render.py` (miejsce wyboru utworu i wywołania `plan_ujec`), `src/bot.py` (zadanie montażu, `/status`, `/gotowe`), `src/komunikaty.py`. Bot przestaje przekazywać `--utwor` i wymagać `staly.mp3`, przekazuje `--muzyka <katalog_danych>/muzyka`. Podpis dostaje linię „Muzyka: tytuł, autor. Licencja: …” i `podpis` tylko wtedy, gdy wybrany utwór ma wpis w `licencje.csv` (pole `licencja` niepuste); bez wpisu podpis nie wspomina o muzyce. `/status` dostaje wiersz „Muzyka: N utworów, M z licencją”. Brak kandydata (za mało utworów albo żaden nie pasuje tempem czy długością) kończy render błędem, a bot pokazuje jego treść.
- **Constraints:** `--utwor` dalej działa (pomiar części 3 z niego korzysta). Testy: render bez `--utwor` na katalogu z jednym klikiem mp3 i wpisem w CSV daje podsumowanie z polami licencji; render bez `--utwor` i bez `licencje.csv` (albo bez wpisu dla wybranego pliku) daje podsumowanie z `licencja: null`, bez błędu; render z `--utwor` działa jak dotąd; bot z podmienionym `uruchom` wysyła podpis z autorem utworu, gdy licencja jest, i bez linii o muzyce, gdy jej nie ma.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.3 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/render.py, src/music.py, src/bot.py, src/komunikaty.py, tests/test_render.py, tests/test_bot.py. Weryfikacja: python -m pytest -q
```

### [Task 4.4: Pomiar]
- **Objective:** `Pomiary/measure_muzyka.py`, wynik w `outputs/pomiar_muzyka.json`.
- **Context/Inputs:** sekcja A: kliki od 60 do 180 BPM co 10; błąd tempa w % po uwzględnieniu oktawy i liczba pomyłek o oktawę. Sekcja B (gdy `dane/muzyka/` ma pliki): tabela utworów (czas, tempo przy `start_bpm` 120 i 150 obok siebie z oznaczeniem par różniących się o 3:2 albo 2:1 do odsłuchu, liczba uderzeń, czas indeksowania, licencja tak albo nie), a dla każdego wzoru z `dane/probki/wzory/` wybrany utwór, odległość, mnożnik i sekunda startu. Sekcja C: dwa przebiegi doboru dają to samo.
- **Constraints:** progi: A błąd do 2% dla wszystkich temp, C identyczność; B tylko raport.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 4.4 z Pomiary/PLAN_EDITY_4_MUZYKA.md; otwórz src/music.py, src/analyze.py, tests/generuj.py. Weryfikacja: python Pomiary/measure_muzyka.py
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- Pomiar A: błąd tempa do 2% po uwzględnieniu oktawy; C: dobór powtarzalny.
- Test ręczny (Ty): dwa wzory o wyraźnie różnym tempie dają różne utwory (jeśli biblioteka ma takie tempa), podpis zawiera autora i licencję dla utworów z wpisem w CSV, `/status` liczy utwory.

## Commity
1. `muzyka: indeks, licencje i dobór po tempie`
2. `render: utwór z biblioteki`
3. `bot: podpis muzyki`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 4 według Pomiary/PLAN_EDITY_4_MUZYKA.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline main..muzyka`, `python -m pytest -q`, stan i znane problemy w `Pomiary/ROZWOJ.md`.
2. `python Pomiary/measure_muzyka.py`, sekcje A i C wobec progów, tabela B: czy dobór ma sens przy tempach wzorów i które `start_bpm` zostaje dla indeksu.
3. `src/music.py`: korekta oktawy (zagęszczenie siatki i co drugie uderzenie), warunek mieszczenia okna, wybór startu po energii, wykrywanie separatora i BOM w CSV.
4. `src/render.py`: ścieżka bez `--utwor` i pola licencji w podsumowaniu.
