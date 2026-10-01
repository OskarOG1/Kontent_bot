import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

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


def obraz_z_markerem(sciezka, rozmiar=(1200, 1600)):
    obraz = Image.new("RGB", rozmiar, (10, 10, 10))
    bok = min(rozmiar) // 10
    lewo = rozmiar[0] // 4 - bok // 2
    gora = rozmiar[1] // 4 - bok // 2
    obraz.paste(Image.new("RGB", (bok, bok), (255, 0, 0)), (lewo, gora))
    obraz.save(sciezka)


def centroid_czerwieni(klatka):
    czerwone = (klatka[..., 0].astype(int) > 180) & (klatka[..., 1].astype(int) < 80) & (klatka[..., 2].astype(int) < 80)
    ys, xs = np.nonzero(czerwone)
    return float(xs.mean()), float(ys.mean())


def odleglosc_od_srodka(punkt, rozmiar):
    cx, cy = rozmiar[0] / 2, rozmiar[1] / 2
    return ((punkt[0] - cx) ** 2 + (punkt[1] - cy) ** 2) ** 0.5


def ostrosc_pionowa(klatka, pas=20):
    wysokosc = klatka.shape[0]
    srodek = wysokosc // 2
    wycinek = klatka[max(0, srodek - pas):srodek + pas].astype(np.int32)
    roznice = np.abs(np.diff(wycinek, axis=0))
    return float(roznice.sum())


def kawalki_zdjec(n):
    return [{"plik": f"z{i}.jpg", "typ": "zdjecie", "message_id": i, "od_s": 0.0} for i in range(n)]


def kawalki_klipow(n):
    return [{"plik": f"k{i}.mp4", "typ": "klip", "message_id": i, "od_s": 0.0} for i in range(n)]


def plan_dwa_segmenty(liczba_klatek, plansza_klatka_od, fps=30):
    return {
        "fps": fps,
        "start_audio_s": 0.0,
        "liczba_klatek": liczba_klatek,
        "ujecia": [
            {"material": "wzor0", "typ": "zdjecie", "klatka_od": 0, "liczba_klatek": plansza_klatka_od, "start_w_klipie_s": 0.0, "numer_wzoru": 0},
            {"material": "wzor1", "typ": "zdjecie", "klatka_od": plansza_klatka_od, "liczba_klatek": liczba_klatek - plansza_klatka_od, "start_w_klipie_s": 0.0, "numer_wzoru": 1},
        ],
    }


def test_rozloz_tempo_zdjecia_co_uderzenie():
    fps = 30
    liczba_klatek = 300
    plansza_klatka_od = 290
    plan = plan_dwa_segmenty(liczba_klatek, plansza_klatka_od, fps)
    uderzenia = list(range(0, liczba_klatek, 15))
    kawalki = kawalki_zdjec(5)

    wynik = render.rozloz_tempo(plan, {"sekcje": None}, uderzenia, kawalki, fps)
    ujecia = wynik["ujecia"]

    plansza = ujecia[-1]
    assert plansza["klatka_od"] == plansza_klatka_od
    assert plansza["liczba_klatek"] == liczba_klatek - plansza_klatka_od

    reszta = ujecia[:-1]
    for ujecie in reszta[:-1]:
        assert ujecie["liczba_klatek"] == 15
    assert reszta[-1]["liczba_klatek"] > 15


def test_rozloz_tempo_klipy_dlugosc_w_oknie():
    fps = 30
    liczba_klatek = 400
    plansza_klatka_od = 385
    plan = plan_dwa_segmenty(liczba_klatek, plansza_klatka_od, fps)
    for ujecie in plan["ujecia"]:
        ujecie["typ"] = "zdjecie"
    kawalki = kawalki_klipow(5)

    wynik = render.rozloz_tempo(plan, {"sekcje": None}, [], kawalki, fps)
    ujecia = wynik["ujecia"]

    for ujecie in ujecia[:-2]:
        assert 60 <= ujecie["liczba_klatek"] <= 96
    assert ujecia[-1]["klatka_od"] == plansza_klatka_od


def test_rozloz_tempo_ujecie_zaczyna_sie_na_klatce_dropu():
    fps = 30
    liczba_klatek = 300
    plan = {
        "fps": fps,
        "start_audio_s": 0.0,
        "liczba_klatek": liczba_klatek,
        "ujecia": [
            {"material": "wzor0", "typ": "zdjecie", "klatka_od": 0, "liczba_klatek": 150, "start_w_klipie_s": 0.0, "numer_wzoru": 0},
            {"material": "wzor1", "typ": "zdjecie", "klatka_od": 150, "liczba_klatek": 140, "start_w_klipie_s": 0.0, "numer_wzoru": 1},
            {"material": "wzor2", "typ": "zdjecie", "klatka_od": 290, "liczba_klatek": 10, "start_w_klipie_s": 0.0, "numer_wzoru": 2},
        ],
    }
    wzor = {"sekcje": {"drop_s": None, "drop_ujecie": 1, "koniec_haka_uderzenia": None}}
    uderzenia = list(range(0, liczba_klatek, 13))
    kawalki = kawalki_zdjec(5)

    wynik = render.rozloz_tempo(plan, wzor, uderzenia, kawalki, fps)
    ujecia = wynik["ujecia"]

    klatka_dropu = render.koniec_haka(plan, wzor["sekcje"])
    assert klatka_dropu == 150
    poczatki = [u["klatka_od"] for u in ujecia]
    assert klatka_dropu in poczatki
    for ujecie in ujecia:
        assert not (ujecie["klatka_od"] < klatka_dropu < ujecie["klatka_od"] + ujecie["liczba_klatek"])


def test_rozloz_tempo_ostatnie_ujecie_jedno_i_na_poczatku_planszy():
    fps = 30
    liczba_klatek = 300
    plansza_klatka_od = 290
    plan = plan_dwa_segmenty(liczba_klatek, plansza_klatka_od, fps)
    uderzenia = list(range(0, liczba_klatek, 15))
    kawalki = kawalki_zdjec(5)

    wynik = render.rozloz_tempo(plan, {"sekcje": None}, uderzenia, kawalki, fps)
    ujecia = wynik["ujecia"]

    ostatnie = [u for u in ujecia if u["klatka_od"] >= plansza_klatka_od]
    assert len(ostatnie) == 1
    assert ostatnie[0]["klatka_od"] == plansza_klatka_od


def test_rozloz_tempo_suma_dlugosci_i_numer_wzoru_niemalejace():
    fps = 30
    liczba_klatek = 300
    plansza_klatka_od = 290
    plan = plan_dwa_segmenty(liczba_klatek, plansza_klatka_od, fps)
    uderzenia = list(range(0, liczba_klatek, 15))
    kawalki = kawalki_zdjec(5)

    wynik = render.rozloz_tempo(plan, {"sekcje": None}, uderzenia, kawalki, fps)
    ujecia = wynik["ujecia"]

    assert sum(u["liczba_klatek"] for u in ujecia) == liczba_klatek
    numery = [u["numer_wzoru"] for u in ujecia]
    assert numery == sorted(numery)
    for ujecie in ujecia:
        oczekiwany = 0 if ujecie["klatka_od"] < plansza_klatka_od else 1
        assert ujecie["numer_wzoru"] == oczekiwany


def test_rozdziel_wycinki_zdjecie_z_przezroczystoscia_idzie_do_wycinkow(tmp_path):
    zwykle_zdjecie = tmp_path / "zwykle.jpg"
    generuj.zdjecie_testowe(zwykle_zdjecie, rozmiar=(120, 160))
    wycinek_zdjecie = tmp_path / "wycinek.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek_zdjecie)
    klip = tmp_path / "klip.mp4"

    materialy = [
        {"plik": zwykle_zdjecie, "typ": "zdjecie", "message_id": 1},
        {"plik": wycinek_zdjecie, "typ": "zdjecie", "message_id": 2},
        {"plik": klip, "typ": "klip", "message_id": 3},
    ]

    zwykle, wycinki = render.rozdziel_wycinki(materialy)

    assert [m["message_id"] for m in zwykle] == [1, 3]
    assert [m["message_id"] for m in wycinki] == [2]


def test_rozdziel_wycinki_gdy_same_wycinki_wszystkie_do_kolejki(tmp_path):
    wycinek_a = tmp_path / "a.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek_a)
    wycinek_b = tmp_path / "b.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek_b)

    materialy = [
        {"plik": wycinek_a, "typ": "zdjecie", "message_id": 1},
        {"plik": wycinek_b, "typ": "zdjecie", "message_id": 2},
    ]

    zwykle, wycinki = render.rozdziel_wycinki(materialy)

    assert [m["message_id"] for m in zwykle] == [1, 2]
    assert wycinki == []


def kawalki_mieszane(zdjecia, klipy):
    return [{"plik": nazwa, "typ": "zdjecie", "message_id": nazwa} for nazwa in zdjecia] + \
        [{"plik": nazwa, "typ": "klip", "message_id": nazwa} for nazwa in klipy]


def test_przeplot_trzy_zdjecia_miedzy_kazdymi_dwoma_kawalkami_klipow():
    hak = {"plik": "z0", "typ": "zdjecie", "message_id": "z0"}
    zdjecia = [{"plik": f"z{i}", "typ": "zdjecie", "message_id": f"z{i}"} for i in range(1, 8)]
    klip0 = [{"plik": "k0", "typ": "klip", "message_id": "k0"} for _ in range(3)]
    klip1 = [{"plik": "k1", "typ": "klip", "message_id": "k1"} for _ in range(3)]
    kawalki = [hak] + zdjecia + [klip0[0], klip1[0], klip0[1], klip1[1], klip0[2], klip1[2]]

    wynik = render.przeplot(kawalki)

    assert wynik[0] is hak
    indeksy_klipow = [i for i, m in enumerate(wynik) if m["typ"] == "klip"]
    assert len(indeksy_klipow) == 6
    for poprzedni, nastepny in zip(indeksy_klipow, indeksy_klipow[1:]):
        assert nastepny - poprzedni == 4
    assert indeksy_klipow[0] - 0 == 4
    for kawalek in klip0 + klip1:
        assert wynik.count(kawalek) >= 1
    for zdjecie in zdjecia:
        assert zdjecie in wynik


def test_przeplot_hak_klip_zostaje_pierwszy_jego_kawalki_ida_z_reszta():
    hak = {"plik": "k0", "typ": "klip", "message_id": "k0", "od_s": 0.0}
    kawalek_haka = {"plik": "k0", "typ": "klip", "message_id": "k0", "od_s": 1.0}
    inny_klip = {"plik": "k1", "typ": "klip", "message_id": "k1", "od_s": 0.0}
    zdjecia = [{"plik": f"z{i}", "typ": "zdjecie", "message_id": f"z{i}"} for i in range(1, 3)]
    kawalki = [hak] + zdjecia + [kawalek_haka, inny_klip]

    wynik = render.przeplot(kawalki, zdjec_miedzy_klipami=1)

    assert wynik[0] is hak
    assert sum(1 for m in wynik if m is kawalek_haka) == 1
    assert sum(1 for m in wynik if m is inny_klip) == 1
    assert [m["typ"] for m in wynik].count("klip") == 3


def test_przeplot_bez_zdjec_albo_bez_klipow_bez_zmian():
    same_zdjecia = kawalki_mieszane(["z0", "z1", "z2"], [])
    assert render.przeplot(same_zdjecia) == same_zdjecia

    same_klipy = kawalki_mieszane([], ["k0", "k1"])
    assert render.przeplot(same_klipy) == same_klipy


def test_przeplot_dwa_zdjecia_powtarzaja_sie_po_kolei():
    hak = {"plik": "z0", "typ": "zdjecie", "message_id": "z0"}
    z1 = {"plik": "z1", "typ": "zdjecie", "message_id": "z1"}
    z2 = {"plik": "z2", "typ": "zdjecie", "message_id": "z2"}
    k0 = {"plik": "k0", "typ": "klip", "message_id": "k0"}
    k1 = {"plik": "k1", "typ": "klip", "message_id": "k1"}
    k2 = {"plik": "k2", "typ": "klip", "message_id": "k2"}
    kawalki = [hak, z1, z2, k0, k1, k2]

    wynik = render.przeplot(kawalki, zdjec_miedzy_klipami=1)

    assert wynik == [hak, z1, k0, z2, k1, z1, k2]


def zbuduj_projekt(tmp_path, dodaj_materialy):
    projekt = tmp_path / "projekt"
    katalog_materialow = projekt / "materialy"
    katalog_materialow.mkdir(parents=True)
    dodaj_materialy(katalog_materialow)
    return projekt


def wzor_dynamika():
    return {
        "ciecia_uderzenia": [],
        "koniec_uderzenia": None,
        "ciecia_s": [0.0, 3.0],
        "zrodlo": {"czas_s": 3.5},
    }


def test_renderuj_pelny_z_dynamika_ma_wiecej_ujec_niz_wzor(tmp_path):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
        generuj.klip_testowy(katalog / "0000000004_d.mp4", czas_s=3.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_dynamika()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=5.0, pierwsze_uderzenie_s=0.1)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    _, uderzenia_utworu = analyze.analizuj_rytm(utwor)
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    plan_wzoru = render.plan_ujec(wzor_dynamika(), uderzenia_utworu, material_zastepczy, fps)

    assert podsumowanie["czas_s"] == round(plan_wzoru["liczba_klatek"] / fps, 3)
    assert podsumowanie["liczba_ujec"] > len(plan_wzoru["ujecia"])

    wyjscie_bez = tmp_path / "wynik_bez.mp4"
    podsumowanie_bez = render.renderuj(
        wzor_json, projekt, utwor, wyjscie_bez, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50, bez_dynamiki=True,
    )
    assert podsumowanie_bez["liczba_ujec"] == len(plan_wzoru["ujecia"])


def wzor_dynamika_z_dropem():
    return {
        "ciecia_uderzenia": [],
        "koniec_uderzenia": None,
        "ciecia_s": [0.0, 3.0, 9.0],
        "zrodlo": {"czas_s": 12.0},
        "sekcje": {"drop_s": None, "drop_ujecie": 1, "koniec_haka_uderzenia": None},
    }


def test_renderuj_przeplot_po_dropie_zdjecia_przynajmniej_polowa_i_zaden_dwa_klipy_pod_rzad(tmp_path, monkeypatch):
    def dodaj(katalog):
        for i in range(6):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
        generuj.klip_testowy(katalog / "0000000006_d.mp4", czas_s=8.0, rozmiar=(270, 480))
        generuj.klip_testowy(katalog / "0000000007_e.mp4", czas_s=8.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor = wzor_dynamika_z_dropem()
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=13.0, pierwsze_uderzenie_s=0.1)
    fps = 30

    przechwycone = {}
    oryginalny = render.rozloz_tempo

    def podmieniony(plan, wzor_arg, uderzenia, kawalki, fps_arg):
        wynik = oryginalny(plan, wzor_arg, uderzenia, kawalki, fps_arg)
        przechwycone["plan_bazowy"] = plan
        przechwycone["plan"] = wynik
        return wynik

    monkeypatch.setattr(render, "rozloz_tempo", podmieniony)

    wyjscie = tmp_path / "wynik.mp4"
    render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    plan_bazowy = przechwycone["plan_bazowy"]
    plan_koncowy = przechwycone["plan"]
    klatka_dropu = render.koniec_haka(plan_bazowy, wzor["sekcje"])
    plansza_start = plan_bazowy["ujecia"][-1]["klatka_od"]

    montaz = [u for u in plan_koncowy["ujecia"] if klatka_dropu <= u["klatka_od"] < plansza_start]
    assert montaz

    for poprzednie, nastepne in zip(montaz, montaz[1:]):
        assert not (poprzednie["typ"] == "klip" and nastepne["typ"] == "klip")

    zdjecia = sum(1 for u in montaz if u["typ"] == "zdjecie")
    assert zdjecia * 2 >= len(montaz)


def test_efekt_ujecia_uderzenie_zoom_pulsuje_i_zanika(tmp_path):
    zdjecie = tmp_path / "marker.jpg"
    obraz_z_markerem(zdjecie)
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(
        przygotowana, wyjscie, numer_ujecia=0, liczba_klatek=24, fps=30, szerokosc=270, wysokosc=480, uderzenie=True,
    )
    klatki = dekoduj_klatki(wyjscie, tmp_path, "marker.raw")

    d0 = odleglosc_od_srodka(centroid_czerwieni(klatki[0]), (270, 480))
    d8 = odleglosc_od_srodka(centroid_czerwieni(klatki[8]), (270, 480))
    d20 = odleglosc_od_srodka(centroid_czerwieni(klatki[20]), (270, 480))

    assert d0 - d8 > 5
    assert abs(d8 - d20) < (d0 - d8)


def test_efekt_blysku_na_poczatku_segmentu(tmp_path):
    klip = tmp_path / "klip.mp4"
    generuj.klip_testowy(klip, czas_s=1.0, rozmiar=(270, 480))

    z_blyskiem = tmp_path / "z_blyskiem.mp4"
    render.segment_klipu(klip, z_blyskiem, start_s=0.0, liczba_klatek=20, fps=30, szerokosc=270, wysokosc=480, blysk_s=0.10)
    bez_blysku = tmp_path / "bez_blysku.mp4"
    render.segment_klipu(klip, bez_blysku, start_s=0.0, liczba_klatek=20, fps=30, szerokosc=270, wysokosc=480)

    klatki_z = dekoduj_klatki(z_blyskiem, tmp_path, "z.raw")
    klatki_bez = dekoduj_klatki(bez_blysku, tmp_path, "bez.raw")

    assert klatki_z[0].astype(np.int32).mean() > 200
    assert abs(float(klatki_z[6].mean()) - float(klatki_bez[6].mean())) <= 5


def test_efekt_wstrzasu_przesuwa_tresc_i_zanika_po_15_klatkach(tmp_path):
    zdjecie = tmp_path / "marker.jpg"
    obraz_z_markerem(zdjecie)
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(
        przygotowana, wyjscie, numer_ujecia=0, liczba_klatek=30, fps=30, szerokosc=270, wysokosc=480, wstrzas=True,
    )
    klatki = dekoduj_klatki(wyjscie, tmp_path, "wstrzas.raw")

    p2 = centroid_czerwieni(klatki[2])
    p5 = centroid_czerwieni(klatki[5])
    p16 = centroid_czerwieni(klatki[16])
    p17 = centroid_czerwieni(klatki[17])

    przesuniecie_wczesne = ((p2[0] - p5[0]) ** 2 + (p2[1] - p5[1]) ** 2) ** 0.5
    przesuniecie_pozne = ((p16[0] - p17[0]) ** 2 + (p16[1] - p17[1]) ** 2) ** 0.5

    assert przesuniecie_wczesne > 0.5
    assert przesuniecie_pozne < 0.5


def test_efekt_smugi_rozmywa_pierwsze_klatki(tmp_path):
    zdjecie = tmp_path / "pasy.jpg"
    generuj.zdjecie_testowe(zdjecie, rozmiar=(1200, 1600))
    praca = tmp_path / "praca"
    praca.mkdir()
    przygotowana = render.przygotuj_zdjecie(zdjecie, praca, 0, 270, 480)
    wyjscie = tmp_path / "segment.mp4"
    render.segment_zdjecia(
        przygotowana, wyjscie, numer_ujecia=0, liczba_klatek=10, fps=30, szerokosc=270, wysokosc=480, przejscie="smuga",
    )
    klatki = dekoduj_klatki(wyjscie, tmp_path, "smuga.raw")

    assert ostrosc_pionowa(klatki[1]) < ostrosc_pionowa(klatki[6])


def test_efekt_najazdu_na_planszy_rozmywa_pierwsze_klatki(tmp_path):
    plansza = tmp_path / "plansza.jpg"
    generuj.zdjecie_testowe(plansza, rozmiar=(1200, 1600))
    wyjscie = tmp_path / "plansza_seg.mp4"
    render.segment_planszy(plansza, wyjscie, liczba_klatek=12, fps=30, szerokosc=270, wysokosc=480, przejscie="najazd")
    klatki = dekoduj_klatki(wyjscie, tmp_path, "najazd.raw")

    assert ostrosc_pionowa(klatki[0]) < ostrosc_pionowa(klatki[8])


def test_efekt_ujecia_na_planie_z_dropem():
    plan = plan_dwa_segmenty(300, 290, fps=30)
    plan["ujecia"][0]["numer_wzoru"] = 0
    plan["ujecia"][1]["numer_wzoru"] = 1
    klatka_dropu = 0

    ujecie_klip = {"typ": "klip", "klatka_od": 30}
    efekt_klip = render.efekt_ujecia(ujecie_klip, 1, klatka_dropu, 0)
    assert efekt_klip["blysk_s"] == 0.10
    assert efekt_klip["wstrzas"] is False

    ujecie_drop = {"typ": "zdjecie", "klatka_od": 0}
    efekt_drop = render.efekt_ujecia(ujecie_drop, 0, klatka_dropu, 0)
    assert efekt_drop["blysk_s"] == 0.30
    assert efekt_drop["wstrzas"] is True

    ujecie_zdjecie_3 = {"typ": "zdjecie", "klatka_od": 60}
    efekt_smuga = render.efekt_ujecia(ujecie_zdjecie_3, 5, klatka_dropu, 3)
    assert efekt_smuga["przejscie"] == "smuga"

    ujecie_zdjecie_2 = {"typ": "zdjecie", "klatka_od": 45}
    efekt_bez_smugi = render.efekt_ujecia(ujecie_zdjecie_2, 4, klatka_dropu, 2)
    assert efekt_bez_smugi["przejscie"] == "brak"

    efekt_planszy = render.efekt_ujecia({"typ": "zdjecie", "klatka_od": 290}, -1, klatka_dropu, 3)
    assert efekt_planszy == {"uderzenie": False, "blysk_s": 0.0, "wstrzas": False, "przejscie": "najazd"}


def test_renderuj_bez_dynamiki_polecenia_bez_nowych_filtrow(tmp_path, monkeypatch):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
        generuj.klip_testowy(katalog / "0000000004_d.mp4", czas_s=3.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_dynamika()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=5.0, pierwsze_uderzenie_s=0.1)
    fps = 30

    polecenia = []
    oryginalny = render.uruchom_ffmpeg

    def podmieniony(argumenty, katalog=None):
        polecenia.append(argumenty)
        return oryginalny(argumenty, katalog=katalog)

    monkeypatch.setattr(render, "uruchom_ffmpeg", podmieniony)

    wyjscie = tmp_path / "wynik.mp4"
    render.renderuj(
        wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50, bez_dynamiki=True,
    )

    for polecenie in polecenia:
        polecenie_tekst = " ".join(polecenie)
        assert "gblur" not in polecenie_tekst
        assert "fade=t=in" not in polecenie_tekst
        assert "sin(n" not in polecenie_tekst
        assert "on/5" not in polecenie_tekst and "on/6" not in polecenie_tekst


def zbuduj_kolaz_na_klipie(tmp_path, uderzenia_lokalne, liczba_klatek=90, fps=30, rozmiar=(270, 480)):
    szerokosc, wysokosc = rozmiar
    klip = tmp_path / "klip.mp4"
    generuj.klip_testowy(klip, czas_s=liczba_klatek / fps, rozmiar=rozmiar, kolor=(0, 255, 0))

    wycinki = []
    for i in range(3):
        sciezka = tmp_path / f"wycinek_{i}.png"
        generuj.zdjecie_kwadrat_na_przezroczystym(sciezka)
        wycinki.append({"plik": sciezka, "message_id": i})

    kolaz = tmp_path / "kolaz.mov"
    render.przygotuj_kolaz(wycinki, uderzenia_lokalne, liczba_klatek, fps, szerokosc, wysokosc, kolaz)

    wyjscie = tmp_path / "segment.mp4"
    render.segment_klipu(klip, wyjscie, start_s=0.0, liczba_klatek=liczba_klatek, fps=fps, szerokosc=szerokosc, wysokosc=wysokosc, kolaz=kolaz)
    return dekoduj_klatki(wyjscie, tmp_path, "kolaz_seg.raw")


def punkt_pola(indeks, rozmiar=(270, 480)):
    szerokosc, wysokosc = rozmiar
    udzial_x, udzial_y = render.POLA_KOLAZU[indeks]
    return round(udzial_y * wysokosc), round(udzial_x * szerokosc)


def czy_czerwony(piksel):
    piksel = piksel.astype(int)
    return piksel[0] - piksel[1] > 20


def test_kolaz_wskakuje_na_uderzeniach_i_zostaje(tmp_path):
    klatki = zbuduj_kolaz_na_klipie(tmp_path, uderzenia_lokalne=[15, 30, 45, 60, 75])

    y1, x1 = punkt_pola(0)
    assert not czy_czerwony(klatki[10, y1, x1])
    assert czy_czerwony(klatki[20, y1, x1])

    for indeks in range(3):
        y, x = punkt_pola(indeks)
        assert czy_czerwony(klatki[80, y, x])


def test_kolaz_wskok_wieksze_na_szczycie_niz_pozniej(tmp_path):
    klatki = zbuduj_kolaz_na_klipie(tmp_path, uderzenia_lokalne=[15, 30, 45, 60, 75])
    y1, x1 = punkt_pola(0)
    pas = 100

    def liczba_czerwonych(klatka):
        wycinek = klatka[max(0, y1 - pas):y1 + pas, max(0, x1 - pas):x1 + pas].astype(np.int32)
        return int(np.count_nonzero((wycinek[..., 0] - wycinek[..., 1]) > 20))

    n2 = liczba_czerwonych(klatki[17])
    n5 = liczba_czerwonych(klatki[20])
    assert n2 > n5


def test_kolaz_kwalifikuje_bez_dropu_krotkich_i_slow():
    fps = 30
    ujecie = {"klatka_od": 100, "liczba_klatek": 60}

    assert render.kolaz_kwalifikuje(ujecie, None, [], fps) is True

    ujecie_krotkie = {"klatka_od": 100, "liczba_klatek": 30}
    assert render.kolaz_kwalifikuje(ujecie_krotkie, None, [], fps) is False

    assert render.kolaz_kwalifikuje(ujecie, 100, [], fps) is False

    okna_slow = [(90, 130)]
    assert render.kolaz_kwalifikuje(ujecie, None, okna_slow, fps) is False

    okna_slow_bez_nachodzenia = [(0, 50)]
    assert render.kolaz_kwalifikuje(ujecie, None, okna_slow_bez_nachodzenia, fps) is True


def wzor_dynamika_z_klipami():
    return {
        "ciecia_uderzenia": [],
        "koniec_uderzenia": None,
        "ciecia_s": [0.0, 6.0],
        "zrodlo": {"czas_s": 6.5},
    }


def test_renderuj_bez_wycinkow_daje_puste_kolaze(tmp_path):
    def dodaj(katalog):
        for i in range(3):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
        generuj.klip_testowy(katalog / "0000000003_d.mp4", czas_s=3.0, rozmiar=(270, 480))
        generuj.klip_testowy(katalog / "0000000004_e.mp4", czas_s=3.0, rozmiar=(270, 480))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_dynamika_z_klipami()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=8.0, pierwsze_uderzenie_s=0.1)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert podsumowanie["kolaze"] == []


def test_renderuj_z_wycinkami_dodaje_kolaz_i_wycinek_nie_jest_osobnym_ujeciem(tmp_path):
    def dodaj(katalog):
        for i in range(3):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i))
        generuj.klip_testowy(katalog / "0000000003_d.mp4", czas_s=3.0, rozmiar=(270, 480))
        generuj.klip_testowy(katalog / "0000000004_e.mp4", czas_s=3.0, rozmiar=(270, 480))
        generuj.zdjecie_kwadrat_na_przezroczystym(katalog / "0000000005_w.png")

    projekt = zbuduj_projekt(tmp_path, dodaj)
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_dynamika_z_klipami()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=180, czas_s=8.0, pierwsze_uderzenie_s=0.1)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    if podsumowanie["kolaze"]:
        for wpis in podsumowanie["kolaze"]:
            assert "0000000005_w.png" in wpis["wycinki"]
    assert podsumowanie["dynamika"]["wycinki"] == 1


def wzor_28_s_z_dropem():
    krok = 27.0 / 17
    return {
        "ciecia_uderzenia": [],
        "koniec_uderzenia": None,
        "ciecia_s": [round(i * krok, 3) for i in range(17)] + [27.0],
        "zrodlo": {"czas_s": 28.0},
        "sekcje": {"drop_s": None, "drop_ujecie": 6, "koniec_haka_uderzenia": None},
    }


def test_rozloz_tempo_hak_klip_po_zawinieciu_bez_dwoch_klipow_pod_rzad():
    fps = 30
    materialy = [
        {"plik": "k0.mp4", "typ": "klip", "message_id": 0, "czas_s": 7.0},
        {"plik": "z1.jpg", "typ": "zdjecie", "message_id": 1},
        {"plik": "z2.jpg", "typ": "zdjecie", "message_id": 2},
        {"plik": "z3.jpg", "typ": "zdjecie", "message_id": 3},
        {"plik": "k1.mp4", "typ": "klip", "message_id": 4, "czas_s": 7.0},
    ]
    kawalki = render.przeplot(render.wstawki(materialy, render.DLUGOSC_WSTAWKI_S))
    wzor = wzor_28_s_z_dropem()
    plan = render.plan_ujec(wzor, [], kawalki, fps)
    uderzenia = list(range(11, plan["liczba_klatek"], 11))

    wynik = render.rozloz_tempo(plan, wzor, uderzenia, kawalki, fps)
    ujecia = wynik["ujecia"][:-1]

    assert len(ujecia) > len(kawalki)
    for poprzednie, nastepne in zip(ujecia, ujecia[1:]):
        assert not (poprzednie["typ"] == "klip" and nastepne["typ"] == "klip")
    hak = [u for u in ujecia if u["material"] == "k0.mp4" and u["start_w_klipie_s"] == 0.0]
    assert len(hak) == 1


def test_rozloz_tempo_hak_zdjecie_wraca_po_zawinieciu():
    fps = 30
    plan = plan_dwa_segmenty(300, 290, fps)
    uderzenia = list(range(0, 300, 15))

    wynik = render.rozloz_tempo(plan, {"sekcje": None}, uderzenia, kawalki_zdjec(3), fps)

    materialy = [u["material"] for u in wynik["ujecia"][:4]]
    assert materialy == ["z0.jpg", "z1.jpg", "z2.jpg", "z0.jpg"]


def test_przeplot_nieuzyte_zdjecia_na_koncu_w_kolejnosci():
    hak = {"plik": "z0", "typ": "zdjecie", "message_id": "z0"}
    zdjecia = [{"plik": f"z{i}", "typ": "zdjecie", "message_id": f"z{i}"} for i in range(1, 8)]
    klip = {"plik": "k0", "typ": "klip", "message_id": "k0", "od_s": 0.0}

    wynik = render.przeplot([hak] + zdjecia + [klip])

    assert wynik == [hak] + zdjecia[:3] + [klip] + zdjecia[3:]
