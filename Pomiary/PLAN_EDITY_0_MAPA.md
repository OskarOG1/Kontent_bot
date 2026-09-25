# Bot edity: mapa planów

Stan na 2026-09-23, po części 3 (z naprawą 3.7) i po przeglądzie planów pod cel „fabryka editów na TikToka”. Projekt: `C:\Dev\edity-bot`, zdalne repo `origin` na GitHubie (`OskarOG1/Kontent_bot`). Co faktycznie się stało, znane problemy i decyzje z realizacji: `Pomiary/ROZWOJ.md`. Wyciąg z Telegram Bot API 10.3: `Pomiary/TELEGRAM_BOT_API.md`.

## Cel
Fabryka editów 9:16 na TikToka. Właściciel dostaje wzór (gotowy edit) i materiały, a bot montuje z materiałów edit o strukturze i stylu wzoru, na dźwięku wzoru z biblioteki. Z wzoru bierzemy tylko strukturę i styl: jego obraz i dźwięk nigdy nie trafiają do wyniku. Edity promują czapki marki 1993 Supply: kończą się planszą z produktem albo stroną sklepu i mają znak wodny marki (decyzja 20).

Prawdziwe wzory (`0914`, `0915`, `0921`, `0922`, `0923`, wszystkie 4K, w `dane/wzory/`) mają ten sam format:
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
| 4 | PLAN_EDITY_4_MUZYKA | biblioteka muzyki, dobór utworu po tempie z fragmentem z profilu energii, arkusz porównawczy; rozpoznanie dźwięku wzoru w kodzie, ale wyłączone (decyzja 14) | wykonana, PR #7, bez odbioru oceniającego; zadanie 4.5 (pamięć analizy utworu) scalone w PR #11 i wdrożone, na serwerze szczyt 1567 MB (2026-09-24) | utwory wzorów w `dane/muzyka/` (nazwy bez „ (1)”), próbki w `dane/probki/materialy/` | Sonnet |
| 8 | PLAN_EDITY_8_NAKLADKA | drop we wzorze, Twoja nakładka od dropu, Twoja plansza na końcu | wykonana, PR #9 i #10, wdrożona, odbiór OK (2026-09-24) | własna nakładka (gwiazdy); plansza i znak wodny są w `dane/promocyjne/` | Sonnet |
| 5 | PLAN_EDITY_5_KOLOR | kolorystyka wzoru na sekcję (hak, montaż), LUT na każdy segment | wykonana, PR #12 i #13 (5.6, niebo), wdrożona 2026-09-25, siła domyślna 0,6 | nic | Sonnet |
| 6 | PLAN_EDITY_6_TEKST | Twoje napisy w haku, styl jak we wzorach, strefy bezpieczne TikToka | wykonana, PR #15, wdrożona 2026-09-25, czcionka szeryfowa zaakceptowana, test lokalny OK | test ręczny | Sonnet |
| 9 | PLAN_EDITY_9_FABRYKA | restart bez strat, biblioteka wzorów z wyborem, warianty, partie, `/ponow`; nakładka z kryciem (flaga, 9.5, zaraz po części 8); słowa w rytmie i napis pionowy jak w `0923` (9.6 do 9.8, po części 6) | 9.5 scalone w PR #14 i wdrożone; 9.6 do 9.8 na gałęzi `rytm`, odbiór z poprawkami (9.9) 2026-09-25; 9.1 do 9.4 do zrobienia | klip flagi jako nakładka, akceptacja czcionki pisanej | Sonnet |

## Kolejność (poprawiona 2026-09-23)
1. Zrobione: części 1, 2, 7, 3, 4, 8, 5 i 6.
   - Zadanie 4.5 (pamięć analizy utworu) scalone i wdrożone.
   - Zadania 5.6 (niebo) i 9.5 (nakładka z kryciem) scalone i wdrożone 2026-09-25. Część 6 scalona i wdrożona 2026-09-25. Następne 9.6 do 9.8 (gałąź `rytm`), potem 9.1 do 9.4.
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
    - **Zmiana w części 4 (decyzja właściciela 2026-09-23): rozpoznanie wyłączone, `wybierz_utwor` zawsze dobiera po tempie.** Na prawdziwych utworach metoda z kontraktu nie odtworzyła liczb z przeglądu. Zgodność z NIEWŁAŚCIWYM utworem wyszła ponad progiem: 0,829 dla `0915` i 0,76 dla `0922`. Przesunięcie wychodziło 116 s zamiast 40,36 s, bo dropy obu utworów hardstyle są szumowe. Przyczyną nie jest liczba plików w bibliotece: więcej podobnych utworów daje więcej fałszywych trafień, nie mniej. Dobór po tempie i tak trafia właściwe utwory dla `0915` i `0922`, bo tempa się zgadzają (164,1 i 175,2 BPM). Kod rozpoznania zostaje. Powrót wymaga innej metody, np. porównania najlepszego wyniku z drugim zamiast stałego progu, i nowego pomiaru na prawdziwej bibliotece.
15. Sekcje wzoru: drop wykrywany jest ze skoku energii dźwięku wzoru w jego pierwszej połowie i przyciągany do cięcia. Na nim stoją nakładka (8), kolor (5) i napisy (6). Każde ujęcie planu niesie `numer_wzoru`. Po odbiorze części 8 (2026-09-24) szukanie zaczyna się od 8. uderzenia z progiem 0,1 średniej energii. Koniec haka liczy jedna funkcja `render.koniec_haka`: bez dropu to 40% editu, a nie pierwsza klatka.
16. Nakładki i plansze to Twoje pliki (`dane/nakladki/`, `dane/plansze/`, na wzór albo `domyslna`), nigdy wycinki ze wzoru. Nakładka we wzorach `0914` i `0923` to flaga UE z kryciem około 50%. Twój klip flagi z `dane/nagrania/` nadaje się do tego, gdy dostanie tryb `krycie` (zadanie 9.5), bo tryb `ekran` z części 8 rozjaśnia kadr przy nieczarnym tle.
    - Kolejność warstw: materiał z kolorem, nakładka, napisy, znak wodny.
    - Plansza zajmuje miejsce ostatniego ujęcia, bez koloru i nakładki.
17. Odbiór części 4 do 9 na arkuszu porównawczym (`Pomiary/arkusz.py`, wiersz wzoru nad wierszem wyniku, te same ułamki długości). Progi liczbowe uzupełniają werdykt.
18. Zadanie 5.0 (lekka kopia wzoru) zdjęte, bo analiza 4K na serwerze trwa 51 s przy progu 150 s. Od 2026-09-24 czas analizy i montażu nie jest progiem (decyzja właściciela). Liczą się tylko limity bota (`LIMIT_ANALIZY_S` 300 s, `LIMIT_RENDERU_S` 900 s), a gdy praca się do nich zbliża, limit się podnosi.
19. Czas testów nie jest progiem (Twoja decyzja z 2026-09-23).
20. Edity promują czapki 1993 Supply (Twoja informacja z 2026-09-24). Znak wodny marki z `dane/promocyjne/1993supply_watermark.png` leży na całym edicie poza planszą. Ustawienie jak w Twoim wzorze `0914`: 51% szerokości, środek na 80% wysokości, krycie około 0,6 (zadanie 8.6). Plansza to produkt albo strona sklepu.
21. Układ `dane/` od 2026-09-24:
    - wzory do pomiaru leżą w `dane/wzory/*.mp4`;
    - biblioteka to `zdjęcia`, `nagrania`, `zdjęcia_bez_tła` i `promocyjne`;
    - `dane/probki/` zniknął, a pomiary biorą stałą próbkę z biblioteki (blok WSPÓLNE);
    - bot tych katalogów nie czyta, materiały dalej idą przez Telegram.
22. Napisy w rytmie (Twoje wymaganie z 2026-09-24, wzór `0923`), treść zawsze z Twoich wiadomości (zadania 9.6 do 9.8):
    - pojedyncze słowa (`/slowa`) na kolejnych uderzeniach utworu, a ostatnie wlatuje na dropie;
    - napis pionowy pisany literami przy lewej krawędzi (`/pionowo`);
    - złoto z granatowym obrysem.

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
