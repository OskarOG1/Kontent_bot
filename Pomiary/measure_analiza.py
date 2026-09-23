import json
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 2 (analiza wzoru).
# Sekcja A (syntetyczna): 6 temp x 3 uklady ciec. Progi: 100% ciec (czulosc i precyzja
#   przy tolerancji 1 klatki) i blad tempa do 2% po uwzglednieniu oktawy.
# Sekcja B (realna): pliki z dane/probki/wzory/ (albo z katalogu podanego jako argument),
#   osobno ContentDetector (analyze.wykryj_ciecia) i AdaptiveDetector z domyslnymi
#   parametrami. Tylko raport i arkusze PNG, ocenia oceniajacy na arkuszach.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from scenedetect import AdaptiveDetector, detect  # noqa: E402

import analyze  # noqa: E402
from generuj import wideo_z_cieciami  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_analiza.json"
DOMYSLNY_KATALOG_PROBEK = KATALOG_REPO / "dane" / "probki" / "wzory"
TEMPA = [70, 90, 110, 128, 150, 170]
UKLADY = ["co_uderzenie", "co_pol_uderzenia", "mieszany"]
FPS = 30
CZAS_S = 12.0
PIERWSZE_UDERZENIE_S = 0.3
TOLERANCJA_KLATEK = 1
TOLERANCJA_TEMPA = 0.02
TOLERANCJA_UDERZENIA_S = 0.04
WYSOKOSC_MINIATURY = 200
LIMIT_ARKUSZA_PX = 1600


def zapisz_wyniki(wyniki: dict) -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(wyniki, plik, ensure_ascii=False, indent=2)


def klatki_ciec(bpm: float, uklad: str) -> list[int]:
    odstep = 60.0 / bpm
    liczba_klatek = int(round(CZAS_S * FPS))
    czasy = []
    k = 0
    while True:
        t = PIERWSZE_UDERZENIE_S + k * odstep
        if t >= CZAS_S:
            break
        czasy.append(t)
        if uklad == "co_pol_uderzenia":
            czasy.append(t + odstep / 2)
        if uklad == "mieszany" and k % 3 == 2:
            czasy.append(t + 4 / FPS)
        k += 1
    klatki = sorted({int(round(t * FPS)) for t in czasy})
    wynik = []
    for klatka in klatki:
        if klatka <= 0 or klatka >= liczba_klatek - 3:
            continue
        if wynik and klatka - wynik[-1] < 3:
            continue
        wynik.append(klatka)
    return wynik


def dopasuj(oczekiwane: list[int], znalezione: list[int], tolerancja: int) -> int:
    wolne = list(znalezione)
    trafione = 0
    for klatka in oczekiwane:
        najlepszy = None
        for kandydat in wolne:
            if abs(kandydat - klatka) <= tolerancja and (najlepszy is None or abs(kandydat - klatka) < abs(najlepszy - klatka)):
                najlepszy = kandydat
        if najlepszy is not None:
            wolne.remove(najlepszy)
            trafione += 1
    return trafione


def blad_tempa(tempo: float | None, prawdziwe: float) -> tuple[float | None, int]:
    if tempo is None:
        return None, 0
    kandydaci = [(abs(tempo * m - prawdziwe) / prawdziwe, m) for m in (0.5, 1.0, 2.0)]
    blad, mnoznik = min(kandydaci)
    return blad, int(mnoznik != 1.0)


def sekcja_a() -> dict:
    wyniki = {"przypadki": [], "progi": {}}
    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        for bpm in TEMPA:
            for uklad in UKLADY:
                klatki = klatki_ciec(bpm, uklad)
                sciezka = katalog / f"{bpm}_{uklad}.mp4"
                wideo_z_cieciami(
                    sciezka,
                    [k / FPS for k in klatki],
                    CZAS_S,
                    fps=FPS,
                    bpm=bpm,
                    pierwsze_uderzenie_s=PIERWSZE_UDERZENIE_S,
                )
                start = time.monotonic()
                znalezione = [int(round(t * FPS)) for t in analyze.wykryj_ciecia(sciezka) if t > 0]
                czas_ciec = time.monotonic() - start
                start = time.monotonic()
                tempo, uderzenia = analyze.analizuj_rytm(sciezka)
                czas_rytmu = time.monotonic() - start
                trafione = dopasuj(klatki, znalezione, TOLERANCJA_KLATEK)
                blad, oktawa = blad_tempa(tempo, bpm)
                przypadek = {
                    "bpm": bpm,
                    "uklad": uklad,
                    "ciecia_oczekiwane": len(klatki),
                    "ciecia_znalezione": len(znalezione),
                    "czulosc": trafione / len(klatki),
                    "precyzja": trafione / len(znalezione) if znalezione else 0.0,
                    "tempo": tempo,
                    "blad_tempa_proc": None if blad is None else round(100 * blad, 2),
                    "pomylka_oktawy": oktawa,
                    "liczba_uderzen": len(uderzenia),
                    "czas_ciec_s": round(czas_ciec, 2),
                    "czas_rytmu_s": round(czas_rytmu, 2),
                }
                wyniki["przypadki"].append(przypadek)
                print(
                    f"A {bpm:>3} {uklad:<17} ciecia {trafione}/{len(klatki)} (znalezione {len(znalezione)}) "
                    f"tempo {tempo} blad {przypadek['blad_tempa_proc']}% oktawa {oktawa}"
                )
                zapisz_wyniki({"A": wyniki})
    przypadki = wyniki["przypadki"]
    ciecia_ok = all(p["czulosc"] == 1.0 and p["precyzja"] == 1.0 for p in przypadki)
    tempo_ok = all(p["blad_tempa_proc"] is not None and p["blad_tempa_proc"] <= 100 * TOLERANCJA_TEMPA for p in przypadki)
    wyniki["czulosc_srednia"] = round(statistics.mean(p["czulosc"] for p in przypadki), 4)
    wyniki["precyzja_srednia"] = round(statistics.mean(p["precyzja"] for p in przypadki), 4)
    wyniki["blad_tempa_maks_proc"] = max((p["blad_tempa_proc"] for p in przypadki if p["blad_tempa_proc"] is not None), default=None)
    wyniki["pomylki_oktawy"] = sum(p["pomylka_oktawy"] for p in przypadki)
    wyniki["progi"] = {"ciecia_100_proc": ciecia_ok, "tempo_do_2_proc": tempo_ok}
    return wyniki


def ciecia_adaptive(sciezka: Path) -> list[float]:
    dane = analyze.odczytaj_strumienie(sciezka)
    fps = analyze.ulamek_fps(analyze.strumien_wideo(dane))
    sceny = detect(str(sciezka), AdaptiveDetector())
    ciecia = [round(float(p.frame_num / fps), 3) for p, _ in sceny if p.frame_num > 0]
    return [0.0] + ciecia


def odsetek_na_uderzeniach(ciecia: list[float], uderzenia: list[float]) -> float | None:
    if len(uderzenia) < 2:
        return None
    punkty = list(uderzenia) + [(a + b) / 2 for a, b in zip(uderzenia, uderzenia[1:])]
    punkty = np.array(punkty)
    wlasciwe = [t for t in ciecia if t > 0]
    if not wlasciwe:
        return None
    trafione = sum(1 for t in wlasciwe if float(np.min(np.abs(punkty - t))) <= TOLERANCJA_UDERZENIA_S)
    return trafione / len(wlasciwe)


def klatka_z_wideo(uchwyt, numer: int):
    uchwyt.set(cv2.CAP_PROP_POS_FRAMES, max(0, numer))
    ok, klatka = uchwyt.read()
    return klatka if ok else None


def miniatura(klatka, wysokosc: int):
    if klatka is None:
        return np.zeros((wysokosc, int(wysokosc * 9 / 16), 3), dtype=np.uint8)
    h, w = klatka.shape[:2]
    return cv2.resize(klatka, (max(1, int(round(w * wysokosc / h))), wysokosc), interpolation=cv2.INTER_AREA)


def arkusze(sciezka: Path, nazwa: str, detektor: str, ciecia_s: list[float], fps: float) -> list[str]:
    uchwyt = cv2.VideoCapture(str(sciezka))
    liczba_klatek = int(uchwyt.get(cv2.CAP_PROP_FRAME_COUNT))
    poczatki = [int(round(t * fps)) for t in ciecia_s]
    konce = poczatki[1:] + [liczba_klatek]
    wiersze = []
    for numer, (a, b) in enumerate(zip(poczatki, konce)):
        ostatnia = max(a, b - 1)
        klatki = [klatka_z_wideo(uchwyt, x) for x in (a, (a + ostatnia) // 2, ostatnia)]
        obrazy = [miniatura(k, WYSOKOSC_MINIATURY) for k in klatki]
        opis = np.zeros((WYSOKOSC_MINIATURY, 150, 3), dtype=np.uint8)
        cv2.putText(opis, f"#{numer}", (6, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(opis, f"{a / fps:.2f} s", (6, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(opis, f"{(b - a)} kl", (6, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        wiersze.append(np.hstack([opis] + obrazy))
    uchwyt.release()
    if not wiersze:
        return []
    na_arkusz = max(1, LIMIT_ARKUSZA_PX // (WYSOKOSC_MINIATURY + 2))
    sciezki = []
    for indeks in range(0, len(wiersze), na_arkusz):
        porcja = wiersze[indeks : indeks + na_arkusz]
        szerokosc = max(w.shape[1] for w in porcja)
        uzupelnione = [
            np.hstack([w, np.zeros((w.shape[0], szerokosc - w.shape[1], 3), dtype=np.uint8)]) if w.shape[1] < szerokosc else w
            for w in porcja
        ]
        przerwa = np.full((2, szerokosc, 3), 90, dtype=np.uint8)
        obraz = np.vstack([element for w in uzupelnione for element in (w, przerwa)])
        cel = KATALOG_OUTPUTS / f"arkusz_{nazwa}_{detektor}_{indeks // na_arkusz + 1}.png"
        ok, bufor = cv2.imencode(".png", obraz)
        if ok:
            cel.write_bytes(bufor.tobytes())
            sciezki.append(cel.name)
    return sciezki


def sekcja_b(katalog_probek: Path) -> dict:
    pliki = sorted(p for p in katalog_probek.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".m4v", ".mkv", ".webm"}) if katalog_probek.is_dir() else []
    if not pliki:
        print(f"B pominieta: brak plikow w {katalog_probek}")
        return {"pominieta": True, "powod": f"brak plikow w {katalog_probek}"}
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    wyniki = {"wzory": []}
    for sciezka in pliki:
        meta = analyze.metadane(sciezka)
        fps = meta["fps"]
        czas_rytmu = None
        uderzenia = []
        if meta["ma_dzwiek"]:
            start = time.monotonic()
            tempo, uderzenia = analyze.analizuj_rytm(sciezka)
            czas_rytmu = round(time.monotonic() - start, 2)
        else:
            tempo = None
        wpis = {"plik": sciezka.name, "czas_s": meta["czas_s"], "fps": fps, "tempo": tempo, "uderzenia": len(uderzenia), "czas_rytmu_s": czas_rytmu, "detektory": {}}
        for detektor, funkcja in (("content", analyze.wykryj_ciecia), ("adaptive", ciecia_adaptive)):
            start = time.monotonic()
            ciecia = funkcja(sciezka)
            czas = round(time.monotonic() - start, 2)
            dlugosci = [b - a for a, b in zip(ciecia, ciecia[1:] + [meta["czas_s"]])]
            odsetek = odsetek_na_uderzeniach(ciecia, uderzenia)
            pliki_arkuszy = arkusze(sciezka, sciezka.stem, detektor, ciecia, fps)
            wpis["detektory"][detektor] = {
                "liczba_ciec": len(ciecia) - 1,
                "mediana_dlugosci_ujecia_s": round(statistics.median(dlugosci), 3),
                "odsetek_ciec_na_uderzeniach": None if odsetek is None else round(odsetek, 3),
                "czas_analizy_s": czas,
                "arkusze": pliki_arkuszy,
            }
            print(f"B {sciezka.name} {detektor}: {wpis['detektory'][detektor]}")
        wyniki["wzory"].append(wpis)
        zapisz_wyniki_calosc(wyniki_b=wyniki)
    return wyniki


WYNIKI_CALOSC: dict = {}


def zapisz_wyniki_calosc(wyniki_a: dict | None = None, wyniki_b: dict | None = None) -> None:
    if wyniki_a is not None:
        WYNIKI_CALOSC["A"] = wyniki_a
    if wyniki_b is not None:
        WYNIKI_CALOSC["B"] = wyniki_b
    zapisz_wyniki(WYNIKI_CALOSC)


def main() -> int:
    katalog_probek = Path(sys.argv[1]) if len(sys.argv) > 1 else DOMYSLNY_KATALOG_PROBEK
    wyniki_a = sekcja_a()
    zapisz_wyniki_calosc(wyniki_a=wyniki_a)
    print("A progi:", wyniki_a["progi"], "czulosc", wyniki_a["czulosc_srednia"], "precyzja", wyniki_a["precyzja_srednia"],
          "blad tempa maks %", wyniki_a["blad_tempa_maks_proc"], "pomylki oktawy", wyniki_a["pomylki_oktawy"])
    wyniki_b = sekcja_b(katalog_probek)
    zapisz_wyniki_calosc(wyniki_b=wyniki_b)
    zaliczone = all(wyniki_a["progi"].values())
    print("WYNIK A:", "ZALICZONA" if zaliczone else "NIEZALICZONA")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
