import colorsys
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile
from PIL import Image

ODWROTNA_TRANSPOZYCJA_EXIF = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_90,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_270,
}

OBROT_DO_K_ROT90 = {90: -1, 180: 2, 270: 1}


def profil_glosnosci(czas: float, glosnosc) -> float:
    if not glosnosc:
        return 1.0
    mnoznik = glosnosc[0][1]
    for od_s, wartosc in glosnosc:
        if czas >= od_s:
            mnoznik = wartosc
        else:
            break
    return mnoznik


def klik(
    sciezka_wav: Path,
    bpm: float,
    czas_s: float,
    pierwsze_uderzenie_s: float = 0.0,
    sr: int = 22050,
    glosnosc=None,
) -> list[float]:
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
        mnoznik = profil_glosnosci(czas, glosnosc)
        sygnal[poczatek:koniec] += (ziarno[: koniec - poczatek] * mnoznik).astype(np.float32)
        czasy.append(czas)
        k += 1
    sygnal = np.clip(sygnal * 0.9, -1.0, 1.0)
    soundfile.write(str(sciezka_wav), sygnal, sr, subtype="PCM_16")
    return czasy


def melodia(
    sciezka_wav: Path,
    bpm: float,
    czas_s: float,
    ziarno: int = 0,
    sr: int = 22050,
    glosnosc=None,
) -> list[float]:
    liczba_probek = int(round(czas_s * sr))
    sygnal = np.zeros(liczba_probek, dtype=np.float32)
    dlugosc_klika = int(0.03 * sr)
    tk = np.arange(dlugosc_klika) / sr
    generator = np.random.default_rng(ziarno)
    tlo = generator.uniform(-1.0, 1.0, dlugosc_klika)
    ziarno_klika = (0.7 * np.cos(2 * np.pi * 1500 * tk) + 0.3 * tlo) * np.exp(-tk / 0.006)
    odstep = 60.0 / bpm
    dlugosc_tonu = max(1, int(round(0.5 * odstep * sr)))
    tt = np.arange(dlugosc_tonu) / sr
    obwiednia_tonu = np.exp(-tt / max(1e-6, 0.5 * odstep * 0.3))
    czasy = []
    k = 0
    while True:
        czas = k * odstep
        poczatek = int(round(czas * sr))
        if poczatek >= liczba_probek:
            break
        mnoznik = profil_glosnosci(czas, glosnosc)
        koniec_klika = min(poczatek + dlugosc_klika, liczba_probek)
        sygnal[poczatek:koniec_klika] += (ziarno_klika[: koniec_klika - poczatek] * mnoznik).astype(np.float32)
        polton = int(generator.integers(0, 24))
        czestotliwosc = 220.0 * (2 ** (polton / 12))
        ton = np.sin(2 * np.pi * czestotliwosc * tt) * obwiednia_tonu
        koniec_tonu = min(poczatek + dlugosc_tonu, liczba_probek)
        sygnal[poczatek:koniec_tonu] += (ton[: koniec_tonu - poczatek] * mnoznik * 0.5).astype(np.float32)
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
    dzwiek: Path | None = None,
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
        ma_dzwiek = dzwiek is not None or bpm is not None
        if dzwiek is not None:
            argumenty += ["-i", str(dzwiek)]
        elif bpm is not None:
            sciezka_wav = katalog / "klik.wav"
            klik(sciezka_wav, bpm, czas_s, pierwsze_uderzenie_s)
            argumenty += ["-i", str(sciezka_wav)]
        argumenty += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p"]
        if ma_dzwiek:
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


def nakladka_testowa(
    sciezka: Path,
    czas_s: float,
    tryb: str,
    rozmiar: tuple[int, int] = (270, 480),
    fps: float = 30,
) -> None:
    sciezka = Path(sciezka)
    szerokosc, wysokosc = rozmiar
    polowa = wysokosc // 2
    liczba_klatek = max(1, int(round(czas_s * fps)))

    if tryb == "png":
        obraz = Image.new("RGBA", rozmiar, (0, 0, 0, 0))
        obraz.paste(Image.new("RGBA", (szerokosc, polowa), (220, 30, 30, 255)), (0, 0))
        obraz.save(sciezka)
        return

    if tryb == "alfa":
        klatka = np.zeros((wysokosc, szerokosc, 4), dtype=np.uint8)
        klatka[:polowa] = (220, 30, 30, 255)
        klatka[polowa:] = (0, 0, 0, 0)
        dane_klatki = klatka.tobytes()
        argumenty_wejscia = ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{szerokosc}x{wysokosc}", "-framerate", ulamek_fps(fps), "-i", "pipe:0"]
        argumenty_kodowania = ["-c:v", "png", "-pix_fmt", "rgba"]
    elif tryb == "zielen":
        klatka = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
        klatka[:polowa] = (220, 30, 30)
        klatka[polowa:] = (0, 255, 0)
        dane_klatki = klatka.tobytes()
        argumenty_wejscia = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc}x{wysokosc}", "-framerate", ulamek_fps(fps), "-i", "pipe:0"]
        argumenty_kodowania = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p"]
    elif tryb == "ekran":
        klatka = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
        klatka[:polowa] = (255, 255, 255)
        klatka[polowa:] = (0, 0, 0)
        dane_klatki = klatka.tobytes()
        argumenty_wejscia = ["-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc}x{wysokosc}", "-framerate", ulamek_fps(fps), "-i", "pipe:0"]
        argumenty_kodowania = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p"]
    else:
        raise ValueError(f"Nieznany tryb nakladki: {tryb}")

    argumenty = ["ffmpeg", "-y", "-loglevel", "error", *argumenty_wejscia, *argumenty_kodowania, "-an", "-frames:v", str(liczba_klatek), str(sciezka)]
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        with open(katalog / "stderr.txt", "wb") as plik_bledow:
            proces = subprocess.Popen(argumenty, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=plik_bledow)
            try:
                for _ in range(liczba_klatek):
                    proces.stdin.write(dane_klatki)
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


def zdjecie_testowe(
    sciezka: Path,
    rozmiar: tuple[int, int] = (1200, 1600),
    orientacja_exif: int = 1,
    alfa: bool = False,
    kolor: tuple[int, int, int] | None = None,
) -> None:
    sciezka = Path(sciezka)
    szerokosc, wysokosc = rozmiar
    tryb = "RGBA" if alfa else "RGB"
    if kolor is not None:
        piksele = tuple(kolor) + ((255,) if alfa else ())
        obraz = Image.new(tryb, rozmiar, piksele)
    else:
        obraz = Image.new(tryb, rozmiar)
        polowa = wysokosc // 2
        gorna = (220, 30, 30) + ((255,) if alfa else ())
        dolna = (30, 30, 220) + ((255,) if alfa else ())
        obraz.paste(Image.new(tryb, (szerokosc, polowa), gorna), (0, 0))
        obraz.paste(Image.new(tryb, (szerokosc, wysokosc - polowa), dolna), (0, polowa))
    if alfa:
        maska = Image.new("L", rozmiar, 255)
        rog = max(1, min(szerokosc, wysokosc) // 4)
        maska.paste(0, (0, 0, rog, rog))
        obraz.putalpha(maska)
    if orientacja_exif in ODWROTNA_TRANSPOZYCJA_EXIF:
        obraz = obraz.transpose(ODWROTNA_TRANSPOZYCJA_EXIF[orientacja_exif])
    exif = obraz.getexif()
    exif[0x0112] = orientacja_exif
    obraz.save(sciezka, exif=exif)


def klip_testowy(
    sciezka: Path,
    czas_s: float,
    rozmiar: tuple[int, int] = (480, 270),
    obrot: int = 0,
    fps: float = 30,
    kolor: tuple[int, int, int] | None = None,
) -> None:
    sciezka = Path(sciezka)
    szerokosc, wysokosc = rozmiar
    liczba_klatek = max(1, int(round(czas_s * fps)))
    if kolor is not None:
        klatka_wyswietlana = np.full((wysokosc, szerokosc, 3), kolor, dtype=np.uint8)
    else:
        klatka_wyswietlana = np.zeros((wysokosc, szerokosc, 3), dtype=np.uint8)
        polowa = wysokosc // 2
        klatka_wyswietlana[:polowa] = (220, 30, 30)
        klatka_wyswietlana[polowa:] = (30, 30, 220)
    if obrot:
        klatka_surowa = np.rot90(klatka_wyswietlana, k=OBROT_DO_K_ROT90[obrot])
    else:
        klatka_surowa = klatka_wyswietlana
    wysokosc_surowa, szerokosc_surowa = klatka_surowa.shape[:2]
    dane_klatki = np.ascontiguousarray(klatka_surowa).tobytes()

    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        plik_surowy = katalog / "surowy.mp4"
        argumenty = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc_surowa}x{wysokosc_surowa}",
            "-framerate", ulamek_fps(fps), "-i", "pipe:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "-an",
            "-frames:v", str(liczba_klatek), str(plik_surowy),
        ]
        with open(katalog / "stderr_kodowanie.txt", "wb") as plik_bledow:
            proces = subprocess.Popen(argumenty, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=plik_bledow)
            try:
                for _ in range(liczba_klatek):
                    proces.stdin.write(dane_klatki)
            except BrokenPipeError:
                pass
            finally:
                try:
                    proces.stdin.close()
                except BrokenPipeError:
                    pass
            kod = proces.wait()
        if kod != 0:
            blad = (katalog / "stderr_kodowanie.txt").read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {kod}: {blad}")

        if obrot:
            argumenty_remux = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-display_rotation", str(obrot), "-i", str(plik_surowy),
                "-c", "copy", str(sciezka),
            ]
            wynik = subprocess.run(argumenty_remux, stdin=subprocess.DEVNULL, capture_output=True)
            if wynik.returncode != 0:
                raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
        else:
            shutil.copyfile(plik_surowy, sciezka)


def szum(sciezka: Path, czas_s: float, rozmiar: tuple[int, int], fps: float = 30) -> None:
    sciezka = Path(sciezka)
    szerokosc, wysokosc = rozmiar
    liczba_klatek = max(1, int(round(czas_s * fps)))
    generator = np.random.default_rng(0)
    argumenty = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{szerokosc}x{wysokosc}",
        "-framerate", ulamek_fps(fps), "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", "-an",
        "-frames:v", str(liczba_klatek), str(sciezka),
    ]
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog = Path(katalog_tymczasowy)
        with open(katalog / "stderr.txt", "wb") as plik_bledow:
            proces = subprocess.Popen(argumenty, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=plik_bledow)
            try:
                for _ in range(liczba_klatek):
                    klatka = generator.integers(0, 256, (wysokosc, szerokosc, 3), dtype=np.uint8)
                    proces.stdin.write(klatka.tobytes())
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
