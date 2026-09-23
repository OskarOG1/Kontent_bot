import json
import subprocess

import numpy as np
from PIL import Image, ImageOps

import generuj


def uruchom_ffprobe(sciezka):
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", "-show_streams", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return json.loads(wynik.stdout.decode("utf-8", errors="replace"))


def strumien_wideo(dane):
    for strumien in dane["streams"]:
        if strumien["codec_type"] == "video":
            return strumien
    raise AssertionError("brak strumienia wideo")


def rotacja_strumienia(strumien):
    for wpis in strumien.get("side_data_list", []):
        if "rotation" in wpis:
            return int(float(wpis["rotation"]))
    return 0


def zdekoduj_pierwsza_klatke(sciezka, tmp_path, nazwa):
    surowy = tmp_path / nazwa
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(sciezka), "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", str(surowy)],
        stdin=subprocess.DEVNULL, check=True,
    )
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    if rotacja_strumienia(strumien) % 180 == 90:
        szerokosc, wysokosc = int(strumien["height"]), int(strumien["width"])
    else:
        szerokosc, wysokosc = int(strumien["width"]), int(strumien["height"])
    return np.fromfile(surowy, dtype=np.uint8).reshape(wysokosc, szerokosc, 3)


def gora_czerwona(klatka):
    polowa = klatka.shape[0] // 2
    gora = klatka[:polowa].astype(np.int32).mean(axis=(0, 1))
    dol = klatka[polowa:].astype(np.int32).mean(axis=(0, 1))
    return gora[0] > gora[2] and dol[2] > dol[0]


def test_zdjecie_testowe_exif_transpose_daje_czerwien_na_gorze(tmp_path):
    for orientacja in (1, 6, 8):
        sciezka = tmp_path / f"zdjecie_{orientacja}.jpg"
        generuj.zdjecie_testowe(sciezka, rozmiar=(120, 160), orientacja_exif=orientacja)
        obraz = ImageOps.exif_transpose(Image.open(sciezka))
        assert obraz.size == (120, 160)
        tablica = np.array(obraz.convert("RGB"))
        assert gora_czerwona(tablica)


def test_klip_testowy_bez_obrotu_ma_czerwien_na_gorze(tmp_path):
    sciezka = tmp_path / "klip_0.mp4"
    generuj.klip_testowy(sciezka, czas_s=0.2, rozmiar=(120, 160), obrot=0)
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    assert rotacja_strumienia(strumien) == 0
    klatka = zdekoduj_pierwsza_klatke(sciezka, tmp_path, "dekodowana_0.raw")
    assert klatka.shape[:2] == (160, 120)
    assert gora_czerwona(klatka)


def test_klip_testowy_z_obrotem_90_ma_czerwien_na_gorze_i_metadane(tmp_path):
    sciezka = tmp_path / "klip_90.mp4"
    generuj.klip_testowy(sciezka, czas_s=0.2, rozmiar=(120, 160), obrot=90)
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    assert rotacja_strumienia(strumien) % 180 == 90
    assert int(strumien["width"]) == 160 and int(strumien["height"]) == 120
    klatka = zdekoduj_pierwsza_klatke(sciezka, tmp_path, "dekodowana_90.raw")
    assert klatka.shape[:2] == (160, 120)
    assert gora_czerwona(klatka)


def test_klip_testowy_z_obrotem_270_ma_czerwien_na_gorze_i_metadane(tmp_path):
    sciezka = tmp_path / "klip_270.mp4"
    generuj.klip_testowy(sciezka, czas_s=0.2, rozmiar=(120, 160), obrot=270)
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    assert rotacja_strumienia(strumien) % 180 == 90
    klatka = zdekoduj_pierwsza_klatke(sciezka, tmp_path, "dekodowana_270.raw")
    assert klatka.shape[:2] == (160, 120)
    assert gora_czerwona(klatka)


def test_zdjecie_testowe_z_alfa_ma_przezroczysty_fragment(tmp_path):
    sciezka = tmp_path / "zdjecie_alfa.png"
    generuj.zdjecie_testowe(sciezka, rozmiar=(120, 160), alfa=True)
    obraz = Image.open(sciezka)
    assert obraz.mode == "RGBA"
    tablica = np.array(obraz)
    assert (tablica[:, :, 3] == 0).any()
    assert (tablica[:, :, 3] == 255).any()


def test_szum_generuje_rozny_material(tmp_path):
    sciezka = tmp_path / "szum.mp4"
    generuj.szum(sciezka, czas_s=0.3, rozmiar=(120, 80))
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    assert int(strumien["width"]) == 120 and int(strumien["height"]) == 80
