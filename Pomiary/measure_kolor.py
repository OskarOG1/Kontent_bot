import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 5 (kolor).
# Sekcja A (syntetyczna): wzor dwusekcyjny (hak cieply, montaz niebieski, plansza pominieta
#   ze statystyk), materialy szare z generatora. Renderuje przy sile 0, 0.6 i 1.0, mierzy
#   DeltaE76 miedzy srednim Lab wyrenderowanego ujecia a celem tej sekcji. Robi to dwa razy:
#   z prawdziwymi "sekcje" (cel na sekcje) i bez nich (cel z calosci, kolor.cel_sekcji(..., None, ...)).
# Sekcja B (prawdziwe wzory z dane/wzory/*.mp4, cache analizy w outputs/wzor_<nazwa>.json):
#   ta sama miara DeltaE na probce materialow z bloku WSPOLNE (8 zdjec, 4 nagrania, 2 zdjecia
#   bez tla z prawdziwa alfa) i prawdziwej muzyce, DeltaE liczone z klatki tuz po starcie
#   i z klatki tuz po drop_s z podsumowania renderu. Narzut czasu renderu (sila 0.6 wobec 0)
#   liczony z czasu procesora ffmpeg (-benchmark, linia "bench:"), jedno porownanie na wzor.
#   Czas analizy z probkowaniem i bez (najwiekszy plik wzoru, mediana z 5 przebiegow na przemian,
#   prog oceniany tylko gdy rozrzut przebiegow bazowych ponizej 20%, inaczej "niepewny") -
#   doprecyzowanie wlasciciela 2026-09-24, patrz ROZWOJ.md.
# Sekcja C: sprawdza, ze arkusze porownawcze z sekcji B (outputs/porownanie_kolor_<wzor>_<sila>.png)
#   powstaly dla kazdego wzoru i kazdej z sil 0, 0.6, 1.0.
# Sekcja D (zadanie 5.6, niebo bez przebarwienia): trzy jasne zdjecia z dane/zdjęcia/ przygotowane
#   jak w renderze, LUT przy sile 0.6 do celu montazu wzoru 0915 (ten wzor lezy na serwerze),
#   nalozony przez ffmpeg lut3d bez ochrony jasnych partii i z nia. Miara: srednie a/b pikseli,
#   ktore w oryginale maja L > 70. Uruchamiana tez osobno: python Pomiary/measure_kolor.py --sekcja D.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import kolor  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_kolor.json"

PROG_NARZUTU_PROBKOWANIA = 1.3
PROG_ROZRZUTU_BAZOWEGO = 0.20
ROZSZERZENIA_WZOROW = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}

# Sekcja D: pierwsze dwa zdjecia (tlum z flagami, biala sciana) maja twardy prog chromy,
# trzecie (mgla) tylko musi sie poprawic.
WZOR_NIEBA = "0915"
ZDJECIA_NIEBA = [
    "8d75cf40c8d7a3eaceb27b9dcf6083cd.jpg",
    "2402ce4e43187bb07ec41db88ff06fad.jpg",
    "b80a5cedb15e50edd08a59328da10190.jpg",
]
PROG_JASNOSCI_NIEBA = 70.0
PROG_CHROMY_JASNYCH = 3.0
SILA_NIEBA = 0.6

# Zabezpieczenie przed utrata postepu przy awarii (sekcja B trwa dlugo):
# wyniki kazdego wzoru i kazdego przebiegu probkowania trafiaja na dysk od razu,
# nie dopiero na koncu calej sekcji. Ponowne uruchomienie wznawia z tych plikow.
PLIK_CZESCIOWE_B = KATALOG_OUTPUTS / "pomiar_kolor_b_czesciowe.json"
PLIK_CZESCIOWE_PROBKOWANIE = KATALOG_OUTPUTS / "pomiar_kolor_probkowanie_czesciowe.json"


def wczytaj_czesciowe(plik: Path) -> dict:
    if plik.is_file():
        try:
            return json.loads(plik.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def zapisz_czesciowe(plik: Path, dane: dict) -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    tymczasowy = plik.with_name(plik.name + ".tmp")
    tymczasowy.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tymczasowy, plik)

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def delta_e76(lab1, lab2) -> float:
    return float(np.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(lab1, lab2))))


def srednia_lab(klatka: np.ndarray) -> list:
    return [float(x) for x in kolor.rgb_do_lab(klatka).reshape(-1, 3).mean(axis=0)]


def zdekoduj_klatke(sciezka: Path, czas_s: float, katalog_tymczasowy: Path) -> np.ndarray:
    wymiary = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    szerokosc, wysokosc = (int(x) for x in wymiary.stdout.decode().strip().split(","))
    surowa = katalog_tymczasowy / f"klatka_{czas_s:.3f}.raw"
    wynik = subprocess.run(
        [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", f"{max(0.0, czas_s):.6f}", "-i", str(sciezka),
            "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", str(surowa),
        ],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
    return np.fromfile(surowa, dtype=np.uint8).reshape(wysokosc, szerokosc, 3)


def zbieraj_czas_cpu(akumulator_s: list):
    def podmieniony(argumenty, katalog=None):
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "info", "-benchmark", *argumenty],
            stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog,
        )
        if wynik.returncode != 0:
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
        dopasowanie = re.search(r"bench:\s*utime=([\d.]+)s\s*stime=([\d.]+)s", wynik.stderr.decode("utf-8", errors="replace"))
        if dopasowanie:
            akumulator_s[0] += float(dopasowanie.group(1)) + float(dopasowanie.group(2))
    return podmieniony


def wzor_syntetyczny_dwie_sekcje() -> dict:
    return {
        "ciecia_uderzenia": [0.0, 1.0, 2.0, 3.0],
        "koniec_uderzenia": 4.0,
        "ciecia_s": [0.0],
        "zrodlo": {"czas_s": 4.0},
        "sekcje": {"drop_s": 2.0, "drop_ujecie": 2, "koniec_haka_uderzenia": None},
        "kolorystyka": {
            "probki_na_s": 10,
            "ujecia": [
                {"lab_srednia": [55.0, 8.0, 35.0], "lab_odchylenie": [12.0, 5.0, 5.0], "probki": 10},
                {"lab_srednia": [55.0, 8.0, 35.0], "lab_odchylenie": [12.0, 5.0, 5.0], "probki": 10},
                {"lab_srednia": [35.0, -5.0, -35.0], "lab_odchylenie": [12.0, 5.0, 5.0], "probki": 10},
                {"lab_srednia": [35.0, -5.0, -35.0], "lab_odchylenie": [12.0, 5.0, 5.0], "probki": 10},
            ],
        },
    }


def zbuduj_projekt_szary(katalog_projektu: Path) -> None:
    katalog_materialow = katalog_projektu / "materialy"
    katalog_materialow.mkdir(parents=True)
    for i in range(4):
        generuj.zdjecie_testowe(katalog_materialow / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=(128, 128, 128))


def zmierz_sekcja_a_wariant(wzor: dict, z_sekcjami: bool, katalog_tymczasowy: Path) -> dict:
    katalog_wariantu = katalog_tymczasowy / ("sekcje" if z_sekcjami else "calosc")
    katalog_wariantu.mkdir()
    projekt = katalog_wariantu / "projekt"
    zbuduj_projekt_szary(projekt)
    utwor = katalog_tymczasowy / "klik.wav"
    if not utwor.exists():
        generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)

    sekcje_do_celu = wzor["sekcje"] if z_sekcjami else None
    wzor_do_renderu = dict(wzor, sekcje=sekcje_do_celu)
    wzor_json = katalog_wariantu / "wzor.json"
    wzor_json.write_text(json.dumps(wzor_do_renderu), encoding="utf-8")

    cel_hak = kolor.cel_sekcji(wzor["kolorystyka"], sekcje_do_celu, numer_wzoru=0)
    cel_montaz = kolor.cel_sekcji(wzor["kolorystyka"], sekcje_do_celu, numer_wzoru=2)

    _, uderzenia = analyze.analizuj_rytm(utwor)
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    plan = render.plan_ujec(wzor_do_renderu, uderzenia, material_zastepczy, fps=30)

    wyniki_sily = {}
    for sila in (0.0, 0.6, 1.0):
        wyjscie = katalog_wariantu / f"wynik_{sila}.mp4"
        render.renderuj(wzor_json, projekt, utwor, wyjscie, szerokosc=270, wysokosc=480, fps=30, limit_mb=50, sila_koloru=sila)
        klatka_hak = zdekoduj_klatke(wyjscie, (plan["ujecia"][0]["klatka_od"] + 1) / 30, katalog_wariantu)
        klatka_montaz = zdekoduj_klatke(wyjscie, (plan["ujecia"][2]["klatka_od"] + 1) / 30, katalog_wariantu)
        wyniki_sily[str(sila)] = {
            "delta_e_hak": round(delta_e76(srednia_lab(klatka_hak), cel_hak["lab_srednia"]), 2),
            "delta_e_montaz": round(delta_e76(srednia_lab(klatka_montaz), cel_montaz["lab_srednia"]), 2),
        }
        wyjscie.unlink(missing_ok=True)
        wyjscie.with_suffix(".json").unlink(missing_ok=True)
    return wyniki_sily


def sekcja_a() -> dict:
    wzor = wzor_syntetyczny_dwie_sekcje()
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        wynik_sekcje = zmierz_sekcja_a_wariant(wzor, True, katalog_tymczasowy)
        wynik_calosc = zmierz_sekcja_a_wariant(wzor, False, katalog_tymczasowy)

    poprawa = (
        wynik_sekcje["0.6"]["delta_e_hak"] < wynik_sekcje["0.0"]["delta_e_hak"]
        and wynik_sekcje["0.6"]["delta_e_montaz"] < wynik_sekcje["0.0"]["delta_e_montaz"]
    )
    wyniki = {"cel_na_sekcje": wynik_sekcje, "cel_z_calosci": wynik_calosc}
    wyniki["progi"] = {"sila_0_6_lepsza_niz_0": poprawa}
    print(f"A: {wyniki['progi']}")
    print(f"A cel na sekcje: {wynik_sekcje}")
    print(f"A cel z calosci: {wynik_calosc}")
    return wyniki


def znajdz_wzory() -> list:
    katalog = KATALOG_REPO / "dane" / "wzory"
    if not katalog.is_dir():
        return []
    return sorted(p for p in katalog.glob("*") if p.is_file() and p.suffix.lower() in ROZSZERZENIA_WZOROW)


def znajdz_muzyke() -> Path | None:
    katalog = KATALOG_REPO / "dane" / "muzyka"
    return katalog if katalog.is_dir() and any(katalog.iterdir()) else None


def dowiaz_lub_kopiuj(zrodlo: Path, cel: Path) -> None:
    try:
        os.link(zrodlo, cel)
    except OSError:
        shutil.copy(zrodlo, cel)


def zbuduj_probke_materialow(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    indeks = 1
    for plik in sorted((KATALOG_REPO / "dane" / "zdjęcia").glob("*"))[:8]:
        dowiaz_lub_kopiuj(plik, katalog_materialow / f"{indeks:010d}_z{plik.suffix.lower()}")
        indeks += 1
    for plik in sorted((KATALOG_REPO / "dane" / "nagrania").glob("*"))[:4]:
        dowiaz_lub_kopiuj(plik, katalog_materialow / f"{indeks:010d}_n{plik.suffix.lower()}")
        indeks += 1
    dodane_alfa = 0
    for plik in sorted((KATALOG_REPO / "dane" / "zdjęcia_bez_tła").glob("*")):
        if dodane_alfa >= 2:
            break
        try:
            if not plik.is_file() or not render.ma_alfa_z_pil(plik):
                continue
        except Exception:
            continue
        dowiaz_lub_kopiuj(plik, katalog_materialow / f"{indeks:010d}_t{plik.suffix.lower()}")
        indeks += 1
        dodane_alfa += 1


def wczytaj_lub_przeanalizuj_wzor(sciezka: Path) -> dict:
    nazwa = sciezka.stem
    cel = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    if cel.is_file():
        dane = json.loads(cel.read_text(encoding="utf-8"))
        if dane.get("wersja") == analyze.WERSJA_WZORU:
            print(f"{nazwa}: wzor z cache ({cel.name})")
            return dane
    start = time.monotonic()
    dane = analyze.analizuj_wzor(sciezka, nazwa)
    czas = time.monotonic() - start
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{nazwa}: analiza wzoru w {czas:.1f} s")
    return dane


def przetworz_wzor_b(sciezka_wzoru: Path, projekt: Path, muzyka: Path, katalog_tymczasowy: Path) -> dict:
    nazwa = sciezka_wzoru.stem
    wzor = wczytaj_lub_przeanalizuj_wzor(sciezka_wzoru)
    wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    kolorystyka = wzor.get("kolorystyka")
    sekcje = wzor.get("sekcje")

    wyniki_sily = {}
    cpu_0 = cpu_06 = None
    for sila in (0.0, 0.6, 1.0):
        wyjscie = katalog_tymczasowy / f"{nazwa}_{sila}.mp4"
        if sila in (0.0, 0.6):
            akumulator = [0.0]
            oryginalny = render.uruchom_ffmpeg
            render.uruchom_ffmpeg = zbieraj_czas_cpu(akumulator)
            try:
                podsumowanie = render.renderuj(
                    wzor_json, projekt, None, wyjscie, szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200,
                    muzyka=muzyka, sila_koloru=sila,
                )
            finally:
                render.uruchom_ffmpeg = oryginalny
            if sila == 0.0:
                cpu_0 = akumulator[0]
            else:
                cpu_06 = akumulator[0]
        else:
            podsumowanie = render.renderuj(
                wzor_json, projekt, None, wyjscie, szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200,
                muzyka=muzyka, sila_koloru=sila,
            )

        cel_arkusza = KATALOG_OUTPUTS / f"porownanie_kolor_{nazwa}_{sila}.png"
        arkusz.arkusz_porownawczy(sciezka_wzoru, wyjscie, cel_arkusza)
        wpis = {"arkusz": cel_arkusza.name}

        drop_s = podsumowanie.get("drop_s")
        if kolorystyka is not None and sekcje is not None and drop_s is not None:
            klatka_hak = zdekoduj_klatke(wyjscie, 0.2, katalog_tymczasowy)
            klatka_montaz = zdekoduj_klatke(wyjscie, drop_s + 0.2, katalog_tymczasowy)
            cel_hak = kolor.cel_sekcji(kolorystyka, sekcje, numer_wzoru=0)
            cel_montaz = kolor.cel_sekcji(kolorystyka, sekcje, numer_wzoru=sekcje["drop_ujecie"])
            wpis["delta_e_hak"] = round(delta_e76(srednia_lab(klatka_hak), cel_hak["lab_srednia"]), 2)
            wpis["delta_e_montaz"] = round(delta_e76(srednia_lab(klatka_montaz), cel_montaz["lab_srednia"]), 2)
        wyniki_sily[str(sila)] = wpis
        wyjscie.unlink(missing_ok=True)
        wyjscie.with_suffix(".json").unlink(missing_ok=True)

    wynik = {"sily": wyniki_sily}
    wynik["narzut_render_procent"] = round((cpu_06 - cpu_0) / cpu_0 * 100, 1) if cpu_0 else None
    return wynik


class ProcesAtrapa:
    def wait(self, timeout=None):
        return 1

    def poll(self):
        return 1

    def kill(self):
        pass


def zmierz_czas_probkowania(sciezka_wzoru: Path) -> dict:
    stan = wczytaj_czesciowe(PLIK_CZESCIOWE_PROBKOWANIE)
    if stan.get("wzor") != sciezka_wzoru.stem:
        stan = {"wzor": sciezka_wzoru.stem, "czasy_z_probkowaniem_s": [], "czasy_bez_probkowania_s": []}
    czasy_z = stan["czasy_z_probkowaniem_s"]
    czasy_bez = stan["czasy_bez_probkowania_s"]

    oryginalny = analyze.uruchom_probkowanie
    while len(czasy_z) < 5 or len(czasy_bez) < 5:
        if len(czasy_z) <= len(czasy_bez):
            start = time.monotonic()
            analyze.analizuj_wzor(sciezka_wzoru, "pomiar_z")
            czasy_z.append(round(time.monotonic() - start, 2))
        else:
            analyze.uruchom_probkowanie = lambda sciezka, cel: ProcesAtrapa()
            try:
                start = time.monotonic()
                analyze.analizuj_wzor(sciezka_wzoru, "pomiar_bez")
                czasy_bez.append(round(time.monotonic() - start, 2))
            finally:
                analyze.uruchom_probkowanie = oryginalny
        zapisz_czesciowe(PLIK_CZESCIOWE_PROBKOWANIE, stan)
        print(f"  probkowanie {sciezka_wzoru.stem}: z={len(czasy_z)}/5, bez={len(czasy_bez)}/5")

    mediana_z = statistics.median(czasy_z)
    mediana_bez = statistics.median(czasy_bez)
    rozrzut_bez = (max(czasy_bez) - min(czasy_bez)) / mediana_bez if mediana_bez else 1.0
    if rozrzut_bez < PROG_ROZRZUTU_BAZOWEGO:
        ocena = "w progu" if mediana_z <= PROG_NARZUTU_PROBKOWANIA * mediana_bez else "poza progiem"
    else:
        ocena = "niepewny"
    return {
        "wzor": sciezka_wzoru.stem,
        "czasy_z_probkowaniem_s": [round(c, 2) for c in czasy_z],
        "czasy_bez_probkowania_s": [round(c, 2) for c in czasy_bez],
        "mediana_z_s": round(mediana_z, 2),
        "mediana_bez_s": round(mediana_bez, 2),
        "narzut_wobec_mediany_procent": round((mediana_z / mediana_bez - 1) * 100, 1) if mediana_bez else None,
        "rozrzut_bazowych_procent": round(rozrzut_bez * 100, 1),
        "ocena_progu": ocena,
    }


def sekcja_b() -> dict:
    wzory = znajdz_wzory()
    muzyka = znajdz_muzyke()
    if not wzory or muzyka is None:
        print("B pominieta: brak dane/wzory/*.mp4 lub dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/wzory lub dane/muzyka"}

    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        projekt = katalog_tymczasowy / "projekt"
        zbuduj_probke_materialow(projekt / "materialy")

        wyniki_wzorow = wczytaj_czesciowe(PLIK_CZESCIOWE_B)
        for sciezka in wzory:
            if sciezka.stem in wyniki_wzorow:
                print(f"B {sciezka.stem}: z checkpointu ({PLIK_CZESCIOWE_B.name}), pomijam ponowny render")
                continue
            wynik = przetworz_wzor_b(sciezka, projekt, muzyka, katalog_tymczasowy)
            wyniki_wzorow[sciezka.stem] = wynik
            zapisz_czesciowe(PLIK_CZESCIOWE_B, wyniki_wzorow)
            print(f"B {sciezka.stem}: {wynik}")

        najwiekszy = max(wzory, key=lambda p: p.stat().st_size)
        wynik_probkowania = zmierz_czas_probkowania(najwiekszy)
        print(f"B (czas probkowania na {najwiekszy.stem}): {wynik_probkowania}")

    progi_delta = []
    for wynik in wyniki_wzorow.values():
        sily = wynik["sily"]
        if "delta_e_hak" in sily.get("0.0", {}) and "delta_e_hak" in sily.get("0.6", {}):
            progi_delta.append(sily["0.6"]["delta_e_hak"] < sily["0.0"]["delta_e_hak"])
            progi_delta.append(sily["0.6"]["delta_e_montaz"] < sily["0.0"]["delta_e_montaz"])

    wyniki = {"wzory": wyniki_wzorow, "czas_probkowania": wynik_probkowania}
    wyniki["progi"] = {
        "sila_0_6_lepsza_niz_0_wszedzie": all(progi_delta) if progi_delta else None,
        "probkowanie_w_progu": wynik_probkowania["ocena_progu"] != "poza progiem",
    }
    print(f"B: {wyniki['progi']}")
    return wyniki


def sekcja_c(wyniki_b: dict) -> dict:
    if wyniki_b.get("pominieta"):
        print("C pominieta: brak danych z sekcji B")
        return {"pominieta": True, "powod": "brak danych z sekcji B"}
    arkusze = [wpis["arkusz"] for wynik in wyniki_b["wzory"].values() for wpis in wynik["sily"].values()]
    wszystkie_istnieja = all((KATALOG_OUTPUTS / nazwa).is_file() for nazwa in arkusze)
    wyniki = {"arkusze": arkusze, "progi": {"arkusze_powstaly": bool(arkusze) and wszystkie_istnieja}}
    print(f"C: {wyniki['progi']}, {len(arkusze)} arkuszy")
    return wyniki


def naloz_lut(obraz: np.ndarray, lut: np.ndarray, katalog: Path) -> np.ndarray:
    Image.fromarray(obraz).save(katalog / "niebo_wejscie.png")
    kolor.zapisz_cube(lut, katalog / "niebo.cube")
    render.uruchom_ffmpeg(["-i", "niebo_wejscie.png", "-vf", "lut3d=niebo.cube", "niebo_wyjscie.png"], katalog=katalog)
    with Image.open(katalog / "niebo_wyjscie.png") as wynik:
        return np.array(wynik.convert("RGB"))


def sekcja_d() -> dict:
    wzor_json = KATALOG_OUTPUTS / f"wzor_{WZOR_NIEBA}.json"
    katalog_zdjec = KATALOG_REPO / "dane" / "zdjęcia"
    brakujace = [nazwa for nazwa in ZDJECIA_NIEBA if not (katalog_zdjec / nazwa).is_file()]
    if not wzor_json.is_file() or brakujace:
        print(f"D pominieta: brak {wzor_json.name} albo zdjec {brakujace}")
        return {"pominieta": True, "powod": f"brak {wzor_json.name} albo zdjec z dane/zdjęcia"}

    wzor = json.loads(wzor_json.read_text(encoding="utf-8"))
    sekcje = wzor["sekcje"]
    cel = kolor.cel_sekcji(wzor["kolorystyka"], sekcje, numer_wzoru=sekcje["drop_ujecie"])

    wyniki_zdjec = {}
    wiersze = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        for nazwa in ZDJECIA_NIEBA:
            przygotowane = render.przygotuj_zdjecie(katalog_zdjec / nazwa, katalog_tymczasowy, 0, 1080, 1920)
            obraz = render.obraz_do_statystyk(przygotowane)
            zrodlo = kolor.statystyki_obrazu(obraz)
            maska = kolor.rgb_do_lab(obraz)[..., 0] > PROG_JASNOSCI_NIEBA
            wpis = {"jasnych_pikseli_procent": round(float(maska.mean()) * 100, 1)}
            kafle = [obraz]
            for wersja, ochrona in (("przed", False), ("po", True)):
                lut = kolor.lut_transferu(zrodlo, cel, SILA_NIEBA, ochrona_jasnych=ochrona)
                wynik = naloz_lut(obraz, lut, katalog_tymczasowy)
                a, b = kolor.rgb_do_lab(wynik)[maska][:, 1:].mean(axis=0)
                wpis[wersja] = {"a": round(float(a), 2), "b": round(float(b), 2), "chroma": round(float(np.hypot(a, b)), 2)}
                kafle.append(wynik)
            wyniki_zdjec[nazwa] = wpis
            wiersze.append(np.hstack(kafle))
            print(f"D {nazwa}: {wpis}")

    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    arkusz_nieba = KATALOG_OUTPUTS / "porownanie_kolor_niebo.png"
    Image.fromarray(np.vstack(wiersze)).save(arkusz_nieba)
    wyniki = {
        "wzor": WZOR_NIEBA,
        "sila": SILA_NIEBA,
        "cel_montazu_lab": [round(x, 2) for x in cel["lab_srednia"]],
        "zdjecia": wyniki_zdjec,
        "arkusz": arkusz_nieba.name,
        "progi": {
            "chroma_jasnych_mniejsza_po_poprawce": all(w["po"]["chroma"] < w["przed"]["chroma"] for w in wyniki_zdjec.values()),
            "tlum_i_sciana_chroma_najwyzej_3": all(wyniki_zdjec[n]["po"]["chroma"] <= PROG_CHROMY_JASNYCH for n in ZDJECIA_NIEBA[:2]),
        },
    }
    print(f"D: {wyniki['progi']}")
    return wyniki


def tylko_sekcja_d() -> int:
    WYNIKI_CALOSC.update(wczytaj_czesciowe(PLIK_WYNIKOW))
    wyniki_d = sekcja_d()
    zapisz_sekcje("D", wyniki_d)
    zaliczone = bool(wyniki_d.get("pominieta")) or all(wyniki_d["progi"].values())
    print("WYNIK D:", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


def main() -> int:
    if sys.argv[1:3] == ["--sekcja", "D"]:
        return tylko_sekcja_d()

    wyniki_a = sekcja_a()
    zapisz_sekcje("A", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("B", wyniki_b)
    PLIK_CZESCIOWE_B.unlink(missing_ok=True)
    PLIK_CZESCIOWE_PROBKOWANIE.unlink(missing_ok=True)

    wyniki_c = sekcja_c(wyniki_b)
    zapisz_sekcje("C", wyniki_c)

    wyniki_d = sekcja_d()
    zapisz_sekcje("D", wyniki_d)

    zaliczone = all(wyniki_a["progi"].values())
    if not wyniki_b.get("pominieta"):
        zaliczone = zaliczone and all(v for v in wyniki_b["progi"].values() if v is not None)
        zaliczone = zaliczone and all(wyniki_c["progi"].values())
    if not wyniki_d.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_d["progi"].values())
    print("WYNIK:", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
