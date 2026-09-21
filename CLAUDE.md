# edity-bot

Bot na Telegramie, który montuje edity wideo 9:16 z materiałów właściciela według wzorcowego editu, z muzyką royalty free.
Plany, pomiary i notatki: `Pomiary/` (poza gitem). Mapa planów: `Pomiary/PLAN_EDITY_0_MAPA.md`. Wyciąg z Telegram Bot API: `Pomiary/TELEGRAM_BOT_API.md`.

## Reguły
1. Każdą zmianę w kodzie mierzy skrypt w `Pomiary/measure_<temat>.py`. Komentarze wolno pisać tylko w plikach pomiarowych.
2. Zakaz komentarzy i docstringów w `src/` i `tests/`.
3. Nazwy funkcji bez `_` na początku, nazewnictwo po polsku.
4. W komunikatach bota, README i commitach bez myślników i półpauz wewnątrz zdań: zamiast nich dwukropek, przecinek, nawias albo osobne zdanie.
5. Commity bez wzmianek o AI i bez Co-Authored-By.
6. Przy pracy z planu otwieraj tylko pliki wskazane w zadaniu, nie przeszukuj repo.
7. Z wzorcowego editu bierzemy tylko strukturę i styl. Jego obraz i dźwięk nigdy nie trafiają do wyniku.
8. Raport na koniec pracy: wniosek w pierwszym zdaniu, liczby, problemy, opcje do decyzji. Bez relacjonowania drogi.
9. Repo tylko lokalne: bez GitHuba i jakiegokolwiek zdalnego repozytorium (`git remote`, `git push`, `gh`). Na serwer kod trafia przez `wdroz.ps1` (archiwum i scp).
10. `.env` zawiera prawdziwy token bota: nie otwieraj go bez potrzeby, nie przepisuj jego wartości do innych plików, logów ani raportów, nigdy go nie commituj.
11. Projekt nie ma związku z allegro-rag-agents: nie korzystaj z jego plików ani skryptów.
