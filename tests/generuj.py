import colorsys
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile


def klik(sciezka_wav: Path, bpm: float, czas_s: float, pierwsze_uderzenie_s: float = 0.0, sr: int = 22050) -> list[float]:
    liczba_probek = int(round(czas_s * sr))
    sygnal = np.zeros(liczba_probek, dtype=np.float32)
    dlugosc_klika = int(0.03 * sr)
    t = np.arange(dlugosc_klika) / sr
    tlo = np.random.default_rng(0).uniform(-1.0, 1.0, dlugosc_klika)
    ziarno = (0.7 * np.cos(2 * np.pi * 1500 * t) + 0.3 * tlo) * np.exp(-t / 0.006)
    odstep = 60.0 / bpm
    czasy = []
    k = 0
    while True:
        czas = pierwsze_uderzenie_s + k * odstep
        poczatek = int(round(czas * sr))
        if poczatek >= liczba_probek:
            break
        koniec = min(poczatek + dlugosc_klika, liczba_probek)
        sygnal[poczatek:koniec] += ziarno[: koniec - poczatek].astype(np.float32)
        czasy.append(czas)
        k += 1
    sygnal = np.clip(sygnal * 0.9, -1.0, 1.0)
    soundfile.write(str(sciezka_wav), sygnal, sr, subtype="PCM_16")
    return czasy


def kolor_ujecia(numer: int) -> tuple[int, int, int]:
    odcien = (numer * 0.381966) % 1.0
    nasycenie = 0.9 if numer % 2 == 0 else 0.5
    jasnosc = 0.95 if numer % 2 == 0 else 0.35
    r, g, b = colorsys.hsv_to_rgb(odcien, nasycenie, jasnosc)
    return int(r * 255), int(g * 255), int(b * 255)


def ulamek_fps(fps: float) -> str:
    ulamek = Fraction(fps).limit_denominator(1001)
    return f"{ulamek.numerator}/{ulamek.denominator}"


def wideo_z_cieciami(
    sciezka: Path,
    ciecia_s: list[float],
    czas_s: float,
    fps: float = 30,
    rozmiar: tuple[int, int] = (270, 480),
    bpm: float | None = None,
    pierwsze_uderzenie_s: float = 0.0,
    blyski_s=(),
) -> None:
    sciezka = Path(sciezka)
    szerokosc, wysokosc = rozmiar
    liczba_klatek = int(round(czas_s * fps))
    granice = sorted({int(round(t * fps)) for t in ciecia_s if t > 0})
    granice = [g for g in granice if 0 < g < liczba_klatek]
    blyski = {int(round(t * fps)) for t in blyski_s}
    biala = np.full((wysokosc, szerokosc, 3), 255, dtype=np.uint8).tobytes()
    kolory = {}

    def klatka_ujecia(numer: int) -> bytes:
        if numer not in kolory:
            kolory[numer] = np.full((wysokosc, szerokosc, 3), kolor_ujecia(numer), dtype=np.uint8).tobytes()
        return kolory[numer]

    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        argumenty = ["ffmpeg", "-y", "-loglevel", "error"]
        argumenty += [
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc}x{wysokosc}",
            "-framerate", ulamek_fps(fps), "-i", "pipe:0",
        ]
        if bpm is not None:
            sciezka_wav = katalog / "klik.wav"
            klik(sciezka_wav, bpm, czas_s, pierwsze_uderzenie_s)
            argumenty += ["-i", str(sciezka_wav)]
        argumenty += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p"]
        if bpm is not None:
            argumenty += ["-c:a", "aac", "-b:a", "128k"]
        else:
            argumenty += ["-an"]
        argumenty += ["-frames:v", str(liczba_klatek), str(sciezka)]

        with open(katalog / "stderr.txt", "wb") as plik_bledow:
            proces = subprocess.Popen(argumenty, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=plik_bledow)
            numer_ujecia = 0
            try:
                for klatka in range(liczba_klatek):
                    while numer_ujecia < len(granice) and klatka >= granice[numer_ujecia]:
                        numer_ujecia += 1
                    proces.stdin.write(biala if klatka in blyski else klatka_ujecia(numer_ujecia))
            except BrokenPipeError:
                pass
            finally:
                try:
                    proces.stdin.close()
                except BrokenPipeError:
                    pass
            kod = proces.wait()
        if kod != 0:
            blad = (katalog / "stderr.txt").read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {kod}: {blad}")
