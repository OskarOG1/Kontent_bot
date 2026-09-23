# edity bot

Bot na Telegramie, który montuje edity wideo 9:16 z materiałów właściciela według wzorcowego editu, z muzyką royalty free.

## Uruchomienie lokalne

1. Utwórz środowisko wirtualne: `python -m venv venv`, potem aktywuj je (`venv\Scripts\activate` na Windows).
2. Zainstaluj zależności: `pip install -r requirements.txt -r requirements-test.txt`.
3. Skopiuj `.env.example` do `.env` i uzupełnij `BOT_TOKEN` (token bota z BotFather) oraz `OWNER_ID` (Twój numeryczny ID w Telegramie).
4. Uruchom bota: `python src/bot.py`.
5. Uruchom testy: `python -m pytest -q`.

## Wymagania

Python 3.13, ffmpeg i ffprobe 8.1 dostępne w PATH.

## Dane

Materiały, projekty i wzory trzymane są w katalogu `dane/` (poza gitem, ścieżka konfigurowalna przez `KATALOG_DANYCH`). Wyniki pomiarów trafiają do `outputs/`.

## Wdrożenie

Bot działa na VPS w Dockerze (obraz `python:3.13-slim` z ffmpeg, `libgl1` i `libglib2.0-0`), uruchomiony jako `docker compose` z usługami `bot` i `bot-api`. Kod trafia na serwer bez GitHuba: skrypt `wdroz.ps1` pakuje gałąź `main` (`git archive main`), kopiuje archiwum na serwer i tam je rozpakowuje, po czym uruchamia `docker compose up -d --build`. Przed pakowaniem skrypt porównuje lokalny `main` z `origin/main` i zatrzymuje się, gdy się różnią (synchronizuj przez `git checkout main`, `git pull`), chyba że podano `-Wymus`.

```powershell
.\wdroz.ps1 -Serwer root@<adres>
```

Katalog `dane/` na serwerze jest zamontowany jako wolumen poza obrazem, a plik `.env` trafia na serwer osobno (`scp`), nie przez `wdroz.ps1`. Pełna procedura pierwszego wdrożenia (katalogi, `.env`, muzyka, restart) jest opisana w `Pomiary/PLAN_EDITY_7_WDROZENIE.md`.
