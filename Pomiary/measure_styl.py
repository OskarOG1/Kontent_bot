import json
import subprocess
import sys
import time
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
# Sekcje B i C dopisuje zadanie 12.7.
# Wyniki zapisywane do outputs/pomiar_styl.json po kazdej sekcji.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))

from PIL import Image  # noqa: E402

import magazyn  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_styl.json"
KATALOG_NAGRAN = KATALOG_REPO / "dane" / "nagrania"
SZEROKOSC_ARKUSZA = 270
WYSOKOSC_ARKUSZA = 480

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


if __name__ == "__main__":
    sekcja_a()
