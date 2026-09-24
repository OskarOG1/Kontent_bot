import numpy

MACIERZ_RGB_DO_XYZ = numpy.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])
MACIERZ_XYZ_DO_RGB = numpy.linalg.inv(MACIERZ_RGB_DO_XYZ)
BIEL_D65 = numpy.array([0.95047, 1.0, 1.08883])


def gamma_do_liniowego(kanal: numpy.ndarray) -> numpy.ndarray:
    kanal = numpy.clip(kanal, 0.0, 1.0)
    return numpy.where(kanal <= 0.04045, kanal / 12.92, ((kanal + 0.055) / 1.055) ** 2.4)


def liniowy_do_gamma(kanal: numpy.ndarray) -> numpy.ndarray:
    kanal = numpy.clip(kanal, 0.0, 1.0)
    return numpy.where(kanal <= 0.0031308, kanal * 12.92, 1.055 * kanal ** (1 / 2.4) - 0.055)


def f_lab(t: numpy.ndarray) -> numpy.ndarray:
    prog = (6 / 29) ** 3
    return numpy.where(t > prog, numpy.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)


def f_lab_odwrotna(t: numpy.ndarray) -> numpy.ndarray:
    prog = 6 / 29
    return numpy.where(t > prog, t ** 3, 3 * (6 / 29) ** 2 * (t - 4 / 29))


def rgb_do_lab(tablica) -> numpy.ndarray:
    wejscie = numpy.asarray(tablica)
    if numpy.issubdtype(wejscie.dtype, numpy.integer):
        rgb = wejscie.astype(numpy.float64) / 255.0
    else:
        rgb = wejscie.astype(numpy.float64)
    liniowe = gamma_do_liniowego(rgb)
    xyz = liniowe @ MACIERZ_RGB_DO_XYZ.T
    fx = f_lab(xyz[..., 0] / BIEL_D65[0])
    fy = f_lab(xyz[..., 1] / BIEL_D65[1])
    fz = f_lab(xyz[..., 2] / BIEL_D65[2])
    l = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return numpy.stack([l, a, b], axis=-1)


def lab_do_rgb(tablica) -> numpy.ndarray:
    lab = numpy.asarray(tablica, dtype=numpy.float64)
    l, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    fy = (l + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    x = BIEL_D65[0] * f_lab_odwrotna(fx)
    y = BIEL_D65[1] * f_lab_odwrotna(fy)
    z = BIEL_D65[2] * f_lab_odwrotna(fz)
    xyz = numpy.stack([x, y, z], axis=-1)
    liniowe = xyz @ MACIERZ_XYZ_DO_RGB.T
    return numpy.clip(liniowy_do_gamma(liniowe), 0.0, 1.0)


def statystyki_obrazu(tablica_rgb) -> dict:
    lab = rgb_do_lab(tablica_rgb).reshape(-1, 3)
    srednia = lab.mean(axis=0)
    odchylenie = lab.std(axis=0)
    return {
        "lab_srednia": [float(wartosc) for wartosc in srednia],
        "lab_odchylenie": [float(wartosc) for wartosc in odchylenie],
    }


def polacz_statystyki(wpisy: list[dict]) -> dict:
    wagi = numpy.array([wpis["probki"] for wpis in wpisy], dtype=numpy.float64)
    srednie = numpy.array([wpis["lab_srednia"] for wpis in wpisy], dtype=numpy.float64)
    odchylenia = numpy.array([wpis["lab_odchylenie"] for wpis in wpisy], dtype=numpy.float64)
    suma_wag = wagi.sum()
    srednia = (wagi[:, None] * srednie).sum(axis=0) / suma_wag
    wariancja = (wagi[:, None] * (odchylenia ** 2 + (srednie - srednia) ** 2)).sum(axis=0) / suma_wag
    return {
        "lab_srednia": [float(wartosc) for wartosc in srednia],
        "lab_odchylenie": [float(wartosc) for wartosc in numpy.sqrt(wariancja)],
    }


def indeksy_sekcji(liczba_ujec: int, sekcje: dict | None, numer_wzoru: int) -> list[int]:
    calosc = list(range(liczba_ujec - 1))
    if not sekcje:
        return calosc
    drop_ujecie = sekcje["drop_ujecie"]
    if numer_wzoru < drop_ujecie:
        return [i for i in calosc if i < drop_ujecie]
    return [i for i in calosc if i >= drop_ujecie]


def cel_sekcji(kolorystyka: dict, sekcje: dict | None, numer_wzoru: int) -> dict:
    ujecia = kolorystyka["ujecia"]
    calosc = [ujecia[i] for i in range(len(ujecia) - 1)]
    sekcja = [ujecia[i] for i in indeksy_sekcji(len(ujecia), sekcje, numer_wzoru)]
    uzyteczne = [wpis for wpis in sekcja if wpis["probki"] > 0]
    if not uzyteczne:
        uzyteczne = [wpis for wpis in calosc if wpis["probki"] > 0] or calosc
    return polacz_statystyki(uzyteczne)


def lut_transferu(zrodlo: dict, cel: dict, sila: float, rozmiar: int = 33) -> numpy.ndarray:
    os_siatki = numpy.arange(rozmiar, dtype=numpy.float64) / (rozmiar - 1)
    r, g, b = numpy.meshgrid(os_siatki, os_siatki, os_siatki, indexing="ij")
    lab = rgb_do_lab(numpy.stack([r, g, b], axis=-1))

    srednia_zr = numpy.array(zrodlo["lab_srednia"], dtype=numpy.float64)
    odchylenie_zr = numpy.array(zrodlo["lab_odchylenie"], dtype=numpy.float64)
    srednia_cel = numpy.array(cel["lab_srednia"], dtype=numpy.float64)
    odchylenie_cel = numpy.array(cel["lab_odchylenie"], dtype=numpy.float64)

    stosunek = numpy.clip(odchylenie_cel / numpy.maximum(odchylenie_zr, 1e-6), 0.5, 2.0)
    lab_przeniesiony = (lab - srednia_zr) * stosunek + srednia_cel
    lab_zmieszany = lab * (1.0 - sila) + lab_przeniesiony * sila
    return numpy.clip(lab_do_rgb(lab_zmieszany), 0.0, 1.0)


def zapisz_cube(lut: numpy.ndarray, sciezka) -> None:
    rozmiar = lut.shape[0]
    permutowany = numpy.transpose(lut, (2, 1, 0, 3))
    with open(sciezka, "w", encoding="utf-8") as plik:
        plik.write(f"LUT_3D_SIZE {rozmiar}\n")
        for r, g, b in permutowany.reshape(-1, 3):
            plik.write(f"{r:.6f} {g:.6f} {b:.6f}\n")
