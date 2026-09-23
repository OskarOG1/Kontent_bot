import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pytest
import soundfile

import analyze
from generuj import klik, melodia, wideo_z_cieciami


def ffprobe_json(sciezka, *argumenty) -> dict:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-of", "json", *argumenty, str(sciezka)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )
    return json.loads(wynik.stdout)


def liczba_klatek(sciezka) -> int:
    dane = ffprobe_json(sciezka, "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames")
    return int(dane["streams"][0]["nb_read_frames"])


def strumienie_audio(sciezka) -> list:
    return ffprobe_json(sciezka, "-select_streams", "a", "-show_entries", "stream=codec_name")["streams"]


@pytest.mark.parametrize("fps", [30, 25])
def test_generator_liczba_klatek(tmp_path, fps):
    sciezka = tmp_path / "w.mp4"
    wideo_z_cieciami(sciezka, [0.0, 0.5, 1.2], 2.0, fps=fps)
    assert liczba_klatek(sciezka) == round(2.0 * fps)


def test_generator_audio_tylko_z_bpm(tmp_path):
    z_dzwiekiem = tmp_path / "z.mp4"
    bez_dzwieku = tmp_path / "bez.mp4"
    wideo_z_cieciami(z_dzwiekiem, [0.0, 1.0], 2.0, bpm=120)
    wideo_z_cieciami(bez_dzwieku, [0.0, 1.0], 2.0)
    assert len(strumienie_audio(z_dzwiekiem)) == 1
    assert strumienie_audio(bez_dzwieku) == []


def test_klik_pierwsze_uderzenie_w_zadanym_czasie(tmp_path):
    sciezka = tmp_path / "klik.wav"
    czasy = klik(sciezka, 120, 3.0, pierwsze_uderzenie_s=0.5)
    sygnal, sr = soundfile.read(str(sciezka))
    pierwsza_probka = int(np.argmax(np.abs(sygnal) > 0.01))
    assert abs(pierwsza_probka / sr - 0.5) < 0.001
    assert czasy[:3] == pytest.approx([0.5, 1.0, 1.5])


def zakoduj_do_mp3(wav, mp3):
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)],
        check=True,
    )


def mediana_bledu(uderzenia, klikniecia) -> float:
    klikniecia = np.array(klikniecia)
    bledy = [float(np.min(np.abs(klikniecia - t))) for t in uderzenia]
    return float(np.median(bledy))


def blad_tempa_z_oktawa(tempo, prawdziwe) -> float:
    return min(abs(tempo * m - prawdziwe) / prawdziwe for m in (0.5, 1.0, 2.0))


def test_ciecia_szybkie_ujecia_po_4_i_6_klatek(tmp_path):
    klatki = [4, 10, 14, 20, 24, 30, 34]
    sciezka = tmp_path / "szybkie.mp4"
    wideo_z_cieciami(sciezka, [k / 30 for k in klatki], 40 / 30)
    znalezione = analyze.wykryj_ciecia(sciezka)
    oczekiwane = [0.0] + [k / 30 for k in klatki]
    assert len(znalezione) == len(oczekiwane)
    for wykryte, wzorcowe in zip(znalezione, oczekiwane):
        assert abs(wykryte - wzorcowe) <= 1 / 30 + 1e-6


def test_biala_klatka_miedzy_ujeciami_nie_tworzy_ujecia(tmp_path):
    sciezka = tmp_path / "blysk.mp4"
    wideo_z_cieciami(sciezka, [1.0], 2.0, blyski_s=[1.0])
    znalezione = analyze.wykryj_ciecia(sciezka)
    assert len(znalezione) == 2
    assert abs(znalezione[1] - 1.0) <= 1 / 30 + 1e-6


def test_ciecia_przy_fps_ulamkowym(tmp_path):
    fps = 30000 / 1001
    klatki = [30, 75, 100]
    sciezka = tmp_path / "ntsc.mp4"
    wideo_z_cieciami(sciezka, [k / fps for k in klatki], 130 / fps, fps=fps)
    znalezione = analyze.wykryj_ciecia(sciezka)
    oczekiwane = [0.0] + [k / fps for k in klatki]
    assert len(znalezione) == len(oczekiwane)
    for wykryte, wzorcowe in zip(znalezione, oczekiwane):
        assert abs(wykryte - wzorcowe) <= 1 / fps + 1e-6


def test_rytm_zwraca_typy_pythona(tmp_path):
    sciezka = tmp_path / "klik.wav"
    klik(sciezka, 120, 6.0)
    tempo, uderzenia = analyze.analizuj_rytm(sciezka)
    assert type(tempo) is float
    assert uderzenia and all(type(t) is float for t in uderzenia)


def test_os_czasu_taka_sama_dla_mp3_i_mp4(tmp_path):
    wav = tmp_path / "klik.wav"
    klikniecia = klik(wav, 120, 8.0, pierwsze_uderzenie_s=0.5)
    mp3 = tmp_path / "klik.mp3"
    zakoduj_do_mp3(wav, mp3)
    mp4 = tmp_path / "klik.mp4"
    wideo_z_cieciami(mp4, [0.0], 8.0, bpm=120, pierwsze_uderzenie_s=0.5)
    for plik in (mp3, mp4):
        _, uderzenia = analyze.analizuj_rytm(plik)
        assert mediana_bledu(uderzenia, klikniecia) <= 0.015


@pytest.mark.parametrize("bpm", [90, 120, 150])
def test_tempo_i_uderzenia_dla_kliku(tmp_path, bpm):
    wav = tmp_path / "klik.wav"
    klikniecia = klik(wav, bpm, 10.0, pierwsze_uderzenie_s=0.3)
    tempo, uderzenia = analyze.analizuj_rytm(wav)
    assert blad_tempa_z_oktawa(tempo, bpm) <= 0.02
    trafione = sum(1 for k in klikniecia if min(abs(t - k) for t in uderzenia) <= 0.035)
    assert trafione / len(klikniecia) >= 0.9


def test_pozycja_i_czas_sa_odwracalne():
    uderzenia = [0.5, 1.0, 1.6, 2.0, 2.9]
    for t in [0.1, 0.5, 0.77, 1.9, 2.9, 3.4]:
        pozycja = analyze.pozycja_w_uderzeniach(t, uderzenia)
        assert abs(analyze.czas_z_pozycji(pozycja, uderzenia) - t) < 1e-6


def test_pozycja_ekstrapoluje_mediana_odstepu():
    uderzenia = [1.0, 2.0, 3.0, 5.0]
    assert analyze.pozycja_w_uderzeniach(0.0, uderzenia) == pytest.approx(-1.0)
    assert analyze.pozycja_w_uderzeniach(6.0, uderzenia) == pytest.approx(4.0)


def test_kwantyzuj_usuwa_duplikaty():
    assert analyze.kwantyzuj([1.0, 1.05, 2.0]) == [1.0, 2.0]


SKRYPT = Path(analyze.__file__)


def uruchom_cli(wejscie, wyjscie):
    return subprocess.run(
        [sys.executable, str(SKRYPT), str(wejscie), str(wyjscie)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )


def tylko_typy_wbudowane(wartosc) -> bool:
    if isinstance(wartosc, dict):
        return all(type(k) is str and tylko_typy_wbudowane(v) for k, v in wartosc.items())
    if isinstance(wartosc, list):
        return all(tylko_typy_wbudowane(v) for v in wartosc)
    return type(wartosc) in (int, float, str, bool, type(None))


def test_wzor_120_bpm_z_cieciem_na_kazde_uderzenie(tmp_path):
    sciezka = tmp_path / "wzor.mp4"
    ciecia = [0.5 * k for k in range(1, 16)]
    wideo_z_cieciami(sciezka, ciecia, 8.0, bpm=120, pierwsze_uderzenie_s=0.5)
    wzor = analyze.analizuj_wzor(sciezka, "abc")
    pozycje = wzor["ciecia_uderzenia"]
    assert len(pozycje) == 16
    assert [b - a for a, b in zip(pozycje, pozycje[1:])] == [1.0] * 15
    assert wzor["koniec_uderzenia"] == pytest.approx(pozycje[-1] + 1.0)
    assert abs(wzor["tempo_bpm"] - 120) <= 2.4
    assert wzor["zrodlo"]["ma_dzwiek"] is True
    assert wzor["ciecia_s"][0] == 0.0
    assert wzor["ciecia_s"] == sorted(set(wzor["ciecia_s"]))
    assert wzor["ciecia_s"][-1] < wzor["zrodlo"]["czas_s"]


def test_wideo_bez_dzwieku_ma_puste_pola_rytmu(tmp_path):
    wejscie = tmp_path / "wzory" / "20260921_153012" / "zrodlo.mp4"
    wejscie.parent.mkdir(parents=True)
    wideo_z_cieciami(wejscie, [1.0], 2.0)
    wyjscie = wejscie.parent / "wzor.json"
    wynik = uruchom_cli(wejscie, wyjscie)
    assert wynik.returncode == 0
    dane = json.loads(wyjscie.read_text(encoding="utf-8"))
    assert dane["id"] == "20260921_153012"
    assert dane["wersja"] == 2
    assert dane["tempo_bpm"] is None
    assert dane["uderzenia_s"] == []
    assert dane["energia_uderzen"] is None
    assert dane["ciecia_uderzenia"] is None
    assert dane["koniec_uderzenia"] is None
    assert dane["odcisk_dzwieku"] is None
    assert dane["zrodlo"] == {"czas_s": 2.0, "szerokosc": 270, "wysokosc": 480, "fps": 30.0, "ma_dzwiek": False}
    assert dane["kolorystyka"] is None and dane["tekst"] is None


def test_wzor_zawiera_tylko_typy_wbudowane(tmp_path):
    sciezka = tmp_path / "wzor.mp4"
    wideo_z_cieciami(sciezka, [1.0, 2.0], 4.0, bpm=120)
    wzor = analyze.analizuj_wzor(sciezka, "abc")
    assert tylko_typy_wbudowane(wzor)
    wyjscie = tmp_path / "wzor.json"
    analyze.zapisz_json(wzor, wyjscie)
    assert tylko_typy_wbudowane(json.loads(wyjscie.read_text(encoding="utf-8")))


def test_cli_na_pliku_tekstowym_konczy_sie_bledem(tmp_path):
    wejscie = tmp_path / "notatka.mp4"
    wejscie.write_text("to nie jest wideo", encoding="utf-8")
    wyjscie = tmp_path / "wzor.json"
    wynik = uruchom_cli(wejscie, wyjscie)
    assert wynik.returncode != 0
    assert len(wynik.stderr.strip().splitlines()) == 1
    assert not wyjscie.exists()


def test_cli_na_pliku_bez_wideo_konczy_sie_bledem(tmp_path):
    wav = tmp_path / "klik.wav"
    klik(wav, 120, 2.0)
    wynik = uruchom_cli(wav, tmp_path / "wzor.json")
    assert wynik.returncode != 0
    assert len(wynik.stderr.strip().splitlines()) == 1


def test_odcisk_dzwieku_ma_oczekiwany_ksztalt_i_typy(tmp_path):
    wav = tmp_path / "melodia.wav"
    melodia(wav, 120, 20.0, ziarno=1)
    dzwiek = analyze.analizuj_dzwiek(wav)
    odcisk = dzwiek["odcisk"]
    oczekiwane_chroma = 20 / 0.09288
    oczekiwane_obwiednia = 20 / 0.01161
    assert abs(len(odcisk["chroma"]) - oczekiwane_chroma) <= 2
    assert all(len(klatka) == 12 for klatka in odcisk["chroma"])
    assert abs(len(odcisk["obwiednia"]) - oczekiwane_obwiednia) <= 2
    assert all(type(wartosc) is float for klatka in odcisk["chroma"] for wartosc in klatka)
    assert all(type(wartosc) is float for wartosc in odcisk["obwiednia"])


def test_energia_uderzen_odzwierciedla_glosnosc(tmp_path):
    wav = tmp_path / "melodia.wav"
    melodia(wav, 120, 20.0, ziarno=1, glosnosc=[(0, 0.1), (10, 1.0)])
    dzwiek = analyze.analizuj_dzwiek(wav)
    uderzenia = dzwiek["uderzenia_s"]
    energia = dzwiek["energia_uderzen"]
    assert len(energia) == len(uderzenia) - 1
    przed = [e for u, e in zip(uderzenia, energia) if u < 10.0]
    po = [e for u, e in zip(uderzenia, energia) if u >= 10.0]
    assert przed and po
    assert (sum(po) / len(po)) >= 5 * (sum(przed) / len(przed))


def test_analizuj_dzwiek_bez_dzwieku_daje_none(tmp_path):
    sciezka = tmp_path / "bez_dzwieku.mp4"
    wideo_z_cieciami(sciezka, [1.0], 2.0)
    assert analyze.analizuj_dzwiek(sciezka) is None
    wzor = analyze.analizuj_wzor(sciezka, "abc")
    assert wzor["odcisk_dzwieku"] is None
    assert wzor["energia_uderzen"] is None


def test_analizuj_wzor_z_melodia_daje_wersje_2(tmp_path):
    sciezka = tmp_path / "wzor.mp4"
    wav = tmp_path / "melodia.wav"
    melodia(wav, 120, 8.0, ziarno=2)
    wideo_z_cieciami(sciezka, [1.0, 4.0], 8.0, dzwiek=wav)
    wzor = analyze.analizuj_wzor(sciezka, "abc")
    assert wzor["wersja"] == 2
    assert wzor["odcisk_dzwieku"] is not None
    assert wzor["energia_uderzen"] is not None


def test_wszystkie_przelicza_tylko_katalogi_ze_zrodlem(tmp_path):
    katalog_danych = tmp_path / "dane"
    wzor_a = katalog_danych / "wzory" / "aaa"
    wzor_b = katalog_danych / "wzory" / "bbb"
    wzor_a.mkdir(parents=True)
    wzor_b.mkdir(parents=True)
    wideo_z_cieciami(wzor_a / "zrodlo.mp4", [1.0], 2.0)
    stary = {"wersja": 1, "id": "bbb", "cos": "nietkniete"}
    (wzor_b / "wzor.json").write_text(json.dumps(stary), encoding="utf-8")

    wynik = subprocess.run(
        [sys.executable, str(SKRYPT), "--wszystkie", "--katalog-danych", str(katalog_danych)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    assert wynik.returncode == 0
    dane_a = json.loads((wzor_a / "wzor.json").read_text(encoding="utf-8"))
    assert dane_a["id"] == "aaa"
    assert dane_a["wersja"] == 2
    dane_b = json.loads((wzor_b / "wzor.json").read_text(encoding="utf-8"))
    assert dane_b == stary


def test_analizuj_rytm_nie_zmienia_globalnych_filtrow_warnings(tmp_path):
    wav = tmp_path / "klik.wav"
    klik(wav, 120, 4.0)
    przed = list(warnings.filters)
    analyze.analizuj_rytm(wav)
    assert list(warnings.filters) == przed
