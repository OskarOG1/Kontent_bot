import numpy as np
import pytest

import tekst

POLSKIE = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"


def wysokosc_znaku(czcionka, znak):
    bbox = czcionka.getbbox(znak)
    return bbox[3] - bbox[1]


@pytest.mark.parametrize("preset,zakres", [("szeryf", (38, 40)), ("blok", (48, 50))])
def test_wysokosc_wersalika_h_w_pikselach(preset, zakres):
    wysokosc = 1920
    dane_presetu = tekst.PRESETY[preset]
    sciezka, waga = tekst.wybierz_czcionke(dane_presetu)
    docelowa = dane_presetu["wysokosc_wersalika"] * wysokosc
    czcionka = tekst.dopasuj_wysokosc(sciezka, waga, docelowa)
    wys = wysokosc_znaku(czcionka, "H")
    assert zakres[0] <= wys <= zakres[1]


def test_wysokosc_litery_x_presetu_rytm_w_pikselach():
    wysokosc = 1920
    dane_presetu = tekst.PRESETY["rytm"]
    sciezka, waga = tekst.wybierz_czcionke(dane_presetu)
    docelowa = dane_presetu["wysokosc_wersalika"] * wysokosc
    czcionka = tekst.dopasuj_wysokosc(sciezka, waga, docelowa, znak_pomiaru="x")
    wys = wysokosc_znaku(czcionka, "x")
    assert 137 <= wys <= 151


def test_czcionki_maja_polskie_znaki():
    for preset in tekst.PRESETY.values():
        znaki = tekst.znaki_czcionki(preset["czcionka"])
        brakujace = [znak for znak in POLSKIE if ord(znak) not in znaki]
        assert brakujace == []


def test_obraz_tekstu_niepusty_ze_znakami_specjalnymi():
    obraz = tekst.obraz_tekstu(
        "Polska: 100% 'niepodległa' \\ 1918", 1080, 1920, {"preset": "szeryf"}
    )
    alfa = np.array(obraz)[:, :, 3]
    assert alfa.max() > 0


def ramka_niezerowej_alfy(obraz):
    alfa = np.array(obraz)[:, :, 3]
    wiersze, kolumny = np.nonzero(alfa)
    return kolumny.min(), wiersze.min(), kolumny.max(), wiersze.max()


def w_strefie(ramka, szerokosc, wysokosc):
    x0, y0, x1, y1 = ramka
    lewo = tekst.STREFA_BEZPIECZNA["lewo"] * szerokosc
    prawo = tekst.STREFA_BEZPIECZNA["prawo"] * szerokosc
    gora = tekst.STREFA_BEZPIECZNA["gora"] * wysokosc
    dol = tekst.STREFA_BEZPIECZNA["dol"] * wysokosc
    return x0 >= lewo - 1 and x1 <= prawo + 1 and y0 >= gora - 1 and y1 <= dol + 1


def test_dlugie_slowo_miesci_sie_w_strefie():
    szerokosc, wysokosc = 1080, 1920
    obraz = tekst.obraz_tekstu(
        "Konstantynopolitańczykowianeczka", szerokosc, wysokosc, {"preset": "szeryf"}
    )
    ramka = ramka_niezerowej_alfy(obraz)
    assert w_strefie(ramka, szerokosc, wysokosc)


@pytest.mark.parametrize("preset", ["szeryf", "blok"])
@pytest.mark.parametrize("pozycja", ["gora", "srodek", "dol"])
def test_pozycje_w_strefie_bezpiecznej(preset, pozycja):
    szerokosc, wysokosc = 1080, 1920
    obraz = tekst.obraz_tekstu(
        "Przykładowy napis testowy",
        szerokosc,
        wysokosc,
        {"preset": preset, "pozycja": pozycja},
    )
    ramka = ramka_niezerowej_alfy(obraz)
    assert w_strefie(ramka, szerokosc, wysokosc)


@pytest.mark.parametrize("preset", ["szeryf", "blok"])
def test_dolna_granica_przy_znaku_wodnym(preset):
    szerokosc, wysokosc = 1080, 1920
    obraz = tekst.obraz_tekstu(
        "To jest bardzo długa linia tekstu do złamania na wiele wierszy",
        szerokosc,
        wysokosc,
        {"preset": preset, "pozycja": "dol"},
        dolna_granica=0.75,
    )
    _, _, _, y1 = ramka_niezerowej_alfy(obraz)
    assert y1 <= 0.75 * wysokosc


def test_oczysc_usuwa_emoji():
    znaki_szeryfu = tekst.znaki_czcionki(tekst.PRESETY["szeryf"]["czcionka"])
    wynik = tekst.oczysc("Siema 🔥🔥 ziomek ✨", znaki_szeryfu)
    assert wynik == ("Siema ziomek", 3)


def test_szeryf_nie_zmienia_wielkosci_liter_blok_daje_wersaliki():
    assert tekst.PRESETY["szeryf"]["wersaliki"] is False
    assert tekst.PRESETY["blok"]["wersaliki"] is True

    szerokosc, wysokosc = 1080, 1920
    obraz_szeryf_a = tekst.obraz_tekstu("ala", szerokosc, wysokosc, {"preset": "szeryf"})
    obraz_szeryf_b = tekst.obraz_tekstu("ALA", szerokosc, wysokosc, {"preset": "szeryf"})
    assert not np.array_equal(np.array(obraz_szeryf_a), np.array(obraz_szeryf_b))

    obraz_blok_mala = tekst.obraz_tekstu("ala", szerokosc, wysokosc, {"preset": "blok"})
    obraz_blok_wielka = tekst.obraz_tekstu("ALA", szerokosc, wysokosc, {"preset": "blok"})
    assert np.array_equal(np.array(obraz_blok_mala), np.array(obraz_blok_wielka))
