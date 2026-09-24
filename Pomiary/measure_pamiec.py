import ctypes
import json
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar zadania 4.5 (pamiec analizy utworu, PLAN_EDITY_4_MUZYKA.md).
# Kazdy pomiar pamieci uruchamia ten sam plik jako osobny podproces z flaga --worker-*:
#   podproces liczy swoj wlasny szczyt working set (Windows: GetProcessMemoryInfo na
#   GetCurrentProcess, Linux: resource.getrusage(RUSAGE_SELF).ru_maxrss) i drukuje JSON
#   w ostatniej linii stdout. Dzieki temu kazdy plik i render maja wlasny, nieskazony
#   podproces (RUSAGE_CHILDREN w procesie rodzica sumowalby szczyty kolejnych podprocesow).
# Sekcja A: kazdy plik z dane/muzyka/ i dane/wzory/*.mp4 -> tempo i uderzenia stara droga
#   (beat_track bez bpm, jak przed zadaniem 4.5) wobec nowej (analyze.analizuj_dzwiek),
#   plus szczyt pamieci nowej drogi.
# Sekcja B: szczyt pamieci pelnego renderu 1080x1920 z nakladka, plansza i znakiem,
#   indeksujac od zera kopie biblioteki dane/muzyka/ w katalogu tymczasowym.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_pamiec.json"
SKRYPT = Path(__file__).resolve()

PROG_SZCZYT_ANALIZY_MB = 1024.0
PROG_SZCZYT_RENDERU_MB = 2048.0

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


class LiczbnikiPamieciWindows(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def szczyt_wlasny_bajty() -> int:
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(LiczbnikiPamieciWindows), ctypes.c_ulong]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        liczniki = LiczbnikiPamieciWindows()
        liczniki.cb = ctypes.sizeof(LiczbnikiPamieciWindows)
        psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(liczniki), liczniki.cb)
        return liczniki.PeakWorkingSetSize
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def analiza_stara_droga(sciezka) -> dict | None:
    import librosa
    import numpy

    import analyze

    sciezka = Path(sciezka)
    with TemporaryDirectory() as katalog:
        wav = Path(katalog) / "dzwiek.wav"
        try:
            analyze.zdekoduj_do_wav(sciezka, wav)
        except analyze.BladAnalizy:
            return None
        if not wav.exists() or wav.stat().st_size < 1000:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sygnal, sr = librosa.load(str(wav), sr=analyze.CZESTOTLIWOSC_ANALIZY, mono=True)
    if len(sygnal) < sr:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obwiednia_rytmu = librosa.onset.onset_strength(y=sygnal, sr=sr, hop_length=analyze.KROK_ROZKLADU)
        tempo, pozycje_uderzen = librosa.beat.beat_track(
            onset_envelope=obwiednia_rytmu, sr=sr, hop_length=analyze.KROK_ROZKLADU, units="time",
            start_bpm=analyze.START_BPM, trim=False,
        )
        uderzenia_s = analyze.doprecyzuj_uderzenia(librosa, sygnal, sr, [float(t) for t in pozycje_uderzen])
    if len(uderzenia_s) < 2:
        return {"tempo_bpm": None, "uderzenia_s": []}
    return {"tempo_bpm": round(float(numpy.asarray(tempo).reshape(-1)[0]), 1), "uderzenia_s": uderzenia_s}


def worker_analiza(sciezka: str, droga: str) -> None:
    import analyze

    if droga == "nowa":
        dzwiek = analyze.analizuj_dzwiek(sciezka)
        wynik = {"tempo_bpm": dzwiek["tempo_bpm"], "uderzenia_s": dzwiek["uderzenia_s"]} if dzwiek else None
    else:
        wynik = analiza_stara_droga(sciezka)
    print(json.dumps({"wynik": wynik, "szczyt_bajty": szczyt_wlasny_bajty()}))


def worker_render(argumenty_json: str) -> None:
    import render

    argumenty = json.loads(argumenty_json)
    render.renderuj(
        Path(argumenty["wzor"]), Path(argumenty["projekt"]), None, Path(argumenty["wyjscie"]),
        szerokosc=argumenty["szerokosc"], wysokosc=argumenty["wysokosc"], fps=argumenty["fps"],
        limit_mb=argumenty["limit_mb"], muzyka=Path(argumenty["muzyka"]),
        nakladka=Path(argumenty["nakladka"]) if argumenty.get("nakladka") else None,
        plansza=Path(argumenty["plansza"]) if argumenty.get("plansza") else None,
        znak=Path(argumenty["znak"]) if argumenty.get("znak") else None,
    )
    print(json.dumps({"szczyt_bajty": szczyt_wlasny_bajty()}))


def uruchom_worker(argumenty: list[str]) -> dict:
    wynik = subprocess.run(
        [sys.executable, str(SKRYPT), *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    if wynik.returncode != 0:
        ostatnia_linia = wynik.stderr.strip().splitlines()[-1] if wynik.stderr.strip() else ""
        raise RuntimeError(f"worker zakonczyl sie kodem {wynik.returncode}: {ostatnia_linia}")
    return json.loads(wynik.stdout.strip().splitlines()[-1])


def znajdz_pliki_do_sekcji_a() -> list[Path]:
    import music

    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    katalog_wzorow = KATALOG_REPO / "dane" / "wzory"
    pliki = []
    if katalog_muzyki.is_dir():
        pliki += music.pliki_muzyki(katalog_muzyki)
    if katalog_wzorow.is_dir():
        pliki += sorted(p for p in katalog_wzorow.glob("*.mp4") if p.is_file())
    return pliki


def sekcja_a() -> dict:
    pliki = znajdz_pliki_do_sekcji_a()
    if not pliki:
        print("A pominieta: brak dane/muzyka i dane/wzory/*.mp4")
        return {"pominieta": True, "powod": "brak dane/muzyka i dane/wzory/*.mp4"}

    wpisy = []
    for sciezka in pliki:
        nowy = uruchom_worker(["--worker-analiza", str(sciezka), "nowa"])
        stary = uruchom_worker(["--worker-analiza", str(sciezka), "stara"])
        wpis = {
            "plik": sciezka.name,
            "tempo_bpm_nowa": nowy["wynik"]["tempo_bpm"] if nowy["wynik"] else None,
            "tempo_bpm_stara": stary["wynik"]["tempo_bpm"] if stary["wynik"] else None,
            "liczba_uderzen_nowa": len(nowy["wynik"]["uderzenia_s"]) if nowy["wynik"] else 0,
            "liczba_uderzen_stara": len(stary["wynik"]["uderzenia_s"]) if stary["wynik"] else 0,
            "identyczne": nowy["wynik"] == stary["wynik"],
            "szczyt_analizy_nowa_mb": round(nowy["szczyt_bajty"] / (1024 * 1024), 1),
            "szczyt_analizy_stara_mb": round(stary["szczyt_bajty"] / (1024 * 1024), 1),
        }
        wpisy.append(wpis)
        print(f"A {sciezka.name}: identyczne={wpis['identyczne']} szczyt nowa={wpis['szczyt_analizy_nowa_mb']} MB stara={wpis['szczyt_analizy_stara_mb']} MB")

    szczyt_maks_mb = max(w["szczyt_analizy_nowa_mb"] for w in wpisy)
    wyniki = {"pliki": wpisy, "szczyt_analizy_maks_mb": szczyt_maks_mb}
    wyniki["progi"] = {
        "tempo_i_uderzenia_identyczne": all(w["identyczne"] for w in wpisy),
        "szczyt_do_1gb": szczyt_maks_mb <= PROG_SZCZYT_ANALIZY_MB,
    }
    print(f"A: {wyniki['progi']}, szczyt maks {szczyt_maks_mb} MB")
    return wyniki


def zbuduj_materialy(katalog_materialow: Path) -> None:
    import generuj

    katalog_materialow.mkdir(parents=True, exist_ok=True)
    for i in range(8):
        generuj.zdjecie_testowe(katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))


def znajdz_plansze() -> Path | None:
    kandydat = KATALOG_REPO / "dane" / "plansze"
    if kandydat.is_dir():
        pliki = sorted(p for p in kandydat.glob("domyslna.*") if p.is_file())
        if pliki:
            return pliki[0]
    promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if promocyjne.is_dir():
        for p in sorted(promocyjne.iterdir()):
            if p.suffix.lower() in (".jpg", ".jpeg"):
                return p
    return None


def znajdz_nakladke(katalog_tymczasowy: Path) -> Path:
    import generuj

    kandydat = KATALOG_REPO / "dane" / "nakladki" / "domyslna.mp4"
    if kandydat.is_file():
        return kandydat
    sciezka = katalog_tymczasowy / "nakladka.mp4"
    generuj.nakladka_testowa(sciezka, 15.0, "alfa")
    return sciezka


def znajdz_znak() -> Path | None:
    sciezka = KATALOG_REPO / "dane" / "promocyjne" / "1993supply_watermark.png"
    return sciezka if sciezka.is_file() else None


def wybierz_wzor() -> Path | None:
    katalog_wzorow = KATALOG_REPO / "dane" / "wzory"
    if not katalog_wzorow.is_dir():
        return None
    pliki = sorted(katalog_wzorow.glob("*.mp4"))
    return pliki[0] if pliki else None


def przygotuj_wzor_json(sciezka_zrodlowa: Path, cel_katalog: Path) -> Path:
    import analyze

    nazwa = sciezka_zrodlowa.stem
    cache = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    dane = None
    if cache.is_file():
        dane = json.loads(cache.read_text(encoding="utf-8"))
        if dane.get("wersja") != analyze.WERSJA_WZORU:
            dane = None
    if dane is None:
        dane = analyze.analizuj_wzor(sciezka_zrodlowa, nazwa)
        KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    cel = cel_katalog / "wzor.json"
    cel.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    return cel


def sekcja_b() -> dict:
    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    sciezka_wzoru = wybierz_wzor()
    if not katalog_muzyki.is_dir() or sciezka_wzoru is None:
        print("B pominieta: brak dane/muzyka lub dane/wzory/*.mp4")
        return {"pominieta": True, "powod": "brak dane/muzyka lub dane/wzory/*.mp4"}

    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        muzyka_kopia = katalog_tymczasowy / "muzyka"
        shutil.copytree(katalog_muzyki, muzyka_kopia, ignore=shutil.ignore_patterns("indeks.json"))

        katalog_projektu = katalog_tymczasowy / "projekt"
        zbuduj_materialy(katalog_projektu / "materialy")
        wzor_json = przygotuj_wzor_json(sciezka_wzoru, katalog_tymczasowy)
        nakladka = znajdz_nakladke(katalog_tymczasowy)
        plansza = znajdz_plansze()
        znak = znajdz_znak()
        wyjscie = katalog_tymczasowy / "wynik.mp4"

        argumenty = {
            "wzor": str(wzor_json), "projekt": str(katalog_projektu), "wyjscie": str(wyjscie),
            "szerokosc": 1080, "wysokosc": 1920, "fps": 30, "limit_mb": 200,
            "muzyka": str(muzyka_kopia),
            "nakladka": str(nakladka) if nakladka else None,
            "plansza": str(plansza) if plansza else None,
            "znak": str(znak) if znak else None,
        }
        try:
            wynik = uruchom_worker(["--worker-render", json.dumps(argumenty)])
        except RuntimeError as blad:
            print(f"B: BLAD {blad}")
            return {"blad": str(blad)}

        szczyt_mb = round(wynik["szczyt_bajty"] / (1024 * 1024), 1)
        wyniki = {
            "wzor": sciezka_wzoru.stem,
            "nakladka": Path(nakladka).name if nakladka else None,
            "plansza": Path(plansza).name if plansza else None,
            "znak": znak is not None,
            "szczyt_renderu_mb": szczyt_mb,
        }
    wyniki["progi"] = {"szczyt_do_2gb": szczyt_mb <= PROG_SZCZYT_RENDERU_MB}
    print(f"B: {wyniki['progi']}, szczyt {szczyt_mb} MB")
    return wyniki


def main() -> int:
    wyniki_a = sekcja_a()
    zapisz_sekcje("A", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("B", wyniki_b)

    zaliczone = True
    if not wyniki_a.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_a["progi"].values())
    if not wyniki_b.get("pominieta") and "blad" not in wyniki_b:
        zaliczone = zaliczone and all(wyniki_b["progi"].values())
    print("WYNIK:", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker-analiza":
        worker_analiza(sys.argv[2], sys.argv[3])
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker-render":
        worker_render(sys.argv[2])
        sys.exit(0)
    sys.exit(main())
