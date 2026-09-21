import asyncio
import itertools
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.exceptions import TelegramEntityTooLarge
from aiogram.methods import GetFile, SendMessage
from aiogram.types import (
    Animation,
    Chat,
    Document,
    File,
    Message,
    PhotoSize,
    Update,
    User,
    Video,
)

WLASCICIEL_ID = 111222333
OBCY_ID = 999888777
CZAT_ID = 111222333
TOKEN_TESTOWY = "123456:TEST-TOKEN"

_licznik_message_id = itertools.count(1)
_licznik_update_id = itertools.count(1)


def nastepny_message_id() -> int:
    return next(_licznik_message_id)


def zbuduj_uzytkownika(id_uzytkownika: int) -> User:
    return User(id=id_uzytkownika, is_bot=False, first_name="Test")


def zbuduj_wiadomosc(od_id: int = WLASCICIEL_ID, message_id: int | None = None, **kwargs) -> Message:
    dane = dict(
        message_id=message_id if message_id is not None else nastepny_message_id(),
        date=datetime.now(timezone.utc),
        chat=Chat(id=CZAT_ID, type="private"),
        from_user=zbuduj_uzytkownika(od_id),
    )
    dane.update(kwargs)
    return Message(**dane)


def zbuduj_update(wiadomosc: Message, edytowana: bool = False) -> Update:
    pole = "edited_message" if edytowana else "message"
    return Update(update_id=next(_licznik_update_id), **{pole: wiadomosc})


def zdjecie(file_id: str, file_unique_id: str, file_size: int | None = None) -> list[PhotoSize]:
    return [
        PhotoSize(file_id=f"{file_id}_maly", file_unique_id=f"{file_unique_id}_maly", width=90, height=90, file_size=1000),
        PhotoSize(file_id=file_id, file_unique_id=file_unique_id, width=1080, height=1920, file_size=file_size),
    ]


def dokument(
    file_id: str,
    file_unique_id: str,
    nazwa: str | None = None,
    mime: str | None = None,
    file_size: int | None = None,
) -> Document:
    return Document(file_id=file_id, file_unique_id=file_unique_id, file_name=nazwa, mime_type=mime, file_size=file_size)


def klip(file_id: str, file_unique_id: str, nazwa: str | None = None, file_size: int | None = None) -> Video:
    return Video(
        file_id=file_id,
        file_unique_id=file_unique_id,
        width=1080,
        height=1920,
        duration=5,
        file_name=nazwa,
        file_size=file_size,
    )


def animacja(file_id: str, file_unique_id: str, nazwa: str | None = None, file_size: int | None = None) -> Animation:
    return Animation(
        file_id=file_id,
        file_unique_id=file_unique_id,
        width=1080,
        height=1920,
        duration=5,
        file_name=nazwa,
        file_size=file_size,
    )


class SesjaTestowa(BaseSession):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wywolania: list = []
        self.opoznienie_pobierania_s = 0.0
        self.tresc_pliku = b"zawartosc-testowa"
        self.plik_za_duzy = False

    async def close(self) -> None:
        return None

    async def make_request(self, bot, method, timeout=None):
        self.wywolania.append(method)
        if isinstance(method, GetFile):
            if self.opoznienie_pobierania_s:
                await asyncio.sleep(self.opoznienie_pobierania_s)
            if self.plik_za_duzy:
                raise TelegramEntityTooLarge(method=method, message="file is too big")
            return File(file_id=method.file_id, file_unique_id="plik_unikalny", file_path=f"sciezka/{method.file_id}")
        if isinstance(method, SendMessage):
            return Message(
                message_id=nastepny_message_id(),
                date=datetime.now(timezone.utc),
                chat=Chat(id=method.chat_id, type="private"),
                text=method.text,
            )
        return True

    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        if self.opoznienie_pobierania_s:
            await asyncio.sleep(self.opoznienie_pobierania_s)
        yield self.tresc_pliku


def zbuduj_bota() -> Bot:
    return Bot(token=TOKEN_TESTOWY, session=SesjaTestowa())


def nazwy_wywolan(sesja: SesjaTestowa) -> list[str]:
    return [type(metoda).__name__ for metoda in sesja.wywolania]
