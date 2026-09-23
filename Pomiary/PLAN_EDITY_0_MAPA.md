# Bot edity: mapa planów

Stan na 2026-09-23, po części 3 (z naprawą 3.7) i po przeglądzie planów pod cel „fabryka editów na TikToka”. Projekt: `C:\Dev\edity-bot`, zdalne repo `origin` na GitHubie (`OskarOG1/Kontent_bot`). Co faktycznie się stało, znane problemy i decyzje z realizacji: `Pomiary/ROZWOJ.md`. Wyciąg z Telegram Bot API 10.3: `Pomiary/TELEGRAM_BOT_API.md`.

## Cel
Fabryka editów 9:16 na TikToka. Właściciel dostaje wzór (gotowy edit) i materiały, a bot montuje z materiałów edit o strukturze i stylu wzoru, na dźwięku wzoru z biblioteki. Z wzoru bierzemy tylko strukturę i styl: jego obraz i dźwięk nigdy nie trafiają do wyniku.

Prawdziwe wzory (`0915`, `0921`, `0922`, wszystkie 4K) mają ten sam format:
- hak z napisem: pierwsze 4 do 11 s, naturalne kolory;
- drop: od niego wchodzi pełnoekranowa nakładka graficzna i zwykle zmienia się grading;
- montaż;
- plansza końcowa: około 1 s.

## Jak pracujemy
- **Wykonawca: Sonnet.** Jedna sesja na jeden plik planu, otwarta w `C:\Dev\edity-bot`, na gałęzi tej części. Prompt startowy stoi na początku każdego pliku, każde zadanie ma też własny krótki prompt. Na starcie wykonawca czyta `ROZWOJ.md` i dopisuje do niego po każdym zadaniu.
- **Oceniający: Opus.** Osobna sesja po zakończeniu części, prompt w sekcji „Odbiór”. Nie poprawia kodu: uruchamia testy i pomiar, czyta tylko wskazane miejsca i wydaje werdykt z listą poprawek `plik:linia`. Werdykt wizualny wydaje na arkuszu porównawczym, w którym wiersz wzoru stoi nad wierszem wyniku (`outputs/porownanie_*.png`, decyzja 17); progi liczbowe są dodatkiem.
- **Poprawki** wracają do sesji wykonawcy: „Popraw według listy, po każdej poprawce test, jeden commit »poprawki po odbiorze części N«”.
- **Po odbiorze** scalasz gałąź części do `main` (i wypychasz, jeśli chcesz); następna część startuje od `main` po `git pull`. Na serwer kod idzie przez `wdroz.ps1`, nie przez GitHub. Po części, która zmienia `wzor.json` (4, 8, 5), uruchom na serwerze `docker compose exec bot python src/analyze.py --wszystkie`.
- **Test ręczny na Telegramie robisz Ty**, kilka minut na część.

## Części

| Nr | Plik | Efekt | Stan 2026-09-23 | Od Ciebie | Kto |
|---|---|---|---|---|---|
| 1 | PLAN_EDITY_1_SZKIELET | bot przyjmuje wzór i materiały, tylko Twoje konto, kolejka zadań | wykonana, odbiór OK | nic | Sonnet |
| 2 | PLAN_EDITY_2_ANALIZA | wzór mp4 zamienia się w `wzor.json`: cięcia, tempo, uderzenia | wykonana, PR #1, odbiór OK | nic | Sonnet |
| 7 | PLAN_EDITY_7_WDROZENIE | bot w Dockerze na VPS z lokalnym serwerem Bot API | wykonana, PR #2 i #3, serwer na `@cwel54_bot` | zrobione | Sonnet pliki, Ty serwer |
| 3 | PLAN_EDITY_3_RENDER | `/gotowe` zwraca edit 9:16, klipy cięte na wstawki | wykonana, PR #4 i #5 (naprawa dźwięku 3.7), wdrożona, test ręczny OK | nic | Sonnet |
| 4 | PLAN_EDITY_4_MUZYKA | dźwięk wzoru rozpoznany w bibliotece i montaż na tym samym fragmencie utworu; dobór po tempie jako zapas; arkusz porównawczy | do zrobienia (przepisana 2026-09-23) | utwory wzorów w `dane/muzyka/` (nazwy bez „ (1)”), próbki w `dane/probki/materialy/` | Sonnet |
| 8 | PLAN_EDITY_8_NAKLADKA | drop we wzorze, Twoja nakładka od dropu, Twoja plansza na końcu | do zrobienia (nowa 2026-09-23) | pliki nakładek i plansz | Sonnet |
| 5 | PLAN_EDITY_5_KOLOR | kolorystyka wzoru na sekcję (hak, montaż), LUT na każdy segment | do zrobienia (przepisana 2026-09-23) | nic | Sonnet |
| 6 | PLAN_EDITY_6_TEKST | Twoje napisy w haku, styl jak we wzorach, strefy bezpieczne TikToka | do zrobienia (przepisana 2026-09-23) | akceptacja czcionki | Sonnet |
| 9 | PLAN_EDITY_9_FABRYKA | restart bez strat, biblioteka wzorów z wyborem, warianty, partie, `/ponow` | do zrobienia (nowa 2026-09-23) | nic | Sonnet |

## Kolejność (poprawiona 2026-09-23)
1. Zrobione: części 1, 2, 7 i 3.
2. Część 4 idzie pierwsza, bo bez niej edit leci na intro utworu, a nie na fragmencie ze wzoru, i reszta stylu traci sens.
3. Część 8 wprowadza sekcje wzoru, na których stoją części 5 i 6. Nakładka to najbardziej rozpoznawalny element wzorów.
4. Części 5 i 6: obie zależą od 8, a między sobą nie, więc 6 może iść przed 5.
5. Część 9.

Po każdej części: odbiór, scalenie, `wdroz.ps1` i, gdy trzeba, `analyze.py --wszystkie` na serwerze.

## Decyzje
1. Lokalny serwer Bot API jest potrzebny: `.env` ma limity 2500 MB (pobieranie) i 200 MB (wysyłka). Do pracy lokalnej służy osobny bot testowy na zwykłym API, bo główny bot po przejściu na serwer lokalny nie działa równolegle na zwykłym.
2. Analiza i render to osobne procesy z własnym CLI, bot tylko je kolejkuje.
3. Cięcia wzoru zapisane w jednostkach uderzeń i w sekundach. W trybie dźwięku wzoru (decyzja 14) render tnie w sekundach wzoru, w trybie tempa w uderzeniach.
4. Bot bierze najnowszy wzór; wybór aktywnego wzoru z listy przychodzi w części 9.
5. Wynik idzie jako dokument; limit wysyłki pilnowany przy kodowaniu (50 MB na zwykłym API, wartość z `.env` z serwerem lokalnym).
6. Biblioteka muzyki to dźwięki wzorów (utwory z TikToka), a edity wracają na TikTok, więc licencja nie jest warunkiem doboru (Twoja decyzja z 2026-09-22). `licencje.csv` i dane licencji w podpisie odłożone (przegląd 2026-09-23).
7. Kolorystyka: transfer Reinharda w Lab przez LUT. Cel liczony jest na sekcję wzoru (hak, montaż) ze statystyk ujęć, a LUT nakładany na każdy segment w jego jedynym kodowaniu. Plansza zostaje bez LUT. Siła domyślna 0,6 do ustalenia na arkuszach.
8. Tekst: linie przychodzą jako zwykłe wiadomości w trakcie `/nowy` i pokazują się w haku, przed dropem. Preset szeryfowy jak we wzorach, strefy bezpieczne TikToka, znaki bez glifu usuwane. Wykrywanie napisów we wzorze tylko jako pomiar.
9. Projekt osobny od allegro-rag-agents.
10. Zdalne repo na GitHubie, gałąź na część; push i scalanie na Twoją prośbę; na serwer przez `wdroz.ps1`. `Pomiary/` jest w repozytorium od 2026-09-23.
11. `START_BPM = 150` dla wzorów i utworów. Przy 120 prawdziwy wzór dawał 110 zamiast 164 BPM (2026-09-22), a „Ex's And Oh's” 88,3 zamiast 175,2 BPM (przegląd 2026-09-23).
12. Twoje wymaganie z 2026-09-21, szczegóły potwierdzone 2026-09-22: klipy i gify cięte są na wstawki o długości mediany ujęć wzoru (w granicach 0,5 do 2,0 s) i układane rundami po materiałach w kolejności wysłania, więc jeden klip nie wypełnia ujęć pod rząd.
13. Domyślny detektor cięć: ContentDetector, potwierdzony przy odbiorze części 2 (AdaptiveDetector tnie szybki ruch kamery poza rytmem i jest wolniejszy).
14. Dźwięk wzoru (przegląd 2026-09-23):
    - analiza zapisuje w `wzor.json` odcisk dźwięku (chroma i obwiednia), a indeks biblioteki ma odciski utworów;
    - render rozpoznaje utwór i przesunięcie, z progiem zgodności 0,5 (prawdziwe pary mają 0,78 i 0,81, niepasujące najwyżej 0,12), i tnie dokładnie w czasach cięć wzoru;
    - dobór po tempie działa tylko wtedy, gdy żaden utwór nie pasuje, a fragment wybiera korelacja profilu energii, nie najgłośniejsze okno.
15. Sekcje wzoru: drop wykrywany jest ze skoku energii dźwięku wzoru w jego pierwszej połowie i przyciągany do cięcia. Na nim stoją nakładka (8), kolor (5) i napisy (6). Każde ujęcie planu niesie `numer_wzoru`.
16. Nakładki i plansze to Twoje pliki (`dane/nakladki/`, `dane/plansze/`, na wzór albo `domyslna`), nigdy wycinki ze wzoru.
    - Kolejność warstw: materiał z kolorem, nakładka, napisy.
    - Plansza zajmuje miejsce ostatniego ujęcia, bez koloru i nakładki.
17. Odbiór części 4 do 9 na arkuszu porównawczym (`Pomiary/arkusz.py`, wiersz wzoru nad wierszem wyniku, te same ułamki długości). Progi liczbowe uzupełniają werdykt.
18. Zadanie 5.0 (lekka kopia wzoru) zdjęte, bo analiza 4K na serwerze trwa 51 s przy progu 150 s. Wraca, jeśli analiza razem z próbkowaniem koloru przekroczy około 150 s.
19. Czas testów nie jest progiem (Twoja decyzja z 2026-09-23).

## Ryzyka przyjęte świadomie
- Dźwięk przyspieszony („sped up”) albo w innej tonacji niż plik w bibliotece nie zostanie rozpoznany i wtedy działa dobór po tempie. Odpowiedź: do biblioteki wrzucać tę wersję, która gra na TikToku.
- Lektor albo efekty dźwiękowe w haku obniżają zgodność odcisku. Na dwóch prawdziwych wzorach zapas nad progiem jest duży.
- Drop to heurystyka z energii dźwięku, sprawdzona na trzech wzorach z referencją z arkuszy (±0,5 s).
- Kolor na sekcję nie odtworzy posteryzacji ani efektów obrazu wzoru. Ostatnie ujęcie wzoru jest wyłączone ze statystyk, bo we wzorach to plansza.
- Analiza z kolorem dokłada drugie dekodowanie 4K, równolegle z wykrywaniem cięć; limit 300 s ma zapas.
- Tempo: w trybie tempa możliwe pomyłki oktawy i 3:2; w trybie dźwięku wzoru tempo nie gra roli.
- Szybki ruch we wzorze daje fałszywe cięcia (AdaptiveDetector dołożył trzy w jednym ujęciu wzoru `0915`).
- Wideo HDR z iPhone'a (HEVC 10 bit) może wyjść wyblakłe; obejście: nagrywanie bez HDR.
- Render obciąża CPU serwera (141 s na edit 32 s przy 2 CPU), a warianty i partie mnożą ten czas; część 9 to mierzy.

## Muzyka: skąd brać
Biblioteka to dźwięki wzorów: do `dane/muzyka/` wrzucasz utwór, który gra we wzorze, najlepiej pełną wersję w tym samym tempie i tonacji co na TikToku. Nazwa pliku trafia do podpisu, więc bez dopisków typu „ (1)”. Po dodaniu skopiuj katalog na serwer i zbuduj tam indeks (`docker compose exec bot python src/music.py indeksuj`); bez tego zrobi to pierwszy montaż. Wzór, którego utworu nie ma w bibliotece, dostaje utwór o najbliższym tempie.

## Poza zakresem
- efekty na cięciach (błysk, wstrząs, zoom w rytm, glitch);
- posteryzacja i inne efekty obrazu wzoru;
- śledzenie twarzy i nakładki na twarze;
- rozpoznawanie przyspieszonych wersji dźwięku;
- automatyczna publikacja na TikToku;
- zbieranie trendów i pobieranie wzorów z linków;
- `licencje.csv`.

Kod jest układany tak, żeby kolejne rzeczy były tanie: przypisanie materiałów do ujęć (`render.wstawki`, `render.plan_ujec`, `render.uloz_wariant`) i wybór utworu (`music.wybierz_utwor`) to osobne czyste funkcje.
