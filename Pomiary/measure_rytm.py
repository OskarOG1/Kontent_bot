import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 9.6 do 9.8 (napisy w rytmie: slowa i napis pionowy).
# Sekcja A: dla kazdego prawdziwego wzoru z dane/wzory/ render z muzyka z biblioteki, slowami
#   "europe be like POLAND" i napisem pionowym "1993 supply made in poland" (haslo wlasciciela,
#   nie tekst ze wzoru, regula 7). Sprawdzamy odsetek slow zaczynajacych sie na klatce uderzenia
#   z render.uderzenia_wyniku (+-1 klatka) i odleglosc poczatku akcentu od poczatku nakladki
#   w uderzeniach.
# Sekcja B: narzut czasu procesora przebiegu koncowego (1080x1920, 20 s) ze slowami i napisem
#   pionowym wobec przebiegu bez nich (-benchmark, jak w measure_tekst.py). Bez progu (decyzja
#   wlasciciela 2026-09-24), tylko raport.
# W calym pomiarze render.uruchom_ffmpeg podmieniony na wersje z limitem 900 s (jak
#   LIMIT_RENDERU_S bota): zawieszony przebieg trafia do wyniku jako blad wzoru, pomiar idzie dalej.
# Sekcja C: arkusze porownawcze outputs/porownanie_rytm_<wzor>.png i outputs/rytm_klatki.png
#   (klatki wyniku w chwilach slow obok klatek 0923 z 9.6, 10.3, 10.8, 11.1, 11.8 i 12.3 s).

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import magazyn  # noqa: E402
import render  # noqa: E402
import tekst  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_rytm.json"
KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"
KATALOG_MUZYKI = KATALOG_REPO / "dane" / "muzyka"

FPS = 30
LIMIT_RENDERU_S = 900
SLOWA_TESTOWE = "europe be like POLAND"
PIONOWO_TESTOWY = "1993 supply made in poland"
WZOR_PORONAWCZY_KLATKI_S = [9.6, 10.3, 10.8, 11.1, 11.8, 12.3]

BENCH_RE = re.compile(r"bench:\s*utime=([\d.]+)s\s*stime=([\d.]+)s")

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def znajdz_wzory() -> list[Path]:
    if not KATALOG_WZOROW.is_dir():
        return []
    return sorted(p for p in KATALOG_WZOROW.glob("*.mp4"))


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


def uruchom_ffmpeg_z_limitem(argumenty: list[str], katalog: Path | None = None) -> None:
    wynik = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog, timeout=LIMIT_RENDERU_S,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")


def uruchom_ffmpeg_z_limitem_i_benchmarkiem(sumator: list, argumenty: list[str], katalog: Path | None = None) -> None:
    wynik = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "info", "-benchmark", *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog, timeout=LIMIT_RENDERU_S,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
    dopasowanie = BENCH_RE.search(wynik.stderr.decode("utf-8", errors="replace"))
    if dopasowanie:
        sumator.append(float(dopasowanie.group(1)) + float(dopasowanie.group(2)))


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


def zapisz_projekt_json(katalog_projektu: Path) -> None:
    dane = {"teksty": [], "slowa": SLOWA_TESTOWE, "pionowo": PIONOWO_TESTOWY}
    (katalog_projektu / "projekt.json").write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def sekcja_a() -> dict:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("A pominieta: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("A pominieta: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}

    oryginalny = render.uruchom_ffmpeg
    render.uruchom_ffmpeg = uruchom_ffmpeg_z_limitem

    wpisy = []
    try:
        with TemporaryDirectory() as katalog_tymczasowy:
            katalog_tymczasowy = Path(katalog_tymczasowy)
            katalog_projektu = katalog_tymczasowy / "projekt"
            zbuduj_materialy_realne(katalog_projektu / "materialy")
            zapisz_projekt_json(katalog_projektu)

            for sciezka in pliki_wzorow:
                nazwa = sciezka.stem
                wczytaj_lub_przeanalizuj_wzor(sciezka)
                wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
                wyjscie = KATALOG_OUTPUTS / f"rytm_zrodlo_{nazwa}.mp4"
                nakladka = magazyn.plik_zasobu(KATALOG_REPO / "dane", "nakladki", nazwa)
                try:
                    podsumowanie = render.renderuj(
                        wzor_json, katalog_projektu, None, wyjscie,
                        szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=KATALOG_MUZYKI,
                        nakladka=nakladka,
                    )
                except subprocess.TimeoutExpired:
                    wpisy.append({"wzor": nazwa, "blad": f"przekroczono limit {LIMIT_RENDERU_S} s"})
                    print(f"A {nazwa}: BLAD przekroczono limit {LIMIT_RENDERU_S} s")
                    continue
                except Exception as blad:
                    wpisy.append({"wzor": nazwa, "blad": str(blad)})
                    print(f"A {nazwa}: BLAD {blad}")
                    continue

                slowa = podsumowanie.get("slowa")
                if not slowa:
                    wpisy.append({"wzor": nazwa, "blad": "brak slow w podsumowaniu"})
                    print(f"A {nazwa}: BLAD brak slow w podsumowaniu")
                    continue

                start_audio_s = podsumowanie["utwor"]["start_s"]
                utwor_sciezka = KATALOG_MUZYKI / podsumowanie["utwor"]["plik"]
                _, uderzenia_utworu = analyze.analizuj_rytm(utwor_sciezka)
                liczba_klatek_wyniku = round(podsumowanie["czas_s"] * FPS)
                uderzenia = render.uderzenia_wyniku(uderzenia_utworu, start_audio_s, liczba_klatek_wyniku, FPS)

                na_uderzeniu = 0
                for poczatek, _ in slowa["okna"]:
                    if any(abs(poczatek - u) <= 1 for u in uderzenia):
                        na_uderzeniu += 1
                odsetek_na_uderzeniu = round(na_uderzeniu / len(slowa["okna"]) * 100, 1)

                odleglosc_nakladki_uderzenia = None
                nakladka = podsumowanie.get("nakladka")
                if nakladka and nakladka.get("od_s") is not None:
                    start_akcentu_klatka = slowa["okna"][-1][0]
                    start_nakladki_klatka = round(nakladka["od_s"] * FPS)
                    if uderzenia:
                        indeks_akcent = min(range(len(uderzenia)), key=lambda i: abs(uderzenia[i] - start_akcentu_klatka))
                        indeks_nakladka = min(range(len(uderzenia)), key=lambda i: abs(uderzenia[i] - start_nakladki_klatka))
                        odleglosc_nakladki_uderzenia = abs(indeks_akcent - indeks_nakladka)

                wpis = {
                    "wzor": nazwa,
                    "liczba_slow": slowa["liczba"],
                    "procent_slow_na_uderzeniu": odsetek_na_uderzeniu,
                    "odleglosc_akcentu_od_nakladki_uderzenia": odleglosc_nakladki_uderzenia,
                }
                wpisy.append(wpis)
                print(f"A {nazwa}: {odsetek_na_uderzeniu}% slow na uderzeniu, akcent {odleglosc_nakladki_uderzenia} uderzen od nakladki")
    finally:
        render.uruchom_ffmpeg = oryginalny

    zaliczone = [w for w in wpisy if "blad" not in w]
    wyniki = {
        "wzory": wpisy,
        "wszystkie_100_procent": bool(zaliczone) and all(w["procent_slow_na_uderzeniu"] == 100.0 for w in zaliczone),
        "akcent_maks_1_uderzenie": bool(zaliczone) and all(
            w["odleglosc_akcentu_od_nakladki_uderzenia"] is None or w["odleglosc_akcentu_od_nakladki_uderzenia"] <= 1
            for w in zaliczone
        ),
    }
    return wyniki


def wzor_syntetyczny_do_narzutu() -> dict:
    return {
        "ciecia_s": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
        "zrodlo": {"czas_s": 20.0},
        "sekcje": {"drop_s": 12.0, "drop_ujecie": 6, "koniec_haka_uderzenia": None},
    }


def zbuduj_projekt_syntetyczny(katalog_projektu: Path) -> None:
    katalog_materialow = katalog_projektu / "materialy"
    katalog_materialow.mkdir(parents=True)
    for i in range(10):
        generuj.zdjecie_testowe(
            katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=(20, 20, 20),
        )


def renderuj_z_pomiarem_cpu(**kwargs) -> tuple[dict, float, float]:
    sumator: list[float] = []
    oryginalny = render.uruchom_ffmpeg
    render.uruchom_ffmpeg = lambda argumenty, katalog=None: uruchom_ffmpeg_z_limitem_i_benchmarkiem(sumator, argumenty, katalog)
    start_zegar = time.perf_counter()
    try:
        podsumowanie = render.renderuj(**kwargs)
    finally:
        render.uruchom_ffmpeg = oryginalny
    czas_zegara_s = time.perf_counter() - start_zegar
    return podsumowanie, round(sum(sumator), 3), round(czas_zegara_s, 3)


def sekcja_b() -> dict:
    wzor = wzor_syntetyczny_do_narzutu()
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        zbuduj_projekt_syntetyczny(katalog_projektu)
        wzor_json = katalog_tymczasowy / "wzor.json"
        wzor_json.write_text(json.dumps(wzor), encoding="utf-8")
        utwor = katalog_tymczasowy / "klik.wav"
        generuj.klik(utwor, bpm=128, czas_s=20.0, pierwsze_uderzenie_s=0.3)

        wyjscie_bez = katalog_tymczasowy / "bez.mp4"
        _, cpu_bez_s, zegar_bez_s = renderuj_z_pomiarem_cpu(
            wzor_json=wzor_json, katalog_projektu=katalog_projektu, utwor=utwor, wyjscie=wyjscie_bez,
            szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200,
        )
        print(f"B bez slow i pionowego: cpu {cpu_bez_s} s, zegar {zegar_bez_s} s")

        zapisz_projekt_json(katalog_projektu)
        wyjscie_z = katalog_tymczasowy / "z_rytmem.mp4"
        podsumowanie, cpu_z_s, zegar_z_s = renderuj_z_pomiarem_cpu(
            wzor_json=wzor_json, katalog_projektu=katalog_projektu, utwor=utwor, wyjscie=wyjscie_z,
            szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200,
        )
        narzut_procent = round((cpu_z_s - cpu_bez_s) / cpu_bez_s * 100, 1) if cpu_bez_s > 0 else None
        print(f"B ze slowami i pionowym: cpu {cpu_z_s} s ({narzut_procent}%), zegar {zegar_z_s} s")

    return {
        "bez_rytmu": {"cpu_s": cpu_bez_s, "zegar_s": zegar_bez_s},
        "z_rytmem": {"cpu_s": cpu_z_s, "zegar_s": zegar_z_s},
        "narzut_cpu_procent": narzut_procent,
        "uwaga": "tylko raport, bez progu (decyzja wlasciciela 2026-09-24)",
    }


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


def zbuduj_arkusz_klatek(wynik_0923: Path, zrodlo_0923: Path) -> Path | None:
    if not zrodlo_0923.is_file():
        return None
    komorka = (240, 427)
    wiersze = []
    for czas_s in WZOR_PORONAWCZY_KLATKI_S:
        try:
            klatka_wzoru = cv2.resize(wyciagnij_klatke(zrodlo_0923, czas_s), komorka, interpolation=cv2.INTER_AREA)
        except RuntimeError:
            continue
        try:
            klatka_wyniku = cv2.resize(wyciagnij_klatke(wynik_0923, czas_s), komorka, interpolation=cv2.INTER_AREA)
        except RuntimeError:
            klatka_wyniku = np.zeros((komorka[1], komorka[0], 3), dtype=np.uint8)
        wiersze.append(np.hstack([klatka_wzoru, klatka_wyniku]))
    if not wiersze:
        return None
    siatka = np.vstack(wiersze)
    cel = KATALOG_OUTPUTS / "rytm_klatki.png"
    ok, bufor = cv2.imencode(".png", siatka)
    if not ok:
        raise RuntimeError("Nie udalo sie zakodowac arkusza rytm_klatki.png")
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(bufor.tobytes())
    return cel


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


def sekcja_c() -> dict:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("C pominieta: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("C pominieta: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}

    oryginalny = render.uruchom_ffmpeg
    render.uruchom_ffmpeg = uruchom_ffmpeg_z_limitem

    plansza = znajdz_plansze()
    wpisy = []
    wynik_0923 = None
    zrodlo_0923 = None
    try:
        with TemporaryDirectory() as katalog_tymczasowy:
            katalog_tymczasowy = Path(katalog_tymczasowy)
            katalog_projektu = katalog_tymczasowy / "projekt"
            zbuduj_materialy_realne(katalog_projektu / "materialy")
            zapisz_projekt_json(katalog_projektu)

            for sciezka in pliki_wzorow:
                nazwa = sciezka.stem
                wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
                wyjscie = KATALOG_OUTPUTS / f"rytm_zrodlo_{nazwa}.mp4"
                nakladka = magazyn.plik_zasobu(KATALOG_REPO / "dane", "nakladki", nazwa)
                if not wyjscie.is_file():
                    try:
                        render.renderuj(
                            wzor_json, katalog_projektu, None, wyjscie,
                            szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=KATALOG_MUZYKI,
                            plansza=plansza, nakladka=nakladka,
                        )
                    except subprocess.TimeoutExpired:
                        wpisy.append({"wzor": nazwa, "blad": f"przekroczono limit {LIMIT_RENDERU_S} s"})
                        print(f"C {nazwa}: BLAD przekroczono limit {LIMIT_RENDERU_S} s")
                        continue
                    except Exception as blad:
                        wpisy.append({"wzor": nazwa, "blad": str(blad)})
                        print(f"C {nazwa}: BLAD {blad}")
                        continue
                cel_arkusza = KATALOG_OUTPUTS / f"porownanie_rytm_{nazwa}.png"
                arkusz.arkusz_porownawczy(sciezka, wyjscie, cel_arkusza)
                wpisy.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
                print(f"C {nazwa}: arkusz {cel_arkusza.name}")
                if nazwa == "0923":
                    wynik_0923 = wyjscie
                    zrodlo_0923 = sciezka
    finally:
        render.uruchom_ffmpeg = oryginalny

    arkusz_klatek = None
    if wynik_0923 is not None:
        arkusz_klatek = zbuduj_arkusz_klatek(wynik_0923, zrodlo_0923)
        if arkusz_klatek:
            print(f"C: arkusz klatek {arkusz_klatek.name}")

    wyniki = {
        "wzory": wpisy,
        "arkusze_powstaly": bool(wpisy) and all("arkusz" in w for w in wpisy),
        "rytm_klatki": arkusz_klatek.name if arkusz_klatek else None,
    }
    return wyniki


def main() -> int:
    wyniki_a = sekcja_a()
    zapisz_sekcje("a", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("b", wyniki_b)

    wyniki_c = sekcja_c()
    zapisz_sekcje("c", wyniki_c)

    print("Pomiar zakonczony. B tylko raport (decyzja wlasciciela 2026-09-24). Wyglad C ocenia wlasciciel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
