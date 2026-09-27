import argparse
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 11 (rezyser i krytyk AI), zadanie 11.4.
# Bez OPENROUTER_API_KEY w srodowisku caly pomiar konczy sie natychmiast, wynik
#   {"pominiety": "brak klucza"}, kod 0 (pomiar wydaje prawdziwe pieniadze, wiec
#   nigdy nie probuje wywolania bez klucza).
# Przed pierwszym wywolaniem modelu drukowany jest szacunek kosztu jednego edytu
#   z rezyser.koszt_usd na przewidywanych tokenach z planu czesci 11 (rezyser
#   ok. 15000 wejscia/6000 wyjscia, krytyk ok. 8000/3000) i szacunek calego pomiaru.
# Sekcja A: na kazdym z 5 prawdziwych wzorow (dane/wzory/*.mp4) dwa montaze na tej
#   samej bibliotece i muzyce:
#   - "auto": montaz automatyczny z czesci 10 (render z --ai i --bez-rezysera, prog
#     oceny 1), wiec krytyk tylko go ocenia, bez poprawki. Montaz jest ten sam co bez --ai;
#   - "ai": rezyser i krytyk z jedna poprawka, jak w bocie (prog 7).
#   Zapisywane: ocena krytyka (dla ai tez ocena przed poprawka), liczba ujec, uzyte
#   materialy, liczba ostrzezen scenariusza, tokeny wejscia/wyjscia, koszt USD, czas zegara.
#   Progi: scenariusz poprawny (bez przejscia na automat, tzn. podsumowanie["ai"]
#   ma rezyser=true) na co najmniej 4 z 5 wzorow; koszt jednego edytu z AI ponizej
#   1 USD. Laczny koszt pomiaru (z ocenami automatu) w wynikach.
# Sekcja C: dla kazdego wzoru outputs/porownanie_rezyser_<wzor>_auto.png i
#   outputs/porownanie_rezyser_<wzor>_ai.png (Pomiary/arkusz.py, ta sama warstwa
#   co czesci 4 do 9), do tego probny edit outputs/rezyser_0923.mp4 (kopia
#   wyniku AI dla wzoru 0923, jesli byl w probce). Werdykt na arkuszach i probnym
#   edicie wydaje wlasciciel, ocena krytyka to tylko dodatek.
# --procesy N: rendery (wzor x tryb, razem do 10) ida w N procesach naraz. Czekanie
#   na model naklada sie wtedy na rendery innych wzorow. ffmpeg sam uzywa kilku rdzeni,
#   a jeden render zajmuje okolo 1 GB pamieci, wiec na laptopie rozsadne N to 2 do 3.
#   Czas zegara pojedynczego renderu jest wtedy zawyzony przez rownolegla prace. Procesy startuja
#   metoda spawn na kazdym systemie, tak jak na Windows.
# render.uruchom_ffmpeg dostaje limit 900 s na wywolanie (jak w pomiarze czesci 10),
#   takze w procesach roboczych, bo podmiana stoi na poziomie modulu.
# Wyniki zapisywane do outputs/pomiar_rezyser.json po kazdym renderze.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

from dotenv import load_dotenv  # noqa: E402
from PIL import Image  # noqa: E402

import arkusz  # noqa: E402
import generuj  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402
import rezyser  # noqa: E402

load_dotenv(KATALOG_REPO / ".env")

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_rezyser.json"
KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"
KATALOG_MUZYKI = KATALOG_REPO / "dane" / "muzyka"

FPS = 30
LIMIT_FFMPEG_S = 900
PROG_OCENY_AI = 7
WZOR_PROBNEGO_EDITU = "0923"
MODEL_AI = os.environ.get("MODEL_AI") or "anthropic/claude-opus-5.5"
TRYBY = ("auto", "ai")

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def uruchom_ffmpeg_z_limitem(argumenty: list[str], katalog: Path | None = None) -> None:
    try:
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *argumenty],
            stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog, timeout=LIMIT_FFMPEG_S,
        )
    except subprocess.TimeoutExpired as blad:
        raise RuntimeError(f"ffmpeg przekroczyl limit czasu {LIMIT_FFMPEG_S} s") from blad
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")


render.uruchom_ffmpeg = uruchom_ffmpeg_z_limitem


def znajdz_wzory() -> list[Path]:
    if not KATALOG_WZOROW.is_dir():
        return []
    return sorted(p for p in KATALOG_WZOROW.glob("*.mp4"))


def ma_prawdziwa_alfa(sciezka: Path) -> bool:
    try:
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
        bez_tla = [p for p in sorted(katalog_bez_tla.glob("*")) if p.is_file() and ma_prawdziwa_alfa(p)][:2]

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


def zapisz_projekt_json(katalog_projektu: Path) -> None:
    dane = {"teksty": [], "slowa": "europe be like POLAND", "pionowo": "1993 supply made in poland"}
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


def przygotuj_wzor(wzor_mp4: Path, katalog_tymczasowy: Path) -> tuple[Path, Path] | None:
    # Krytyk szuka zrodlo.* obok wzor.json (jak w dane/wzory/<id>/ na serwerze), wiec wzor idzie
    # do wlasnego katalogu razem z kopia analizy z outputs/wzor_<nazwa>.json.
    nazwa = wzor_mp4.stem
    wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    if not wzor_json.is_file():
        return None
    katalog_wzoru = katalog_tymczasowy / f"wzor_{nazwa}"
    katalog_wzoru.mkdir(parents=True, exist_ok=True)
    zrodlo_lokalne = katalog_wzoru / f"zrodlo{wzor_mp4.suffix}"
    if not zrodlo_lokalne.is_file():
        try:
            os.link(wzor_mp4, zrodlo_lokalne)
        except OSError:
            shutil.copy(wzor_mp4, zrodlo_lokalne)
    wzor_json_lokalny = katalog_wzoru / "wzor.json"
    shutil.copy(wzor_json, wzor_json_lokalny)
    return wzor_json_lokalny, zrodlo_lokalne


def zrenderuj_zadanie(zadanie: dict) -> dict:
    # Jeden render (wzor x tryb). Funkcja na poziomie modulu, bo przy --procesy idzie
    # do ProcessPoolExecutor (na Windows proces roboczy importuje ten plik od nowa).
    nazwa, tryb = zadanie["nazwa"], zadanie["tryb"]
    katalog_projektu = Path(zadanie["katalog"]) / f"projekt_{nazwa}_{tryb}"
    wyjscie = Path(zadanie["katalog"]) / f"wynik_{nazwa}_{tryb}.mp4"
    wpis = {"wzor": nazwa, "tryb": tryb}
    try:
        zbuduj_katalog_materialow(katalog_projektu / "materialy")
        zapisz_projekt_json(katalog_projektu)
        start = time.monotonic()
        podsumowanie = render.renderuj(
            zadanie["wzor_json"], katalog_projektu, None, wyjscie,
            szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=KATALOG_MUZYKI,
            nakladka=zadanie["nakladka"], plansza=zadanie["plansza"], znak=zadanie["znak"],
            ai=True, model_ai=MODEL_AI,
            bez_rezysera=tryb == "auto", prog_oceny_ai=1 if tryb == "auto" else PROG_OCENY_AI,
        )
        dane_ai = podsumowanie.get("ai") or {}
        wpis.update({
            "liczba_ujec": podsumowanie["liczba_ujec"],
            "materialy_uzyte": podsumowanie["materialy_uzyte"],
            "ostrzezenia_scenariusza": len(dane_ai.get("ostrzezenia") or []),
            "ostrzezenia": dane_ai.get("ostrzezenia") or [],
            "rezyser": dane_ai.get("rezyser"),
            "ocena": dane_ai.get("ocena"),
            "ocena_przed": dane_ai.get("ocena_przed"),
            "poprawka": dane_ai.get("poprawka"),
            "tokeny_wejscia": dane_ai.get("tokeny_wejscia"),
            "tokeny_wyjscia": dane_ai.get("tokeny_wyjscia"),
            "koszt_usd": dane_ai.get("koszt_usd"),
            "powod_pominiecia": dane_ai.get("powod_pominiecia"),
            "zegar_s": round(time.monotonic() - start, 2),
        })

        arkusz_cel = KATALOG_OUTPUTS / f"porownanie_rezyser_{nazwa}_{tryb}.png"
        try:
            arkusz.arkusz_porownawczy(zadanie["zrodlo"], wyjscie, arkusz_cel)
            wpis["arkusz"] = arkusz_cel.name
        except Exception as blad:
            print(f"{nazwa} {tryb}: arkusz nie powstal: {blad}")

        if tryb == "ai" and nazwa == WZOR_PROBNEGO_EDITU:
            cel_probny = KATALOG_OUTPUTS / "rezyser_0923.mp4"
            shutil.copy(wyjscie, cel_probny)
            wpis["probny_edit"] = cel_probny.name
    except Exception as blad:
        wpis["blad"] = str(blad)
        print(f"{nazwa} {tryb}: blad {blad}")
    print(f"{nazwa} {tryb}: gotowe")
    return wpis


def zloz_wpisy(wyniki: list[dict]) -> tuple[list[dict], list[str]]:
    wedlug_wzoru: dict[str, dict] = {}
    pliki_c = []
    for wpis in sorted(wyniki, key=lambda w: (w["wzor"], TRYBY.index(w["tryb"]))):
        wpis = dict(wpis)
        nazwa, tryb = wpis.pop("wzor"), wpis.pop("tryb")
        wpis_wzoru = wedlug_wzoru.setdefault(nazwa, {"wzor": nazwa})
        arkusz_nazwa = wpis.pop("arkusz", None)
        if arkusz_nazwa:
            wpis_wzoru.setdefault("arkusze", []).append(arkusz_nazwa)
        probny = wpis.pop("probny_edit", None)
        if probny:
            pliki_c.append(probny)
        wpis_wzoru[tryb] = wpis
    return list(wedlug_wzoru.values()), pliki_c


def sekcja_a_i_c(procesy: int) -> tuple[dict, dict]:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("A/C pominiete: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}, {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("A/C pominiete: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}, {"pominieta": True, "powod": "brak dane/muzyka"}

    music.indeksuj(KATALOG_MUZYKI)

    nakladka = znajdz_nakladke()
    plansza = znajdz_plansze()
    znak = znajdz_znak()

    wyniki: list[dict] = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        zadania = []
        for wzor_mp4 in pliki_wzorow:
            przygotowany = przygotuj_wzor(wzor_mp4, katalog_tymczasowy)
            if przygotowany is None:
                print(f"{wzor_mp4.stem}: brak outputs/wzor_{wzor_mp4.stem}.json, pomijam (analiza spoza tego pomiaru)")
                continue
            wzor_json, zrodlo = przygotowany
            for tryb in TRYBY:
                zadania.append({
                    "nazwa": wzor_mp4.stem, "tryb": tryb, "wzor_json": wzor_json, "zrodlo": zrodlo,
                    "katalog": katalog_tymczasowy, "nakladka": nakladka, "plansza": plansza, "znak": znak,
                })

        def zapisz_postep() -> None:
            wpisy, _ = zloz_wpisy(wyniki)
            zapisz_sekcje("A", {"w_toku": True, "wzory": wpisy})

        print(f"Renderow: {len(zadania)}, procesow naraz: {procesy}")
        if procesy > 1:
            with ProcessPoolExecutor(max_workers=procesy, mp_context=multiprocessing.get_context("spawn")) as wykonawca:
                przyszle = [wykonawca.submit(zrenderuj_zadanie, zadanie) for zadanie in zadania]
                for przyszly in as_completed(przyszle):
                    wyniki.append(przyszly.result())
                    zapisz_postep()
        else:
            for zadanie in zadania:
                wyniki.append(zrenderuj_zadanie(zadanie))
                zapisz_postep()

    wpisy, pliki_c = zloz_wpisy(wyniki)
    return {"wzory": wpisy}, {"pliki": pliki_c}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procesy", type=int, default=1, help="ile renderow naraz (domyslnie 1, po kolei)")
    argumenty = parser.parse_args()
    procesy = max(1, argumenty.procesy)

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Pomiar pominiety: brak OPENROUTER_API_KEY (pomiar wydaje prawdziwe pieniadze)")
        zapisz_sekcje("wynik", {"pominiety": "brak klucza"})
        return 0

    szacunek_rezysera = rezyser.koszt_usd(MODEL_AI, 15000, 6000)
    szacunek_krytyka = rezyser.koszt_usd(MODEL_AI, 8000, 3000)
    print(f"Szacunek kosztu: rezyser {szacunek_rezysera} USD, krytyk {szacunek_krytyka} USD za edit (jedna poprawka podwaja krytyka)")
    if szacunek_rezysera is not None and szacunek_krytyka is not None:
        na_wzor = szacunek_rezysera + 3 * szacunek_krytyka
        print(f"Szacunek calego pomiaru: najwyzej {round(na_wzor * len(znajdz_wzory()), 2)} USD (na wzor: rezyser, 2 oceny AI, ocena automatu)")

    wyniki_a, wyniki_c = sekcja_a_i_c(procesy)
    zapisz_sekcje("A", wyniki_a)
    zapisz_sekcje("C", wyniki_c)

    if not wyniki_a.get("pominieta"):
        wzory = wyniki_a.get("wzory", [])
        poprawne = sum(1 for w in wzory if (w.get("ai") or {}).get("rezyser"))
        koszty_ai = [w["ai"]["koszt_usd"] for w in wzory if (w.get("ai") or {}).get("koszt_usd") is not None]
        koszty_wszystkie = [
            w[tryb]["koszt_usd"] for w in wzory for tryb in TRYBY if (w.get(tryb) or {}).get("koszt_usd") is not None
        ]
        progi = {
            "scenariusz_poprawny_co_najmniej_4_z_5": poprawne >= 4,
            "koszt_edytu_ai_ponizej_1_usd": all(k < 1.0 for k in koszty_ai) if koszty_ai else None,
        }
        zapisz_sekcje("progi", progi)
        zapisz_sekcje("koszt_pomiaru_usd", round(sum(koszty_wszystkie), 4))
        print(f"Progi: {progi}, koszt pomiaru: {round(sum(koszty_wszystkie), 4)} USD")

    print("Pomiar zakonczony.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
