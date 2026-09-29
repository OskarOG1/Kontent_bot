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


def zmontuj_ze_stubami(tmp_path, monkeypatch, ujecia, wycinki, numery=None, wzor=None, gwiazdy=False, bez_dynamiki=False):
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
        plan, wzor or {}, wycinki, numery, {}, czasy, tmp_path / "montaz", 270, 480, 30, 0.0, bez_dynamiki, [], [],
        None, 50, None, None, 2.5, None, None, None, None, tmp_path / "wynik.mp4",
        gwiazdy_w_haku=gwiazdy,
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


def mapa_z_szumem_na_bokach():
    mapa = np.zeros((160, 90), dtype=np.float32)
    mapa[:, :25] = 80.0
    mapa[:, 65:] = 80.0
    return mapa


def warstwa_rgba(sciezka, szerokosc, wysokosc):
    wynik = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(sciezka), "-pix_fmt", "rgba", "-f", "rawvideo", "-"],
        stdin=subprocess.DEVNULL, capture_output=True, check=True,
    )
    return np.frombuffer(wynik.stdout, dtype=np.uint8).reshape(-1, wysokosc, szerokosc, 4)


def ramka_alfa(klatka, prog=128):
    wiersze, kolumny = np.where(klatka[:, :, 3] >= prog)
    if len(wiersze) == 0:
        return None
    return kolumny.min(), wiersze.min(), kolumny.max() + 1, wiersze.max() + 1


def wycinek_koloru(katalog, nazwa, kolor):
    sciezka = katalog / nazwa
    generuj.zdjecie_kwadrat_na_przezroczystym(sciezka, kolor=kolor, udzial_kwadratu=0.8)
    return {"plik": str(sciezka)}


def test_wejscia_elementow_kolazu_leza_na_polowkach_uderzen_i_nie_w_ostatnich_klatkach():
    assert render.polowki_uderzen([4, 12, 20]) == [4, 8, 12, 16, 20]
    assert render.czasy_wejsc_kolazu([4, 12, 20], 40, 30) == [4, 8, 12, 16, 20]
    assert render.czasy_wejsc_kolazu([4, 12, 19], 20, 30) == [4, 8, 12]
    assert render.czasy_wejsc_kolazu([0, 6, 12], 60, 30) == [3, 6, 9, 12]
    assert render.czasy_wejsc_kolazu(list(range(4, 90, 6)), 90, 30) == [4, 7, 10, 13, 16]
    assert len(render.czasy_wejsc_kolazu(list(range(2, 200, 2)), 200, 30, 9)) == render.LICZBA_ELEMENTOW_KOLAZU


def test_kolaz_wprowadza_elementy_na_polowkach_i_nie_wiecej_niz_piec(tmp_path):
    wycinki = [wycinek_koloru(tmp_path, f"w{i}.png", (220, 30 * i, 30)) for i in range(7)]
    kolaz = tmp_path / "kolaz.mov"

    miejsca = render.przygotuj_kolaz(wycinki, [4, 12, 20], 40, 30, 270, 480, kolaz, mapa=np.zeros((160, 90), dtype=np.float32))
    klatki = warstwa_rgba(kolaz, 270, 480)

    assert len(miejsca) == 5 and len(klatki) == 40
    assert klatki[3, :, :, 3].max() == 0
    assert klatki[4, :, :, 3].max() > 0
    assert klatki[39, :, :, 3].max() > 0

    miejsca = render.przygotuj_kolaz(wycinki, [4, 12, 19], 20, 30, 270, 480, tmp_path / "krotki.mov", mapa=np.zeros((160, 90), dtype=np.float32))
    assert len(miejsca) == 3

    miejsca = render.przygotuj_kolaz(wycinki, list(range(4, 90, 6)), 90, 30, 270, 480, tmp_path / "gesty.mov", mapa=np.zeros((160, 90), dtype=np.float32))
    assert len(miejsca) == render.LICZBA_ELEMENTOW_KOLAZU


def test_wjazd_zaczyna_przesuniety_i_wiekszy_a_w_czwartej_klatce_stoi_na_miejscu():
    element = Image.new("RGBA", (60, 60), (220, 30, 30, 255))
    srodek = (200.0, 240.0)

    pierwsza = ramka_alfa(np.asarray(render.platno_wjazdu(element, srodek, 0, 270, 480)), prog=20)
    trzecia = ramka_alfa(np.asarray(render.platno_wjazdu(element, srodek, 2, 270, 480)), prog=20)
    czwarta = ramka_alfa(np.asarray(render.platno_wjazdu(element, srodek, 3, 270, 480)))

    assert czwarta == (170, 210, 230, 270)
    assert render.kierunek_do_krawedzi(srodek, 270, 480) == (1.0, 0.0)
    assert (pierwsza[2] - pierwsza[0]) > 1.15 * 60
    assert (pierwsza[0] + pierwsza[2]) / 2 - 200 > 0.2 * 60
    assert (trzecia[2] - trzecia[0]) < (pierwsza[2] - pierwsza[0])
    assert 0 < (trzecia[0] + trzecia[2]) / 2 - 200 < (pierwsza[0] + pierwsza[2]) / 2 - 200


def test_wjazd_w_kolazu_zaczyna_w_klatce_wejscia_i_stoi_na_miejscu(tmp_path):
    wycinek = wycinek_koloru(tmp_path, "w.png", (220, 30, 30))
    kolaz = tmp_path / "kolaz.mov"

    miejsca = render.przygotuj_kolaz([wycinek], [4], 30, 30, 270, 480, kolaz, mapa=mapa_z_szumem_po_lewej(), wejscie="wjazd")
    klatki = warstwa_rgba(kolaz, 270, 480)

    assert len(miejsca) == 1
    assert ramka_alfa(klatki[3], prog=1) is None
    assert ramka_alfa(klatki[4], prog=1) is not None
    assert ramka_alfa(klatki[7]) == ramka_alfa(klatki[25])


def test_powiekszenie_jednego_elementu_z_dwukrotnej_skali_i_rozmycia_do_ostrej_jedynki(tmp_path):
    wysoki = tmp_path / "wysoki.png"
    Image.new("RGBA", (30, 180), (30, 30, 220, 255)).save(wysoki)
    wycinek = {"plik": str(wysoki)}
    kolaz = tmp_path / "kolaz.mov"

    miejsca = render.przygotuj_kolaz(
        [wycinek, wycinek_koloru(tmp_path, "w2.png", (30, 220, 30))], [3], 30, 30, 270, 480, kolaz,
        mapa=mapa_z_szumem_na_bokach(), wejscie="powiekszenie",
    )
    klatki = warstwa_rgba(kolaz, 270, 480)

    assert len(miejsca) == 1
    poczatek = 3
    docelowa = ramka_alfa(klatki[poczatek + 14])
    pierwsza = ramka_alfa(klatki[poczatek], prog=20)
    assert docelowa[3] == 480 and abs((docelowa[3] - docelowa[1]) - 0.90 * 480) < 3
    assert (pierwsza[2] - pierwsza[0]) > 1.6 * (docelowa[2] - docelowa[0])

    def czesc_czesciowa(klatka):
        alfa = klatka[:, :, 3]
        return ((alfa > 0) & (alfa < 255)).sum() / max(1, (alfa > 0).sum())

    assert czesc_czesciowa(klatki[poczatek]) > 5 * czesc_czesciowa(klatki[poczatek + 14]) + 0.05
    assert klatki[poczatek + 14, :, :, 3].max() == 255


def test_kafel_to_prostokat_ze_zwyklego_zdjecia_w_jego_kolorze(tmp_path):
    zdjecie = tmp_path / "zdjecie.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(600, 400), kolor=(0, 200, 0))
    kolaz = tmp_path / "kolaz.mov"

    miejsca = render.przygotuj_kolaz(
        [{"plik": str(zdjecie), "kafel": True}], [3], 20, 30, 270, 480, kolaz, mapa=mapa_z_szumem_po_lewej(),
    )
    klatki = warstwa_rgba(kolaz, 270, 480)

    x, y = miejsca[0]
    szerokosc_kafla, wysokosc_kafla = round(0.45 * 270), round(0.28 * 480)
    srodek_x = min(269, max(0, round(x * 270) + szerokosc_kafla // 2))
    srodek_y = min(479, max(0, round(y * 480) + wysokosc_kafla // 2))
    piksel = klatki[15, srodek_y, srodek_x].astype(int)
    assert piksel[3] == 255 and piksel[1] > 150 and piksel[0] < 80
    ramka = ramka_alfa(klatki[15])
    assert abs((ramka[2] - ramka[0]) - min(szerokosc_kafla, 270 - max(0, round(x * 270)))) <= 3 or ramka[0] == 0 or ramka[2] == 270


def plan_z_ujeciami(dlugosci, kolejne=None):
    kolejne = kolejne or {}
    ujecia = []
    klatka = 0
    for i, dlugosc in enumerate(dlugosci):
        ujecia.append({"klatka_od": klatka, "liczba_klatek": dlugosc, "typ": "klip", "material": f"m{i}", **kolejne.get(i, {})})
        klatka += dlugosc
    return {"fps": 30, "liczba_klatek": klatka, "ujecia": ujecia}


def plamy_zlote(klatka):
    return (klatka[:, :, 0] > 200) & (klatka[:, :, 1] > 150) & (klatka[:, :, 2] < 60) & (klatka[:, :, 3] > 200)


def kat_pierscienia(klatka):
    wiersze, kolumny = np.where(klatka[:, :, 3] > 0)
    kat = np.arctan2(wiersze - klatka.shape[0] / 2, kolumny - klatka.shape[1] / 2)
    return np.degrees(np.angle(np.exp(1j * 12 * kat).sum())) / 12


def pozycje_gwiazd(t_s, szerokosc=270, wysokosc=480):
    promien = szerokosc * (0.40 - 0.34 * np.exp(-t_s / 1.5))
    obrot = np.radians(140 * t_s)
    wynik = []
    for k in range(12):
        kat = -np.pi / 2 + 2 * np.pi * k / 12 + obrot
        wynik.append((round(szerokosc / 2 + promien * np.cos(kat)), round(wysokosc / 2 + promien * np.sin(kat))))
    return promien, wynik


def test_klatka_gwiazd_po_sekundzie_ma_dwanascie_zlotych_plam_na_okregu_o_srodku_kadru(tmp_path):
    warstwa = tmp_path / "gwiazdy.mov"
    render.materializuj_warstwe(lambda k: render.obraz_gwiazd(k, 30, 270, 480), 40, 30, 270, 480, warstwa)
    klatka = warstwa_rgba(warstwa, 270, 480)[30]

    promien, pozycje = pozycje_gwiazd(1.0)
    zlote = plamy_zlote(klatka)
    wiersze, kolumny = np.where(klatka[:, :, 3] > 0)
    odleglosci = np.hypot(kolumny - 135, wiersze - 240)
    assert zlote.sum() > 0.8 * (klatka[:, :, 3] > 0).sum()
    assert abs(odleglosci.mean() - promien) < 0.05 * promien
    assert odleglosci.max() < 1.15 * promien and odleglosci.min() > 0.85 * promien

    zajete = np.zeros((480, 270), dtype=bool)
    for x, y in pozycje:
        assert zlote[y - 1:y + 2, x - 1:x + 2].any()
        zajete[max(0, y - 8):y + 9, max(0, x - 8):x + 9] = True
    assert ((klatka[:, :, 3] > 0) & ~zajete).sum() == 0


def test_gwiazdy_pojawiaja_sie_po_kolei_i_okrag_obraca_sie_o_140_stopni_na_sekunde(tmp_path):
    warstwa = tmp_path / "gwiazdy.mov"
    render.materializuj_warstwe(lambda k: render.obraz_gwiazd(k, 30, 270, 480), 45, 30, 270, 480, warstwa)
    klatki = warstwa_rgba(warstwa, 270, 480)

    ilosc = [int((klatka[:, :, 3] > 0).sum()) for klatka in klatki]
    assert ilosc[0] > 0 and ilosc[3] > ilosc[0] and ilosc[11] > ilosc[5]

    for k in (20, 30, 40):
        roznica = (kat_pierscienia(klatki[k + 1]) - kat_pierscienia(klatki[k]) + 15) % 30 - 15
        assert abs(roznica - 140 / 30) < 1.0


def test_okno_gwiazd_automatu_zaczyna_na_drugim_ujeciu_trwa_4_6_s_i_konczy_przed_dropem_i_kolazem():
    plan = plan_z_ujeciami([60, 200, 60, 60])
    assert render.okno_gwiazd(plan, None, [], [], 30) == (60, 60 + round(4.6 * 30))
    assert render.okno_gwiazd(plan, None, [], [2], 30) == (60, 198)
    assert render.okno_gwiazd(plan_z_ujeciami([60, 100, 100, 60]), None, [], [2], 30) == (60, 160)

    plan = plan_z_ujeciami([60, 200, 60, 60])
    assert render.okno_gwiazd(plan, 200, [30, 90, 150, 170, 200], [], 30) == (60, 170)

    assert render.okno_gwiazd(plan_z_ujeciami([60, 100]), 130, [30, 80, 130], [], 30) is None
    assert render.okno_gwiazd(plan_z_ujeciami([60]), None, [], [], 30) is None


def test_okno_gwiazd_ze_scenariusza_obejmuje_kolejne_ujecia_z_gwiazdami():
    efekt = {"uderzenie": False, "blysk_s": 0.0, "wstrzas": False, "przejscie": "brak"}
    plan = plan_z_ujeciami(
        [40, 40, 40, 40, 40],
        {i: {"efekt_scenariusza": efekt, "gwiazdy": i in (1, 2, 4)} for i in range(5)},
    )
    assert render.okno_gwiazd(plan, None, [], [], 30) == (40, 120)
    assert render.okno_gwiazd(plan, None, [], [1], 30) == (80, 120)

    bez =plan_z_ujeciami([40, 40, 40], {i: {"efekt_scenariusza": efekt, "gwiazdy": False} for i in range(3)})
    assert render.okno_gwiazd(bez, None, [], [], 30) is None

    krotkie = plan_z_ujeciami([10, 10, 10], {i: {"efekt_scenariusza": efekt, "gwiazdy": i == 1} for i in range(3)})
    assert render.okno_gwiazd(krotkie, None, [], [], 30) is None


def ujecia_do_gwiazd():
    return [
        {"material": "a", "typ": "klip", "klatka_od": 0, "liczba_klatek": 60, "start_w_klipie_s": 0.0, "numer_wzoru": 0},
        {"material": "b", "typ": "klip", "klatka_od": 60, "liczba_klatek": 120, "start_w_klipie_s": 0.0, "numer_wzoru": 0},
    ]


def test_gwiazdy_wylaczone_flaga_konfiguracja_i_bez_dynamiki_daja_brak_warstwy(tmp_path, monkeypatch):
    wynik, _ = zmontuj_ze_stubami(tmp_path / "a", monkeypatch, ujecia_do_gwiazd(), [], gwiazdy=True)
    assert wynik["gwiazdy"] == {"od_s": 2.0, "do_s": 6.0}
    assert (tmp_path / "a" / "montaz" / "gwiazdy.mov").exists()

    wynik, _ = zmontuj_ze_stubami(tmp_path / "b", monkeypatch, ujecia_do_gwiazd(), [], gwiazdy=False)
    assert wynik["gwiazdy"] is None
    assert not (tmp_path / "b" / "montaz" / "gwiazdy.mov").exists()

    wynik, _ = zmontuj_ze_stubami(tmp_path / "c", monkeypatch, ujecia_do_gwiazd(), [], gwiazdy=True, bez_dynamiki=True)
    assert wynik["gwiazdy"] is None
    assert not (tmp_path / "c" / "montaz" / "gwiazdy.mov").exists()


def test_flaga_bez_gwiazd_wylacza_gwiazdy_w_renderze(tmp_path, monkeypatch):
    przekazane = []
    monkeypatch.setattr(render, "renderuj", lambda *args, **kwargs: przekazane.append(kwargs))
    baza = ["--wzor", "w.json", "--projekt", str(tmp_path), "--wyjscie", str(tmp_path / "w.mp4")]

    assert render.glowna(baza) == 0
    assert render.glowna(baza + ["--bez-gwiazd"]) == 0
    assert [k["gwiazdy_w_haku"] for k in przekazane] == [True, False]


def test_przebieg_koncowy_dostaje_gwiazdy_jako_klip_bez_petli_i_nad_napisami(tmp_path, monkeypatch):
    polecenia = []
    monkeypatch.setattr(render, "uruchom_ffmpeg", lambda argumenty, katalog=None: polecenia.append(argumenty))
    warstwa = tmp_path / "gwiazdy.mov"
    render.materializuj_warstwe(lambda k: render.obraz_gwiazd(k, 30, 270, 480), 45, 30, 270, 480, warstwa)
    napis = tmp_path / "napis.webm"
    napis.write_bytes(b"")

    render.przebieg_koncowy(
        tmp_path / "polaczone.mp4", tmp_path / "utwor.wav", 0.0, 150, 30, tmp_path / "wynik.mp4", 50,
        szerokosc=270, wysokosc=480,
        teksty=[{"plik": napis, "od_s": 0.5, "do_s": 3.0}],
        gwiazdy={"plik": warstwa, "od_s": 1.0, "do_s": 2.5},
    )

    polecenie = polecenia[-1]
    indeks = polecenie.index(str(warstwa))
    assert polecenie[indeks - 1] == "-i"
    assert "-t" not in polecenie[indeks - 3:indeks]
    assert "-loop" not in polecenie and "-stream_loop" not in polecenie
    filtr = polecenie[polecenie.index("-filter_complex") + 1]
    assert filtr.index("[gwiazdy]overlay") < filtr.index("[tekst0]overlay")
