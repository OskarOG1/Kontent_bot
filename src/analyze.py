import argparse
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

WERSJA_WZORU = 3
CZESTOTLIWOSC_ANALIZY = 22050
KROK_ROZKLADU = 128
KROK_DOKLADNY = 32
OKNO_DOKLADNE = 512
POSZUKIWANIE_S = 0.05
START_BPM = 150.0
KROK_CHROMA = 2048
KROK_OBWIEDNI = 256
PROG_DROPU = 0.1
OKNO_TEMPOGRAMU = 384
KAWALEK_TEMPOGRAMU = 4096


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


def tempogram_sredni(obwiednia: numpy.ndarray, sr: int) -> numpy.ndarray:
    import librosa

    zakladka = OKNO_TEMPOGRAMU // 2
    n = len(obwiednia)
    suma = numpy.zeros(OKNO_TEMPOGRAMU)
    liczba_kolumn = 0
    for start in range(0, n, KAWALEK_TEMPOGRAMU):
        koniec = min(start + KAWALEK_TEMPOGRAMU, n)
        lewy = max(0, start - zakladka)
        prawy = min(n, koniec + zakladka)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kawalek = librosa.feature.tempogram(
                onset_envelope=obwiednia[lewy:prawy], sr=sr,
                hop_length=KROK_ROZKLADU, win_length=OKNO_TEMPOGRAMU,
            )
        kawalek = kawalek[:, start - lewy:koniec - lewy]
        suma += kawalek.sum(axis=1)
        liczba_kolumn += kawalek.shape[1]
    return (suma / liczba_kolumn).reshape(OKNO_TEMPOGRAMU, 1)


def analizuj_dzwiek(sciezka) -> dict | None:
    import librosa

    sciezka = Path(sciezka)
    with tempfile.TemporaryDirectory() as katalog:
        wav = Path(katalog) / "dzwiek.wav"
        try:
            zdekoduj_do_wav(sciezka, wav)
        except BladAnalizy:
            return None
        if not wav.exists() or wav.stat().st_size < 1000:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sygnal, sr = librosa.load(str(wav), sr=CZESTOTLIWOSC_ANALIZY, mono=True)
    if len(sygnal) < sr:
        return None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obwiednia_rytmu = librosa.onset.onset_strength(y=sygnal, sr=sr, hop_length=KROK_ROZKLADU)
        tempo_wstepne = librosa.feature.tempo(
            tg=tempogram_sredni(obwiednia_rytmu, sr), sr=sr, hop_length=KROK_ROZKLADU, start_bpm=START_BPM,
        )
        tempo, pozycje_uderzen = librosa.beat.beat_track(
            onset_envelope=obwiednia_rytmu, sr=sr, hop_length=KROK_ROZKLADU, units="time",
            bpm=float(numpy.asarray(tempo_wstepne).reshape(-1)[0]), trim=False,
        )
        uderzenia_s = doprecyzuj_uderzenia(librosa, sygnal, sr, [float(t) for t in pozycje_uderzen])
        chroma = librosa.feature.chroma_stft(y=sygnal, sr=sr, hop_length=KROK_CHROMA)
        obwiednia_odcisku = librosa.onset.onset_strength(y=sygnal, sr=sr, hop_length=KROK_OBWIEDNI)

    if len(uderzenia_s) < 2:
        tempo_bpm = None
        uderzenia_s = []
        energia_uderzen = []
    else:
        tempo_bpm = round(float(numpy.asarray(tempo).reshape(-1)[0]), 1)
        energia_uderzen = [
            round(float(numpy.sqrt(numpy.mean(numpy.square(
                sygnal[int(round(a * sr)):int(round(b * sr))]
            )))), 4)
            for a, b in zip(uderzenia_s, uderzenia_s[1:])
        ]

    return {
        "czas_s": round(len(sygnal) / sr, 3),
        "tempo_bpm": tempo_bpm,
        "uderzenia_s": uderzenia_s,
        "energia_uderzen": energia_uderzen,
        "odcisk": {
            "krok_chroma_s": round(KROK_CHROMA / sr, 5),
            "chroma": [[round(float(wartosc), 4) for wartosc in klatka] for klatka in chroma.T],
            "krok_obwiedni_s": round(KROK_OBWIEDNI / sr, 5),
            "obwiednia": [round(float(wartosc), 4) for wartosc in obwiednia_odcisku],
        },
    }


def analizuj_rytm(sciezka) -> tuple[float | None, list[float]]:
    dzwiek = analizuj_dzwiek(sciezka)
    if dzwiek is None:
        return None, []
    return dzwiek["tempo_bpm"], dzwiek["uderzenia_s"]


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


def wykryj_drop(
    uderzenia_s: list[float],
    energia_uderzen: list[float] | None,
    ciecia_s: list[float],
    ciecia_uderzenia: list[float] | None,
    czas_s: float,
) -> dict | None:
    if not uderzenia_s or not energia_uderzen:
        return None
    if len(uderzenia_s) < 16:
        return None
    if len(ciecia_s) < 2:
        return None
    granica_czasu = czas_s / 2
    srednia_energii = sum(energia_uderzen) / len(energia_uderzen)
    najlepszy_i = None
    najlepszy_wynik = None
    for i in range(8, len(uderzenia_s)):
        if uderzenia_s[i] > granica_czasu:
            break
        przed = energia_uderzen[max(0, i - 8):i]
        po = energia_uderzen[i:i + 8]
        if len(przed) < 4 or len(po) < 4:
            continue
        wynik = sum(po) / len(po) - sum(przed) / len(przed)
        if najlepszy_wynik is None or wynik > najlepszy_wynik:
            najlepszy_wynik = wynik
            najlepszy_i = i
    if najlepszy_i is None or najlepszy_wynik < PROG_DROPU * srednia_energii:
        return None
    t = uderzenia_s[najlepszy_i]
    kandydaci = [(idx, c) for idx, c in enumerate(ciecia_s) if idx >= 1]
    if not kandydaci:
        return None
    najblizszy_idx, najblizszy_c = min(kandydaci, key=lambda kc: (abs(kc[1] - t), kc[0]))
    if abs(najblizszy_c - t) <= 1.0:
        drop_idx, drop_c = najblizszy_idx, najblizszy_c
    else:
        po_czasie = [(idx, c) for idx, c in kandydaci if c > t]
        if po_czasie:
            drop_idx, drop_c = min(po_czasie, key=lambda kc: kc[1])
        else:
            drop_idx, drop_c = najblizszy_idx, najblizszy_c
    koniec_haka = ciecia_uderzenia[drop_idx] if ciecia_uderzenia is not None else None
    return {
        "drop_s": drop_c,
        "drop_ujecie": drop_idx,
        "koniec_haka_uderzenia": koniec_haka,
    }


def analizuj_wzor(sciezka, wzor_id: str) -> dict:
    sciezka = Path(sciezka)
    zrodlo = metadane(sciezka)
    czas_s = zrodlo["czas_s"]
    ciecia = [c for c in wykryj_ciecia(sciezka) if c < czas_s]
    if not ciecia or ciecia[0] != 0.0:
        ciecia = [0.0] + [c for c in ciecia if c > 0.0]
    dzwiek = analizuj_dzwiek(sciezka) if zrodlo["ma_dzwiek"] else None
    if dzwiek is not None:
        tempo = dzwiek["tempo_bpm"]
        uderzenia = dzwiek["uderzenia_s"]
        energia_uderzen = dzwiek["energia_uderzen"] if len(uderzenia) >= 2 else None
        odcisk_dzwieku = dzwiek["odcisk"]
    else:
        tempo, uderzenia = None, []
        energia_uderzen = None
        odcisk_dzwieku = None
    if len(uderzenia) >= 2:
        ciecia_uderzenia = kwantyzuj([pozycja_w_uderzeniach(t, uderzenia) for t in ciecia])
        koniec_uderzenia = kwantyzuj([pozycja_w_uderzeniach(czas_s, uderzenia)])[0]
    else:
        tempo, uderzenia = None, []
        energia_uderzen = None
        ciecia_uderzenia = None
        koniec_uderzenia = None
    sekcje = wykryj_drop(uderzenia, energia_uderzen, ciecia, ciecia_uderzenia, czas_s)
    return {
        "wersja": WERSJA_WZORU,
        "id": wzor_id,
        "zrodlo": zrodlo,
        "ciecia_s": ciecia,
        "tempo_bpm": tempo,
        "uderzenia_s": uderzenia,
        "energia_uderzen": energia_uderzen,
        "ciecia_uderzenia": ciecia_uderzenia,
        "koniec_uderzenia": koniec_uderzenia,
        "odcisk_dzwieku": odcisk_dzwieku,
        "sekcje": sekcje,
        "kolorystyka": None,
        "tekst": None,
    }


def zapisz_json(dane: dict, cel: Path) -> None:
    cel = Path(cel)
    tymczasowy = cel.with_name(cel.name + ".tmp")
    with open(tymczasowy, "w", encoding="utf-8") as plik:
        json.dump(dane, plik, ensure_ascii=False, indent=2)
    os.replace(tymczasowy, cel)


def main_wszystkie(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="analyze.py --wszystkie")
    parser.add_argument("--katalog-danych", default="dane")
    ns = parser.parse_args(argv)
    katalog_wzorow = Path(ns.katalog_danych) / "wzory"
    przeliczone = pominiete = bledy = 0
    if katalog_wzorow.is_dir():
        for katalog in sorted(katalog_wzorow.iterdir()):
            if not katalog.is_dir():
                continue
            zrodla = sorted(katalog.glob("zrodlo.*"))
            if not zrodla:
                print(f"Pomijam {katalog.name}: brak zrodlo.*")
                pominiete += 1
                continue
            try:
                dane = analizuj_wzor(zrodla[0], katalog.name)
                zapisz_json(dane, katalog / "wzor.json")
                przeliczone += 1
            except Exception as blad:
                opis = str(blad).splitlines()[0] if str(blad) else type(blad).__name__
                print(f"Blad przy {katalog.name}: {opis}", file=sys.stderr)
                bledy += 1
    print(f"Przeliczone: {przeliczone}, pominiete: {pominiete}, bledy: {bledy}")
    return 0 if bledy == 0 else 1


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--wszystkie":
        return main_wszystkie(argv[2:])
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
