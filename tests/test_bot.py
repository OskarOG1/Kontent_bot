import asyncio
import json
import sys
from pathlib import Path

import pytest
from aiogram import Bot
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import File

import bot
import generuj
import kolejka
import magazyn
from konfiguracja import Konfiguracja
from pomocnicze import (
    CZAT_ID,
    OBCY_ID,
    TOKEN_TESTOWY,
    WLASCICIEL_ID,
    SesjaTestowa,
    dokument,
    klip,
    nazwy_wywolan,
    zbuduj_bota,
    zbuduj_update,
    zbuduj_wiadomosc,
    zdjecie,
)


@pytest.fixture
def konf(tmp_path) -> Konfiguracja:
    return Konfiguracja(
        token="123456:TEST",
        wlasciciel_id=WLASCICIEL_ID,
        katalog_danych=tmp_path / "dane",
        limit_pobierania_mb=20,
        limit_wysylki_mb=50,
    )


@pytest.fixture
def srodowisko(konf):
    kolejka_obiekt = kolejka.Kolejka()
    dyspozytor = bot.utworz_dispatcher(konf, kolejka_obiekt)
    bot_obiekt = zbuduj_bota()
    return dyspozytor, bot_obiekt, bot_obiekt.session, konf


async def test_obcy_start_zero_wywolan(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    wiadomosc = zbuduj_wiadomosc(od_id=OBCY_ID, text="/start")
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert sesja.wywolania == []
    assert not konf.katalog_danych.exists()


async def test_wlasciciel_start_jedno_sendmessage(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    wiadomosc = zbuduj_wiadomosc(text="/start")
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert nazwy_wywolan(sesja) == ["SendMessage"]


async def test_pomoc_wspomina_o_napisach(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    wiadomosc = zbuduj_wiadomosc(text="/start")
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert "napis" in teksty_odpowiedzi(sesja)[-1]


async def test_zdjecie_bez_nowy_komunikat_bez_plikow(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f1", "u1", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert nazwy_wywolan(sesja) == ["SendMessage"]
    assert not (konf.katalog_danych / "projekty").exists()


async def test_nowy_potem_trzy_materialy_rozne_rozszerzenia(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    m_zdjecie = zbuduj_wiadomosc(photo=zdjecie("f_photo", "u_photo", file_size=1000))
    m_dokument = zbuduj_wiadomosc(document=dokument("f_doc", "u_doc", nazwa="IMG_1.HEIC", mime="image/jpeg", file_size=1000))
    m_wideo = zbuduj_wiadomosc(video=klip("f_video", "u_video", file_size=1000))

    for wiadomosc in (m_zdjecie, m_dokument, m_wideo):
        await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    projekt_id = dane_stanu["projekt_id"]
    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    materialy = magazyn.lista_materialow(katalog_projektu)

    assert [wpis["message_id"] for wpis in materialy] == sorted(wpis["message_id"] for wpis in materialy)
    rozszerzenia = sorted(wpis["plik"].suffix.lstrip(".") for wpis in materialy)
    assert rozszerzenia == ["heic", "jpg", "mp4"]


async def test_album_trzech_zdjec_jedna_reakcja(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    grupa = "album_1"
    for numer in range(3):
        wiadomosc = zbuduj_wiadomosc(
            photo=zdjecie(f"f_{numer}", f"u_{numer}", file_size=1000),
            media_group_id=grupa,
        )
        await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    projekt_id = dane_stanu["projekt_id"]
    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    materialy = magazyn.lista_materialow(katalog_projektu)

    assert len(materialy) == 3
    assert nazwy_wywolan(sesja).count("SetMessageReaction") == 1


async def test_document_25mb_komunikat_bez_pobrania(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    rozmiar_25mb = 25 * 1024 * 1024
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_big", "u_big", nazwa="klip.mp4", file_size=rozmiar_25mb))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    assert "GetFile" not in nazwy_wywolan(sesja)
    assert nazwy_wywolan(sesja) == ["SendMessage", "SendMessage"]


async def test_limit_telegrama_dziala_mimo_wyzszego_limitu_w_konfiguracji(konf):
    konf.limit_pobierania_mb = 200
    dyspozytor = bot.utworz_dispatcher(konf, kolejka.Kolejka())
    bot_obiekt = zbuduj_bota()
    sesja = bot_obiekt.session
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    wiadomosc = zbuduj_wiadomosc(document=dokument("f_big", "u_big", nazwa="klip.mp4", file_size=25 * 1024 * 1024))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    assert "GetFile" not in nazwy_wywolan(sesja)
    ostatnia = [m for m in sesja.wywolania if type(m).__name__ == "SendMessage"][-1]
    assert "20 MB" in ostatnia.text


def test_efektywny_limit_mb_bez_adresu_lokalnego(konf):
    konf.limit_pobierania_mb = 2500
    assert bot.efektywny_limit_mb(konf) == 20


def test_efektywny_limit_mb_z_adresem_lokalnym(konf):
    konf.telegram_api_url = "http://bot-api:8081"
    konf.limit_pobierania_mb = 2500
    assert bot.efektywny_limit_mb(konf) == 2500


def test_efektywny_limit_wysylki_mb_bez_adresu_lokalnego(konf):
    konf.limit_wysylki_mb = 2000
    assert bot.efektywny_limit_wysylki_mb(konf) == 50


def test_efektywny_limit_wysylki_mb_z_adresem_lokalnym(konf):
    konf.telegram_api_url = "http://bot-api:8081"
    konf.limit_wysylki_mb = 2000
    assert bot.efektywny_limit_wysylki_mb(konf) == 2000


def test_zbuduj_sesje_bez_adresu_lokalnego_brak_sesji(konf):
    assert bot.zbuduj_sesje(konf) is None


def test_zbuduj_sesje_z_adresem_lokalnym(konf):
    konf.telegram_api_url = "http://bot-api:8081"
    sesja = bot.zbuduj_sesje(konf)
    assert sesja.api.is_local is True
    assert sesja.api.base == "http://bot-api:8081/bot{token}/{method}"


async def test_pobierz_plik_w_trybie_lokalnym_kopiuje_sciezke_z_getfile(tmp_path, monkeypatch):
    zrodlo = tmp_path / "zrodlowy.mp4"
    zrodlo.write_bytes(b"zawartosc-lokalna")
    sesja = SesjaTestowa(api=TelegramAPIServer.from_base("http://bot-api:8081", is_local=True))
    bot_obiekt = Bot(token=TOKEN_TESTOWY, session=sesja)

    async def get_file_podmieniony(file_id, request_timeout=None):
        return File(file_id=file_id, file_unique_id="u_lokalny", file_path=str(zrodlo))

    monkeypatch.setattr(bot_obiekt, "get_file", get_file_podmieniony)

    cel = tmp_path / "cel.mp4"
    await bot.pobierz_plik(bot_obiekt, "f_lokalny", cel)

    assert cel.read_bytes() == b"zawartosc-lokalna"
    assert "GetFile" not in nazwy_wywolan(sesja)
    assert not zrodlo.exists()


async def test_get_file_lokalny_dostaje_dlugi_limit_czasu(tmp_path, monkeypatch):
    zrodlo = tmp_path / "zrodlowy.mp4"
    zrodlo.write_bytes(b"zawartosc")
    sesja = SesjaTestowa(api=TelegramAPIServer.from_base("http://bot-api:8081", is_local=True))
    bot_obiekt = Bot(token=TOKEN_TESTOWY, session=sesja)
    limity_czasu = []

    async def get_file_podmieniony(file_id, request_timeout=None):
        limity_czasu.append(request_timeout)
        return File(file_id=file_id, file_unique_id="u_lokalny", file_path=str(zrodlo))

    monkeypatch.setattr(bot_obiekt, "get_file", get_file_podmieniony)

    await bot.pobierz_plik(bot_obiekt, "f_lokalny", tmp_path / "cel.mp4")

    assert limity_czasu == [bot.LIMIT_GETFILE_LOKALNY_S]


async def test_pobierz_plik_zwykle_api_nic_nie_usuwa(tmp_path, monkeypatch):
    bot_obiekt = zbuduj_bota()
    oryginalny_unlink = Path.unlink
    usuniecia = []

    def unlink_liczony(self, missing_ok=False):
        usuniecia.append(self)
        return oryginalny_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink_liczony)

    cel = tmp_path / "cel.mp4"
    await bot.pobierz_plik(bot_obiekt, "f_zdalny", cel)

    assert cel.read_bytes() == b"zawartosc-testowa"
    assert usuniecia == []


async def test_blad_usuwania_zrodla_nie_przerywa_pobrania(tmp_path, monkeypatch, caplog):
    zrodlo = tmp_path / "zrodlowy.mp4"
    zrodlo.write_bytes(b"zawartosc-lokalna")
    sesja = SesjaTestowa(api=TelegramAPIServer.from_base("http://bot-api:8081", is_local=True))
    bot_obiekt = Bot(token=TOKEN_TESTOWY, session=sesja)

    async def get_file_podmieniony(file_id, request_timeout=None):
        return File(file_id=file_id, file_unique_id="u_lokalny", file_path=str(zrodlo))

    monkeypatch.setattr(bot_obiekt, "get_file", get_file_podmieniony)

    def unlink_z_bledem(self, missing_ok=False):
        raise PermissionError("brak uprawnien")

    monkeypatch.setattr(Path, "unlink", unlink_z_bledem)

    cel = tmp_path / "cel.mp4"
    with caplog.at_level("WARNING", logger="bot"):
        await bot.pobierz_plik(bot_obiekt, "f_lokalny", cel)

    assert cel.read_bytes() == b"zawartosc-lokalna"
    assert any("usun" in rekord.message for rekord in caplog.records)


async def test_blad_kopiowania_zostawia_zrodlo(tmp_path, monkeypatch):
    zrodlo = tmp_path / "zrodlowy.mp4"
    zrodlo.write_bytes(b"zawartosc-lokalna")
    sesja = SesjaTestowa(api=TelegramAPIServer.from_base("http://bot-api:8081", is_local=True))
    bot_obiekt = Bot(token=TOKEN_TESTOWY, session=sesja)

    async def get_file_podmieniony(file_id, request_timeout=None):
        return File(file_id=file_id, file_unique_id="u_lokalny", file_path=str(zrodlo))

    monkeypatch.setattr(bot_obiekt, "get_file", get_file_podmieniony)

    def kopiuj_z_bledem(zrodlo_sciezka, cel_sciezka, rozmiar_kawalka):
        raise OSError("dysk pelny")

    monkeypatch.setattr(bot, "kopiuj_plik", kopiuj_z_bledem)

    cel = tmp_path / "cel.mp4"
    with pytest.raises(OSError):
        await bot.pobierz_plik(bot_obiekt, "f_lokalny", cel)

    assert zrodlo.exists()
    assert not cel.exists()
    assert not cel.with_name(cel.name + ".part").exists()


async def test_zbyt_duzy_plik_zgloszony_przez_telegram_daje_komunikat_o_limicie(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    sesja.plik_za_duzy = True
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    wiadomosc = zbuduj_wiadomosc(video=klip("f_video", "u_video", file_size=None))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    ostatnia = [m for m in sesja.wywolania if type(m).__name__ == "SendMessage"][-1]
    assert "20 MB" in ostatnia.text
    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    katalog_projektu = konf.katalog_danych / "projekty" / dane_stanu["projekt_id"]
    assert magazyn.lista_materialow(katalog_projektu) == []


async def test_gotowe_czeka_na_trwajace_pobrania(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    sesja.opoznienie_pobierania_s = 0.5
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    zadania = []
    for numer in range(3):
        wiadomosc = zbuduj_wiadomosc(photo=zdjecie(f"f_{numer}", f"u_{numer}", file_size=1000))
        zadania.append(asyncio.create_task(dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))))

    await asyncio.sleep(0.05)
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))
    await asyncio.gather(*zadania)

    ostatnia = [m for m in sesja.wywolania if type(m).__name__ == "SendMessage"][-1]
    assert "3" in ostatnia.text


async def test_gotowe_bez_materialow_stan_trwa(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))

    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    assert dane_stanu.get("projekt_id") is not None

    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f_pozniej", "u_pozniej", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    projekt_id = dane_stanu["projekt_id"]
    materialy = magazyn.lista_materialow(konf.katalog_danych / "projekty" / projekt_id)
    assert len(materialy) == 1


async def test_dwadziescia_tekstow_naraz(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))

    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    projekt_id = dane_stanu["projekt_id"]

    zadania = []
    for numer in range(20):
        wiadomosc = zbuduj_wiadomosc(text=f"tekst {numer}")
        zadania.append(dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc)))
    await asyncio.gather(*zadania)

    dane_projektu = magazyn.wczytaj_projekt(konf.katalog_danych / "projekty" / projekt_id)
    assert len(dane_projektu["teksty"]) == 20
    identyfikatory = [wpis["message_id"] for wpis in dane_projektu["teksty"]]
    assert identyfikatory == sorted(identyfikatory)


async def test_edited_message_obcego_zero_wywolan(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    wiadomosc = zbuduj_wiadomosc(od_id=OBCY_ID, text="edycja")
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc, edytowana=True))
    assert sesja.wywolania == []


def klucz_stanu(bot_obiekt):
    return StorageKey(bot_id=bot_obiekt.id, chat_id=CZAT_ID, user_id=WLASCICIEL_ID)


def teksty_odpowiedzi(sesja) -> list[str]:
    return [metoda.text for metoda in sesja.wywolania if type(metoda).__name__ == "SendMessage"]


async def czekaj_na_kolejke(kolejka_obiekt, limit_s: float = 5.0) -> None:
    koniec = asyncio.get_running_loop().time() + limit_s
    while kolejka_obiekt.dlugosc() > 0:
        assert asyncio.get_running_loop().time() < koniec
        await asyncio.sleep(0.01)


async def wyslij_wzor(dyspozytor, bot_obiekt, nazwa: str = "wzor") -> None:
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/wzor")))
    wideo = zbuduj_wiadomosc(video=klip(f"f_{nazwa}", f"u_{nazwa}", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wideo))


def przygotuj_wzor_i_utwor(konf: Konfiguracja) -> Path:
    katalog_wzoru = konf.katalog_danych / "wzory" / "w1"
    katalog_wzoru.mkdir(parents=True)
    wzor_json = katalog_wzoru / "wzor.json"
    wzor_przygotowany(wzor_json)
    katalog_muzyki = konf.katalog_danych / "muzyka"
    katalog_muzyki.mkdir(parents=True, exist_ok=True)
    (katalog_muzyki / "staly.mp3").write_bytes(b"audio-testowe")
    return wzor_json


def wzor_przygotowany(sciezka: Path) -> None:
    dane = {
        "wersja": 1,
        "id": sciezka.parent.name,
        "zrodlo": {"czas_s": 15.03, "szerokosc": 1080, "wysokosc": 1920, "fps": 30.0, "ma_dzwiek": True},
        "ciecia_s": [0.0, 0.5, 1.0],
        "tempo_bpm": 120.2,
        "uderzenia_s": [0.1, 0.6],
        "ciecia_uderzenia": [-0.25, 0.75, 1.75],
        "koniec_uderzenia": 29.75,
        "kolorystyka": None,
        "tekst": None,
    }
    sciezka.write_text(json.dumps(dane), encoding="utf-8")


@pytest.fixture
async def z_praca_w_tle(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    kolejka_obiekt = dyspozytor["kolejka_obiekt"]
    kolejka_obiekt.start()
    yield dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt
    kolejka_obiekt._zadanie_pracownika.cancel()


async def test_wzor_dostaje_analize_i_podsumowanie(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append((argumenty, limit_s))
        wzor_przygotowany(Path(argumenty[3]))
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    teksty = teksty_odpowiedzi(sesja)
    assert len(teksty) == 3
    assert teksty[1] == "Analizuję wzór."
    assert "ujęć 3" in teksty[2]
    assert "15,0 s" in teksty[2]
    assert "średnia długość ujęcia 5,01 s" in teksty[2]
    assert "tempo 120,2 BPM" in teksty[2]
    argumenty, limit_s = wywolania[0]
    assert argumenty[0] == sys.executable
    assert Path(argumenty[1]).is_absolute() and Path(argumenty[1]).name == "analyze.py"
    assert Path(argumenty[1]).is_file()
    assert Path(argumenty[2]).name.startswith("zrodlo.") and Path(argumenty[2]).is_file()
    assert Path(argumenty[3]).name == "wzor.json"
    assert limit_s == 300


async def test_podsumowanie_wzoru_bez_dzwieku(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        sciezka = Path(argumenty[3])
        wzor_przygotowany(sciezka)
        dane = json.loads(sciezka.read_text(encoding="utf-8"))
        dane["zrodlo"]["ma_dzwiek"] = False
        dane["tempo_bpm"] = None
        sciezka.write_text(json.dumps(dane), encoding="utf-8")
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)
    assert "brak dźwięku" in teksty_odpowiedzi(sesja)[-1]


async def test_blad_analizy_daje_pierwsza_linie_stderr(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        return kolejka.Wynik(
            kod=1,
            stdout="",
            stderr="Plik nie ma strumienia wideo" + chr(10) + "druga linia" + chr(10),
            czas_s=0.1,
            przekroczono_czas=False,
        )

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert teksty_odpowiedzi(sesja)[-1] == "Analiza wzoru nie powiodła się: Plik nie ma strumienia wideo"
    zrodla = list((konf.katalog_danych / "wzory").glob("*/zrodlo.*"))
    assert len(zrodla) == 1


async def test_przekroczony_czas_analizy_ma_osobny_komunikat(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        return kolejka.Wynik(kod=None, stdout="", stderr="", czas_s=300.0, przekroczono_czas=True)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "zbyt długo" in teksty_odpowiedzi(sesja)[-1]
    assert len(list((konf.katalog_danych / "wzory").glob("*/zrodlo.*"))) == 1


async def test_status_odpowiada_gdy_analiza_trwa(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    zwolnij = asyncio.Event()

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        await zwolnij.wait()
        wzor_przygotowany(Path(argumenty[3]))
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await asyncio.sleep(0.05)
    assert kolejka_obiekt.dlugosc() == 1

    przed = len(teksty_odpowiedzi(sesja))
    await asyncio.wait_for(
        dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status"))), timeout=2
    )
    teksty = teksty_odpowiedzi(sesja)
    assert len(teksty) == przed + 1
    assert "Kolejka zadań: 1" in teksty[-1]

    zwolnij.set()
    await czekaj_na_kolejke(kolejka_obiekt)
    assert "ujęć 3" in teksty_odpowiedzi(sesja)[-1]


async def test_drugi_wzor_dostaje_pozycje_w_kolejce(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    zwolnij = asyncio.Event()

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        await zwolnij.wait()
        wzor_przygotowany(Path(argumenty[3]))
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt, "pierwszy")
    await wyslij_wzor(dyspozytor, bot_obiekt, "drugi")
    assert "Analizuję wzór." in teksty_odpowiedzi(sesja)
    assert "Analizuję wzór. Pozycja w kolejce: 2." in teksty_odpowiedzi(sesja)

    zwolnij.set()
    await czekaj_na_kolejke(kolejka_obiekt)
    assert sum(1 for t in teksty_odpowiedzi(sesja) if "ujęć 3" in t) == 2


def podsumowanie_renderu_testowe() -> dict:
    return {
        "czas_s": 12.3,
        "liczba_ujec": 20,
        "materialy_uzyte": 5,
        "materialy_pominiete": [],
        "rozmiar_mb": 8.1,
        "czas_renderu_s": 3.4,
        "utwor": {
            "plik": "Hot N Cold (Hardstyle).mp3", "tryb": "tempo", "zgodnosc": None,
            "start_s": 12.3, "tempo_bpm": 164.1, "mnoznik": 1.0,
        },
    }


async def wyslij_material_i_gotowe(dyspozytor, bot_obiekt) -> None:
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f_material", "u_material", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))


def jedyny_projekt_id(konf) -> str:
    projekty = list((konf.katalog_danych / "projekty").iterdir())
    assert len(projekty) == 1
    return projekty[0].name


def render_udany_podmieniony():
    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wyjscie = Path(argumenty[argumenty.index("--wyjscie") + 1])
        wyjscie.write_bytes(b"wideo-testowe")
        wyjscie.with_suffix(".json").write_text(json.dumps(podsumowanie_renderu_testowe()), encoding="utf-8")
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    return uruchom_podmienione


async def test_render_sukces_jedno_send_document(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    monkeypatch.setattr(kolejka, "uruchom", render_udany_podmieniony())
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    wywolania_wysylki = [m for m in sesja.wywolania if type(m).__name__ == "SendDocument"]
    assert len(wywolania_wysylki) == 1
    assert "ujęć 20" in wywolania_wysylki[0].caption
    assert "Muzyka: Hot N Cold (Hardstyle), dobór po tempie 164,1 BPM, od 12,3 s." in wywolania_wysylki[0].caption
    projekt_id = jedyny_projekt_id(konf)
    dane_projektu = magazyn.wczytaj_projekt(konf.katalog_danych / "projekty" / projekt_id)
    assert dane_projektu["stan"] == "gotowy"
    assert dane_projektu["wynik"] == "wynik.mp4"


async def test_render_sukces_podpis_z_linia_napisow(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wyjscie = Path(argumenty[argumenty.index("--wyjscie") + 1])
        wyjscie.write_bytes(b"wideo-testowe")
        podsumowanie = podsumowanie_renderu_testowe()
        podsumowanie["teksty"] = {"linie": 2, "usuniete_znaki": 1, "okna": [[0, 30], [30, 60]]}
        wyjscie.with_suffix(".json").write_text(json.dumps(podsumowanie), encoding="utf-8")
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    wywolania_wysylki = [m for m in sesja.wywolania if type(m).__name__ == "SendDocument"]
    assert "Napisy: 2." in wywolania_wysylki[0].caption
    assert "Usunięte znaki bez czcionki: 1 (np. emoji)." in wywolania_wysylki[0].caption


async def test_render_blad_daje_komunikat_i_stan_blad(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        return kolejka.Wynik(kod=1, stdout="", stderr="Brak dobrego materialu\ndruga linia\n", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    projekt_id = jedyny_projekt_id(konf)
    dane_projektu = magazyn.wczytaj_projekt(konf.katalog_danych / "projekty" / projekt_id)
    assert dane_projektu["stan"] == "blad"
    assert dane_projektu["blad"] == "Brak dobrego materialu"
    assert teksty_odpowiedzi(sesja)[-1] == "Montaż nie powiódł się: Brak dobrego materialu"
    assert "SendDocument" not in nazwy_wywolan(sesja)


async def test_brak_wzoru_nie_dodaje_zadania_do_kolejki(z_praca_w_tle):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)

    assert kolejka_obiekt.dlugosc() == 0
    assert teksty_odpowiedzi(sesja)[-1] == "Najpierw wyślij wzór przez /wzor."


async def test_brak_muzyki_nie_dodaje_zadania_do_kolejki(z_praca_w_tle):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    katalog_wzoru = konf.katalog_danych / "wzory" / "w1"
    katalog_wzoru.mkdir(parents=True)
    wzor_przygotowany(katalog_wzoru / "wzor.json")

    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)

    assert kolejka_obiekt.dlugosc() == 0
    assert teksty_odpowiedzi(sesja)[-1] == "Biblioteka muzyki jest pusta. Dodaj utwory do dane/muzyka."


async def test_render_dostaje_muzyke_a_nie_utwor(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert "--utwor" not in argumenty
    assert Path(argumenty[argumenty.index("--muzyka") + 1]) == konf.katalog_danych / "muzyka"


async def test_status_pokazuje_liczbe_utworow(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    assert "Muzyka: 1 utworów." in teksty_odpowiedzi(sesja)[-1]


async def test_status_przy_zbieraniu_pokazuje_liczbe_linii(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="Pierwsza linia")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="Druga linia")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    assert "linii tekstu 2" in teksty_odpowiedzi(sesja)[-1]


async def test_limit_mb_renderu_bez_lokalnego_serwera(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    konf.limit_wysylki_mb = 200
    przygotuj_wzor_i_utwor(konf)
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert argumenty[argumenty.index("--limit-mb") + 1] == "50"


async def test_limit_mb_renderu_z_lokalnym_serwerem(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    konf.limit_wysylki_mb = 200
    konf.telegram_api_url = "http://bot-api:8081"
    przygotuj_wzor_i_utwor(konf)
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert argumenty[argumenty.index("--limit-mb") + 1] == "200"


async def test_sila_koloru_renderu_z_konfiguracji(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    konf.sila_koloru = 0.25
    przygotuj_wzor_i_utwor(konf)
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert argumenty[argumenty.index("--sila-koloru") + 1] == "0.25"


async def test_styl_i_pozycja_tekstu_renderu_z_konfiguracji(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    konf.styl_tekstu = "blok"
    konf.pozycja_tekstu = "gora"
    przygotuj_wzor_i_utwor(konf)
    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert argumenty[argumenty.index("--styl-tekstu") + 1] == "blok"
    assert argumenty[argumenty.index("--pozycja-tekstu") + 1] == "gora"


async def test_dokument_za_duzy_przy_wysylce_daje_komunikat(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    sesja.dokument_za_duzy = True
    przygotuj_wzor_i_utwor(konf)

    monkeypatch.setattr(kolejka, "uruchom", render_udany_podmieniony())
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "MB" in teksty_odpowiedzi(sesja)[-1]


async def test_pdf_w_trakcie_zbierania_daje_komunikat_i_zero_plikow(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_pdf", "u_pdf", nazwa="dokument.pdf", mime="application/pdf", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    assert "GetFile" not in nazwy_wywolan(sesja)
    assert teksty_odpowiedzi(sesja)[-1] == "Nie rozpoznaję tego typu pliku. Wyślij zdjęcie albo klip."
    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    projekt_id = dane_stanu["projekt_id"]
    materialy = magazyn.lista_materialow(konf.katalog_danych / "projekty" / projekt_id)
    assert len(materialy) == 0


async def test_nieudane_pobranie_wzoru_nie_zostawia_katalogu(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    sesja.plik_za_duzy = True
    await wyslij_wzor(dyspozytor, bot_obiekt)

    katalog_wzorow = konf.katalog_danych / "wzory"
    assert list(katalog_wzorow.iterdir()) == []


async def test_status_nie_liczy_katalogu_bez_wzor_json(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    pusty = konf.katalog_danych / "wzory" / "pusty"
    pusty.mkdir(parents=True)
    przygotuj_wzor_i_utwor(konf)

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    assert "wzorów zapisanych: 1" in teksty_odpowiedzi(sesja)[-1]


async def test_nakladka_bez_wzoru_daje_brak_wzoru(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    assert teksty_odpowiedzi(sesja)[-1] == "Najpierw wyślij wzór przez /wzor."


async def test_plansza_bez_wzoru_daje_brak_wzoru(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/plansza")))
    assert teksty_odpowiedzi(sesja)[-1] == "Najpierw wyślij wzór przez /wzor."


async def test_nakladka_png_zapisuje_plik_i_podaje_tryb_drugi_zastepuje_pierwszy(srodowisko, tmp_path):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)

    prawdziwy_png = tmp_path / "n.png"
    generuj.nakladka_testowa(prawdziwy_png, 0.5, "png")
    sesja.tresc_pliku = prawdziwy_png.read_bytes()

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_nak", "u_nak", nazwa="n.png", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    zapisany = konf.katalog_danych / "nakladki" / "w1.png"
    assert zapisany.exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Nakładka zapisana: przezroczystość."

    inny_png = tmp_path / "n2.png"
    generuj.nakladka_testowa(inny_png, 0.5, "png")
    sesja.tresc_pliku = inny_png.read_bytes()
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc2 = zbuduj_wiadomosc(document=dokument("f_nak2", "u_nak2", nazwa="n2.png", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc2))

    pliki = list((konf.katalog_danych / "nakladki").glob("w1.*"))
    assert len(pliki) == 1


async def test_nakladka_krycie_zapisuje_plik_i_podaje_tryb(srodowisko, tmp_path):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)

    plik_krycie = tmp_path / "n.mp4"
    generuj.nakladka_testowa(plik_krycie, 0.5, "krycie")
    sesja.tresc_pliku = plik_krycie.read_bytes()

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_nak", "u_nak", nazwa="n.mp4", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    zapisany = konf.katalog_danych / "nakladki" / "w1.mp4"
    assert zapisany.exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Nakładka zapisana: krycie 50%."


async def test_nakladka_usun_usuwa_plik(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    katalog = konf.katalog_danych / "nakladki"
    katalog.mkdir(parents=True)
    (katalog / "w1.png").write_bytes(b"x")

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka usun")))

    assert not (katalog / "w1.png").exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Nakładka usunięta."


async def test_nakladka_zdjecie_daje_prosbe_o_plik(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f_p", "u_p", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert "jako plik" in teksty_odpowiedzi(sesja)[-1]
    assert not (konf.katalog_danych / "nakladki").exists()


async def test_plansza_przyjmuje_zdjecie(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/plansza")))
    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f_p", "u_p", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    zapisany = konf.katalog_danych / "plansze" / "w1.jpg"
    assert zapisany.exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Plansza zapisana."


async def test_render_dostaje_nakladke_i_plansze_gdy_sa_pliki(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)
    katalog_nakladek = konf.katalog_danych / "nakladki"
    katalog_nakladek.mkdir(parents=True)
    (katalog_nakladek / "w1.png").write_bytes(b"x")
    katalog_plansz = konf.katalog_danych / "plansze"
    katalog_plansz.mkdir(parents=True)
    (katalog_plansz / "w1.jpg").write_bytes(b"y")

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert Path(argumenty[argumenty.index("--nakladka") + 1]) == katalog_nakladek / "w1.png"
    assert Path(argumenty[argumenty.index("--plansza") + 1]) == katalog_plansz / "w1.jpg"


async def test_render_bez_plikow_bez_argumentow_nakladki_i_planszy(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    argumenty = wywolania[0]
    assert "--nakladka" not in argumenty
    assert "--plansza" not in argumenty


async def test_podsumowanie_wzoru_z_dropem_zawiera_drop_w(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        sciezka = Path(argumenty[3])
        wzor_przygotowany(sciezka)
        dane = json.loads(sciezka.read_text(encoding="utf-8"))
        dane["sekcje"] = {"drop_s": 7.3, "drop_ujecie": 9, "koniec_haka_uderzenia": 19.75}
        sciezka.write_text(json.dumps(dane), encoding="utf-8")
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "drop w 7,3 s (ujęcie 9)" in teksty_odpowiedzi(sesja)[-1]


async def test_podsumowanie_wzoru_bez_dropu(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wzor_przygotowany(Path(argumenty[3]))
        return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "bez dropu" in teksty_odpowiedzi(sesja)[-1]


async def test_status_pokazuje_nakladke_i_plansze(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    katalog_nakladek = konf.katalog_danych / "nakladki"
    katalog_nakladek.mkdir(parents=True)
    (katalog_nakladek / "w1.png").write_bytes(b"x")

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    ostatnia = teksty_odpowiedzi(sesja)[-1]
    assert "nakładka tak" in ostatnia
    assert "plansza nie" in ostatnia


async def test_nakladka_podczas_zbierania_zachowuje_projekt(z_praca_w_tle, monkeypatch, tmp_path):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(photo=zdjecie("f1", "u1", file_size=1000))))

    png = tmp_path / "n.png"
    generuj.nakladka_testowa(png, 0.5, "png")
    sesja.tresc_pliku = png.read_bytes()
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_nak", "u_nak", nazwa="n.png", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "--nakladka" in wywolania[0]
    projekt_id = jedyny_projekt_id(konf)
    materialy = magazyn.lista_materialow(konf.katalog_danych / "projekty" / projekt_id)
    assert len(materialy) == 1


async def test_plansza_podczas_zbierania_zachowuje_projekt(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(photo=zdjecie("f1", "u1", file_size=1000))))

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/plansza")))
    wiadomosc = zbuduj_wiadomosc(photo=zdjecie("f_p", "u_p", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "--plansza" in wywolania[0]
    projekt_id = jedyny_projekt_id(konf)
    materialy = magazyn.lista_materialow(konf.katalog_danych / "projekty" / projekt_id)
    assert len(materialy) == 1


async def test_wzor_podczas_zbierania_zachowuje_projekt(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        if str(bot.SKRYPT_ANALIZY) in argumenty:
            wzor_przygotowany(Path(argumenty[3]))
            return kolejka.Wynik(kod=0, stdout="", stderr="", czas_s=0.1, przekroczono_czas=False)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nowy")))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(photo=zdjecie("f1", "u1", file_size=1000))))

    await wyslij_wzor(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    assert dane_stanu.get("projekt_id") is not None

    katalog_muzyki = konf.katalog_danych / "muzyka"
    katalog_muzyki.mkdir(parents=True, exist_ok=True)
    (katalog_muzyki / "staly.mp3").write_bytes(b"audio-testowe")

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/gotowe")))
    await czekaj_na_kolejke(kolejka_obiekt)

    assert teksty_odpowiedzi(sesja)[-1] != "Najpierw użyj /nowy albo /wzor."
    projekt_id = jedyny_projekt_id(konf)
    materialy = magazyn.lista_materialow(konf.katalog_danych / "projekty" / projekt_id)
    assert len(materialy) == 1


async def test_nakladka_pobieranie_z_bledem_zostawia_stary_plik(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    przygotuj_wzor_i_utwor(konf)
    katalog = konf.katalog_danych / "nakladki"
    katalog.mkdir(parents=True)
    (katalog / "w1.png").write_bytes(b"stara-nakladka")

    sesja.plik_za_duzy = True
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/nakladka")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_nak", "u_nak", nazwa="n.png", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    assert (katalog / "w1.png").read_bytes() == b"stara-nakladka"


async def test_znak_png_zapisuje_plik_i_render_dostaje_argument(z_praca_w_tle, monkeypatch, tmp_path):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    znak_png = tmp_path / "z.png"
    generuj.nakladka_testowa(znak_png, 0.5, "png")
    sesja.tresc_pliku = znak_png.read_bytes()

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/znak")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_znak", "u_znak", nazwa="z.png", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))

    zapisany = konf.katalog_danych / "znak_wodny.png"
    assert zapisany.exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Znak wodny zapisany."

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert Path(wywolania[0][wywolania[0].index("--znak") + 1]) == zapisany


async def test_znak_niepoprawny_typ_daje_prosbe(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/znak")))
    wiadomosc = zbuduj_wiadomosc(document=dokument("f_z", "u_z", nazwa="z.jpg", file_size=1000))
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(wiadomosc))
    assert teksty_odpowiedzi(sesja)[-1] == "To nie jest PNG. Wyślij znak wodny jako plik PNG."
    assert not (konf.katalog_danych / "znak_wodny.png").exists()


async def test_znak_usun_usuwa_plik(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    katalog = konf.katalog_danych
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "znak_wodny.png").write_bytes(b"x")

    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/znak usun")))

    assert not (katalog / "znak_wodny.png").exists()
    assert teksty_odpowiedzi(sesja)[-1] == "Znak wodny usunięty."


async def test_render_bez_znaku_bez_argumentu(z_praca_w_tle, monkeypatch):
    dyspozytor, bot_obiekt, sesja, konf, kolejka_obiekt = z_praca_w_tle
    przygotuj_wzor_i_utwor(konf)

    wywolania = []

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        wywolania.append(argumenty)
        return await render_udany_podmieniony()(argumenty, limit_s, katalog)

    monkeypatch.setattr(kolejka, "uruchom", uruchom_podmienione)
    await wyslij_material_i_gotowe(dyspozytor, bot_obiekt)
    await czekaj_na_kolejke(kolejka_obiekt)

    assert "--znak" not in wywolania[0]


async def test_status_pokazuje_znak_wodny(srodowisko):
    dyspozytor, bot_obiekt, sesja, konf = srodowisko
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    assert "Znak wodny: nie" in teksty_odpowiedzi(sesja)[-1]

    katalog = konf.katalog_danych
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "znak_wodny.png").write_bytes(b"x")
    await dyspozytor.feed_update(bot_obiekt, zbuduj_update(zbuduj_wiadomosc(text="/status")))
    assert "Znak wodny: tak" in teksty_odpowiedzi(sesja)[-1]
