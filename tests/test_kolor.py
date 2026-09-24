import subprocess

import numpy as np
import pytest
from PIL import Image

import kolor


def test_biel_daje_lab_okolo_100_0_0():
    biel = np.full((4, 4, 3), 255, dtype=np.uint8)
    lab = kolor.rgb_do_lab(biel)
    assert lab[..., 0] == pytest.approx(100.0, abs=1.0)
    assert lab[..., 1] == pytest.approx(0.0, abs=1.0)
    assert lab[..., 2] == pytest.approx(0.0, abs=1.0)


def test_czysta_czerwien_daje_oczekiwany_lab():
    czerwien = np.full((4, 4, 3), (255, 0, 0), dtype=np.uint8)
    lab = kolor.rgb_do_lab(czerwien)
    assert lab[..., 0] == pytest.approx(53.2, abs=1.0)
    assert lab[..., 1] == pytest.approx(80.1, abs=1.0)
    assert lab[..., 2] == pytest.approx(67.2, abs=1.0)


def test_rgb_do_lab_akceptuje_float_0_1():
    biel = np.ones((2, 2, 3), dtype=np.float64)
    lab = kolor.rgb_do_lab(biel)
    assert lab[..., 0] == pytest.approx(100.0, abs=1.0)


def test_lab_do_rgb_jest_odwrotnoscia_rgb_do_lab():
    oryginal = np.array([[0.8, 0.2, 0.5]], dtype=np.float64)
    lab = kolor.rgb_do_lab(oryginal)
    powrot = kolor.lab_do_rgb(lab)
    assert powrot == pytest.approx(oryginal, abs=0.01)


def test_statystyki_obrazu_jednolitego_koloru_ma_zerowe_odchylenie():
    obraz = np.full((10, 10, 3), (30, 30, 220), dtype=np.uint8)
    statystyki = kolor.statystyki_obrazu(obraz)
    oczekiwane = kolor.rgb_do_lab(np.array([[30, 30, 220]], dtype=np.uint8))[0]
    assert statystyki["lab_srednia"] == pytest.approx(list(oczekiwane), abs=0.01)
    assert statystyki["lab_odchylenie"] == pytest.approx([0.0, 0.0, 0.0], abs=0.01)


def zapisz_gradient(sciezka, szerokosc=64, wysokosc=64):
    gradient = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
    for x in range(szerokosc):
        gradient[:, x, 0] = round(x * 255 / (szerokosc - 1))
    for y in range(wysokosc):
        gradient[y, :, 1] = round(y * 255 / (wysokosc - 1))
    gradient[:, :, 2] = 128
    Image.fromarray(gradient).save(sciezka)
    return gradient


def zastosuj_lut_przez_ffmpeg(tmp_path, lut, nazwa_lut="test.cube"):
    kolor.zapisz_cube(lut, tmp_path / nazwa_lut)
    wejscie = zapisz_gradient(tmp_path / "gradient.png")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", "gradient.png", "-vf", f"lut3d={nazwa_lut}", "wynik.png"],
        cwd=tmp_path, stdin=subprocess.DEVNULL, capture_output=True, check=True,
    )
    wynik = np.array(Image.open(tmp_path / "wynik.png").convert("RGB"))
    return wejscie, wynik


def test_lut_identycznych_statystyk_jest_tozsama_przez_ffmpeg(tmp_path):
    statystyki = {"lab_srednia": [50.0, 10.0, -5.0], "lab_odchylenie": [20.0, 8.0, 8.0]}
    lut = kolor.lut_transferu(statystyki, statystyki, sila=1.0, rozmiar=17)
    wejscie, wynik = zastosuj_lut_przez_ffmpeg(tmp_path, lut)
    assert np.max(np.abs(wynik.astype(int) - wejscie.astype(int))) <= 2


def test_lut_sila_zero_jest_tozsama_przez_ffmpeg(tmp_path):
    zrodlo = {"lab_srednia": [50.0, 0.0, 0.0], "lab_odchylenie": [15.0, 5.0, 5.0]}
    cel = {"lab_srednia": [30.0, 20.0, -25.0], "lab_odchylenie": [5.0, 2.0, 2.0]}
    lut = kolor.lut_transferu(zrodlo, cel, sila=0.0, rozmiar=17)
    wejscie, wynik = zastosuj_lut_przez_ffmpeg(tmp_path, lut)
    assert np.max(np.abs(wynik.astype(int) - wejscie.astype(int))) <= 2


def test_lut_zrodlo_jednolicie_szare_bez_nan_i_w_zakresie():
    zrodlo = {"lab_srednia": [50.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0]}
    cel = {"lab_srednia": [40.0, 25.0, -30.0], "lab_odchylenie": [18.0, 10.0, 10.0]}
    lut = kolor.lut_transferu(zrodlo, cel, sila=1.0, rozmiar=9)
    assert numpy_bez_nan_i_inf(lut)
    assert lut.min() >= 0.0 and lut.max() <= 1.0


def numpy_bez_nan_i_inf(tablica) -> bool:
    return bool(np.all(np.isfinite(tablica)))


def test_lut_cel_cieply_podnosi_srednie_b_materialu():
    zrodlo = {"lab_srednia": [50.0, 0.0, 0.0], "lab_odchylenie": [15.0, 5.0, 5.0]}
    cel = {"lab_srednia": [50.0, 0.0, 40.0], "lab_odchylenie": [15.0, 5.0, 5.0]}
    lut = kolor.lut_transferu(zrodlo, cel, sila=1.0, rozmiar=17)
    material = np.full((20, 20, 3), (128, 128, 128), dtype=np.uint8)
    b_przed = kolor.statystyki_obrazu(material)["lab_srednia"][2]

    indeksy = np.clip(np.round(material.astype(np.float64) / 255 * (lut.shape[0] - 1)).astype(int), 0, lut.shape[0] - 1)
    po_lut = lut[indeksy[..., 0], indeksy[..., 1], indeksy[..., 2]]
    b_po = kolor.statystyki_obrazu((po_lut * 255).astype(np.uint8))["lab_srednia"][2]
    assert b_po > b_przed


def kolorystyka_dwoch_sekcji():
    return {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [60.0, 5.0, 30.0], "lab_odchylenie": [10.0, 5.0, 5.0], "probki": 10},
            {"lab_srednia": [55.0, 5.0, 25.0], "lab_odchylenie": [10.0, 5.0, 5.0], "probki": 10},
            {"lab_srednia": [40.0, -5.0, -30.0], "lab_odchylenie": [10.0, 5.0, 5.0], "probki": 10},
            {"lab_srednia": [35.0, -5.0, -25.0], "lab_odchylenie": [10.0, 5.0, 5.0], "probki": 10},
            {"lab_srednia": [0.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }


def test_cel_sekcji_hak_i_montaz_liczone_osobno():
    kolorystyka = kolorystyka_dwoch_sekcji()
    sekcje = {"drop_s": 2.0, "drop_ujecie": 2, "koniec_haka_uderzenia": None}
    hak = kolor.cel_sekcji(kolorystyka, sekcje, numer_wzoru=0)
    montaz = kolor.cel_sekcji(kolorystyka, sekcje, numer_wzoru=2)
    assert hak["lab_srednia"][2] > 20
    assert montaz["lab_srednia"][2] < -20


def test_cel_sekcji_pomija_ostatnie_ujecie():
    kolorystyka = {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [50.0, 0.0, 0.0], "lab_odchylenie": [5.0, 5.0, 5.0], "probki": 10},
            {"lab_srednia": [999.0, 999.0, 999.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }
    cel = kolor.cel_sekcji(kolorystyka, None, numer_wzoru=0)
    assert cel["lab_srednia"] == pytest.approx([50.0, 0.0, 0.0])


def test_cel_sekcji_bez_sekcji_jedna_sekcja_wszystkich_ujec():
    kolorystyka = {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [40.0, 0.0, 0.0], "lab_odchylenie": [10.0, 0.0, 0.0], "probki": 10},
            {"lab_srednia": [60.0, 0.0, 0.0], "lab_odchylenie": [10.0, 0.0, 0.0], "probki": 10},
            {"lab_srednia": [0.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }
    cel = kolor.cel_sekcji(kolorystyka, None, numer_wzoru=1)
    assert cel["lab_srednia"][0] == pytest.approx(50.0)


def test_cel_sekcji_pomija_ujecia_bez_probek():
    kolorystyka = {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [40.0, 0.0, 0.0], "lab_odchylenie": [5.0, 0.0, 0.0], "probki": 10},
            {"lab_srednia": [999.0, 999.0, 999.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 0},
            {"lab_srednia": [0.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }
    cel = kolor.cel_sekcji(kolorystyka, None, numer_wzoru=0)
    assert cel["lab_srednia"] == pytest.approx([40.0, 0.0, 0.0])


def test_cel_sekcji_sekcja_bez_uzytecznych_bierze_calosc():
    kolorystyka = {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [40.0, 0.0, 0.0], "lab_odchylenie": [5.0, 0.0, 0.0], "probki": 0},
            {"lab_srednia": [60.0, 0.0, 0.0], "lab_odchylenie": [5.0, 0.0, 0.0], "probki": 10},
            {"lab_srednia": [0.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }
    sekcje = {"drop_s": 1.0, "drop_ujecie": 1, "koniec_haka_uderzenia": None}
    hak = kolor.cel_sekcji(kolorystyka, sekcje, numer_wzoru=0)
    assert hak["lab_srednia"][0] == pytest.approx(60.0)


def test_cel_sekcji_odchylenie_zgodne_z_liczeniem_recznym():
    kolorystyka = {
        "probki_na_s": 10,
        "ujecia": [
            {"lab_srednia": [40.0, 0.0, 0.0], "lab_odchylenie": [4.0, 0.0, 0.0], "probki": 10},
            {"lab_srednia": [60.0, 0.0, 0.0], "lab_odchylenie": [6.0, 0.0, 0.0], "probki": 20},
            {"lab_srednia": [0.0, 0.0, 0.0], "lab_odchylenie": [0.0, 0.0, 0.0], "probki": 10},
        ],
    }
    cel = kolor.cel_sekcji(kolorystyka, None, numer_wzoru=0)
    srednia_reczna = (10 * 40.0 + 20 * 60.0) / 30
    wariancja_reczna = (
        10 * (4.0 ** 2 + (40.0 - srednia_reczna) ** 2) + 20 * (6.0 ** 2 + (60.0 - srednia_reczna) ** 2)
    ) / 30
    assert cel["lab_srednia"][0] == pytest.approx(srednia_reczna)
    assert cel["lab_odchylenie"][0] == pytest.approx(wariancja_reczna ** 0.5)
