import json
import math
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 8 (nakladka, plansza, drop).
# Sekcja A (prawdziwe wzory z dane/probki/wzory/): drop wykryty przez analyze.wykryj_drop
#   wobec przyblizonej referencji z arkuszy klatek (kontrakt czesci 8). Prog: w granicy 0,5 s
#   dla co najmniej 2 z 3 znanych wzorow. Pomijana, gdy brak dane/probki/wzory.
# Sekcja B (syntetyczna, zawsze dostepna): narzut czasu przebiegu koncowego (1080x1920, 20 s)
#   z nakladka w kazdym trybie (alfa, zielen, ekran) wobec przebiegu bez nakladki. Material to
#   szum (jak w pomiarze czesci 3), bo jednolity kolor koduje sie tak szybko, ze narzut nakladki
#   (dekodowanie i kompozycja drugiego wejscia) dominuje procentowo i nie odzwierciedla realnego
#   materialu.
# Sekcja C (prawdziwe wzory i biblioteka muzyki): render z nakladka i plansza dla kazdego
#   wzoru, arkusz porownawczy. Nakladka i plansza z dane/nakladki/, dane/plansze/ przez
#   magazyn.plik_zasobu (domyslna.*), a bez nich syntetyczne zastepniki zbudowane tutaj.
#   Pomijana, gdy brak dane/probki/wzory albo dane/muzyka.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import magazyn  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_nakladka.json"

ROZSZERZENIA_WZOROW = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
REFERENCJA_DROP_S = {"0915": 7.2, "0921": 5.5, "0922": 11.0}
PROG_DROPU_S = 0.5
PROG_NARZUTU_PROCENT = 40.0
ZIARNO_GWIAZD = 20260924

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def znajdz_wzory() -> list[Path]:
    katalog_wzorow = KATALOG_REPO / "dane" / "probki" / "wzory"
    if not katalog_wzorow.is_dir():
        return []
    return sorted(p for p in katalog_wzorow.glob("*") if p.suffix.lower() in ROZSZERZENIA_WZOROW)


def znajdz_biblioteke_muzyki() -> Path | None:
    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    if katalog_muzyki.is_dir() and music.pliki_muzyki(katalog_muzyki):
        return katalog_muzyki
    return None


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


def sekcja_a(pliki_wzorow: list[Path]) -> dict:
    if not pliki_wzorow:
        print("A pominieta: brak dane/probki/wzory")
        return {"pominieta": True, "powod": "brak dane/probki/wzory"}

    wpisy = []
    trafienia = 0
    ocenialne = 0
    for sciezka in pliki_wzorow:
        nazwa = sciezka.stem
        wzor = wczytaj_lub_przeanalizuj_wzor(sciezka)
        sekcje = wzor.get("sekcje")
        drop_s = sekcje.get("drop_s") if sekcje else None
        wpis = {"wzor": nazwa, "drop_s": drop_s, "drop_ujecie": sekcje.get("drop_ujecie") if sekcje else None}
        referencja = REFERENCJA_DROP_S.get(nazwa)
        if referencja is not None:
            wpis["referencja_s"] = referencja
            if drop_s is not None:
                blad = round(abs(drop_s - referencja), 3)
                wpis["blad_s"] = blad
                ocenialne += 1
                if blad <= PROG_DROPU_S:
                    trafienia += 1
        wpisy.append(wpis)
        print(f"A {nazwa}: {wpis}")

    wyniki = {"wzory": wpisy, "trafienia": trafienia, "ocenialne": ocenialne}
    wyniki["progi"] = {"co_najmniej_2_z_3_w_granicy_0_5s": trafienia >= 2}
    print(f"A: {wyniki['progi']}")
    return wyniki


def sekcja_b() -> dict:
    szerokosc, wysokosc, fps = 1080, 1920, 30
    czas_s = 20.0
    liczba_klatek = round(czas_s * fps)

    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        polaczone = katalog / "polaczone.mp4"
        generuj.szum(polaczone, czas_s=czas_s, rozmiar=(szerokosc, wysokosc), fps=fps)
        utwor = katalog / "utwor.wav"
        generuj.klik(utwor, 128, czas_s + 5.0)

        wynik_bez = katalog / "bez.mp4"
        start = time.monotonic()
        render.przebieg_koncowy(polaczone, utwor, 0.0, liczba_klatek, fps, wynik_bez, 200)
        czas_bez_s = time.monotonic() - start

        tryby = {}
        for tryb, rozszerzenie in (("alfa", "mov"), ("zielen", "mp4"), ("ekran", "mp4")):
            nakladka = katalog / f"nak_{tryb}.{rozszerzenie}"
            generuj.nakladka_testowa(nakladka, 2.0, tryb, rozmiar=(szerokosc, wysokosc), fps=fps)
            wykryty_tryb = render.tryb_nakladki(nakladka)
            wynik_z = katalog / f"z_{tryb}.mp4"
            start = time.monotonic()
            render.przebieg_koncowy(
                polaczone, utwor, 0.0, liczba_klatek, fps, wynik_z, 200,
                szerokosc=szerokosc, wysokosc=wysokosc,
                nakladka=nakladka, tryb_nakladki_wartosc=wykryty_tryb,
                nakladka_od_s=0.0, nakladka_do_s=czas_s,
            )
            czas_z_s = time.monotonic() - start
            narzut_procent = round((czas_z_s - czas_bez_s) / czas_bez_s * 100, 1)
            tryby[tryb] = {
                "wykryty_tryb": wykryty_tryb,
                "czas_z_s": round(czas_z_s, 2),
                "narzut_procent": narzut_procent,
            }
            print(f"B {tryb}: {tryby[tryb]}")

    wyniki = {"czas_bez_nakladki_s": round(czas_bez_s, 2), "tryby": tryby}
    wyniki["progi"] = {f"narzut_{tryb}_do_40_procent": dane["narzut_procent"] <= PROG_NARZUTU_PROCENT for tryb, dane in tryby.items()}
    print(f"B: {wyniki['progi']}")
    return wyniki


def gwiazda_punkty(cx: float, cy: float, promien_zewnetrzny: float, promien_wewnetrzny: float, obrot: float) -> list:
    punkty = []
    for i in range(10):
        kat = obrot + i * math.pi / 5
        promien = promien_zewnetrzny if i % 2 == 0 else promien_wewnetrzny
        punkty.append((cx + promien * math.sin(kat), cy - promien * math.cos(kat)))
    return punkty


def klatka_gwiazd(szerokosc: int, wysokosc: int, rng: random.Random) -> Image.Image:
    obraz = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
    rysownik = ImageDraw.Draw(obraz)
    liczba_gwiazd = max(8, (szerokosc * wysokosc) // 60000)
    for _ in range(liczba_gwiazd):
        cx = rng.uniform(0, szerokosc)
        cy = rng.uniform(0, wysokosc)
        promien = rng.uniform(min(szerokosc, wysokosc) * 0.01, min(szerokosc, wysokosc) * 0.03)
        punkty = gwiazda_punkty(cx, cy, promien, promien * 0.45, rng.uniform(0, math.pi))
        rysownik.polygon(punkty, fill=(255, 215, 0, 255))
    return obraz


def zbuduj_nakladke_gwiazd(cel: Path, szerokosc: int, wysokosc: int, fps: int = 30, czas_s: float = 1.0) -> None:
    rng = random.Random(ZIARNO_GWIAZD)
    obraz = klatka_gwiazd(szerokosc, wysokosc, rng)
    dane_klatki = np.array(obraz).tobytes()
    liczba_klatek = max(1, round(czas_s * fps))
    argumenty = [
        "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{szerokosc}x{wysokosc}",
        "-framerate", str(fps), "-i", "pipe:0",
        "-c:v", "png", "-pix_fmt", "rgba",
        "-frames:v", str(liczba_klatek), str(cel),
    ]
    proces = subprocess.run(argumenty, input=dane_klatki * liczba_klatek, capture_output=True)
    if proces.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {proces.returncode}: {proces.stderr.decode('utf-8', errors='replace')}")


def zbuduj_plansze_koniec(cel: Path, szerokosc: int = 1600, wysokosc: int = 900) -> None:
    obraz = Image.new("RGB", (szerokosc, wysokosc), (20, 20, 20))
    rysownik = ImageDraw.Draw(obraz)
    tekst = "KONIEC"
    try:
        czcionka = ImageFont.truetype("arial.ttf", 140)
    except OSError:
        czcionka = ImageFont.load_default()
    ramka = rysownik.textbbox((0, 0), tekst, font=czcionka)
    szerokosc_tekstu = ramka[2] - ramka[0]
    wysokosc_tekstu = ramka[3] - ramka[1]
    rysownik.text(
        ((szerokosc - szerokosc_tekstu) / 2 - ramka[0], (wysokosc - wysokosc_tekstu) / 2 - ramka[1]),
        tekst, font=czcionka, fill=(255, 255, 255),
    )
    obraz.save(cel)


def wybierz_lub_zbuduj_nakladke(katalog_danych: Path, wzor_id: str, katalog_tymczasowy: Path, szerokosc: int, wysokosc: int) -> Path:
    istniejaca = magazyn.plik_zasobu(katalog_danych, "nakladki", wzor_id)
    if istniejaca is not None:
        return istniejaca
    cel = katalog_tymczasowy / "nakladka_gwiazdy.mov"
    if not cel.exists():
        zbuduj_nakladke_gwiazd(cel, szerokosc, wysokosc)
    return cel


def wybierz_lub_zbuduj_plansze(katalog_danych: Path, wzor_id: str, katalog_tymczasowy: Path) -> Path:
    istniejaca = magazyn.plik_zasobu(katalog_danych, "plansze", wzor_id)
    if istniejaca is not None:
        return istniejaca
    cel = katalog_tymczasowy / "plansza_koniec.jpg"
    if not cel.exists():
        zbuduj_plansze_koniec(cel)
    return cel


def zbuduj_materialy_domyslne(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    for i in range(8):
        sciezka = katalog_materialow / f"{i + 1:010d}_m.jpg"
        generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))


def znajdz_katalog_materialow() -> Path | None:
    probki = KATALOG_REPO / "dane" / "probki" / "materialy"
    if probki.is_dir() and any(probki.iterdir()):
        return probki
    return None


def sekcja_c(pliki_wzorow: list[Path], katalog_muzyki) -> dict:
    if not pliki_wzorow:
        print("C pominieta: brak dane/probki/wzory")
        return {"pominieta": True, "powod": "brak dane/probki/wzory"}
    if katalog_muzyki is None:
        print("C pominieta: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}

    katalog_danych = KATALOG_REPO / "dane"
    wpisy = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_materialow_realny = znajdz_katalog_materialow()
        katalog_projektu = katalog_tymczasowy / "projekt"
        if katalog_materialow_realny is not None:
            (katalog_projektu / "materialy").mkdir(parents=True)
            for plik in katalog_materialow_realny.iterdir():
                if plik.is_file():
                    shutil.copy(plik, katalog_projektu / "materialy" / plik.name)
        else:
            zbuduj_materialy_domyslne(katalog_projektu / "materialy")

        for sciezka in pliki_wzorow:
            nazwa = sciezka.stem
            wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
            nakladka = wybierz_lub_zbuduj_nakladke(katalog_danych, nazwa, katalog_tymczasowy, 1080, 1920)
            plansza = wybierz_lub_zbuduj_plansze(katalog_danych, nazwa, katalog_tymczasowy)
            wyjscie = KATALOG_OUTPUTS / f"porownanie_zrodlo_nakladka_{nazwa}.mp4"
            try:
                render.renderuj(
                    wzor_json, katalog_projektu, None, wyjscie,
                    szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200, muzyka=katalog_muzyki,
                    nakladka=nakladka, plansza=plansza,
                )
            except Exception as blad:
                wpisy.append({"wzor": nazwa, "blad": str(blad)})
                print(f"C {nazwa}: BLAD {blad}")
                continue
            cel_arkusza = KATALOG_OUTPUTS / f"porownanie_nakladka_{nazwa}.png"
            arkusz.arkusz_porownawczy(sciezka, wyjscie, cel_arkusza)
            wpisy.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
            print(f"C {nazwa}: arkusz {cel_arkusza.name}")

    wyniki = {"wzory": wpisy}
    wyniki["progi"] = {"arkusze_powstaly": bool(wpisy) and all("arkusz" in w for w in wpisy)}
    print(f"C: {wyniki['progi']}")
    return wyniki


def main() -> int:
    pliki_wzorow = znajdz_wzory()
    katalog_muzyki = znajdz_biblioteke_muzyki()

    wyniki_a = sekcja_a(pliki_wzorow)
    zapisz_sekcje("A", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("B", wyniki_b)

    wyniki_c = sekcja_c(pliki_wzorow, katalog_muzyki)
    zapisz_sekcje("C", wyniki_c)

    zaliczone = all(wyniki_b["progi"].values())
    if not wyniki_a.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_a["progi"].values())
    if not wyniki_c.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_c["progi"].values())
    print("WYNIK B (i A, C gdy dostepne):", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
