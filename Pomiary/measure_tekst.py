import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 6 (napisy).
# Sekcja linie: dla kazdego prawdziwego wzoru z dane/wzory/ (cache outputs/wzor_<nazwa>.json)
#   plan liczony po ciecia_s (bez uderzen, zeby nie zalezec od biblioteki muzyki), potem
#   render.koniec_haka i najwyzsza liczba linii, jaka przyjmie tekst.okna_tekstow bez ValueError.
# Sekcja narzut: syntetyczny projekt (3 zdjecia), wzor z hakiem na 3 s (90 klatek), render
#   1080x1920 bez napisow i z 3 liniami (polskie znaki, bardzo dluga, emoji) dla obu presetow.
#   Narzut liczony z czasu procesora ffmpeg (suma utime+stime z linii "bench:", flaga
#   -benchmark podmienionym render.uruchom_ffmpeg), bo pojedynczy czas_s z podsumowania
#   renderu to czas zegara calego procesu Pythona, nie samego ffmpeg. Bez progu (decyzja
#   wlasciciela 2026-09-24), tylko raport. Arkusz outputs/tekst.png: klatka ze srodka okna
#   kazdej linii, oba presety obok siebie.
# Sekcja porownanie: dla kazdego prawdziwego wzoru arkusz porownawczy z 2 liniami, materialy
#   i plansza jak w bloku WSPOLNE (dane/zdjecia, dane/nagrania, dane/zdjecia_bez_tla, muzyka
#   z biblioteki, plansza z dane/plansze albo pierwszy plik bez przezroczystosci z promocyjne).

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import render  # noqa: E402
import tekst  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_tekst.json"
KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"

FPS = 30
LINIE_TESTOWE = [
    "Zażółć gęślą jaźń",
    "To jest bardzo długa linia tekstu, która na pewno się złamie na wiele wierszy w kadrze",
    "Impreza dzisiaj 🔥🔥 ziomek",
]
PRESETY = ["szeryf", "blok"]

BENCH_RE = re.compile(r"bench:\s*utime=([\d.]+)s\s*stime=([\d.]+)s")

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


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


def znajdz_wzory() -> list[Path]:
    if not KATALOG_WZOROW.is_dir():
        return []
    return sorted(p for p in KATALOG_WZOROW.glob("*.mp4"))


def plan_bez_uderzen(wzor: dict) -> dict:
    material_zastepczy = [{"plik": "zastepczy", "typ": "zdjecie", "message_id": 0}]
    return render.plan_ujec(wzor, [], material_zastepczy, FPS)


def najwyzsza_liczba_linii(plan: dict, koniec_haka_klatka: int) -> int:
    n = 0
    while True:
        try:
            tekst.okna_tekstow(n + 1, plan, koniec_haka_klatka)
        except ValueError:
            return n
        n += 1
        if n > plan["liczba_klatek"]:
            return n


def sekcja_linie() -> dict:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("linie pominieta: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}

    wpisy = []
    for sciezka in pliki_wzorow:
        nazwa = sciezka.stem
        wzor = wczytaj_lub_przeanalizuj_wzor(sciezka)
        plan = plan_bez_uderzen(wzor)
        koniec_haka_klatka = render.koniec_haka(plan, wzor.get("sekcje"))
        maks_linii = najwyzsza_liczba_linii(plan, koniec_haka_klatka)
        wpis = {
            "wzor": nazwa,
            "liczba_klatek_edita": plan["liczba_klatek"],
            "koniec_haka_klatka": koniec_haka_klatka,
            "najwyzsza_liczba_linii": maks_linii,
        }
        wpisy.append(wpis)
        print(f"linie {nazwa}: koniec haka {koniec_haka_klatka} klatek, najwyzsza liczba linii {maks_linii}")

    return {"wzory": wpisy}


def uruchom_ffmpeg_z_benchmarkiem(sumator: list, argumenty: list[str], katalog: Path | None = None) -> None:
    wynik = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "info", "-benchmark", *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
    dopasowanie = BENCH_RE.search(wynik.stderr.decode("utf-8", errors="replace"))
    if dopasowanie:
        sumator.append(float(dopasowanie.group(1)) + float(dopasowanie.group(2)))


def renderuj_z_pomiarem_cpu(**kwargs) -> tuple[dict, float, float]:
    sumator: list[float] = []
    oryginalny = render.uruchom_ffmpeg
    render.uruchom_ffmpeg = lambda argumenty, katalog=None: uruchom_ffmpeg_z_benchmarkiem(sumator, argumenty, katalog)
    start_zegar = time.perf_counter()
    try:
        podsumowanie = render.renderuj(**kwargs)
    finally:
        render.uruchom_ffmpeg = oryginalny
    czas_zegara_s = time.perf_counter() - start_zegar
    return podsumowanie, round(sum(sumator), 3), round(czas_zegara_s, 3)


def wzor_syntetyczny_haka_3s() -> dict:
    return {
        "ciecia_s": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        "zrodlo": {"czas_s": 6.0},
    }


def zbuduj_projekt_syntetyczny(katalog_projektu: Path) -> None:
    katalog_materialow = katalog_projektu / "materialy"
    katalog_materialow.mkdir(parents=True)
    for i in range(3):
        generuj.zdjecie_testowe(
            katalog_materialow / f"000000000{i}_m.jpg", rozmiar=(800, 600), kolor=generuj.kolor_ujecia(i),
        )


def zapisz_projekt_json(katalog_projektu: Path, linie: list[str]) -> None:
    dane = {"teksty": [{"message_id": i + 1, "tekst": linia} for i, linia in enumerate(linie)]}
    (katalog_projektu / "projekt.json").write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def wyciagnij_klatke(sciezka: Path, czas_s: float) -> np.ndarray:
    with TemporaryDirectory() as katalog:
        klatka = Path(katalog) / "klatka.png"
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-ss", f"{czas_s:.6f}", "-i", str(sciezka), "-frames:v", "1", str(klatka)],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0 or not klatka.exists():
            raise RuntimeError(f"nie udalo sie wyciagnac klatki z {sciezka} w {czas_s} s")
        return cv2.imread(str(klatka))


def zbuduj_arkusz_tekst(wyniki_presetow: dict) -> Path:
    komorka = (240, 427)
    klatki_kolumn = []
    for preset in PRESETY:
        wyjscie = Path(wyniki_presetow[preset]["wyjscie"])
        okna = wyniki_presetow[preset]["okna"]
        fps = wyniki_presetow[preset]["fps"]
        klatki = []
        for klatka_od, klatka_do in okna:
            czas_s = (klatka_od + klatka_do) / 2 / fps
            klatka = wyciagnij_klatke(wyjscie, czas_s)
            klatka = cv2.resize(klatka, komorka, interpolation=cv2.INTER_AREA)
            klatki.append(klatka)
        klatki_kolumn.append(np.vstack(klatki))

    siatka = np.hstack(klatki_kolumn)
    cel = KATALOG_OUTPUTS / "tekst.png"
    ok, bufor = cv2.imencode(".png", siatka)
    if not ok:
        raise RuntimeError("Nie udalo sie zakodowac arkusza tekst.png")
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(bufor.tobytes())
    return cel


def sekcja_narzut() -> dict:
    wzor = wzor_syntetyczny_haka_3s()
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        zbuduj_projekt_syntetyczny(katalog_projektu)
        wzor_json = katalog_tymczasowy / "wzor.json"
        wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
        utwor = katalog_tymczasowy / "klik.wav"
        generuj.klik(utwor, bpm=128, czas_s=6.0, pierwsze_uderzenie_s=0.3)

        wyjscie_bez = katalog_tymczasowy / "bez.mp4"
        _, cpu_bez_s, zegar_bez_s = renderuj_z_pomiarem_cpu(
            wzor_json=wzor_json, katalog_projektu=katalog_projektu, utwor=utwor, wyjscie=wyjscie_bez,
            szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200,
        )
        print(f"narzut bez napisow: cpu {cpu_bez_s} s, zegar {zegar_bez_s} s")

        wyniki_presetow = {}
        for preset in PRESETY:
            zapisz_projekt_json(katalog_projektu, LINIE_TESTOWE)
            wyjscie = KATALOG_OUTPUTS / f"tekst_{preset}.mp4"
            podsumowanie, cpu_s, zegar_s = renderuj_z_pomiarem_cpu(
                wzor_json=wzor_json, katalog_projektu=katalog_projektu, utwor=utwor, wyjscie=wyjscie,
                szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200,
                styl_tekstu=preset, pozycja_tekstu="dol",
            )
            narzut_procent = round((cpu_s - cpu_bez_s) / cpu_bez_s * 100, 1) if cpu_bez_s > 0 else None
            wyniki_presetow[preset] = {
                "cpu_s": cpu_s,
                "zegar_s": zegar_s,
                "narzut_cpu_procent": narzut_procent,
                "linie": podsumowanie["teksty"]["linie"],
                "usuniete_znaki": podsumowanie["teksty"]["usuniete_znaki"],
                "okna": podsumowanie["teksty"]["okna"],
                "fps": FPS,
                "wyjscie": str(wyjscie),
            }
            print(f"narzut {preset}: cpu {cpu_s} s ({narzut_procent}%), okna {podsumowanie['teksty']['okna']}")

        arkusz_tekst = zbuduj_arkusz_tekst(wyniki_presetow)
        for wpis in wyniki_presetow.values():
            del wpis["wyjscie"]

    wyniki = {
        "bez_napisow": {"cpu_s": cpu_bez_s, "zegar_s": zegar_bez_s},
        "presety": wyniki_presetow,
        "arkusz": arkusz_tekst.name,
    }
    print(f"narzut: arkusz {arkusz_tekst.name}")
    return wyniki


def zbuduj_materialy_realne(katalog_materialow: Path) -> None:
    katalog_zdjecia = KATALOG_REPO / "dane" / "zdjęcia"
    katalog_nagrania = KATALOG_REPO / "dane" / "nagrania"
    katalog_bez_tla = KATALOG_REPO / "dane" / "zdjęcia_bez_tła"

    katalog_materialow.mkdir(parents=True, exist_ok=True)
    wybrane = []
    if katalog_zdjecia.is_dir():
        wybrane += sorted(p for p in katalog_zdjecia.iterdir() if p.is_file())[:8]
    if katalog_nagrania.is_dir():
        wybrane += sorted(p for p in katalog_nagrania.iterdir() if p.is_file())[:4]
    if katalog_bez_tla.is_dir():
        z_alfa = [p for p in sorted(katalog_bez_tla.iterdir()) if p.is_file() and render.ma_alfa_z_pil(p)]
        wybrane += z_alfa[:2]

    if not wybrane:
        for i in range(8):
            sciezka = katalog_materialow / f"{i + 1:010d}_m.jpg"
            generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))
        return

    for indeks, zrodlo in enumerate(wybrane):
        cel = katalog_materialow / f"{indeks + 1:010d}_{zrodlo.stem[:8]}{zrodlo.suffix}"
        try:
            cel.hardlink_to(zrodlo)
        except OSError:
            shutil.copy(zrodlo, cel)


def znajdz_plansze() -> Path | None:
    katalog_plansz = KATALOG_REPO / "dane" / "plansze"
    if katalog_plansz.is_dir():
        znalezione = sorted(p for p in katalog_plansz.glob("domyslna.*") if p.is_file())
        if znalezione:
            return znalezione[0]
    katalog_promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if katalog_promocyjne.is_dir():
        for plik in sorted(katalog_promocyjne.iterdir()):
            if plik.suffix.lower() in (".jpg", ".jpeg", ".png") and not render.ma_alfa_z_pil(plik):
                return plik
    return None


def sekcja_porownanie() -> dict:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("porownanie pominieta: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}

    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    if not katalog_muzyki.is_dir() or not any(katalog_muzyki.iterdir()):
        print("porownanie pominieta: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}

    plansza = znajdz_plansze()
    wpisy = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        zbuduj_materialy_realne(katalog_projektu / "materialy")
        zapisz_projekt_json(katalog_projektu, LINIE_TESTOWE[:2])

        for sciezka in pliki_wzorow:
            nazwa = sciezka.stem
            wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
            wyjscie = KATALOG_OUTPUTS / f"porownanie_zrodlo_tekst_{nazwa}.mp4"
            try:
                render.renderuj(
                    wzor_json, katalog_projektu, None, wyjscie,
                    szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=katalog_muzyki,
                    plansza=plansza, styl_tekstu="szeryf", pozycja_tekstu="dol",
                )
            except Exception as blad:
                wpisy.append({"wzor": nazwa, "blad": str(blad)})
                print(f"porownanie {nazwa}: BLAD {blad}")
                continue
            cel_arkusza = KATALOG_OUTPUTS / f"porownanie_tekst_{nazwa}.png"
            arkusz.arkusz_porownawczy(sciezka, wyjscie, cel_arkusza)
            wpisy.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
            print(f"porownanie {nazwa}: arkusz {cel_arkusza.name}")

    wyniki = {"wzory": wpisy}
    wyniki["arkusze_powstaly"] = bool(wpisy) and all("arkusz" in w for w in wpisy)
    print(f"porownanie: arkusze_powstaly {wyniki['arkusze_powstaly']}")
    return wyniki


def main() -> int:
    wyniki_linie = sekcja_linie()
    zapisz_sekcje("linie", wyniki_linie)

    wyniki_narzut = sekcja_narzut()
    zapisz_sekcje("narzut", wyniki_narzut)

    wyniki_porownanie = sekcja_porownanie()
    zapisz_sekcje("porownanie", wyniki_porownanie)

    print("Pomiar zakonczony (bez progu czasu, decyzja wlasciciela 2026-09-24). Wyglad oceniaja oceniajacy i wlasciciel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
