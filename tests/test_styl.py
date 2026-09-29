import json
import subprocess

import numpy as np

import generuj
import render
import rezyser


def klip_lavfi(sciezka, zrodlo, czas_s=2.0):
    subprocess.run(
        [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", zrodlo, "-t", str(czas_s),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(sciezka),
        ],
        stdin=subprocess.DEVNULL, check=True,
    )
    return sciezka


def klip_z_pasami(sciezka, gora=35, dol=35, kolor_pasa="black", tresc="testsrc2", czas_s=2.0):
    wysokosc_tresci = 270 - gora - dol
    laczenie = ":" if "=" in tresc else "="
    zrodlo = (
        f"{tresc}{laczenie}size=480x{wysokosc_tresci}:rate=30,"
        f"pad=w=480:h=270:x=0:y={gora}:color={kolor_pasa}"
    )
    return klip_lavfi(sciezka, zrodlo, czas_s)


def klatki_wideo(sciezka, szerokosc, wysokosc):
    wynik = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(sciezka), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=True,
    )
    return np.frombuffer(wynik.stdout, dtype=np.uint8).reshape(-1, wysokosc, szerokosc, 3)


def test_wykryj_kadr_para_pasow_u_gory_i_u_dolu(tmp_path):
    klip = klip_z_pasami(tmp_path / "pasy.mp4")

    kadr = render.wykryj_kadr(klip, 2.0)

    assert kadr is not None
    assert kadr["x"] == 0.0 and kadr["w"] == 1.0
    assert 35 / 270 <= kadr["y"] <= 35 / 270 + 0.02
    assert 200 / 270 - 0.04 <= kadr["h"] <= 200 / 270


def test_wykryj_kadr_pasy_boczne(tmp_path):
    klip = klip_lavfi(tmp_path / "boczne.mp4", "testsrc2=size=360x270:rate=30,pad=w=480:h=270:x=60:y=0:color=black")

    kadr = render.wykryj_kadr(klip, 2.0)

    assert kadr is not None
    assert kadr["y"] == 0.0 and kadr["h"] == 1.0
    assert 60 / 480 <= kadr["x"] <= 60 / 480 + 0.02
    assert 360 / 480 - 0.04 <= kadr["w"] <= 360 / 480


def test_wykryj_kadr_jednostronna_ciemnosc_to_nie_pasy(tmp_path):
    klip = klip_z_pasami(tmp_path / "gora.mp4", gora=70, dol=0)

    assert render.wykryj_kadr(klip, 2.0) is None


def test_wykryj_kadr_ciemnobordowy_brzeg_to_nie_pasy(tmp_path):
    klip = klip_z_pasami(tmp_path / "bordo.mp4", kolor_pasa="0x390E10")

    assert render.wykryj_kadr(klip, 2.0) is None


def test_wykryj_kadr_czarny_i_zwykly_klip_bez_przyciecia(tmp_path):
    czarny = tmp_path / "czarny.mp4"
    generuj.klip_testowy(czarny, czas_s=1.0, kolor=(0, 0, 0))
    zwykly = tmp_path / "zwykly.mp4"
    generuj.klip_testowy(zwykly, czas_s=1.0)

    assert render.wykryj_kadr(czarny, 1.0) is None
    assert render.wykryj_kadr(zwykly, 1.0) is None


def test_filtr_kadru_pusty_bez_kadru():
    assert render.filtr_kadru(None) == ""
    filtr = render.filtr_kadru({"x": 0.0, "y": 0.1, "w": 1.0, "h": 0.8})
    assert filtr.startswith("crop=") and filtr.endswith(",")


def test_segment_klipu_z_kadrem_bez_ciemnych_brzegow(tmp_path):
    klip = klip_z_pasami(tmp_path / "pasy.mp4", tresc="color=c=0x5080B0")
    kadr = render.wykryj_kadr(klip, 2.0)
    z_kadrem = tmp_path / "z_kadrem.mp4"
    bez_kadru = tmp_path / "bez_kadru.mp4"

    render.segment_klipu(klip, z_kadrem, start_s=0.0, liczba_klatek=10, fps=30, szerokosc=270, wysokosc=480, kadr=kadr)
    render.segment_klipu(klip, bez_kadru, start_s=0.0, liczba_klatek=10, fps=30, szerokosc=270, wysokosc=480)

    klatki_z = klatki_wideo(z_kadrem, 270, 480)
    klatki_bez = klatki_wideo(bez_kadru, 270, 480)
    assert len(klatki_z) == 10
    assert klatki_z[:, :4].max(axis=3).mean() > 100
    assert klatki_z[:, -4:].max(axis=3).mean() > 100
    assert klatki_bez[:, :4].max(axis=3).mean() < 30
    assert klatki_bez[:, -4:].max(axis=3).mean() < 30


def test_statystyki_klipu_z_kadrem_jak_sama_tresc(tmp_path):
    klip = klip_z_pasami(tmp_path / "pasy.mp4", tresc="color=c=0x5080B0")
    tresc = klip_lavfi(tmp_path / "tresc.mp4", "color=c=0x5080B0:size=480x270:rate=30")
    kadr = render.wykryj_kadr(klip, 2.0)

    z_kadrem = render.statystyki_klipu(klip, 0.0, 1.0, 2.0, kadr=kadr)
    bez_kadru = render.statystyki_klipu(klip, 0.0, 1.0, 2.0)
    sama_tresc = render.statystyki_klipu(tresc, 0.0, 1.0, 2.0)

    assert np.allclose(z_kadrem["lab_srednia"], sama_tresc["lab_srednia"], atol=1.0)
    assert bez_kadru["lab_srednia"][0] < sama_tresc["lab_srednia"][0] - 5


def test_arkusz_rezysera_pokazuje_klip_bez_pasow(tmp_path):
    klip = klip_z_pasami(tmp_path / "pasy.mp4", tresc="color=c=0x5080B0")
    kadr = render.wykryj_kadr(klip, 2.0)
    kx, ky = rezyser.KOMORKA_KLATKI_KLIPU

    z_kadrem = rezyser.klatki_klipu(klip, rezyser.LICZBA_KLATEK_KLIPU, 2.0, kx, ky, przyciecie=render.filtr_kadru(kadr))
    bez_kadru = rezyser.klatki_klipu(klip, rezyser.LICZBA_KLATEK_KLIPU, 2.0, kx, ky)

    assert len(z_kadrem) == rezyser.LICZBA_KLATEK_KLIPU
    assert min(k[:3].max(axis=2).mean() for k in z_kadrem) > 100
    assert max(k[:3].max(axis=2).mean() for k in bez_kadru) < 30


def test_arkusze_materialow_biora_kadr_z_materialu(tmp_path, monkeypatch):
    klip = klip_z_pasami(tmp_path / "pasy.mp4", tresc="color=c=0x5080B0")
    kadr = render.wykryj_kadr(klip, 2.0)
    wywolania = []
    oryginal = rezyser.klatki_klipu

    def podgladaj(*argumenty, **nazwane):
        wywolania.append(nazwane.get("przyciecie", ""))
        return oryginal(*argumenty, **nazwane)

    monkeypatch.setattr(rezyser, "klatki_klipu", podgladaj)
    rezyser.arkusze_materialow([{"plik": str(klip), "typ": "klip", "czas_s": 2.0, "kadr": kadr}], [], tmp_path / "arkusze")

    assert wywolania == [render.filtr_kadru(kadr)]


def test_renderuj_klip_z_pasami_na_liscie_pasow(tmp_path):
    projekt = tmp_path / "projekt"
    katalog = projekt / "materialy"
    katalog.mkdir(parents=True)
    for i in range(3):
        generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
    klip_z_pasami(katalog / "0000000003_d.mp4", tresc="color=c=0x5080B0", czas_s=3.0)
    generuj.klip_testowy(katalog / "0000000004_d.mp4", czas_s=3.0, rozmiar=(270, 480))
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps({
        "ciecia_uderzenia": [],
        "koniec_uderzenia": None,
        "ciecia_s": [0.0, 3.0],
        "zrodlo": {"czas_s": 3.5},
    }), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=5.0, pierwsze_uderzenie_s=0.1)

    podsumowanie = render.renderuj(wzor_json, projekt, utwor, tmp_path / "wynik.mp4", szerokosc=270, wysokosc=480, fps=30, limit_mb=50)

    assert [wpis["plik"] for wpis in podsumowanie["pasy"]] == ["0000000003_d.mp4"]
    assert podsumowanie["pasy"][0]["kadr"]["h"] < 0.8
