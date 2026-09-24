import json

import numpy as np
import pytest
from PIL import Image

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


def zbuduj_projekt_czarny(tmp_path, n=4):
    def dodaj(katalog):
        for i in range(n):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(0, 0, 0))

    return zbuduj_projekt(tmp_path, dodaj)


def zrenderuj(tmp_path, projekt, wzor, nakladka=None, plansza=None, znak=None, szerokosc=270, wysokosc=480, fps=30):
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)
    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(
        wzor_json, projekt, utwor, wyjscie,
        szerokosc=szerokosc, wysokosc=wysokosc, fps=fps, limit_mb=50,
        nakladka=nakladka, plansza=plansza, znak=znak,
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

    dane = uruchom_ffprobe(wyjscie)
    strumien = strumien_wideo(dane)
    assert strumien["pix_fmt"] == "yuv420p"
    assert strumien.get("color_range") != "pc"

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    ostatnia = klatki[-1]
    gora = pas_gorny(ostatnia)
    dol = pas_dolny(ostatnia)
    assert gora[0] >= 250 and gora[1] >= 250 and gora[2] >= 250
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


def test_nakladka_bez_sekcji_zaczyna_sie_od_konca_haka(tmp_path):
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

    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)
    granica = render.koniec_haka(plan, wzor.get("sekcje"))

    assert podsumowanie["nakladka"]["od_s"] == pytest.approx(granica / fps, abs=1e-6)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    przed = pas_gorny(klatki[max(0, granica - 3)])
    po = pas_gorny(klatki[min(klatki.shape[0] - 1, granica + 3)])
    assert jest_niebieski(przed)
    assert jest_czerwony(po)


def plan_dziesieciu_ujec():
    return {"fps": 30, "liczba_klatek": 300, "ujecia": [{"klatka_od": i * 30, "numer_wzoru": i} for i in range(10)]}


def test_koniec_haka_bez_sekcji_czterdziesci_procent():
    assert render.koniec_haka(plan_dziesieciu_ujec(), None) == 120


def test_koniec_haka_z_sekcjami_uzywa_drop_ujecie():
    assert render.koniec_haka(plan_dziesieciu_ujec(), {"drop_ujecie": 3}) == 90


def test_koniec_haka_drop_ujecie_poza_zakresem_wraca_do_40_procent():
    assert render.koniec_haka(plan_dziesieciu_ujec(), {"drop_ujecie": 99}) == 120


def test_znak_wodny_pozycja_i_krycie(tmp_path):
    projekt = zbuduj_projekt_czarny(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    znak = tmp_path / "znak.png"
    generuj.znak_testowy(znak, rozmiar=(200, 50))

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, znak=znak)
    assert podsumowanie["znak"] is True

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    klatka = klatki[klatki.shape[0] // 2]
    wysokosc, szerokosc = klatka.shape[:2]

    srodek_x = szerokosc // 2
    srodek_y = round(wysokosc * 0.8)
    piksel_srodkowy = klatka[srodek_y, srodek_x].astype(np.int32)
    assert 140 <= piksel_srodkowy.mean() <= 175

    piksel_poza = klatka[5, 5]
    assert piksel_poza.max() <= 6

    kolumna = klatka[srodek_y, :, 0].astype(np.int32)
    jasne_poziomo = np.where(kolumna > 100)[0]
    assert jasne_poziomo.size > 0
    szerokosc_znaku = jasne_poziomo[-1] - jasne_poziomo[0] + 1
    assert abs(szerokosc_znaku / szerokosc - 0.51) <= 2 / szerokosc + 0.02

    wiersz = klatka[:, srodek_x, 0].astype(np.int32)
    jasne_pionowo = np.where(wiersz > 100)[0]
    assert jasne_pionowo.size > 0
    assert 0.75 <= jasne_pionowo[0] / wysokosc <= 0.85
    assert 0.75 <= jasne_pionowo[-1] / wysokosc <= 0.85


def test_znak_wodny_bez_na_planszy(tmp_path):
    projekt = zbuduj_projekt_czarny(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    znak = tmp_path / "znak.png"
    generuj.znak_testowy(znak, rozmiar=(200, 50))
    plansza = tmp_path / "plansza.jpg"
    generuj.zdjecie_testowe(plansza, rozmiar=(1600, 900), kolor=(0, 0, 0))

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, znak=znak, plansza=plansza)
    assert podsumowanie["plansza"] == "plansza.jpg"

    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    ostatnie_ujecie = plan["ujecia"][-1]
    srodek = ostatnie_ujecie["klatka_od"] + ostatnie_ujecie["liczba_klatek"] // 2
    srodek = min(srodek, klatki.shape[0] - 1)
    klatka_planszy = klatki[srodek]
    wysokosc, szerokosc = klatka_planszy.shape[:2]
    piksel = klatka_planszy[round(wysokosc * 0.8), szerokosc // 2].astype(np.int32)
    assert piksel.max() <= 6


def test_znak_wodny_nad_nakladka_alfa(tmp_path):
    projekt = zbuduj_projekt_czarny(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    nakladka = tmp_path / "nakladka.png"
    Image.new("RGBA", (270, 480), (220, 30, 30, 255)).save(nakladka)
    znak = tmp_path / "znak.png"
    generuj.znak_testowy(znak, rozmiar=(200, 50))

    wyjscie, _ = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka, znak=znak)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    klatka = klatki[-2]
    wysokosc, szerokosc = klatka.shape[:2]
    piksel = klatka[round(wysokosc * 0.8), szerokosc // 2].astype(np.int32)
    assert piksel[1] > 100 and piksel[2] > 100
