# Bot edity: mapa planów

Stan na 2026-09-22, po wykonaniu części 1 i 2. Projekt: `C:\Dev\edity-bot`, zdalne repo `origin` na GitHubie (`OskarOG1/Kontent_bot`). Wymagania i zatwierdzone decyzje: `KONTEKST_PROJEKTU.md`. Co faktycznie się stało, znane problemy i decyzje z realizacji: `Pomiary/ROZWOJ.md`. Wyciąg z Telegram Bot API 10.3: `Pomiary/TELEGRAM_BOT_API.md`.

## Jak pracujemy

- **Wykonawca: Sonnet.** Jedna sesja na jeden plik planu, otwarta w `C:\Dev\edity-bot`, na gałęzi tej części. Prompt startowy stoi na początku każdego pliku, każde zadanie ma też własny krótki prompt. Na starcie czyta `ROZWOJ.md` i dopisuje do niego po każdym zadaniu.
- **Oceniający: Opus.** Osobna sesja po zakończeniu części, prompt w sekcji „Odbiór”. Nie poprawia kodu: uruchamia testy i pomiar, ogląda arkusze klatek (PNG zamiast oglądania wideo), czyta tylko wskazane miejsca i wydaje werdykt z listą poprawek `plik:linia`.
- **Poprawki** wracają do sesji wykonawcy: „Popraw według listy, po każdej poprawce test, jeden commit »poprawki po odbiorze części N«”.
- **Po odbiorze** scalasz gałąź części do `main` (i wypychasz, jeśli chcesz); następna część startuje od `main`. Na serwer kod idzie przez `wdroz.ps1`, nie przez GitHub.
- **Test ręczny na Telegramie robisz Ty**, kilka minut na część.

## Części

| Nr | Plik | Efekt | Stan 2026-09-22 | Od Ciebie | Kto |
|---|---|---|---|---|---|
| 1 | PLAN_EDITY_1_SZKIELET | bot przyjmuje wzór i materiały, tylko Twoje konto, kolejka zadań | wykonana, odbiór OK | nic | Sonnet |
| 2 | PLAN_EDITY_2_ANALIZA | wzór mp4 zamienia się w `wzor.json`: cięcia, tempo, uderzenia | wykonana, scalona w PR #1, odbiór OK | nic | Sonnet |
| 7 | PLAN_EDITY_7_WDROZENIE | bot w Dockerze na VPS z lokalnym serwerem Bot API | wykonana: PR #2 i #3, serwer na głównym bocie `@cwel54_bot`, wzór 4K pobrany w 9 s i przeanalizowany w 51 s | VPS, drugi bot z BotFather do pracy lokalnej, `api_id` i `api_hash` z my.telegram.org | Sonnet pliki, Ty serwer |
| 3 | PLAN_EDITY_3_RENDER | `/gotowe` zwraca edit 9:16 na stałym utworze, klipy cięte na wstawki | następna | `dane/muzyka/staly.mp3` | Sonnet |
| 4 | PLAN_EDITY_4_MUZYKA | biblioteka utworów, dobór po tempie, najmocniejszy fragment | do zrobienia | 5 do 15 utworów, `licencje.csv` opcjonalny (tylko do podpisu) | Sonnet |
| 5 | PLAN_EDITY_5_KOLOR | lekka kopia wzoru (5.0) i kolorystyka jak we wzorze | do zrobienia | nic | Sonnet |
| 6 | PLAN_EDITY_6_TEKST | Twoje napisy na ekranie | do zrobienia | akceptacja czcionki | Sonnet |

## Kolejność (poprawiona 2026-09-22)

1. Zrobione 2026-09-22: odbiór części 1 i 2 (OK) i scalenie `analiza-wzoru` do `main` (PR #1).
2. Część 7 razem z lokalnym serwerem Bot API (zadanie 7.2): scalona w PR #2, a odbiór wymaga zadania 7.3 i kroków właściciela po nim. Powód: oba prawdziwe wzory mają około 150 MB (4K, 60 fps), klipy z telefonu często ponad 20 MB, a zwykłe Bot API pobiera najwyżej 20 MB i wysyła 50 MB. Bez tego żaden test ręczny na prawdziwych plikach nie przejdzie, a przy okazji wyjdzie czas analizy na serwerze.
3. Rozstrzygnięte 2026-09-23: analiza wzoru 4K na serwerze trwa 51 s, więc zadanie 5.0 (lekka kopia wzoru) odpada i zostaje w planie 5 na wypadek dłuższych albo cięższych wzorów.
4. Część 3, potem 4, 5 i 6 (5 i 6 w dowolnej kolejności), po każdej aktualizacja serwera.

## Decyzje

1. Lokalny serwer Bot API jest potrzebny: `.env` ma limity 2500 MB (pobieranie) i 200 MB (wysyłka). Do pracy lokalnej osobny bot testowy na zwykłym API, bo główny bot po przejściu na serwer lokalny nie działa równolegle na zwykłym.
2. Analiza i render to osobne procesy z własnym CLI, bot tylko je kolejkuje.
3. Cięcia wzoru w jednostkach uderzeń, nie w sekundach.
4. Bot bierze najnowszy wzór; wybór z listy dopiero przy wariantach.
5. Wynik jako dokument; limit wysyłki pilnowany przy kodowaniu (50 MB na zwykłym API, wartość z `.env` z serwerem lokalnym).
6. Twoja decyzja z 2026-09-22: edity trafiają z powrotem na TikTok, więc `licencje.csv` przestaje być warunkiem doboru utworu. Każdy plik z `dane/muzyka/` jest kandydatem niezależnie od wpisu w CSV; wpis daje tylko dane do podpisu pod postem (tytuł, autor, licencja), gdy jest.
7. Kolorystyka przez LUT z statystyk Lab, siła 0,6 do ustalenia pomiarem.
8. Tekst: linie jako zwykłe wiadomości w trakcie `/nowy`, styl z presetu; wykrywanie stylu we wzorze tylko jako pomiar rozpoznawczy.
9. Projekt osobny od allegro-rag-agents.
10. Zdalne repo na GitHubie; gałąź na część; push i scalanie na Twoją prośbę; na serwer przez `wdroz.ps1`.
11. Twoja decyzja z 2026-09-22: `START_BPM = 150` dla wzorów, bo domyślne 120 dało na prawdziwym wzorze pomyłkę 3:2 (110 zamiast 164 BPM). Potwierdzone na jednym wzorze. Dla utworów z biblioteki część 4 porówna 120 i 150.
12. Twoje wymaganie z 2026-09-21, szczegóły potwierdzone 2026-09-22: klipy i gify cięte na wstawki o długości mediany ujęć wzoru (w granicach 0,5 do 2,0 s), układane rundami po materiałach w kolejności wysłania, więc jeden klip nie wypełnia ujęć pod rząd.
13. Domyślny detektor cięć: ContentDetector, potwierdzony przy odbiorze części 2 (AdaptiveDetector tnie szybki ruch kamery poza rytmem i jest wolniejszy).

## Ryzyka przyjęte świadomie

- Analiza wzoru 4K trwa lokalnie 40 do 55 s, na serwerze będzie wolniej przy limicie 300 s. Odpowiedź: zadanie 5.0.
- Tempo: pomyłki o oktawę i 3:2. `START_BPM = 150` sprawdzone na jednym wzorze; stały utwór w części 3 liczony tą samą stałą, więc cięcia mijające się z rytmem mogą wynikać z tempa utworu.
- Szybki ruch we wzorze daje fałszywe cięcia (AdaptiveDetector dołożył trzy w jednym ujęciu wzoru `0915`).
- Wideo HDR z iPhone'a (HEVC 10 bit) może wyjść wyblakłe; obejście: nagrywanie bez HDR.
- Render obciąża CPU serwera; część 7 ogranicza CPU kontenera.
- Próbki wzorów leżą w `dane/wzory/Edity/`, czyli w katalogu wzorów bota, i `/status` liczy je jako wzór. Lepiej przenieść je do `dane/probki/wzory/`, skąd biorą je pomiary.

## Muzyka: skąd brać

Edity trafiają z powrotem na TikTok, więc `licencje.csv` jest opcjonalny: dobór utworu go nie wymaga (decyzja 6). Jeśli chcesz podpis z tytułem i autorem pod postem, dopisz wpis w `licencje.csv`; kierunki jak dawniej: Pixabay Music, Free Music Archive (CC0 albo CC BY), incompetech (CC BY), płatne subskrypcje (Epidemic Sound, Artlist).

## Poza zakresem

Warianty (10 wersji), zbieranie trendów, pobieranie zdjęć z legalnych API. Kod jest układany tak, żeby warianty były tanie: przypisanie materiałów do ujęć (`render.wstawki`, `render.plan_ujec`) i wybór fragmentu utworu to osobne czyste funkcje.
