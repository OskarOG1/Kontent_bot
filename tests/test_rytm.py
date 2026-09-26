import json

import numpy as np
import pytest

import generuj
import komunikaty
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


def ramka_zlotej_alfy(obraz):
    tablica = np.array(obraz)
    maska = kolor_zloty_maska(tablica) & (tablica[..., 3] > 0)
    ys, xs = np.nonzero(maska)
    return xs, ys


def test_obraz_slowa_akcent_szeroki_i_wyzszy_niz_zwykle_slowo():
    zwykle = tekst.obraz_slowa("POLAND", 1080, 1920)
    akcent = tekst.obraz_slowa("POLAND", 1080, 1920, akcent=True, wjazd=1.0)

    xs_zwykle, ys_zwykle = ramka_zlotej_alfy(zwykle)
    xs_akcent, ys_akcent = ramka_zlotej_alfy(akcent)

    szerokosc_akcentu = xs_akcent.max() - xs_akcent.min()
    assert 0.60 * 1080 <= szerokosc_akcentu <= 0.95 * 1080

    wysokosc_zwykla = ys_zwykle.max() - ys_zwykle.min()
    wysokosc_akcentu = ys_akcent.max() - ys_akcent.min()
    assert wysokosc_akcentu >= 1.15 * wysokosc_zwykla


def test_obraz_slowa_akcent_krotkie_slowo_wieksze_o_okolo_16_razy():
    zwykle = tekst.obraz_slowa("EU", 1080, 1920)
    akcent = tekst.obraz_slowa("EU", 1080, 1920, akcent=True, wjazd=1.0)

    _, ys_zwykle = ramka_zlotej_alfy(zwykle)
    _, ys_akcent = ramka_zlotej_alfy(akcent)

    wysokosc_zwykla = ys_zwykle.max() - ys_zwykle.min()
    wysokosc_akcentu = ys_akcent.max() - ys_akcent.min()
    assert 1.45 * wysokosc_zwykla <= wysokosc_akcentu <= 1.75 * wysokosc_zwykla


def test_obraz_slowa_akcent_wjazd_wychodzi_poza_kadr():
    akcent = tekst.obraz_slowa("POLAND", 1080, 1920, akcent=True, wjazd=6.0)
    tablica = np.array(akcent)
    widoczne = (kolor_zloty_maska(tablica) | kolor_granatowy_maska(tablica)) & (tablica[..., 3] > 0)
    assert widoczne[:, 0].any()
    assert widoczne[:, -1].any()


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
    zapisz_projekt_slowa(projekt, "raz dwa POLAND")
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


def plan_syntetyczny(fps=30, liczba_klatek=300, poczatki=(0, 30, 90, 150)):
    return {"fps": fps, "liczba_klatek": liczba_klatek, "ujecia": [{"klatka_od": k} for k in poczatki]}


def test_obraz_pionowy_geometria():
    wysokosci = []
    for k in (3, 10, 20):
        obraz = tekst.obraz_pionowy("Testowy napis pionowy", k, 270, 480)
        tablica = np.array(obraz)
        ys, xs = np.nonzero(tablica[..., 3])
        assert xs.min() >= 0
        assert xs.max() <= 0.12 * 270
        assert abs(int(ys.max()) - round(0.85 * 480)) <= 1
        wysokosci.append(int(ys.max()) - int(ys.min()))
    assert wysokosci[0] < wysokosci[1] < wysokosci[2]


def test_okno_pionowe_geometria():
    plan = plan_syntetyczny()
    poczatek, koniec_pisania, koniec = tekst.okno_pionowe(plan, 10, 30, 200)
    assert poczatek == 30
    assert koniec_pisania == 30 + 2 * 10
    assert koniec == 90


def test_okno_pionowe_za_duzo_znakow_rzuca_blad_z_maksimum():
    plan = plan_syntetyczny()
    with pytest.raises(ValueError, match="0"):
        tekst.okno_pionowe(plan, 5, 30, 20)


def test_okno_pionowe_startuje_od_zera_gdy_drugie_ujecie_za_pozno():
    plan = plan_syntetyczny()
    poczatek, koniec_pisania, koniec = tekst.okno_pionowe(plan, 40, 30, 130)
    assert poczatek == 0
    assert koniec_pisania == 80
    assert koniec == 130


def test_okno_pionowe_jedno_ujecie_w_haku_startuje_od_zera():
    plan = plan_syntetyczny(poczatki=(0,))
    poczatek, koniec_pisania, koniec = tekst.okno_pionowe(plan, 5, 30, 200)
    assert poczatek == 0


def test_okno_pionowe_liczba_z_komunikatu_przechodzi_a_o_1_wiecej_rzuca():
    plan = plan_syntetyczny()
    tekst.okno_pionowe(plan, 35, 30, 100)
    with pytest.raises(ValueError, match="35"):
        tekst.okno_pionowe(plan, 36, 30, 100)


def test_okno_pionowe_konczy_sie_na_koniec_gdy_nastepne_ciecie_dalej():
    plan = plan_syntetyczny(poczatki=(0, 30, 500))
    poczatek, koniec_pisania, koniec = tekst.okno_pionowe(plan, 5, 30, 100)
    assert koniec == 100


def wzor_dlugi_do_pionowego():
    return {
        "ciecia_s": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        "zrodlo": {"czas_s": 8.0},
        "sekcje": {"drop_s": 5.0, "drop_ujecie": 5, "koniec_haka_uderzenia": None},
    }


def test_renderuj_pionowy_pelny_przebieg(tmp_path):
    def dodaj(katalog):
        for i in range(6):
            generuj.zdjecie_testowe(katalog / f"00000000{i:02d}_m.jpg", rozmiar=(800, 600), kolor=(20, 20, 20))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    dane = {"teksty": [], "pionowo": "ABC"}
    (projekt / "projekt.json").write_text(json.dumps(dane), encoding="utf-8")
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_dlugi_do_pionowego()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=10.0, pierwsze_uderzenie_s=0.0)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert podsumowanie["pionowo"]["znaki"] == 3
    poczatek = podsumowanie["pionowo"]["od"]
    koniec = podsumowanie["pionowo"]["do"]
    koniec_pisania = poczatek + 2 * 3

    klatki = dekoduj_klatki(wyjscie, tmp_path, "pionowo.raw")

    def rozmiar_zlota(klatka):
        return int(zlota_maska_klatki(klatka).sum())

    mala = rozmiar_zlota(klatki[poczatek + 2])
    indeks_pelnej = min(koniec_pisania, len(klatki) - 1)
    pelna = rozmiar_zlota(klatki[indeks_pelnej])
    assert mala < pelna

    if koniec + 2 < len(klatki):
        assert rozmiar_zlota(klatki[koniec + 2]) == 0


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


def test_renderuj_za_duzo_slow_pomija_warstwe_i_nie_pada(tmp_path):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(20, 20, 20))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    zapisz_projekt_slowa(projekt, " ".join(f"slowo{i}" for i in range(12)))
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_prosty()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=6.0, pierwsze_uderzenie_s=0.0)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert "pominiete" in podsumowanie["slowa"]
    podpis = komunikaty.podsumowanie_renderu(podsumowanie)
    assert "Słowa w rytmie pominięte" in podpis


def test_renderuj_za_dlugi_pionowy_pomija_warstwe_i_nie_pada(tmp_path):
    def dodaj(katalog):
        for i in range(4):
            generuj.zdjecie_testowe(katalog / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(20, 20, 20))

    projekt = zbuduj_projekt(tmp_path, dodaj)
    dane = {"teksty": [], "pionowo": "a" * 40}
    (projekt / "projekt.json").write_text(json.dumps(dane), encoding="utf-8")
    wzor_json = tmp_path / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_prosty()), encoding="utf-8")
    utwor = tmp_path / "klik.wav"
    generuj.klik(utwor, bpm=120, czas_s=6.0, pierwsze_uderzenie_s=0.0)
    fps = 30

    wyjscie = tmp_path / "wynik.mp4"
    podsumowanie = render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=fps, limit_mb=50)

    assert "pominiety" in podsumowanie["pionowo"]
    podpis = komunikaty.podsumowanie_renderu(podsumowanie)
    assert "Napis pionowy pominięty" in podpis
