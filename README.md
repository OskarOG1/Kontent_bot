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
