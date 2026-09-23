# edity-bot

Bot na Telegramie, który montuje edity wideo 9:16 z materiałów właściciela według wzorcowego editu, z muzyką z biblioteki właściciela.
Plany, pomiary i notatki: `Pomiary/`. Mapa planów: `Pomiary/PLAN_EDITY_0_MAPA.md`. Wyciąg z Telegram Bot API: `Pomiary/TELEGRAM_BOT_API.md`.

## Reguły
6. Przy pracy z planu otwieraj tylko pliki wskazane w zadaniu, nie przeszukuj repo.
7. Z wzorcowego editu bierzemy tylko strukturę i styl. Jego obraz i dźwięk nigdy nie trafiają do wyniku.
8. Raport na koniec pracy: wniosek w pierwszym zdaniu, liczby, problemy, opcje do decyzji. Bez relacjonowania drogi.
9. Repo ma zdalne repozytorium na GitHubie: `https://github.com/OskarOG1/Kontent_bot.git` (`origin`, gałąź `main`). Na serwer kod mimo to trafia przez `wdroz.ps1` (archiwum i scp), nie przez GitHub. Przed każdym push sprawdź, że `.env` i katalogi `dane/`, `outputs/` nie są w indeksie.
10. `.env` zawiera prawdziwy token bota: nie otwieraj go bez potrzeby, nie przepisuj jego wartości do innych plików, logów ani raportów, nigdy go nie commituj.
11. Projekt nie ma związku z allegro-rag-agents: nie korzystaj z jego plików ani skryptów.
12. Dziennik rozwoju to `Pomiary/ROZWOJ.md`. Na starcie pracy przeczytaj go, a w trakcie uzupełniaj na bieżąco, nie na końcu: po każdym zadaniu, decyzji, odkryciu, błędzie z testu ręcznego i nowym wymaganiu właściciela dopisz wpis (stan, znane problemy, decyzje, dziennik, następne kroki). Nie wpisuj tam tokenu ani wartości z `.env`.
