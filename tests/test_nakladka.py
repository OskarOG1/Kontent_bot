import json

import numpy as np
import pytest

import analyze
import generuj
import render
from test_render import (
    dekoduj_klatki,
    strumien_wideo,
    uruchom_ffprobe,
    zbuduj_projekt,
)


def wzor_4_ciecia_z_dropem(drop_ujecie):
    return {
        "ciecia_uderzenia": [0.0, 1.0, 2.0, 3.0],
        "koniec_uderzenia": 4.0,
        "ciecia_s": [0.0],
        "zrodlo": {"czas_s": 4.0},
        "sekcje": {"drop_s": None, "drop_ujecie": drop_ujecie, "koniec_haka_uderzenia": None},
    }


def zbuduj_projekt_niebieski(tmp_path, n=4):
    def dodaj(katalog):
        for i in range(n):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(0, 0, 255))

    return zbuduj_projekt(tmp_path, dodaj)


def zrenderuj(tmp_path, projekt, wzor, nakladka=None, plansza=None, szerokosc=270, wysokosc=480, fps=30):
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)
    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(
        wzor_json, projekt, utwor, wyjscie,
        szerokosc=szerokosc, wysokosc=wysokosc, fps=fps, limit_mb=50,
        nakladka=nakladka, plansza=plansza,
    )
    return wyjscie, podsumowanie


def pas_gorny(klatka, ulamek=0.2):
    wysokosc = klatka.shape[0]
    n = max(1, round(wysokosc * ulamek))
    return klatka[:n].reshape(-1, 3).astype(np.int32).mean(axis=0)


def pas_dolny(klatka, ulamek=0.2):
    wysokosc = klatka.shape[0]
    n = max(1, round(wysokosc * ulamek))
    return klatka[-n:].reshape(-1, 3).astype(np.int32).mean(axis=0)


def jest_czerwony(kolor, tolerancja=30):
    return kolor[0] > 150 and kolor[1] < 100 and kolor[2] < 100


def jest_niebieski(kolor, tolerancja=30):
    return kolor[2] > 150 and kolor[0] < 100 and kolor[1] < 100


def jest_zielony(kolor):
    return kolor[1] > 150 and kolor[0] < 100 and kolor[2] < 100


def jest_bialy(kolor):
    return kolor[0] > 220 and kolor[1] > 220 and kolor[2] > 220


def test_tryb_nakladki_rozpoznaje_cztery_pliki(tmp_path):
    alfa = tmp_path / "alfa.mov"
    generuj.nakladka_testowa(alfa, 0.5, "alfa")
    zielen = tmp_path / "zielen.mp4"
    generuj.nakladka_testowa(zielen, 0.5, "zielen")
    ekran = tmp_path / "ekran.mp4"
    generuj.nakladka_testowa(ekran, 0.5, "ekran")
    png = tmp_path / "obraz.png"
    generuj.nakladka_testowa(png, 0.5, "png")

    assert render.tryb_nakladki(alfa) == "alfa"
    assert render.tryb_nakladki(zielen) == "zielen"
    assert render.tryb_nakladki(ekran) == "ekran"
    assert render.tryb_nakladki(png) == "alfa"


def test_nakladka_alfa_wchodzi_od_dropu_i_dol_zostaje_niebieski(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(2)
    nakladka = tmp_path / "nakladka.mov"
    generuj.nakladka_testowa(nakladka, 1.0, "alfa")

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    assert klatki.shape[0] == pytest.approx(plan["liczba_klatek"], abs=1)

    for indeks, ujecie in enumerate(plan["ujecia"]):
        srodek = ujecie["klatka_od"] + ujecie["liczba_klatek"] // 2
        srodek = min(srodek, klatki.shape[0] - 1)
        klatka = klatki[srodek]
        gora = pas_gorny(klatka)
        dol = pas_dolny(klatka)
        assert jest_niebieski(dol)
        if indeks < 2:
            assert jest_niebieski(gora)
        else:
            assert jest_czerwony(gora)


def test_nakladka_zielen_dol_zostaje_niebieski_nie_zielony(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    nakladka = tmp_path / "nakladka.mp4"
    generuj.nakladka_testowa(nakladka, 1.0, "zielen")

    wyjscie, _ = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    srodek = klatki[klatki.shape[0] // 2]
    dol = pas_dolny(srodek)
    assert jest_niebieski(dol)
    assert not jest_zielony(dol)


def test_nakladka_ekran_gora_biala_dol_niebieski_bez_zmian(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    nakladka = tmp_path / "nakladka.mp4"
    generuj.nakladka_testowa(nakladka, 1.0, "ekran")

    wyjscie, _ = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    srodek = klatki[klatki.shape[0] // 2]
    gora = pas_gorny(srodek)
    dol = pas_dolny(srodek)
    assert jest_bialy(gora)
    assert abs(int(dol[2]) - 255) <= 6 and dol[0] <= 6 and dol[1] <= 6


def test_plansza_z_nakladka_alfa_konczy_okno_nakladki_przed_plansza(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    nakladka = tmp_path / "nakladka.mov"
    generuj.nakladka_testowa(nakladka, 1.0, "alfa")
    plansza = tmp_path / "plansza.jpg"
    generuj.zdjecie_testowe(plansza, rozmiar=(1600, 900), kolor=(0, 255, 0))

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka, plansza=plansza)
    assert podsumowanie["plansza"] == "plansza.jpg"

    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    assert klatki.shape[0] == pytest.approx(plan["liczba_klatek"], abs=1)

    ostatnie_ujecie = plan["ujecia"][-1]
    srodek = ostatnie_ujecie["klatka_od"] + ostatnie_ujecie["liczba_klatek"] // 2
    srodek = min(srodek, klatki.shape[0] - 1)
    klatka_planszy = klatki[srodek]
    wysokosc, szerokosc = klatka_planszy.shape[:2]
    srodkowy_piksel = klatka_planszy[wysokosc // 2, szerokosc // 2]
    assert jest_zielony(srodkowy_piksel)
    gora = pas_gorny(klatka_planszy)
    assert not jest_czerwony(gora)


def test_nakladka_krotsza_od_okna_zapetla_sie(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = {
        "ciecia_uderzenia": [],
        "ciecia_s": [0.0, 0.5, 1.0, 1.5],
        "zrodlo": {"czas_s": 2.0},
        "sekcje": {"drop_s": None, "drop_ujecie": 0, "koniec_haka_uderzenia": None},
    }
    nakladka = tmp_path / "nakladka.mp4"
    generuj.nakladka_testowa(nakladka, 0.5, "zielen")

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    assert wyjscie.exists()
    dane = uruchom_ffprobe(wyjscie)
    strumien = strumien_wideo(dane)
    assert abs(float(strumien["duration"]) - 2.0) <= 1.0 / 30 + 0.02


def test_bez_nakladki_i_planszy_dwa_wejscia_w_przebiegu_koncowym(tmp_path, monkeypatch):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(2)

    wywolania = []
    oryginalny = render.uruchom_ffmpeg

    def podmieniony(argumenty):
        wywolania.append(argumenty)
        oryginalny(argumenty)

    monkeypatch.setattr(render, "uruchom_ffmpeg", podmieniony)

    zrenderuj(tmp_path, projekt, wzor)

    przebiegi_koncowe = [a for a in wywolania if "-x264-params" in a]
    assert len(przebiegi_koncowe) == 1
    assert przebiegi_koncowe[0].count("-i") == 2


def test_nakladka_bez_sekcji_leci_od_poczatku_editu(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = {
        "ciecia_uderzenia": [0.0, 1.0, 2.0, 3.0],
        "koniec_uderzenia": 4.0,
        "ciecia_s": [0.0],
        "zrodlo": {"czas_s": 4.0},
    }
    nakladka = tmp_path / "nakladka.mov"
    generuj.nakladka_testowa(nakladka, 1.0, "alfa")

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    assert podsumowanie["nakladka"]["od_s"] == 0.0

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    gora = pas_gorny(klatki[0])
    assert jest_czerwony(gora)
