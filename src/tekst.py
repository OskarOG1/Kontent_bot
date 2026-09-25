from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KATALOG_CZCIONEK = Path(__file__).resolve().parent.parent / "zasoby" / "czcionki"

STREFA_BEZPIECZNA = {"lewo": 0.08, "prawo": 0.85, "gora": 0.12, "dol": 0.78}

POZYCJE = {"gora": 0.22, "srodek": 0.50, "dol": 0.70}

POLSKIE = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"

PRESETY = {
    "szeryf": {
        "czcionka": KATALOG_CZCIONEK / "librebaskerville" / "LibreBaskerville.ttf",
        "waga": 700,
        "zapasowa": KATALOG_CZCIONEK / "notoserif" / "NotoSerif.ttf",
        "waga_zapasowa": 700,
        "wersaliki": False,
        "wysokosc_wersalika": 0.032,
        "cien": True,
        "obrys": False,
    },
    "blok": {
        "czcionka": KATALOG_CZCIONEK / "anton" / "Anton-Regular.ttf",
        "waga": None,
        "zapasowa": KATALOG_CZCIONEK / "oswald" / "Oswald.ttf",
        "waga_zapasowa": 700,
        "wersaliki": True,
        "wysokosc_wersalika": 0.04,
        "cien": False,
        "obrys": True,
    },
}


def znaki_czcionki(sciezka):
    return set(TTFont(str(sciezka)).getBestCmap().keys())


def oczysc(tekst, znaki):
    usuniete = 0
    wynik = []
    for znak in tekst:
        if znak == " " or ord(znak) in znaki:
            wynik.append(znak)
        else:
            usuniete += 1
    oczyszczony = " ".join("".join(wynik).split())
    return oczyszczony, usuniete


def _wczytaj_czcionke(sciezka, rozmiar, waga):
    czcionka = ImageFont.truetype(str(sciezka), rozmiar)
    if waga is not None:
        try:
            osie = czcionka.get_variation_axes()
        except OSError:
            osie = None
        if osie:
            wartosci = []
            for os_ in osie:
                if os_["name"] == b"Weight":
                    wartosci.append(float(waga))
                else:
                    wartosci.append(float(os_["default"]))
            czcionka.set_variation_by_axes(wartosci)
    return czcionka


def _wybierz_czcionke(preset):
    znaki = znaki_czcionki(preset["czcionka"])
    if all(ord(znak) in znaki for znak in POLSKIE):
        return preset["czcionka"], preset["waga"]
    return preset["zapasowa"], preset["waga_zapasowa"]


def _dopasuj_wysokosc(sciezka, waga, docelowa_wysokosc_px):
    rozmiar = max(int(docelowa_wysokosc_px * 1.4), 12)
    czcionka = _wczytaj_czcionke(sciezka, rozmiar, waga)
    bbox = czcionka.getbbox("AĄŻ")
    wysokosc = bbox[3] - bbox[1]
    if wysokosc > 0:
        rozmiar = max(int(rozmiar * docelowa_wysokosc_px / wysokosc), 12)
        czcionka = _wczytaj_czcionke(sciezka, rozmiar, waga)
    return czcionka


def _szerokosc(rysownik, tekst, czcionka):
    bbox = rysownik.textbbox((0, 0), tekst, font=czcionka)
    return bbox[2] - bbox[0]


def _dopasuj_do_strefy(tekst, rysownik, sciezka, waga, docelowa_wysokosc_px, max_szerokosc):
    czcionka = _dopasuj_wysokosc(sciezka, waga, docelowa_wysokosc_px)
    slowa = tekst.split(" ")
    for _ in range(50):
        najszersze = max(_szerokosc(rysownik, slowo, czcionka) for slowo in slowa)
        if najszersze <= max_szerokosc or czcionka.size <= 4:
            return czcionka
        nowy_rozmiar = max(int(czcionka.size * max_szerokosc / najszersze * 0.95), 4)
        if nowy_rozmiar >= czcionka.size:
            nowy_rozmiar = czcionka.size - 1
        czcionka = _wczytaj_czcionke(sciezka, nowy_rozmiar, waga)
    return czcionka


def _lamanie(tekst, rysownik, czcionka, max_szerokosc):
    slowa = tekst.split(" ")
    wiersze = []
    biezacy = ""
    for slowo in slowa:
        kandydat = f"{biezacy} {slowo}".strip()
        if not biezacy or _szerokosc(rysownik, kandydat, czcionka) <= max_szerokosc:
            biezacy = kandydat
        else:
            wiersze.append(biezacy)
            biezacy = slowo
    if biezacy:
        wiersze.append(biezacy)
    return wiersze


def obraz_tekstu(tekst, szerokosc, wysokosc, styl):
    preset = PRESETY[styl["preset"]]
    pozycja = POZYCJE[styl.get("pozycja", "dol")]
    wersaliki = styl.get("wersaliki")
    if wersaliki is None:
        wersaliki = preset["wersaliki"]
    tresc = tekst.upper() if wersaliki else tekst

    obraz = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
    rysownik = ImageDraw.Draw(obraz)
    if not tresc.strip():
        return obraz

    strefa_lewo = STREFA_BEZPIECZNA["lewo"] * szerokosc
    strefa_prawo = STREFA_BEZPIECZNA["prawo"] * szerokosc
    strefa_szerokosc = strefa_prawo - strefa_lewo
    strefa_gora = STREFA_BEZPIECZNA["gora"] * wysokosc
    strefa_dol = STREFA_BEZPIECZNA["dol"] * wysokosc

    przesuniecie_cienia = max(1, round(0.006 * wysokosc))
    grubosc_obrysu = max(1, round(0.004 * wysokosc))
    margines = przesuniecie_cienia * 3 if preset["cien"] else (grubosc_obrysu if preset["obrys"] else 0)
    szerokosc_uzyteczna = max(strefa_szerokosc - 2 * margines, 1)

    sciezka_czcionki, waga = _wybierz_czcionke(preset)
    docelowa_wysokosc = preset["wysokosc_wersalika"] * wysokosc
    czcionka = _dopasuj_do_strefy(tresc, rysownik, sciezka_czcionki, waga, docelowa_wysokosc, szerokosc_uzyteczna)

    wiersze = _lamanie(tresc, rysownik, czcionka, szerokosc_uzyteczna)

    ascent, descent = czcionka.getmetrics()
    wysokosc_wiersza = (ascent + descent) * 1.25
    wysokosc_bloku = wysokosc_wiersza * len(wiersze)

    srodek_y = pozycja * wysokosc
    gora_bloku = srodek_y - wysokosc_bloku / 2
    if gora_bloku < strefa_gora + margines:
        gora_bloku = strefa_gora + margines
    if gora_bloku + wysokosc_bloku > strefa_dol - margines:
        gora_bloku = strefa_dol - margines - wysokosc_bloku
    gora_bloku = max(gora_bloku, margines)

    y = gora_bloku
    for wiersz in wiersze:
        szer = _szerokosc(rysownik, wiersz, czcionka)
        x = strefa_lewo + (strefa_szerokosc - szer) / 2
        if preset["cien"]:
            warstwa_cienia = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
            rysownik_cienia = ImageDraw.Draw(warstwa_cienia)
            rysownik_cienia.text((x, y + przesuniecie_cienia), wiersz, font=czcionka, fill=(0, 0, 0, 153))
            warstwa_cienia = warstwa_cienia.filter(ImageFilter.GaussianBlur(przesuniecie_cienia))
            obraz.alpha_composite(warstwa_cienia)
            rysownik = ImageDraw.Draw(obraz)
        if preset["obrys"]:
            rysownik.text(
                (x, y),
                wiersz,
                font=czcionka,
                fill=(255, 255, 255, 255),
                stroke_width=grubosc_obrysu,
                stroke_fill=(0, 0, 0, 255),
            )
        else:
            rysownik.text((x, y), wiersz, font=czcionka, fill=(255, 255, 255, 255))
        y += wysokosc_wiersza

    return obraz
