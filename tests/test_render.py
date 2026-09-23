import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageOps

import analyze
import generuj
import render


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


def materialy_zdjec(n):
    return [{"plik": f"zdjecie_{i}.jpg", "typ": "zdjecie", "message_id": i} for i in range(n)]


def test_plan_ujec_granice_z_czasow_bezwzglednych_bez_dryfu():
    bpm = 123.0
    odstep = 60.0 / bpm
    uderzenia_utworu = [round(0.2 + i * odstep, 6) for i in range(200)]
    ciecia_uderzenia = [round(i * 0.5, 6) for i in range(64)]
    koniec_uderzenia = 32.0
    wzor = {"ciecia_uderzenia": ciecia_uderzenia, "koniec_uderzenia": koniec_uderzenia}
    fps = 30
    materialy = materialy_zdjec(5)

    wynik = render.plan_ujec(wzor, uderzenia_utworu, materialy, fps)

    s = 0
    while analyze.czas_z_pozycji(s + ciecia_uderzenia[0], uderzenia_utworu) < 0:
        s += 1
    pozycje = ciecia_uderzenia + [koniec_uderzenia]
    czasy = [analyze.czas_z_pozycji(s + p, uderzenia_utworu) for p in pozycje]
    granice = [round((t - czasy[0]) * fps) for t in czasy]
    oczekiwane = [(granice[k], granice[k + 1] - granice[k]) for k in range(len(granice) - 1) if granice[k + 1] - granice[k] > 0]

    assert wynik["liczba_klatek"] == granice[-1]
    assert [(u["klatka_od"], u["liczba_klatek"]) for u in wynik["ujecia"]] == oczekiwane
    assert sum(u["liczba_klatek"] for u in wynik["ujecia"]) == wynik["liczba_klatek"]


def test_plan_ujec_przypadek_reczny():
    uderzenia_utworu = [round(0.3 + i * 0.6, 6) for i in range(10)]
    wzor = {"ciecia_uderzenia": [-0.25, 0.75, 1.75, 2.25], "koniec_uderzenia": 3.75}
    fps = 10
    materialy = materialy_zdjec(2)

    wynik = render.plan_ujec(wzor, uderzenia_utworu, materialy, fps)

    assert wynik["start_audio_s"] == pytest.approx(0.15, abs=1e-6)
    assert wynik["liczba_klatek"] == 24
    assert [(u["klatka_od"], u["liczba_klatek"]) for u in wynik["ujecia"]] == [(0, 6), (6, 6), (12, 3), (15, 9)]


def test_plan_ujec_pierwsze_uderzenie_blisko_zera_daje_nieujemny_start():
    uderzenia_utworu = [round(0.1 + i * 0.5, 6) for i in range(20)]
    wzor = {"ciecia_uderzenia": [-0.25, 0.25], "koniec_uderzenia": 1.0}
    materialy = materialy_zdjec(2)

    wynik = render.plan_ujec(wzor, uderzenia_utworu, materialy, fps=10)

    assert wynik["start_audio_s"] >= 0


def test_plan_ujec_wzor_bez_uderzen_uzywa_ciecia_s():
    wzor = {"ciecia_uderzenia": [], "ciecia_s": [0.0, 1.0, 2.0], "zrodlo": {"czas_s": 3.0}}
    materialy = materialy_zdjec(2)

    wynik = render.plan_ujec(wzor, [], materialy, fps=10)

    assert wynik["start_audio_s"] == 0
    assert wynik["liczba_klatek"] == 30
    assert [(u["klatka_od"], u["liczba_klatek"]) for u in wynik["ujecia"]] == [(0, 10), (10, 10), (20, 10)]


def test_plan_ujec_material_rundy_modulo():
    wzor = {"ciecia_uderzenia": [], "ciecia_s": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0], "zrodlo": {"czas_s": 7.0}}
    materialy = materialy_zdjec(3)

    wynik = render.plan_ujec(wzor, [], materialy, fps=1)

    assert [u["material"] for u in wynik["ujecia"]] == [
        "zdjecie_0.jpg", "zdjecie_1.jpg", "zdjecie_2.jpg", "zdjecie_0.jpg", "zdjecie_1.jpg", "zdjecie_2.jpg", "zdjecie_0.jpg",
    ]


def test_wstawki_potem_plan_ujec_kawalek_krotszy_od_ujecia_gra_dalej():
    material = [{"plik": "a.mp4", "typ": "klip", "message_id": 1, "czas_s": 2.0}]
    kawalki = render.wstawki(material, dlugosc_wstawki_s=0.6)

    assert [(k["od_s"], k["czas_s"]) for k in kawalki] == [(0.0, 0.6), (0.6, 0.6), (1.2, 0.8)]

    wzor = {"ciecia_uderzenia": [], "ciecia_s": [0.0, 0.6, 1.2, 1.8, 2.4], "zrodlo": {"czas_s": 3.0}}
    wynik = render.plan_ujec(wzor, [], kawalki, fps=10)

    assert [u["start_w_klipie_s"] for u in wynik["ujecia"]] == [0.0, 0.6, 1.2, 0.0, 0.6]


def test_plan_ujec_dwa_ciecia_w_tej_samej_klatce_ujecie_wypada():
    wzor = {"ciecia_uderzenia": [], "ciecia_s": [0.0, 0.03, 1.0], "zrodlo": {"czas_s": 2.0}}
    materialy = materialy_zdjec(2)

    wynik = render.plan_ujec(wzor, [], materialy, fps=10)

    assert [(u["klatka_od"], u["liczba_klatek"]) for u in wynik["ujecia"]] == [(0, 10), (10, 10)]


def test_plan_ujec_okno_bez_dlugosci_daje_value_error():
    uderzenia_utworu = [round(0.2 + i * 0.5, 6) for i in range(20)]
    wzor = {"ciecia_uderzenia": [5.0], "koniec_uderzenia": 5.0}
    materialy = materialy_zdjec(1)

    with pytest.raises(ValueError):
        render.plan_ujec(wzor, uderzenia_utworu, materialy, fps=30)


def test_wstawki_dzieli_klip_na_kawalki_stalej_dlugosci_z_ogonem():
    material = [{"plik": "a.mp4", "typ": "klip", "message_id": 1, "czas_s": 5.0}]
    kawalki = render.wstawki(material, dlugosc_wstawki_s=1.0)
    assert [(k["od_s"], k["czas_s"]) for k in kawalki] == [(0.0, 1.0), (1.0, 1.0), (2.0, 1.0), (3.0, 1.0), (4.0, 1.0)]

    material = [{"plik": "b.mp4", "typ": "klip", "message_id": 2, "czas_s": 2.2}]
    kawalki = render.wstawki(material, dlugosc_wstawki_s=1.0)
    assert [(k["od_s"], k["czas_s"]) for k in kawalki] == [(0.0, 1.0), (1.0, 1.2)]

    material = [{"plik": "c.mp4", "typ": "klip", "message_id": 3, "czas_s": 0.6}]
    kawalki = render.wstawki(material, dlugosc_wstawki_s=1.0)
    assert [(k["od_s"], k["czas_s"]) for k in kawalki] == [(0.0, 0.6)]

    zdjecie = [{"plik": "z.jpg", "typ": "zdjecie", "message_id": 4}]
    assert render.wstawki(zdjecie, dlugosc_wstawki_s=1.0) == zdjecie


def test_wstawki_kolejnosc_rundami_po_materialach():
    materialy = [
        {"plik": "a.mp4", "typ": "klip", "message_id": 1, "czas_s": 3.0},
        {"plik": "z.jpg", "typ": "zdjecie", "message_id": 2},
        {"plik": "b.mp4", "typ": "klip", "message_id": 3, "czas_s": 2.0},
    ]
    kawalki = render.wstawki(materialy, dlugosc_wstawki_s=1.0)
    identyfikatory = [(k["plik"], k["od_s"]) if k["typ"] == "klip" else (k["plik"], None) for k in kawalki]
    assert identyfikatory == [
        ("a.mp4", 0.0), ("z.jpg", None), ("b.mp4", 0.0),
        ("a.mp4", 1.0), ("b.mp4", 1.0),
        ("a.mp4", 2.0),
    ]


def test_plan_ujec_start_w_klipie_niezalezny_od_dlugosci_ujecia():
    materialy = [{"plik": "a.mp4", "typ": "klip", "message_id": 1, "od_s": 3.0}]
    wzor = {"ciecia_uderzenia": [], "ciecia_s": [0.0], "zrodlo": {"czas_s": 5.0}}

    wynik = render.plan_ujec(wzor, [], materialy, fps=10)

    assert wynik["ujecia"][0]["start_w_klipie_s"] == 3.0


def dekoduj_klatki(sciezka, tmp_path, nazwa):
    dane = uruchom_ffprobe(sciezka)
    strumien = strumien_wideo(dane)
    szerokosc, wysokosc = int(strumien["width"]), int(strumien["height"])
    surowy = tmp_path / nazwa
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(sciezka), "-pix_fmt", "rgb24", "-f", "rawvideo", str(surowy)],
        stdin=subprocess.DEVNULL, check=True,
    )
    dane_surowe = np.fromfile(surowy, dtype=np.uint8)
    liczba_klatek = dane_surowe.size // (szerokosc * wysokosc * 3)
    return dane_surowe.reshape(liczba_klatek, wysokosc, szerokosc, 3)


def test_segment_klipu_z_obrotem_90_ma_czerwien_na_gorze(tmp_path):
    klip = tmp_path / "klip.mp4"
    generuj.klip_testowy(klip, czas_s=1.0, rozmiar=(270, 480), obrot=90)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_klipu(klip, wyjscie, start_s=0.0, liczba_klatek=20, fps=30, szerokosc=270, wysokosc=480)
    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    assert klatki.shape == (20, 480, 270, 3)
    assert gora_czerwona(klatki[0])


def test_segment_zdjecia_z_exif_6_ma_czerwien_na_gorze(tmp_path):
    zdjecie = tmp_path / "zdjecie.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(1600, 900), orientacja_exif=6)
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(przygotowana, wyjscie, numer_ujecia=0, liczba_klatek=15, fps=30, szerokosc=270, wysokosc=480)
    klatki = dekoduj_klatki(wyjscie, tmp_path, "dek.raw")
    assert klatki.shape == (15, 480, 270, 3)
    assert gora_czerwona(klatki[0])


def test_segment_zdjecia_z_przezroczystoscia_sie_renderuje(tmp_path):
    zdjecie = tmp_path / "zdjecie.png"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(1200, 1600), alfa=True)
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(przygotowana, wyjscie, numer_ujecia=1, liczba_klatek=10, fps=30, szerokosc=270, wysokosc=480)
    dane = uruchom_ffprobe(wyjscie)
    strumien = strumien_wideo(dane)
    assert int(strumien["width"]) == 270 and int(strumien["height"]) == 480


def test_segment_klipu_krotszego_niz_ujecie_daje_dokladna_liczbe_klatek(tmp_path):
    klip = tmp_path / "krotki.mp4"
    generuj.klip_testowy(klip, czas_s=0.4, rozmiar=(270, 480), fps=30)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_klipu(klip, wyjscie, start_s=0.0, liczba_klatek=30, fps=30, szerokosc=270, wysokosc=480)
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(wyjscie)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    assert int(wynik.stdout.decode().strip()) == 30


def test_segment_zdjecia_poziomego_daje_docelowy_rozmiar_i_sar(tmp_path):
    zdjecie = tmp_path / "poziome.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(1600, 900))
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(przygotowana, wyjscie, numer_ujecia=0, liczba_klatek=10, fps=30, szerokosc=270, wysokosc=480)
    dane = uruchom_ffprobe(wyjscie)
    strumien = strumien_wideo(dane)
    assert int(strumien["width"]) == 270 and int(strumien["height"]) == 480
    assert strumien["sample_aspect_ratio"] == "1:1"


def test_przygotuj_materialy_uszkodzony_trafia_do_pominietych(tmp_path):
    uszkodzony = tmp_path / "zly.mp4"
    uszkodzony.write_bytes(b"to nie jest wideo" * 50)
    dobry = tmp_path / "dobry.mp4"
    generuj.klip_testowy(dobry, czas_s=0.5, rozmiar=(270, 480))
    materialy = [
        {"plik": uszkodzony, "typ": "klip", "message_id": 1},
        {"plik": dobry, "typ": "klip", "message_id": 2},
    ]
    praca = tmp_path / "praca"
    praca.mkdir()

    dobre, pominiete = render.przygotuj_materialy(materialy, praca, 270, 480)

    assert len(dobre) == 1
    assert dobre[0]["plik"] == dobry
    assert pominiete == [{"plik": "zly.mp4", "powod": "brak strumienia wideo"}]


def test_segment_klipu_gra_dalej_poza_dlugoscia_kawalka_i_zamraza_dopiero_na_koncu_pliku(tmp_path):
    klip = tmp_path / "wieloujeciowy.mp4"
    generuj.wideo_z_cieciami(klip, ciecia_s=[1, 2, 3, 4], czas_s=5.0, fps=30, rozmiar=(270, 480))

    def kolor_srodka(klatka):
        return klatka.reshape(-1, 3).mean(axis=0)

    def zblizony(kolor, oczekiwany, tolerancja=6):
        return all(abs(float(kolor[i]) - oczekiwany[i]) <= tolerancja for i in range(3))

    wyjscie_a = tmp_path / "a.mp4"
    render.segment_klipu(klip, wyjscie_a, start_s=3.0, liczba_klatek=45, fps=30, szerokosc=270, wysokosc=480)
    klatki_a = dekoduj_klatki(wyjscie_a, tmp_path, "a.raw")
    assert klatki_a.shape[0] == 45
    assert zblizony(kolor_srodka(klatki_a[0]), generuj.kolor_ujecia(3))
    assert zblizony(kolor_srodka(klatki_a[-1]), generuj.kolor_ujecia(4))

    wyjscie_b = tmp_path / "b.mp4"
    render.segment_klipu(klip, wyjscie_b, start_s=4.5, liczba_klatek=30, fps=30, szerokosc=270, wysokosc=480)
    klatki_b = dekoduj_klatki(wyjscie_b, tmp_path, "b.raw")
    assert klatki_b.shape[0] == 30
    assert zblizony(kolor_srodka(klatki_b[-1]), generuj.kolor_ujecia(4))


def wzor_syntetyczny_8_ciec():
    return {
        "ciecia_uderzenia": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        "koniec_uderzenia": 8.0,
        "ciecia_s": [0.0],
        "zrodlo": {"czas_s": 8.0},
    }


def zbuduj_projekt(tmp_path, dodaj_materialy):
    projekt = tmp_path / "projekt"
    katalog_materialow = projekt / "materialy"
    katalog_materialow.mkdir(parents=True)
    dodaj_materialy(katalog_materialow)
    return projekt


def test_renderuj_pelny_przebieg(tmp_path):
    def dodaj(katalog):
        generuj.zdjecie_testowe(katalog / "0000000001_a.jpg", rozmiar=(800, 600))
        generuj.zdjecie_testowe(katalog / "0000000002_b.jpg", rozmiar=(600, 800))
        generuj.zdjecie_testowe(katalog / "0000000003_c.jpg", rozmiar=(600, 800))
        generuj.klip_testowy(katalog / "0000000004_d.mp4", czas_s=3.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_syntetyczny_8_ciec()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=10.0, pierwsze_uderzenie_s=0.3)

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=30, limit_mb=50)

    dane = uruchom_ffprobe(wyjscie)
    strumien = strumien_wideo(dane)
    assert strumien["pix_fmt"] == "yuv420p"
    assert strumien["sample_aspect_ratio"] == "1:1"
    assert any(s["codec_type"] == "audio" for s in dane["streams"])
    wynik_formatu = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wyjscie)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    rzeczywisty_czas_s = float(wynik_formatu.stdout.decode().strip())
    assert abs(rzeczywisty_czas_s - podsumowanie["czas_s"]) <= 1.0 / 30 + 0.02
    assert wyjscie.with_suffix(".json").exists()
    assert not (projekt / "praca").exists()


def test_renderuj_ciecia_na_swoim_miejscu(tmp_path):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_syntetyczny_8_ciec()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=10.0, pierwsze_uderzenie_s=0.3)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    _, uderzenia = analyze.analizuj_rytm(utwor)
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    plan = render.plan_ujec(wzor_syntetyczny_8_ciec(), uderzenia, material_zastepczy, fps)
    oczekiwane_granice = [u["klatka_od"] for u in plan["ujecia"][1:]]

    wykryte_s = analyze.wykryj_ciecia(wyjscie)
    wykryte_klatki = [round(t * fps) for t in wykryte_s]

    for oczekiwana in oczekiwane_granice:
        assert any(abs(oczekiwana - wykryta) <= 1 for wykryta in wykryte_klatki)


def test_renderuj_limit_rozmiaru_dla_szumu(tmp_path):
    def dodaj(katalog):
        generuj.szum(katalog / "0000000001_n.mp4", czas_s=10.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_syntetyczny_8_ciec()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=10.0, pierwsze_uderzenie_s=0.3)

    wyjscie = tmp_path / "wynik.mp4"
    render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=30, limit_mb=2)

    assert wyjscie.stat().st_size <= 2 * 1024 * 1024


def test_renderuj_dziala_bez_zrodla_wzoru(tmp_path):
    def dodaj(katalog):
        generuj.zdjecie_testowe(katalog / "0000000001_a.jpg", rozmiar=(800, 600))
        generuj.klip_testowy(katalog / "0000000002_b.mp4", czas_s=3.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor = wzor_syntetyczny_8_ciec()
    del wzor["zrodlo"]
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=10.0, pierwsze_uderzenie_s=0.3)

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=30, limit_mb=50)

    assert wyjscie.exists()
    assert podsumowanie["materialy_uzyte"] == 2


def uruchom_cli(argumenty):
    return subprocess.run(
        [sys.executable, str(Path(render.__file__))] + argumenty,
        stdin=subprocess.DEVNULL, capture_output=True,
    )


def test_cli_sukces_i_blad(tmp_path):
    def dodaj(katalog):
        generuj.zdjecie_testowe(katalog / "0000000001_a.jpg", rozmiar=(800, 600))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_syntetyczny_8_ciec()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=10.0, pierwsze_uderzenie_s=0.3)
    wyjscie = tmp_path / "wynik.mp4"

    wynik = uruchom_cli([
        "--wzor", str(wzor_json), "--projekt", str(projekt), "--utwor", str(utwor), "--wyjscie", str(wyjscie),
        "--szerokosc", "270", "--wysokosc", "480", "--fps", "30",
    ])
    assert wynik.returncode == 0
    assert wyjscie.exists()
    assert wyjscie.with_suffix(".json").exists()

    wynik_bledu = uruchom_cli([
        "--wzor", str(tmp_path / "brak.json"), "--projekt", str(projekt), "--utwor", str(utwor), "--wyjscie", str(tmp_path / "brak_wyniku.mp4"),
    ])
    assert wynik_bledu.returncode != 0
    assert len(wynik_bledu.stderr.decode("utf-8", errors="replace").strip().splitlines()) == 1
