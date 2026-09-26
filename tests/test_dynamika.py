import json
import subprocess
import sys
from pathlib import Path

import analyze
import generuj
import render


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
