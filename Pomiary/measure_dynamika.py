import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 10 (dynamika), zadanie 10.5.
# Sekcja A: na kazdym z 5 prawdziwych wzorow (dane/wzory/*.mp4) render z dynamika i z
#   --bez-dynamiki (ta sama biblioteka materialow, ta sama muzyka). Liczba ujec i uzytych
#   materialow w obu trybach, mediana dlugosci ujecia zdjecia i klipu, liczba kolazy i
#   wycinkow. "Zaden wycinek jako osobne ujecie" to zgodnosc liczby wycinkow z podsumowania
#   (dynamika.wycinki) z liczba plikow z przezroczystoscia faktycznie znalezionych w
#   bibliotece (test_dynamika.py sprawdza to samo zachowanie na poziomie kodu, tu tylko
#   potwierdzenie na prawdziwych danych).
# Sekcja B: narzut czasu procesora (-benchmark, jak w measure_rytm.py) dynamika wobec
#   --bez-dynamiki na pierwszym wzorze, ponownie wykorzystujac renderowanie z sekcji A
#   (bez dodatkowych przebiegow). Tylko raport.
# Sekcja C: dla kazdego wzoru arkusz outputs/porownanie_dynamika_<wzor>.png (wzor kontra
#   wynik z dynamika, Pomiary/arkusz.py). Dla wzoru 0923 dodatkowo outputs/dynamika_drop.png
#   (klatki od 10 przed do 20 po dropie, co 2 klatki) i outputs/dynamika_0923.mp4 (probny
#   edit dla wlasciciela, kopia wyniku z dynamika).
# render.uruchom_ffmpeg podmieniony w calym pomiarze na wersje z limitem 900 s (jak w
#   measure_rytm.py): zawieszony przebieg trafia do wyniku jako blad wzoru, pomiar idzie dalej.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_dynamika.json"
KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"
KATALOG_MUZYKI = KATALOG_REPO / "dane" / "muzyka"

FPS = 30
LIMIT_RENDERU_S = 900
SLOWA_TESTOWE = "europe be like POLAND"
PIONOWO_TESTOWY = "1993 supply made in poland"
WZOR_PROBNEGO_EDITU = "0923"

BENCH_RE = re.compile(r"bench:\s*utime=([\d.]+)s\s*stime=([\d.]+)s")

WYNIKI_CALOSC: dict = {}
CPU_SUMATOR: list[float] = []


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def uruchom_ffmpeg_z_limitem(argumenty: list[str], katalog: Path | None = None) -> None:
    try:
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "info", "-benchmark", *argumenty],
            stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog, timeout=LIMIT_RENDERU_S,
        )
    except subprocess.TimeoutExpired as blad:
        raise RuntimeError(f"ffmpeg przekroczyl limit czasu {LIMIT_RENDERU_S} s") from blad
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
    dopasowanie = BENCH_RE.search(wynik.stderr.decode("utf-8", errors="replace"))
    if dopasowanie:
        CPU_SUMATOR.append(float(dopasowanie.group(1)) + float(dopasowanie.group(2)))


render.uruchom_ffmpeg = uruchom_ffmpeg_z_limitem


def znajdz_wzory() -> list[Path]:
    if not KATALOG_WZOROW.is_dir():
        return []
    return sorted(p for p in KATALOG_WZOROW.glob("*.mp4"))


def wczytaj_lub_przeanalizuj_wzor(sciezka: Path) -> Path:
    nazwa = sciezka.stem
    cel = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    if cel.is_file():
        dane = json.loads(cel.read_text(encoding="utf-8"))
        if dane.get("wersja") == analyze.WERSJA_WZORU:
            print(f"{nazwa}: wzor z cache ({cel.name})")
            return cel
    start = time.monotonic()
    dane = analyze.analizuj_wzor(sciezka, nazwa)
    czas = time.monotonic() - start
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{nazwa}: analiza wzoru w {czas:.1f} s")
    return cel


def ma_prawdziwa_alfa(sciezka: Path) -> bool:
    try:
        with Image.open(sciezka) as obraz:
            if obraz.mode != "RGBA":
                return False
            return obraz.getchannel("A").getextrema()[0] < 255
    except Exception:
        return False


def zbuduj_katalog_materialow(katalog_materialow: Path) -> list[Path]:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    katalog_zdjec = KATALOG_REPO / "dane" / "zdjęcia"
    katalog_nagran = KATALOG_REPO / "dane" / "nagrania"
    katalog_bez_tla = KATALOG_REPO / "dane" / "zdjęcia_bez_tła"

    zdjecia = sorted(p for p in katalog_zdjec.glob("*") if p.is_file())[:8] if katalog_zdjec.is_dir() else []
    nagrania = sorted(p for p in katalog_nagran.glob("*") if p.is_file())[:4] if katalog_nagran.is_dir() else []
    bez_tla = []
    if katalog_bez_tla.is_dir():
        bez_tla = [p for p in sorted(katalog_bez_tla.glob("*")) if p.is_file() and ma_prawdziwa_alfa(p)]

    zrodla = zdjecia + nagrania + bez_tla
    if not zrodla:
        for i in range(8):
            generuj.zdjecie_testowe(
                katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i),
            )
        return []

    wycinki_kopie = []
    for i, plik in enumerate(zrodla):
        cel = katalog_materialow / f"{i + 1:010d}_m{plik.suffix.lower()}"
        try:
            os.link(plik, cel)
        except OSError:
            shutil.copy(plik, cel)
        if plik in bez_tla:
            wycinki_kopie.append(cel)
    return wycinki_kopie


def zapisz_projekt_json(katalog_projektu: Path) -> None:
    dane = {"teksty": [], "slowa": SLOWA_TESTOWE, "pionowo": PIONOWO_TESTOWY}
    (katalog_projektu / "projekt.json").write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def znajdz_plansze() -> Path | None:
    katalog_plansz = KATALOG_REPO / "dane" / "plansze"
    if katalog_plansz.is_dir():
        znalezione = sorted(p for p in katalog_plansz.glob("domyslna.*") if p.is_file())
        if znalezione:
            return znalezione[0]
    katalog_promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if katalog_promocyjne.is_dir():
        for plik in sorted(katalog_promocyjne.iterdir()):
            if plik.suffix.lower() in (".jpg", ".jpeg", ".png") and not ma_prawdziwa_alfa(plik):
                return plik
    return None


def znajdz_znak() -> Path | None:
    katalog_promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if not katalog_promocyjne.is_dir():
        return None
    for plik in sorted(katalog_promocyjne.iterdir()):
        if plik.is_file() and "watermark" in plik.stem.lower():
            return plik
    return None


def znajdz_nakladke() -> Path | None:
    domyslna = KATALOG_REPO / "dane" / "nakladki" / "domyslna.mp4"
    return domyslna if domyslna.is_file() else None


def zrenderuj_wariant(wzor_json, katalog_projektu, wyjscie, muzyka, nakladka, plansza, znak, bez_dynamiki) -> dict | None:
    del CPU_SUMATOR[:]
    return render.renderuj(
        wzor_json, katalog_projektu, None, wyjscie,
        szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=muzyka,
        nakladka=nakladka, plansza=plansza, znak=znak, bez_dynamiki=bez_dynamiki,
    )


def sekcja_a_i_c() -> tuple[dict, dict]:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("A/C pominiete: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}, {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("A/C pominiete: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}, {"pominieta": True, "powod": "brak dane/muzyka"}

    nakladka = znajdz_nakladke()
    plansza = znajdz_plansze()
    znak = znajdz_znak()

    wpisy_a = []
    wpisy_c = []
    narzut_b = None
    wynik_0923 = None
    drop_s_0923 = None

    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        wycinki = zbuduj_katalog_materialow(katalog_projektu / "materialy")
        zapisz_projekt_json(katalog_projektu)

        for indeks_wzoru, sciezka in enumerate(pliki_wzorow):
            nazwa = sciezka.stem
            wzor_json = wczytaj_lub_przeanalizuj_wzor(sciezka)
            wyjscie_dyn = KATALOG_OUTPUTS / f"dynamika_zrodlo_{nazwa}.mp4"
            wyjscie_bez = katalog_tymczasowy / f"bez_dynamiki_{nazwa}.mp4"
            podsumowanie_dyn_json = wyjscie_dyn.with_suffix(".json")

            if wyjscie_dyn.is_file() and podsumowanie_dyn_json.is_file():
                podsumowanie_dyn = json.loads(podsumowanie_dyn_json.read_text(encoding="utf-8"))
                cpu_dyn_s = 0.0
                print(f"A {nazwa}: dynamika z cache ({wyjscie_dyn.name})")
            else:
                try:
                    podsumowanie_dyn = zrenderuj_wariant(
                        wzor_json, katalog_projektu, wyjscie_dyn, KATALOG_MUZYKI, nakladka, plansza, znak, False,
                    )
                    cpu_dyn_s = round(sum(CPU_SUMATOR), 3)
                except (RuntimeError, subprocess.TimeoutExpired) as blad:
                    wpisy_a.append({"wzor": nazwa, "blad": str(blad)})
                    print(f"A {nazwa}: BLAD {blad}")
                    continue

            zaden_osobno = podsumowanie_dyn["dynamika"]["wycinki"] == len(wycinki)

            cel_arkusza = KATALOG_OUTPUTS / f"porownanie_dynamika_{nazwa}.png"
            if not cel_arkusza.is_file():
                arkusz.arkusz_porownawczy(sciezka, wyjscie_dyn, cel_arkusza)
            wpisy_c.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
            print(f"C {nazwa}: arkusz {cel_arkusza.name}")

            if nazwa == WZOR_PROBNEGO_EDITU:
                wynik_0923 = wyjscie_dyn
                drop_s_0923 = podsumowanie_dyn.get("drop_s")

            try:
                podsumowanie_bez = zrenderuj_wariant(
                    wzor_json, katalog_projektu, wyjscie_bez, KATALOG_MUZYKI, nakladka, plansza, znak, True,
                )
                cpu_bez_s = round(sum(CPU_SUMATOR), 3)
            except (RuntimeError, subprocess.TimeoutExpired) as blad:
                wpisy_a.append({"wzor": nazwa, "blad": f"bez-dynamiki: {blad}"})
                print(f"A {nazwa}: BLAD (bez-dynamiki) {blad}")
                continue

            dynamika = podsumowanie_dyn["dynamika"]
            wpis = {
                "wzor": nazwa,
                "liczba_ujec_dynamika": podsumowanie_dyn["liczba_ujec"],
                "liczba_ujec_bez_dynamiki": podsumowanie_bez["liczba_ujec"],
                "materialy_uzyte_dynamika": podsumowanie_dyn["materialy_uzyte"],
                "materialy_uzyte_bez_dynamiki": podsumowanie_bez["materialy_uzyte"],
                "mediana_zdjecia_s": dynamika["mediana_zdjecia_s"],
                "mediana_klipu_s": dynamika["mediana_klipu_s"],
                "liczba_kolazy": len(podsumowanie_dyn["kolaze"]),
                "wycinki": dynamika["wycinki"],
                "zaden_wycinek_jako_osobne_ujecie": zaden_osobno,
            }
            wpisy_a.append(wpis)
            print(
                f"A {nazwa}: ujec {wpis['liczba_ujec_dynamika']} (bez dynamiki {wpis['liczba_ujec_bez_dynamiki']}), "
                f"mediana zdjecia {wpis['mediana_zdjecia_s']} s, klipu {wpis['mediana_klipu_s']} s, "
                f"kolaze {wpis['liczba_kolazy']}, wycinki {wpis['wycinki']}"
            )

            if indeks_wzoru == 0 and cpu_bez_s > 0 and cpu_dyn_s > 0:
                narzut_b = {
                    "wzor": nazwa,
                    "cpu_dynamika_s": cpu_dyn_s,
                    "cpu_bez_dynamiki_s": cpu_bez_s,
                    "narzut_procent": round((cpu_dyn_s - cpu_bez_s) / cpu_bez_s * 100, 1),
                }
                print(f"B {nazwa}: cpu dynamika {cpu_dyn_s} s, bez dynamiki {cpu_bez_s} s ({narzut_b['narzut_procent']}%)")

    zaliczone_a = [w for w in wpisy_a if "blad" not in w]
    progi_a = {
        "mediana_zdjecia_w_progu": bool(zaliczone_a) and all(
            0.3 <= w["mediana_zdjecia_s"] <= 0.7 for w in zaliczone_a if w["mediana_zdjecia_s"] is not None
        ),
        "mediana_klipu_w_progu": bool(zaliczone_a) and all(
            2.0 <= w["mediana_klipu_s"] <= 3.2 for w in zaliczone_a if w["mediana_klipu_s"] is not None
        ),
        "wiecej_ujec_niz_bez_dynamiki": bool(zaliczone_a) and all(
            w["liczba_ujec_dynamika"] > w["liczba_ujec_bez_dynamiki"] for w in zaliczone_a
        ),
        "zaden_wycinek_jako_osobne_ujecie": bool(zaliczone_a) and all(
            w["zaden_wycinek_jako_osobne_ujecie"] for w in zaliczone_a
        ),
        "zaden_render_nie_przekroczyl_limitu": all("limit" not in str(w.get("blad", "")) for w in wpisy_a),
    }
    wyniki_a = {"wzory": wpisy_a, "narzut_b": narzut_b, "progi": progi_a}
    print(f"A: {progi_a}")

    arkusz_dropu = None
    if wynik_0923 is not None and drop_s_0923 is not None:
        arkusz_dropu = zbuduj_arkusz_dropu(wynik_0923, drop_s_0923)
        if arkusz_dropu:
            print(f"C: arkusz dropu {arkusz_dropu.name}")

    probny_edit = None
    if wynik_0923 is not None:
        cel_edit = KATALOG_OUTPUTS / "dynamika_0923.mp4"
        shutil.copyfile(wynik_0923, cel_edit)
        probny_edit = cel_edit.name
        print(f"C: probny edit {probny_edit}")

    wyniki_c = {
        "wzory": wpisy_c,
        "arkusze_powstaly": bool(wpisy_c) and len(wpisy_c) == len(pliki_wzorow),
        "dynamika_drop": arkusz_dropu.name if arkusz_dropu else None,
        "probny_edit": probny_edit,
    }
    return wyniki_a, wyniki_c


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


def zbuduj_arkusz_dropu(wynik_0923: Path, drop_s: float, fps: float = FPS) -> Path | None:
    komorka = (192, 341)
    przesuniecia_klatek = list(range(-10, 21, 2))
    obrazy = []
    for przesuniecie in przesuniecia_klatek:
        czas_s = max(0.0, drop_s + przesuniecie / fps)
        try:
            klatka = cv2.resize(wyciagnij_klatke(wynik_0923, czas_s), komorka, interpolation=cv2.INTER_AREA)
        except RuntimeError:
            klatka = np.zeros((komorka[1], komorka[0], 3), dtype=np.uint8)
        obrazy.append(klatka)
    if not obrazy:
        return None
    kolumny = 8
    puste = np.zeros((komorka[1], komorka[0], 3), dtype=np.uint8)
    wiersze = []
    for i in range(0, len(obrazy), kolumny):
        wycinek = obrazy[i:i + kolumny]
        while len(wycinek) < kolumny:
            wycinek.append(puste)
        wiersze.append(np.hstack(wycinek))
    siatka = np.vstack(wiersze)
    cel = KATALOG_OUTPUTS / "dynamika_drop.png"
    ok, bufor = cv2.imencode(".png", siatka)
    if not ok:
        raise RuntimeError("Nie udalo sie zakodowac arkusza dynamika_drop.png")
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(bufor.tobytes())
    return cel


def main() -> int:
    wyniki_a, wyniki_c = sekcja_a_i_c()
    zapisz_sekcje("A", wyniki_a)
    zapisz_sekcje("B", wyniki_a.get("narzut_b") or {"pominieta": True})
    zapisz_sekcje("C", wyniki_c)

    print("Pomiar zakonczony. B tylko raport. Arkusze, klatki dropu i probny edit ocenia wlasciciel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
