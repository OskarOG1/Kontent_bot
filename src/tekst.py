import statistics
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
        "wysokosc_wersalika": 0.020,
        "cien": True,
        "obrys": False,
    },
    "blok": {
        "czcionka": KATALOG_CZCIONEK / "anton" / "Anton-Regular.ttf",
        "waga": None,
        "zapasowa": KATALOG_CZCIONEK / "oswald" / "Oswald.ttf",
        "waga_zapasowa": 700,
        "wersaliki": True,
        "wysokosc_wersalika": 0.026,
        "cien": False,
        "obrys": True,
    },
    "rytm": {
        "czcionka": KATALOG_CZCIONEK / "pacifico" / "Pacifico-Regular.ttf",
        "waga": None,
        "zapasowa": KATALOG_CZCIONEK / "kaushanscript" / "KaushanScript-Regular.ttf",
        "waga_zapasowa": None,
        "wersaliki": False,
        "wysokosc_wersalika": 0.075,
        "cien": True,
        "obrys": True,
    },
}

KOLOR_ZLOTY = (233, 196, 106, 255)
KOLOR_GRANATOWY = (24, 33, 74, 255)
PROG_KROKU_KLATEK = 9


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


def wczytaj_czcionke(sciezka, rozmiar, waga):
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


def wybierz_czcionke(preset):
    znaki = znaki_czcionki(preset["czcionka"])
    if all(ord(znak) in znaki for znak in POLSKIE):
        return preset["czcionka"], preset["waga"]
    return preset["zapasowa"], preset["waga_zapasowa"]


def dopasuj_wysokosc(sciezka, waga, docelowa_wysokosc_px, znak_pomiaru="H"):
    rozmiar = max(int(docelowa_wysokosc_px * 1.4), 12)
    czcionka = wczytaj_czcionke(sciezka, rozmiar, waga)
    bbox = czcionka.getbbox(znak_pomiaru)
    wysokosc = bbox[3] - bbox[1]
    if wysokosc > 0:
        rozmiar = max(int(rozmiar * docelowa_wysokosc_px / wysokosc), 12)
        czcionka = wczytaj_czcionke(sciezka, rozmiar, waga)
    return czcionka


def szerokosc_napisu(rysownik, tekst, czcionka):
    bbox = rysownik.textbbox((0, 0), tekst, font=czcionka)
    return bbox[2] - bbox[0]


def dopasuj_do_strefy(tekst, rysownik, sciezka, waga, docelowa_wysokosc_px, max_szerokosc):
    czcionka = dopasuj_wysokosc(sciezka, waga, docelowa_wysokosc_px)
    slowa = tekst.split(" ")
    for _ in range(50):
        najszersze = max(szerokosc_napisu(rysownik, slowo, czcionka) for slowo in slowa)
        if najszersze <= max_szerokosc or czcionka.size <= 4:
            return czcionka
        nowy_rozmiar = max(int(czcionka.size * max_szerokosc / najszersze * 0.95), 4)
        if nowy_rozmiar >= czcionka.size:
            nowy_rozmiar = czcionka.size - 1
        czcionka = wczytaj_czcionke(sciezka, nowy_rozmiar, waga)
    return czcionka


def lamanie(tekst, rysownik, czcionka, max_szerokosc):
    slowa = tekst.split(" ")
    wiersze = []
    biezacy = ""
    for slowo in slowa:
        kandydat = f"{biezacy} {slowo}".strip()
        if not biezacy or szerokosc_napisu(rysownik, kandydat, czcionka) <= max_szerokosc:
            biezacy = kandydat
        else:
            wiersze.append(biezacy)
            biezacy = slowo
    if biezacy:
        wiersze.append(biezacy)
    return wiersze


def obraz_tekstu(tekst, szerokosc, wysokosc, styl, dolna_granica=None):
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
    strefa_dol = (dolna_granica if dolna_granica is not None else STREFA_BEZPIECZNA["dol"]) * wysokosc

    przesuniecie_cienia = max(1, round(0.006 * wysokosc))
    grubosc_obrysu = max(1, round(0.004 * wysokosc))
    margines = przesuniecie_cienia * 3 if preset["cien"] else (grubosc_obrysu if preset["obrys"] else 0)
    szerokosc_uzyteczna = max(strefa_szerokosc - 2 * margines, 1)

    sciezka_czcionki, waga = wybierz_czcionke(preset)
    docelowa_wysokosc = preset["wysokosc_wersalika"] * wysokosc
    czcionka = dopasuj_do_strefy(tresc, rysownik, sciezka_czcionki, waga, docelowa_wysokosc, szerokosc_uzyteczna)

    wiersze = lamanie(tresc, rysownik, czcionka, szerokosc_uzyteczna)

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
        szer = szerokosc_napisu(rysownik, wiersz, czcionka)
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


def okna_tekstow(liczba_linii, plan, koniec_haka_klatka):
    if liczba_linii <= 0:
        return []

    fps = plan["fps"]
    liczba_klatek_calosci = plan["liczba_klatek"]
    poczatki_ujec = sorted({ujecie["klatka_od"] for ujecie in plan["ujecia"]})

    def przyciagnij(klatka):
        if not poczatki_ujec:
            return klatka
        najblizszy = min(poczatki_ujec, key=lambda k: abs(k - klatka))
        if abs(najblizszy - klatka) <= 8:
            return najblizszy
        return klatka

    koniec_okna = koniec_haka_klatka
    while True:
        granice = [round(koniec_okna * i / liczba_linii) for i in range(liczba_linii + 1)]
        poczatki = [granice[0]]
        for i in range(1, liczba_linii):
            poczatki.append(przyciagnij(granice[i]))
        koncowe = poczatki[1:] + [koniec_okna]
        dlugosci = [koniec - start for start, koniec in zip(poczatki, koncowe)]
        if all(dlugosc >= fps for dlugosc in dlugosci):
            return list(zip(poczatki, koncowe))
        kandydaci = {k for k in poczatki_ujec if k > koniec_okna}
        if liczba_klatek_calosci > koniec_okna:
            kandydaci.add(liczba_klatek_calosci)
        if not kandydaci:
            maks_linii = max(int(liczba_klatek_calosci // fps), 0)
            raise ValueError(f"Za dużo linii tekstu, najwyżej {maks_linii}")
        koniec_okna = min(kandydaci)


def skala_wjazdu_akcentu(klatka_lokalna: int) -> float:
    if klatka_lokalna >= 6:
        return 1.0
    return 1 + 5 * (1 - klatka_lokalna / 6) ** 2


def obraz_slowa(tresc: str, szerokosc: int, wysokosc: int, akcent: bool = False, wjazd: float = 1.0):
    obraz = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
    rysownik = ImageDraw.Draw(obraz)
    if not tresc.strip():
        return obraz

    strefa_lewo = STREFA_BEZPIECZNA["lewo"] * szerokosc
    strefa_prawo = STREFA_BEZPIECZNA["prawo"] * szerokosc
    strefa_szerokosc = strefa_prawo - strefa_lewo

    preset = PRESETY["rytm"]
    przesuniecie_cienia = max(1, round(0.004 * wysokosc))
    grubosc_obrysu = max(1, round(0.005 * wysokosc))
    margines = przesuniecie_cienia * 3 + grubosc_obrysu

    if akcent:
        max_szerokosc = max(0.95 * szerokosc, 1)
        docelowa_wysokosc = preset["wysokosc_wersalika"] * wysokosc * 1.6
    else:
        max_szerokosc = max(strefa_szerokosc - 2 * margines, 1)
        docelowa_wysokosc = preset["wysokosc_wersalika"] * wysokosc

    sciezka_czcionki, waga = wybierz_czcionke(preset)
    czcionka = dopasuj_wysokosc(sciezka_czcionki, waga, docelowa_wysokosc, znak_pomiaru="x")
    szer = szerokosc_napisu(rysownik, tresc, czcionka)
    while szer > max_szerokosc and czcionka.size > 4:
        czcionka = wczytaj_czcionke(sciezka_czcionki, czcionka.size - 1, waga)
        szer = szerokosc_napisu(rysownik, tresc, czcionka)

    if akcent and wjazd != 1.0:
        rozmiar_wjazdu = max(int(czcionka.size * wjazd), 4)
        czcionka = wczytaj_czcionke(sciezka_czcionki, rozmiar_wjazdu, waga)
        szer = szerokosc_napisu(rysownik, tresc, czcionka)

    ascent, descent = czcionka.getmetrics()
    wysokosc_tekstu = ascent + descent
    if akcent:
        x = szerokosc / 2 - szer / 2
    else:
        x = strefa_lewo + (strefa_szerokosc - szer) / 2
    y = wysokosc * 0.5 - wysokosc_tekstu / 2

    warstwa_cienia = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
    rysownik_cienia = ImageDraw.Draw(warstwa_cienia)
    rysownik_cienia.text((x, y + przesuniecie_cienia), tresc, font=czcionka, fill=(0, 0, 0, 102))
    warstwa_cienia = warstwa_cienia.filter(ImageFilter.GaussianBlur(przesuniecie_cienia))
    obraz.alpha_composite(warstwa_cienia)
    rysownik = ImageDraw.Draw(obraz)
    rysownik.text(
        (x, y), tresc, font=czcionka, fill=KOLOR_ZLOTY,
        stroke_width=grubosc_obrysu, stroke_fill=KOLOR_GRANATOWY,
    )
    return obraz


def indeks_pierwszego_uderzenia_od(uderzenia: list[int], klatka: float) -> int:
    for indeks, wartosc in enumerate(uderzenia):
        if wartosc >= klatka:
            return indeks
    return len(uderzenia) - 1


def okna_slow(
    liczba_slow: int, uderzenia: list[int], koniec_haka: int,
    fps: float = 30, liczba_klatek_calosci: int | None = None,
) -> list[tuple[int, int]]:
    if liczba_slow <= 0:
        return []

    a = indeks_pierwszego_uderzenia_od(uderzenia, koniec_haka - 2)
    odstepy = [uderzenia[i + 1] - uderzenia[i] for i in range(len(uderzenia) - 1)]
    krok = 1 if odstepy and statistics.median(odstepy) >= PROG_KROKU_KLATEK else 2

    if a - krok * (liczba_slow - 1) < 0:
        maks_slow = a // krok + 1
        raise ValueError(f"Za dużo słów w rytmie, najwyżej {maks_slow}")

    okna = []
    for indeks in range(liczba_slow - 1):
        indeks_start = a - krok * (liczba_slow - 1 - indeks)
        indeks_koniec = a - krok * (liczba_slow - 2 - indeks)
        okna.append((uderzenia[indeks_start], uderzenia[indeks_koniec]))

    start_akcentu = uderzenia[a]
    indeks_koniec_akcentu = a + 2 * krok
    if indeks_koniec_akcentu < len(uderzenia):
        koniec_akcentu = uderzenia[indeks_koniec_akcentu]
    else:
        koniec_akcentu = start_akcentu + round(fps)
    if liczba_klatek_calosci is not None:
        koniec_akcentu = min(koniec_akcentu, liczba_klatek_calosci)
    okna.append((start_akcentu, koniec_akcentu))

    return okna


OS_PIONOWA_SZEROKOSC = 0.05
DOLNA_KRAWEDZ_PIONOWA_WYSOKOSC = 0.85
WYSOKOSC_WERSALIKA_PIONOWA = 0.026
LIMIT_DLUGOSCI_PIONOWEJ = 0.8
KROK_ZNAKOW_KLATKI = 2


def obraz_pionowy(tresc: str, k: int, szerokosc: int, wysokosc: int):
    obraz = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
    widoczny = tresc[: max(0, min(k, len(tresc)))]
    if not widoczny.strip():
        return obraz

    preset = PRESETY["szeryf"]
    sciezka_czcionki, waga = wybierz_czcionke(preset)
    docelowa_wysokosc = WYSOKOSC_WERSALIKA_PIONOWA * wysokosc
    czcionka = dopasuj_wysokosc(sciezka_czcionki, waga, docelowa_wysokosc)

    rysownik_tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    grubosc_obrysu = max(1, round(0.005 * wysokosc))
    dlugosc_pelna = szerokosc_napisu(rysownik_tmp, tresc, czcionka)
    limit_dlugosci = LIMIT_DLUGOSCI_PIONOWEJ * wysokosc
    while dlugosc_pelna > limit_dlugosci and czcionka.size > 4:
        czcionka = wczytaj_czcionke(sciezka_czcionki, czcionka.size - 1, waga)
        dlugosc_pelna = szerokosc_napisu(rysownik_tmp, tresc, czcionka)

    bbox = rysownik_tmp.textbbox((0, 0), widoczny, font=czcionka, stroke_width=grubosc_obrysu)
    szer_bbox = max(1, bbox[2] - bbox[0])
    wys_bbox = max(1, bbox[3] - bbox[1])
    pasek = Image.new("RGBA", (szer_bbox, wys_bbox), (0, 0, 0, 0))
    rys_pasek = ImageDraw.Draw(pasek)
    rys_pasek.text(
        (-bbox[0], -bbox[1]), widoczny, font=czcionka, fill=KOLOR_ZLOTY,
        stroke_width=grubosc_obrysu, stroke_fill=KOLOR_GRANATOWY,
    )
    obrocony = pasek.rotate(90, expand=True)

    os_x = OS_PIONOWA_SZEROKOSC * szerokosc
    dolna_krawedz_y = DOLNA_KRAWEDZ_PIONOWA_WYSOKOSC * wysokosc
    x = round(os_x - obrocony.width / 2)
    y = round(dolna_krawedz_y - obrocony.height)
    obraz.alpha_composite(obrocony, (x, y))
    return obraz


def okno_pionowe(plan: dict, liczba_znakow: int, fps: float, koniec: int) -> tuple[int, int, int]:
    plan_ujecia = plan["ujecia"]
    poczatki_ujec = sorted({ujecie["klatka_od"] for ujecie in plan_ujecia})

    poczatek_preferowany = poczatki_ujec[1] if len(poczatki_ujec) > 1 else 0
    if poczatek_preferowany + KROK_ZNAKOW_KLATKI * liczba_znakow + fps <= koniec:
        poczatek = poczatek_preferowany
    else:
        poczatek = 0

    koniec_pisania = poczatek + KROK_ZNAKOW_KLATKI * liczba_znakow
    minimalny_koniec = koniec_pisania + fps

    if minimalny_koniec > koniec:
        maks_znakow = max(int((koniec - poczatek - fps) // KROK_ZNAKOW_KLATKI), 0)
        raise ValueError(f"Za dużo znaków w napisie pionowym, najwyżej {maks_znakow}")

    kandydaci = [k for k in poczatki_ujec if k > minimalny_koniec]
    kandydaci.append(plan["liczba_klatek"])
    koniec_napisu = min(min(kandydaci), koniec)

    return poczatek, koniec_pisania, koniec_napisu
