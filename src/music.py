import argparse
import json
import math
import sys
from pathlib import Path

import numpy

import analyze

ROZSZERZENIA_MUZYKI = {"mp3", "wav", "m4a", "ogg", "flac", "mp4"}
WERSJA_INDEKSU = 2
PROG_ZGODNOSCI = 0.5


def pliki_muzyki(katalog) -> list[Path]:
    katalog = Path(katalog)
    if not katalog.is_dir():
        return []
    wynik = [
        p for p in katalog.iterdir()
        if p.is_file() and p.suffix.lower().lstrip(".") in ROZSZERZENIA_MUZYKI
    ]
    return sorted(wynik, key=lambda p: p.name)


def wczytaj_indeks(katalog: Path) -> dict:
    plik = katalog / "indeks.json"
    if not plik.is_file():
        return {"wersja": WERSJA_INDEKSU, "utwory": []}
    try:
        return json.loads(plik.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"wersja": WERSJA_INDEKSU, "utwory": []}


def indeksuj(katalog) -> tuple[dict, int]:
    katalog = Path(katalog)
    katalog.mkdir(parents=True, exist_ok=True)
    stary = wczytaj_indeks(katalog)
    wpisy_wg_pliku = {wpis["plik"]: wpis for wpis in stary.get("utwory", [])}
    nowe_utwory = []
    przeanalizowane = 0
    for sciezka in pliki_muzyki(katalog):
        stat = sciezka.stat()
        rozmiar = stat.st_size
        zmieniony = stat.st_mtime
        istniejacy = wpisy_wg_pliku.get(sciezka.name)
        if istniejacy is not None and istniejacy.get("rozmiar") == rozmiar and istniejacy.get("zmieniony") == zmieniony:
            nowe_utwory.append(istniejacy)
            continue
        dzwiek = analyze.analizuj_dzwiek(sciezka)
        przeanalizowane += 1
        if dzwiek is None:
            print(f"Pomijam {sciezka.name}: brak dźwięku")
            continue
        wpis = dict(dzwiek)
        wpis["plik"] = sciezka.name
        wpis["rozmiar"] = rozmiar
        wpis["zmieniony"] = zmieniony
        nowe_utwory.append(wpis)
    nowe_utwory.sort(key=lambda w: w["plik"])
    indeks = {"wersja": WERSJA_INDEKSU, "utwory": nowe_utwory}
    analyze.zapisz_json(indeks, katalog / "indeks.json")
    return indeks, przeanalizowane


def zgodnosc_ramek(chroma_wzoru, okno_utworu) -> float:
    chroma_wzoru = numpy.asarray(chroma_wzoru, dtype=float)
    okno_utworu = numpy.asarray(okno_utworu, dtype=float)
    norma_wzoru = numpy.linalg.norm(chroma_wzoru, axis=1)
    norma_okna = numpy.linalg.norm(okno_utworu, axis=1)
    maska = (norma_wzoru > 1e-9) & (norma_okna > 1e-9)
    if not maska.any():
        return 0.0
    iloczyny = numpy.sum(chroma_wzoru[maska] * okno_utworu[maska], axis=1)
    mianownik = norma_wzoru[maska] * norma_okna[maska]
    return float(numpy.mean(iloczyny / mianownik))


def korelacja(a, b) -> float:
    a = numpy.asarray(a, dtype=float)
    b = numpy.asarray(b, dtype=float)
    if a.size < 2 or a.std() == 0 or b.std() == 0:
        return 0.0
    wynik = float(numpy.corrcoef(a, b)[0, 1])
    return wynik if not math.isnan(wynik) else 0.0


def dopasuj_odcisk(odcisk_wzoru: dict, odcisk_utworu: dict):
    chroma_wzoru = numpy.asarray(odcisk_wzoru["chroma"], dtype=float)
    chroma_utworu = numpy.asarray(odcisk_utworu["chroma"], dtype=float)
    dlugosc_wzoru = len(chroma_wzoru)
    dlugosc_utworu = len(chroma_utworu)
    if dlugosc_wzoru > dlugosc_utworu:
        return None

    najlepsza_zgodnosc = None
    najlepszy_offset = 0
    for o in range(dlugosc_utworu - dlugosc_wzoru + 1):
        okno = chroma_utworu[o:o + dlugosc_wzoru]
        zgodnosc = zgodnosc_ramek(chroma_wzoru, okno)
        if najlepsza_zgodnosc is None or zgodnosc > najlepsza_zgodnosc:
            najlepsza_zgodnosc = zgodnosc
            najlepszy_offset = o

    krok_chroma_s = odcisk_utworu["krok_chroma_s"]
    przyblizone_przesuniecie_s = najlepszy_offset * krok_chroma_s

    obwiednia_wzoru = numpy.asarray(odcisk_wzoru["obwiednia"], dtype=float)
    obwiednia_utworu = numpy.asarray(odcisk_utworu["obwiednia"], dtype=float)
    krok_obwiedni_s = odcisk_utworu["krok_obwiedni_s"]
    dlugosc_wzoru_obw = len(obwiednia_wzoru)

    okno_ramek = max(1, int(round(0.2 / krok_obwiedni_s)))
    srodek_ramka = int(round(przyblizone_przesuniecie_s / krok_obwiedni_s))
    najlepsze_przesuniecie_s = przyblizone_przesuniecie_s
    najlepsza_korelacja_obw = None
    for delta in range(-okno_ramek, okno_ramek + 1):
        start = srodek_ramka + delta
        if start < 0 or start + dlugosc_wzoru_obw > len(obwiednia_utworu):
            continue
        okno_obw = obwiednia_utworu[start:start + dlugosc_wzoru_obw]
        korelacja_obw = korelacja(obwiednia_wzoru, okno_obw)
        if najlepsza_korelacja_obw is None or korelacja_obw > najlepsza_korelacja_obw:
            najlepsza_korelacja_obw = korelacja_obw
            najlepsze_przesuniecie_s = start * krok_obwiedni_s

    return round(float(najlepsza_zgodnosc), 3), round(float(najlepsze_przesuniecie_s), 3)


def wybierz_mnoznik(tempo_utworu: float, tempo_wzoru: float) -> tuple[float, float]:
    kandydaci = [
        (1.0, abs(tempo_utworu - tempo_wzoru)),
        (2.0, abs(2 * tempo_utworu - tempo_wzoru)),
        (0.5, abs(tempo_utworu / 2 - tempo_wzoru)),
    ]
    kandydaci.sort(key=lambda kv: kv[1])
    return kandydaci[0]


def zagesc_mnoznikiem(uderzenia: list[float], energia: list[float], mnoznik: float):
    if mnoznik == 1.0:
        return list(uderzenia), list(energia)
    if mnoznik == 2.0:
        nowe_uderzenia = []
        nowa_energia = []
        for i in range(len(uderzenia) - 1):
            a, b = uderzenia[i], uderzenia[i + 1]
            nowe_uderzenia.append(a)
            if i < len(energia):
                nowa_energia.append(energia[i])
                nowa_energia.append(energia[i])
            nowe_uderzenia.append((a + b) / 2)
        nowe_uderzenia.append(uderzenia[-1])
        return nowe_uderzenia, nowa_energia
    if mnoznik == 0.5:
        nowe_uderzenia = uderzenia[::2]
        nowa_energia = []
        for k in range(len(nowe_uderzenia) - 1):
            i = 2 * k
            wartosci = energia[i:i + 2]
            if wartosci:
                nowa_energia.append(sum(wartosci) / len(wartosci))
        return nowe_uderzenia, nowa_energia
    raise ValueError("Nieobsługiwany mnożnik")


def waz_kandydata_tempo(wzor: dict, uderzenia_dostosowane: list[float]) -> list[int]:
    c0 = wzor["ciecia_uderzenia"][0]
    koniec = wzor["koniec_uderzenia"]
    ostatni_indeks = len(uderzenia_dostosowane) - 1
    if ostatni_indeks < 0:
        return []
    zakres = range(-ostatni_indeks - 2, ostatni_indeks + 2)
    poprawne_s = []
    for s in zakres:
        if analyze.czas_z_pozycji(s + c0, uderzenia_dostosowane) < 0:
            continue
        if s + koniec > ostatni_indeks:
            continue
        poprawne_s.append(s)
    return poprawne_s


def znajdz_start_uderzenie(wzor: dict, uderzenia_dostosowane, energia_dostosowana, poprawne_s):
    c0 = wzor["ciecia_uderzenia"][0]
    koniec = wzor["koniec_uderzenia"]
    energia_wzoru = wzor.get("energia_uderzen") or []
    zakres_j = [j for j in range(math.floor(c0), math.ceil(koniec)) if 0 <= j < len(energia_wzoru)]

    najlepsze_s = None
    najlepsza_wartosc = None
    for s in sorted(poprawne_s):
        pary = [
            (energia_wzoru[j], energia_dostosowana[s + j])
            for j in zakres_j
            if 0 <= s + j < len(energia_dostosowana)
        ]
        if len(pary) >= 2:
            wartosc = korelacja([p[0] for p in pary], [p[1] for p in pary])
        else:
            wartosc = float("-inf")
        if najlepsze_s is None or wartosc > najlepsza_wartosc:
            najlepsze_s = s
            najlepsza_wartosc = wartosc
    return najlepsze_s


def dopasuj_po_dzwieku(wzor: dict, utwory: list[dict], odcisk_wzoru: dict):
    tempo_wzoru = wzor.get("tempo_bpm")
    najlepszy = None
    for wpis in sorted(utwory, key=lambda w: w["plik"]):
        odcisk_utworu = wpis.get("odcisk")
        if odcisk_utworu is None:
            continue
        dopasowanie = dopasuj_odcisk(odcisk_wzoru, odcisk_utworu)
        if dopasowanie is None:
            continue
        zgodnosc, przesuniecie_s = dopasowanie
        if zgodnosc < PROG_ZGODNOSCI:
            continue
        if najlepszy is None or zgodnosc > najlepszy["zgodnosc"]:
            najlepszy = {
                "plik": wpis["plik"], "zgodnosc": zgodnosc, "przesuniecie_s": przesuniecie_s,
                "tempo_bpm": wpis.get("tempo_bpm"), "uderzenia_s": wpis.get("uderzenia_s") or [],
            }
    if najlepszy is None:
        return None
    odleglosc_bpm = None
    if tempo_wzoru is not None and najlepszy["tempo_bpm"] is not None:
        _, odleglosc = wybierz_mnoznik(najlepszy["tempo_bpm"], tempo_wzoru)
        odleglosc_bpm = round(odleglosc, 3)
    return {
        "plik": najlepszy["plik"], "tryb": "dzwiek_wzoru", "zgodnosc": najlepszy["zgodnosc"],
        "przesuniecie_s": najlepszy["przesuniecie_s"], "tempo_bpm": najlepszy["tempo_bpm"], "mnoznik": 1.0,
        "uderzenia_s": najlepszy["uderzenia_s"], "start_uderzenie": None, "odleglosc_bpm": odleglosc_bpm,
    }


def dopasuj_po_tempie(wzor: dict, utwory: list[dict], tempo_wzoru: float):
    bez_tempa = 0
    za_krotkie = 0
    kandydaci = []
    for wpis in utwory:
        tempo_utworu = wpis.get("tempo_bpm")
        uderzenia_utworu = wpis.get("uderzenia_s") or []
        if tempo_utworu is None or len(uderzenia_utworu) < 2:
            bez_tempa += 1
            continue
        mnoznik, odleglosc = wybierz_mnoznik(tempo_utworu, tempo_wzoru)
        energia_utworu = wpis.get("energia_uderzen") or []
        uderzenia_dostosowane, energia_dostosowana = zagesc_mnoznikiem(uderzenia_utworu, energia_utworu, mnoznik)
        poprawne_s = waz_kandydata_tempo(wzor, uderzenia_dostosowane)
        if not poprawne_s:
            za_krotkie += 1
            continue
        kandydaci.append({
            "plik": wpis["plik"], "tempo_bpm": tempo_utworu, "mnoznik": mnoznik, "odleglosc": odleglosc,
            "uderzenia_dostosowane": uderzenia_dostosowane, "energia_dostosowana": energia_dostosowana,
            "poprawne_s": poprawne_s,
        })
    if not kandydaci:
        return None, bez_tempa, za_krotkie
    kandydaci.sort(key=lambda k: (k["odleglosc"], k["plik"]))
    wybrany = kandydaci[0]
    start_uderzenie = znajdz_start_uderzenie(
        wzor, wybrany["uderzenia_dostosowane"], wybrany["energia_dostosowana"], wybrany["poprawne_s"]
    )
    wynik = {
        "plik": wybrany["plik"], "tryb": "tempo", "zgodnosc": None, "przesuniecie_s": None,
        "tempo_bpm": wybrany["tempo_bpm"], "mnoznik": wybrany["mnoznik"],
        "uderzenia_s": wybrany["uderzenia_dostosowane"], "start_uderzenie": start_uderzenie,
        "odleglosc_bpm": round(wybrany["odleglosc"], 3),
    }
    return wynik, bez_tempa, za_krotkie


def zbuduj_wynik_bez_rytmu(wpis: dict) -> dict:
    return {
        "plik": wpis["plik"], "tryb": "bez_rytmu", "zgodnosc": None, "przesuniecie_s": 0.0,
        "tempo_bpm": wpis.get("tempo_bpm"), "mnoznik": 1.0, "uderzenia_s": wpis.get("uderzenia_s") or [],
        "start_uderzenie": None, "odleglosc_bpm": None,
    }


def wybierz_utwor(wzor: dict, indeks: dict) -> dict:
    utwory = indeks.get("utwory", [])

    tempo_wzoru = wzor.get("tempo_bpm")
    ciecia_uderzenia = wzor.get("ciecia_uderzenia")
    if tempo_wzoru is not None and ciecia_uderzenia:
        wynik, bez_tempa, za_krotkie = dopasuj_po_tempie(wzor, utwory, tempo_wzoru)
        if wynik is not None:
            return wynik
        raise ValueError(f"Brak pasującego utworu: bez tempa {bez_tempa}, za krótkie {za_krotkie}")

    dlugosc_wzoru = wzor.get("zrodlo", {}).get("czas_s", 0.0)
    kandydaci = sorted(
        (w for w in utwory if w.get("czas_s", 0.0) >= dlugosc_wzoru),
        key=lambda w: w["plik"],
    )
    if kandydaci:
        return zbuduj_wynik_bez_rytmu(kandydaci[0])

    za_krotkie = sum(1 for w in utwory if w.get("czas_s", 0.0) < dlugosc_wzoru)
    raise ValueError(f"Brak pasującego utworu: bez tempa 0, za krótkie {za_krotkie}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="music.py")
    podkomendy = parser.add_subparsers(dest="komenda", required=True)

    p_indeksuj = podkomendy.add_parser("indeksuj")
    p_indeksuj.add_argument("--katalog", default="dane/muzyka")

    p_wybierz = podkomendy.add_parser("wybierz")
    p_wybierz.add_argument("--wzor", required=True)
    p_wybierz.add_argument("--katalog", default="dane/muzyka")

    ns = parser.parse_args(argv)

    if ns.komenda == "indeksuj":
        indeks, liczba = indeksuj(ns.katalog)
        for wpis in indeks["utwory"]:
            print(wpis["plik"], wpis.get("czas_s"), wpis.get("tempo_bpm"), len(wpis.get("uderzenia_s") or []))
        print(f"Przeanalizowane: {liczba}")
        return 0

    wzor = json.loads(Path(ns.wzor).read_text(encoding="utf-8"))
    indeks, _ = indeksuj(ns.katalog)
    odcisk_wzoru = wzor.get("odcisk_dzwieku")
    for wpis in indeks["utwory"]:
        zgodnosc = None
        if odcisk_wzoru is not None and wpis.get("odcisk") is not None:
            dopasowanie = dopasuj_odcisk(odcisk_wzoru, wpis["odcisk"])
            zgodnosc = dopasowanie[0] if dopasowanie is not None else None
        print(wpis["plik"], zgodnosc)
    wybor = wybierz_utwor(wzor, indeks)
    print(wybor["plik"], wybor["tryb"], len(wybor.get("uderzenia_s") or []))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
