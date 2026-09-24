import argparse
import json
import statistics
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy
import pillow_heif
from PIL import Image, ImageOps

import analyze
import magazyn
import music

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


def uruchom_ffmpeg(argumenty: list[str]) -> None:
    wynik = subprocess.run(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", *argumenty],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    if wynik.returncode != 0:
        raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")


def ma_strumien_wideo(sciezka) -> bool:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return wynik.returncode == 0 and wynik.stdout.decode("utf-8", errors="replace").strip() != ""


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


def wyrazenie_zoom(numer_ujecia: int, liczba_klatek: int) -> str:
    if liczba_klatek <= 1:
        krok = 0.0
    else:
        krok = (ZOOM_MAKSYMALNY - 1.0) / (liczba_klatek - 1)
    if numer_ujecia % 2 == 0:
        return f"min(zoom+{krok:.8f},{ZOOM_MAKSYMALNY})"
    return f"if(eq(on,0),{ZOOM_MAKSYMALNY},max(zoom-{krok:.8f},1.0))"


def segment_zdjecia(sciezka_przygotowana: Path, wyjscie: Path, numer_ujecia: int, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int) -> None:
    szerokosc_robocza = szerokosc * MNOZNIK_ROBOCZY_ZOOM
    wysokosc_robocza = wysokosc * MNOZNIK_ROBOCZY_ZOOM
    wyrazenie = wyrazenie_zoom(numer_ujecia, liczba_klatek)
    filtr = (
        f"scale={szerokosc_robocza}:{wysokosc_robocza}:force_original_aspect_ratio=increase,"
        f"crop={szerokosc_robocza}:{wysokosc_robocza},"
        f"zoompan=z='{wyrazenie}':d=1:s={szerokosc_robocza}x{wysokosc_robocza}:fps={fps},"
        f"scale={szerokosc}:{wysokosc}:flags=lanczos,setsar=1"
    )
    uruchom_ffmpeg([
        "-loop", "1", "-i", str(sciezka_przygotowana),
        "-vf", filtr,
        "-frames:v", str(liczba_klatek),
        "-an",
        *PARAMETRY_KODOWANIA_SEGMENTU,
        str(wyjscie),
    ])


def segment_klipu(sciezka_zrodlowa, wyjscie: Path, start_s: float, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int) -> None:
    filtr = (
        f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,"
        f"crop={szerokosc}:{wysokosc},"
        f"fps={fps},"
        f"tpad=stop_mode=clone:stop=-1,"
        f"setsar=1"
    )
    uruchom_ffmpeg([
        "-ss", f"{start_s:.6f}", "-i", str(sciezka_zrodlowa),
        "-vf", filtr,
        "-frames:v", str(liczba_klatek),
        "-an",
        *PARAMETRY_KODOWANIA_SEGMENTU,
        str(wyjscie),
    ])


def segment_planszy(sciezka, wyjscie: Path, liczba_klatek: int, fps: float, szerokosc: int, wysokosc: int) -> None:
    sciezka = Path(sciezka)
    wyjscie = Path(wyjscie)
    jest_zdjeciem = magazyn.typ_pliku(sciezka.name, None) == "zdjecie"

    tlo = f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,crop={szerokosc}:{wysokosc},boxblur={PROMIEN_ROZMYCIA_PLANSZY}:2"
    pierwszy_plan = f"scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=decrease,setsar=1"
    ogon = f",fps={fps}"
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


def pierwsza_klatka_zielona(sciezka: Path) -> bool:
    with tempfile.TemporaryDirectory() as katalog_tymczasowy:
        klatka = Path(katalog_tymczasowy) / "klatka.png"
        wynik = subprocess.run(
            ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(sciezka), "-frames:v", "1", str(klatka)],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0 or not klatka.exists():
            return False
        with Image.open(klatka) as obraz:
            tablica = numpy.array(obraz.convert("RGB")).reshape(-1, 3)
    if tablica.size == 0:
        return False
    zielone = numpy.count_nonzero((tablica[:, 1] > 150) & (tablica[:, 0] < 100) & (tablica[:, 2] < 100))
    return zielone / len(tablica) >= PROG_ZIELENI


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
    return "ekran"


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
) -> None:
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
        if nakladka.suffix.lower() == ".png":
            wejscia += ["-loop", "1", "-t", f"{okno_s:.6f}", "-i", str(nakladka)]
        else:
            strumien = strumien_wideo_nakladki(nakladka)
            if strumien is not None and wymaga_dekodera_vp9_alfa(strumien):
                wejscia += ["-c:v", "libvpx-vp9"]
            wejscia += ["-stream_loop", "-1", "-t", f"{okno_s:.6f}", "-i", str(nakladka)]

        przygotowanie_nakladki = (
            f"[2:v]scale={szerokosc}:{wysokosc}:force_original_aspect_ratio=increase,"
            f"crop={szerokosc}:{wysokosc},fps={fps}"
        )
        warunek = f"between(t,{nakladka_od_s:.6f},{nakladka_do_s:.6f})"
        if tryb_nakladki_wartosc == "alfa":
            przygotowanie_nakladki += f",format=rgba,setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            kompozycja = f"[0:v][nak]overlay=eval=frame:enable='{warunek}',setsar=1[v]"
        elif tryb_nakladki_wartosc == "zielen":
            przygotowanie_nakladki += f",format=rgba,colorkey=0x00FF00:0.3:0.1,setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            kompozycja = f"[0:v][nak]overlay=eval=frame:enable='{warunek}',setsar=1[v]"
        else:
            przygotowanie_nakladki += f",format=gbrp,setpts=PTS+{nakladka_od_s:.6f}/TB[nak]"
            kompozycja = (
                f"[0:v]format=gbrp[glowne];[glowne][nak]blend=all_mode=screen:enable='{warunek}',"
                f"scale=out_range=tv,format=yuv420p,setsar=1[v]"
            )

        filtr = (
            f"{przygotowanie_nakladki};{kompozycja};"
            f"[1:a]afade=t=out:st={poczatek_wyciszenia:.6f}:d={wyciszenie_s:.6f}[a]"
        )
        mapa_wideo = "[v]"

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


def okno_nakladki(wzor: dict, plan: dict, plansza_uzyta: bool) -> tuple[float, float]:
    plan_ujecia = plan["ujecia"]
    liczba_klatek = plan["liczba_klatek"]
    fps = plan["fps"]
    klatka_start = koniec_haka(plan, wzor.get("sekcje"))
    klatka_koniec = plan_ujecia[-1]["klatka_od"] if plansza_uzyta else liczba_klatek
    return round(klatka_start / fps, 6), round(klatka_koniec / fps, 6)


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
) -> dict:
    czas_startu = time.time()
    wzor_json = Path(wzor_json)
    katalog_projektu = Path(katalog_projektu)
    wyjscie = Path(wyjscie)

    with open(wzor_json, "r", encoding="utf-8") as plik:
        wzor = json.load(plik)

    utwor, tryb, uderzenia_utworu, start_uderzenie, przesuniecie_s, wybor = przygotuj_zrodlo_dzwieku(wzor, utwor, muzyka)

    materialy_surowe = magazyn.lista_materialow(katalog_projektu)
    if not materialy_surowe:
        raise RuntimeError("Brak materiałów w projekcie")

    katalog_pracy = katalog_projektu / "praca"
    katalog_pracy.mkdir(parents=True, exist_ok=True)

    materialy_pominiete = []
    do_przygotowania = []
    for material in materialy_surowe:
        if material["typ"] == "klip":
            czas_s = czas_trwania(material["plik"])
            if czas_s is None:
                materialy_pominiete.append({"plik": Path(material["plik"]).name, "powod": "brak strumienia wideo"})
                continue
            material = dict(material, czas_s=czas_s)
        do_przygotowania.append(material)

    dobre, pominiete_z_przygotowania = przygotuj_materialy(do_przygotowania, katalog_pracy, szerokosc, wysokosc)
    materialy_pominiete += pominiete_z_przygotowania
    if not dobre:
        raise RuntimeError("Brak dobrego materiału do renderu")

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

    sciezki_robocze = {str(material["plik"]): material["plik_roboczy"] for material in dobre if material["typ"] == "zdjecie"}

    plansza_uzyta = plansza is not None and len(plan["ujecia"]) > 1

    sciezki_segmentow = []
    for indeks, ujecie in enumerate(plan["ujecia"]):
        sciezka_segmentu = katalog_pracy / f"segment_{indeks:06d}.mp4"
        if plansza_uzyta and indeks == len(plan["ujecia"]) - 1:
            segment_planszy(plansza, sciezka_segmentu, ujecie["liczba_klatek"], fps, szerokosc, wysokosc)
        elif ujecie["typ"] == "zdjecie":
            segment_zdjecia(sciezki_robocze[ujecie["material"]], sciezka_segmentu, indeks, ujecie["liczba_klatek"], fps, szerokosc, wysokosc)
        else:
            segment_klipu(ujecie["material"], sciezka_segmentu, ujecie["start_w_klipie_s"], ujecie["liczba_klatek"], fps, szerokosc, wysokosc)
        sciezki_segmentow.append(sciezka_segmentu)

    polaczone = katalog_pracy / "polaczone.mp4"
    sklej_segmenty(sciezki_segmentow, polaczone)

    tryb_nak = None
    nakladka_od_s = nakladka_do_s = None
    if nakladka is not None:
        tryb_nak = tryb_nakladki(nakladka)
        nakladka_od_s, nakladka_do_s = okno_nakladki(wzor, plan, plansza_uzyta)
        if (nakladka_do_s - nakladka_od_s) * fps < 1:
            nakladka = None
            tryb_nak = None
            nakladka_od_s = nakladka_do_s = None

    przebieg_koncowy(
        polaczone, utwor, plan["start_audio_s"], plan["liczba_klatek"], fps, wyjscie, limit_mb,
        szerokosc=szerokosc, wysokosc=wysokosc,
        nakladka=nakladka, tryb_nakladki_wartosc=tryb_nak,
        nakladka_od_s=nakladka_od_s, nakladka_do_s=nakladka_do_s,
    )
    zweryfikuj_wynik(wyjscie, szerokosc, wysokosc, fps, plan["liczba_klatek"], limit_mb)

    materialy_uzyte = len({u["material"] for u in plan["ujecia"]})
    rozmiar_mb = wyjscie.stat().st_size / (1024 * 1024)

    podsumowanie = {
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
            {"plik": Path(nakladka).name, "tryb": tryb_nak, "od_s": nakladka_od_s, "do_s": nakladka_do_s}
            if nakladka is not None else None
        ),
        "plansza": Path(plansza).name if plansza_uzyta else None,
        "drop_s": pozycja_dropu_w_planie(wzor, plan["ujecia"], fps),
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
    ustalone = parser.parse_args(argumenty)
    try:
        renderuj(
            Path(ustalone.wzor), Path(ustalone.projekt),
            Path(ustalone.utwor) if ustalone.utwor else None, Path(ustalone.wyjscie),
            szerokosc=ustalone.szerokosc, wysokosc=ustalone.wysokosc, fps=ustalone.fps, limit_mb=ustalone.limit_mb,
            muzyka=Path(ustalone.muzyka) if ustalone.muzyka else None,
            nakladka=Path(ustalone.nakladka) if ustalone.nakladka else None,
            plansza=Path(ustalone.plansza) if ustalone.plansza else None,
        )
    except Exception as blad:
        print(str(blad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(glowna())
