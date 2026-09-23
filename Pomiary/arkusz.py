import math
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

# Arkusz porownawczy (decyzja 17): wiersz wzoru nad wierszem wyniku, te same ulamki
# dlugosci kazdego pliku, cienka jasna linia miedzy kolejnymi parami wierszy.


def czas_trwania_pliku(sciezka: Path) -> float:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return float(wynik.stdout.decode("utf-8", errors="replace").strip())


def wyciagnij_klatki(sciezka: Path, liczba_klatek: int, czas_pliku_s: float, komorka: tuple[int, int]) -> list:
    szerokosc, wysokosc = komorka
    fps = liczba_klatek / czas_pliku_s
    filtr = (
        f"fps={fps:.10f},"
        f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,"
        f"crop={szerokosc}:{wysokosc}"
    )
    with tempfile.TemporaryDirectory() as katalog:
        surowy = Path(katalog) / "klatki.raw"
        wynik = subprocess.run(
            [
                "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(sciezka),
                "-vf", filtr, "-frames:v", str(liczba_klatek),
                "-pix_fmt", "bgr24", "-f", "rawvideo", str(surowy),
            ],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0:
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
        dane = np.fromfile(surowy, dtype=np.uint8)
    liczba_odczytana = dane.size // (wysokosc * szerokosc * 3)
    if liczba_odczytana == 0:
        return []
    klatki = dane[: liczba_odczytana * wysokosc * szerokosc * 3].reshape(liczba_odczytana, wysokosc, szerokosc, 3)
    return [klatki[i] for i in range(liczba_odczytana)]


def arkusz_porownawczy(
    wzor: Path,
    wynik: Path,
    cel: Path,
    klatek_na_s: float = 2.0,
    kolumny: int = 16,
    komorka: tuple[int, int] = (108, 192),
) -> Path:
    wzor = Path(wzor)
    wynik = Path(wynik)
    cel = Path(cel)
    szerokosc, wysokosc = komorka

    czas_wzoru = czas_trwania_pliku(wzor)
    czas_wyniku = czas_trwania_pliku(wynik)
    n = math.ceil(max(czas_wzoru, czas_wyniku) * klatek_na_s)

    klatki_wzoru = wyciagnij_klatki(wzor, n, czas_wzoru, komorka)
    klatki_wyniku = wyciagnij_klatki(wynik, n, czas_wyniku, komorka)

    puste = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
    while len(klatki_wzoru) < n:
        klatki_wzoru.append(puste)
    while len(klatki_wyniku) < n:
        klatki_wyniku.append(puste)

    wiersze_grup = math.ceil(n / kolumny) if n else 0
    grubosc_linii = 2
    linia = np.full((grubosc_linii, kolumny * szerokosc, 3), 230, dtype=np.uint8)

    czesci = []
    for g in range(wiersze_grup):
        wycinek_wzoru = list(klatki_wzoru[g * kolumny:(g + 1) * kolumny])
        wycinek_wyniku = list(klatki_wyniku[g * kolumny:(g + 1) * kolumny])
        while len(wycinek_wzoru) < kolumny:
            wycinek_wzoru.append(puste)
        while len(wycinek_wyniku) < kolumny:
            wycinek_wyniku.append(puste)
        if g > 0:
            czesci.append(linia)
        czesci.append(np.hstack(wycinek_wzoru))
        czesci.append(np.hstack(wycinek_wyniku))

    siatka = np.vstack(czesci) if czesci else np.zeros((wysokosc, kolumny * szerokosc, 3), dtype=np.uint8)

    ok, bufor = cv2.imencode(".png", siatka)
    if not ok:
        raise RuntimeError("Nie udalo sie zakodowac arkusza")
    cel.parent.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(bufor.tobytes())
    return cel
