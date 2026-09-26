import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from time import monotonic

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramAPIError, TelegramEntityTooLarge
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReactionTypeEmoji,
)

import komunikaty
import konfiguracja as konfiguracja_modul
import kolejka as kolejka_modul
import magazyn
import music
import render
import tekst
from konfiguracja import Konfiguracja

log = logging.getLogger("bot")

LIMIT_SERWERA_TELEGRAM_MB = 20
LIMIT_SERWERA_TELEGRAM_LOKALNY_MB = 2500
LIMIT_WYSYLKI_TELEGRAM_MB = 50
LIMIT_WYSYLKI_TELEGRAM_LOKALNY_MB = 2000
LIMIT_ANALIZY_S = 300
LIMIT_RENDERU_S = 900
LIMIT_GETFILE_LOKALNY_S = 1800
LIMIT_SLOW_RYTM = 12
LIMIT_ZNAKOW_PIONOWO = 40
LIMIT_WARIANTOW = 5
LIMIT_WZOROW_WSZYSTKIE = 10
ROZMIAR_KAWALKA_KOPII_B = 64 * 1024
SKRYPT_ANALIZY = Path(__file__).resolve().parent / "analyze.py"
SKRYPT_RENDERU = Path(__file__).resolve().parent / "render.py"


class Stany(StatesGroup):
    czekam_na_wzor = State()
    czekam_na_nakladke = State()
    czekam_na_plansze = State()
    czekam_na_znak = State()
    zbieram = State()


def efektywny_limit_mb(konf: Konfiguracja) -> int:
    limit_serwera = LIMIT_SERWERA_TELEGRAM_LOKALNY_MB if konf.telegram_api_url else LIMIT_SERWERA_TELEGRAM_MB
    return min(konf.limit_pobierania_mb, limit_serwera)


def efektywny_limit_wysylki_mb(konf: Konfiguracja) -> int:
    limit_serwera = LIMIT_WYSYLKI_TELEGRAM_LOKALNY_MB if konf.telegram_api_url else LIMIT_WYSYLKI_TELEGRAM_MB
    return min(konf.limit_wysylki_mb, limit_serwera)


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


def kopiuj_plik(zrodlo: Path, cel: Path, rozmiar_kawalka: int) -> None:
    with open(zrodlo, "rb") as plik_zrodlowy, open(cel, "wb") as plik_docelowy:
        shutil.copyfileobj(plik_zrodlowy, plik_docelowy, length=rozmiar_kawalka)


async def pobierz_plik_lokalnie(bot: Bot, file_id: str, tymczasowy: Path) -> None:
    plik = await bot.get_file(file_id, request_timeout=LIMIT_GETFILE_LOKALNY_S)
    zrodlo = Path(plik.file_path)
    await asyncio.to_thread(kopiuj_plik, zrodlo, tymczasowy, ROZMIAR_KAWALKA_KOPII_B)
    try:
        zrodlo.unlink()
    except OSError:
        log.warning("nie udalo sie usunac pliku zrodlowego na serwerze lokalnym, sciezka=%s", zrodlo)


async def pobierz_plik(bot: Bot, file_id: str, cel: Path) -> None:
    cel.parent.mkdir(parents=True, exist_ok=True)
    tymczasowy = cel.with_name(cel.name + ".part")
    try:
        if bot.session.api.is_local:
            await pobierz_plik_lokalnie(bot, file_id, tymczasowy)
        else:
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


async def renderuj_zadanie_w_tle(
    bot: Bot,
    chat_id: int,
    katalog_projektu: Path,
    indeks_zadania: int,
    wzor_json: Path,
    katalog_muzyki: Path,
    konf: Konfiguracja,
    zapowiedz: asyncio.Event,
    nakladka: Path | None = None,
    plansza: Path | None = None,
    znak: Path | None = None,
) -> None:
    await zapowiedz.wait()
    dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
    zadanie = dane_projektu["zadania"][indeks_zadania]
    zadanie["stan"] = "renderowanie"
    dane_projektu["stan"] = magazyn.stan_z_zadan(dane_projektu["zadania"])
    magazyn.zapisz_projekt(katalog_projektu, dane_projektu)
    await bezpiecznie_wyslij(bot, chat_id, komunikaty.MONTUJE)

    limit_mb = efektywny_limit_wysylki_mb(konf)
    wynik_mp4 = katalog_projektu / zadanie["plik"]
    argumenty = [
        sys.executable, str(SKRYPT_RENDERU),
        "--wzor", str(wzor_json), "--projekt", str(katalog_projektu),
        "--muzyka", str(katalog_muzyki), "--wyjscie", str(wynik_mp4),
        "--limit-mb", str(limit_mb), "--sila-koloru", str(konf.sila_koloru),
        "--styl-tekstu", konf.styl_tekstu, "--pozycja-tekstu", konf.pozycja_tekstu,
        "--wariant", str(zadanie["wariant"]),
    ]
    if nakladka is not None:
        argumenty += ["--nakladka", str(nakladka)]
    if plansza is not None:
        argumenty += ["--plansza", str(plansza)]
    if znak is not None:
        argumenty += ["--znak", str(znak)]
    wynik = await kolejka_modul.uruchom(argumenty, limit_s=LIMIT_RENDERU_S)

    def zapisz_wynik_zadania(stan: str, wynik: str | None = None, blad: str | None = None) -> None:
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        zadanie = dane_projektu["zadania"][indeks_zadania]
        zadanie["stan"] = stan
        zadanie["wynik"] = wynik
        zadanie["blad"] = blad
        dane_projektu["stan"] = magazyn.stan_z_zadan(dane_projektu["zadania"])
        magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    if wynik.przekroczono_czas or wynik.kod != 0:
        opis = "przekroczono limit czasu" if wynik.przekroczono_czas else (pierwsza_linia(wynik.stderr) or f"kod {wynik.kod}")
        zapisz_wynik_zadania("blad", blad=opis)
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.blad_renderu(opis))
        return

    try:
        podsumowanie = json.loads(wynik_mp4.with_suffix(".json").read_text(encoding="utf-8"))
        nazwa = magazyn.nazwa_wzoru(wzor_json.parent)
        podpis = komunikaty.podsumowanie_wariantu(nazwa, podsumowanie.get("wariant", zadanie["wariant"]), podsumowanie)
    except (OSError, ValueError, KeyError):
        log.exception("nie udalo sie odczytac podsumowania renderu, wynik=%s", wynik_mp4)
        podpis = None

    try:
        await bot.send_document(chat_id, FSInputFile(wynik_mp4), caption=podpis)
    except TelegramEntityTooLarge:
        rozmiar = wynik_mp4.stat().st_size if wynik_mp4.exists() else None
        zapisz_wynik_zadania("blad", blad="plik za duzy")
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.limit_rozmiaru(rozmiar, limit_mb))
        return
    except Exception:
        log.exception("wysylka wyniku nie powiodla sie")
        zapisz_wynik_zadania("blad", blad="wysylka nieudana")
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.BLAD_WYSYLKI)
        return

    zapisz_wynik_zadania("gotowy", wynik=wynik_mp4.name)


def zbuduj_zadania_gotowe(argument: str, konf: Konfiguracja) -> tuple[list[tuple[str, int, str]] | None, str | None]:
    if not argument:
        wzor_json = magazyn.aktywny_wzor(konf.katalog_danych)
        if wzor_json is None:
            return None, komunikaty.BRAK_WZORU
        wzor_id = wzor_json.parent.name
        return [(wzor_id, 0, "wynik.mp4")], None
    if argument.isdigit():
        liczba = int(argument)
        if not (2 <= liczba <= LIMIT_WARIANTOW):
            return None, komunikaty.GOTOWE_UZYCIE
        wzor_json = magazyn.aktywny_wzor(konf.katalog_danych)
        if wzor_json is None:
            return None, komunikaty.BRAK_WZORU
        wzor_id = wzor_json.parent.name
        return [(wzor_id, wariant, f"wynik_{wzor_id}_{wariant}.mp4") for wariant in range(liczba)], None
    if argument == "wszystkie":
        wzory = magazyn.lista_wzorow(konf.katalog_danych)[:LIMIT_WZOROW_WSZYSTKIE]
        if not wzory:
            return None, komunikaty.BRAK_WZORU
        return [
            (wzor_json.parent.name, 0, f"wynik_{wzor_json.parent.name}_0.mp4") for wzor_json in wzory
        ], None
    return None, komunikaty.GOTOWE_UZYCIE


async def zlecz_zadania_renderu(
    bot: Bot,
    chat_id: int,
    katalog_projektu: Path,
    zadania_wejsciowe: list[tuple[str, int, str]],
    konf: Konfiguracja,
    kolejka_obiekt: kolejka_modul.Kolejka,
) -> tuple[int, asyncio.Event]:
    katalog_muzyki = konf.katalog_danych / "muzyka"
    zapowiedz = asyncio.Event()
    pierwsza_pozycja = None
    for indeks, (wzor_id, _wariant, _plik) in enumerate(zadania_wejsciowe):
        wzor_json = konf.katalog_danych / "wzory" / wzor_id / "wzor.json"
        nakladka = magazyn.plik_zasobu(konf.katalog_danych, "nakladki", wzor_id)
        plansza = magazyn.plik_zasobu(konf.katalog_danych, "plansze", wzor_id)
        znak = konf.katalog_danych / "znak_wodny.png"
        znak = znak if znak.is_file() else None

        async def zadanie(
            indeks=indeks, wzor_json=wzor_json, nakladka=nakladka, plansza=plansza, znak=znak,
        ) -> None:
            await renderuj_zadanie_w_tle(
                bot, chat_id, katalog_projektu, indeks, wzor_json, katalog_muzyki, konf, zapowiedz,
                nakladka, plansza, znak,
            )

        pozycja = await kolejka_obiekt.dodaj(zadanie)
        if pierwsza_pozycja is None:
            pierwsza_pozycja = pozycja
    return pierwsza_pozycja, zapowiedz


async def obsluz_cmd_gotowe(
    message: Message,
    state: FSMContext,
    konf: Konfiguracja,
    projekt_aktywny: dict,
    pobrania_w_toku: dict,
    kolejka_obiekt: kolejka_modul.Kolejka,
    command: CommandObject,
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

    argument = (command.args or "").strip()
    zadania_wejsciowe, blad = zbuduj_zadania_gotowe(argument, konf)
    if zadania_wejsciowe is None:
        await message.answer(blad)
        return

    katalog_muzyki = konf.katalog_danych / "muzyka"
    if not music.pliki_muzyki(katalog_muzyki):
        await message.answer(komunikaty.BRAK_MUZYKI)
        return

    dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
    dane_projektu["zadania"] = [
        {"wzor_id": wzor_id, "wariant": wariant, "plik": plik, "stan": "w_kolejce", "wynik": None, "blad": None}
        for wzor_id, wariant, plik in zadania_wejsciowe
    ]
    dane_projektu["stan"] = "w_kolejce"
    magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    await state.clear()
    projekt_aktywny["id"] = None

    zdjecia = sum(1 for wpis in materialy if wpis["typ"] == "zdjecie")
    klipy = sum(1 for wpis in materialy if wpis["typ"] == "klip")
    linie = len(dane_projektu.get("teksty", []))

    pozycja, zapowiedz = await zlecz_zadania_renderu(
        message.bot, message.chat.id, katalog_projektu, zadania_wejsciowe, konf, kolejka_obiekt,
    )
    try:
        await message.answer(komunikaty.projekt_w_kolejce(zdjecia, klipy, linie, pozycja))
    finally:
        zapowiedz.set()


async def obsluz_cmd_ponow(
    message: Message,
    konf: Konfiguracja,
    kolejka_obiekt: kolejka_modul.Kolejka,
    command: CommandObject,
) -> None:
    katalog_projektow = konf.katalog_danych / "projekty"
    kandydaci = []
    if katalog_projektow.is_dir():
        for katalog in katalog_projektow.iterdir():
            if not katalog.is_dir():
                continue
            try:
                dane = magazyn.wczytaj_projekt(katalog)
            except (OSError, ValueError):
                continue
            if dane.get("stan") in ("gotowy", "blad"):
                kandydaci.append(katalog)
    if not kandydaci:
        await message.answer(komunikaty.PONOW_BRAK_PROJEKTU)
        return
    katalog_projektu = max(kandydaci, key=lambda katalog: katalog.name)

    argument = (command.args or "").strip()
    zadania_wejsciowe, blad = zbuduj_zadania_gotowe(argument, konf)
    if zadania_wejsciowe is None:
        await message.answer(blad)
        return

    katalog_muzyki = konf.katalog_danych / "muzyka"
    if not music.pliki_muzyki(katalog_muzyki):
        await message.answer(komunikaty.BRAK_MUZYKI)
        return

    dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
    dane_projektu["zadania"] = [
        {"wzor_id": wzor_id, "wariant": wariant, "plik": plik, "stan": "w_kolejce", "wynik": None, "blad": None}
        for wzor_id, wariant, plik in zadania_wejsciowe
    ]
    dane_projektu["stan"] = "w_kolejce"
    magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    pozycja, zapowiedz = await zlecz_zadania_renderu(
        message.bot, message.chat.id, katalog_projektu, zadania_wejsciowe, konf, kolejka_obiekt,
    )
    try:
        await message.answer(komunikaty.ponowiony_w_kolejce(len(zadania_wejsciowe), pozycja))
    finally:
        zapowiedz.set()


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
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        liczba_linii = len(dane_projektu.get("teksty", []))
        linie.append(komunikaty.status_projektu(projekt_id, len(materialy), liczba_linii))
    else:
        linie.append(komunikaty.STATUS_BRAK_PROJEKTU)
    katalog_wzorow = konf.katalog_danych / "wzory"
    liczba_wzorow = 0
    if katalog_wzorow.exists():
        liczba_wzorow = sum(1 for katalog in katalog_wzorow.iterdir() if katalog.is_dir() and (katalog / "wzor.json").is_file())
    linie.append(komunikaty.status_kolejki(kolejka_obiekt.dlugosc(), liczba_wzorow))
    linie.append(komunikaty.status_muzyki(len(music.pliki_muzyki(konf.katalog_danych / "muzyka"))))
    wzor_aktywny = magazyn.aktywny_wzor(konf.katalog_danych)
    if wzor_aktywny is not None:
        wzor_id = wzor_aktywny.parent.name
        ma_nakladke = magazyn.plik_zasobu(konf.katalog_danych, "nakladki", wzor_id) is not None
        ma_plansze = magazyn.plik_zasobu(konf.katalog_danych, "plansze", wzor_id) is not None
        linie.append(komunikaty.status_zasobow_wzoru(wzor_id, ma_nakladke, ma_plansze))
    linie.append(komunikaty.status_znaku((konf.katalog_danych / "znak_wodny.png").is_file()))
    await message.answer("\n".join(linie))


def klawiatura_wzoru(wzor_id: str, nazwa: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"Wybierz {nazwa}", callback_data=f"wzor_wybierz:{wzor_id}"),
            InlineKeyboardButton(text=f"Usuń {nazwa}", callback_data=f"wzor_usun:{wzor_id}"),
        ]]
    )


async def obsluz_cmd_wzory(message: Message, konf: Konfiguracja) -> None:
    wzory = magazyn.lista_wzorow(konf.katalog_danych)[:20]
    if not wzory:
        await message.answer(komunikaty.BRAK_WZOROW)
        return
    wzor_aktywny = magazyn.aktywny_wzor(konf.katalog_danych)
    id_aktywnego = wzor_aktywny.parent.name if wzor_aktywny is not None else None
    for wzor_json in wzory:
        wzor_id = wzor_json.parent.name
        dane = json.loads(wzor_json.read_text(encoding="utf-8"))
        nazwa = magazyn.nazwa_wzoru(wzor_json.parent)
        linia = komunikaty.linia_wzoru(nazwa, wzor_id, dane, aktywny=(wzor_id == id_aktywnego))
        await message.answer(linia, reply_markup=klawiatura_wzoru(wzor_id, nazwa))


async def obsluz_wzor_wybierz(callback: CallbackQuery, konf: Konfiguracja) -> None:
    wzor_id = callback.data.split(":", 1)[1]
    magazyn.ustaw_aktywny_wzor(konf.katalog_danych, wzor_id)
    nazwa = magazyn.nazwa_wzoru(konf.katalog_danych / "wzory" / wzor_id)
    await callback.answer()
    await callback.message.edit_text(komunikaty.wzor_wybrany(nazwa))


async def obsluz_wzor_usun_pytanie(callback: CallbackQuery, konf: Konfiguracja) -> None:
    wzor_id = callback.data.split(":", 1)[1]
    nazwa = magazyn.nazwa_wzoru(konf.katalog_danych / "wzory" / wzor_id)
    klawiatura = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=f"Tak, usuń {nazwa}", callback_data=f"wzor_usun_potwierdz:{wzor_id}"),
        ]]
    )
    await callback.answer()
    await callback.message.edit_text(komunikaty.wzor_usun_potwierdzenie(nazwa), reply_markup=klawiatura)


async def obsluz_wzor_usun_potwierdz(callback: CallbackQuery, konf: Konfiguracja) -> None:
    wzor_id = callback.data.split(":", 1)[1]
    nazwa = magazyn.nazwa_wzoru(konf.katalog_danych / "wzory" / wzor_id)
    shutil.rmtree(konf.katalog_danych / "wzory" / wzor_id, ignore_errors=True)
    usun_pliki_zasobu(konf.katalog_danych, "nakladki", wzor_id)
    usun_pliki_zasobu(konf.katalog_danych, "plansze", wzor_id)
    if magazyn.wczytaj_ustawienia(konf.katalog_danych).get("aktywny_wzor") == wzor_id:
        magazyn.ustaw_aktywny_wzor(konf.katalog_danych, None)
    await callback.answer()
    await callback.message.edit_text(komunikaty.wzor_usuniety(nazwa))


async def bezpiecznie_wyslij(bot: Bot, chat_id: int, tekst: str) -> None:
    try:
        await bot.send_message(chat_id, tekst)
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
        dane.get("sekcje"),
    )


def zapisz_blad_wzoru(katalog_wzoru: Path, opis: str) -> None:
    (Path(katalog_wzoru) / "blad.txt").write_text(opis + "\n", encoding="utf-8")


async def analizuj_wzor_w_tle(
    bot: Bot, chat_id: int, zrodlo: Path, wzor_json: Path, konf: Konfiguracja, zapowiedz: asyncio.Event,
) -> None:
    await zapowiedz.wait()
    wynik = await kolejka_modul.uruchom(
        [sys.executable, str(SKRYPT_ANALIZY), str(zrodlo), str(wzor_json)],
        limit_s=LIMIT_ANALIZY_S,
    )
    if wynik.przekroczono_czas:
        zapisz_blad_wzoru(wzor_json.parent, "przekroczono limit czasu")
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.ANALIZA_PRZEKROCZONO_CZAS)
        return
    if wynik.kod != 0:
        opis = pierwsza_linia(wynik.stderr) or f"kod {wynik.kod}"
        zapisz_blad_wzoru(wzor_json.parent, opis)
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.blad_analizy(opis))
        return
    try:
        dane = json.loads(wzor_json.read_text(encoding="utf-8"))
        tekst = podsumuj_wzor(dane)
    except (OSError, ValueError, KeyError, ZeroDivisionError):
        log.exception("nie udalo sie odczytac wyniku analizy, wzor=%s", wzor_json)
        await bezpiecznie_wyslij(bot, chat_id, komunikaty.blad_analizy("nie udało się odczytać wyniku"))
        return
    magazyn.ustaw_aktywny_wzor(konf.katalog_danych, wzor_json.parent.name)
    await bezpiecznie_wyslij(bot, chat_id, tekst)


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
        shutil.rmtree(katalog_wzoru, ignore_errors=True)
        await message.answer(komunikaty.limit_rozmiaru(None, limit_mb))
        return
    except Exception:
        log.exception("pobieranie wzoru nie powiodlo sie, file_id=%s", file_id)
        shutil.rmtree(katalog_wzoru, ignore_errors=True)
        await message.answer(komunikaty.BLAD_POBIERANIA)
        return

    magazyn.zapisz_nazwe_wzoru(katalog_wzoru, message.caption)
    await wroc_po_zapisie(state)
    zapowiedz = asyncio.Event()

    async def zadanie() -> None:
        await analizuj_wzor_w_tle(message.bot, message.chat.id, cel, katalog_wzoru / "wzor.json", konf, zapowiedz)

    pozycja = await kolejka_obiekt.dodaj(zadanie)
    try:
        await message.answer(komunikaty.analizuje_wzor(pozycja))
    finally:
        zapowiedz.set()


async def obsluz_wzor_niepoprawny(message: Message) -> None:
    await message.answer(komunikaty.WZOR_NIEPOPRAWNY_TYP)


def usun_pliki_zasobu(katalog_danych: Path, rodzaj: str, wzor_id: str, pomin: Path | None = None) -> None:
    katalog = Path(katalog_danych) / rodzaj
    if not katalog.is_dir():
        return
    for plik in katalog.glob(f"{wzor_id}.*"):
        if plik.is_file() and plik != pomin:
            plik.unlink()


async def wroc_po_zapisie(state: FSMContext) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if projekt_id:
        await state.set_state(Stany.zbieram)
        await state.update_data(projekt_id=projekt_id)
    else:
        await state.clear()


async def obsluz_cmd_nakladka(message: Message, state: FSMContext, konf: Konfiguracja, command: CommandObject) -> None:
    wzor_json = magazyn.aktywny_wzor(konf.katalog_danych)
    if wzor_json is None:
        await message.answer(komunikaty.BRAK_WZORU)
        return
    wzor_id = wzor_json.parent.name
    if (command.args or "").strip() == "usun":
        usun_pliki_zasobu(konf.katalog_danych, "nakladki", wzor_id)
        await message.answer(komunikaty.NAKLADKA_USUNIETA)
        return
    await state.set_state(Stany.czekam_na_nakladke)
    await state.update_data(wzor_id=wzor_id)
    await message.answer(komunikaty.nakladka_prosba(wzor_id))


async def obsluz_nakladka_niepoprawny_zalacznik(message: Message) -> None:
    await message.answer(komunikaty.NAKLADKA_WYSLIJ_JAKO_PLIK)


async def obsluz_nakladka_dokument(message: Message, state: FSMContext, konf: Konfiguracja) -> None:
    dane_stanu = await state.get_data()
    wzor_id = dane_stanu.get("wzor_id")
    dokument = message.document
    rozszerzenie = Path(dokument.file_name or "").suffix.lstrip(".").lower()
    if rozszerzenie not in magazyn.ROZSZERZENIA_NAKLADEK:
        await message.answer(komunikaty.NAKLADKA_NIEPOPRAWNY_TYP)
        return

    cel = konf.katalog_danych / "nakladki" / f"{wzor_id}.{rozszerzenie}"
    try:
        await pobierz_plik(message.bot, dokument.file_id, cel)
    except TelegramEntityTooLarge:
        await message.answer(komunikaty.limit_rozmiaru(None, efektywny_limit_mb(konf)))
        return
    except Exception:
        log.exception("pobieranie nakladki nie powiodlo sie, file_id=%s", dokument.file_id)
        await message.answer(komunikaty.BLAD_POBIERANIA)
        return

    usun_pliki_zasobu(konf.katalog_danych, "nakladki", wzor_id, pomin=cel)
    await wroc_po_zapisie(state)
    tryb = render.tryb_nakladki(cel)
    await message.answer(komunikaty.nakladka_zapisana(tryb))


async def obsluz_cmd_plansza(message: Message, state: FSMContext, konf: Konfiguracja, command: CommandObject) -> None:
    wzor_json = magazyn.aktywny_wzor(konf.katalog_danych)
    if wzor_json is None:
        await message.answer(komunikaty.BRAK_WZORU)
        return
    wzor_id = wzor_json.parent.name
    if (command.args or "").strip() == "usun":
        usun_pliki_zasobu(konf.katalog_danych, "plansze", wzor_id)
        await message.answer(komunikaty.PLANSZA_USUNIETA)
        return
    await state.set_state(Stany.czekam_na_plansze)
    await state.update_data(wzor_id=wzor_id)
    await message.answer(komunikaty.plansza_prosba(wzor_id))


async def obsluz_plansza_niepoprawny_zalacznik(message: Message) -> None:
    await message.answer(komunikaty.PLANSZA_NIEPOPRAWNY_TYP)


async def obsluz_plansza_zalacznik(message: Message, state: FSMContext, konf: Konfiguracja) -> None:
    dane_stanu = await state.get_data()
    wzor_id = dane_stanu.get("wzor_id")
    zalacznik = rozpoznaj_zalacznik(message)
    if zalacznik is None:
        await message.answer(komunikaty.PLANSZA_NIEPOPRAWNY_TYP)
        return
    _, rozszerzenie, file_id, _, _ = zalacznik

    cel = konf.katalog_danych / "plansze" / f"{wzor_id}.{rozszerzenie}"
    try:
        await pobierz_plik(message.bot, file_id, cel)
    except TelegramEntityTooLarge:
        await message.answer(komunikaty.limit_rozmiaru(None, efektywny_limit_mb(konf)))
        return
    except Exception:
        log.exception("pobieranie planszy nie powiodlo sie, file_id=%s", file_id)
        await message.answer(komunikaty.BLAD_POBIERANIA)
        return

    usun_pliki_zasobu(konf.katalog_danych, "plansze", wzor_id, pomin=cel)
    await wroc_po_zapisie(state)
    await message.answer(komunikaty.PLANSZA_ZAPISANA)


async def obsluz_cmd_znak(message: Message, state: FSMContext, konf: Konfiguracja, command: CommandObject) -> None:
    if (command.args or "").strip() == "usun":
        (konf.katalog_danych / "znak_wodny.png").unlink(missing_ok=True)
        await message.answer(komunikaty.ZNAK_USUNIETY)
        return
    await state.set_state(Stany.czekam_na_znak)
    await message.answer(komunikaty.ZNAK_PROSBA)


async def obsluz_znak_niepoprawny_zalacznik(message: Message) -> None:
    await message.answer(komunikaty.ZNAK_NIEPOPRAWNY_TYP)


async def obsluz_znak_dokument(message: Message, state: FSMContext, konf: Konfiguracja) -> None:
    dokument = message.document
    rozszerzenie = Path(dokument.file_name or "").suffix.lstrip(".").lower()
    if rozszerzenie != "png":
        await message.answer(komunikaty.ZNAK_NIEPOPRAWNY_TYP)
        return

    cel = konf.katalog_danych / "znak_wodny.png"
    try:
        await pobierz_plik(message.bot, dokument.file_id, cel)
    except TelegramEntityTooLarge:
        await message.answer(komunikaty.limit_rozmiaru(None, efektywny_limit_mb(konf)))
        return
    except Exception:
        log.exception("pobieranie znaku wodnego nie powiodlo sie, file_id=%s", dokument.file_id)
        await message.answer(komunikaty.BLAD_POBIERANIA)
        return

    await wroc_po_zapisie(state)
    await message.answer(komunikaty.ZNAK_ZAPISANY)


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
            await message.answer(komunikaty.MATERIAL_NIEPOPRAWNY_TYP)
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


async def obsluz_cmd_slowa(
    message: Message, state: FSMContext, konf: Konfiguracja, command: CommandObject, blokada_projektu: asyncio.Lock,
) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if not projekt_id:
        await message.answer(komunikaty.BRAK_STANU)
        return

    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    surowy_tekst = (command.args or "").strip()

    async with blokada_projektu:
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        if not surowy_tekst:
            dane_projektu["slowa"] = None
            magazyn.zapisz_projekt(katalog_projektu, dane_projektu)
            await message.answer(komunikaty.SLOWA_WYCZYSZCZONE)
            return

        sciezka_czcionki, _ = tekst.wybierz_czcionke(tekst.PRESETY["rytm"])
        znaki = tekst.znaki_czcionki(sciezka_czcionki)
        oczyszczony, _ = tekst.oczysc(surowy_tekst, znaki)
        slowa = oczyszczony.split(" ") if oczyszczony else []

        if len(slowa) > LIMIT_SLOW_RYTM:
            await message.answer(komunikaty.slowa_za_duzo(len(slowa), LIMIT_SLOW_RYTM))
            return

        dane_projektu["slowa"] = " ".join(slowa) if slowa else None
        magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    if slowa:
        await message.answer(komunikaty.slowa_zapisane(len(slowa)))
    else:
        await message.answer(komunikaty.SLOWA_WYCZYSZCZONE)


async def obsluz_cmd_pionowo(
    message: Message, state: FSMContext, konf: Konfiguracja, command: CommandObject, blokada_projektu: asyncio.Lock,
) -> None:
    dane_stanu = await state.get_data()
    projekt_id = dane_stanu.get("projekt_id")
    if not projekt_id:
        await message.answer(komunikaty.BRAK_STANU)
        return

    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    surowy_tekst = (command.args or "").strip()

    async with blokada_projektu:
        dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
        if not surowy_tekst:
            dane_projektu["pionowo"] = None
            magazyn.zapisz_projekt(katalog_projektu, dane_projektu)
            await message.answer(komunikaty.PIONOWO_WYCZYSZCZONY)
            return

        sciezka_czcionki, _ = tekst.wybierz_czcionke(tekst.PRESETY["szeryf"])
        znaki = tekst.znaki_czcionki(sciezka_czcionki)
        oczyszczony, _ = tekst.oczysc(surowy_tekst, znaki)

        if len(oczyszczony) > LIMIT_ZNAKOW_PIONOWO:
            await message.answer(komunikaty.pionowo_za_dlugi(len(oczyszczony), LIMIT_ZNAKOW_PIONOWO))
            return

        dane_projektu["pionowo"] = oczyszczony or None
        magazyn.zapisz_projekt(katalog_projektu, dane_projektu)

    if oczyszczony:
        await message.answer(komunikaty.pionowo_zapisany(oczyszczony))
    else:
        await message.answer(komunikaty.PIONOWO_WYCZYSZCZONY)


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
    router.message.register(obsluz_cmd_nakladka, Command("nakladka"))
    router.message.register(obsluz_cmd_plansza, Command("plansza"))
    router.message.register(obsluz_cmd_znak, Command("znak"))
    router.message.register(obsluz_cmd_nowy, Command("nowy"))
    router.message.register(obsluz_cmd_gotowe, Command("gotowe"))
    router.message.register(obsluz_cmd_ponow, Command("ponow"))
    router.message.register(obsluz_cmd_anuluj, Command("anuluj"))
    router.message.register(obsluz_cmd_status, Command("status"))
    router.message.register(obsluz_cmd_slowa, Command("slowa"))
    router.message.register(obsluz_cmd_pionowo, Command("pionowo"))
    router.message.register(obsluz_cmd_wzory, Command("wzory"))
    router.callback_query.register(obsluz_wzor_wybierz, F.data.startswith("wzor_wybierz:"))
    router.callback_query.register(obsluz_wzor_usun_potwierdz, F.data.startswith("wzor_usun_potwierdz:"))
    router.callback_query.register(obsluz_wzor_usun_pytanie, F.data.startswith("wzor_usun:"))
    router.message.register(obsluz_wzor_plik, StateFilter(Stany.czekam_na_wzor), to_wideo)
    router.message.register(obsluz_wzor_niepoprawny, StateFilter(Stany.czekam_na_wzor))
    router.message.register(obsluz_nakladka_dokument, StateFilter(Stany.czekam_na_nakladke), F.document)
    router.message.register(obsluz_nakladka_niepoprawny_zalacznik, StateFilter(Stany.czekam_na_nakladke))
    router.message.register(obsluz_plansza_zalacznik, StateFilter(Stany.czekam_na_plansze), to_material)
    router.message.register(obsluz_plansza_niepoprawny_zalacznik, StateFilter(Stany.czekam_na_plansze))
    router.message.register(obsluz_znak_dokument, StateFilter(Stany.czekam_na_znak), F.document)
    router.message.register(obsluz_znak_niepoprawny_zalacznik, StateFilter(Stany.czekam_na_znak))
    router.message.register(obsluz_material, StateFilter(Stany.zbieram), to_material)
    router.message.register(obsluz_tekst, StateFilter(Stany.zbieram), F.text)
    router.message.register(obsluz_plik_bez_stanu, to_material)
    return router


def utworz_dispatcher(konf: Konfiguracja, kolejka_obiekt: kolejka_modul.Kolejka) -> Dispatcher:
    dyspozytor = Dispatcher(storage=MemoryStorage())
    dyspozytor.message.filter(wlasciciel(konf.wlasciciel_id))
    dyspozytor.edited_message.filter(wlasciciel(konf.wlasciciel_id))
    dyspozytor.callback_query.filter(wlasciciel(konf.wlasciciel_id))
    dyspozytor.include_router(zbuduj_router())
    dyspozytor["konf"] = konf
    dyspozytor["kolejka_obiekt"] = kolejka_obiekt
    dyspozytor["projekt_aktywny"] = {"id": None}
    dyspozytor["pobrania_w_toku"] = {}
    dyspozytor["reagowane_albumy"] = set()
    dyspozytor["blokada_projektu"] = asyncio.Lock()
    return dyspozytor


async def wznow_po_starcie(bot: Bot, konf: Konfiguracja, kolejka_obiekt: kolejka_modul.Kolejka) -> None:
    katalog_projektow = konf.katalog_danych / "projekty"
    if katalog_projektow.is_dir():
        for katalog_projektu in sorted(katalog for katalog in katalog_projektow.iterdir() if katalog.is_dir()):
            try:
                dane_projektu = magazyn.wczytaj_projekt(katalog_projektu)
            except (OSError, ValueError):
                continue
            zadania = dane_projektu.get("zadania") or []
            niedokonczone = [
                indeks for indeks, zadanie in enumerate(zadania) if zadanie["stan"] in ("w_kolejce", "renderowanie")
            ]
            if not niedokonczone:
                continue

            katalog_muzyki = konf.katalog_danych / "muzyka"
            zapowiedz = asyncio.Event()
            wznowione = False
            for indeks in niedokonczone:
                zadanie_dane = zadania[indeks]
                wzor_id = zadanie_dane["wzor_id"]
                wzor_json = konf.katalog_danych / "wzory" / wzor_id / "wzor.json"
                if not wzor_json.is_file():
                    continue
                zadanie_dane["stan"] = "w_kolejce"
                wznowione = True
                nakladka = magazyn.plik_zasobu(konf.katalog_danych, "nakladki", wzor_id)
                plansza = magazyn.plik_zasobu(konf.katalog_danych, "plansze", wzor_id)
                znak = konf.katalog_danych / "znak_wodny.png"
                znak = znak if znak.is_file() else None

                async def zadanie(
                    indeks=indeks, wzor_json=wzor_json, nakladka=nakladka, plansza=plansza, znak=znak,
                ) -> None:
                    await renderuj_zadanie_w_tle(
                        bot, konf.wlasciciel_id, katalog_projektu, indeks, wzor_json, katalog_muzyki, konf,
                        zapowiedz, nakladka, plansza, znak,
                    )

                await kolejka_obiekt.dodaj(zadanie)

            if not wznowione:
                continue
            dane_projektu["stan"] = magazyn.stan_z_zadan(zadania)
            magazyn.zapisz_projekt(katalog_projektu, dane_projektu)
            try:
                await bezpiecznie_wyslij(
                    bot, konf.wlasciciel_id, f"Wznawiam montaż projektu {katalog_projektu.name} po restarcie.",
                )
            finally:
                zapowiedz.set()

    katalog_wzorow = konf.katalog_danych / "wzory"
    if katalog_wzorow.is_dir():
        for katalog_wzoru in sorted(katalog for katalog in katalog_wzorow.iterdir() if katalog.is_dir()):
            if (katalog_wzoru / "wzor.json").is_file() or (katalog_wzoru / "blad.txt").is_file():
                continue
            zrodla = sorted(katalog_wzoru.glob("zrodlo.*"))
            if not zrodla:
                continue
            zrodlo = zrodla[0]
            wzor_json = katalog_wzoru / "wzor.json"
            zapowiedz = asyncio.Event()

            async def zadanie(zrodlo=zrodlo, wzor_json=wzor_json, zapowiedz=zapowiedz) -> None:
                await analizuj_wzor_w_tle(bot, konf.wlasciciel_id, zrodlo, wzor_json, konf, zapowiedz)

            await kolejka_obiekt.dodaj(zadanie)
            try:
                await bezpiecznie_wyslij(
                    bot, konf.wlasciciel_id, f"Wznawiam analizę wzoru {katalog_wzoru.name} po restarcie.",
                )
            finally:
                zapowiedz.set()


def zbuduj_sesje(konf: Konfiguracja) -> AiohttpSession | None:
    if not konf.telegram_api_url:
        return None
    return AiohttpSession(api=TelegramAPIServer.from_base(konf.telegram_api_url, is_local=True))


async def uruchom_bota(konf: Konfiguracja) -> None:
    bot = Bot(token=konf.token, session=zbuduj_sesje(konf), default=DefaultBotProperties(parse_mode=None))
    kolejka_obiekt = kolejka_modul.Kolejka()
    kolejka_obiekt.start()
    dyspozytor = utworz_dispatcher(konf, kolejka_obiekt)
    await bot.set_my_commands([BotCommand(command=nazwa, description=opis) for nazwa, opis in komunikaty.KOMENDY])
    await wznow_po_starcie(bot, konf, kolejka_obiekt)
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
