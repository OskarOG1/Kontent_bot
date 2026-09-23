# Telegram Bot API: wyciąg dla bota edity

Źródło: https://core.telegram.org/bots/api, odczyt 2026-09-21, Bot API 10.3 (24.08.2026). Tylko to, czego używa bot. Kotwicę sekcji dopisz do adresu po `#` (np. `#getfile`). Zdania oznaczone „(poza dokumentacją)” pochodzą z innych źródeł i są niepewne.

## Limity plików

| Operacja | Serwer Telegrama | Lokalny serwer Bot API |
|---|---|---|
| Pobranie pliku przez bota (`getFile`) | 20 MB | bez limitu; `file_path` to ścieżka bezwzględna na dysku serwera, pobieranie zbędne |
| Wysłanie pliku jako multipart (`sendDocument`, `sendVideo`) | 50 MB, zdjęcie 10 MB | do 2000 MB, także ze ścieżki lokalnej (`file://`) |
| Wysłanie przez URL | zdjęcie 5 MB, reszta 20 MB; `sendDocument` przez URL tylko PDF i ZIP | |
| Ponowne wysłanie przez `file_id` | bez limitu; typu nie da się zmienić (wideo nie pójdzie jako dokument) | |

- Link z `getFile` działa co najmniej godzinę, potem wywołaj `getFile` ponownie.
- `getFile` może nie zachować nazwy pliku ani MIME: zapisz je z obiektu wiadomości.
- `file_size` jest opcjonalne w każdym typie pliku. Kontrola rozmiaru przed pobraniem nie wystarczy, obsłuż też błąd `getFile` dla zbyt dużego pliku.

## Lokalny serwer Bot API (`#using-a-local-bot-api-server`)

- Kod: github.com/tdlib/telegram-bot-api. Uruchomienie wymaga `api_id` i `api_hash` z my.telegram.org (poza dokumentacją).
- Przed pierwszym startem na lokalnym serwerze wywołaj `logOut` na serwerze Telegrama, inaczej nie ma gwarancji, że bot dostanie aktualizacje. Po `logOut` przez 10 minut nie da się wrócić na serwer Telegrama (`#logout`).
- `close` zamyka instancję przed przeniesieniem między lokalnymi serwerami; przez pierwsze 10 minut po starcie zwraca 429 (`#close`).

## Wiadomość (`#message`): pola używane przez bota

- `message_id`: zwykle rośnie w obrębie czatu, ale bywa 0 (wiadomości efemeryczne i zaplanowane). Nie używaj go jako jedynego klucza nazwy pliku, łącz z `file_unique_id`.
- `from`, `chat`, `date`, `text`, `caption`.
- `media_group_id`: wspólny identyfikator albumu. Każdy element albumu przychodzi jako osobna aktualizacja.
- `photo`: tablica `PhotoSize` w kilku rozmiarach; zwyczajowo największy jest ostatni (dokumentacja nie mówi tego wprost). Zdjęcie wysłane jako „zdjęcie” klient kompresuje, oryginał przychodzi tylko jako plik (poza dokumentacją, z KONTEKST_PROJEKTU).
- `document`: `file_id`, `file_unique_id`, opcjonalnie `file_name`, `mime_type`, `file_size`.
- `video`: `width`, `height`, `duration` w sekundach (wszystko podane przez nadawcę), opcjonalnie `file_name`, `mime_type`, `file_size`.
- `animation`: gdy jest ustawione, `document` też jest ustawione.
- `live_photo` (nowe w 10.x): gdy jest ustawione, `photo` też jest ustawione.
- `video_note`: okrągłe wideo.
- `file_unique_id` jest stały w czasie i między botami, ale nie służy do pobierania. `file_id` służy do pobierania i jest inny dla każdego bota.

## Metody

- `getUpdates` (long polling): `offset`, `limit` od 1 do 100, `timeout`, `allowed_updates`. Nie działa przy ustawionym webhooku. Dwie instancje z tym samym tokenem na pollingu wzajemnie się wyrzucają, błąd 409 Conflict (poza dokumentacją, znane z praktyki).
- `sendDocument`: do 50 MB, `caption` do 1024 znaków, miniatura JPEG poniżej 200 kB i najwyżej 320 px.
- `sendVideo`: do 50 MB, `supports_streaming`, opcjonalnie `width`, `height`, `duration`.
- `sendChatAction`: status trwa do 5 s albo do następnej wiadomości bota. Akcje: `typing`, `upload_document`, `upload_video`, `record_video`, `upload_photo`.
- `setMessageReaction`: bot ustawia najwyżej jedną reakcję na wiadomość. Reakcja na wiadomość z albumu trafia na pierwszą wiadomość albumu. Emoji z zamkniętej listy (`#reactiontypeemoji`), są na niej m.in. 👍 👌 🔥 ✍ 🫡 🏆 🎉 ❤.
- `setMyCommands`: do 100 komend. `BotCommand.command` ma od 1 do 32 znaków, tylko małe litery angielskie, cyfry i podkreślenie, dlatego `/wzor`, a nie `/wzór`. Opis od 1 do 256 znaków.

## Aktualizacje (`#update`)

Typy istotne dla bota: `message`, `edited_message`, ewentualnie `callback_query`. Filtr dostępu musi objąć każdy typ, który bot obsługuje. Gdy `allowed_updates` nie podano, obowiązuje poprzednie ustawienie.

## Błędy (`#making-requests`, `#responseparameters`)

Odpowiedź ma `ok`, `description`, `error_code` (znaczenie kodów może się zmienić) i opcjonalnie `parameters`. `parameters.retry_after` mówi, ile sekund czekać po przekroczeniu limitu zapytań.

## Zmiany 10.0 do 10.3 (maj do sierpnia 2026)

Tryb gościa, wiadomości efemeryczne, Rich Messages, media w ankietach. Dla bota edity bez znaczenia. W 10.3 metody `send*` dostały `ephemeral_message_parameters` w miejsce `receiver_user_id` i `callback_query_id`, co dotyczy tylko wiadomości efemerycznych.
