import asyncio
import json

import pytest

import bot
import generuj
import kolejka
import magazyn
import render
from konfiguracja import Konfiguracja
from pomocnicze import CZAT_ID, WLASCICIEL_ID, zbuduj_bota


@pytest.fixture
def konf(tmp_path) -> Konfiguracja:
    return Konfiguracja(
        token="123456:TEST",
        wlasciciel_id=WLASCICIEL_ID,
        katalog_danych=tmp_path / "dane",
        limit_pobierania_mb=20,
        limit_wysylki_mb=50,
    )


def teksty_wyslane(sesja) -> list[str]:
    return [metoda.text for metoda in sesja.wywolania if type(metoda).__name__ == "SendMessage"]


def zapisz_wzor(konf, wzor_id: str) -> None:
    katalog_wzoru = konf.katalog_danych / "wzory" / wzor_id
    katalog_wzoru.mkdir(parents=True)
    (katalog_wzoru / "wzor.json").write_text("{}", encoding="utf-8")


def zapisz_projekt(konf, projekt_id: str, stan: str, wzor_id: str | None = None) -> None:
    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    magazyn.zapisz_projekt(
        katalog_projektu,
        {"id": projekt_id, "stan": stan, "teksty": [], "wzor_id": wzor_id, "wynik": None, "blad": None},
    )


async def test_projekt_renderowanie_wraca_do_kolejki_z_jedna_wiadomoscia(konf):
    zapisz_wzor(konf, "w1")
    zapisz_projekt(konf, "p1", "renderowanie", wzor_id="w1")

    kolejka_obiekt = kolejka.Kolejka()
    bot_obiekt = zbuduj_bota()
    sesja = bot_obiekt.session

    await bot.wznow_po_starcie(bot_obiekt, konf, kolejka_obiekt)

    assert kolejka_obiekt.dlugosc() == 1
    assert teksty_wyslane(sesja) == ["Wznawiam montaż projektu p1 po restarcie."]
    dane = magazyn.wczytaj_projekt(konf.katalog_danych / "projekty" / "p1")
    assert dane["stan"] == "w_kolejce"


async def test_projekt_w_kolejce_tez_wraca(konf):
    zapisz_wzor(konf, "w1")
    zapisz_projekt(konf, "p1", "w_kolejce", wzor_id="w1")

    kolejka_obiekt = kolejka.Kolejka()
    bot_obiekt = zbuduj_bota()

    await bot.wznow_po_starcie(bot_obiekt, konf, kolejka_obiekt)

    assert kolejka_obiekt.dlugosc() == 1


async def test_projekt_gotowy_pozostaje_nietkniety(konf):
    zapisz_wzor(konf, "w1")
    zapisz_projekt(konf, "p1", "gotowy", wzor_id="w1")

    kolejka_obiekt = kolejka.Kolejka()
    bot_obiekt = zbuduj_bota()
    sesja = bot_obiekt.session

    await bot.wznow_po_starcie(bot_obiekt, konf, kolejka_obiekt)

    assert kolejka_obiekt.dlugosc() == 0
    assert teksty_wyslane(sesja) == []
    dane = magazyn.wczytaj_projekt(konf.katalog_danych / "projekty" / "p1")
    assert dane["stan"] == "gotowy"


async def test_wzor_bez_wzor_json_wraca_do_analizy_a_z_blad_txt_nie(konf):
    katalog_w1 = konf.katalog_danych / "wzory" / "w1"
    katalog_w1.mkdir(parents=True)
    (katalog_w1 / "zrodlo.mp4").write_bytes(b"dane")

    katalog_w2 = konf.katalog_danych / "wzory" / "w2"
    katalog_w2.mkdir(parents=True)
    (katalog_w2 / "zrodlo.mp4").write_bytes(b"dane")
    (katalog_w2 / "blad.txt").write_text("stary blad", encoding="utf-8")

    kolejka_obiekt = kolejka.Kolejka()
    bot_obiekt = zbuduj_bota()
    sesja = bot_obiekt.session

    await bot.wznow_po_starcie(bot_obiekt, konf, kolejka_obiekt)

    assert kolejka_obiekt.dlugosc() == 1
    assert teksty_wyslane(sesja) == ["Wznawiam analizę wzoru w1 po restarcie."]


async def test_nieudana_analiza_zapisuje_blad_txt(konf, monkeypatch):
    bot_obiekt = zbuduj_bota()
    katalog_wzoru = konf.katalog_danych / "wzory" / "w1"
    katalog_wzoru.mkdir(parents=True)
    zrodlo = katalog_wzoru / "zrodlo.mp4"
    zrodlo.write_bytes(b"dane")
    wzor_json = katalog_wzoru / "wzor.json"

    async def uruchom_podmienione(argumenty, limit_s=None, katalog=None):
        return kolejka.Wynik(kod=1, stdout="", stderr="Plik uszkodzony\ndruga linia\n", czas_s=0.1, przekroczono_czas=False)

    monkeypatch.setattr(bot.kolejka_modul, "uruchom", uruchom_podmienione)
    zapowiedz = asyncio.Event()
    zapowiedz.set()
    await bot.analizuj_wzor_w_tle(bot_obiekt, CZAT_ID, zrodlo, wzor_json, zapowiedz)

    assert (katalog_wzoru / "blad.txt").read_text(encoding="utf-8").strip() == "Plik uszkodzony"
    assert not wzor_json.exists()


def zbuduj_projekt_materialow(tmp_path, ilosc=4):
    projekt = tmp_path / "projekt"
    katalog_materialow = projekt / "materialy"
    katalog_materialow.mkdir(parents=True)
    for i in range(ilosc):
        generuj.zdjecie_testowe(katalog_materialow / f"000000000{i}_m.jpg", rozmiar=(800, 600))
    return projekt


def test_render_z_pozostawiona_praca_usuwa_ja_i_konczy_sukcesem(tmp_path):
    projekt = zbuduj_projekt_materialow(tmp_path)
    katalog_pracy = projekt / "praca"
    (katalog_pracy / "segment_000000.mp4").mkdir(parents=True)

    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps({"ciecia_s": [0.0, 1.0, 2.0, 3.0], "zrodlo": {"czas_s": 4.0}}), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=4.0, pierwsze_uderzenie_s=0.0)

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=30, limit_mb=50)

    assert wyjscie.is_file()
    assert not katalog_pracy.exists()
    assert podsumowanie["czas_s"] > 0
