import argparse
import json
import random
import statistics
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import numpy
import pillow_heif
from PIL import Image, ImageOps

import analyze
import kolor
import magazyn
import music
import rezyser
import tekst

pillow_heif.register_heif_opener()

MNOZNIK_ROBOCZY_ZOOM = 2
ZOOM_MAKSYMALNY = 1.12
PARAMETRY_KODOWANIA_SEGMENTU = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
PROMIEN_ROZMYCIA_PLANSZY = 20
PIX_FMT_Z_ALFA = {
    "rgba", "bgra", "argb", "abgr",
    "yuva420p", "yuva422p", "yuva444p",
    "yuva420p9le", "yuva420p9be", "yuva420p10le", "yuva420p10be",
    "yuva420p16le", "yuva420p16be",
    "yuva422p9le", "yuva422p10le", "yuva444p9le", "yuva444p10le",
    "ya8", "ya16le", "ya16be",
    "gbrap", "gbrap10le", "gbrap10be", "gbrap12le", "gbrap12be", "gbrap16le", "gbrap16be",
    "rgba64le", "rgba64be", "bgra64le", "bgra64be",
}
PROG_ZIELENI = 0.3
PROG_CZERNI = 40
UDZIAL_CZERNI_EKRANU = 0.4
UDZIAL_SZEROKOSCI_ZNAKU = 0.51
POZYCJA_ZNAKU_PION = 0.8
KRYCIE_ZNAKU = 0.65
KRYCIE_NAKLADKI = 0.5
TEMPO_ZDJECIA_MIN_S = 0.30
TEMPO_KLIPU_MIN_S = 2.0
TEMPO_KLIPU_MAX_S = 3.2
DLUGOSC_WSTAWKI_S = 3.5
DLUGOSC_NAKLADKI_KRYCIE_S = 2.5
ZDJEC_MIEDZY_KLIPAMI = 3
SKALA_NAKLADKI_KRYCIE = 0.85
SILA_UDERZENIA_ZOOM = 0.12
KLATEK_UDERZENIA_ZOOM = 5
SILA_NAJAZDU = 0.35
KLATEK_NAJAZDU = 6
KLATEK_WSTRZASU = 15
FILTR_SMUGI = (
    "gblur=sigma=1:sigmaV=80:enable='lt(n,3)',"
    "gblur=sigma=1:sigmaV=35:enable='between(n,3,4)',"
    "gblur=sigma=1:sigmaV=12:enable='between(n,5,6)'"
)
FILTR_NAJAZDU = "gblur=sigma=18:enable='lt(n,3)'"
LINIA_ROZCIAGNIECIA = 0.45
KLATEK_ROZCIAGNIECIA = 10
KOTWICA_ZOOM = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
UDZIAL_SZEROKOSCI_KOLAZU = 0.55
UDZIAL_WYSOKOSCI_KOLAZU = 0.36
POLA_KOLAZU = ((0.30, 0.30), (0.70, 0.47), (0.38, 0.66))
WSKOK_SKALE_KOLAZU = (0.45, 0.85, 1.12, 1.05)
LICZBA_WYCINKOW_KOLAZU = 3
MINIMUM_KLIPU_KOLAZU_S = 1.5
PROG_KANALU_PASA = 40
UDZIAL_JASNYCH_W_PASIE = 0.02
MINIMUM_PASA = 0.02
MINIMUM_KADRU_BEZ_PASOW = 0.5
LICZBA_KLATEK_PASOW = 6
SZEROKOSC_KLATKI_PASOW = 320
ZAPAS_PASA = 2


def uruchom_ffmpeg(argumenty: list[str], katalog: Path | None = None) -> None:
    wynik = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True, cwd=katalog,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")


def ma_strumien_wideo(sciezka) -> bool:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return wynik.returncode == 0 and wynik.stdout.decode("utf-8", errors="replace").strip() != ""


def klatka_do_pasow(sciezka_zrodlowa, czas_s: float) -> numpy.ndarray | None:
    wynik = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{czas_s:.6f}", "-i", str(sciezka_zrodlowa),
            "-frames:v", "1", "-vf", f"scale={SZEROKOSC_KLATKI_PASOW}:-2", "-pix_fmt", "rgb24", "-f", "rawvideo", "-",
        ],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    bajty_wiersza = SZEROKOSC_KLATKI_PASOW * 3
    if wynik.returncode != 0 or not wynik.stdout or len(wynik.stdout) % bajty_wiersza != 0:
        return None
    return numpy.frombuffer(wynik.stdout, dtype=numpy.uint8).reshape(-1, SZEROKOSC_KLATKI_PASOW, 3)


def dlugosc_pasa(udzialy_jasnych) -> int:
    dlugosc = 0
    for udzial in udzialy_jasnych:
        if udzial > UDZIAL_JASNYCH_W_PASIE:
            break
        dlugosc += 1
    return dlugosc


def para_pasow(udzialy_jasnych) -> tuple[int, int]:
    rozmiar = len(udzialy_jasnych)
    pierwszy = dlugosc_pasa(udzialy_jasnych)
    drugi = dlugosc_pasa(udzialy_jasnych[::-1])
    if min(pierwszy, drugi) < MINIMUM_PASA * rozmiar:
        return 0, 0
    pierwszy, drugi = pierwszy + ZAPAS_PASA, drugi + ZAPAS_PASA
    if rozmiar - pierwszy - drugi < MINIMUM_KADRU_BEZ_PASOW * rozmiar:
        return 0, 0
    return pierwszy, drugi


def pasy_z_klatek(klatki: numpy.ndarray) -> tuple[int, int, int, int]:
    jasne = klatki.max(axis=3) > PROG_KANALU_PASA
    gora, dol = para_pasow(jasne.mean(axis=(0, 2)))
    lewo, prawo = para_pasow(jasne.mean(axis=(0, 1)))
    return gora, dol, lewo, prawo


def wykryj_kadr(sciezka_zrodlowa, czas_s: float) -> dict | None:
    klatki = []
    for indeks in range(LICZBA_KLATEK_PASOW):
        klatka = klatka_do_pasow(sciezka_zrodlowa, czas_s * (indeks + 0.5) / LICZBA_KLATEK_PASOW)
        if klatka is not None:
            klatki.append(klatka)
    if not klatki or len({klatka.shape for klatka in klatki}) != 1:
        return None
    stos = numpy.stack(klatki)
    gora, dol, lewo, prawo = pasy_z_klatek(stos)
    if gora == dol == lewo == prawo == 0:
        return None
    wysokosc, szerokosc = stos.shape[1:3]
    return {
        "x": round(lewo / szerokosc, 6),
        "y": round(gora / wysokosc, 6),
        "w": round((szerokosc - lewo - prawo) / szerokosc, 6),
        "h": round((wysokosc - gora - dol) / wysokosc, 6),
    }


def filtr_kadru(kadr: dict | None) -> str:
    if not kadr:
        return ""
    return (
        f"crop=trunc(iw*{kadr['w']:.6f}/2)*2:trunc(ih*{kadr['h']:.6f}/2)*2:"
        f"trunc(iw*{kadr['x']:.6f}/2)*2:trunc(ih*{kadr['y']:.6f}/2)*2,"
    )


def przygotuj_zdjecie(sciezka, katalog_pracy: Path, indeks: int, szerokosc: int, wysokosc: int) -> Path:
    obraz = Image.open(sciezka)
    obraz = ImageOps.exif_transpose(obraz)
    if obraz.mode in ("RGBA", "LA") or (obraz.mode == "P" and "transparency" in obraz.info):
        obraz = obraz.convert("RGBA")
        tlo = Image.new("RGB", obraz.size, (0, 0, 0))
        tlo.paste(obraz, mask=obraz.split()[-1])
        obraz = tlo
    else:
        obraz = obraz.convert("RGB")
    docelowa_szerokosc = szerokosc * MNOZNIK_ROBOCZY_ZOOM
    docelowa_wysokosc = wysokosc * MNOZNIK_ROBOCZY_ZOOM
    skala = max(docelowa_szerokosc / obraz.width, docelowa_wysokosc / obraz.height)
    if skala < 1.0:
        nowy_rozmiar = (max(1, round(obraz.width * skala)), max(1, round(obraz.height * skala)))
        obraz = obraz.resize(nowy_rozmiar, Image.LANCZOS)
    wyjscie = katalog_pracy / f"zdjecie_{indeks:04d}.png"
    obraz.save(wyjscie)
    return wyjscie


def wyrazenie_zoom(
    numer_ujecia: int, liczba_klatek: int, uderzenie: bool = False,
    sila_uderzenia: float = SILA_UDERZENIA_ZOOM, klatki_uderzenia: int = KLATEK_UDERZENIA_ZOOM,
) -> str:
    if liczba_klatek <= 1:
        krok = 0.0
    else:
        krok = (ZOOM_MAKSYMALNY - 1.0) / (liczba_klatek - 1)
    if not uderzenie:
        if numer_ujecia % 2 == 0:
            return f"min(zoom+{krok:.8f},{ZOOM_MAKSYMALNY})"
        return f"if(eq(on,0),{ZOOM_MAKSYMALNY},max(zoom-{krok:.8f},1.0))"
    if numer_ujecia % 2 == 0:
        baza = f"(1+{krok:.8f}*on)"
    else:
        baza = f"({ZOOM_MAKSYMALNY}-{krok:.8f}*on)"
    return f"{baza}*(1+{sila_uderzenia}*pow(max(0,1-on/{klatki_uderzenia}),2))"


def filtr_rozciagniecia(szerokosc: int, wysokosc: int, wejscie: str, wyjscie: str) -> str:
    linia = round(wysokosc * LINIA_ROZCIAGNIECIA / 2) * 2
    return (
        f"[{wejscie}]split[roz_a][roz_b];"
        f"[roz_b]crop={szerokosc}:2:0:{linia},scale={szerokosc}:{wysokosc - linia}:flags=neighbor,"
        f"format=yuva420p,fade=t=out:start_frame=0:nb_frames={KLATEK_ROZCIAGNIECIA}:alpha=1[roz_s];"
        f"[roz_a][roz_s]overlay=0:{linia}:enable='lt(n,{KLATEK_ROZCIAGNIECIA})',format=yuv420p[{wyjscie}]"
    )


def filtr_wstrzasu(szerokosc: int, wysokosc: int) -> str:
    return (
        f"scale=trunc(iw*1.08/2)*2:trunc(ih*1.08/2)*2,"
        f"crop={szerokosc}:{wysokosc}:"
        f"x='(iw-ow)/2+((iw-ow)/2)*sin(n*2.1)*max(0,1-n/{KLATEK_WSTRZASU})':"
        f"y='(ih-oh)/2+((ih-oh)/2)*cos(n*1.7)*max(0,1-n/{KLATEK_WSTRZASU})'"
    )


def efekt_ujecia(ujecie: dict, indeks: int, klatka_dropu: int | None, licznik_zdjec_montazu: int) -> dict:
    if indeks < 0:
        return {"uderzenie": False, "blysk_s": 0.0, "wstrzas": False, "przejscie": "najazd"}
    na_dropie = klatka_dropu is not None and ujecie["klatka_od"] == klatka_dropu
    if na_dropie:
        blysk_s, wstrzas = 0.30, True
    elif ujecie["typ"] == "klip":
        blysk_s, wstrzas = 0.10, False
    else:
        blysk_s, wstrzas = 0.0, False
    przejscie = "brak"
    po_dropie = klatka_dropu is not None and ujecie["klatka_od"] > klatka_dropu
    if indeks == 1 and not na_dropie:
        przejscie = "najazd"
    elif not na_dropie and ujecie["typ"] == "zdjecie" and po_dropie and licznik_zdjec_montazu % 3 == 0:
        przejscie = "smuga" if (licznik_zdjec_montazu // 3) % 2 == 1 else "rozciagniecie"
    return {"uderzenie": True, "blysk_s": blysk_s, "wstrzas": wstrzas, "przejscie": przejscie}


def filtr_przejscia(przejscie: str) -> str:
    if przejscie == "smuga":
        return f",{FILTR_SMUGI}"
    if przejscie == "najazd":
        return f",{FILTR_NAJAZDU}"
    return ""


def koncowka_segmentu(blysk_s: float) -> str:
    koncowka = f",fade=t=in:st=0:d={blysk_s}:color=white" if blysk_s > 0 else ""
    return koncowka + ",setsar=1"


def graf_z_rozciagnieciem(filtr: str, koncowka: str, szerokosc: int, wysokosc: int) -> str:
    return (
        f"[0:v]{filtr}[przed];"
        f"{filtr_rozciagniecia(szerokosc, wysokosc, 'przed', 'po')};"
        f"[po]{koncowka.lstrip(',')}"
    )


def segment_zdjecia(
    sciezka_przygotowana: Path, wyjscie: Path, numer_ujecia: int, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int,
    lut_sciezka: str | None = None, katalog: Path | None = None,
    uderzenie: bool = False, blysk_s: float = 0.0, wstrzas: bool = False, przejscie: str = "brak",
) -> None:
    szerokosc_robocza = szerokosc * MNOZNIK_ROBOCZY_ZOOM
    wysokosc_robocza = wysokosc * MNOZNIK_ROBOCZY_ZOOM
    najazd = przejscie == "najazd"
    if najazd:
        wyrazenie = wyrazenie_zoom(
            numer_ujecia, liczba_klatek, uderzenie=True, sila_uderzenia=SILA_NAJAZDU, klatki_uderzenia=KLATEK_NAJAZDU,
        )
    else:
        wyrazenie = wyrazenie_zoom(numer_ujecia, liczba_klatek, uderzenie=uderzenie)
    kotwica = f":{KOTWICA_ZOOM}" if uderzenie or najazd else ""
    filtr = (
        f"scale={szerokosc_robocza}:{wysokosc_robocza}:force_original_aspect_ratio=increase,"
        f"crop={szerokosc_robocza}:{wysokosc_robocza},"
        f"zoompan=z='{wyrazenie}'{kotwica}:d=1:s={szerokosc_robocza}x{wysokosc_robocza}:fps={fps},"
        f"scale={szerokosc}:{wysokosc}:flags=lanczos"
    )
    if lut_sciezka is not None:
        filtr += f",lut3d={lut_sciezka}"
    if wstrzas:
        filtr += f",{filtr_wstrzasu(szerokosc, wysokosc)}"
    filtr += filtr_przejscia(przejscie)
    koncowka = koncowka_segmentu(blysk_s)
    if przejscie == "rozciagniecie":
        argumenty_filtra = [
            "-filter_complex", f"{graf_z_rozciagnieciem(filtr, koncowka, szerokosc, wysokosc)}[baza]",
            "-map", "[baza]",
        ]
    else:
        argumenty_filtra = ["-vf", filtr + koncowka]
    uruchom_ffmpeg([
        "-loop", "1", "-i", str(sciezka_przygotowana),
        *argumenty_filtra,
        "-frames:v", str(liczba_klatek),
        "-an",
        *PARAMETRY_KODOWANIA_SEGMENTU,
        str(wyjscie),
    ], katalog=katalog)


def segment_klipu(
    sciezka_zrodlowa, wyjscie: Path, start_s: float, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int,
    lut_sciezka: str | None = None, katalog: Path | None = None,
    uderzenie: bool = False, blysk_s: float = 0.0, wstrzas: bool = False, przejscie: str = "brak",
    kolaz: Path | None = None, kadr: dict | None = None,
) -> None:
    filtr = (
        f"{filtr_kadru(kadr)}"
        f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,"
        f"crop={szerokosc}:{wysokosc},"
        f"fps={fps},"
        f"tpad=stop_mode=clone:stop=-1"
    )
    if uderzenie or przejscie == "najazd":
        sila, klatki = (SILA_NAJAZDU, KLATEK_NAJAZDU) if przejscie == "najazd" else (SILA_UDERZENIA_ZOOM, KLATEK_UDERZENIA_ZOOM)
        wyrazenie = f"(1+{sila}*pow(max(0,1-on/{klatki}),2))"
        filtr += f",zoompan=z='{wyrazenie}':{KOTWICA_ZOOM}:d=1:s={szerokosc}x{wysokosc}:fps={fps}"
    if lut_sciezka is not None:
        filtr += f",lut3d={lut_sciezka}"
    if wstrzas:
        filtr += f",{filtr_wstrzasu(szerokosc, wysokosc)}"
    filtr += filtr_przejscia(przejscie)
    koncowka = koncowka_segmentu(blysk_s)
    if przejscie == "rozciagniecie":
        graf_bazy = graf_z_rozciagnieciem(filtr, koncowka, szerokosc, wysokosc)
    else:
        graf_bazy = f"[0:v]{filtr}{koncowka}"
    if kolaz is None and przejscie != "rozciagniecie":
        uruchom_ffmpeg([
            "-ss", f"{start_s:.6f}", "-i", str(sciezka_zrodlowa),
            "-vf", filtr + koncowka,
            "-frames:v", str(liczba_klatek),
            "-an",
            *PARAMETRY_KODOWANIA_SEGMENTU,
            str(wyjscie),
        ], katalog=katalog)
    elif kolaz is None:
        uruchom_ffmpeg([
            "-ss", f"{start_s:.6f}", "-i", str(sciezka_zrodlowa),
            "-filter_complex", f"{graf_bazy}[baza]",
            "-map", "[baza]",
            "-frames:v", str(liczba_klatek),
            "-an",
            *PARAMETRY_KODOWANIA_SEGMENTU,
            str(wyjscie),
        ], katalog=katalog)
    else:
        filtr_complex = f"{graf_bazy}[baza];[1:v]format=rgba[nak];[baza][nak]overlay=format=auto[out]"
        uruchom_ffmpeg([
            "-ss", f"{start_s:.6f}", "-i", str(sciezka_zrodlowa),
            "-i", str(kolaz),
            "-filter_complex", filtr_complex,
            "-map", "[out]",
            "-frames:v", str(liczba_klatek),
            "-an",
            *PARAMETRY_KODOWANIA_SEGMENTU,
            str(wyjscie),
        ], katalog=katalog)


def obraz_do_statystyk(sciezka_przygotowana: Path, szerokosc: int = 270, wysokosc: int = 480) -> numpy.ndarray:
    with Image.open(sciezka_przygotowana) as obraz:
        obraz = obraz.convert("RGB")
        skala = max(szerokosc / obraz.width, wysokosc / obraz.height)
        nowy_rozmiar = (max(1, round(obraz.width * skala)), max(1, round(obraz.height * skala)))
        obraz = obraz.resize(nowy_rozmiar, Image.LANCZOS)
        lewo = (obraz.width - szerokosc) // 2
        gora = (obraz.height - wysokosc) // 2
        obraz = obraz.crop((lewo, gora, lewo + szerokosc, gora + wysokosc))
        return numpy.array(obraz)


def statystyki_zdjecia(sciezka_przygotowana: Path, szerokosc: int = 270, wysokosc: int = 480) -> dict:
    return kolor.statystyki_obrazu(obraz_do_statystyk(sciezka_przygotowana, szerokosc, wysokosc))


def probuj_klatke_klipu(argumenty_czasu: list[str], sciezka_zrodlowa, filtr: str, plik_klatki: Path) -> numpy.ndarray | None:
    try:
        uruchom_ffmpeg([*argumenty_czasu, "-i", str(sciezka_zrodlowa), "-vf", filtr, "-frames:v", "1", str(plik_klatki)])
    except RuntimeError:
        return None
    if not plik_klatki.exists():
        return None
    with Image.open(plik_klatki) as obraz:
        return numpy.array(obraz.convert("RGB"))


def statystyki_klipu(
    sciezka_zrodlowa, start_s: float, dlugosc_s: float, czas_klipu_s: float, szerokosc: int = 135, wysokosc: int = 240,
    kadr: dict | None = None,
) -> dict | None:
    filtr = f"{filtr_kadru(kadr)}scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,crop={szerokosc}:{wysokosc}"
    efektywna_dlugosc = min(dlugosc_s, czas_klipu_s - start_s)
    klatki = []
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        if efektywna_dlugosc > 0:
            for indeks, udzial in enumerate((0.25, 0.5, 0.75)):
                czas = start_s + efektywna_dlugosc * udzial
                klatka = probuj_klatke_klipu(["-ss", f"{czas:.6f}"], sciezka_zrodlowa, filtr, katalog_tymczasowy / f"klatka_{indeks}.png")
                if klatka is not None:
                    klatki.append(klatka)
        if not klatki:
            klatka = probuj_klatke_klipu(["-sseof", "-0.1"], sciezka_zrodlowa, filtr, katalog_tymczasowy / "ostatnia.png")
            if klatka is not None:
                klatki.append(klatka)
    if not klatki:
        return None
    return kolor.statystyki_obrazu(numpy.stack(klatki))


def segment_planszy(
    sciezka, wyjscie: Path, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int, przejscie: str = "brak",
) -> None:
    sciezka = Path(sciezka)
    wyjscie = Path(wyjscie)
    jest_zdjeciem = magazyn.typ_pliku(sciezka.name, None) == "zdjecie"

    tlo = f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,crop={szerokosc}:{wysokosc},boxblur={PROMIEN_ROZMYCIA_PLANSZY}:2"
    pierwszy_plan = f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=decrease,setsar=1"
    ogon = f",fps={fps}"
    if przejscie == "najazd":
        wyrazenie = f"(1+{SILA_NAJAZDU}*pow(max(0,1-on/{KLATEK_NAJAZDU}),2))"
        ogon += (
            f",zoompan=z='{wyrazenie}':{KOTWICA_ZOOM}:d=1:s={szerokosc}x{wysokosc}:fps={fps},"
            f"{FILTR_NAJAZDU}"
        )
    if not jest_zdjeciem:
        ogon += ",tpad=stop_mode=clone:stop=-1"
    ogon += ",setsar=1[out]"
    filtr = f"[0:v]split=2[a][b];[a]{tlo}[tlo];[b]{pierwszy_plan}[fg];[tlo][fg]overlay=(W-w)/2:(H-h)/2{ogon}"

    if jest_zdjeciem:
        with tempfile.TemporaryDirectory() as katalog_tymczasowy:
            przygotowany = przygotuj_zdjecie(sciezka, Path(katalog_tymczasowy), 0, szerokosc, wysokosc)
            uruchom_ffmpeg([
                "-loop", "1", "-i", str(przygotowany),
                "-filter_complex", filtr,
                "-map", "[out]",
                "-frames:v", str(liczba_klatek),
                "-an",
                *PARAMETRY_KODOWANIA_SEGMENTU,
                str(wyjscie),
            ])
    else:
        uruchom_ffmpeg([
            "-i", str(sciezka),
            "-filter_complex", filtr,
            "-map", "[out]",
            "-frames:v", str(liczba_klatek),
            "-an",
            *PARAMETRY_KODOWANIA_SEGMENTU,
            str(wyjscie),
        ])


def ma_alfa_z_pil(sciezka: Path) -> bool:
    with Image.open(sciezka) as obraz:
        if obraz.mode in ("RGBA", "LA"):
            return True
        return "transparency" in obraz.info


def strumien_wideo_nakladki(sciezka: Path) -> dict | None:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", "-show_streams", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    if wynik.returncode != 0:
        return None
    dane = json.loads(wynik.stdout.decode("utf-8", errors="replace"))
    for strumien in dane.get("streams", []):
        if strumien.get("codec_type") == "video":
            return strumien
    return None


def wymaga_dekodera_vp9_alfa(strumien: dict) -> bool:
    return strumien.get("codec_name") == "vp9" and str(strumien.get("tags", {}).get("alpha_mode")) == "1"


def piksele_pierwszej_klatki(sciezka: Path) -> numpy.ndarray | None:
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        klatka = Path(katalog_tymczasowy) / "klatka.png"
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(sciezka), "-frames:v", "1", str(klatka)],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0 or not klatka.exists():
            return None
        with Image.open(klatka) as obraz:
            tablica = numpy.array(obraz.convert("RGB")).reshape(-1, 3)
    return tablica if tablica.size > 0 else None


def kolor_brzegu(sciezka: Path) -> tuple[int, int, int]:
    strumien = strumien_wideo_nakladki(sciezka)
    if strumien is None:
        return (0, 0, 0)
    szerokosc = int(strumien["width"])
    wysokosc = int(strumien["height"])
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        surowy = Path(katalog_tymczasowy) / "klatka.raw"
        wynik = subprocess.run(
            [
                "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(sciezka),
                "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", str(surowy),
            ],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0 or not surowy.exists():
            return (0, 0, 0)
        tablica = numpy.fromfile(surowy, dtype=numpy.uint8)
    if tablica.size < szerokosc * wysokosc * 3:
        return (0, 0, 0)
    klatka = tablica[: szerokosc * wysokosc * 3].reshape(wysokosc, szerokosc, 3)
    pas = max(1, round(wysokosc * 0.05))
    brzeg = numpy.concatenate([klatka[:pas], klatka[-pas:]]).reshape(-1, 3)
    srednia = brzeg.astype(numpy.float64).mean(axis=0)
    return tuple(int(round(wartosc)) for wartosc in srednia)


def pierwsza_klatka_zielona(sciezka: Path) -> bool:
    tablica = piksele_pierwszej_klatki(sciezka)
    if tablica is None:
        return False
    zielone = numpy.count_nonzero((tablica[:, 1] > 150) & (tablica[:, 0] < 100) & (tablica[:, 2] < 100))
    return zielone / len(tablica) >= PROG_ZIELENI


def pierwsza_klatka_prawie_czarna(sciezka: Path) -> bool:
    tablica = piksele_pierwszej_klatki(sciezka)
    if tablica is None:
        return False
    prawie_czarne = numpy.count_nonzero(tablica.max(axis=1) < PROG_CZERNI)
    return prawie_czarne / len(tablica) >= UDZIAL_CZERNI_EKRANU


def tryb_nakladki(sciezka) -> str:
    sciezka = Path(sciezka)
    if sciezka.suffix.lower() in (".png", ".gif") and ma_alfa_z_pil(sciezka):
        return "alfa"
    strumien = strumien_wideo_nakladki(sciezka)
    if strumien is not None:
        if strumien.get("pix_fmt") in PIX_FMT_Z_ALFA:
            return "alfa"
        if wymaga_dekodera_vp9_alfa(strumien):
            return "alfa"
    if pierwsza_klatka_zielona(sciezka):
        return "zielen"
    if pierwsza_klatka_prawie_czarna(sciezka):
        return "ekran"
    return "krycie"


def wymiary_i_pozycja_znaku(sciezka: Path, szerokosc: int, wysokosc: int) -> tuple[int, int, int, int]:
    with Image.open(sciezka) as obraz:
        obraz = obraz.convert("RGBA")
        bbox = obraz.getchannel("A").getbbox() or (0, 0, obraz.width, obraz.height)
        szerokosc_bbox = bbox[2] - bbox[0]
        skala = (szerokosc * UDZIAL_SZEROKOSCI_ZNAKU) / szerokosc_bbox
        docelowa_szerokosc = max(1, round(obraz.width * skala))
        docelowa_wysokosc = max(1, round(obraz.height * skala))
        srodek_x = (bbox[0] + bbox[2]) / 2 * skala
        srodek_y = (bbox[1] + bbox[3]) / 2 * skala
    x = round(szerokosc / 2 - srodek_x)
    y = round(wysokosc * POZYCJA_ZNAKU_PION - srodek_y)
    return docelowa_szerokosc, docelowa_wysokosc, x, y


def przygotuj_materialy(materialy: list[dict], katalog_pracy: Path, szerokosc: int, wysokosc: int) -> tuple[list[dict], list[dict]]:
    dobre = []
    pominiete = []
    for indeks, material in enumerate(materialy):
        try:
            if material["typ"] == "zdjecie":
                plik_roboczy = przygotuj_zdjecie(material["plik"], katalog_pracy, indeks, szerokosc, wysokosc)
                nowy = dict(material)
                nowy["plik_roboczy"] = plik_roboczy
                dobre.append(nowy)
            else:
                if not ma_strumien_wideo(material["plik"]):
                    raise RuntimeError("brak strumienia wideo")
                dobre.append(dict(material))
        except Exception as blad:
            pominiete.append({"plik": Path(material["plik"]).name, "powod": str(blad)})
    return dobre, pominiete


def znajdz_start_uderzenia(c0: float, uderzenia: list[float]) -> int:
    s = 0
    if analyze.czas_z_pozycji(s + c0, uderzenia) >= 0:
        while analyze.czas_z_pozycji((s - 1) + c0, uderzenia) >= 0:
            s -= 1
        return s
    while analyze.czas_z_pozycji(s + c0, uderzenia) < 0:
        s += 1
    return s


def uloz_wariant(materialy: list, wariant: int) -> list:
    if wariant == 0 or len(materialy) <= 1:
        return list(materialy)
    hak, *reszta = materialy
    random.Random(wariant).shuffle(reszta)
    return [hak] + reszta


def rozdziel_wycinki(materialy: list[dict]) -> tuple[list[dict], list[dict]]:
    zwykle = []
    wycinki = []
    for material in materialy:
        if material["typ"] == "zdjecie" and ma_alfa_z_pil(Path(material["plik"])):
            wycinki.append(material)
        else:
            zwykle.append(material)
    if not zwykle:
        return list(materialy), []
    return zwykle, wycinki


def wstawki(materialy: list[dict], dlugosc_wstawki_s: float, minimum_s: float = 0.3) -> list[dict]:
    kolejki = []
    for material in materialy:
        if material["typ"] != "klip":
            kolejki.append([dict(material)])
            continue
        czas_s = material["czas_s"]
        kawalki = []
        indeks = 0
        while True:
            start = round(indeks * dlugosc_wstawki_s, 6)
            if start >= czas_s:
                break
            koniec = min(start + dlugosc_wstawki_s, czas_s)
            dlugosc = round(koniec - start, 6)
            if kawalki and dlugosc < minimum_s:
                kawalki[-1]["czas_s"] = round(kawalki[-1]["czas_s"] + dlugosc, 6)
            else:
                kawalki.append({
                    "plik": material["plik"],
                    "typ": "klip",
                    "message_id": material["message_id"],
                    "czas_s": dlugosc,
                    "od_s": start,
                })
            indeks += 1
        kolejki.append(kawalki)
    wynik = []
    maks_dlugosc = max((len(kolejka) for kolejka in kolejki), default=0)
    for i in range(maks_dlugosc):
        for kolejka in kolejki:
            if i < len(kolejka):
                wynik.append(kolejka[i])
    return wynik


def przeplot(kawalki: list[dict], zdjec_miedzy_klipami: int = ZDJEC_MIEDZY_KLIPAMI) -> list[dict]:
    if not kawalki:
        return list(kawalki)
    hak, *reszta = kawalki
    zdjecia = [m for m in reszta if m["typ"] != "klip"]
    klipy = [m for m in reszta if m["typ"] == "klip"]
    if not zdjecia or not klipy:
        return list(kawalki)

    wynik = [hak]
    uzyte = set()
    indeks = 0
    for klip in klipy:
        for _ in range(zdjec_miedzy_klipami):
            pozycja = indeks % len(zdjecia)
            wynik.append(zdjecia[pozycja])
            uzyte.add(pozycja)
            indeks += 1
        wynik.append(klip)
    for pozycja, zdjecie in enumerate(zdjecia):
        if pozycja not in uzyte:
            wynik.append(zdjecie)
    return wynik


def plan_ujec(
    wzor: dict,
    uderzenia_utworu: list[float],
    materialy: list[dict],
    fps: int,
    start_uderzenie: int | None = None,
    przesuniecie_s: float | None = None,
) -> dict:
    if przesuniecie_s is not None:
        czasy = list(wzor["ciecia_s"]) + [wzor["zrodlo"]["czas_s"]]
        start_audio_s = przesuniecie_s
    else:
        ciecia_uderzenia = wzor.get("ciecia_uderzenia") or []
        if ciecia_uderzenia and len(uderzenia_utworu) >= 2:
            c0 = ciecia_uderzenia[0]
            s = start_uderzenie if start_uderzenie is not None else znajdz_start_uderzenia(c0, uderzenia_utworu)
            pozycje = list(ciecia_uderzenia) + [wzor["koniec_uderzenia"]]
            czasy = [analyze.czas_z_pozycji(s + p, uderzenia_utworu) for p in pozycje]
        else:
            czasy = list(wzor["ciecia_s"]) + [wzor["zrodlo"]["czas_s"]]
        start_audio_s = czasy[0]

    liczba_klatek = round((czasy[-1] - czasy[0]) * fps)
    if liczba_klatek <= 0:
        raise ValueError("Utwór za krótki na całe okno wzoru")

    granice = [round((t - czasy[0]) * fps) for t in czasy]
    ujecia = []
    for k in range(len(granice) - 1):
        klatka_od = granice[k]
        dlugosc = granice[k + 1] - klatka_od
        if dlugosc <= 0:
            continue
        kawalek = materialy[k % len(materialy)]
        ujecia.append({
            "material": str(kawalek["plik"]),
            "typ": kawalek["typ"],
            "klatka_od": klatka_od,
            "liczba_klatek": dlugosc,
            "start_w_klipie_s": kawalek["od_s"] if kawalek["typ"] == "klip" else 0.0,
            "numer_wzoru": k,
        })

    return {
        "fps": fps,
        "start_audio_s": round(start_audio_s, 6),
        "liczba_klatek": liczba_klatek,
        "ujecia": ujecia,
    }


def rozloz_tempo(plan: dict, wzor: dict, uderzenia: list[int], kawalki: list[dict], fps: int) -> dict:
    liczba_klatek = plan["liczba_klatek"]
    plan_ujecia = plan["ujecia"]
    sekcje = wzor.get("sekcje")

    twarde = {0, liczba_klatek}
    if sekcje and sekcje.get("drop_ujecie") is not None:
        twarde.add(koniec_haka(plan, sekcje))
    if plan_ujecia:
        twarde.add(plan_ujecia[-1]["klatka_od"])
    twarde = sorted(twarde)

    def numer_wzoru_dla(klatka: int) -> int:
        wynik = 0
        for ujecie_wzoru in plan_ujecia:
            if ujecie_wzoru["klatka_od"] <= klatka:
                wynik = ujecie_wzoru["numer_wzoru"]
            else:
                break
        return wynik

    def pierwsze_w_oknie(lista: list[int], dolna: int, gorna: int) -> int | None:
        for wartosc in lista:
            if dolna <= wartosc <= gorna:
                return wartosc
        return None

    zawijaj_bez_haka = len(kawalki) > 1 and kawalki[0]["typ"] == "klip" and kawalki[-1]["typ"] == "klip"

    def kawalek(numer: int) -> dict:
        if numer < len(kawalki) or not zawijaj_bez_haka:
            return kawalki[numer % len(kawalki)]
        return kawalki[1 + (numer - 1) % (len(kawalki) - 1)]

    ciecia_wzoru = [u["klatka_od"] for u in plan_ujecia]
    min_klatek_zdjecia = round(TEMPO_ZDJECIA_MIN_S * fps)
    min_klatek_klipu = round(TEMPO_KLIPU_MIN_S * fps)
    maks_klatek_klipu = round(TEMPO_KLIPU_MAX_S * fps)

    ujecia = []
    k = 0

    for indeks_segmentu in range(len(twarde) - 1):
        poczatek_segmentu = twarde[indeks_segmentu]
        koniec_segmentu = twarde[indeks_segmentu + 1]
        if koniec_segmentu <= poczatek_segmentu:
            continue

        if plan_ujecia and poczatek_segmentu == plan_ujecia[-1]["klatka_od"]:
            material = kawalek(k)
            ujecia.append({
                "material": str(material["plik"]),
                "typ": material["typ"],
                "klatka_od": poczatek_segmentu,
                "liczba_klatek": koniec_segmentu - poczatek_segmentu,
                "start_w_klipie_s": material["od_s"] if material["typ"] == "klip" else 0.0,
                "numer_wzoru": numer_wzoru_dla(poczatek_segmentu),
            })
            k += 1
            continue

        pozycja = poczatek_segmentu
        while pozycja < koniec_segmentu:
            material = kawalek(k)
            if material["typ"] == "zdjecie":
                cel = pierwsze_w_oknie(uderzenia, pozycja + min_klatek_zdjecia, koniec_segmentu)
                koniec_ujecia = cel if cel is not None else koniec_segmentu
            else:
                dolna = pozycja + min_klatek_klipu
                gorna = pozycja + maks_klatek_klipu
                cel = pierwsze_w_oknie(ciecia_wzoru, dolna, gorna)
                if cel is None:
                    cel = pierwsze_w_oknie(uderzenia, dolna, gorna)
                if cel is None:
                    cel = dolna
                koniec_ujecia = min(cel, koniec_segmentu)

            if 0 < koniec_segmentu - koniec_ujecia < min_klatek_zdjecia:
                koniec_ujecia = koniec_segmentu

            ujecia.append({
                "material": str(material["plik"]),
                "typ": material["typ"],
                "klatka_od": pozycja,
                "liczba_klatek": koniec_ujecia - pozycja,
                "start_w_klipie_s": material["od_s"] if material["typ"] == "klip" else 0.0,
                "numer_wzoru": numer_wzoru_dla(pozycja),
            })
            pozycja = koniec_ujecia
            k += 1

    return {
        "fps": plan["fps"],
        "start_audio_s": plan["start_audio_s"],
        "liczba_klatek": liczba_klatek,
        "ujecia": ujecia,
    }


def fragment_klipu(od_s: float, czas_klipu_s: float, liczba_klatek: int, fps: int) -> tuple[float, str | None]:
    dlugosc_s = liczba_klatek / fps
    if dlugosc_s > czas_klipu_s:
        return 0.0, "klip krótszy od ujęcia, koniec klipu zatrzymany"
    najpozniej_s = czas_klipu_s - dlugosc_s
    if od_s < 0 or od_s > najpozniej_s:
        return round(min(max(od_s, 0.0), najpozniej_s), 6), "od_s poza zakresem klipu, przycięte"
    return od_s, None


def plan_ze_scenariusza(
    scenariusz, plan: dict, kawalki_wedlug_numeru: dict, uderzenia: list[int], fps: int, wzor: dict,
) -> tuple[dict, list[str]]:
    liczba_klatek = plan["liczba_klatek"]
    plan_ujecia = plan["ujecia"]
    sekcje = wzor.get("sekcje")

    twarde = {0, liczba_klatek}
    if sekcje and sekcje.get("drop_ujecie") is not None:
        twarde.add(koniec_haka(plan, sekcje))
    if plan_ujecia:
        twarde.add(plan_ujecia[-1]["klatka_od"])
    twarde = sorted(twarde)

    def numer_wzoru_dla(klatka: int) -> int:
        wynik = 0
        for ujecie_wzoru in plan_ujecia:
            if ujecie_wzoru["klatka_od"] <= klatka:
                wynik = ujecie_wzoru["numer_wzoru"]
            else:
                break
        return wynik

    def nastepna_twarda(klatka: int) -> int:
        for wartosc in twarde:
            if wartosc > klatka:
                return wartosc
        return liczba_klatek

    def dlugosc_z_uderzen(klatka: int, liczba_uderzen: int) -> int:
        if uderzenia:
            start_pozycja = None
            for pozycja, k in enumerate(uderzenia):
                if k >= klatka:
                    start_pozycja = pozycja
                    break
            if start_pozycja is not None and start_pozycja + liczba_uderzen < len(uderzenia):
                return max(1, uderzenia[start_pozycja + liczba_uderzen] - klatka)
        srednia_klatek_uderzenia = liczba_klatek / len(uderzenia) if uderzenia else fps
        return max(1, round(liczba_uderzen * srednia_klatek_uderzenia))

    ostrzezenia = []
    ujecia = []
    klatka = 0

    for pozycja, ujecie_scenariusza in enumerate(scenariusz.ujecia):
        if klatka >= liczba_klatek:
            break
        kawalek = kawalki_wedlug_numeru.get(ujecie_scenariusza.material)
        if kawalek is None:
            ostrzezenia.append(f"ujęcie {pozycja}: nieznany numer materiału {ujecie_scenariusza.material}, pominięte")
            continue
        typ = kawalek["typ"]
        if typ == "wycinek":
            ostrzezenia.append(f"ujęcie {pozycja}: wycinek {ujecie_scenariusza.material} jako ujęcie, pominięte")
            continue

        granica = nastepna_twarda(klatka)
        dlugosc = dlugosc_z_uderzen(klatka, ujecie_scenariusza.uderzenia)
        koniec = min(klatka + dlugosc, granica, liczba_klatek)
        dlugosc = koniec - klatka
        if dlugosc <= 0:
            continue

        if typ == "klip":
            od_s, ostrzezenie = fragment_klipu(ujecie_scenariusza.od_s, float(kawalek["czas_s"]), dlugosc, fps)
            if ostrzezenie:
                ostrzezenia.append(f"ujęcie {pozycja}: {ostrzezenie}")
        else:
            if ujecie_scenariusza.od_s != 0:
                ostrzezenia.append(f"ujęcie {pozycja}: zdjęcie nie ma fragmentu, od_s wymuszone na 0")
            od_s = 0.0

        ujecia.append({
            "material": str(kawalek["plik"]),
            "typ": typ,
            "klatka_od": klatka,
            "liczba_klatek": dlugosc,
            "start_w_klipie_s": od_s if typ == "klip" else 0.0,
            "numer_wzoru": numer_wzoru_dla(klatka),
            "efekt_scenariusza": {
                "uderzenie": ujecie_scenariusza.uderzenie,
                "blysk_s": ujecie_scenariusza.blysk_s,
                "wstrzas": ujecie_scenariusza.wstrzas,
                "przejscie": ujecie_scenariusza.przejscie,
            },
            "kolaz_scenariusza": list(ujecie_scenariusza.kolaz),
        })
        klatka = koniec

    if klatka < liczba_klatek:
        for ujecie_wzoru in plan_ujecia:
            koniec_ujecia = ujecie_wzoru["klatka_od"] + ujecie_wzoru["liczba_klatek"]
            if koniec_ujecia <= klatka:
                continue
            nowe = dict(ujecie_wzoru)
            if nowe["klatka_od"] < klatka:
                przesuniecie = klatka - nowe["klatka_od"]
                if nowe["typ"] == "klip":
                    nowe["start_w_klipie_s"] = nowe.get("start_w_klipie_s", 0.0) + przesuniecie / fps
                nowe["klatka_od"] = klatka
                nowe["liczba_klatek"] -= przesuniecie
            if nowe["liczba_klatek"] > 0:
                nowe.setdefault("efekt_scenariusza", None)
                nowe.setdefault("kolaz_scenariusza", None)
                ujecia.append(nowe)
            klatka = koniec_ujecia

    plan_wynikowy = {
        "fps": fps,
        "start_audio_s": plan["start_audio_s"],
        "liczba_klatek": liczba_klatek,
        "ujecia": ujecia,
    }
    return plan_wynikowy, ostrzezenia


def zastosuj_poprawki(plan: dict, poprawki: list, kawalki_wedlug_numeru: dict, fps: int) -> tuple[dict, list[str]]:
    ujecia = [dict(u) for u in plan["ujecia"]]
    ostrzezenia = []
    for poprawka in poprawki:
        indeks = poprawka.ujecie
        if not (0 <= indeks < len(ujecia)):
            ostrzezenia.append(f"poprawka: nieznane ujęcie {indeks}, pominięta")
            continue
        zmiana = poprawka.zmiana
        kawalek = kawalki_wedlug_numeru.get(zmiana.material)
        if kawalek is None or kawalek["typ"] == "wycinek":
            ostrzezenia.append(f"poprawka ujęcia {indeks}: materiał {zmiana.material} nie jest zdjęciem ani klipem, pominięta")
            continue
        oryginal = ujecia[indeks]
        typ = kawalek["typ"]
        start_w_klipie_s = 0.0
        if typ == "klip":
            start_w_klipie_s, ostrzezenie = fragment_klipu(zmiana.od_s, float(kawalek["czas_s"]), oryginal["liczba_klatek"], fps)
            if ostrzezenie:
                ostrzezenia.append(f"poprawka ujęcia {indeks}: {ostrzezenie}")
        ujecia[indeks] = {
            "material": str(kawalek["plik"]),
            "typ": typ,
            "klatka_od": oryginal["klatka_od"],
            "liczba_klatek": oryginal["liczba_klatek"],
            "start_w_klipie_s": start_w_klipie_s,
            "numer_wzoru": oryginal["numer_wzoru"],
            "efekt_scenariusza": {
                "uderzenie": zmiana.uderzenie, "blysk_s": zmiana.blysk_s,
                "wstrzas": zmiana.wstrzas, "przejscie": zmiana.przejscie,
            },
            "kolaz_scenariusza": list(zmiana.kolaz),
        }
    plan_poprawiony = {"fps": plan["fps"], "start_audio_s": plan["start_audio_s"], "liczba_klatek": plan["liczba_klatek"], "ujecia": ujecia}
    return plan_poprawiony, ostrzezenia


def plik_zrodlowy_wzoru(wzor_json: Path) -> Path | None:
    kandydaci = sorted(Path(wzor_json).parent.glob("zrodlo.*"))
    return kandydaci[0] if kandydaci else None


def zapisz_scenariusz(katalog_projektu: Path, wzor_id: str, wariant: int, scenariusz, ostrzezenia: list[str]) -> None:
    sciezka = Path(katalog_projektu) / f"scenariusz_{wzor_id}_{wariant}.json"
    dane = {"scenariusz": scenariusz.model_dump(), "ostrzezenia": ostrzezenia}
    sciezka.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")


def ocen_montaz(
    klient, model, wzor_json: Path, plan: dict, wyjscie: Path, katalog_pracy: Path,
    materialy: list[dict] | None = None, wycinki: list[dict] | None = None, plansza_uzyta: bool = False,
) -> tuple:
    zrodlo_wzoru = plik_zrodlowy_wzoru(wzor_json)
    if zrodlo_wzoru is None:
        return None, rezyser.zuzycie(powod="brak źródła wzoru do arkusza krytyka")
    try:
        arkusz = rezyser.arkusz_krytyka(wyjscie, zrodlo_wzoru, Path(katalog_pracy) / "arkusz_krytyka.jpg")
        opis = rezyser.opis_montazu(plan, plan["fps"], materialy, wycinki, plansza_uzyta)
        tresc = {"obrazy": [arkusz], "tekst": rezyser.POLECENIE_KRYTYKA + "\n\n" + opis}
        dane, zuzycie = rezyser.wywolaj_model(klient, model, tresc, rezyser.schemat_oceny())
    except Exception as wyjatek:
        return None, rezyser.zuzycie(powod=f"błąd krytyka: {type(wyjatek).__name__}")
    if dane is None:
        return None, zuzycie
    ocena = rezyser.zbuduj_ocene(dane)
    if ocena is None:
        return None, dict(zuzycie, powod="JSON niezgodny ze schematem")
    return ocena, zuzycie


def dolicz_zuzycie(ai_info: dict, zuzycie: dict) -> None:
    ai_info["tokeny_wejscia"] += zuzycie.get("wejscie", 0)
    ai_info["tokeny_wyjscia"] += zuzycie.get("wyjscie", 0)
    if zuzycie.get("koszt_usd") is not None:
        ai_info["koszt_usd"] = (ai_info["koszt_usd"] or 0.0) + zuzycie["koszt_usd"]


def rezyseruj(
    wzor: dict,
    wzor_json: Path,
    plan_auto: dict,
    plan_bazowy: dict,
    zwykle: list[dict],
    wycinki: list[dict],
    uderzenia_wyn: list[int],
    fps: int,
    katalog_projektu: Path,
    katalog_pracy: Path,
    wariant: int,
    model_ai: str,
    model_ai_zapas: str | None,
    bez_rezysera: bool,
    bez_krytyka: bool,
    prog_oceny_ai: int,
    klient_ai,
    montuj,
    wyjscie: Path,
    okna_tekstow: dict | None = None,
) -> tuple[dict, dict, dict]:
    model = [model_ai, model_ai_zapas] if model_ai_zapas else model_ai
    klient = klient_ai if klient_ai is not None else httpx.Client()

    zwykle_wedlug_numeru, wycinki_wedlug_numeru = rezyser.numeracja(zwykle, wycinki)
    materialy_wedlug_numeru = dict(zwykle_wedlug_numeru)
    materialy_wedlug_numeru.update({numer: dict(wycinek, typ="wycinek") for numer, wycinek in wycinki_wedlug_numeru.items()})

    scenariusz = None
    plan_1 = plan_auto
    ostrzezenia = []
    zuzycie_rezysera = rezyser.zuzycie(powod="reżyser wyłączony")
    if not bez_rezysera:
        try:
            sciezki_arkuszy = rezyser.arkusze_materialow(zwykle, wycinki, Path(katalog_pracy) / "arkusze_rezysera")
            opis = rezyser.opis_wzoru(wzor, plan_bazowy, uderzenia_wyn, zwykle, okna_tekstow, wycinki)
            tresc = {"obrazy": sciezki_arkuszy, "tekst": rezyser.POLECENIE_REZYSERA + "\n\n" + opis}
            dane, zuzycie_rezysera = rezyser.wywolaj_model(klient, model, tresc, rezyser.schemat_scenariusza())
            if dane is not None:
                scenariusz = rezyser.zbuduj_scenariusz(dane)
                if scenariusz is None:
                    zuzycie_rezysera = dict(zuzycie_rezysera, powod="JSON niezgodny ze schematem")
            if scenariusz is not None:
                plan_1, ostrzezenia = plan_ze_scenariusza(
                    scenariusz, plan_auto, materialy_wedlug_numeru, uderzenia_wyn, fps, wzor,
                )
        except Exception as wyjatek:
            scenariusz = None
            plan_1 = plan_auto
            ostrzezenia = []
            zuzycie_rezysera = dict(zuzycie_rezysera, powod=f"błąd reżysera: {type(wyjatek).__name__}")

    rezyser_aktywny = scenariusz is not None
    if rezyser_aktywny:
        zapisz_scenariusz(katalog_projektu, Path(wzor_json).parent.name, wariant, scenariusz, ostrzezenia)
        try:
            wynik_1 = montuj(plan_1, wycinki_wedlug_numeru, Path(katalog_pracy) / "montaz_ai_1", wyjscie)
        except Exception as wyjatek:
            rezyser_aktywny = False
            zuzycie_rezysera = dict(zuzycie_rezysera, powod=f"błąd montażu scenariusza: {type(wyjatek).__name__}")
            plan_1 = plan_auto
            wynik_1 = montuj(plan_auto, None, Path(katalog_pracy) / "montaz_auto", wyjscie)
    else:
        wynik_1 = montuj(plan_1, None, Path(katalog_pracy) / "montaz_ai_1", wyjscie)

    ai_info = {
        "model": model_ai,
        "rezyser": rezyser_aktywny,
        "ocena": None,
        "ocena_przed": None,
        "poprawka": False,
        "ostrzezenia": list(ostrzezenia),
        "tokeny_wejscia": zuzycie_rezysera.get("wejscie", 0),
        "tokeny_wyjscia": zuzycie_rezysera.get("wyjscie", 0),
        "koszt_usd": zuzycie_rezysera.get("koszt_usd"),
        "powod_pominiecia": None if rezyser_aktywny else zuzycie_rezysera.get("powod"),
    }

    if bez_krytyka:
        return plan_1, wynik_1, ai_info

    plansza_uzyta = bool(wynik_1.get("plansza_uzyta"))
    ocena_1, zuzycie_krytyka_1 = ocen_montaz(
        klient, model, wzor_json, plan_1, wyjscie, katalog_pracy, zwykle, wycinki, plansza_uzyta,
    )
    dolicz_zuzycie(ai_info, zuzycie_krytyka_1)

    if ocena_1 is None:
        ai_info["ostrzezenia"].append(f"krytyk: {zuzycie_krytyka_1.get('powod')}")
        if not rezyser_aktywny and ai_info["powod_pominiecia"] is None:
            ai_info["powod_pominiecia"] = zuzycie_krytyka_1.get("powod")
        return plan_1, wynik_1, ai_info

    ai_info["ocena"] = ocena_1.ocena
    if ocena_1.ocena >= prog_oceny_ai or not ocena_1.poprawki:
        return plan_1, wynik_1, ai_info

    plan_2, ostrzezenia_poprawek = zastosuj_poprawki(plan_1, ocena_1.poprawki, materialy_wedlug_numeru, fps)
    ai_info["ostrzezenia"] += ostrzezenia_poprawek
    if plan_2["ujecia"] == plan_1["ujecia"]:
        return plan_1, wynik_1, ai_info

    wyjscie_2 = Path(wyjscie).with_name(Path(wyjscie).stem + "_ai_poprawka" + Path(wyjscie).suffix)
    try:
        wynik_2 = montuj(plan_2, wycinki_wedlug_numeru, Path(katalog_pracy) / "montaz_ai_2", wyjscie_2)
    except Exception as wyjatek:
        ai_info["ostrzezenia"].append(f"montaż po poprawce nieudany: {type(wyjatek).__name__}")
        wyjscie_2.unlink(missing_ok=True)
        return plan_1, wynik_1, ai_info

    ocena_2, zuzycie_krytyka_2 = ocen_montaz(
        klient, model, wzor_json, plan_2, wyjscie_2, katalog_pracy, zwykle, wycinki, bool(wynik_2.get("plansza_uzyta")),
    )
    dolicz_zuzycie(ai_info, zuzycie_krytyka_2)
    if ocena_2 is None:
        ai_info["ostrzezenia"].append(f"krytyk po poprawce: {zuzycie_krytyka_2.get('powod')}")

    ai_info["ocena_przed"] = ocena_1.ocena
    if ocena_2 is not None and ocena_2.ocena >= ocena_1.ocena:
        shutil.copyfile(wyjscie_2, wyjscie)
        wyjscie_2.unlink(missing_ok=True)
        ai_info["ocena"] = ocena_2.ocena
        ai_info["poprawka"] = True
        return plan_2, wynik_2, ai_info

    wyjscie_2.unlink(missing_ok=True)
    return plan_1, wynik_1, ai_info


def czas_trwania(sciezka) -> float | None:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    if wynik.returncode != 0:
        return None
    try:
        czas = float(wynik.stdout.decode("utf-8", errors="replace").strip())
    except ValueError:
        return None
    return czas if czas > 0 else None


def sklej_segmenty(sciezki_segmentow: list[Path], wyjscie: Path) -> None:
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        lista = Path(katalog_tymczasowy) / "lista.txt"
        with open(lista, "w", encoding="utf-8") as plik:
            for sciezka in sciezki_segmentow:
                plik.write(f"file '{Path(sciezka).resolve().as_posix()}'\n")
        uruchom_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(wyjscie)])


def materializuj_nakladke(
    nakladka: Path, tryb: str, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int, katalog: Path,
) -> Path:
    nakladka = Path(nakladka)
    wejscie_opcje = []
    strumien = strumien_wideo_nakladki(nakladka)
    if strumien is not None and wymaga_dekodera_vp9_alfa(strumien):
        wejscie_opcje += ["-c:v", "libvpx-vp9"]
    wejscie_opcje += ["-stream_loop", "-1", "-i", str(nakladka)]

    if tryb in ("alfa", "zielen"):
        if tryb == "alfa":
            filtr = (
                f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=decrease,"
                f"format=rgba,pad={szerokosc}:{wysokosc}:(ow-iw)/2:(oh-ih)/2:color=0x00000000,fps={fps}"
            )
        else:
            filtr = (
                f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,"
                f"crop={szerokosc}:{wysokosc},fps={fps},format=rgba,colorkey=0x00FF00:0.3:0.1"
            )
        wyjscie = katalog / "nakladka.mov"
        uruchom_ffmpeg([
            *wejscie_opcje, "-map", "0:v:0", "-frames:v", str(liczba_klatek), "-vf", filtr,
            "-c:v", "png", "-pix_fmt", "rgba", str(wyjscie),
        ])
        return wyjscie

    if tryb == "krycie":
        krotszy_bok = round(szerokosc * SKALA_NAKLADKI_KRYCIE)
        r, g, b = kolor_brzegu(nakladka)
        kolor_hex = f"0x{r:02x}{g:02x}{b:02x}"
        filtr = (
            f"scale='if(gt(iw,ih),-2,{szerokosc})':'if(gt(iw,ih),{krotszy_bok},-2)',"
            f"crop='min(iw,{szerokosc})':'min(ih,{wysokosc})',"
            f"pad={szerokosc}:{wysokosc}:(ow-iw)/2:(oh-ih)/2:color={kolor_hex},fps={fps}"
        )
    else:
        filtr = f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,crop={szerokosc}:{wysokosc},fps={fps}"

    wyjscie = katalog / "nakladka.mp4"
    uruchom_ffmpeg([
        *wejscie_opcje, "-map", "0:v:0", "-frames:v", str(liczba_klatek), "-vf", filtr,
        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(wyjscie),
    ])
    return wyjscie


def przebieg_koncowy(
    polaczone_wideo: Path,
    utwor: Path,
    start_audio_s: float,
    liczba_klatek: int,
    fps: float,
    wyjscie: Path,
    limit_mb: float,
    szerokosc: int | None = None,
    wysokosc: int | None = None,
    nakladka: Path | None = None,
    tryb_nakladki_wartosc: str | None = None,
    nakladka_od_s: float | None = None,
    nakladka_do_s: float | None = None,
    znak: Path | None = None,
    znak_do_s: float | None = None,
    teksty: list[dict] | None = None,
    slowa: dict | None = None,
    pionowo: dict | None = None,
) -> None:
    polaczone_wideo = Path(polaczone_wideo)
    czas_trwania_s = liczba_klatek / fps
    wyciszenie_s = min(0.5, czas_trwania_s)
    poczatek_wyciszenia = max(0.0, czas_trwania_s - wyciszenie_s)

    bitrate_audio_bps = 192_000
    limit_bitow = limit_mb * 8 * 1024 * 1024 * 0.95
    maxrate_bps = max(100_000, int(limit_bitow / czas_trwania_s) - bitrate_audio_bps)
    bufsize_bps = maxrate_bps

    wejscia = ["-i", str(polaczone_wideo), "-ss", f"{start_audio_s:.6f}", "-t", f"{czas_trwania_s:.6f}", "-i", str(utwor)]

    if nakladka is None:
        filtr = (
            "[0:v]setsar=1[v];"
            f"[1:a]afade=t=out:st={poczatek_wyciszenia:.6f}:d={wyciszenie_s:.6f}[a]"
        )
        mapa_wideo = "[v]"
    else:
        okno_s = round(nakladka_do_s - nakladka_od_s, 6)
        nakladka = Path(nakladka)
        liczba_klatek_nakladki = round(okno_s * fps)
        sciezka_nakladki = materializuj_nakladke(
            nakladka, tryb_nakladki_wartosc, liczba_klatek_nakladki, fps, szerokosc, wysokosc, polaczone_wideo.parent,
        )
        wejscia += ["-i", str(sciezka_nakladki)]

        warunek = f"between(t,{nakladka_od_s:.6f},{nakladka_do_s:.6f})"
        if tryb_nakladki_wartosc == "krycie":
            przygotowanie_nakladki = (
                f"[2:v]format=rgba,colorchannelmixer=aa={KRYCIE_NAKLADKI},"
                f"setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            )
            kompozycja = f"[0:v][nak]overlay=eval=frame:enable='{warunek}',setsar=1[v]"
        elif tryb_nakladki_wartosc == "ekran":
            przygotowanie_nakladki = f"[2:v]format=gbrp,setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            kompozycja = (
                f"[0:v]format=gbrp[glowne];[glowne][nak]blend=all_mode=screen:enable='{warunek}',"
                f"scale=out_range=tv,format=yuv420p,setsar=1[v]"
            )
        else:
            przygotowanie_nakladki = f"[2:v]setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            kompozycja = f"[0:v][nak]overlay=eval=frame:enable='{warunek}',setsar=1[v]"

        filtr = (
            f"{przygotowanie_nakladki};{kompozycja};"
            f"[1:a]afade=t=out:st={poczatek_wyciszenia:.6f}:d={wyciszenie_s:.6f}[a]"
        )
        mapa_wideo = "[v]"

    if teksty:
        fade_s = 4 / fps
        for indeks_tekstu, wpis in enumerate(teksty):
            czas_trwania_napisu_s = round(wpis["do_s"] - wpis["od_s"], 6)
            indeks_wejscia = wejscia.count("-i")
            wejscia += ["-c:v", "libvpx-vp9", "-i", str(wpis["plik"])]
            koniec_zanikania = max(0.0, czas_trwania_napisu_s - fade_s)
            etykieta = f"tekst{indeks_tekstu}"
            etykieta_wyjscia = f"[vt{indeks_tekstu}]"
            filtr += (
                f";[{indeks_wejscia}:v]fade=t=in:st=0:d={fade_s:.6f}:alpha=1,"
                f"fade=t=out:st={koniec_zanikania:.6f}:d={fade_s:.6f}:alpha=1,"
                f"setpts=PTS+{wpis['od_s']:.6f}/TB[{etykieta}];"
                f"{mapa_wideo}[{etykieta}]overlay=eval=frame:enable="
                f"'between(t,{wpis['od_s']:.6f},{wpis['do_s']:.6f})'{etykieta_wyjscia}"
            )
            mapa_wideo = etykieta_wyjscia

    for warstwa in (slowa, pionowo):
        if warstwa is None:
            continue
        indeks_wejscia = wejscia.count("-i")
        wejscia += ["-i", str(warstwa["plik"])]
        etykieta = f"warstwa{indeks_wejscia}"
        etykieta_wyjscia = f"[w{indeks_wejscia}]"
        filtr += (
            f";[{indeks_wejscia}:v]setpts=PTS+{warstwa['od_s']:.6f}/TB[{etykieta}];"
            f"{mapa_wideo}[{etykieta}]overlay=eval=frame:enable="
            f"'between(t,{warstwa['od_s']:.6f},{warstwa['do_s']:.6f})'{etykieta_wyjscia}"
        )
        mapa_wideo = etykieta_wyjscia

    if znak is not None:
        znak = Path(znak)
        okno_znaku_s = round(znak_do_s, 6)
        liczba_klatek_znaku = round(okno_znaku_s * fps)
        dw, dh, x, y = wymiary_i_pozycja_znaku(znak, szerokosc, wysokosc)
        sciezka_znaku = polaczone_wideo.parent / "znak.mov"
        uruchom_ffmpeg([
            "-loop", "1", "-i", str(znak),
            "-frames:v", str(liczba_klatek_znaku),
            "-vf", f"scale={dw}:{dh},format=rgba,colorchannelmixer=aa={KRYCIE_ZNAKU},fps={fps}",
            "-c:v", "png", "-pix_fmt", "rgba",
            str(sciezka_znaku),
        ])
        indeks_znaku = wejscia.count("-i")
        wejscia += ["-i", str(sciezka_znaku)]
        filtr += (
            f";{mapa_wideo}[{indeks_znaku}:v]overlay={x}:{y}:enable='between(t,0,{okno_znaku_s:.6f})'[vz]"
        )
        mapa_wideo = "[vz]"

    uruchom_ffmpeg([
        *wejscia,
        "-filter_complex", filtr,
        "-map", mapa_wideo, "-map", "[a]",
        "-r", str(fps),
        "-frames:v", str(liczba_klatek),
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-maxrate", str(maxrate_bps), "-bufsize", str(bufsize_bps), "-x264-params", "vbv-init=0",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", str(bitrate_audio_bps),
        "-movflags", "+faststart",
        "-t", f"{czas_trwania_s:.6f}",
        str(wyjscie),
    ])


def zweryfikuj_wynik(wyjscie: Path, szerokosc: int, wysokosc: int, fps: float, liczba_klatek: int, limit_mb: float) -> None:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(wyjscie)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    if wynik.returncode != 0:
        raise RuntimeError("Nie udało się odczytać wyniku ffprobe")
    dane = json.loads(wynik.stdout.decode("utf-8", errors="replace"))
    strumien_v = next((s for s in dane["streams"] if s["codec_type"] == "video"), None)
    if strumien_v is None:
        raise RuntimeError("Wynik nie ma strumienia wideo")
    if int(strumien_v["width"]) != szerokosc or int(strumien_v["height"]) != wysokosc:
        raise RuntimeError("Wynik ma zły rozmiar kadru")
    if strumien_v.get("pix_fmt") != "yuv420p":
        raise RuntimeError("Wynik ma zły pix_fmt")
    if not any(s["codec_type"] == "audio" for s in dane["streams"]):
        raise RuntimeError("Wynik nie ma dźwięku")
    oczekiwany_czas_s = liczba_klatek / fps
    rzeczywisty_czas_s = float(dane["format"]["duration"])
    if abs(rzeczywisty_czas_s - oczekiwany_czas_s) > 1.0 / fps + 0.02:
        raise RuntimeError("Długość wyniku nie zgadza się z planem")
    rozmiar_mb = Path(wyjscie).stat().st_size / (1024 * 1024)
    if rozmiar_mb > limit_mb:
        raise RuntimeError(f"Plik wynikowy {rozmiar_mb:.2f} MB przekracza limit {limit_mb} MB")


def przygotuj_zrodlo_dzwieku(wzor: dict, utwor: Path | None, muzyka: Path | None):
    if utwor is not None:
        utwor = Path(utwor)
        _, uderzenia_utworu = analyze.analizuj_rytm(utwor)
        return utwor, "staly", uderzenia_utworu, None, None, None
    if muzyka is not None:
        muzyka = Path(muzyka)
        indeks, _ = music.indeksuj(muzyka)
        wybor = music.wybierz_utwor(wzor, indeks)
        utwor = muzyka / wybor["plik"]
        tryb = wybor["tryb"]
        if tryb == "dzwiek_wzoru":
            return utwor, tryb, [], None, wybor["przesuniecie_s"], wybor
        if tryb == "tempo":
            return utwor, tryb, wybor["uderzenia_s"], wybor["start_uderzenie"], None, wybor
        return utwor, tryb, [], None, None, wybor
    raise RuntimeError("Brak utworu i katalogu muzyki")


def pozycja_dropu_w_planie(wzor: dict, plan_ujecia: list[dict], fps: float) -> float | None:
    sekcje = wzor.get("sekcje")
    if not sekcje or sekcje.get("drop_ujecie") is None:
        return None
    for ujecie in plan_ujecia:
        if ujecie["numer_wzoru"] >= sekcje["drop_ujecie"]:
            return round(ujecie["klatka_od"] / fps, 3)
    return None


def koniec_haka(plan: dict, sekcje: dict | None) -> int:
    plan_ujecia = plan["ujecia"]
    liczba_klatek = plan["liczba_klatek"]
    fps = plan["fps"]
    klatka = None
    if sekcje and sekcje.get("drop_ujecie") is not None:
        klatka = next((u["klatka_od"] for u in plan_ujecia if u["numer_wzoru"] >= sekcje["drop_ujecie"]), None)
    if klatka is None:
        cel = liczba_klatek * 0.4
        klatka = min((u["klatka_od"] for u in plan_ujecia), key=lambda k: abs(k - cel))
    return max(fps, min(klatka, liczba_klatek))


def okno_nakladki(
    wzor: dict, plan: dict, plansza_uzyta: bool, tryb: str | None = None, dlugosc_krycie_s: float = 0.0,
) -> tuple[float, float]:
    plan_ujecia = plan["ujecia"]
    liczba_klatek = plan["liczba_klatek"]
    fps = plan["fps"]
    klatka_start = koniec_haka(plan, wzor.get("sekcje"))
    klatka_koniec_domyslna = plan_ujecia[-1]["klatka_od"] if plansza_uzyta else liczba_klatek
    if tryb == "krycie" and dlugosc_krycie_s > 0:
        klatka_koniec = min(klatka_start + round(dlugosc_krycie_s * fps), klatka_koniec_domyslna)
    else:
        klatka_koniec = klatka_koniec_domyslna
    return round(klatka_start / fps, 6), round(klatka_koniec / fps, 6)


def okno_znaku(plan: dict, plansza_uzyta: bool) -> float:
    plan_ujecia = plan["ujecia"]
    liczba_klatek = plan["liczba_klatek"]
    fps = plan["fps"]
    klatka_koniec = plan_ujecia[-1]["klatka_od"] if plansza_uzyta else liczba_klatek
    return round(klatka_koniec / fps, 6)


def wczytaj_linie_tekstu(katalog_projektu: Path) -> list[str]:
    sciezka = katalog_projektu / "projekt.json"
    if not sciezka.exists():
        return []
    with open(sciezka, "r", encoding="utf-8") as plik:
        dane = json.load(plik)
    return [wpis["tekst"] for wpis in dane.get("teksty", [])]


def wczytaj_slowa_projektu(katalog_projektu: Path) -> list[str]:
    sciezka = katalog_projektu / "projekt.json"
    if not sciezka.exists():
        return []
    with open(sciezka, "r", encoding="utf-8") as plik:
        dane = json.load(plik)
    slowa = dane.get("slowa")
    return slowa.split(" ") if slowa else []


def wczytaj_pionowy_projektu(katalog_projektu: Path) -> str:
    sciezka = katalog_projektu / "projekt.json"
    if not sciezka.exists():
        return ""
    with open(sciezka, "r", encoding="utf-8") as plik:
        dane = json.load(plik)
    return dane.get("pionowo") or ""


def materializuj_tekst(obraz_napisu, liczba_klatek: int, fps: float, wyjscie: Path) -> None:
    tymczasowy_png = wyjscie.with_suffix(".png")
    obraz_napisu.save(tymczasowy_png)
    uruchom_ffmpeg([
        "-loop", "1", "-i", str(tymczasowy_png),
        "-frames:v", str(liczba_klatek), "-r", str(fps),
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        str(wyjscie),
    ])


def materializuj_warstwe(generator_klatek, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int, wyjscie: Path) -> None:
    proces = subprocess.Popen(
        [
            "ffmpeg", "-y", "-nostdin", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{szerokosc}x{wysokosc}",
            "-framerate", str(fps), "-i", "pipe:0",
            "-frames:v", str(liczba_klatek),
            "-c:v", "png", "-pix_fmt", "rgba",
            str(wyjscie),
        ],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    try:
        for indeks in range(liczba_klatek):
            obraz = generator_klatek(indeks).convert("RGBA")
            proces.stdin.write(numpy.asarray(obraz, dtype=numpy.uint8).tobytes())
    except BrokenPipeError:
        pass
    finally:
        try:
            proces.stdin.close()
        except BrokenPipeError:
            pass
    kod = proces.wait()
    if kod != 0:
        blad = proces.stderr.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {kod}: {blad}")


def kolaz_kwalifikuje(ujecie: dict, numer_klipu: int, klatka_dropu: int | None, okna_slow: list, fps: float) -> bool:
    if numer_klipu % 2 != 1:
        return False
    if ujecie["liczba_klatek"] / fps < MINIMUM_KLIPU_KOLAZU_S:
        return False
    if klatka_dropu is not None and ujecie["klatka_od"] == klatka_dropu:
        return False
    poczatek = ujecie["klatka_od"]
    koniec = poczatek + ujecie["liczba_klatek"]
    for od, do in okna_slow:
        if poczatek < do and od < koniec:
            return False
    return True


def wytnij_do_alfa(sciezka: Path):
    obraz = Image.open(sciezka).convert("RGBA")
    bbox = obraz.getchannel("A").getbbox()
    if bbox is not None:
        obraz = obraz.crop(bbox)
    return obraz


def dopasuj_do_pola_kolazu(obraz, szerokosc: int, wysokosc: int):
    pole_szerokosc = szerokosc * UDZIAL_SZEROKOSCI_KOLAZU
    pole_wysokosc = wysokosc * UDZIAL_WYSOKOSCI_KOLAZU
    skala = min(pole_szerokosc / obraz.width, pole_wysokosc / obraz.height)
    nowy_rozmiar = (max(1, round(obraz.width * skala)), max(1, round(obraz.height * skala)))
    return obraz.resize(nowy_rozmiar, Image.LANCZOS)


def wybierz_wycinki_kolazu(wycinki_posortowane: list[dict], indeks_puli: int) -> tuple[list[dict], int]:
    ile = LICZBA_WYCINKOW_KOLAZU
    wybrane = [wycinki_posortowane[(indeks_puli + i) % len(wycinki_posortowane)] for i in range(ile)]
    return wybrane, indeks_puli + ile


def przygotuj_kolaz(
    wycinki_kolazu: list[dict], uderzenia_lokalne: list[int], liczba_klatek: int, fps: float,
    szerokosc: int, wysokosc: int, wyjscie: Path,
) -> None:
    obrazy = [dopasuj_do_pola_kolazu(wytnij_do_alfa(Path(w["plik"])), szerokosc, wysokosc) for w in wycinki_kolazu]
    poczatki = [uderzenia_lokalne[i] if i < len(uderzenia_lokalne) else liczba_klatek for i in range(len(obrazy))]
    srodki = [(round(POLA_KOLAZU[i][0] * szerokosc), round(POLA_KOLAZU[i][1] * wysokosc)) for i in range(len(obrazy))]

    def klatka_dla(indeks_lokalny: int):
        platno = Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))
        for i, obraz in enumerate(obrazy):
            if indeks_lokalny < poczatki[i]:
                continue
            przesuniecie = indeks_lokalny - poczatki[i]
            skala = WSKOK_SKALE_KOLAZU[przesuniecie] if przesuniecie < len(WSKOK_SKALE_KOLAZU) else 1.0
            szerokosc_klatki = max(1, round(obraz.width * skala))
            wysokosc_klatki = max(1, round(obraz.height * skala))
            wersja = obraz.resize((szerokosc_klatki, wysokosc_klatki), Image.LANCZOS)
            srodek_x, srodek_y = srodki[i]
            platno.alpha_composite(wersja, (srodek_x - szerokosc_klatki // 2, srodek_y - wysokosc_klatki // 2))
        return platno

    materializuj_warstwe(klatka_dla, liczba_klatek, fps, szerokosc, wysokosc, wyjscie)


def uderzenia_wyniku(uderzenia_utworu: list[float], start_audio_s: float, liczba_klatek: int, fps: float) -> list[int]:
    if uderzenia_utworu:
        wynik = []
        widziane = set()
        for uderzenie in uderzenia_utworu:
            klatka = round((uderzenie - start_audio_s) * fps)
            if 0 <= klatka < liczba_klatek and klatka not in widziane:
                widziane.add(klatka)
                wynik.append(klatka)
        return wynik
    krok = round(fps / 2)
    return list(range(0, liczba_klatek, krok)) if krok > 0 else []


def przygotuj_slowa(
    slowa_surowe: list[str], wzor: dict, plan: dict, katalog_pracy: Path,
    szerokosc: int, wysokosc: int, uderzenia_utworu: list[float], start_audio_s: float,
) -> tuple[dict | None, dict | None]:
    if not slowa_surowe:
        return None, None

    fps = plan["fps"]
    liczba_klatek_calosci = plan["liczba_klatek"]
    koniec_haka_klatka = koniec_haka(plan, wzor.get("sekcje"))
    uderzenia = uderzenia_wyniku(uderzenia_utworu, start_audio_s, liczba_klatek_calosci, fps)

    try:
        okna = tekst.okna_slow(len(slowa_surowe), uderzenia, koniec_haka_klatka, fps=fps, liczba_klatek_calosci=liczba_klatek_calosci)
    except ValueError as blad:
        return None, {"pominiete": str(blad)}

    poczatek_warstwy = okna[0][0]
    koniec_warstwy = okna[-1][1]
    liczba_klatek_warstwy = koniec_warstwy - poczatek_warstwy

    odstepy = [uderzenia[i + 1] - uderzenia[i] for i in range(len(uderzenia) - 1)]
    krok = 1 if odstepy and statistics.median(odstepy) >= tekst.PROG_KROKU_KLATEK else 2

    def klatka_dla(indeks_globalny: int):
        klatka_absolutna = poczatek_warstwy + indeks_globalny
        for indeks_slowa, (od, do) in enumerate(okna):
            if od <= klatka_absolutna < do:
                if indeks_slowa == len(slowa_surowe) - 1:
                    wjazd = tekst.skala_wjazdu_akcentu(klatka_absolutna - od)
                    return tekst.obraz_slowa(slowa_surowe[indeks_slowa], szerokosc, wysokosc, akcent=True, wjazd=wjazd)
                return tekst.obraz_slowa(slowa_surowe[indeks_slowa], szerokosc, wysokosc)
        return Image.new("RGBA", (szerokosc, wysokosc), (0, 0, 0, 0))

    sciezka_warstwy = katalog_pracy / "slowa.mov"
    materializuj_warstwe(klatka_dla, liczba_klatek_warstwy, fps, szerokosc, wysokosc, sciezka_warstwy)

    warstwa = {
        "plik": sciezka_warstwy,
        "od_s": round(poczatek_warstwy / fps, 6),
        "do_s": round(koniec_warstwy / fps, 6),
    }
    podsumowanie = {"liczba": len(slowa_surowe), "krok": krok, "okna": [list(okno) for okno in okna]}
    return warstwa, podsumowanie


def przygotuj_pionowy(
    tresc_surowa: str, plan: dict, katalog_pracy: Path, szerokosc: int, wysokosc: int, koniec: int,
) -> tuple[dict | None, dict | None]:
    if not tresc_surowa:
        return None, None

    fps = plan["fps"]
    try:
        poczatek, koniec_pisania, koniec_napisu = tekst.okno_pionowe(plan, len(tresc_surowa), fps, koniec)
    except ValueError as blad:
        return None, {"pominiety": str(blad)}
    liczba_klatek_warstwy = koniec_napisu - poczatek

    def klatka_dla(indeks_lokalny: int):
        klatka_absolutna = poczatek + indeks_lokalny
        if klatka_absolutna < koniec_pisania:
            k = (klatka_absolutna - poczatek) // tekst.KROK_ZNAKOW_KLATKI
        else:
            k = len(tresc_surowa)
        return tekst.obraz_pionowy(tresc_surowa, k, szerokosc, wysokosc)

    sciezka_warstwy = katalog_pracy / "pionowo.mov"
    materializuj_warstwe(klatka_dla, liczba_klatek_warstwy, fps, szerokosc, wysokosc, sciezka_warstwy)

    warstwa = {
        "plik": sciezka_warstwy,
        "od_s": round(poczatek / fps, 6),
        "do_s": round(koniec_napisu / fps, 6),
    }
    podsumowanie = {"znaki": len(tresc_surowa), "od": poczatek, "do": koniec_napisu}
    return warstwa, podsumowanie


def przygotuj_teksty(
    linie_surowe: list[str], wzor: dict, plan: dict, katalog_pracy: Path,
    szerokosc: int, wysokosc: int, styl_tekstu: str, pozycja_tekstu: str, ma_znak: bool,
    koniec_nadpisany: int | None = None,
) -> tuple[list[dict], dict]:
    preset = tekst.PRESETY[styl_tekstu]
    sciezka_czcionki, _ = tekst.wybierz_czcionke(preset)
    znaki = tekst.znaki_czcionki(sciezka_czcionki)

    linie = []
    usuniete_znaki = 0
    for surowa in linie_surowe:
        oczyszczona, usuniete = tekst.oczysc(surowa, znaki)
        usuniete_znaki += usuniete
        if oczyszczona:
            linie.append(oczyszczona)

    podsumowanie_tekstow = {"linie": len(linie), "usuniete_znaki": usuniete_znaki, "okna": []}
    if not linie:
        return [], podsumowanie_tekstow

    fps = plan["fps"]
    koniec_haka_klatka = koniec_nadpisany if koniec_nadpisany is not None else koniec_haka(plan, wzor.get("sekcje"))
    okna = tekst.okna_tekstow(len(linie), plan, koniec_haka_klatka)

    tekst_wzoru = wzor.get("tekst") or {}
    styl = {
        "preset": styl_tekstu,
        "pozycja": tekst_wzoru.get("pozycja", pozycja_tekstu),
        "wersaliki": tekst_wzoru.get("wersaliki"),
    }
    dolna_granica = 0.75 if ma_znak else None

    teksty_do_przebiegu = []
    for indeks, (linia, (klatka_od, klatka_do)) in enumerate(zip(linie, okna)):
        obraz_napisu = tekst.obraz_tekstu(linia, szerokosc, wysokosc, styl, dolna_granica=dolna_granica)
        sciezka_wideo = katalog_pracy / f"tekst_{indeks:02d}.webm"
        materializuj_tekst(obraz_napisu, klatka_do - klatka_od, fps, sciezka_wideo)
        teksty_do_przebiegu.append({
            "plik": sciezka_wideo,
            "od_s": round(klatka_od / fps, 6),
            "do_s": round(klatka_do / fps, 6),
        })
        podsumowanie_tekstow["okna"].append([klatka_od, klatka_do])

    return teksty_do_przebiegu, podsumowanie_tekstow


def zmontuj(
    plan: dict,
    wzor: dict,
    wycinki: list[dict],
    wycinki_wedlug_numeru: dict | None,
    sciezki_robocze: dict,
    czasy_klipow: dict,
    katalog_pracy: Path,
    szerokosc: int,
    wysokosc: int,
    fps: int,
    sila_koloru: float,
    bez_dynamiki: bool,
    uderzenia_wyn: list[int],
    okna_slow: list,
    utwor: Path | None,
    limit_mb: float,
    nakladka: Path | None,
    znak: Path | None,
    dlugosc_nakladki_krycie_s: float,
    teksty_do_przebiegu,
    warstwa_slow,
    warstwa_pionowo,
    plansza: Path | None,
    wyjscie: Path,
    kadry_klipow: dict | None = None,
) -> dict:
    katalog_pracy = Path(katalog_pracy)
    katalog_pracy.mkdir(parents=True, exist_ok=True)
    kadry_klipow = kadry_klipow or {}

    plansza_uzyta = plansza is not None and len(plan["ujecia"]) > 1
    kolorystyka = wzor.get("kolorystyka")
    uzyc_kolor = sila_koloru > 0 and kolorystyka is not None
    sekcje = wzor.get("sekcje")
    klatka_dropu = koniec_haka(plan, sekcje) if sekcje and sekcje.get("drop_ujecie") is not None else None
    licznik_zdjec_montazu = 0
    licznik_klipow = 0
    wycinki_posortowane = sorted(wycinki, key=lambda material: material["message_id"]) if wycinki else []
    indeks_puli_kolazu = 0
    podsumowanie_kolazy = []

    sciezki_segmentow = []
    for indeks, ujecie in enumerate(plan["ujecia"]):
        sciezka_segmentu = katalog_pracy / f"segment_{indeks:06d}.mp4"
        ma_efekt_scenariusza = ujecie.get("efekt_scenariusza") is not None
        if plansza_uzyta and indeks == len(plan["ujecia"]) - 1:
            efekt = None if bez_dynamiki else efekt_ujecia(ujecie, -1, klatka_dropu, licznik_zdjec_montazu)
            segment_planszy(
                plansza, sciezka_segmentu, ujecie["liczba_klatek"], fps, szerokosc, wysokosc,
                przejscie=efekt["przejscie"] if efekt else "brak",
            )
        else:
            lut_nazwa = None
            if uzyc_kolor and ujecie["typ"] == "zdjecie" and ma_alfa_z_pil(Path(ujecie["material"])):
                zrodlo = None
            elif uzyc_kolor and ujecie["typ"] == "zdjecie":
                zrodlo = statystyki_zdjecia(sciezki_robocze[ujecie["material"]], szerokosc=270, wysokosc=480)
            elif uzyc_kolor:
                zrodlo = statystyki_klipu(
                    ujecie["material"], ujecie["start_w_klipie_s"], ujecie["liczba_klatek"] / fps,
                    czasy_klipow[ujecie["material"]], kadr=kadry_klipow.get(ujecie["material"]),
                )
            else:
                zrodlo = None
            if zrodlo is not None:
                cel = kolor.cel_sekcji(kolorystyka, wzor.get("sekcje"), ujecie["numer_wzoru"])
                lut = kolor.lut_transferu(zrodlo, cel, sila_koloru)
                lut_nazwa = f"lut_{indeks:06d}.cube"
                kolor.zapisz_cube(lut, katalog_pracy / lut_nazwa)
            katalog_ffmpeg = katalog_pracy if lut_nazwa is not None else None
            if not bez_dynamiki and ujecie["typ"] == "zdjecie" and klatka_dropu is not None and ujecie["klatka_od"] > klatka_dropu:
                licznik_zdjec_montazu += 1
            if ma_efekt_scenariusza:
                efekt = dict(ujecie["efekt_scenariusza"])
            elif bez_dynamiki:
                efekt = None
            else:
                efekt = efekt_ujecia(ujecie, indeks, klatka_dropu, licznik_zdjec_montazu)
            if efekt is not None and klatka_dropu is not None and ujecie["klatka_od"] == klatka_dropu:
                efekt = dict(efekt, blysk_s=0.3, wstrzas=True)
            if ujecie["typ"] == "zdjecie":
                segment_zdjecia(
                    sciezki_robocze[ujecie["material"]], sciezka_segmentu, indeks, ujecie["liczba_klatek"], fps, szerokosc, wysokosc,
                    lut_sciezka=lut_nazwa, katalog=katalog_ffmpeg,
                    uderzenie=efekt["uderzenie"] if efekt else False,
                    blysk_s=efekt["blysk_s"] if efekt else 0.0,
                    wstrzas=efekt["wstrzas"] if efekt else False,
                    przejscie=efekt["przejscie"] if efekt else "brak",
                )
            else:
                licznik_klipow += 1
                sciezka_kolazu = None
                if ma_efekt_scenariusza:
                    numery_kolazu = ujecie.get("kolaz_scenariusza") or []
                    wybrane = [
                        wycinki_wedlug_numeru[numer] for numer in numery_kolazu
                        if wycinki_wedlug_numeru and numer in wycinki_wedlug_numeru
                    ][:LICZBA_WYCINKOW_KOLAZU]
                    if wybrane:
                        uderzenia_lokalne = [
                            k - ujecie["klatka_od"] for k in uderzenia_wyn
                            if ujecie["klatka_od"] < k < ujecie["klatka_od"] + ujecie["liczba_klatek"]
                        ]
                        sciezka_kolazu = katalog_pracy / f"kolaz_{indeks:06d}.mov"
                        przygotuj_kolaz(wybrane, uderzenia_lokalne, ujecie["liczba_klatek"], fps, szerokosc, wysokosc, sciezka_kolazu)
                        podsumowanie_kolazy.append({"ujecie": indeks, "wycinki": [Path(w["plik"]).name for w in wybrane]})
                elif not bez_dynamiki and wycinki_posortowane and kolaz_kwalifikuje(ujecie, licznik_klipow, klatka_dropu, okna_slow, fps):
                    wybrane, indeks_puli_kolazu = wybierz_wycinki_kolazu(wycinki_posortowane, indeks_puli_kolazu)
                    uderzenia_lokalne = [
                        k - ujecie["klatka_od"] for k in uderzenia_wyn
                        if ujecie["klatka_od"] < k < ujecie["klatka_od"] + ujecie["liczba_klatek"]
                    ]
                    sciezka_kolazu = katalog_pracy / f"kolaz_{indeks:06d}.mov"
                    przygotuj_kolaz(wybrane, uderzenia_lokalne, ujecie["liczba_klatek"], fps, szerokosc, wysokosc, sciezka_kolazu)
                    podsumowanie_kolazy.append({"ujecie": indeks, "wycinki": [Path(w["plik"]).name for w in wybrane]})
                segment_klipu(
                    ujecie["material"], sciezka_segmentu, ujecie["start_w_klipie_s"], ujecie["liczba_klatek"], fps, szerokosc, wysokosc,
                    lut_sciezka=lut_nazwa, katalog=katalog_ffmpeg,
                    uderzenie=efekt["uderzenie"] if efekt else False,
                    blysk_s=efekt["blysk_s"] if efekt else 0.0,
                    wstrzas=efekt["wstrzas"] if efekt else False,
                    przejscie=efekt["przejscie"] if efekt else "brak",
                    kolaz=sciezka_kolazu,
                    kadr=kadry_klipow.get(ujecie["material"]),
                )
        sciezki_segmentow.append(sciezka_segmentu)

    polaczone = katalog_pracy / "polaczone.mp4"
    sklej_segmenty(sciezki_segmentow, polaczone)

    tryb_nak = None
    nakladka_lok = nakladka
    nakladka_od_s = nakladka_do_s = None
    if nakladka_lok is not None:
        tryb_nak = tryb_nakladki(nakladka_lok)
        nakladka_od_s, nakladka_do_s = okno_nakladki(
            wzor, plan, plansza_uzyta, tryb=tryb_nak, dlugosc_krycie_s=dlugosc_nakladki_krycie_s,
        )
        if (nakladka_do_s - nakladka_od_s) * fps < 1:
            nakladka_lok = None
            tryb_nak = None
            nakladka_od_s = nakladka_do_s = None

    znak_do_s = okno_znaku(plan, plansza_uzyta) if znak is not None else None

    przebieg_koncowy(
        polaczone, utwor, plan["start_audio_s"], plan["liczba_klatek"], fps, wyjscie, limit_mb,
        szerokosc=szerokosc, wysokosc=wysokosc,
        nakladka=nakladka_lok, tryb_nakladki_wartosc=tryb_nak,
        nakladka_od_s=nakladka_od_s, nakladka_do_s=nakladka_do_s,
        znak=znak, znak_do_s=znak_do_s,
        teksty=teksty_do_przebiegu,
        slowa=warstwa_slow,
        pionowo=warstwa_pionowo,
    )
    zweryfikuj_wynik(wyjscie, szerokosc, wysokosc, fps, plan["liczba_klatek"], limit_mb)

    return {
        "podsumowanie_kolazy": podsumowanie_kolazy,
        "plansza_uzyta": plansza_uzyta,
        "uzyc_kolor": uzyc_kolor,
        "tryb_nakladki": tryb_nak,
        "nakladka_od_s": nakladka_od_s,
        "nakladka_do_s": nakladka_do_s,
        "znak_do_s": znak_do_s,
        "klatka_dropu": klatka_dropu,
    }


def renderuj(
    wzor_json: Path,
    katalog_projektu: Path,
    utwor: Path | None,
    wyjscie: Path,
    szerokosc: int = 1080,
    wysokosc: int = 1920,
    fps: int = 30,
    limit_mb: float = 50,
    muzyka: Path | None = None,
    nakladka: Path | None = None,
    plansza: Path | None = None,
    znak: Path | None = None,
    sila_koloru: float = 0.6,
    styl_tekstu: str = "szeryf",
    pozycja_tekstu: str = "dol",
    wariant: int = 0,
    bez_dynamiki: bool = False,
    dlugosc_nakladki_krycie_s: float = DLUGOSC_NAKLADKI_KRYCIE_S,
    ai: bool = False,
    model_ai: str = "anthropic/claude-opus-5.5",
    model_ai_zapas: str | None = None,
    bez_rezysera: bool = False,
    bez_krytyka: bool = False,
    prog_oceny_ai: int = 7,
    klient_ai=None,
) -> dict:
    czas_startu = time.time()
    wzor_json = Path(wzor_json).resolve()
    katalog_projektu = Path(katalog_projektu).resolve()
    wyjscie = Path(wyjscie).resolve()
    utwor = Path(utwor).resolve() if utwor is not None else None
    muzyka = Path(muzyka).resolve() if muzyka is not None else None
    nakladka = Path(nakladka).resolve() if nakladka is not None else None
    plansza = Path(plansza).resolve() if plansza is not None else None
    znak = Path(znak).resolve() if znak is not None else None

    with open(wzor_json, "r", encoding="utf-8") as plik:
        wzor = json.load(plik)

    utwor, tryb, uderzenia_utworu, start_uderzenie, przesuniecie_s, wybor = przygotuj_zrodlo_dzwieku(wzor, utwor, muzyka)

    materialy_surowe = magazyn.lista_materialow(katalog_projektu)
    if not materialy_surowe:
        raise RuntimeError("Brak materiałów w projekcie")

    katalog_pracy = katalog_projektu / "praca"
    if katalog_pracy.exists():
        shutil.rmtree(katalog_pracy)
    katalog_pracy.mkdir(parents=True, exist_ok=True)

    materialy_pominiete = []
    do_przygotowania = []
    for material in materialy_surowe:
        if material["typ"] == "klip":
            czas_s = czas_trwania(material["plik"])
            if czas_s is None:
                materialy_pominiete.append({"plik": Path(material["plik"]).name, "powod": "brak strumienia wideo"})
                continue
            material = dict(material, czas_s=czas_s, kadr=wykryj_kadr(material["plik"], czas_s))
        do_przygotowania.append(material)

    dobre, pominiete_z_przygotowania = przygotuj_materialy(do_przygotowania, katalog_pracy, szerokosc, wysokosc)
    materialy_pominiete += pominiete_z_przygotowania
    if not dobre:
        raise RuntimeError("Brak dobrego materiału do renderu")
    dobre = uloz_wariant(dobre, wariant)

    if bez_dynamiki:
        material_zastepczy = [{"plik": "zastepczy", "typ": "zdjecie", "message_id": 0}]
        plan_wstepny = plan_ujec(
            wzor, uderzenia_utworu, material_zastepczy, fps,
            start_uderzenie=start_uderzenie, przesuniecie_s=przesuniecie_s,
        )
        dlugosci_s = [u["liczba_klatek"] / fps for u in plan_wstepny["ujecia"]]
        dlugosc_wstawki_s = min(2.0, max(0.5, statistics.median(dlugosci_s)))

        kawalki = wstawki(dobre, dlugosc_wstawki_s)
        plan = plan_ujec(
            wzor, uderzenia_utworu, kawalki, fps,
            start_uderzenie=start_uderzenie, przesuniecie_s=przesuniecie_s,
        )
        liczba_wycinkow = 0
        wycinki = []
        uderzenia_wyn = []
    else:
        zwykle, wycinki = rozdziel_wycinki(dobre)
        kawalki = przeplot(wstawki(zwykle, DLUGOSC_WSTAWKI_S))
        plan_bazowy = plan_ujec(
            wzor, uderzenia_utworu, kawalki, fps,
            start_uderzenie=start_uderzenie, przesuniecie_s=przesuniecie_s,
        )
        uderzenia_wyn = uderzenia_wyniku(uderzenia_utworu, plan_bazowy["start_audio_s"], plan_bazowy["liczba_klatek"], fps)
        plan = rozloz_tempo(plan_bazowy, wzor, uderzenia_wyn, kawalki, fps)
        liczba_wycinkow = len(wycinki)

    slowa_surowe = wczytaj_slowa_projektu(katalog_projektu)
    warstwa_slow, podsumowanie_slow = przygotuj_slowa(
        slowa_surowe, wzor, plan, katalog_pracy, szerokosc, wysokosc, uderzenia_utworu, plan["start_audio_s"],
    )
    koniec_nadpisany = round(warstwa_slow["od_s"] * fps) if warstwa_slow else None

    linie_surowe = wczytaj_linie_tekstu(katalog_projektu)
    teksty_do_przebiegu, podsumowanie_tekstow = przygotuj_teksty(
        linie_surowe, wzor, plan, katalog_pracy, szerokosc, wysokosc, styl_tekstu, pozycja_tekstu, znak is not None,
        koniec_nadpisany=koniec_nadpisany,
    )

    tresc_pionowa = wczytaj_pionowy_projektu(katalog_projektu)
    koniec_dla_pionowego = koniec_nadpisany if koniec_nadpisany is not None else koniec_haka(plan, wzor.get("sekcje"))
    warstwa_pionowo, podsumowanie_pionowo = przygotuj_pionowy(
        tresc_pionowa, plan, katalog_pracy, szerokosc, wysokosc, koniec_dla_pionowego,
    )

    sciezki_robocze = {str(material["plik"]): material["plik_roboczy"] for material in dobre if material["typ"] == "zdjecie"}
    czasy_klipow = {str(material["plik"]): material["czas_s"] for material in dobre if material["typ"] == "klip"}
    kadry_klipow = {str(material["plik"]): material.get("kadr") for material in dobre if material["typ"] == "klip"}
    okna_slow = podsumowanie_slow.get("okna", []) if podsumowanie_slow else []

    def wykonaj_montaz(plan_do_montazu, wycinki_wedlug_numeru, katalog_pracy_montazu, wyjscie_docelowe):
        return zmontuj(
            plan_do_montazu, wzor, wycinki, wycinki_wedlug_numeru, sciezki_robocze, czasy_klipow, katalog_pracy_montazu,
            szerokosc, wysokosc, fps, sila_koloru, bez_dynamiki, uderzenia_wyn, okna_slow,
            utwor, limit_mb, nakladka, znak, dlugosc_nakladki_krycie_s,
            teksty_do_przebiegu, warstwa_slow, warstwa_pionowo, plansza, wyjscie_docelowe,
            kadry_klipow=kadry_klipow,
        )

    ai_info = None
    if ai and not bez_dynamiki:
        okna_tekstow = {
            "napisy": podsumowanie_tekstow.get("okna", []),
            "slowa": okna_slow,
            "pionowy": (
                [podsumowanie_pionowo["od"], podsumowanie_pionowo["do"]]
                if podsumowanie_pionowo and "od" in podsumowanie_pionowo else None
            ),
        }
        plan, wynik_montazu, ai_info = rezyseruj(
            wzor, wzor_json, plan, plan_bazowy, zwykle, wycinki, uderzenia_wyn, fps,
            katalog_projektu, katalog_pracy, wariant, model_ai, model_ai_zapas,
            bez_rezysera, bez_krytyka, prog_oceny_ai, klient_ai, wykonaj_montaz, wyjscie,
            okna_tekstow=okna_tekstow,
        )
    else:
        wynik_montazu = wykonaj_montaz(plan, None, katalog_pracy / "montaz", wyjscie)

    materialy_uzyte = len({u["material"] for u in plan["ujecia"]})
    rozmiar_mb = wyjscie.stat().st_size / (1024 * 1024)

    dlugosci_zdjec_s = [u["liczba_klatek"] / fps for u in plan["ujecia"] if u["typ"] == "zdjecie"]
    dlugosci_klipow_s = [u["liczba_klatek"] / fps for u in plan["ujecia"] if u["typ"] == "klip"]
    podsumowanie_dynamiki = {
        "ujecia": len(plan["ujecia"]),
        "mediana_zdjecia_s": round(statistics.median(dlugosci_zdjec_s), 3) if dlugosci_zdjec_s else None,
        "mediana_klipu_s": round(statistics.median(dlugosci_klipow_s), 3) if dlugosci_klipow_s else None,
        "wycinki": liczba_wycinkow,
    }

    podsumowanie = {
        "wariant": wariant,
        "czas_s": round(plan["liczba_klatek"] / fps, 3),
        "liczba_ujec": len(plan["ujecia"]),
        "materialy_uzyte": materialy_uzyte,
        "materialy_pominiete": materialy_pominiete,
        "rozmiar_mb": round(rozmiar_mb, 2),
        "czas_renderu_s": round(time.time() - czas_startu, 2),
        "utwor": {
            "plik": utwor.name,
            "tryb": tryb,
            "zgodnosc": wybor.get("zgodnosc") if wybor else None,
            "start_s": round(plan["start_audio_s"], 3),
            "tempo_bpm": wybor.get("tempo_bpm") if wybor else None,
            "mnoznik": wybor.get("mnoznik") if wybor else 1.0,
        },
        "nakladka": (
            {"plik": Path(nakladka).name, "tryb": wynik_montazu["tryb_nakladki"], "od_s": wynik_montazu["nakladka_od_s"], "do_s": wynik_montazu["nakladka_do_s"]}
            if nakladka is not None and wynik_montazu["tryb_nakladki"] is not None else None
        ),
        "plansza": Path(plansza).name if wynik_montazu["plansza_uzyta"] else None,
        "znak": znak is not None,
        "drop_s": pozycja_dropu_w_planie(wzor, plan["ujecia"], fps),
        "kolor": {"sila": sila_koloru, "sekcje": bool(wzor.get("sekcje"))} if wynik_montazu["uzyc_kolor"] else None,
        "teksty": podsumowanie_tekstow,
        "slowa": podsumowanie_slow,
        "pionowo": podsumowanie_pionowo,
        "dynamika": podsumowanie_dynamiki,
        "kolaze": wynik_montazu["podsumowanie_kolazy"],
        "pasy": [{"plik": Path(plik).name, "kadr": kadr} for plik, kadr in kadry_klipow.items() if kadr],
        "ai": ai_info,
    }

    sciezka_podsumowania = wyjscie.with_suffix(".json")
    with open(sciezka_podsumowania, "w", encoding="utf-8") as plik:
        json.dump(podsumowanie, plik, ensure_ascii=False, indent=2)

    shutil.rmtree(katalog_pracy)
    return podsumowanie


def glowna(argumenty: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wzor", required=True)
    parser.add_argument("--projekt", required=True)
    parser.add_argument("--utwor")
    parser.add_argument("--muzyka")
    parser.add_argument("--wyjscie", required=True)
    parser.add_argument("--szerokosc", type=int, default=1080)
    parser.add_argument("--wysokosc", type=int, default=1920)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--limit-mb", type=float, default=50)
    parser.add_argument("--nakladka")
    parser.add_argument("--plansza")
    parser.add_argument("--znak")
    parser.add_argument("--sila-koloru", type=float, default=0.6)
    parser.add_argument("--styl-tekstu", choices=sorted(tekst.PRESETY), default="szeryf")
    parser.add_argument("--pozycja-tekstu", choices=sorted(tekst.POZYCJE), default="dol")
    parser.add_argument("--wariant", type=int, default=0)
    parser.add_argument("--bez-dynamiki", action="store_true")
    parser.add_argument("--dlugosc-nakladki-krycie", type=float, default=DLUGOSC_NAKLADKI_KRYCIE_S)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--model-ai", default="anthropic/claude-opus-5.5")
    parser.add_argument("--model-ai-zapas")
    parser.add_argument("--bez-rezysera", action="store_true")
    parser.add_argument("--bez-krytyka", action="store_true")
    parser.add_argument("--prog-oceny-ai", type=int, default=7)
    ustalone = parser.parse_args(argumenty)
    try:
        renderuj(
            Path(ustalone.wzor), Path(ustalone.projekt),
            Path(ustalone.utwor) if ustalone.utwor else None, Path(ustalone.wyjscie),
            szerokosc=ustalone.szerokosc, wysokosc=ustalone.wysokosc, fps=ustalone.fps, limit_mb=ustalone.limit_mb,
            muzyka=Path(ustalone.muzyka) if ustalone.muzyka else None,
            nakladka=Path(ustalone.nakladka) if ustalone.nakladka else None,
            plansza=Path(ustalone.plansza) if ustalone.plansza else None,
            znak=Path(ustalone.znak) if ustalone.znak else None,
            sila_koloru=ustalone.sila_koloru,
            styl_tekstu=ustalone.styl_tekstu,
            pozycja_tekstu=ustalone.pozycja_tekstu,
            wariant=ustalone.wariant,
            bez_dynamiki=ustalone.bez_dynamiki,
            dlugosc_nakladki_krycie_s=ustalone.dlugosc_nakladki_krycie,
            ai=ustalone.ai,
            model_ai=ustalone.model_ai,
            model_ai_zapas=ustalone.model_ai_zapas,
            bez_rezysera=ustalone.bez_rezysera,
            bez_krytyka=ustalone.bez_krytyka,
            prog_oceny_ai=ustalone.prog_oceny_ai,
        )
    except Exception as blad:
        print(str(blad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(glowna())
