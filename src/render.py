import subprocess
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps

import analyze

pillow_heif.register_heif_opener()

MNOZNIK_ROBOCZY_ZOOM = 2
ZOOM_MAKSYMALNY = 1.12
PARAMETRY_KODOWANIA_SEGMENTU = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]


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
) -> dict:
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
        })

    return {
        "fps": fps,
        "start_audio_s": round(start_audio_s, 6),
        "liczba_klatek": liczba_klatek,
        "ujecia": ujecia,
    }
