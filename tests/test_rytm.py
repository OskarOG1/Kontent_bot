import json

import numpy as np
import pytest

import generuj
import render
import tekst
from test_render import dekoduj_klatki, zbuduj_projekt


def test_uderzenia_wyniku_konwertuje_i_filtruje():
    assert render.uderzenia_wyniku([10.0, 10.5, 11.0, 11.5], 10.0, 60, 30) == [0, 15, 30, 45]


def test_uderzenia_wyniku_bez_rytmu_daje_siatke():
    assert render.uderzenia_wyniku([], 10.0, 60, 30) == [0, 15, 30, 45]


def test_okna_slow_przyklad_z_planu():
    uderzenia = list(range(0, 400, 15))
    okna = tekst.okna_slow(5, uderzenia, 150)
    assert okna == [(90, 105), (105, 120), (120, 135), (135, 150), (150, 180)]


def test_okna_slow_krok_2_przy_gestych_uderzeniach():
    uderzenia = list(range(0, 400, 8))
    okna = tekst.okna_slow(4, uderzenia, 150)
    dlugosci_slow = [koniec - poczatek for poczatek, koniec in okna[:-1]]
    assert dlugosci_slow == [16, 16, 16]


def test_okna_slow_za_duzo_slow_rzuca_blad_z_maksimum():
    uderzenia = list(range(0, 200, 15))
    with pytest.raises(ValueError, match="4"):
        tekst.okna_slow(12, uderzenia, 45)


def kolor_zloty_maska(tablica):
    return (tablica[..., 0] > 200) & (tablica[..., 1] > 160) & (tablica[..., 2] < 140)


def kolor_granatowy_maska(tablica):
    return (tablica[..., 0] < 60) & (tablica[..., 1] < 60) & (tablica[..., 2] > 50) & (tablica[..., 2] < 130)


def test_obraz_slowa_kolory_i_znaki():
    obraz = tekst.obraz_slowa("żółć", 270, 480)
    tablica = np.array(obraz)
    alfa = tablica[..., 3]
    assert alfa.max() > 0

    znaki = tekst.znaki_czcionki(tekst.wybierz_czcionke(tekst.PRESETY["rytm"])[0])
    assert all(ord(znak) in znaki for znak in "żółć")

    widoczne = alfa > 0
    assert kolor_zloty_maska(tablica)[widoczne].any()
    assert kolor_granatowy_maska(tablica)[widoczne].any()


def zapisz_projekt_slowa(projekt, slowa, linie=None):
    dane = {"teksty": [{"message_id": i + 1, "tekst": linia} for i, linia in enumerate(linie or [])], "slowa": slowa}
    (projekt / "projekt.json").write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def wzor_prosty(czas_s=4.0):
    return {"ciecia_s": [0.0, 1.0, 2.0, 3.0], "zrodlo": {"czas_s": czas_s}}


def zlota_maska_klatki(klatka):
    tablica = klatka.astype(np.int32)
    return (tablica[..., 0] > 200) & (tablica[..., 1] > 150) & (tablica[..., 2] < 150)


def test_renderuj_slowa_w_rytmie_pelny_przebieg(tmp_path):
    def dodaj(katalog):
        for i in range(3):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(20, 20, 20))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    zapisz_projekt_slowa(projekt, "raz dwa GO")
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_prosty(6.0)), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=6.0, pierwsze_uderzenie_s=0.0)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert podsumowanie["slowa"]["liczba"] == 3
    okna = podsumowanie["slowa"]["okna"]
    assert len(okna) == 3

    klatki = dekoduj_klatki(wyjscie, tmp_path, "slowa.raw")

    for poczatek, koniec in okna:
        srodek = (poczatek + koniec) // 2
        if srodek < len(klatki):
            assert zlota_maska_klatki(klatki[srodek]).any()

    pierwszy_poczatek = okna[0][0]
    if pierwszy_poczatek > 0:
        assert not zlota_maska_klatki(klatki[pierwszy_poczatek - 1]).any()

    start_akcentu = okna[-1][0]
    def szerokosc_zlota(klatka):
        maska = zlota_maska_klatki(klatka)
        kolumny = np.where(maska.any(axis=0))[0]
        return int(kolumny.max() - kolumny.min()) if kolumny.size else 0

    if start_akcentu + 6 < len(klatki):
        szerokosc_pierwsza = szerokosc_zlota(klatki[start_akcentu])
        szerokosc_siodma = szerokosc_zlota(klatki[start_akcentu + 6])
        assert szerokosc_pierwsza >= szerokosc_siodma

    assert abs((len(klatki)) - podsumowanie["czas_s"] * fps) <= 1


def test_renderuj_bez_slow_nie_zmienia_przebiegu_koncowego(tmp_path, monkeypatch):
    def dodaj(katalog):
        generuj.zdjecie_testowe(katalog / "0000000001_a.jpg", rozmiar=(800, 600))
        generuj.zdjecie_testowe(katalog / "0000000002_b.jpg", rozmiar=(800, 600))

    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_prosty()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)
    fps = 30

    oryginalny = render.uruchom_ffmpeg

    def przechwyc(lista):
        def podmieniony(argumenty, katalog=None):
            lista.append(argumenty)
            return oryginalny(argumenty, katalog=katalog)
        return podmieniony

    projekt_bez = zbuduj_projekt(tmp_path / "bez", dodaj)
    zapisz_projekt_slowa(projekt_bez, None)
    polecenia_bez = []
    monkeypatch.setattr(render, "uruchom_ffmpeg", przechwyc(polecenia_bez))
    render.renderuj(wzor_json, projekt_bez, utwor, tmp_path / "bez.mp4", szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    projekt_pusty = zbuduj_projekt(tmp_path / "pusty", dodaj)
    polecenia_pusty = []
    monkeypatch.setattr(render, "uruchom_ffmpeg", przechwyc(polecenia_pusty))
    render.renderuj(wzor_json, projekt_pusty, utwor, tmp_path / "pusty.mp4", szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    def znormalizuj(polecenie, projekt, wyjscie):
        wynik = [arg.replace(str(projekt), "PROJEKT") for arg in polecenie]
        return [arg.replace(str(wyjscie), "WYJSCIE") for arg in wynik]

    ostatnie_bez = znormalizuj(polecenia_bez[-1], projekt_bez, tmp_path / "bez.mp4")
    ostatnie_pusty = znormalizuj(polecenia_pusty[-1], projekt_pusty, tmp_path / "pusty.mp4")
    assert ostatnie_bez == ostatnie_pusty


def test_renderuj_slowa_i_linie_razem_linia_konczy_sie_na_pierwszym_slowie(tmp_path):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(20, 20, 20))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    zapisz_projekt_slowa(projekt, "raz dwa GO", linie=["Linia napisu"])
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_prosty(6.0)), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=6.0, pierwsze_uderzenie_s=0.0)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert podsumowanie["teksty"]["okna"][-1][1] == podsumowanie["slowa"]["okna"][0][0]
