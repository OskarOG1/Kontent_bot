import asyncio
import json
import sys
from pathlib import Path

import pytest
from aiogram.fsm.storage.base import StorageKey

import bot
import kolejka
import magazyn
from konfiguracja import Konfiguracja
from pomocnicze import (
    CZAT_ID,
    OBCY_ID,
    WLASCICIEL_ID,
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
