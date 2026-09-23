import os
import time

import pytest
import soundfile

import analyze
import music
from generuj import klik, melodia, wideo_z_cieciami


def wzor_prosty(tempo_bpm, c0=0.0, koniec=4.0, energia_uderzen=None):
    return {
        "tempo_bpm": tempo_bpm,
        "ciecia_uderzenia": [c0],
        "koniec_uderzenia": koniec,
        "energia_uderzen": energia_uderzen,
        "odcisk_dzwieku": None,
        "zrodlo": {"czas_s": koniec},
    }


def zbuduj_wzor_z_dzwieku(sciezka, czas_s, ukryj_odcisk=False):
    dzwiek = analyze.analizuj_dzwiek(sciezka)
    uderzenia = dzwiek["uderzenia_s"]
    ciecia_uderzenia = analyze.kwantyzuj([analyze.pozycja_w_uderzeniach(0.0, uderzenia)])
    koniec_uderzenia = analyze.kwantyzuj([analyze.pozycja_w_uderzeniach(czas_s, uderzenia)])[0]
    return {
        "tempo_bpm": dzwiek["tempo_bpm"],
        "uderzenia_s": uderzenia,
        "energia_uderzen": dzwiek["energia_uderzen"],
        "ciecia_uderzenia": ciecia_uderzenia,
        "koniec_uderzenia": koniec_uderzenia,
        "odcisk_dzwieku": None if ukryj_odcisk else dzwiek["odcisk"],
        "zrodlo": {"czas_s": czas_s},
    }


def tylko_typy_wbudowane(wartosc) -> bool:
    if isinstance(wartosc, dict):
        return all(type(k) is str and tylko_typy_wbudowane(v) for k, v in wartosc.items())
    if isinstance(wartosc, list):
        return all(tylko_typy_wbudowane(v) for v in wartosc)
    return type(wartosc) in (int, float, str, bool, type(None))


def test_dopasuj_odcisk_rozpoznaje_fragment_wlasnego_utworu(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    melodia(katalog / "a.wav", 120, 20.0, ziarno=1)
    melodia(katalog / "b.wav", 120, 20.0, ziarno=2)
    indeks, _ = music.indeksuj(katalog)

    sygnal, sr = soundfile.read(str(katalog / "a.wav"))
    poczatek = int(round(7.3 * sr))
    koniec = int(round((7.3 + 6.0) * sr))
    fragment = tmp_path / "fragment.wav"
    soundfile.write(str(fragment), sygnal[poczatek:koniec], sr, subtype="PCM_16")
    dzwiek_fragmentu = analyze.analizuj_dzwiek(fragment)

    odcisk_a = [w for w in indeks["utwory"] if w["plik"] == "a.wav"][0]["odcisk"]
    dopasowanie_a = music.dopasuj_odcisk(dzwiek_fragmentu["odcisk"], odcisk_a)
    assert abs(dopasowanie_a[1] - 7.3) < 0.015
    assert dopasowanie_a[0] >= 0.8

    odcisk_b = [w for w in indeks["utwory"] if w["plik"] == "b.wav"][0]["odcisk"]
    dopasowanie_b = music.dopasuj_odcisk(dzwiek_fragmentu["odcisk"], odcisk_b)
    assert dopasowanie_b[0] < music.PROG_ZGODNOSCI


def test_wybierz_utwor_pomija_tryb_dzwiek_wzoru(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    melodia(katalog / "a.wav", 120, 20.0, ziarno=1)
    indeks, _ = music.indeksuj(katalog)

    sygnal, sr = soundfile.read(str(katalog / "a.wav"))
    poczatek = int(round(7.3 * sr))
    koniec = int(round((7.3 + 6.0) * sr))
    fragment = tmp_path / "fragment.wav"
    soundfile.write(str(fragment), sygnal[poczatek:koniec], sr, subtype="PCM_16")
    wzor = zbuduj_wzor_z_dzwieku(fragment, 6.0, ukryj_odcisk=False)
    assert wzor["odcisk_dzwieku"] is not None

    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["tryb"] != "dzwiek_wzoru"


def test_fragment_spoza_biblioteki_przechodzi_do_trybu_tempo(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    melodia(katalog / "a.wav", 120, 20.0, ziarno=1)
    melodia(katalog / "b.wav", 120, 20.0, ziarno=2)
    indeks, _ = music.indeksuj(katalog)

    wideo = tmp_path / "wzor.mp4"
    wav_c = tmp_path / "c.wav"
    melodia(wav_c, 120, 20.0, ziarno=3)
    wideo_z_cieciami(wideo, [1.0, 5.0], 20.0, dzwiek=wav_c)
    wzor = analyze.analizuj_wzor(wideo, "c")

    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["tryb"] == "tempo"


def test_dopasuj_odcisk_gdy_wzor_dluzszy_niz_utwor(tmp_path):
    dlugi = tmp_path / "dlugi.wav"
    krotki = tmp_path / "krotki.wav"
    klik(dlugi, 120, 20.0)
    klik(krotki, 120, 5.0)
    odcisk_dlugi = analyze.analizuj_dzwiek(dlugi)["odcisk"]
    odcisk_krotki = analyze.analizuj_dzwiek(krotki)["odcisk"]
    assert music.dopasuj_odcisk(odcisk_dlugi, odcisk_krotki) is None


def test_tempo_mnoznik_podwojony(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "wolny.wav", 70, 30.0)
    indeks, _ = music.indeksuj(katalog)
    tempo_utworu = indeks["utwory"][0]["tempo_bpm"]
    oryginalne_uderzenia = len(indeks["utwory"][0]["uderzenia_s"])
    wzor = wzor_prosty(2 * tempo_utworu, c0=0.0, koniec=4.0)

    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["tryb"] == "tempo"
    assert wybor["mnoznik"] == 2.0
    assert abs(len(wybor["uderzenia_s"]) - 2 * oryginalne_uderzenia) <= 1
    assert wybor["odleglosc_bpm"] == pytest.approx(0.0, abs=1e-6)


def test_tempo_mnoznik_polowiony(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "szybki.wav", 128, 20.0)
    indeks, _ = music.indeksuj(katalog)
    tempo_utworu = indeks["utwory"][0]["tempo_bpm"]
    wzor = wzor_prosty(tempo_utworu / 2, c0=0.0, koniec=4.0)

    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["tryb"] == "tempo"
    assert wybor["mnoznik"] == 0.5


def test_profil_energii_trafia_w_skok_utworu(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "utwor.wav", 120, 60.0, glosnosc=[(0, 0.1), (30, 1.0)])
    indeks, _ = music.indeksuj(katalog)

    wzor_wav = tmp_path / "wzor.wav"
    klik(wzor_wav, 120, 16.0, glosnosc=[(0, 0.1), (8, 1.0)])
    wzor = zbuduj_wzor_z_dzwieku(wzor_wav, 16.0, ukryj_odcisk=True)

    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["tryb"] == "tempo"
    c0 = wzor["ciecia_uderzenia"][0]
    czas_startu = analyze.czas_z_pozycji(wybor["start_uderzenie"] + c0, wybor["uderzenia_s"])
    odstep_uderzenia = 60.0 / wybor["tempo_bpm"]
    assert abs(czas_startu - 22.0) <= odstep_uderzenia


def test_remis_tempa_wygrywa_pierwszy_alfabetycznie():
    wzor = wzor_prosty(120.0, c0=0.0, koniec=4.0)
    uderzenia = [i * 0.5 for i in range(40)]
    energia = [0.5] * (len(uderzenia) - 1)
    indeks = {
        "wersja": 2,
        "utwory": [
            {"plik": "zzz.mp3", "tempo_bpm": 120.0, "uderzenia_s": uderzenia, "energia_uderzen": energia, "odcisk": None, "czas_s": 20.0},
            {"plik": "aaa.mp3", "tempo_bpm": 120.0, "uderzenia_s": uderzenia, "energia_uderzen": energia, "odcisk": None, "czas_s": 20.0},
        ],
    }
    wybor = music.wybierz_utwor(wzor, indeks)
    assert wybor["plik"] == "aaa.mp3"


def test_brak_kandydata_podaje_liczby_odrzuconych():
    wzor = wzor_prosty(120.0, c0=0.0, koniec=100.0)
    indeks = {
        "wersja": 2,
        "utwory": [
            {"plik": "cichy.mp3", "tempo_bpm": None, "uderzenia_s": [], "energia_uderzen": None, "odcisk": None, "czas_s": 200.0},
            {"plik": "krotki1.mp3", "tempo_bpm": 120.0, "uderzenia_s": [i * 0.5 for i in range(10)], "energia_uderzen": [0.5] * 9, "odcisk": None, "czas_s": 5.0},
            {"plik": "krotki2.mp3", "tempo_bpm": 120.0, "uderzenia_s": [i * 0.5 for i in range(10)], "energia_uderzen": [0.5] * 9, "odcisk": None, "czas_s": 5.0},
        ],
    }
    with pytest.raises(ValueError) as blad:
        music.wybierz_utwor(wzor, indeks)
    tekst = str(blad.value)
    assert "bez tempa 1" in tekst
    assert "za krótkie 2" in tekst


def test_indeksuj_ponowny_przebieg_bez_zmian(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "a.wav", 120, 5.0)
    indeks1, n1 = music.indeksuj(katalog)
    assert n1 == 1
    indeks2, n2 = music.indeksuj(katalog)
    assert n2 == 0
    assert indeks2 == indeks1


def test_indeksuj_zmiana_czasu_modyfikacji(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    sciezka = katalog / "a.wav"
    klik(sciezka, 120, 5.0)
    music.indeksuj(katalog)
    nowy_czas = time.time() + 5
    os.utime(sciezka, (nowy_czas, nowy_czas))
    _, n = music.indeksuj(katalog)
    assert n == 1


def test_indeksuj_usuwa_skasowane_pliki(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "a.wav", 120, 5.0)
    klik(katalog / "b.wav", 120, 5.0)
    music.indeksuj(katalog)
    (katalog / "a.wav").unlink()
    indeks, _ = music.indeksuj(katalog)
    nazwy = {w["plik"] for w in indeks["utwory"]}
    assert nazwy == {"b.wav"}


def test_indeksuj_pomija_mp4_bez_dzwieku(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "a.wav", 120, 5.0)
    wideo_z_cieciami(katalog / "b.mp4", [1.0], 3.0)
    indeks, _ = music.indeksuj(katalog)
    nazwy = {w["plik"] for w in indeks["utwory"]}
    assert nazwy == {"a.wav"}


def test_indeksuj_zawiera_tylko_typy_wbudowane(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "a.wav", 120, 5.0)
    indeks, _ = music.indeksuj(katalog)
    assert tylko_typy_wbudowane(indeks)


def test_wybierz_utwor_deterministyczny(tmp_path):
    katalog = tmp_path / "muzyka"
    katalog.mkdir()
    klik(katalog / "a.wav", 120, 20.0)
    klik(katalog / "b.wav", 130, 20.0)
    indeks, _ = music.indeksuj(katalog)
    wzor = wzor_prosty(125.0, c0=0.0, koniec=4.0)
    wybor1 = music.wybierz_utwor(wzor, indeks)
    wybor2 = music.wybierz_utwor(wzor, indeks)
    assert wybor1 == wybor2
