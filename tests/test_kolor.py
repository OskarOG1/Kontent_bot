import numpy as np
import pytest

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
