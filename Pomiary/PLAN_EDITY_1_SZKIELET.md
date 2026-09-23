# Część 1: szkielet bota

**Status 2026-09-22:** wykonana (commity `34519d2` do `84aaf6c`, poprawki `d6a49bf` i `3f60ead`), 33 testy, pomiar w progach. Odbiór 2026-09-22 (Opus): OK, szczegóły w `ROZWOJ.md`. Repo na GitHubie powstało po tej części, więc punkt 2 odbioru sprawdza wyciek tokenu, nie brak zdalnego repo.
**Zależy od:** nic. W katalogu są `CLAUDE.md`, `Pomiary/`, `.gitignore` i `.env`.
**Istniejące, nie nadpisuj:** `.env` (prawdziwy token bota i ID właściciela), `.gitignore` (już ignoruje `.env`, `dane/`, `outputs/`, `Pomiary/`, `venv/` i cache).
**Efekt:** bot (long polling) przyjmuje od właściciela wzór mp4 i materiały do projektu, obcych ignoruje, a kolejka ciężkich zadań czeka na analizę (część 2) i render (część 3).
**Nowe pliki:** `.env.example`, `requirements.txt`, `requirements-test.txt`, `README.md`, `src/konfiguracja.py`, `src/komunikaty.py`, `src/magazyn.py`, `src/kolejka.py`, `src/bot.py`, `tests/conftest.py`, `tests/pomocnicze.py`, `tests/test_konfiguracja.py`, `tests/test_magazyn.py`, `tests/test_kolejka.py`, `tests/test_bot.py`, `Pomiary/measure_szkielet.py`.
**Wiedza o API:** `Pomiary/TELEGRAM_BOT_API.md`. Dokumentacji nie pobieraj z sieci.

Prompt startowy (cała część w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj po kolei zadania z Pomiary/PLAN_EDITY_1_SZKIELET.md, zaczynając od „Stan wejściowy”. Otwieraj tylko pliki wymienione w zadaniu oraz Pomiary/TELEGRAM_BOT_API.md. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie z sekcji „Commity”. Na koniec uruchom pomiar i zdaj krótki raport.
```

## WSPÓLNE (ten sam blok w każdej części)
- Plan pisany 2026-09-21, zanim powstał kod. Jeżeli nazwy lub kontrakty z poprzednich części nie zgadzają się z tym, co zastaniesz, zatrzymaj się i zapytaj zamiast zgadywać. Otwieraj tylko pliki wymienione w zadaniu, nie przeszukuj repo ani dysku.
- Po co: bot na Telegramie montuje edit wideo 9:16 z materiałów właściciela według struktury wzorcowego editu (cięcia na uderzeniach, tempo, kolorystyka, sposób podania tekstu), z muzyką z biblioteki właściciela w `dane/muzyka/` (licencja nie jest warunkiem, decyzja 6 w mapie). Z wzoru bierzemy tylko strukturę i styl: jego obraz ani dźwięk nigdy nie trafiają do wyniku.
- Środowisko: lokalnie Windows 11, Python 3.13, ffmpeg i ffprobe 8.1 w PATH, brak Dockera. Serwer: Docker (obraz Debian) na Ubuntu 22.04. Ścieżki przez pathlib, procesy jako lista argumentów, bez powłoki.
- Reguły repo:
  1. Każda zmiana ma pomiar w `Pomiary/measure_<temat>.py`, tylko tam wolno pisać komentarze. Skrypt zaczyna od `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` i zapisuje wyniki do `outputs/` po każdej sekcji.
  2. Zero komentarzy i docstringów w `src/` i `tests/`.
  3. Nazwy funkcji bez `_` na początku, nazewnictwo po polsku (moduły `bot`, `analyze`, `music`, `render` zachowują nazwy z KONTEKST).
  4. Komunikaty bota, README i commity bez myślników i półpauz wewnątrz zdań.
  5. Commity bez wzmianek o AI i bez Co-Authored-By. Zdalne repo `origin` na GitHubie (dodane po części 1): push tylko na prośbę właściciela, a przed nim sprawdź, że `.env`, `dane/`, `outputs/` i `Pomiary/` nie są w indeksie.
  6. Każde wywołanie ffmpeg i ffprobe z zamkniętym stdin (`-nostdin` albo `stdin=DEVNULL`), inaczej proces potomny potrafi zawisnąć.
- Testy: `python -m pytest -q` z katalogu głównego, cały zestaw poniżej 60 s. Media testowe generowane w locie w małej rozdzielczości (270x480), nigdy z `dane/`.
- Raport na koniec sesji: wniosek, liczby z pomiaru, problemy. Bez opisu drogi.

## Stan wejściowy
`git status` zgłasza brak repo; `.gitignore` zawiera `.env`; `python --version` to 3.13; `ffmpeg -version` działa. Jeżeli repo ma już commity albo zdalne repozytorium, zatrzymaj się i zapytaj.

## Kontrakty ustalane w tej części
Kolejne części na nich polegają. Zmiana nazwy lub kształtu wymaga aktualizacji planów 2 do 7.

**Układ danych** (`KATALOG_DANYCH`, domyślnie `dane/` w katalogu repo):
```
dane/wzory/<wzor_id>/zrodlo.<ext>
dane/wzory/<wzor_id>/wzor.json                          (część 2)
dane/projekty/<projekt_id>/projekt.json
dane/projekty/<projekt_id>/materialy/<message_id:010d>_<file_unique_id>.<ext>
dane/projekty/<projekt_id>/wynik.mp4 oraz wynik.json    (część 3)
dane/muzyka/                                            (części 3 i 4)
```
Identyfikatory mają postać `RRRRMMDD_GGMMSS`; kolizja w tej samej sekundzie dostaje przyrostek `_2`, `_3`.

**projekt.json**
```json
{"id": "20260921_153012", "utworzony": "2026-09-21T15:30:12", "stan": "zbieranie",
 "teksty": [{"message_id": 57, "tekst": "11 listopada"}], "wzor_id": null, "wynik": null, "blad": null}
```
`stan` przyjmuje wartości `zbieranie`, `w_kolejce`, `renderowanie`, `gotowy`, `blad`, `anulowany`. Listy materiałów celowo nie ma w pliku: wynika z zawartości `materialy/`, więc równoległe zapisy albumu nie gubią wpisów.

**Typy materiałów:** zdjęcie: jpg, jpeg, png, webp, heic, heif; klip: mp4, mov, m4v, webm, mkv. Rozszerzenie z nazwy pliku, a gdy nazwy brak, z MIME. `photo` z Telegrama to jpg, `video` i `animation` bez nazwy to mp4.

**Funkcje:**
- `konfiguracja.wczytaj(srodowisko: Mapping[str, str] | None = None) -> Konfiguracja`, pola: `token`, `wlasciciel_id: int`, `katalog_danych: Path`, `limit_pobierania_mb: int = 20`, `limit_wysylki_mb: int = 50`.
- `magazyn.nowy_projekt(katalog_danych) -> Path`, `magazyn.nowy_wzor(katalog_danych) -> Path`.
- `magazyn.sciezka_materialu(katalog_projektu, message_id, file_unique_id, rozszerzenie) -> Path`.
- `magazyn.typ_pliku(nazwa: str | None, mime: str | None) -> str | None`, wynik `"zdjecie"`, `"klip"` albo `None`.
- `magazyn.lista_materialow(katalog_projektu) -> list[dict]`, wpis `{"plik": Path, "typ": str, "message_id": int}`, rosnąco po `message_id`, bez plików `.part`.
- `magazyn.wczytaj_projekt(katalog_projektu) -> dict`, `magazyn.zapisz_projekt(katalog_projektu, dane) -> None`.
- `kolejka.uruchom(argumenty: list[str], limit_s: float | None = None, katalog: Path | None = None) -> Wynik` (async); `Wynik` ma pola `kod`, `stdout`, `stderr`, `czas_s`, `przekroczono_czas`.
- `kolejka.Kolejka`: `start()`, `async dodaj(zadanie) -> int` (pozycja, 1 znaczy „rusza teraz”), `dlugosc() -> int`. Zadanie to bezargumentowa funkcja async.
- `bot.utworz_dispatcher(konf, kolejka) -> Dispatcher` (testy budują bota bez sieci), `bot.pobierz_plik(bot, file_id, cel: Path)` (jedyne miejsce pobierania, część 7 podmieni je na lokalny serwer), `bot.main()`.

## Zadania

### [Task 1.1: Repo i konfiguracja]
- **Objective:** lokalne repo git (gałąź `main`, bez zdalnego repozytorium) z plikami startowymi i modułem `konfiguracja`.
- **Context/Inputs:** `.gitignore` już istnieje, zostaw go. Przed pierwszym commitem `git status` nie może pokazywać `.env`. `requirements.txt`: aiogram 3.x (najnowsza), python-dotenv, psutil. `requirements-test.txt`: pytest, pytest-asyncio, tryb asyncio `auto` w konfiguracji pytest trzymanej w repo. `.env.example`: te same klucze co w `.env` (`BOT_TOKEN`, `OWNER_ID`, `KATALOG_DANYCH`, `LIMIT_POBIERANIA_MB`, `LIMIT_WYSYLKI_MB`), ale z pustymi albo przykładowymi wartościami. Nie kopiuj `.env` i nie otwieraj go: wartości z niego nie mogą trafić do żadnego pliku w repo ani do raportu. README: uruchomienie lokalne w kilku krokach (venv, instalacja, `.env`, `python src/bot.py`, testy). `tests/conftest.py` dodaje `src` do `sys.path`.
- **Constraints:** brak `BOT_TOKEN` albo `OWNER_ID`, a także `OWNER_ID` niebędące liczbą, daje wyjątek z nazwą zmiennej w treści; `main()` zamienia go na jedną linię na stderr bez tracebacku. Względny `KATALOG_DANYCH` liczony od katalogu repo, nie od bieżącego katalogu. Prawdziwy `.env` leży już w katalogu repo, więc wczytanie pliku `.env` może nastąpić tylko wtedy, gdy `srodowisko` nie zostało podane (czyli w `main()`); testy podają słownik i nie mogą zależeć od tego pliku. Testy: trzy przypadki błędów (muszą przechodzić mimo istniejącego `.env`) oraz przypadek z `monkeypatch.chdir(tmp_path)`, w którym katalog danych dalej wskazuje repo.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 1.1 z Pomiary/PLAN_EDITY_1_SZKIELET.md. Weryfikacja: python -m pytest -q tests/test_konfiguracja.py
```

### [Task 1.2: Magazyn]
- **Objective:** `src/magazyn.py` z funkcjami z kontraktu i `tests/test_magazyn.py`.
- **Context/Inputs:** kontrakt „Układ danych”, „projekt.json”, „Typy materiałów”, sygnatury `magazyn.*`. Nowy projekt dostaje `projekt.json` ze stanem `zbieranie` i pustą listą `teksty`.
- **Constraints:** bez zależności od aiogram, bo moduł działa też w CLI renderu. Testy mają złapać: dwa `nowy_projekt` w tej samej sekundzie dają różne katalogi (podmień zegar); `lista_materialow` pomija `.part` i nieznane rozszerzenia, a `message_id` 9 stawia przed 10; `typ_pliku("IMG_1.HEIC", None)` to zdjęcie, `typ_pliku(None, "video/quicktime")` to klip, `application/pdf` to `None`; `message_id` 0 z dwoma różnymi `file_unique_id` daje dwie ścieżki; `zapisz_projekt` pisze do pliku obok i podmienia przez `os.replace`, więc przerwany zapis nie zostawia uciętego JSON, a po udanym nie zostaje plik tymczasowy.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 1.2 z Pomiary/PLAN_EDITY_1_SZKIELET.md. Weryfikacja: python -m pytest -q tests/test_magazyn.py
```

### [Task 1.3: Kolejka i procesy]
- **Objective:** `src/kolejka.py` z `uruchom` i `Kolejka` (jeden pracownik) oraz `tests/test_kolejka.py`.
- **Context/Inputs:** analiza i render będą osobnymi procesami Pythona, które same uruchamiają ffmpeg. Limit czasu musi więc zabić całe drzewo procesów (psutil), nie tylko rodzica.
- **Constraints:** testy: (a) podczas `uruchom` na procesie śpiącym 2 s korutyna tykająca co 10 ms nie widzi opóźnienia ponad 100 ms; (b) proces uruchamiający dziecko, które śpi 30 s, po `limit_s=1` daje `przekroczono_czas=True`, a ani rodzic, ani dziecko nie żyją (`psutil.pid_exists`); (c) proces czytający stdin kończy się od razu; (d) zadanie rzucające wyjątek nie zatrzymuje pracownika, następne się wykonuje, a wyjątek trafia do logu; (e) trzy zadania dodane naraz dostają pozycje 1, 2, 3 i nigdy nie biegną dwa jednocześnie.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 1.3 z Pomiary/PLAN_EDITY_1_SZKIELET.md. Weryfikacja: python -m pytest -q tests/test_kolejka.py
```

### [Task 1.4: Bot]
- **Objective:** `src/bot.py`, `src/komunikaty.py`, `tests/pomocnicze.py`, `tests/test_bot.py`: handlery aiogram 3 z dostępem tylko dla właściciela.
- **Context/Inputs:**
  - Komendy, ustawiane też przez `setMyCommands` przy starcie: `/start` (pomoc), `/wzor`, `/nowy`, `/gotowe`, `/anuluj`, `/status`. Stany FSM (domyślny MemoryStorage): `czekam_na_wzor` oraz `zbieram` z `projekt_id` w danych stanu.
  - `/wzor`: następny plik wideo (`video`, `animation`, `document` z MIME `video/*`) trafia do `dane/wzory/<id>/zrodlo.<ext>`, odpowiedź potwierdza zapis. Inny typ w tym stanie: komunikat, stan trwa.
  - `/nowy`: nowy projekt i stan `zbieram`. Przyjmowane: `photo` (największy rozmiar), `document` z MIME `image/*` albo `video/*`, `video`, `animation`. Po zapisie reakcja 👍, dla albumu jedna na `media_group_id`; błąd reakcji tylko do logu.
  - Zwykły tekst (nie komenda) w stanie `zbieram` dopisuje wpis do `teksty` w `projekt.json`, posortowany po `message_id`. Każdy odczyt z zapisem `projekt.json` pod jedną blokadą asyncio, bo aiogram obsługuje aktualizacje równolegle.
  - Plik poza stanami `zbieram` i `czekam_na_wzor`: komunikat „najpierw /nowy albo /wzor”, nic nie zapisujemy.
  - Znany `file_size` powyżej `limit_pobierania_mb`: komunikat z rozmiarem i limitem, bez pobierania. Błąd pobierania z powodu rozmiaru daje ten sam komunikat.
  - `pobierz_plik` zapisuje do `<cel>.part` i zmienia nazwę po sukcesie, przy błędzie usuwa `.part`.
  - `/gotowe`: odczekuje około 1 s (reszta albumu może być jeszcze w drodze do handlerów), potem czeka, aż skończą się trwające pobrania tego projektu, najwyżej 120 s. Licznik pobrań rośnie przed pierwszym `await` w handlerze pliku. Zero materiałów: komunikat, stan `zbieram` trwa. W przeciwnym razie projekt dostaje `stan` `w_kolejce`, odpowiedź podaje liczbę zdjęć, klipów i linii tekstu, stan FSM znika. Montaż podepnie część 3.
  - `/anuluj`: projekt `anulowany`, stan FSM znika, pliki zostają.
  - `/status`: stan FSM, projekt z liczbą materiałów, długość kolejki, liczba wzorów.
  - Obcy użytkownik: zero odpowiedzi, zero plików, zero zmian stanu, zarówno dla `message`, jak i `edited_message`.
  - Kotwice aiogram 3 (sprawdź w zainstalowanej wersji): `Bot.download(plik, destination=...)`, `Message.react(...)`, w testach `Dispatcher.feed_update(bot, update)` i fałszywa sesja jako podklasa `BaseSession` z `aiogram.client.session.base` z własnym `make_request`, który zapisuje wywołania do listy.
- **Constraints:** komunikaty jako stałe w `komunikaty.py`, wysyłane jako zwykły tekst bez `parse_mode`, bo nazwy plików z `_` i `*` psują Markdown. Liczby dziesiętne w komunikatach z przecinkiem. W handlerach nic blokującego (`subprocess.run`, `time.sleep`, synchroniczne czytanie dużych plików). Bez własnego ponawiania zapytań. Testy z podmienionym pobieraniem:
  1. obcy `/start`: 0 wywołań API, w `dane` nic nie powstaje;
  2. właściciel `/start`: dokładnie 1 `sendMessage`;
  3. zdjęcie bez `/nowy`: komunikat, 0 plików;
  4. `/nowy`, potem `photo`, `document` `image/jpeg` o nazwie `IMG_1.HEIC` i `video`: 3 pliki z rozszerzeniami jpg, heic, mp4 w kolejności `message_id`;
  5. album 3 zdjęć: 3 pliki i dokładnie 1 `setMessageReaction`;
  6. `document` z `file_size` 25 MB: komunikat o limicie, pobieranie niewywołane;
  7. `/gotowe`, gdy 3 pobrania jeszcze trwają (podmienione pobieranie czeka 0,5 s): odpowiedź liczy 3 materiały;
  8. `/gotowe` bez materiałów: komunikat, stan `zbieram` trwa;
  9. 20 wiadomości tekstowych naraz: 20 wpisów w `teksty` w kolejności `message_id`;
  10. `edited_message` od obcego: 0 wywołań API.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 1.4 z Pomiary/PLAN_EDITY_1_SZKIELET.md; otwórz też Pomiary/TELEGRAM_BOT_API.md i pliki src/konfiguracja.py, src/magazyn.py, src/kolejka.py. Weryfikacja: python -m pytest -q
```

### [Task 1.5: Pomiar]
- **Objective:** `Pomiary/measure_szkielet.py` z wynikiem w `outputs/pomiar_szkielet.json`.
- **Context/Inputs:** mierzy dwie ciche awarie tej części: zablokowaną pętlę zdarzeń i zgubione pliki albumu. Korzysta z `tests/pomocnicze.py`.
- **Constraints:** sekcja A: opóźnienie pętli zdarzeń (tykanie co 10 ms) podczas zadania w kolejce, które uruchamia proces śpiący 3 s; p50, p99, max w ms. Sekcja B: album 10 plików z losowym opóźnieniem pobierania od 0 do 1 s i `/gotowe` zaraz po ostatnim pliku, 20 powtórzeń; ile razy `/gotowe` policzyło 10 z 10. Sekcja C: narzut `uruchom` na procesie, który od razu się kończy, mediana w ms. Progi: A max poniżej 50 ms, B 20 z 20, C tylko do raportu.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 1.5 z Pomiary/PLAN_EDITY_1_SZKIELET.md; otwórz tests/pomocnicze.py. Weryfikacja: python Pomiary/measure_szkielet.py i odczyt outputs/pomiar_szkielet.json
```

## Gotowe, gdy
- `python -m pytest -q` przechodzi w całości.
- `outputs/pomiar_szkielet.json`: A max poniżej 50 ms, B 20 z 20.
- Test ręczny (Ty, około 3 minut): `.env` jest gotowy, `python src/bot.py`. `/start` odpowiada, menu komend jest widoczne. `/nowy`, album 5 zdjęć wysłanych jako pliki i 1 klip: w `dane/projekty/<id>/materialy/` leży 6 plików, na albumie jedna reakcja. `/gotowe` podaje 5 zdjęć i 1 klip. Potem `OWNER_ID=1` w `.env` i restart: bot nie reaguje na nic. Na koniec przywróć swoje ID.

## Commity
1. `repo: szkielet i konfiguracja`
2. `magazyn: projekty, wzory i materiały`
3. `kolejka: procesy w tle i jeden pracownik`
4. `bot: dostęp właściciela, wzór i materiały`

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 1 według Pomiary/PLAN_EDITY_1_SZKIELET.md, sekcje „Gotowe, gdy” i „Odbiór”. Nie poprawiaj kodu i nie otwieraj plików spoza kroków odbioru. Werdykt: OK albo lista poprawek (plik:linia, co jest źle, jaki test to złapie).
```
1. `git log --oneline` (4 commity z listy), `python -m pytest -q`.
2. Sekrety: `git log --all --oneline -S 8905898429` (numer bota z tokenu) nic nie zwraca, czyli token nie trafił do historii ani na GitHuba, także przez `.env.example`; `git ls-files` nie zawiera `.env`, `dane/`, `outputs/` ani `Pomiary/`.
3. `python Pomiary/measure_szkielet.py`, wynik wobec progów.
4. `src/bot.py`: gdzie działa filtr właściciela i czy obejmuje `edited_message`; czy w handlerach nie ma wywołań blokujących; czy nigdzie nie ustawiono `parse_mode`; jak `/gotowe` czeka na pobrania.
5. `src/kolejka.py`: zabijanie drzewa procesów po limicie, odporność pracownika na wyjątek, zamknięte stdin.
6. `src/komunikaty.py`: znaki `—`, `–` albo ` - ` wewnątrz zdań.
