import json
import math
import os
import subprocess
import sys
import tempfile
import warnings
from fractions import Fraction
from pathlib import Path

import numpy

WERSJA_WZORU = 1
CZESTOTLIWOSC_ANALIZY = 22050
KROK_ROZKLADU = 128
KROK_DOKLADNY = 32
OKNO_DOKLADNE = 512
POSZUKIWANIE_S = 0.05


class BladAnalizy(Exception):
    pass


def uruchom_narzedzie(argumenty: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argumenty, stdin=subprocess.DEVNULL, capture_output=True)


def odczytaj_strumienie(sciezka: Path) -> dict:
    try:
        wynik = uruchom_narzedzie(
            ["ffprobe", "-v", "error", "-of", "json", "-show_streams", "-show_format", str(sciezka)]
        )
    except FileNotFoundError as blad:
        raise BladAnalizy("Brak programu ffprobe w systemie") from blad
    if wynik.returncode != 0:
        raise BladAnalizy("Nie udało się odczytać pliku jako wideo")
    return json.loads(wynik.stdout.decode("utf-8", errors="replace"))


def strumien_wideo(dane: dict) -> dict:
    for strumien in dane.get("streams", []):
        if strumien.get("codec_type") == "video" and strumien.get("disposition", {}).get("attached_pic") != 1:
            return strumien
    raise BladAnalizy("Plik nie ma strumienia wideo")


def ulamek_fps(strumien: dict) -> Fraction:
    for klucz in ("r_frame_rate", "avg_frame_rate"):
        tekst = strumien.get(klucz, "0/0")
        try:
            wartosc = Fraction(tekst)
        except (ValueError, ZeroDivisionError):
            continue
        if wartosc > 0:
            return wartosc
    raise BladAnalizy("Nie udało się ustalić liczby klatek na sekundę")


def obrocony_o_90(strumien: dict) -> bool:
    obrot = None
    for dane in strumien.get("side_data_list", []):
        if "rotation" in dane:
            obrot = dane["rotation"]
    if obrot is None:
        obrot = strumien.get("tags", {}).get("rotate")
    try:
        return int(float(obrot)) % 180 == 90
    except (TypeError, ValueError):
        return False


def metadane(sciezka) -> dict:
    sciezka = Path(sciezka)
    dane = odczytaj_strumienie(sciezka)
    strumien = strumien_wideo(dane)
    fps = ulamek_fps(strumien)
    szerokosc = int(strumien["width"])
    wysokosc = int(strumien["height"])
    if obrocony_o_90(strumien):
        szerokosc, wysokosc = wysokosc, szerokosc
    czas = dane.get("format", {}).get("duration") or strumien.get("duration")
    try:
        czas_s = float(czas)
    except (TypeError, ValueError) as blad:
        raise BladAnalizy("Nie udało się ustalić czasu trwania") from blad
    ma_dzwiek = any(s.get("codec_type") == "audio" for s in dane.get("streams", []))
    return {
        "czas_s": round(czas_s, 3),
        "szerokosc": szerokosc,
        "wysokosc": wysokosc,
        "fps": round(float(fps), 3),
        "ma_dzwiek": ma_dzwiek,
    }


def wykryj_ciecia(sciezka, min_klatek: int = 3) -> list[float]:
    from scenedetect import ContentDetector, detect

    sciezka = Path(sciezka)
    fps = ulamek_fps(strumien_wideo(odczytaj_strumienie(sciezka)))
    sceny = detect(str(sciezka), ContentDetector(min_scene_len=min_klatek))
    ciecia = []
    for poczatek, _ in sceny:
        klatka = poczatek.frame_num
        if klatka > 0:
            ciecia.append(round(float(klatka / fps), 3))
    return [0.0] + ciecia


def zdekoduj_do_wav(sciezka: Path, cel: Path) -> None:
    wynik = uruchom_narzedzie(
        [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(sciezka),
            "-vn", "-ac", "1", "-ar", str(CZESTOTLIWOSC_ANALIZY), "-c:a", "pcm_s16le", str(cel),
        ]
    )
    if wynik.returncode != 0:
        raise BladAnalizy("Nie udało się zdekodować dźwięku")


def analizuj_rytm(sciezka) -> tuple[float | None, list[float]]:
    warnings.filterwarnings("ignore")
    import librosa

    sciezka = Path(sciezka)
    with tempfile.TemporaryDirectory() as katalog:
        wav = Path(katalog) / "dzwiek.wav"
        try:
            zdekoduj_do_wav(sciezka, wav)
        except BladAnalizy:
            return None, []
        if not wav.exists() or wav.stat().st_size < 1000:
            return None, []
        sygnal, sr = librosa.load(str(wav), sr=CZESTOTLIWOSC_ANALIZY, mono=True)
    if len(sygnal) < sr:
        return None, []
    obwiednia = librosa.onset.onset_strength(y=sygnal, sr=sr, hop_length=KROK_ROZKLADU)
    tempo, uderzenia = librosa.beat.beat_track(
        onset_envelope=obwiednia, sr=sr, hop_length=KROK_ROZKLADU, units="time"
    )
    czasy = doprecyzuj_uderzenia(librosa, sygnal, sr, [float(t) for t in uderzenia])
    if len(czasy) < 2:
        return None, []
    tempo_bpm = round(float(numpy.asarray(tempo).reshape(-1)[0]), 1)
    return tempo_bpm, czasy


def doprecyzuj_uderzenia(librosa, sygnal, sr: int, uderzenia: list[float]) -> list[float]:
    obwiednia = librosa.onset.onset_strength(
        y=sygnal, sr=sr, hop_length=KROK_DOKLADNY, n_fft=OKNO_DOKLADNE, n_mels=40
    )
    polowa = int(POSZUKIWANIE_S * sr / KROK_DOKLADNY)
    wynik = []
    for t in uderzenia:
        srodek = int(round(t * sr / KROK_DOKLADNY))
        poczatek = max(0, srodek - polowa)
        koniec = min(len(obwiednia), srodek + polowa + 1)
        if koniec <= poczatek:
            continue
        indeks = poczatek + int(numpy.argmax(obwiednia[poczatek:koniec]))
        czas = round(float(indeks * KROK_DOKLADNY / sr), 3)
        if not wynik or czas > wynik[-1]:
            wynik.append(czas)
    return wynik


def mediana_odstepu(uderzenia: list[float]) -> float:
    odstepy = sorted(b - a for a, b in zip(uderzenia, uderzenia[1:]))
    srodek = len(odstepy) // 2
    if len(odstepy) % 2:
        return odstepy[srodek]
    return (odstepy[srodek - 1] + odstepy[srodek]) / 2


def pozycja_w_uderzeniach(t: float, uderzenia: list[float]) -> float:
    ostatni = len(uderzenia) - 1
    if t <= uderzenia[0]:
        return (t - uderzenia[0]) / mediana_odstepu(uderzenia)
    if t >= uderzenia[ostatni]:
        return ostatni + (t - uderzenia[ostatni]) / mediana_odstepu(uderzenia)
    lewy, prawy = 0, ostatni
    while prawy - lewy > 1:
        srodek = (lewy + prawy) // 2
        if uderzenia[srodek] <= t:
            lewy = srodek
        else:
            prawy = srodek
    return lewy + (t - uderzenia[lewy]) / (uderzenia[prawy] - uderzenia[lewy])


def czas_z_pozycji(p: float, uderzenia: list[float]) -> float:
    ostatni = len(uderzenia) - 1
    if p <= 0:
        return uderzenia[0] + p * mediana_odstepu(uderzenia)
    if p >= ostatni:
        return uderzenia[ostatni] + (p - ostatni) * mediana_odstepu(uderzenia)
    lewy = int(math.floor(p))
    return uderzenia[lewy] + (p - lewy) * (uderzenia[lewy + 1] - uderzenia[lewy])


def kwantyzuj(pozycje: list[float], krok: float = 0.25) -> list[float]:
    wynik = []
    widziane = set()
    for pozycja in pozycje:
        numer = int(math.floor(pozycja / krok + 0.5))
        if numer in widziane:
            continue
        widziane.add(numer)
        wynik.append(round(numer * krok, 6))
    return wynik


def analizuj_wzor(sciezka, wzor_id: str) -> dict:
    sciezka = Path(sciezka)
    zrodlo = metadane(sciezka)
    czas_s = zrodlo["czas_s"]
    ciecia = [c for c in wykryj_ciecia(sciezka) if c < czas_s]
    if not ciecia or ciecia[0] != 0.0:
        ciecia = [0.0] + [c for c in ciecia if c > 0.0]
    if zrodlo["ma_dzwiek"]:
        tempo, uderzenia = analizuj_rytm(sciezka)
    else:
        tempo, uderzenia = None, []
    if len(uderzenia) >= 2:
        ciecia_uderzenia = kwantyzuj([pozycja_w_uderzeniach(t, uderzenia) for t in ciecia])
        koniec_uderzenia = kwantyzuj([pozycja_w_uderzeniach(czas_s, uderzenia)])[0]
    else:
        tempo, uderzenia = None, []
        ciecia_uderzenia = None
        koniec_uderzenia = None
    return {
        "wersja": WERSJA_WZORU,
        "id": wzor_id,
        "zrodlo": zrodlo,
        "ciecia_s": ciecia,
        "tempo_bpm": tempo,
        "uderzenia_s": uderzenia,
        "ciecia_uderzenia": ciecia_uderzenia,
        "koniec_uderzenia": koniec_uderzenia,
        "kolorystyka": None,
        "tekst": None,
    }


def zapisz_json(dane: dict, cel: Path) -> None:
    cel = Path(cel)
    tymczasowy = cel.with_name(cel.name + ".tmp")
    with open(tymczasowy, "w", encoding="utf-8") as plik:
        json.dump(dane, plik, ensure_ascii=False, indent=2)
    os.replace(tymczasowy, cel)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Użycie: analyze.py <wejscie> <wyjscie.json>", file=sys.stderr)
        return 2
    wejscie = Path(argv[1])
    wyjscie = Path(argv[2])
    try:
        dane = analizuj_wzor(wejscie, wyjscie.resolve().parent.name)
        zapisz_json(dane, wyjscie)
    except BladAnalizy as blad:
        print(str(blad).splitlines()[0], file=sys.stderr)
        return 1
    except Exception as blad:
        opis = str(blad).splitlines()[0] if str(blad) else type(blad).__name__
        print(f"Analiza nie powiodła się: {opis}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
