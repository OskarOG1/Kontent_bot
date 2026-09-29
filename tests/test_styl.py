import json
import subprocess

import numpy as np
from PIL import Image

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


def zdjecie_w_paski(sciezka, rozmiar=(540, 960), pas=24):
    obraz = np.zeros((rozmiar[1], rozmiar[0], 3), dtype=np.uint8)
    for indeks, gora in enumerate(range(0, rozmiar[1], pas)):
        obraz[gora:gora + pas] = (230, 200, 40) if indeks % 2 == 0 else (30, 60, 200)
    Image.fromarray(obraz).save(sciezka)
    return sciezka


def segment_zdjecia_testowy(tmp_path, nazwa, przejscie, liczba_klatek=14, zdjecie=None):
    zrodlo = zdjecie or zdjecie_w_paski(tmp_path / f"{nazwa}.png")
    praca = tmp_path / f"praca_{nazwa}"
    praca.mkdir()
    przygotowane = render.przygotuj_zdjecie(zrodlo, praca, 0, 270, 480)
    wyjscie = tmp_path / f"{nazwa}.mp4"
    render.segment_zdjecia(
        przygotowane, wyjscie, numer_ujecia=0, liczba_klatek=liczba_klatek, fps=30, szerokosc=270, wysokosc=480,
        przejscie=przejscie,
    )
    return klatki_wideo(wyjscie, 270, 480)


def zmiennosc_pionowa(klatka, od, do):
    return float(np.abs(np.diff(klatka[od:do].astype(np.int32), axis=0)).sum())


def test_smuga_slabnie_przez_siedem_klatek(tmp_path):
    klatki = segment_zdjecia_testowy(tmp_path, "smuga", "smuga")
    bez = segment_zdjecia_testowy(tmp_path, "bez", "brak")

    ostrosc = [zmiennosc_pionowa(k, 100, 380) for k in klatki]
    assert len(klatki) == 14
    assert ostrosc[1] < ostrosc[3] < ostrosc[5] < ostrosc[8]
    assert abs(ostrosc[8] - zmiennosc_pionowa(bez[8], 100, 380)) < 0.05 * ostrosc[8]


def test_rozciagniecie_daje_pionowe_smugi_pod_linia_i_znika(tmp_path):
    klatki = segment_zdjecia_testowy(tmp_path, "rozciagniecie", "rozciagniecie")

    linia = round(480 * render.LINIA_ROZCIAGNIECIA)
    assert len(klatki) == 14
    assert zmiennosc_pionowa(klatki[0], linia + 20, 470) < 0.1 * zmiennosc_pionowa(klatki[12], linia + 20, 470)
    assert zmiennosc_pionowa(klatki[0], 10, linia - 20) > 0.5 * zmiennosc_pionowa(klatki[12], 10, linia - 20)
    assert zmiennosc_pionowa(klatki[5], linia + 20, 470) > zmiennosc_pionowa(klatki[0], linia + 20, 470)


def test_najazd_na_zdjeciu_i_klipie_rozmywa_pierwsze_klatki(tmp_path):
    klatki_zdjecia = segment_zdjecia_testowy(tmp_path, "najazd", "najazd")
    klip = klip_lavfi(tmp_path / "paski.mp4", "testsrc2=size=480x270:rate=30")
    wyjscie = tmp_path / "najazd_klip.mp4"
    render.segment_klipu(klip, wyjscie, start_s=0.0, liczba_klatek=12, fps=30, szerokosc=270, wysokosc=480, przejscie="najazd")
    klatki_klipu = klatki_wideo(wyjscie, 270, 480)

    assert zmiennosc_pionowa(klatki_zdjecia[0], 100, 380) < 0.5 * zmiennosc_pionowa(klatki_zdjecia[10], 100, 380)
    assert zmiennosc_pionowa(klatki_klipu[0], 0, 480) < 0.5 * zmiennosc_pionowa(klatki_klipu[10], 0, 480)


def test_rozciagniecie_na_klipie_z_kolazem(tmp_path):
    klip = klip_lavfi(tmp_path / "klip.mp4", "testsrc2=size=480x270:rate=30")
    wycinek = tmp_path / "wycinek.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek)
    kolaz = tmp_path / "kolaz.mov"
    render.przygotuj_kolaz([{"plik": str(wycinek)}], [3], 12, 30, 270, 480, kolaz)
    wyjscie = tmp_path / "segment.mp4"

    render.segment_klipu(
        klip, wyjscie, start_s=0.0, liczba_klatek=12, fps=30, szerokosc=270, wysokosc=480,
        przejscie="rozciagniecie", blysk_s=0.1, kolaz=kolaz,
    )

    assert len(klatki_wideo(wyjscie, 270, 480)) == 12


def test_efekt_ujecia_drugie_ujecie_najazd_i_zmiana_smugi_z_rozciagnieciem():
    drugie = render.efekt_ujecia({"typ": "zdjecie", "klatka_od": 10}, 1, None, 0)
    drugie_na_dropie = render.efekt_ujecia({"typ": "klip", "klatka_od": 10}, 1, 10, 0)
    po_dropie = [render.efekt_ujecia({"typ": "zdjecie", "klatka_od": 60}, 7, 10, licznik)["przejscie"] for licznik in range(1, 13)]

    assert drugie["przejscie"] == "najazd"
    assert drugie_na_dropie["przejscie"] == "brak" and drugie_na_dropie["wstrzas"] is True
    assert po_dropie == [
        "brak", "brak", "smuga", "brak", "brak", "rozciagniecie",
        "brak", "brak", "smuga", "brak", "brak", "rozciagniecie",
    ]


def mapa_z_szumem_po_lewej():
    mapa = np.zeros((160, 90), dtype=np.float32)
    mapa[:, :45] = np.random.default_rng(1).uniform(50, 100, (160, 45))
    return mapa


def test_ruch_tla_zero_dla_takich_samych_klatek_i_duzy_dla_szumu():
    klatka = np.full((160, 90), 120.0, dtype=np.float32)
    szum = np.random.default_rng(0).uniform(0, 255, (4, 160, 90)).astype(np.float32)

    assert render.ruch_tla(np.stack([klatka] * 4)) == 0.0
    assert render.ruch_tla(szum) > render.PROG_RUCHU_KOLAZU


def test_miejsca_kolazu_wybieraja_gladka_strone_i_strone_z_polecenia():
    mapa = mapa_z_szumem_po_lewej()
    rozmiary = [(0.4, 0.5)] * 3

    miejsca = render.miejsca_kolazu(mapa, rozmiary)

    assert len(set(miejsca)) == 3
    for x, y in miejsca:
        assert x + 0.2 > 0.5
        assert x >= -0.08 * 0.4 - 1e-9 and x + 0.4 <= 1 + 0.08 * 0.4 + 1e-9
        assert y >= -0.08 * 0.5 - 1e-9 and y + 0.5 <= 1 + 0.08 * 0.5 + 1e-9

    u_gory = render.miejsca_kolazu(mapa, rozmiary, strona="gora")
    assert len(u_gory) == 3
    for _, y in u_gory:
        assert y < 0.05


def test_mapa_zajetosci_ma_wymiary_kadru_i_wyzsze_wartosci_na_szumie():
    klatki = np.stack([mapa_z_szumem_po_lewej()] * 4)

    mapa = render.mapa_zajetosci(klatki)

    assert mapa.shape == (160, 90)
    assert mapa[:, :35].mean() > 5 * mapa[:, 55:].mean() + 1


def zmontuj_ze_stubami(tmp_path, monkeypatch, ujecia, wycinki, numery=None, wzor=None):
    monkeypatch.setattr(render, "sklej_segmenty", lambda *args, **kwargs: None)
    monkeypatch.setattr(render, "przebieg_koncowy", lambda *args, **kwargs: None)
    monkeypatch.setattr(render, "zweryfikuj_wynik", lambda *args, **kwargs: None)
    segmenty = {}

    def zapisz(zrodlo, wyjscie, *args, **kwargs):
        segmenty[int(wyjscie.stem.split("_")[-1])] = kwargs.get("kolaz")

    monkeypatch.setattr(render, "segment_klipu", zapisz)
    monkeypatch.setattr(render, "segment_zdjecia", zapisz)
    liczba_klatek = sum(u["liczba_klatek"] for u in ujecia)
    plan = {"fps": 30, "start_audio_s": 0.0, "liczba_klatek": liczba_klatek, "ujecia": ujecia}
    czasy = {u["material"]: 3.0 for u in ujecia if u["typ"] == "klip"}
    wynik = render.zmontuj(
        plan, wzor or {}, wycinki, numery, {}, czasy, tmp_path / "montaz", 270, 480, 30, 0.0, False, [], [],
        None, 50, None, None, 2.5, None, None, None, None, tmp_path / "wynik.mp4",
    )
    return wynik, segmenty


def ujecie_klipu(material, od, dlugosc=60, **kwargs):
    return {
        "material": str(material), "typ": "klip", "klatka_od": od, "liczba_klatek": dlugosc,
        "start_w_klipie_s": 0.0, "numer_wzoru": 0, **kwargs,
    }


def klipy_tla(tmp_path):
    spokojny = tmp_path / "spokojny.mp4"
    generuj.klip_testowy(spokojny, czas_s=3.0, rozmiar=(270, 480), kolor=(0, 200, 0))
    ruchomy = tmp_path / "ruchomy.mp4"
    generuj.szum(ruchomy, 3.0, (270, 480))
    wycinek = tmp_path / "wycinek.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek)
    return spokojny, ruchomy, wycinek


def test_kolaz_ze_scenariusza_odpada_na_tle_w_ruchu_i_zostaje_na_spokojnym(tmp_path, monkeypatch):
    spokojny, ruchomy, wycinek = klipy_tla(tmp_path)
    efekt = {"uderzenie": False, "blysk_s": 0.0, "wstrzas": False, "przejscie": "brak"}
    ujecia = [
        ujecie_klipu(ruchomy, 0, efekt_scenariusza=efekt, kolaz_scenariusza=[7]),
        ujecie_klipu(spokojny, 60, efekt_scenariusza=efekt, kolaz_scenariusza=[7]),
    ]

    wynik, segmenty = zmontuj_ze_stubami(
        tmp_path, monkeypatch, ujecia, [{"plik": str(wycinek), "message_id": 7}], {7: {"plik": str(wycinek), "message_id": 7}},
    )

    assert segmenty[0] is None and segmenty[1] is not None
    assert [w["ujecie"] for w in wynik["podsumowanie_kolazy"]] == [1]
    assert wynik["podsumowanie_kolazy"][0]["ruch"] <= render.PROG_RUCHU_KOLAZU
    assert len(wynik["podsumowanie_kolazy"][0]["miejsca"]) == 1
    assert [w["ujecie"] for w in wynik["kolaze_pominiete"]] == [0]
    assert wynik["kolaze_pominiete"][0]["ruch"] > render.PROG_RUCHU_KOLAZU
    assert len(wynik["ostrzezenia_kolazy"]) == 1
    assert wynik["ostrzezenia_kolazy"][0].startswith("ujęcie 0: tło w ruchu (")
    assert wynik["ostrzezenia_kolazy"][0].endswith("), kolaż pominięty")


def test_kolaz_automatu_tylko_na_spokojnym_tle_najwyzej_trzy_i_co_trzy_sekundy(tmp_path, monkeypatch):
    spokojny, ruchomy, wycinek = klipy_tla(tmp_path)
    ujecia = [ujecie_klipu(ruchomy if i == 1 else spokojny, i * 60) for i in range(6)]

    wynik, segmenty = zmontuj_ze_stubami(tmp_path, monkeypatch, ujecia, [{"plik": str(wycinek), "message_id": 7}])

    wybrane = [w["ujecie"] for w in wynik["podsumowanie_kolazy"]]
    assert wybrane == [0, 2, 4]
    assert segmenty[1] is None
    starty = [ujecia[i]["klatka_od"] / 30 for i in wybrane]
    assert all(b - a >= render.ODSTEP_KOLAZY_AUTOMATU_S for a, b in zip(starty, starty[1:]))
    assert wynik["kolaze_pominiete"] == []


def test_kolaz_automatu_nie_stoi_na_dropie(tmp_path, monkeypatch):
    spokojny, _, wycinek = klipy_tla(tmp_path)
    ujecia = [ujecie_klipu(spokojny, 0), ujecie_klipu(spokojny, 60)]
    monkeypatch.setattr(render, "koniec_haka", lambda plan, sekcje: 0)

    wynik, _ = zmontuj_ze_stubami(
        tmp_path, monkeypatch, ujecia, [{"plik": str(wycinek), "message_id": 7}], wzor={"sekcje": {"drop_ujecie": 1}},
    )

    assert [w["ujecie"] for w in wynik["podsumowanie_kolazy"]] == [1]


def test_kolaz_na_zdjeciu_widac_w_wybranym_miejscu(tmp_path):
    zdjecie = tmp_path / "tlo.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(270, 480), kolor=(0, 200, 0))
    wycinek = tmp_path / "wycinek.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek)
    kolaz = tmp_path / "kolaz.mov"

    miejsca = render.przygotuj_kolaz(
        [{"plik": str(wycinek)}], [3], 15, 30, 270, 480, kolaz, mapa=mapa_z_szumem_po_lewej(),
    )
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(zdjecie, wyjscie, 0, 15, 30, 270, 480, kolaz=kolaz)
    klatki = klatki_wideo(wyjscie, 270, 480)

    assert len(klatki) == 15
    x, y = miejsca[0]
    bok = 0.6 * 270
    srodek_x = min(269, max(0, round((x * 270) + bok / 2)))
    srodek_y = min(479, max(0, round((y * 480) + bok / 2)))
    assert srodek_x > 135
    piksel = klatki[12, srodek_y, srodek_x].astype(int)
    assert piksel[0] - piksel[1] > 100
    przed = klatki[1, srodek_y, srodek_x].astype(int)
    assert przed[1] - przed[0] > 100


def test_segmenty_bez_kolazu_maja_te_same_polecenia_ffmpeg(tmp_path, monkeypatch):
    zdjecie = tmp_path / "tlo.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(270, 480), kolor=(0, 200, 0))
    klip = klip_lavfi(tmp_path / "klip.mp4", "testsrc2=size=480x270:rate=30")
    polecenia = []
    monkeypatch.setattr(render, "uruchom_ffmpeg", lambda argumenty, katalog=None: polecenia.append(argumenty))

    render.segment_zdjecia(zdjecie, tmp_path / "a.mp4", 0, 12, 30, 270, 480)
    render.segment_klipu(klip, tmp_path / "b.mp4", 0.0, 12, 30, 270, 480)

    for polecenie in polecenia:
        assert polecenie.count("-i") == 1
        assert "-filter_complex" not in polecenie
        assert "-vf" in polecenie
