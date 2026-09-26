import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 9 (fabryka), zadanie 9.4: warianty i partie.
# Sekcja A (syntetyczna): powtarzalnosc render.uloz_wariant (ten sam wariant 100 razy)
#   i roznorodnosc (12 materialow, warianty 1 do 5, sredni udzial ujec planu z innym
#   materialem niz w wariancie 0, na wzorze syntetycznym z 32 ujeciami).
# Sekcja B (syntetyczna): czas renderu wariantow 0, 1 i 2 syntetycznego projektu
#   1080x1920, 20 s, lokalnie, w sekundach renderu na sekunde wyniku. Tylko raport,
#   bez szacunku na serwer (decyzja wlasciciela, ROZWOJ.md).
# Sekcja C (prawdziwy wzor, gdy sa dane/wzory/*.mp4 i dane/muzyka): arkusze
#   porownawcze wariantow 0, 1 i 2 tego samego wzoru.
# render.uruchom_ffmpeg podmieniony w calym pomiarze na wersje z limitem czasu 900 s,
# jak w Pomiary/measure_rytm.py: zawieszony przebieg dalby TimeoutExpired zlapane jako
# blad wariantu, pomiar idzie dalej.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_fabryka.json"

LICZBA_UJEC_A = 32
LICZBA_MATERIALOW_A = 12
PROG_UDZIALU_INNYCH_PROCENT = 50.0

WYNIKI_CALOSC: dict = {}


def uruchom_ffmpeg_z_limitem(argumenty: list[str], katalog: Path | None = None) -> None:
    try:
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *argumenty],
            stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog, timeout=900,
        )
    except subprocess.TimeoutExpired as blad:
        raise RuntimeError("ffmpeg przekroczyl limit czasu 900 s") from blad
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")


render.uruchom_ffmpeg = uruchom_ffmpeg_z_limitem


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def materialy_syntetyczne(liczba: int) -> list[dict]:
    return [{"plik": f"m{i:02d}.jpg", "typ": "zdjecie", "message_id": i} for i in range(liczba)]


def udzial_innych_materialow(plan_bazowy: dict, plan_wariantu: dict) -> float:
    ujecia_bazowe = plan_bazowy["ujecia"]
    ujecia_wariantu = plan_wariantu["ujecia"]
    rozne = sum(1 for a, b in zip(ujecia_bazowe, ujecia_wariantu) if a["material"] != b["material"])
    return rozne / len(ujecia_bazowe)


def sekcja_a() -> dict:
    materialy = materialy_syntetyczne(LICZBA_MATERIALOW_A)

    powtorzenia = [render.uloz_wariant(materialy, 3) for _ in range(100)]
    powtarzalnosc = all(powtorzenie == powtorzenia[0] for powtorzenie in powtorzenia)

    wzor = {"ciecia_s": [float(i) for i in range(LICZBA_UJEC_A)], "zrodlo": {"czas_s": float(LICZBA_UJEC_A)}}
    plan_bazowy = render.plan_ujec(wzor, [], render.uloz_wariant(materialy, 0), fps=30)

    udzialy_procent = []
    for wariant in range(1, 6):
        plan_wariantu = render.plan_ujec(wzor, [], render.uloz_wariant(materialy, wariant), fps=30)
        udzialy_procent.append(round(udzial_innych_materialow(plan_bazowy, plan_wariantu) * 100, 2))
    sredni_udzial_procent = round(sum(udzialy_procent) / len(udzialy_procent), 2)

    wyniki = {
        "powtarzalnosc_100_probek": powtarzalnosc,
        "udzialy_innych_materialow_procent": udzialy_procent,
        "sredni_udzial_innych_materialow_procent": sredni_udzial_procent,
    }
    wyniki["progi"] = {
        "pelna_powtarzalnosc": powtarzalnosc,
        "sredni_udzial_co_najmniej_50_procent": sredni_udzial_procent >= PROG_UDZIALU_INNYCH_PROCENT,
    }
    print(f"A: {wyniki['progi']}, sredni udzial innych materialow {sredni_udzial_procent}%")
    return wyniki


def sekcja_b() -> dict:
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        katalog_materialow = katalog_projektu / "materialy"
        katalog_materialow.mkdir(parents=True)
        for i in range(6):
            generuj.zdjecie_testowe(katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))

        wzor_json = katalog_tymczasowy / "wzor.json"
        wzor_json.write_text(
            json.dumps({"ciecia_s": [i * 2.0 for i in range(10)], "zrodlo": {"czas_s": 20.0}}), encoding="utf-8",
        )
        utwor = katalog_tymczasowy / "klik.wav"
        generuj.klik(utwor, bpm=120, czas_s=20.0, pierwsze_uderzenie_s=0.0)

        warianty = []
        for wariant in (0, 1, 2):
            wyjscie = katalog_tymczasowy / f"wynik_{wariant}.mp4"
            start = time.time()
            render.renderuj(
                wzor_json, katalog_projektu, utwor, wyjscie,
                szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200, wariant=wariant,
            )
            czas_renderu_s = time.time() - start
            wskaznik = round(czas_renderu_s / 20.0, 3)
            warianty.append({
                "wariant": wariant, "czas_renderu_s": round(czas_renderu_s, 2), "renderu_na_sekunde_wyniku": wskaznik,
            })
            print(f"B wariant {wariant}: {czas_renderu_s:.1f} s ({wskaznik:.2f} s renderu na s wyniku)")

    wyniki = {"warianty": warianty}
    wyniki["progi"] = {"tylko_raport": True}
    print("B: tylko raport (decyzja wlasciciela 2026-09-24)")
    return wyniki


def znajdz_wzory_prawdziwe() -> list[Path]:
    katalog = KATALOG_REPO / "dane" / "wzory"
    if not katalog.is_dir():
        return []
    return sorted(p for p in katalog.glob("*.mp4") if p.is_file())


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
        from PIL import Image
        with Image.open(sciezka) as obraz:
            if obraz.mode != "RGBA":
                return False
            return obraz.getchannel("A").getextrema()[0] < 255
    except Exception:
        return False


def zbuduj_katalog_materialow(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    katalog_zdjec = KATALOG_REPO / "dane" / "zdjęcia"
    katalog_nagran = KATALOG_REPO / "dane" / "nagrania"
    katalog_bez_tla = KATALOG_REPO / "dane" / "zdjęcia_bez_tła"

    zdjecia = sorted(p for p in katalog_zdjec.glob("*") if p.is_file())[:8] if katalog_zdjec.is_dir() else []
    nagrania = sorted(p for p in katalog_nagran.glob("*") if p.is_file())[:4] if katalog_nagran.is_dir() else []
    bez_tla = []
    if katalog_bez_tla.is_dir():
        for plik in sorted(katalog_bez_tla.glob("*")):
            if plik.is_file() and ma_prawdziwa_alfa(plik):
                bez_tla.append(plik)
            if len(bez_tla) >= 2:
                break

    zrodla = zdjecia + nagrania + bez_tla
    if not zrodla:
        for i in range(8):
            generuj.zdjecie_testowe(
                katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i),
            )
        return

    for i, plik in enumerate(zrodla):
        cel = katalog_materialow / f"{i + 1:010d}_m{plik.suffix.lower()}"
        try:
            os.link(plik, cel)
        except OSError:
            shutil.copy(plik, cel)


def sekcja_c() -> dict:
    wzory = znajdz_wzory_prawdziwe()
    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    if not wzory or not katalog_muzyki.is_dir() or not music.pliki_muzyki(katalog_muzyki):
        print("C pominieta: brak dane/wzory/*.mp4 lub dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/wzory/*.mp4 lub dane/muzyka"}

    sciezka_wzoru = wzory[0]
    nazwa = sciezka_wzoru.stem
    wzor_json = wczytaj_lub_przeanalizuj_wzor(sciezka_wzoru)

    wpisy = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_projektu = katalog_tymczasowy / "projekt"
        zbuduj_katalog_materialow(katalog_projektu / "materialy")

        for wariant in (0, 1, 2):
            wyjscie = KATALOG_OUTPUTS / f"fabryka_zrodlo_{nazwa}_{wariant}.mp4"
            try:
                render.renderuj(
                    wzor_json, katalog_projektu, None, wyjscie,
                    szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200, muzyka=katalog_muzyki, wariant=wariant,
                )
            except Exception as blad:
                wpisy.append({"wariant": wariant, "blad": str(blad)})
                print(f"C {nazwa} wariant {wariant}: BLAD {blad}")
                continue
            cel_arkusza = KATALOG_OUTPUTS / f"porownanie_fabryka_{nazwa}_{wariant}.png"
            arkusz.arkusz_porownawczy(sciezka_wzoru, wyjscie, cel_arkusza)
            wpisy.append({"wariant": wariant, "arkusz": cel_arkusza.name})
            print(f"C {nazwa} wariant {wariant}: arkusz {cel_arkusza.name}")

    wyniki = {"wzor": nazwa, "warianty": wpisy}
    wyniki["progi"] = {"arkusze_powstaly": len(wpisy) == 3 and all("arkusz" in wpis for wpis in wpisy)}
    print(f"C: {wyniki['progi']}")
    return wyniki


def main() -> int:
    wyniki_a = sekcja_a()
    zapisz_sekcje("A", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("B", wyniki_b)

    wyniki_c = sekcja_c()
    zapisz_sekcje("C", wyniki_c)

    zaliczone = all(wyniki_a["progi"].values())
    if not wyniki_c.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_c["progi"].values())
    print("WYNIK A (i C gdy dostepne):", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
