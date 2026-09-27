import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 10 (dynamika), zadania 10.8 i 10.10 (powtorka 10.5 po poprawkach 10.6/10.7,
#   pelny czas procesora, komplet wzorow i zapis po kazdym wzorze z 10.10).
# Sekcja A: na kazdym z 5 prawdziwych wzorow (dane/wzory/*.mp4) render z dynamika i z
#   --bez-dynamiki (ta sama biblioteka materialow, ta sama muzyka), bez pamieci wynikow z
#   poprzednich przebiegow (kazde wywolanie renderuje oba warianty od nowa, czas nie ma
#   znaczenia). Liczba ujec i uzytych materialow w obu trybach, mediana dlugosci ujecia
#   zdjecia i klipu, liczba kolazy i wycinkow, udzial zdjec po dropie i najdluzsza seria
#   klipow pod rzad (plan z dynamika przechwycony przez podmiane render.rozloz_tempo).
#   "Zaden wycinek jako osobne ujecie" to zgodnosc liczby wycinkow z podsumowania
#   (dynamika.wycinki) z liczba plikow z przezroczystoscia faktycznie znalezionych w
#   bibliotece (test_dynamika.py sprawdza to samo zachowanie na poziomie kodu, tu tylko
#   potwierdzenie na prawdziwych danych).
#   Prog wszystkie_wzory_w_obu_trybach: kazdy wzor wyrenderowany w obu trybach bez bledu.
# Sekcja B: narzut czasu procesora dynamika wobec --bez-dynamiki na pierwszym wzorze, oba
#   swiezo zmierzone w tym przebiegu. Tylko raport. Czas renderu to suma trzech czesci:
#   -benchmark procesow ffmpeg z render.uruchom_ffmpeg, -benchmark procesow ffmpeg z
#   render.materializuj_warstwe (kolaze, slowa, napis pionowy; podmieniona na wersje z
#   -benchmark, logiem w pliku tymczasowym i limitem 900 s) oraz time.process_time() procesu
#   Pythona. Indeks muzyki liczony raz przed sekcja A. Poza suma zostaja krotkie wywolania
#   ffprobe i probkowanie koloru (subprocess.run w render.py), obecne w obu trybach.
#   Dodatkowo koszt render.materializuj_nakladke dla kazdej nakladki z dane/nakladki/ i dla
#   syntetycznego pierscienia (okno z planu pierwszego wzoru): czas procesora i rozmiar pliku.
# Sekcja C: dla kazdego wzoru arkusz outputs/porownanie_dynamika_<wzor>.png (wzor kontra
#   wynik z dynamika, Pomiary/arkusz.py). Dla wzoru 0923 dodatkowo outputs/dynamika_drop.png
#   (klatki od 10 przed do 20 po dropie, co 2 klatki) i outputs/dynamika_0923.mp4 (probny
#   edit dla wlasciciela, kopia wyniku z dynamika).
# render.uruchom_ffmpeg podmieniony w calym pomiarze na wersje z limitem 900 s (jak w
#   measure_rytm.py): zawieszony przebieg trafia do wyniku jako blad wzoru, pomiar idzie dalej.
# Wyniki A, B i C zapisywane do outputs/pomiar_dynamika.json po kazdym wzorze ("w_toku": true),
#   a na koncu ostatecznie.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import music  # noqa: E402
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
CPU_WARSTW: list[float] = []


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


def materializuj_warstwe_z_limitem(generator_klatek, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int, wyjscie: Path) -> None:
    # Te same argumenty co render.materializuj_warstwe, plus -benchmark. Log ffmpeg idzie do pliku,
    # nie do potoku, bo przy -loglevel info potok stderr moglby sie zapelnic w trakcie zapisu klatek.
    przekroczony = threading.Event()
    with TemporaryDirectory() as katalog_logu:
        sciezka_logu = Path(katalog_logu) / "ffmpeg.log"
        with open(sciezka_logu, "wb") as log:
            proces = subprocess.Popen(
                [
                    "ffmpeg", "-y", "-nostdin", "-loglevel", "info", "-benchmark",
                    "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{szerokosc}x{wysokosc}",
                    "-framerate", str(fps), "-i", "pipe:0",
                    "-frames:v", str(liczba_klatek),
                    "-c:v", "png", "-pix_fmt", "rgba",
                    str(wyjscie),
                ],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log,
            )

            def zabij() -> None:
                przekroczony.set()
                proces.kill()

            straznik = threading.Timer(LIMIT_RENDERU_S, zabij)
            straznik.start()
            try:
                try:
                    for indeks in range(liczba_klatek):
                        obraz = generator_klatek(indeks).convert("RGBA")
                        proces.stdin.write(np.asarray(obraz, dtype=np.uint8).tobytes())
                except OSError:
                    pass
                finally:
                    try:
                        proces.stdin.close()
                    except OSError:
                        pass
                kod = proces.wait()
            finally:
                straznik.cancel()
        tresc = sciezka_logu.read_text(encoding="utf-8", errors="replace")
    if przekroczony.is_set():
        raise RuntimeError(f"ffmpeg przekroczyl limit czasu {LIMIT_RENDERU_S} s (warstwa {Path(wyjscie).name})")
    if kod != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {kod}: {tresc}")
    dopasowanie = BENCH_RE.search(tresc)
    if dopasowanie:
        CPU_WARSTW.append(float(dopasowanie.group(1)) + float(dopasowanie.group(2)))


render.materializuj_warstwe = materializuj_warstwe_z_limitem

OSTATNI_PLAN: dict = {}
ORYGINALNY_ROZLOZ_TEMPO = render.rozloz_tempo


def rozloz_tempo_z_przechwyceniem(plan, wzor_arg, uderzenia, kawalki, fps_arg):
    wynik = ORYGINALNY_ROZLOZ_TEMPO(plan, wzor_arg, uderzenia, kawalki, fps_arg)
    OSTATNI_PLAN["plan_bazowy"] = plan
    OSTATNI_PLAN["plan"] = wynik
    OSTATNI_PLAN["sekcje"] = wzor_arg.get("sekcje")
    return wynik


render.rozloz_tempo = rozloz_tempo_z_przechwyceniem


def udzial_zdjec_i_seria_klipow_po_dropie() -> tuple[float | None, int | None]:
    plan_bazowy = OSTATNI_PLAN.get("plan_bazowy")
    plan_koncowy = OSTATNI_PLAN.get("plan")
    if plan_bazowy is None or plan_koncowy is None or not plan_bazowy["ujecia"]:
        return None, None
    klatka_dropu = render.koniec_haka(plan_bazowy, OSTATNI_PLAN.get("sekcje"))
    plansza_start = plan_bazowy["ujecia"][-1]["klatka_od"]
    montaz = [u for u in plan_koncowy["ujecia"] if klatka_dropu <= u["klatka_od"] < plansza_start]
    if not montaz:
        return None, None
    udzial_zdjec = sum(1 for u in montaz if u["typ"] == "zdjecie") / len(montaz)
    seria = 0
    najdluzsza = 0
    for ujecie in montaz:
        if ujecie["typ"] == "klip":
            seria += 1
            najdluzsza = max(najdluzsza, seria)
        else:
            seria = 0
    return round(udzial_zdjec, 3), najdluzsza


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


def zrenderuj_wariant(wzor_json, katalog_projektu, wyjscie, muzyka, nakladka, plansza, znak, bez_dynamiki) -> tuple[dict, dict]:
    del CPU_SUMATOR[:]
    del CPU_WARSTW[:]
    start_python = time.process_time()
    podsumowanie = render.renderuj(
        wzor_json, katalog_projektu, None, wyjscie,
        szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=muzyka,
        nakladka=nakladka, plansza=plansza, znak=znak, bez_dynamiki=bez_dynamiki,
    )
    czasy = {
        "ffmpeg_s": round(sum(CPU_SUMATOR), 3),
        "warstwy_s": round(sum(CPU_WARSTW), 3),
        "python_s": round(time.process_time() - start_python, 3),
    }
    czasy["razem_s"] = round(czasy["ffmpeg_s"] + czasy["warstwy_s"] + czasy["python_s"], 3)
    return podsumowanie, czasy


def zapisz_w_toku(wpisy_a: list, wpisy_c: list, narzut_b: dict | None) -> None:
    WYNIKI_CALOSC["A"] = {"w_toku": True, "wzory": wpisy_a}
    WYNIKI_CALOSC["B"] = narzut_b if narzut_b is not None else {"w_toku": True}
    WYNIKI_CALOSC["C"] = {"w_toku": True, "wzory": wpisy_c}
    zapisz_wyniki()


def koszt_nakladek(wzor_json: Path, plan: dict | None, plansza: Path | None) -> list[dict]:
    if plan is None:
        return []
    wzor = json.loads(Path(wzor_json).read_text(encoding="utf-8"))
    plansza_uzyta = plansza is not None and len(plan["ujecia"]) > 1
    katalog_nakladek = KATALOG_REPO / "dane" / "nakladki"
    nakladki = sorted(p for p in katalog_nakladek.iterdir() if p.is_file()) if katalog_nakladek.is_dir() else []
    wyniki = []
    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        pierscien = katalog / "pierscien_syntetyczny.png"
        generuj.pierscien_testowy(pierscien, rozmiar=(1080, 1080))
        for nakladka in nakladki + [pierscien]:
            try:
                tryb = render.tryb_nakladki(nakladka)
                od_s, do_s = render.okno_nakladki(
                    wzor, plan, plansza_uzyta, tryb=tryb, dlugosc_krycie_s=render.DLUGOSC_NAKLADKI_KRYCIE_S,
                )
                liczba_klatek = round((do_s - od_s) * FPS)
                del CPU_SUMATOR[:]
                wynik = render.materializuj_nakladke(nakladka, tryb, liczba_klatek, FPS, 1080, 1920, katalog)
                wpis = {
                    "plik": nakladka.name,
                    "tryb": tryb,
                    "okno_s": round(do_s - od_s, 3),
                    "klatki": liczba_klatek,
                    "cpu_s": round(sum(CPU_SUMATOR), 3),
                    "rozmiar_mb": round(wynik.stat().st_size / (1024 * 1024), 2),
                }
                wynik.unlink()
            except (RuntimeError, OSError, ValueError) as blad:
                wpis = {"plik": nakladka.name, "blad": str(blad)}
            wyniki.append(wpis)
            print(f"B nakladka {wpis}")
    return wyniki


def sekcja_a_i_c() -> tuple[dict, dict]:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("A/C pominiete: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}, {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("A/C pominiete: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}, {"pominieta": True, "powod": "brak dane/muzyka"}

    _, przeanalizowane = music.indeksuj(KATALOG_MUZYKI)
    print(f"Indeks muzyki gotowy przed renderami (przeanalizowane teraz: {przeanalizowane})")

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
            try:
                nazwa = sciezka.stem
                wzor_json = wczytaj_lub_przeanalizuj_wzor(sciezka)
                wyjscie_dyn = KATALOG_OUTPUTS / f"dynamika_zrodlo_{nazwa}.mp4"
                wyjscie_bez = katalog_tymczasowy / f"bez_dynamiki_{nazwa}.mp4"

                OSTATNI_PLAN.clear()
                try:
                    podsumowanie_dyn, czasy_dyn = zrenderuj_wariant(
                        wzor_json, katalog_projektu, wyjscie_dyn, KATALOG_MUZYKI, nakladka, plansza, znak, False,
                    )
                except (RuntimeError, subprocess.TimeoutExpired) as blad:
                    wpisy_a.append({"wzor": nazwa, "blad": str(blad)})
                    print(f"A {nazwa}: BLAD {blad}")
                    continue

                zaden_osobno = podsumowanie_dyn["dynamika"]["wycinki"] == len(wycinki)
                udzial_zdjec_po_dropie, najdluzsza_seria_klipow = udzial_zdjec_i_seria_klipow_po_dropie()
                plan_dyn = OSTATNI_PLAN.get("plan")

                cel_arkusza = KATALOG_OUTPUTS / f"porownanie_dynamika_{nazwa}.png"
                arkusz.arkusz_porownawczy(sciezka, wyjscie_dyn, cel_arkusza)
                wpisy_c.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
                print(f"C {nazwa}: arkusz {cel_arkusza.name}")

                if nazwa == WZOR_PROBNEGO_EDITU:
                    wynik_0923 = wyjscie_dyn
                    drop_s_0923 = podsumowanie_dyn.get("drop_s")

                try:
                    podsumowanie_bez, czasy_bez = zrenderuj_wariant(
                        wzor_json, katalog_projektu, wyjscie_bez, KATALOG_MUZYKI, nakladka, plansza, znak, True,
                    )
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
                    "udzial_zdjec_po_dropie": udzial_zdjec_po_dropie,
                    "najdluzsza_seria_klipow_po_dropie": najdluzsza_seria_klipow,
                    "cpu_dynamika_s": czasy_dyn["razem_s"],
                    "cpu_bez_dynamiki_s": czasy_bez["razem_s"],
                }
                wpisy_a.append(wpis)
                print(
                    f"A {nazwa}: ujec {wpis['liczba_ujec_dynamika']} (bez dynamiki {wpis['liczba_ujec_bez_dynamiki']}), "
                    f"mediana zdjecia {wpis['mediana_zdjecia_s']} s, klipu {wpis['mediana_klipu_s']} s, "
                    f"kolaze {wpis['liczba_kolazy']}, wycinki {wpis['wycinki']}, "
                    f"zdjecia po dropie {wpis['udzial_zdjec_po_dropie']}, "
                    f"najdluzsza seria klipow {wpis['najdluzsza_seria_klipow_po_dropie']}"
                )

                if indeks_wzoru == 0 and czasy_dyn["razem_s"] > 0 and czasy_bez["razem_s"] > 0:
                    narzut_b = {
                        "wzor": nazwa,
                        "dynamika": czasy_dyn,
                        "bez_dynamiki": czasy_bez,
                        "narzut_procent": round((czasy_dyn["razem_s"] - czasy_bez["razem_s"]) / czasy_bez["razem_s"] * 100, 1),
                    }
                    print(f"B {nazwa}: dynamika {czasy_dyn}, bez dynamiki {czasy_bez} ({narzut_b['narzut_procent']}%)")
                    narzut_b["nakladki"] = koszt_nakladek(wzor_json, plan_dyn, plansza)
            finally:
                zapisz_w_toku(wpisy_a, wpisy_c, narzut_b)

    zaliczone_a = [w for w in wpisy_a if "blad" not in w]
    progi_a = {
        "wszystkie_wzory_w_obu_trybach": bool(pliki_wzorow) and len(zaliczone_a) == len(pliki_wzorow),
        "mediana_zdjecia_w_progu": bool(zaliczone_a) and all(
            0.3 <= w["mediana_zdjecia_s"] <= 0.7 for w in zaliczone_a if w["mediana_zdjecia_s"] is not None
        ),
        "mediana_klipu_w_progu": bool(zaliczone_a) and all(
            2.0 <= w["mediana_klipu_s"] <= 3.2 for w in zaliczone_a if w["mediana_klipu_s"] is not None
        ),
        "ujec_nie_mniej_niz_bez_dynamiki": bool(zaliczone_a) and all(
            w["liczba_ujec_dynamika"] >= w["liczba_ujec_bez_dynamiki"] for w in zaliczone_a
        ),
        "po_dropie_polowa_zdjec_i_zaden_dwa_klipy_pod_rzad": bool(zaliczone_a) and all(
            w["udzial_zdjec_po_dropie"] is not None
            and w["udzial_zdjec_po_dropie"] >= 0.5
            and w["najdluzsza_seria_klipow_po_dropie"] <= 1
            for w in zaliczone_a
        ),
        "zaden_wycinek_jako_osobne_ujecie": bool(zaliczone_a) and all(
            w["zaden_wycinek_jako_osobne_ujecie"] for w in zaliczone_a
        ),
        "zaden_render_nie_przekroczyl_limitu": all("limit" not in str(w.get("blad", "")) for w in wpisy_a),
    }
    wyniki_a = {"liczba_wzorow": len(pliki_wzorow), "wzory": wpisy_a, "narzut_b": narzut_b, "progi": progi_a}
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
