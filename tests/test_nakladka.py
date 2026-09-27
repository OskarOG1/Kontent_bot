import json
import subprocess
from pathlib import Path

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


def zrenderuj(
    tmp_path, projekt, wzor, nakladka=None, plansza=None, znak=None, szerokosc=270, wysokosc=480, fps=30,
    dlugosc_nakladki_krycie_s=None,
):
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)
    wyjscie = tmp_path / "wynik.mp4"
    dodatkowe = {}
    if dlugosc_nakladki_krycie_s is not None:
        dodatkowe["dlugosc_nakladki_krycie_s"] = dlugosc_nakladki_krycie_s
    podsumowanie = render.renderuj(
        wzor_json, projekt, utwor, wyjscie,
        szerokosc=szerokosc, wysokosc=wysokosc, fps=fps, limit_mb=50,
        nakladka=nakladka, plansza=plansza, znak=znak, bez_dynamiki=True,
        **dodatkowe,
    )
    return wyjscie, podsumowanie


def nakladka_krycie_16_9_ze_znacznikami(sciezka, czas_s=1.0, fps=30, rozmiar=(640, 360), pozycje_x=(176, 464)):
    import tempfile

    szerokosc, wysokosc = rozmiar
    tlo = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
    tlo[:] = (100, 100, 180)
    bok = 24
    y0 = wysokosc // 2 - bok // 2
    for x0 in pozycje_x:
        tlo[y0:y0 + bok, x0:x0 + bok] = (220, 30, 30)
    dane_klatki = tlo.tobytes()
    liczba_klatek = max(1, round(czas_s * fps))
    argumenty = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc}x{wysokosc}",
        "-framerate", str(fps), "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "-an",
        "-frames:v", str(liczba_klatek), str(sciezka),
    ]
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        with open(katalog / "stderr.txt", "wb") as plik_bledow:
            proces = subprocess.Popen(argumenty, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=plik_bledow)
            try:
                for _ in range(liczba_klatek):
                    proces.stdin.write(dane_klatki)
            except BrokenPipeError:
                pass
            finally:
                try:
                    proces.stdin.close()
                except BrokenPipeError:
                    pass
            kod = proces.wait()
        if kod != 0:
            blad = (katalog / "stderr.txt").read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {kod}: {blad}")


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


def test_tryb_nakladki_rozpoznaje_piec_plikow(tmp_path):
    alfa = tmp_path / "alfa.mov"
    generuj.nakladka_testowa(alfa, 0.5, "alfa")
    zielen = tmp_path / "zielen.mp4"
    generuj.nakladka_testowa(zielen, 0.5, "zielen")
    ekran = tmp_path / "ekran.mp4"
    generuj.nakladka_testowa(ekran, 0.5, "ekran")
    png = tmp_path / "obraz.png"
    generuj.nakladka_testowa(png, 0.5, "png")
    krycie = tmp_path / "krycie.mp4"
    generuj.nakladka_testowa(krycie, 0.5, "krycie")

    assert render.tryb_nakladki(alfa) == "alfa"
    assert render.tryb_nakladki(zielen) == "zielen"
    assert render.tryb_nakladki(ekran) == "ekran"
    assert render.tryb_nakladki(png) == "alfa"
    assert render.tryb_nakladki(krycie) == "krycie"


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


def test_nakladka_krycie_okno_daje_srednia_a_poza_oknem_bez_zmian(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(2)
    nakladka = tmp_path / "nakladka.mp4"
    generuj.nakladka_testowa(nakladka, 1.0, "krycie")

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)
    assert podsumowanie["nakladka"]["tryb"] == "krycie"

    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)

    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    material = np.array([0, 0, 255])
    zolty = np.array([255, 220, 0])
    granat = np.array([0, 51, 153])

    for indeks, ujecie in enumerate(plan["ujecia"]):
        srodek = ujecie["klatka_od"] + ujecie["liczba_klatek"] // 2
        srodek = min(srodek, klatki.shape[0] - 1)
        klatka = klatki[srodek]
        gora = pas_gorny(klatka)
        dol = pas_dolny(klatka)
        if indeks < 2:
            assert jest_niebieski(gora)
            assert jest_niebieski(dol)
        else:
            assert np.all(np.abs(gora - (material + zolty) / 2) <= 8)
            assert np.all(np.abs(dol - (material + granat) / 2) <= 8)


def test_nakladka_alfa_pierscien_miesci_sie_caly_w_kadrze(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(0)
    nakladka = tmp_path / "pierscien.png"
    generuj.pierscien_testowy(nakladka, rozmiar=(600, 600))

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)
    assert podsumowanie["nakladka"]["tryb"] == "alfa"

    fps = 30
    od_s = podsumowanie["nakladka"]["od_s"]
    do_s = podsumowanie["nakladka"]["do_s"]
    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    srodek = min(round((od_s + do_s) / 2 * fps), klatki.shape[0] - 1)
    klatka = klatki[srodek]
    wysokosc, szerokosc = klatka.shape[:2]

    def maska_zolta(pasek):
        pasek = pasek.astype(np.int32)
        return (pasek[:, 0] > 150) & (pasek[:, 1] > 120) & (pasek[:, 2] < 100)

    srodkowy_wiersz = klatka[wysokosc // 2]
    zolte_poziomo = np.where(maska_zolta(srodkowy_wiersz))[0]
    assert zolte_poziomo.size > 0
    assert 0.05 <= zolte_poziomo[0] / szerokosc <= 0.95
    assert 0.05 <= zolte_poziomo[-1] / szerokosc <= 0.95

    srodkowa_kolumna = klatka[:, szerokosc // 2]
    zolte_pionowo = np.where(maska_zolta(srodkowa_kolumna))[0]
    assert zolte_pionowo.size > 0
    srodek_pierscienia = (zolte_pionowo[0] + zolte_pionowo[-1]) / 2
    assert abs(srodek_pierscienia - wysokosc / 2) <= 2

    gora = klatka[:5].reshape(-1, 3).astype(np.int32).mean(axis=0)
    dol = klatka[-5:].reshape(-1, 3).astype(np.int32).mean(axis=0)
    assert jest_niebieski(gora)
    assert jest_niebieski(dol)


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

    def podmieniony(argumenty, katalog=None):
        wywolania.append(argumenty)
        oryginalny(argumenty, katalog=katalog)

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


def test_kolor_brzegu_srednia_gornych_i_dolnych_wierszy(tmp_path):
    nakladka = tmp_path / "krycie_16_9.mp4"
    nakladka_krycie_16_9_ze_znacznikami(nakladka)

    r, g, b = render.kolor_brzegu(nakladka)

    assert abs(r - 100) <= 10
    assert abs(g - 100) <= 10
    assert abs(b - 180) <= 10


def test_nakladka_krycie_16_9_oba_znaczniki_widoczne_w_kadrze_9_16(tmp_path):
    projekt = zbuduj_projekt_czarny(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(2)
    nakladka = tmp_path / "krycie_16_9.mp4"
    nakladka_krycie_16_9_ze_znacznikami(nakladka, czas_s=1.0)

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)
    assert podsumowanie["nakladka"]["tryb"] == "krycie"

    fps = 30
    od_s = podsumowanie["nakladka"]["od_s"]
    do_s = podsumowanie["nakladka"]["do_s"]
    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    srodek = min(round((od_s + do_s) / 2 * fps), klatki.shape[0] - 1)
    klatka = klatki[srodek].astype(np.int32)
    wysokosc, szerokosc = klatka.shape[:2]

    lewa_strefa = klatka[:, :round(szerokosc * 0.2)]
    prawa_strefa = klatka[:, round(szerokosc * 0.8):]

    def ma_czerwony(strefa):
        return bool(np.any((strefa[..., 0] - strefa[..., 1] > 30) & (strefa[..., 0] - strefa[..., 2] > 30)))

    assert ma_czerwony(lewa_strefa)
    assert ma_czerwony(prawa_strefa)


def wzor_dlugi_z_dropem():
    return {
        "ciecia_uderzenia": [0.0, 1.0, 2.0, 8.0],
        "koniec_uderzenia": 9.0,
        "ciecia_s": [0.0],
        "zrodlo": {"czas_s": 9.0},
        "sekcje": {"drop_s": None, "drop_ujecie": 2, "koniec_haka_uderzenia": None},
    }


def test_nakladka_krycie_ograniczona_do_2_5s_od_dropu(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_dlugi_z_dropem()
    nakladka = tmp_path / "krycie.mp4"
    generuj.nakladka_testowa(nakladka, 3.0, "krycie")

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)

    assert podsumowanie["nakladka"]["tryb"] == "krycie"
    assert podsumowanie["nakladka"]["do_s"] == pytest.approx(podsumowanie["nakladka"]["od_s"] + 2.5, abs=1e-3)


def test_nakladka_krycie_zero_trwa_do_konca_i_alfa_bez_zmian(tmp_path):
    projekt = zbuduj_projekt_niebieski(tmp_path)
    wzor = wzor_dlugi_z_dropem()
    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]

    nakladka_krycie = tmp_path / "krycie.mp4"
    generuj.nakladka_testowa(nakladka_krycie, 5.0, "krycie")
    wyjscie_krycie, podsumowanie_krycie = zrenderuj(
        tmp_path, projekt, wzor, nakladka=nakladka_krycie, dlugosc_nakladki_krycie_s=0,
    )
    _, uderzenia = analyze.analizuj_rytm(tmp_path / "klik.wav")
    plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)
    oczekiwany_koniec_s = plan["liczba_klatek"] / fps
    assert podsumowanie_krycie["nakladka"]["do_s"] == pytest.approx(oczekiwany_koniec_s, abs=1e-3)
    assert oczekiwany_koniec_s - podsumowanie_krycie["nakladka"]["od_s"] > 2.5

    nakladka_alfa = tmp_path / "alfa.mov"
    generuj.nakladka_testowa(nakladka_alfa, 5.0, "alfa")
    wyjscie_alfa, podsumowanie_alfa = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka_alfa)
    assert podsumowanie_alfa["nakladka"]["tryb"] == "alfa"
    assert podsumowanie_alfa["nakladka"]["do_s"] == pytest.approx(oczekiwany_koniec_s, abs=1e-3)


def opcje_wejsc(polecenie):
    wynik = []
    opcje = []
    i = 0
    while i < len(polecenie):
        token = polecenie[i]
        if token == "-filter_complex":
            break
        opcje.append(token)
        if token == "-i":
            wynik.append((opcje[:-1], polecenie[i + 1]))
            opcje = []
            i += 2
            continue
        i += 1
    return wynik


def klatki_pliku(sciezka):
    wynik = subprocess.run(
        [
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(sciezka),
        ],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return int(wynik.stdout.decode("utf-8", errors="replace").strip())


def test_warstwy_przebiegu_koncowego_jako_klipy_bez_t_loop_stream_loop(tmp_path, monkeypatch):
    fps = 30
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]

    alfa_png = tmp_path / "alfa.png"
    generuj.nakladka_testowa(alfa_png, 1.0, "png")
    alfa_vp9 = tmp_path / "alfa_vp9.webm"
    generuj.nakladka_vp9_alfa_testowa(alfa_vp9, 1.0)
    zielen = tmp_path / "zielen.mp4"
    generuj.nakladka_testowa(zielen, 1.0, "zielen")
    ekran = tmp_path / "ekran.mp4"
    generuj.nakladka_testowa(ekran, 1.0, "ekran")
    krycie = tmp_path / "krycie.mp4"
    generuj.nakladka_testowa(krycie, 1.0, "krycie")

    warianty = [
        ("alfa", alfa_png),
        ("alfa", alfa_vp9),
        ("zielen", zielen),
        ("ekran", ekran),
        ("krycie", krycie),
    ]

    oryginalny = render.uruchom_ffmpeg

    for indeks, (tryb_oczekiwany, nakladka) in enumerate(warianty):
        katalog_wariantu = tmp_path / f"wariant_{indeks}"
        katalog_wariantu.mkdir()
        projekt = zbuduj_projekt_czarny(katalog_wariantu)
        wzor = wzor_4_ciecia_z_dropem(2)
        znak = katalog_wariantu / "znak.png"
        generuj.znak_testowy(znak, rozmiar=(200, 50))

        wywolania = []
        klatki_zmierzone = {}

        def podmieniony(argumenty, katalog=None):
            wywolania.append(argumenty)
            oryginalny(argumenty, katalog=katalog)
            nazwa = Path(argumenty[-1]).name
            if nazwa in ("nakladka.mov", "nakladka.mp4", "znak.mov"):
                klatki_zmierzone[nazwa] = klatki_pliku(argumenty[-1])

        monkeypatch.setattr(render, "uruchom_ffmpeg", podmieniony)

        wyjscie, podsumowanie = zrenderuj(katalog_wariantu, projekt, wzor, nakladka=nakladka, znak=znak)
        assert podsumowanie["nakladka"]["tryb"] == tryb_oczekiwany

        przebiegi_koncowe = [a for a in wywolania if "-x264-params" in a]
        assert len(przebiegi_koncowe) == 1
        polecenie = przebiegi_koncowe[0]

        wejscia_info = opcje_wejsc(polecenie)
        assert len(wejscia_info) == 4

        for opcje, _plik in wejscia_info[2:]:
            assert "-t" not in opcje
            assert "-loop" not in opcje
            assert "-stream_loop" not in opcje

        _, plik_nakladki = wejscia_info[2]
        _, plik_znaku = wejscia_info[3]
        assert Path(plik_nakladki).name in klatki_zmierzone
        assert Path(plik_znaku).name in klatki_zmierzone

        od_s = podsumowanie["nakladka"]["od_s"]
        do_s = podsumowanie["nakladka"]["do_s"]
        oczekiwane_klatki_nakladki = round((do_s - od_s) * fps)
        assert klatki_zmierzone[Path(plik_nakladki).name] == oczekiwane_klatki_nakladki

        _, uderzenia = analyze.analizuj_rytm(katalog_wariantu / "klik.wav")
        plan = render.plan_ujec(wzor, uderzenia, material_zastepczy, fps)
        assert klatki_zmierzone[Path(plik_znaku).name] == plan["liczba_klatek"]


def test_nakladka_krycie_skala_miesci_znaczniki_blisko_krawedzi_zrodla(tmp_path):
    projekt = zbuduj_projekt_czarny(tmp_path)
    wzor = wzor_4_ciecia_z_dropem(2)
    nakladka = tmp_path / "krycie_szeroka.mp4"
    nakladka_krycie_16_9_ze_znacznikami(nakladka, czas_s=1.0, pozycje_x=(128, 512))

    wyjscie, podsumowanie = zrenderuj(tmp_path, projekt, wzor, nakladka=nakladka)
    assert podsumowanie["nakladka"]["tryb"] == "krycie"

    fps = 30
    od_s = podsumowanie["nakladka"]["od_s"]
    do_s = podsumowanie["nakladka"]["do_s"]
    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    srodek = min(round((od_s + do_s) / 2 * fps), klatki.shape[0] - 1)
    klatka = klatki[srodek].astype(np.int32)
    wysokosc, szerokosc = klatka.shape[:2]

    lewa_strefa = klatka[:, :round(szerokosc * 0.2)]
    prawa_strefa = klatka[:, round(szerokosc * 0.8):]

    def ma_czerwony(strefa):
        return bool(np.any((strefa[..., 0] - strefa[..., 1] > 30) & (strefa[..., 0] - strefa[..., 2] > 30)))

    assert ma_czerwony(lewa_strefa)
    assert ma_czerwony(prawa_strefa)


def test_materializuj_nakladke_z_dzwiekiem_daje_sam_obraz(tmp_path):
    zrodlo = tmp_path / "flaga_z_dzwiekiem.mp4"
    generuj.nakladka_z_dzwiekiem_testowa(zrodlo, 1.0)

    wynik = render.materializuj_nakladke(zrodlo, "krycie", 75, 30, 270, 480, tmp_path)

    typy = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(wynik)],
        stdin=subprocess.DEVNULL, capture_output=True,
    ).stdout.decode("utf-8", errors="replace").split()
    assert typy == ["video"]
    assert klatki_pliku(wynik) == 75
