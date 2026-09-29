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

# Pomiar czesci 12 (styl 0923 w renderze).
# Sekcja A (zadanie 12.1, pasy kinowe): kazdy klip z dane/nagrania/ przechodzi przez
#   render.wykryj_kadr, tak jak w renderze (6 klatek z calego klipu). Zapisywane: kadr
#   (ulamki x, y, w, h albo null), czas klipu i czas zegara wykrywania. Dla klipu z pasami
#   powstaje arkusz outputs/pasy_<klip>.png: klatka ze srodka klipu w kadrze 9:16 tak jak
#   w segmencie, po lewej bez przyciecia, po prawej z przycieciem. Werdykt na arkuszach
#   wydaje wlasciciel: po prawej nie ma czarnych pasow i nie brakuje tresci.
#   Bez katalogu dane/nagrania/ pomiar bierze trzy klipy z generatora: z pasami u gory
#   i u dolu, z ciemnym brzegiem tylko u gory i bez pasow (oczekiwane: tylko pierwszy
#   z kadrem).
#   Czas wykrywania to czas zegara (nie jest progiem, decyzja 18 w mapie). Na 4K HEVC
#   6 klatek to okolo 2,6 s na klip (pomiar 2026-09-27 na klipie syntetycznym).
# Sekcja B (zadanie 12.7): na kazdym z wzorow dane/wzory/*.mp4 dwa montaze na tej samej
#   bibliotece i muzyce: "auto" (automat, bez AI, nie wymaga klucza) i "ai" (rezyser i
#   krytyk jak w bocie, prog 7; tylko z OPENROUTER_API_KEY, przed pierwszym wywolaniem
#   modelu drukowany jest szacunek kosztu). Zapisywane: kolaze (ujecie, ruch tla, liczba
#   elementow, wejscie, miejsca), pominiete kolaze, okno gwiazd, przejscia, liczba ujec,
#   ostrzezenia, koszt AI, czas zegara. Progi: kazdy kolaz ma ruch tla najwyzej
#   render.PROG_RUCHU_KOLAZU, zaden kolaz nie zaczyna sie na dropie, zaden render nie
#   zakonczyl sie bledem (render.uruchom_ffmpeg ma limit 900 s na wywolanie).
# Sekcja C: arkusze outputs/porownanie_styl_<wzor>_auto.png i _ai.png (Pomiary/arkusz.py)
#   oraz probne edity outputs/styl_0923_auto.mp4 i outputs/styl_0923_ai.mp4. Werdykt na
#   arkuszach i edicie wydaje wlasciciel: wycinki na spokojnym tle, bez zaslaniania twarzy,
#   rytm i efekty jak w 0923, nie jego tresc.
# --procesy N: rendery (wzor x tryb) w N procesach naraz (spawn), jak w measure_rezyser.py.
# --tylko-a: tylko sekcja A.
# Wyniki zapisywane do outputs/pomiar_styl.json po kazdej sekcji.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))

from dotenv import load_dotenv  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(KATALOG_REPO / "tests"))

import arkusz  # noqa: E402
import generuj  # noqa: E402
import magazyn  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402
import rezyser  # noqa: E402

load_dotenv(KATALOG_REPO / ".env")

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_styl.json"
KATALOG_NAGRAN = KATALOG_REPO / "dane" / "nagrania"
SZEROKOSC_ARKUSZA = 270
WYSOKOSC_ARKUSZA = 480

KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"
KATALOG_MUZYKI = KATALOG_REPO / "dane" / "muzyka"
FPS = 30
LIMIT_FFMPEG_S = 900
PROG_OCENY_AI = 7
WZOR_PROBNEGO_EDITU = "0923"
MODEL_AI = os.environ.get("MODEL_AI") or "anthropic/claude-opus-5.5"
TRYBY = ("auto", "ai")

WYNIKI: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI, plik, ensure_ascii=False, indent=2)


def klip_lavfi(sciezka: Path, zrodlo: str, czas_s: float = 3.0) -> Path:
    subprocess.run(
        [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", zrodlo, "-t", str(czas_s),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "-an", str(sciezka),
        ],
        stdin=subprocess.DEVNULL, check=True,
    )
    return sciezka


def klipy_zastepcze(katalog: Path) -> list[Path]:
    # 1280x720 jak klip filmowy z YouTube: tresc 2,4:1 (1280x534) i pasy po 93 px.
    return [
        klip_lavfi(katalog / "z_pasami.mp4", "testsrc2=size=1280x534:rate=30,pad=w=1280:h=720:x=0:y=93:color=black"),
        klip_lavfi(katalog / "ciemna_gora.mp4", "testsrc2=size=1280x534:rate=30,pad=w=1280:h=720:x=0:y=186:color=black"),
        klip_lavfi(katalog / "bez_pasow.mp4", "testsrc2=size=1280x720:rate=30"),
    ]


def klatka_9_16(klip: Path, czas_s: float, kadr: dict | None) -> Image.Image:
    filtr = (
        f"{render.filtr_kadru(kadr)}scale={SZEROKOSC_ARKUSZA}:{WYSOKOSC_ARKUSZA}:force_original_aspect_ratio=increase,"
        f"crop={SZEROKOSC_ARKUSZA}:{WYSOKOSC_ARKUSZA}"
    )
    wynik = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{czas_s:.3f}", "-i", str(klip), "-frames:v", "1",
            "-vf", filtr, "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
        ],
        stdin=subprocess.DEVNULL, capture_output=True, check=True,
    )
    return Image.frombytes("RGB", (SZEROKOSC_ARKUSZA, WYSOKOSC_ARKUSZA), wynik.stdout)


def arkusz_pasow(klip: Path, czas_s: float, kadr: dict, cel: Path) -> None:
    arkusz = Image.new("RGB", (2 * SZEROKOSC_ARKUSZA + 10, WYSOKOSC_ARKUSZA), (40, 40, 40))
    arkusz.paste(klatka_9_16(klip, czas_s / 2, None), (0, 0))
    arkusz.paste(klatka_9_16(klip, czas_s / 2, kadr), (SZEROKOSC_ARKUSZA + 10, 0))
    arkusz.save(cel)


def sekcja_a() -> None:
    print("== Sekcja A: pasy kinowe")
    with TemporaryDirectory() as katalog_tymczasowy:
        if KATALOG_NAGRAN.is_dir():
            klipy = sorted(p for p in KATALOG_NAGRAN.iterdir() if p.is_file() and magazyn.typ_pliku(p.name, None) == "klip")
            zrodlo = "dane/nagrania"
        else:
            klipy = klipy_zastepcze(Path(katalog_tymczasowy))
            zrodlo = "generator"
        wpisy = []
        for klip in klipy:
            czas_s = render.czas_trwania(klip)
            if czas_s is None:
                wpisy.append({"plik": klip.name, "blad": "brak strumienia wideo"})
                continue
            start = time.perf_counter()
            kadr = render.wykryj_kadr(klip, czas_s)
            czas_wykrywania_s = time.perf_counter() - start
            wpis = {"plik": klip.name, "czas_klipu_s": round(czas_s, 2), "kadr": kadr, "czas_wykrywania_s": round(czas_wykrywania_s, 2)}
            if kadr is not None:
                cel = KATALOG_OUTPUTS / f"pasy_{klip.stem}.png"
                KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
                arkusz_pasow(klip, czas_s, kadr, cel)
                wpis["arkusz"] = str(cel.relative_to(KATALOG_REPO))
            wpisy.append(wpis)
            print(f"{klip.name}: kadr {kadr}, {czas_wykrywania_s:.2f} s")
        czasy = sorted(w["czas_wykrywania_s"] for w in wpisy if "czas_wykrywania_s" in w)
        WYNIKI["A"] = {
            "zrodlo": zrodlo,
            "klipy": wpisy,
            "z_pasami": sum(1 for w in wpisy if w.get("kadr")),
            "mediana_czasu_wykrywania_s": czasy[len(czasy) // 2] if czasy else None,
            "suma_czasu_wykrywania_s": round(sum(czasy), 2),
        }
        if zrodlo == "generator":
            WYNIKI["A"]["zgodnie_z_oczekiwaniem"] = [w["plik"] for w in wpisy if w.get("kadr")] == ["z_pasami.mp4"]
    zapisz_wyniki()
    print(json.dumps({k: v for k, v in WYNIKI["A"].items() if k != "klipy"}, ensure_ascii=False))


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


def ma_prawdziwa_alfa(sciezka: Path) -> bool:
    try:
        with Image.open(sciezka) as obraz:
            return obraz.mode == "RGBA" and obraz.getchannel("A").getextrema()[0] < 255
    except Exception:
        return False


def zbuduj_katalog_materialow(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    katalog_zdjec = KATALOG_REPO / "dane" / "zdjęcia"
    katalog_bez_tla = KATALOG_REPO / "dane" / "zdjęcia_bez_tła"
    zdjecia = sorted(p for p in katalog_zdjec.glob("*") if p.is_file())[:8] if katalog_zdjec.is_dir() else []
    nagrania = sorted(p for p in KATALOG_NAGRAN.glob("*") if p.is_file())[:4] if KATALOG_NAGRAN.is_dir() else []
    bez_tla = []
    if katalog_bez_tla.is_dir():
        bez_tla = [p for p in sorted(katalog_bez_tla.glob("*")) if p.is_file() and ma_prawdziwa_alfa(p)][:2]
    zrodla = zdjecia + nagrania + bez_tla
    if not zrodla:
        for i in range(8):
            generuj.zdjecie_testowe(katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))
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
            ai=tryb == "ai", model_ai=MODEL_AI, prog_oceny_ai=PROG_OCENY_AI,
        )
        dane_ai = podsumowanie.get("ai") or {}
        kolaze = podsumowanie.get("kolaze") or []
        wpis.update({
            "liczba_ujec": podsumowanie["liczba_ujec"],
            "drop_s": podsumowanie.get("drop_s"),
            "kolaze": [
                {
                    "ujecie": k["ujecie"], "start_s": k.get("start_s"), "ruch_tla": k["ruch"],
                    "elementow": len(k["miejsca"]), "wejscie": k.get("wejscie"), "miejsca": k["miejsca"],
                }
                for k in kolaze
            ],
            "kolaze_pominiete": podsumowanie.get("kolaze_pominiete") or [],
            "gwiazdy": podsumowanie.get("gwiazdy"),
            "przejscia": podsumowanie.get("przejscia") or [],
            "ostrzezenia": dane_ai.get("ostrzezenia") or [],
            "rezyser": dane_ai.get("rezyser"),
            "ocena": dane_ai.get("ocena"),
            "poprawka": dane_ai.get("poprawka"),
            "koszt_usd": dane_ai.get("koszt_usd"),
            "powod_pominiecia": dane_ai.get("powod_pominiecia"),
            "zegar_s": round(time.monotonic() - start, 2),
        })
        arkusz_cel = KATALOG_OUTPUTS / f"porownanie_styl_{nazwa}_{tryb}.png"
        try:
            arkusz.arkusz_porownawczy(zadanie["zrodlo"], wyjscie, arkusz_cel)
            wpis["arkusz"] = arkusz_cel.name
        except Exception as blad:
            print(f"{nazwa} {tryb}: arkusz nie powstal: {blad}")
        if nazwa == WZOR_PROBNEGO_EDITU:
            cel_probny = KATALOG_OUTPUTS / f"styl_0923_{tryb}.mp4"
            shutil.copy(wyjscie, cel_probny)
            wpis["probny_edit"] = cel_probny.name
    except Exception as blad:
        wpis["blad"] = str(blad)
        print(f"{nazwa} {tryb}: blad {blad}")
    print(f"{nazwa} {tryb}: gotowe")
    return wpis


def zloz_wpisy(wyniki: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    wedlug_wzoru: dict[str, dict] = {}
    arkusze = []
    probne = []
    for wpis in sorted(wyniki, key=lambda w: (w["wzor"], TRYBY.index(w["tryb"]))):
        wpis = dict(wpis)
        nazwa, tryb = wpis.pop("wzor"), wpis.pop("tryb")
        arkusz_nazwa = wpis.pop("arkusz", None)
        if arkusz_nazwa:
            arkusze.append(arkusz_nazwa)
        probny = wpis.pop("probny_edit", None)
        if probny:
            probne.append(probny)
        wedlug_wzoru.setdefault(nazwa, {"wzor": nazwa})[tryb] = wpis
    return list(wedlug_wzoru.values()), arkusze, probne


def sekcje_b_i_c(procesy: int, z_ai: bool) -> None:
    print("== Sekcje B i C: kolaze, gwiazdy, przejscia, arkusze")
    pliki_wzorow = sorted(KATALOG_WZOROW.glob("*.mp4")) if KATALOG_WZOROW.is_dir() else []
    if not pliki_wzorow or not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        powod = "brak dane/wzory" if not pliki_wzorow else "brak dane/muzyka"
        WYNIKI["B"] = {"pominieta": True, "powod": powod}
        WYNIKI["C"] = {"pominieta": True, "powod": powod}
        zapisz_wyniki()
        print(f"B/C pominiete: {powod}")
        return
    music.indeksuj(KATALOG_MUZYKI)
    nakladka, plansza, znak = znajdz_nakladke(), znajdz_plansze(), znajdz_znak()
    tryby = TRYBY if z_ai else ("auto",)
    wyniki: list[dict] = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        zadania = []
        for wzor_mp4 in pliki_wzorow:
            przygotowany = przygotuj_wzor(wzor_mp4, katalog_tymczasowy)
            if przygotowany is None:
                print(f"{wzor_mp4.stem}: brak outputs/wzor_{wzor_mp4.stem}.json, pomijam")
                continue
            wzor_json, zrodlo = przygotowany
            for tryb in tryby:
                zadania.append({
                    "nazwa": wzor_mp4.stem, "tryb": tryb, "wzor_json": wzor_json, "zrodlo": zrodlo,
                    "katalog": katalog_tymczasowy, "nakladka": nakladka, "plansza": plansza, "znak": znak,
                })

        def zapisz_postep() -> None:
            wpisy, _, _ = zloz_wpisy(wyniki)
            WYNIKI["B"] = {"w_toku": True, "wzory": wpisy}
            zapisz_wyniki()

        print(f"Renderow: {len(zadania)}, procesow naraz: {procesy}")
        if procesy > 1:
            with ProcessPoolExecutor(max_workers=procesy, mp_context=multiprocessing.get_context("spawn")) as wykonawca:
                for przyszly in as_completed([wykonawca.submit(zrenderuj_zadanie, z) for z in zadania]):
                    wyniki.append(przyszly.result())
                    zapisz_postep()
        else:
            for zadanie in zadania:
                wyniki.append(zrenderuj_zadanie(zadanie))
                zapisz_postep()

    wpisy, arkusze, probne = zloz_wpisy(wyniki)
    wpisy_renderow = [w[tryb] for w in wpisy for tryb in TRYBY if tryb in w]
    kolaze = [k for w in wpisy_renderow for k in w.get("kolaze", [])]
    na_dropie = [
        k for w in wpisy_renderow for k in w.get("kolaze", [])
        if w.get("drop_s") is not None and k.get("start_s") is not None and abs(k["start_s"] - w["drop_s"]) < 0.05
    ]
    koszty = [w["koszt_usd"] for w in wpisy_renderow if w.get("koszt_usd") is not None]
    WYNIKI["B"] = {
        "wzory": wpisy,
        "progi": {
            "ruch_tla_kazdego_kolazu_w_progu": all(k["ruch_tla"] <= render.PROG_RUCHU_KOLAZU for k in kolaze),
            "zaden_kolaz_na_dropie": not na_dropie,
            "zaden_render_bez_bledu_limitu": not any("blad" in w for w in wpisy_renderow),
        },
        "liczba_kolazy": len(kolaze),
        "koszt_ai_usd": round(sum(koszty), 4) if koszty else None,
        "tryby": list(tryby),
    }
    WYNIKI["C"] = {"arkusze": arkusze, "probne_edity": probne}
    zapisz_wyniki()
    print(json.dumps({k: v for k, v in WYNIKI["B"].items() if k != "wzory"}, ensure_ascii=False))
    print(f"Arkusze: {len(arkusze)}, probne edity: {probne}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--procesy", type=int, default=1, help="ile renderow naraz (domyslnie 1)")
    parser.add_argument("--tylko-a", action="store_true")
    argumenty = parser.parse_args()
    sekcja_a()
    if argumenty.tylko_a:
        return 0
    z_ai = bool(os.environ.get("OPENROUTER_API_KEY"))
    if z_ai:
        szacunek = rezyser.koszt_usd(MODEL_AI, 15000, 6000)
        szacunek_krytyka = rezyser.koszt_usd(MODEL_AI, 8000, 3000)
        print(f"Szacunek kosztu AI: rezyser {szacunek} USD, krytyk {szacunek_krytyka} USD za edit (z jedna poprawka do 2 krytykow)")
        if szacunek is not None and szacunek_krytyka is not None:
            liczba = len(list(KATALOG_WZOROW.glob("*.mp4"))) if KATALOG_WZOROW.is_dir() else 0
            print(f"Szacunek calego montazu z AI: okolo {round((szacunek + 2 * szacunek_krytyka) * liczba, 2)} USD")
    else:
        print("Brak OPENROUTER_API_KEY: montaz z AI pominiety, tylko automat")
    sekcje_b_i_c(max(1, argumenty.procesy), z_ai)
    print("Pomiar zakonczony.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
