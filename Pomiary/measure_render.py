import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 3 (render).
# Sekcja A (syntetyczna, 1080x1920): wzor 40 ciec co jedno uderzenie, materialy roznorodne
#   (obroty EXIF, przezroczystosc, HEIC, klip z obrotem, klip krotszy od ujecia), utwor klik
#   124 BPM jako mp3. Progi: 100% granic planu znalezionych w wyniku (tolerancja 1 klatka),
#   mediana odleglosci ciec od najblizszego uderzenia lub polowy uderzenia do 20 ms, pelna
#   zgodnosc formatu wyjsciowego.
# Sekcja B: sam przebieg koncowy (bez segmentow) na 60 s szumu 1080x1920, limit 50 MB.
#   Prog: wynik najwyzej 47,5 MB.
# Sekcja C (realne pliki, tylko gdy jest dane/muzyka/staly.mp3): kazdy wzor z katalogu probek
#   analizowany raz (cache w outputs/wzor_<nazwa>.json), potem render z materialow probek albo
#   z najnowszego projektu z co najmniej 3 materialami. Tylko raport i arkusze PNG.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import analyze  # noqa: E402
import generuj  # noqa: E402
import magazyn  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_render.json"
DOMYSLNY_KATALOG_WZOROW_C = KATALOG_REPO / "dane" / "probki" / "wzory"

FPS = 30
SZEROKOSC_A = 1080
WYSOKOSC_A = 1920
LICZBA_CIEC_A = 40
BPM_UTWORU_A = 124
CZAS_UTWORU_A_S = 60.0
TOLERANCJA_KLATEK = 1
PROG_MEDIANY_RYTMU_S = 0.020
PROG_ROZMIARU_B_MB = 47.5
LIMIT_ARKUSZA_C_PX = 1600

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def zakoduj_do_mp3(wav: Path, mp3: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)],
        check=True,
    )


def dopasuj(oczekiwane: list[int], znalezione: list[int], tolerancja: int) -> int:
    wolne = list(znalezione)
    trafione = 0
    for klatka in oczekiwane:
        najlepszy = None
        for kandydat in wolne:
            if abs(kandydat - klatka) <= tolerancja and (najlepszy is None or abs(kandydat - klatka) < abs(najlepszy - klatka)):
                najlepszy = kandydat
        if najlepszy is not None:
            wolne.remove(najlepszy)
            trafione += 1
    return trafione


def mediana_odleglosci_do_rytmu(ciecia_s: list[float], uderzenia_s: list[float]) -> float | None:
    if len(uderzenia_s) < 2:
        return None
    wlasciwe = [t for t in ciecia_s if t > 0]
    if not wlasciwe:
        return None
    punkty = np.array(list(uderzenia_s) + [(a + b) / 2 for a, b in zip(uderzenia_s, uderzenia_s[1:])])
    odleglosci = [float(np.min(np.abs(punkty - t))) for t in wlasciwe]
    return statistics.median(odleglosci)


def sprawdz_format(sciezka: Path, fps: int) -> tuple[bool, dict]:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    dane = json.loads(wynik.stdout.decode("utf-8", errors="replace"))
    wideo = next(s for s in dane["streams"] if s["codec_type"] == "video")
    audio = next((s for s in dane["streams"] if s["codec_type"] == "audio"), None)
    szczegoly = {
        "kodek_wideo": wideo.get("codec_name"),
        "profil": wideo.get("profile"),
        "pix_fmt": wideo.get("pix_fmt"),
        "sar": wideo.get("sample_aspect_ratio"),
        "fps_zgloszony": wideo.get("r_frame_rate"),
        "czas_strumienia_wideo_s": float(wideo["duration"]) if wideo.get("duration") else None,
        "kodek_audio": audio.get("codec_name") if audio else None,
        "audio_sr": audio.get("sample_rate") if audio else None,
        "audio_kanaly": audio.get("channels") if audio else None,
        "czas_strumienia_audio_s": float(audio["duration"]) if audio and audio.get("duration") else None,
    }
    ok = (
        wideo.get("codec_name") == "h264"
        and wideo.get("profile") == "High"
        and wideo.get("pix_fmt") == "yuv420p"
        and wideo.get("sample_aspect_ratio") == "1:1"
        and wideo.get("r_frame_rate") == f"{fps}/1"
        and audio is not None
        and audio.get("codec_name") == "aac"
        and audio.get("sample_rate") == "48000"
        and audio.get("channels") == 2
    )
    return ok, szczegoly


def wzor_syntetyczny_a() -> dict:
    return {
        "wersja": 1,
        "id": "syntetyczny_a",
        "zrodlo": {"czas_s": 20.0, "szerokosc": SZEROKOSC_A, "wysokosc": WYSOKOSC_A, "fps": 30.0, "ma_dzwiek": True},
        "ciecia_s": [round(i * 0.5, 3) for i in range(LICZBA_CIEC_A)],
        "tempo_bpm": 120.0,
        "uderzenia_s": [round(i * 0.5, 3) for i in range(LICZBA_CIEC_A + 1)],
        "ciecia_uderzenia": [float(i) for i in range(LICZBA_CIEC_A)],
        "koniec_uderzenia": float(LICZBA_CIEC_A),
        "kolorystyka": None,
        "tekst": None,
    }


def zbuduj_materialy_a(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    message_id = 1
    orientacje = {2: 6, 5: 8}
    for i in range(10):
        kolor = generuj.kolor_ujecia(20 + i)
        if i == 7:
            sciezka = katalog_materialow / f"{message_id:010d}_p{i}.png"
            generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), alfa=True, kolor=kolor)
        elif i == 9:
            sciezka = katalog_materialow / f"{message_id:010d}_p{i}.heic"
            generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), kolor=kolor)
        else:
            sciezka = katalog_materialow / f"{message_id:010d}_p{i}.jpg"
            generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), orientacja_exif=orientacje.get(i, 1), kolor=kolor)
        message_id += 1

    sciezka_obrot = katalog_materialow / f"{message_id:010d}_k0.mp4"
    generuj.klip_testowy(sciezka_obrot, czas_s=0.4, rozmiar=(SZEROKOSC_A, WYSOKOSC_A), obrot=90, kolor=generuj.kolor_ujecia(50))
    message_id += 1

    sciezka_krotki = katalog_materialow / f"{message_id:010d}_k1.mp4"
    generuj.klip_testowy(sciezka_krotki, czas_s=0.2, rozmiar=(SZEROKOSC_A, WYSOKOSC_A), obrot=0, kolor=generuj.kolor_ujecia(51))
    message_id += 1

    sciezka_wieloujeciowy = katalog_materialow / f"{message_id:010d}_k2.mp4"
    ciecia_wieloujeciowe = [round(i * 0.5, 3) for i in range(1, 12)]
    generuj.wideo_z_cieciami(sciezka_wieloujeciowy, ciecia_wieloujeciowe, 6.0, fps=FPS, rozmiar=(SZEROKOSC_A, WYSOKOSC_A))
    message_id += 1


def sekcja_a() -> dict:
    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        projekt = katalog / "projekt"
        zbuduj_materialy_a(projekt / "materialy")

        wzor = wzor_syntetyczny_a()
        wzor_json = katalog / "wzor.json"
        wzor_json.write_text(json.dumps(wzor), encoding="utf-8")

        utwor_wav = katalog / "klik.wav"
        generuj.klik(utwor_wav, bpm=BPM_UTWORU_A, czas_s=CZAS_UTWORU_A_S, pierwsze_uderzenie_s=0.3)
        utwor_mp3 = katalog / "staly.mp3"
        zakoduj_do_mp3(utwor_wav, utwor_mp3)

        wyjscie = KATALOG_OUTPUTS / "render_a.mp4"
        podsumowanie = render.renderuj(
            wzor_json, projekt, utwor_mp3, wyjscie,
            szerokosc=SZEROKOSC_A, wysokosc=WYSOKOSC_A, fps=FPS, limit_mb=50,
        )

        _, uderzenia_utworu = analyze.analizuj_rytm(utwor_mp3)
        material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
        plan = render.plan_ujec(wzor, uderzenia_utworu, material_zastepczy, FPS)
        oczekiwane_klatki = [u["klatka_od"] for u in plan["ujecia"][1:]]

        wykryte_s = analyze.wykryj_ciecia(wyjscie)
        wykryte_klatki = [int(round(t * FPS)) for t in wykryte_s if t > 0]
        trafione = dopasuj(oczekiwane_klatki, wykryte_klatki, TOLERANCJA_KLATEK)
        odsetek = trafione / len(oczekiwane_klatki) if oczekiwane_klatki else None

        _, uderzenia_wyniku = analyze.analizuj_rytm(wyjscie)
        mediana_s = mediana_odleglosci_do_rytmu(wykryte_s, uderzenia_wyniku)

        format_ok, szczegoly_formatu = sprawdz_format(wyjscie, FPS)

    wyniki = {
        "czas_renderu_s": round(podsumowanie["czas_renderu_s"], 2),
        "sekundy_renderu_na_sekunde_wyniku": round(podsumowanie["czas_renderu_s"] / podsumowanie["czas_s"], 3),
        "rozmiar_mb": podsumowanie["rozmiar_mb"],
        "czas_wyniku_s": podsumowanie["czas_s"],
        "liczba_ujec": podsumowanie["liczba_ujec"],
        "materialy_uzyte": podsumowanie["materialy_uzyte"],
        "materialy_pominiete": podsumowanie["materialy_pominiete"],
        "granice_oczekiwane": len(oczekiwane_klatki),
        "granice_znalezione_w_tolerancji": trafione,
        "odsetek_granic_znalezionych": None if odsetek is None else round(odsetek, 4),
        "mediana_odleglosci_od_rytmu_ms": None if mediana_s is None else round(mediana_s * 1000, 2),
        "format": szczegoly_formatu,
    }
    wyniki["progi"] = {
        "granice_100_proc": odsetek == 1.0,
        "mediana_do_20ms": mediana_s is not None and mediana_s <= PROG_MEDIANY_RYTMU_S,
        "format_pelna_zgodnosc": format_ok,
    }
    print(f"A: {wyniki['progi']}, granice {trafione}/{len(oczekiwane_klatki)}, mediana {wyniki['mediana_odleglosci_od_rytmu_ms']} ms")
    return wyniki


def sekcja_b() -> dict:
    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        szum = katalog / "szum.mp4"
        generuj.szum(szum, czas_s=60.0, rozmiar=(SZEROKOSC_A, WYSOKOSC_A), fps=FPS)
        utwor_wav = katalog / "audio.wav"
        generuj.klik(utwor_wav, bpm=120, czas_s=61.0)
        wyjscie = katalog / "wynik_b.mp4"
        liczba_klatek = int(round(60.0 * FPS))

        start = time.monotonic()
        render.przebieg_koncowy(szum, utwor_wav, 0.0, liczba_klatek, FPS, wyjscie, 50)
        czas_s = time.monotonic() - start
        rozmiar_mb = wyjscie.stat().st_size / (1024 * 1024)

    wyniki = {"czas_s": round(czas_s, 2), "rozmiar_mb": round(rozmiar_mb, 2)}
    wyniki["progi"] = {"rozmiar_do_47_5mb": rozmiar_mb <= PROG_ROZMIARU_B_MB}
    print(f"B: {wyniki}")
    return wyniki


def znajdz_katalog_projektu_probek(katalog_repo: Path) -> Path | None:
    probki = katalog_repo / "dane" / "probki"
    if (probki / "materialy").is_dir() and any((probki / "materialy").iterdir()):
        return probki
    projekty = katalog_repo / "dane" / "projekty"
    if not projekty.is_dir():
        return None
    for katalog in sorted(projekty.iterdir(), key=lambda k: k.name, reverse=True):
        if katalog.is_dir() and len(magazyn.lista_materialow(katalog)) >= 3:
            return katalog
    return None


def wczytaj_lub_przeanalizuj_wzor(sciezka: Path) -> dict:
    nazwa = sciezka.stem
    cel = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    if cel.is_file():
        print(f"C {nazwa}: wzor z cache ({cel.name})")
        return json.loads(cel.read_text(encoding="utf-8"))
    start = time.monotonic()
    dane = analyze.analizuj_wzor(sciezka, nazwa)
    czas = time.monotonic() - start
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"C {nazwa}: analiza wzoru w {czas:.1f} s")
    return dane


def arkusz_wyniku(wyjscie: Path, plan: dict, nazwa: str) -> str | None:
    ujecia = plan["ujecia"]
    if not ujecia:
        return None
    uchwyt = cv2.VideoCapture(str(wyjscie))
    miniatury = []
    for ujecie in ujecia:
        srodek = ujecie["klatka_od"] + ujecie["liczba_klatek"] // 2
        uchwyt.set(cv2.CAP_PROP_POS_FRAMES, srodek)
        ok, klatka = uchwyt.read()
        if ok:
            miniatury.append(klatka)
    uchwyt.release()
    if not miniatury:
        return None
    kolumny = max(1, int(math.ceil(math.sqrt(len(miniatury)))))
    wiersze = int(math.ceil(len(miniatury) / kolumny))
    bok = max(1, LIMIT_ARKUSZA_C_PX // max(kolumny, wiersze))
    komorki = [cv2.resize(m, (bok, bok), interpolation=cv2.INTER_AREA) for m in miniatury]
    puste = np.zeros((bok, bok, 3), dtype=np.uint8)
    while len(komorki) < kolumny * wiersze:
        komorki.append(puste)
    siatka = np.vstack([np.hstack(komorki[i * kolumny:(i + 1) * kolumny]) for i in range(wiersze)])
    cel = KATALOG_OUTPUTS / f"render_{nazwa}.png"
    ok, bufor = cv2.imencode(".png", siatka)
    if ok:
        cel.write_bytes(bufor.tobytes())
        return cel.name
    return None


def sekcja_c(katalog_wzorow_arg: Path | None) -> dict:
    staly = KATALOG_REPO / "dane" / "muzyka" / "staly.mp3"
    if not staly.is_file():
        print("C pominieta: brak dane/muzyka/staly.mp3")
        return {"pominieta": True, "powod": "brak dane/muzyka/staly.mp3"}

    katalog_wzorow = katalog_wzorow_arg or DOMYSLNY_KATALOG_WZOROW_C
    rozszerzenia = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
    pliki_wzorow = sorted(p for p in katalog_wzorow.glob("*") if p.suffix.lower() in rozszerzenia) if katalog_wzorow.is_dir() else []
    if not pliki_wzorow:
        print(f"C pominieta: brak plikow w {katalog_wzorow}")
        return {"pominieta": True, "powod": f"brak plikow w {katalog_wzorow}"}

    katalog_projektu = znajdz_katalog_projektu_probek(KATALOG_REPO)
    if katalog_projektu is None:
        print("C pominieta: brak materialow probek ani projektu z co najmniej 3 materialami")
        return {"pominieta": True, "powod": "brak materialow"}

    _, uderzenia_utworu = analyze.analizuj_rytm(staly)
    material_zastepczy = [{"plik": "x", "typ": "zdjecie", "message_id": 0}]
    wyniki = {"katalog_wzorow": str(katalog_wzorow), "katalog_materialow": str(katalog_projektu), "wzory": []}
    for sciezka in pliki_wzorow:
        nazwa = sciezka.stem
        wzor = wczytaj_lub_przeanalizuj_wzor(sciezka)
        wyjscie = KATALOG_OUTPUTS / f"render_{nazwa}.mp4"
        start = time.monotonic()
        try:
            podsumowanie = render.renderuj(KATALOG_OUTPUTS / f"wzor_{nazwa}.json", katalog_projektu, staly, wyjscie)
        except Exception as blad:
            wpis = {"wzor": nazwa, "blad": str(blad)}
            wyniki["wzory"].append(wpis)
            print(f"C {nazwa}: BLAD {blad}")
            zapisz_sekcje("C", wyniki)
            continue
        czas_calkowity_s = round(time.monotonic() - start, 2)

        plan = render.plan_ujec(wzor, uderzenia_utworu, material_zastepczy, FPS)
        arkusz = arkusz_wyniku(wyjscie, plan, nazwa)

        wpis = {
            "wzor": nazwa,
            "czas_renderu_s": round(podsumowanie["czas_renderu_s"], 2),
            "czas_calkowity_s": czas_calkowity_s,
            "rozmiar_mb": podsumowanie["rozmiar_mb"],
            "liczba_ujec": podsumowanie["liczba_ujec"],
            "materialy_uzyte": podsumowanie["materialy_uzyte"],
            "materialy_pominiete": podsumowanie["materialy_pominiete"],
            "arkusz": arkusz,
        }
        wyniki["wzory"].append(wpis)
        print(f"C {nazwa}: {wpis}")
        zapisz_sekcje("C", wyniki)
    return wyniki


def main() -> int:
    katalog_wzorow_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    wyniki_a = sekcja_a()
    zapisz_sekcje("A", wyniki_a)

    wyniki_b = sekcja_b()
    zapisz_sekcje("B", wyniki_b)

    wyniki_c = sekcja_c(katalog_wzorow_arg)
    zapisz_sekcje("C", wyniki_c)

    zaliczone = all(wyniki_a["progi"].values()) and all(wyniki_b["progi"].values())
    print("WYNIK A i B:", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
