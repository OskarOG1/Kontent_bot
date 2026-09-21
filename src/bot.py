import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from time import monotonic

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError, TelegramEntityTooLarge
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, Message, ReactionTypeEmoji

import komunikaty
import konfiguracja as konfiguracja_modul
import kolejka as kolejka_modul
import magazyn
from konfiguracja import Konfiguracja

log = logging.getLogger("bot")

LIMIT_SERWERA_TELEGRAM_MB = 20
LIMIT_ANALIZY_S = 300
SKRYPT_ANALIZY = Path(__file__).resolve().parent / "analyze.py"


class Stany(StatesGroup):
    czekam_na_wzor = State()
    zbieram = State()


def efektywny_limit_mb(konf: Konfiguracja) -> int:
    return min(konf.limit_pobierania_mb, LIMIT_SERWERA_TELEGRAM_MB)


def to_wideo(message: Message) -> bool:
    if message.video or message.animation:
        return True
    if message.document and (message.document.mime_type or "").startswith("video/"):
        return True
    return False


def to_material(message: Message) -> bool:
    return bool(message.photo or message.document or message.video or message.animation)


def rozpoznaj_zalacznik(message: Message):
    if message.photo:
        rozmiar = max(message.photo, key=lambda ps: ps.width * ps.height)
        return "zdjecie", "jpg", rozmiar.file_id, rozmiar.file_unique_id, rozmiar.file_size
    if message.video:
        nazwa = message.video.file_name
        rozszerzenie = Path(nazwa).suffix.lstrip(".").lower() if nazwa else "mp4"
        return "klip", rozszerzenie, message.video.file_id, message.video.file_unique_id, message.video.file_size
    if message.animation:
        nazwa = message.animation.file_name
        rozszerzenie = Path(nazwa).suffix.lstrip(".").lower() if nazwa else "mp4"
        return (
            "klip",
            rozszerzenie,
            message.animation.file_id,
            message.animation.file_unique_id,
            message.animation.file_size,
        )
    if message.document:
        typ = magazyn.typ_pliku(message.document.file_name, message.document.mime_type)
        if typ is None:
            return None
        rozszerzenie = (
            Path(message.document.file_name).suffix.lstrip(".").lower()
            if message.document.file_name
            else ("jpg" if typ == "zdjecie" else "mp4")
        )
        return typ, rozszerzenie, message.document.file_id, message.document.file_unique_id, message.document.file_size
    return None


async def pobierz_plik(bot: Bot, file_id: str, cel: Path) -> None:
    cel.parent.mkdir(parents=True, exist_ok=True)
    tymczasowy = cel.with_name(cel.name + ".part")
    try:
        await bot.download(file_id, destination=tymczasowy)
    except Exception:
        tymczasowy.unlink(missing_ok=True)
        raise
    os.replace(tymczasowy, cel)


async def bezpiecznie_zareaguj(message: Message) -> None:
    try:
        await message.react([ReactionTypeEmoji(emoji="👍")])
    except TelegramAPIError:
        log.exception("nie udalo sie ustawic reakcji")


async def obsluz_start(message: Message) -> None:
    await message.answer(komunikaty.POMOC)


async def obsluz_cmd_wzor(message: Message, state: FSMContext) -> None:
    await state.set_state(Stany.czekam_na_wzor)
    await message.answer(komunikaty.WZOR_PROSBA)


async def obsluz_cmd_nowy(message: Message, state: FSMContext, konf: Konfiguracja, projekt_aktywny: dict) -> None:
    katalog_projektu = magazyn.nowy_projekt(konf.katalog_danych)
    projekt_id = katalog_projektu.name
    projekt_aktywny["id"] = projekt_id
    await state.set_state(Stany.zbieram)
    await state.update_data(projekt_id=projekt_id)
    await message.answer(komunikaty.NOWY_PROJEKT)


async def obsluz_cmd_gotowe(
    message: Message,
    state: FSMContext,
    konf: Konfiguracja,
    projekt_aktywny: dict,
    pobrania_w_toku: dict,
) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if not projekt_id:
        await message.answer(komunikaty.BRAK_STANU)
        return

    await asyncio.sleep(1)
    limit_czasu = monotonic() + 120
    while pobrania_w_toku.get(projekt_id, 0) > 0 and monotonic() < limit_czasu:
        await asyncio.sleep(0.05)

    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    materialy = magazyn.lista_materialow(katalog_projektu)
    if not materialy:
        await message.answer(komunikaty.BRAK_MATERIALOW)
        return

    dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
    dane_projektu["stan"] = "w_kolejce"
    magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    await state.clear()
    projekt_aktywny["id"] = None

    zdjecia = sum(1 for wpis in materialy if wpis["typ"] == "zdjecie")
    klipy = sum(1 for wpis in materialy if wpis["typ"] == "klip")
    linie = len(dane_projektu.get("teksty", []))
    await message.answer(komunikaty.projekt_w_kolejce(zdjecia, klipy, linie))


async def obsluz_cmd_anuluj(message: Message, state: FSMContext, konf: Konfiguracja, projekt_aktywny: dict) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if projekt_id:
        katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        dane_projektu["stan"] = "anulowany"
        magazyn.zapisz_projekt(katalog_projektu, dane_projektu)
    await state.clear()
    projekt_aktywny["id"] = None
    await message.answer(komunikaty.PROJEKT_ANULOWANY)


async def obsluz_cmd_status(
    message: Message,
    state: FSMContext,
    konf: Konfiguracja,
    kolejka_obiekt: kolejka_modul.Kolejka,
) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    linie = []
    if projekt_id:
        katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
        materialy = magazyn.lista_materialow(katalog_projektu)
        linie.append(komunikaty.status_projektu(projekt_id, len(materialy)))
    else:
        linie.append(komunikaty.STATUS_BRAK_PROJEKTU)
    katalog_wzorow = konf.katalog_danych / "wzory"
    liczba_wzorow = len(list(katalog_wzorow.iterdir())) if katalog_wzorow.exists() else 0
    linie.append(komunikaty.status_kolejki(kolejka_obiekt.dlugosc(), liczba_wzorow))
    await message.answer("\n".join(linie))


async def bezpiecznie_odpisz(message: Message, tekst: str) -> None:
    try:
        await message.answer(tekst)
    except TelegramAPIError:
        log.exception("nie udalo sie wyslac odpowiedzi")


def pierwsza_linia(tekst: str) -> str:
    for linia in tekst.splitlines():
        if linia.strip():
            return linia.strip()
    return ""


def podsumuj_wzor(dane: dict) -> str:
    zrodlo = dane["zrodlo"]
    liczba_ujec = len(dane["ciecia_s"])
    return komunikaty.podsumowanie_wzoru(
        zrodlo["czas_s"],
        liczba_ujec,
        zrodlo["czas_s"] / liczba_ujec,
        dane["tempo_bpm"],
        zrodlo["ma_dzwiek"],
    )


async def analizuj_wzor_w_tle(message: Message, zrodlo: Path, wzor_json: Path, zapowiedz: asyncio.Event) -> None:
    await zapowiedz.wait()
    wynik = await kolejka_modul.uruchom(
        [sys.executable, str(SKRYPT_ANALIZY), str(zrodlo), str(wzor_json)],
        limit_s=LIMIT_ANALIZY_S,
    )
    if wynik.przekroczono_czas:
        await bezpiecznie_odpisz(message, komunikaty.ANALIZA_PRZEKROCZONO_CZAS)
        return
    if wynik.kod != 0:
        opis = pierwsza_linia(wynik.stderr) or f"kod {wynik.kod}"
        await bezpiecznie_odpisz(message, komunikaty.blad_analizy(opis))
        return
    try:
        dane = json.loads(wzor_json.read_text(encoding="utf-8"))
        tekst = podsumuj_wzor(dane)
    except (OSError, ValueError, KeyError, ZeroDivisionError):
        log.exception("nie udalo sie odczytac wyniku analizy, wzor=%s", wzor_json)
        await bezpiecznie_odpisz(message, komunikaty.blad_analizy("nie udało się odczytać wyniku"))
        return
    await bezpiecznie_odpisz(message, tekst)


async def obsluz_wzor_plik(
    message: Message,
    state: FSMContext,
    konf: Konfiguracja,
    kolejka_obiekt: kolejka_modul.Kolejka,
) -> None:
    zalacznik = rozpoznaj_zalacznik(message)
    if zalacznik is None:
        await message.answer(komunikaty.WZOR_NIEPOPRAWNY_TYP)
        return
    _, rozszerzenie, file_id, _, rozmiar = zalacznik
    limit_mb = efektywny_limit_mb(konf)
    if rozmiar is not None and rozmiar > limit_mb * 1024 * 1024:
        await message.answer(komunikaty.limit_rozmiaru(rozmiar, limit_mb))
        return

    katalog_wzoru = magazyn.nowy_wzor(konf.katalog_danych)
    cel = katalog_wzoru / f"zrodlo.{rozszerzenie}"
    try:
        await pobierz_plik(message.bot, file_id, cel)
    except TelegramEntityTooLarge:
        await message.answer(komunikaty.limit_rozmiaru(None, limit_mb))
        return
    except Exception:
        log.exception("pobieranie wzoru nie powiodlo sie, file_id=%s", file_id)
        await message.answer(komunikaty.BLAD_POBIERANIA)
        return

    await state.clear()
    zapowiedz = asyncio.Event()

    async def zadanie() -> None:
        await analizuj_wzor_w_tle(message, cel, katalog_wzoru / "wzor.json", zapowiedz)

    pozycja = await kolejka_obiekt.dodaj(zadanie)
    try:
        await message.answer(komunikaty.analizuje_wzor(pozycja))
    finally:
        zapowiedz.set()


async def obsluz_wzor_niepoprawny(message: Message) -> None:
    await message.answer(komunikaty.WZOR_NIEPOPRAWNY_TYP)


async def obsluz_material(
    message: Message,
    state: FSMContext,
    konf: Konfiguracja,
    projekt_aktywny: dict,
    pobrania_w_toku: dict,
    reagowane_albumy: set,
) -> None:
    projekt_id = projekt_aktywny["id"]
    pobrania_w_toku[projekt_id] = pobrania_w_toku.get(projekt_id, 0) + 1
    try:
        zalacznik = rozpoznaj_zalacznik(message)
        if zalacznik is None:
            return
        _, rozszerzenie, file_id, file_unique_id, rozmiar = zalacznik
        limit_mb = efektywny_limit_mb(konf)

        if rozmiar is not None and rozmiar > limit_mb * 1024 * 1024:
            await message.answer(komunikaty.limit_rozmiaru(rozmiar, limit_mb))
            return

        katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
        cel = magazyn.sciezka_materialu(katalog_projektu, message.message_id, file_unique_id, rozszerzenie)
        try:
            await pobierz_plik(message.bot, file_id, cel)
        except TelegramEntityTooLarge:
            await message.answer(komunikaty.limit_rozmiaru(None, limit_mb))
            return
        except Exception:
            log.exception("pobieranie materialu nie powiodlo sie, file_id=%s", file_id)
            await message.answer(komunikaty.BLAD_POBIERANIA)
            return

        if message.media_group_id:
            if message.media_group_id not in reagowane_albumy:
                reagowane_albumy.add(message.media_group_id)
                await bezpiecznie_zareaguj(message)
        else:
            await bezpiecznie_zareaguj(message)
    finally:
        pobrania_w_toku[projekt_id] -= 1


async def obsluz_tekst(message: Message, state: FSMContext, konf: Konfiguracja, blokada_projektu: asyncio.Lock) -> None:
    if message.text.startswith("/"):
        return
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if not projekt_id:
        return
    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    async with blokada_projektu:
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        dane_projektu["teksty"].append({"message_id": message.message_id, "tekst": message.text})
        dane_projektu["teksty"].sort(key=lambda wpis: wpis["message_id"])
        magazyn.zapisz_projekt(katalog_projektu, dane_projektu)


async def obsluz_plik_bez_stanu(message: Message) -> None:
    await message.answer(komunikaty.BRAK_STANU)


def wlasciciel(wlasciciel_id: int):
    def sprawdz(zdarzenie) -> bool:
        return zdarzenie.from_user is not None and zdarzenie.from_user.id == wlasciciel_id

    return sprawdz


def zbuduj_router() -> Router:
    router = Router()
    router.message.register(obsluz_start, Command("start"))
    router.message.register(obsluz_cmd_wzor, Command("wzor"))
    router.message.register(obsluz_cmd_nowy, Command("nowy"))
    router.message.register(obsluz_cmd_gotowe, Command("gotowe"))
    router.message.register(obsluz_cmd_anuluj, Command("anuluj"))
    router.message.register(obsluz_cmd_status, Command("status"))
    router.message.register(obsluz_wzor_plik, StateFilter(Stany.czekam_na_wzor), to_wideo)
    router.message.register(obsluz_wzor_niepoprawny, StateFilter(Stany.czekam_na_wzor))
    router.message.register(obsluz_material, StateFilter(Stany.zbieram), to_material)
    router.message.register(obsluz_tekst, StateFilter(Stany.zbieram), F.text)
    router.message.register(obsluz_plik_bez_stanu, to_material)
    return router


def utworz_dispatcher(konf: Konfiguracja, kolejka_obiekt: kolejka_modul.Kolejka) -> Dispatcher:
    dyspozytor = Dispatcher(storage=MemoryStorage())
    dyspozytor.message.filter(wlasciciel(konf.wlasciciel_id))
    dyspozytor.edited_message.filter(wlasciciel(konf.wlasciciel_id))
    dyspozytor.include_router(zbuduj_router())
    dyspozytor["konf"] = konf
    dyspozytor["kolejka_obiekt"] = kolejka_obiekt
    dyspozytor["projekt_aktywny"] = {"id": None}
    dyspozytor["pobrania_w_toku"] = {}
    dyspozytor["reagowane_albumy"] = set()
    dyspozytor["blokada_projektu"] = asyncio.Lock()
    return dyspozytor


async def uruchom_bota(konf: Konfiguracja) -> None:
    bot = Bot(token=konf.token, default=DefaultBotProperties(parse_mode=None))
    kolejka_obiekt = kolejka_modul.Kolejka()
    kolejka_obiekt.start()
    dyspozytor = utworz_dispatcher(konf, kolejka_obiekt)
    await bot.set_my_commands([BotCommand(command=nazwa, description=opis) for nazwa, opis in komunikaty.KOMENDY])
    await dyspozytor.start_polling(bot)


def main() -> None:
    try:
        konf = konfiguracja_modul.wczytaj()
    except ValueError as blad:
        print(f"Blad konfiguracji: {blad}", file=sys.stderr)
        sys.exit(1)
    logging.basicConfig(level=logging.INFO)
    asyncio.run(uruchom_bota(konf))


if __name__ == "__main__":
    main()
