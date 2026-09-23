# Część 7: wdrożenie na VPS

**Status (2026-09-22):** 7.1 i 7.2 wykonane i scalone do `main` (PR #2, `e9a4755`); obie usługi działają na `46.62.151.181` (Ubuntu 24.04, serwer współdzielony z produkcją innego projektu) z botem testowym. Odbiór (Opus): poprawki w zadaniu 7.3, w tym jedna blokująca: bot nie może czytać plików z wolumenu serwera Bot API, więc na serwerze nie przejdzie żadne pobranie.

**Zależy od:** części 2 (pierwsze wdrożenie: bot przyjmuje i analizuje wzory); render dochodzi po części 3. Po każdej kolejnej części wystarczy aktualizacja z punktu 9.
**Gałąź:** `wdrozenie` od `main`.
**Efekt:** bot działa w Dockerze na VPS (Ubuntu 22.04), sam wstaje po restarcie, a stare projekty są sprzątane.
**Kto:** zadania 7.1 (pliki Dockera i skrypt) i 7.2 (lokalny serwer Bot API) robi Sonnet lokalnie, kroki na serwerze robisz Ty, bo to praca z uprawnieniami na maszynie produkcyjnej. Zadanie 7.2 jest potrzebne od razu: prawdziwe wzory mają około 150 MB, klipy z telefonu często ponad 20 MB, a `.env` ma limity 2500 i 200 MB, których zwykłe Bot API nie obsłuży (pobieranie 20 MB, wysyłka 50 MB).

Prompt startowy (zadania 7.1 i 7.2 w jednej sesji):
```text
Katalog roboczy: C:\Dev\edity-bot. Wykonaj zadania 7.1 i 7.2 z Pomiary/PLAN_EDITY_7_WDROZENIE.md, zaczynając od „Stan wejściowy”. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym zadaniu. Otwieraj tylko pliki wymienione w zadaniu. Po każdym zadaniu uruchom jego weryfikację i zrób commit o nazwie podanej przy zadaniu. Kroków na serwerze nie wykonuj, należą do właściciela. Na koniec zdaj krótki raport.
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
`main` zawiera `0e84cba` (część 2 scalona), a `python -m pytest -q` przechodzi; utwórz gałąź `wdrozenie` od `main`. Jeśli część 3 jest już zrobiona (commit `bot: montaż po /gotowe`), wdrożenie obejmuje też render.

## Zadania

### [Task 7.1: Obraz, compose i skrypt wdrożenia]
- **Objective:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `wdroz.ps1` i sekcja „Wdrożenie” w README.
- **Context/Inputs:** obraz `python:3.13-slim` (ta sama wersja Pythona co lokalnie) z pakietami apt `ffmpeg`, `libgl1` i `libglib2.0-0` (scenedetect 0.7.1 wymaga pełnego `opencv-python`, patrz `ROZWOJ.md`); `NUMBA_CACHE_DIR` wskazuje katalog zapisywalny dla UID 1000 na wolumenie danych (np. `/app/dane/.cache/numba`), bo bez zapisywalnej pamięci podręcznej każda analiza płaci około 24 s kompilacji librosy; do obrazu trafiają `src/`, `tests/`, `zasoby/` (gdy istnieje), `requirements*.txt`; proces jako użytkownik nieuprzywilejowany o UID 1000; start `python src/bot.py`. Compose: jedna usługa `bot`, `env_file: .env`, wolumen `./dane:/app/dane`, `restart: unless-stopped`, limit `cpus` (domyślnie 2, łatwy do zmiany), logi `json-file` z rotacją (10 MB, 3 pliki), bez portów, bo bot używa pollingu. `.dockerignore`: `dane`, `outputs`, `Pomiary`, `.env`, `venv`, `.git`. Kod trafia na serwer bez GitHuba i bez gita na serwerze: `wdroz.ps1 -Serwer root@<adres>` (PowerShell, wbudowane w Windows 11 `ssh` i `scp`) pakuje gałąź `main` (`git archive main`), nigdy bieżącą gałąź, bo w tym samym katalogu może właśnie trwać praca nad kolejną częścią; zatrzymuje się z komunikatem, gdy lokalny `main` różni się od `origin/main` (najpierw synchronizacja po scaleniu PR), chyba że podano `-Wymus`; kopiuje archiwum do `/opt/edity-bot/`, a przez ssh usuwa stare katalogi kodu (`src/`, `tests/`, `zasoby/`), rozpakowuje archiwum, uruchamia `docker compose up -d --build` i pokazuje ostatnie 20 linii logu.
- **Constraints:** skrypt nigdy nie usuwa ani nie nadpisuje `dane/` i `.env` na serwerze (nie ma ich w archiwum; usuwanie dotyczy tylko wymienionych katalogów kodu). Lokalnie nie ma Dockera, więc obraz pierwszy raz zbuduje się na serwerze; sprawdź pliki uważnym czytaniem. Wersja ffmpeg w obrazie (Debian) różni się od lokalnej 8.1; testy uruchomione w kontenerze (krok 7 niżej) to wychwycą.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 7.1 z Pomiary/PLAN_EDITY_7_WDROZENIE.md; otwórz README.md i requirements.txt. Weryfikacja: przeczytaj gotowe pliki i wypisz w raporcie, co trafi do obrazu i co wdroz.ps1 robi na serwerze.
```
Commit: `wdrożenie: Docker, compose i skrypt wdroz.ps1`.

## Kroki na serwerze (Ty)
Zrobione 2026-09-22: kroki 1, 2, 4 (bez `licencje.csv`), 6 i 7 (71 z 71), ale z botem testowym, bo na serwer trafił lokalny `.env`. Zostają kroki 3 i 5 (główny bot), 8 i 10, najlepiej razem z punktami po zadaniu 7.3 na końcu tej sekcji.

Bot testowy `@local125_bot` już jest (2026-09-22): jego token stoi w lokalnym `.env`. Konfiguracja głównego bota dla serwera leży poza repo w `C:\Dev\edity-bot-serwer.env` (token głównego bota, ID, limity, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`), żeby żaden `git add` jej nie złapał. Główny bot po przejściu na serwer lokalny nie może równocześnie działać na zwykłym API, a dwie instancje z jednym tokenem wyrzucają się nawzajem.

1. `docker --version` i `docker compose version`; brak: instalacja Docker Engine według oficjalnej instrukcji dla Ubuntu 22.04.
2. Katalogi: `ssh root@<vps> "mkdir -p /opt/edity-bot/dane/wzory /opt/edity-bot/dane/projekty /opt/edity-bot/dane/muzyka && chown -R 1000:1000 /opt/edity-bot/dane"` (kontener pisze jako UID 1000).
3. Konfiguracja serwera: uzupełnij `TELEGRAM_API_URL` w `C:\Dev\edity-bot-serwer.env` adresem usługi serwera Bot API z `docker-compose.yml` (zadanie 7.2), potem `scp C:\Dev\edity-bot-serwer.env root@<vps>:/opt/edity-bot/.env`. Lokalny `.env` (bot testowy) nie ma i nie może mieć `TELEGRAM_API_URL`, bo bot szukałby serwera, którego na komputerze nie ma. Później plik `.env` zmieniasz na serwerze (np. `SILA_KOLORU` po części 5); skrypt wdrożenia go nie rusza.
4. Muzyka i `licencje.csv` z komputera: pojedyncze pliki `scp dane/muzyka/staly.mp3 root@<vps>:/opt/edity-bot/dane/muzyka/`, bo `scp -r dane/muzyka` przy istniejącym katalogu na serwerze zrobi `dane/muzyka/muzyka`. Źródłem prawdy dla `licencje.csv` zostaje Twój komputer.
5. Zatrzymaj każdą lokalną instancję głównego bota (lokalnie od teraz działa tylko `@local125_bot`). Dwie instancje z tym samym tokenem na pollingu wyrzucają się nawzajem (409 Conflict).
6. Przełączenie na serwer lokalny (akapit „Przełączenie” pod zadaniem 7.2), potem `.\wdroz.ps1 -Serwer root@<vps>`: w logu start pollingu bez błędów, obie usługi działają.
7. Testy w kontenerze: `ssh root@<vps> "cd /opt/edity-bot && docker compose run --rm bot sh -c 'pip install -q -r requirements-test.txt && python -m pytest -q'"`.
8. Próba na Telegramie: `/start`, `/status`, `/wzor` z prawdziwym wzorem 4K (około 150 MB), po części 3 także `/nowy`, 5 zdjęć i 1 klip, `/gotowe`. Pomiar tej zmiany na serwerze: czas od wysłania wzoru do podsumowania (powyżej około 150 s zleć zadanie 5.0, lekką kopię wzoru, zanim ruszysz dalej) i czas renderu z podpisu wiadomości, oba zapisane w `ROZWOJ.md` obok lokalnych.
9. Aktualizacja po kolejnych częściach: po odbiorze i scaleniu części do `main` zsynchronizuj lokalny `main` (`git checkout main`, `git pull`), potem `.\wdroz.ps1 -Serwer root@<vps>` (kod jest wbudowany w obraz, sam restart kontenera nie wystarczy).
10. Sprzątanie w cronie roota, projekty starsze niż 7 dni (materiały i wyniki; oryginały masz w telefonie): `10 4 * * * find /opt/edity-bot/dane/projekty -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} +`. Siedem dni to propozycja do potwierdzenia.

### Po zadaniu 7.3 (Ty)
Dziś na serwerze działa bot testowy `@local125_bot`, a główny bot stoi nieużywany na zwykłym API. Decyzja właściciela (2026-09-22): przy wdrożeniu 7.3 serwer przechodzi na głównego bota (krok 3), a bot testowy wraca do pracy lokalnej, więc wykonujesz wszystkie punkty od a do h. Kolejność ma znaczenie: punkt a działa tylko na starej konfiguracji. Polecenia a, b i f wpisujesz w powłoce serwera (`ssh root@46.62.151.181`, potem `cd /opt/edity-bot`), żeby nie walczyć z cudzysłowami PowerShella; żadne z nich nie wypisuje tokenu.

a. Wylogowanie bota testowego z serwera lokalnego, żeby mógł wrócić na zwykłe API: `docker compose exec -T bot python -c "import os,urllib.request as u; print(u.urlopen(os.environ['TELEGRAM_API_URL']+'/bot'+os.environ['BOT_TOKEN']+'/logOut', data=b'').read().decode())"`. Oczekiwane `{"ok":true,"result":true}`.
b. `docker compose down`, potem `docker volume rm edity-bot_bot_api_dane`. Stary wolumen ma pliki UID 101 i tylko sesję bota (32 KB), nowy powstanie z właścicielem 1000.
c. W `C:\Dev\edity-bot-serwer.env` zamień komentarz na `TELEGRAM_API_URL=http://bot-api:8081`, potem z komputera `scp C:\Dev\edity-bot-serwer.env root@46.62.151.181:/opt/edity-bot/.env`.
d. `logOut` głównego bota na serwerze Telegrama (`https://api.telegram.org/bot<token głównego bota>/logOut` w przeglądarce) i zatrzymanie każdej jego lokalnej instancji.
e. Na komputerze `git checkout main`, `git pull`, `.\wdroz.ps1 -Serwer root@46.62.151.181`. W logu `Run polling for bot @...` z nazwą właściwego bota.
f. Uprawnienia, po starcie pollingu (katalog bota powstaje przy jego pierwszym zapytaniu): `docker compose exec -T bot-api id -u telegram-bot-api` daje `1000`, a `docker compose exec -T bot sh -c 'ls /var/lib/telegram-bot-api/*/ >/dev/null 2>&1 && echo odczyt OK || echo BRAK ODCZYTU'` daje `odczyt OK`. Przy okazji limit pamięci: `docker inspect -f '{{.HostConfig.Memory}}' edity-bot-bot-1` ma dać `3221225472`, a nie `0` (zero znaczy, że `mem_limit` nie zadziałał).
g. Krok 8 z prawdziwym wzorem 4K. W trakcie analizy kilka razy `docker stats --no-stream edity-bot-bot-1 edity-bot-bot-api-1`: szczyt pamięci obu usług trafia do `ROZWOJ.md` obok czasu. Szczyt bota blisko 3 GB oznacza podniesienie `mem_limit`.
h. Krok 10 (cron dla `dane/projekty`) nadal do zrobienia. Wolumenu serwera Bot API nie trzeba już sprzątać, bo bot usuwa plik po skopiowaniu.

## Zadanie 7.2: lokalny serwer Bot API (pliki do 2000 MB)

### [Task 7.2: Bot z lokalnym serwerem API]
- **Objective:** bot potrafi działać z lokalnym serwerem Bot API, gdy w `.env` jest `TELEGRAM_API_URL`.
- **Context/Inputs:** `Pomiary/TELEGRAM_BOT_API.md`, sekcje „Limity plików” i „Lokalny serwer Bot API”. `src/konfiguracja.py` dostaje opcjonalne `telegram_api_url`. `src/bot.py`: przy ustawionym adresie sesja aiogram wskazuje ten serwer w trybie lokalnym (w aiogram 3 serwer API ustawia się w sesji, sprawdź w zainstalowanej wersji). `bot.pobierz_plik` w trybie lokalnym kopiuje plik spod ścieżki zwróconej przez `getFile` zamiast pobierać go przez HTTP. Compose dostaje usługę serwera (gotowy obraz, np. `aiogram/telegram-bot-api`, sprawdź, czy jest utrzymywany; zmienne `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, tryb lokalny) i wspólny wolumen zamontowany w obu kontenerach pod tą samą ścieżką, żeby ścieżka z `getFile` była czytelna dla bota. Limity: dziś `LIMIT_SERWERA_TELEGRAM_MB = 20` (bot.py:26 w `0e84cba`) i `efektywny_limit_mb` (36) obcinają pobieranie do 20 MB; przy ustawionym `TELEGRAM_API_URL` obcięcie znika i obowiązuje wartość z `.env` (2500), a wysyłka dostaje górną granicę 2000 MB w `efektywny_limit_wysylki_mb` (funkcja z zadania 3.5; jeśli części 3 jeszcze nie ma, dodaj ją tutaj, z granicą 50 MB bez serwera lokalnego).
- **Constraints:** bez `TELEGRAM_API_URL` zachowanie identyczne jak dziś. Testy: konfiguracja z adresem i bez; limit pobierania z adresem 2500, bez adresu 20; limit wysyłki z adresem 2000, bez adresu 50; `pobierz_plik` w trybie lokalnym z podmienionym `getFile` zwracającym ścieżkę do pliku tymczasowego kopiuje go do celu. Pomiar: czas pobrania pliku 100 MB przez bota po przełączeniu (krok ręczny, wynik do raportu).
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 7.2 z Pomiary/PLAN_EDITY_7_WDROZENIE.md; otwórz Pomiary/TELEGRAM_BOT_API.md, src/konfiguracja.py, src/bot.py, docker-compose.yml, .env.example, tests/test_bot.py, tests/test_konfiguracja.py. Weryfikacja: python -m pytest -q
```
Commit: `bot: lokalny serwer Bot API`.

Przełączenie (Ty, przed krokiem 6): `.env` na serwerze z kroku 3 (ma `api_id`, `api_hash` i `TELEGRAM_API_URL`); zatrzymaj każdą instancję głównego bota; jednorazowo `logOut` na serwerze Telegrama (`https://api.telegram.org/bot<token>/logOut`); dalej krok 6. Powrót na serwer Telegrama możliwy dopiero po 10 minutach. Serwer lokalny trzyma pobrane pliki na swoim wolumenie: po zadaniu 7.3 usuwa je bot zaraz po skopiowaniu.

## Zadanie 7.3: poprawki po odbiorze

Stan opisany niżej sprawdzony 2026-09-22 na serwerze i w kodzie z `e9a4755`; numery linii mogą się przesunąć, wtedy szukaj po nazwie funkcji.

### [Task 7.3: Poprawki po odbiorze części 7]
- **Objective:** bot na serwerze naprawdę pobiera pliki przez lokalny serwer Bot API, duże pliki nie wpadają w limit czasu, pobrany plik nie leży na dysku dwa razy, `wdroz.ps1` wdraża wyłącznie `main`, a kontener bota ma limit pamięci.
- **Gałąź:** `wdrozenie-poprawki` od `origin/main`. Najpierw `git checkout main` i `git pull`, bo lokalny `main` jest 4 commity za `origin/main`.
- **Context/Inputs:**
  1. Uprawnienia (blokujące). Usługa `bot-api` (dziś obraz `aiogram/telegram-bot-api:latest`) działa jako użytkownik `telegram-bot-api` o UID i GID 101, a katalog bota na wolumenie ma prawa `drwxr-x---`, pliki `-rw-------`. Bot działa jako UID 1000 i już przy wejściu do tego katalogu dostaje `Permission denied` (sprawdzone w kontenerze `bot`). Skutek: `pobierz_plik` w trybie lokalnym zawsze kończy się błędem, a bot odpowiada „nie udało się pobrać” na każdy wzór i materiał. Test `test_pobierz_plik_w_trybie_lokalnym_kopiuje_sciezke_z_getfile` tego nie łapie, bo plik tymczasowy należy do tego samego użytkownika. Cel: serwer Bot API zapisuje pliki jako UID i GID 1000. Nowy plik `bot-api/Dockerfile`: cienki obraz na bazie `aiogram/telegram-bot-api:10.3` (przypięty tag, nie `latest`; 10.3 działa dziś na serwerze), w którym użytkownik i grupa `telegram-bot-api` dostają identyfikator 1000; compose buduje go zamiast pobierać `image`. Entrypoint obrazu bazowego (`/docker-entrypoint.sh`) zostaje bez zmian: sam zmienia właściciela katalogu roboczego i uruchamia serwer z `--username` i `--groupname` tego użytkownika. Przypadek cichy: katalog tymczasowy `/tmp/telegram-bot-api` należy w obrazie bazowym liczbowo do 101 i entrypoint go nie poprawia. Bez zmiany jego właściciela serwer wystartuje i zaloguje bota, a padnie dopiero przy pierwszym pobieraniu pliku. W nowym obrazie oba katalogi, roboczy i tymczasowy, należą do 1000.
  2. Limit czasu `getFile` (`bot.pobierz_plik`, bot.py:94). W trybie lokalnym `getFile` odpowiada dopiero wtedy, gdy serwer Bot API ściągnie z Telegrama cały plik. `Bot.download` woła `get_file` bez `request_timeout`, więc obowiązuje domyślne 60 s sesji aiogram (`DEFAULT_TIMEOUT` w `aiogram/client/session/base.py`). Plik rzędu gigabajta może się w tym nie zmieścić: bot zgłosi „nie udało się pobrać”, choć serwer dokończy pobieranie w tle. Cel: w trybie lokalnym `pobierz_plik` woła `get_file` z długim limitem czasu (stała w `bot.py`, np. 30 min), potem pobiera plik spod zwróconej ścieżki; na zwykłym API bez zmian. Tryb rozpoznaje po sesji bota (`bot.session.api.is_local`), więc sygnatura `pobierz_plik(bot, file_id, cel)` zostaje.
  3. Podwójne przechowywanie. Serwer Bot API trzyma każdy pobrany plik na wolumenie bez końca, a bot kopiuje go do `dane/`, więc każdy wzór (około 150 MB) i klip (do 2000 MB) leży na dysku dwa razy. Serwer jest współdzielony i ma 31 GB wolnego miejsca. Cel: w trybie lokalnym po udanym skopiowaniu `pobierz_plik` usuwa plik źródłowy spod ścieżki z `getFile`. Nieudane usunięcie tylko zapisuje ostrzeżenie w logu, pobranie liczy się jako udane. Nieudane pobranie niczego nie usuwa. Na zwykłym API nic nie jest usuwane. Na serwerze zadziała dopiero razem z punktem 1 (ten sam UID).
  4. `wdroz.ps1` pakuje dziś `HEAD` (`git archive HEAD`) i nie porównuje `main` z `origin/main`. Cel według zadania 7.1: `git fetch origin main` wyłącznie do porównania (kod dalej nie jedzie przez GitHuba), zatrzymanie z komunikatem „zsynchronizuj main: git checkout main, git pull”, gdy `main` i `origin/main` wskazują różne commity (w obie strony: lokalny za zdalnym po scaleniu PR na GitHubie albo przed nim przez niewypchnięte commity), chyba że podano `-Wymus`; potem `git archive main`. Przypadek graniczny do sprawdzenia bez serwera: na starcie zadania lokalny `main` jest za `origin/main`, więc skrypt uruchomiony z dowolnym `-Serwer` musi się zatrzymać przed `git archive` i `scp`. Sekcja „Wdrożenie” w README opisuje `git archive main` i synchronizację.
  5. Limit pamięci. Serwer ma 4 vCPU i 7,6 GB RAM, a API drugiego projektu zajmuje około 1,8 GB. Usługa `bot` ma limit CPU, ale nie ma limitu pamięci, więc zbyt duży plik w analizie albo w renderze może uruchomić OOM killer hosta, który ubije proces innego projektu. Cel: `mem_limit` dla `bot` równy 3 GB (zatwierdzone przez właściciela 2026-09-22), do korekty po pomiarze z punktu g.
  6. `CLAUDE.md`, linia 3: „z muzyką royalty free” nie zgadza się z decyzją 6 z mapy (dowolny plik z `dane/muzyka/`). Opis mówi o muzyce z biblioteki właściciela.
- **Constraints:** nie zmieniaj nazwy usługi `bot-api`, portu 8081 ani ścieżki montowania `/var/lib/telegram-bot-api` w obu usługach: bot łączy się pod `http://bot-api:8081` (tak stoi w `.env` na serwerze), a `download_file` czyta bezwzględną ścieżkę z `getFile` bez tłumaczenia. Bez `TELEGRAM_API_URL` zachowanie identyczne jak dziś, istniejące testy przechodzą bez zmian. Nowe testy: w trybie lokalnym `get_file` dostaje limit czasu nie krótszy niż stała; na zwykłym API `pobierz_plik` niczego nie usuwa; w trybie lokalnym po pobraniu źródła nie ma, a cel ma pełną treść; błąd usuwania źródła (podmienione usuwanie rzucające `PermissionError`) nie przerywa pobrania i zostawia wpis w logu; pobranie przerwane błędem zostawia źródło. Lokalnie nie ma Dockera: nowy obraz sprawdź czytaniem, właściwa weryfikacja to punkty e do g właściciela.
- **Pomiar:** `Pomiary/measure_pobieranie.py`: `pobierz_plik` w trybie lokalnym na plikach 100 MB i 1 GB w katalogu tymczasowym, sprzątanych po sobie. Mierzy czas kopii i największe opóźnienie pętli zdarzeń (zadanie tykające co 10 ms w trakcie kopii). Próg: opóźnienie pętli poniżej 50 ms, jak w pomiarze A części 1. Dodatkowo `chunk_size` 64 KB (domyślny aiogram) wobec 1 MB, naprzemiennie po 3 razy: większy kawałek wchodzi do kodu tylko wtedy, gdy różnica przekracza rozrzut powtórzeń.
- **Sonnet Prompt:**
```text
Katalog: C:\Dev\edity-bot. Wykonaj zadanie 7.3 z Pomiary/PLAN_EDITY_7_WDROZENIE.md. Na starcie przeczytaj Pomiary/ROZWOJ.md i dopisuj do niego po każdym punkcie. Otwórz tylko: src/bot.py, tests/test_bot.py, tests/pomocnicze.py, docker-compose.yml, wdroz.ps1, README.md, CLAUDE.md; nowe pliki: bot-api/Dockerfile i Pomiary/measure_pobieranie.py. Kroków na serwerze nie wykonuj. Weryfikacja: python -m pytest -q i pomiar. Commity z listy przy zadaniu, push tylko na moją prośbę. Na koniec krótki raport.
```
Commity: `wdrożenie: serwer Bot API z UID bota i limit pamięci`, `bot: pobieranie przez serwer lokalny bez limitu 60 s i bez drugiej kopii`, `wdrożenie: wdroz.ps1 pakuje main`, `claude: muzyka z biblioteki właściciela`.

## Gotowe, gdy
- Po restarcie VPS bot sam wstaje (`docker compose ps` po `reboot`). Na 2026-09-22 potwierdzone tylko konfiguracją (Docker włączony przy starcie systemu, `restart: unless-stopped` w obu usługach); prawdziwy reboot zatrzymuje też drugi projekt na serwerze, więc tylko w oknie serwisowym.
- Testy w kontenerze przechodzą; próba z punktu 8 zwraca podsumowanie wzoru 4K, a po części 3 także edit.
- Czasy analizy i renderu na serwerze zapisane w `ROZWOJ.md` obok lokalnych.

## Odbiór (oceniający)
```text
Katalog: C:\Dev\edity-bot. Oceniasz część 7 według Pomiary/PLAN_EDITY_7_WDROZENIE.md. Nie poprawiaj kodu. Przeczytaj Pomiary/ROZWOJ.md, Dockerfile, docker-compose.yml, .dockerignore, wdroz.ps1, zmiany z zadania 7.2 (git diff main..wdrozenie -- src tests) i wynik testów z kontenera, który wklei właściciel. Werdykt: OK albo lista poprawek.
```
Sprawdź: brak `.env` i `dane` w obrazie, proces nie jako root, wolumen `dane` poza obrazem, limit CPU i rotacja logów, żadnego wystawionego portu; `wdroz.ps1` pakuje `main`, nigdy bieżącą gałąź, i zatrzymuje się, gdy `main` różni się od `origin/main`, nie dotyka `dane/` ani `.env` na serwerze, a kod nie jedzie przez GitHuba (`git fetch` służy tylko porównaniu); przy `TELEGRAM_API_URL` limity nie są obcinane do 20 i 50 MB, a `pobierz_plik` w trybie lokalnym kopiuje plik spod ścieżki z `getFile`.

Po zadaniu 7.3 dodatkowo: serwer Bot API działa jako UID 1000, jego katalog tymczasowy też należy do 1000, a obraz bazowy ma przypięty tag; w trybie lokalnym `get_file` z długim limitem czasu i usunięcie źródła tylko po udanej kopii (nieudane usunięcie nie psuje pobrania); `mem_limit` dla `bot`; wynik punktów e do g od właściciela, w tym plik wysłany botowi, który doszedł do `dane/`.
