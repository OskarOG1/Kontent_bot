import json
import random
import shutil
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 4 (muzyka).
# Sekcja A (syntetyczna): 10 melodii 60 s (ziarna 1 do 10), z kazdej 3 fragmenty (10, 20, 30 s)
#   z losowym przesunieciem (stale ziarno pomiaru). Rozpoznanie liczone bezposrednio przez
#   music.dopasuj_odcisk (nie przez wybierz_utwor: tryb dzwiek_wzoru jest dzis wylaczony,
#   patrz ROZWOJ.md zadanie 4.2), plus blad tempa klikow od 60 do 180 BPM co 10.
# Sekcja B (prawdziwe pliki, gdy sa dane/muzyka/ i dane/probki/wzory/): czas indeksowania,
#   tabela utworow, macierz zgodnosci (diagnostyczna, nieuzywana w wyborze), wybor
#   wybierz_utwor dla kazdego wzoru (oczekiwany tryb "tempo", bo dzwiek_wzoru wylaczony).
# Sekcja C: dwa przebiegi wybierz_utwor dla kazdego wzoru daja to samo.
# Sekcja D: render bez --utwor (1080x1920) i arkusz porownawczy dla kazdego wzoru.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

import soundfile as sf  # noqa: E402

import analyze  # noqa: E402
import arkusz  # noqa: E402
import generuj  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_muzyka.json"

PROG_PRZESUNIECIA_MS = 15.0
PROG_BLEDU_TEMPA_PROCENT = 2.0
ZIARNO_POMIARU = 20260923

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane: dict) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def sekcja_a() -> dict:
    rng = random.Random(ZIARNO_POMIARU)
    with TemporaryDirectory() as katalog:
        katalog = Path(katalog)
        biblioteka = katalog / "muzyka"
        biblioteka.mkdir()
        for ziarno in range(1, 11):
            generuj.melodia(biblioteka / f"m{ziarno:02d}.wav", 120, 60.0, ziarno=ziarno)
        indeks, _ = music.indeksuj(biblioteka)

        prob = 0
        bledy_rozpoznania = 0
        bledy_przesuniecia_ms = []
        najnizsza_pasujaca = None
        najwyzsza_niepasujaca = None

        for ziarno in range(1, 11):
            plik_zrodlowy = biblioteka / f"m{ziarno:02d}.wav"
            sygnal, sr = sf.read(str(plik_zrodlowy))
            for dlugosc_s in (10.0, 20.0, 30.0):
                prob += 1
                margines = 60.0 - dlugosc_s
                start_s = rng.uniform(0.0, margines)
                poczatek = int(round(start_s * sr))
                koniec = int(round((start_s + dlugosc_s) * sr))
                fragment = katalog / "fragment.wav"
                sf.write(str(fragment), sygnal[poczatek:koniec], sr, subtype="PCM_16")
                dzwiek = analyze.analizuj_dzwiek(fragment)

                najlepszy_plik = None
                najlepsza_zgodnosc = None
                najlepsze_przesuniecie = None
                for wpis in indeks["utwory"]:
                    dopasowanie = music.dopasuj_odcisk(dzwiek["odcisk"], wpis["odcisk"])
                    if dopasowanie is None:
                        continue
                    zgodnosc, przesuniecie = dopasowanie
                    if wpis["plik"] == plik_zrodlowy.name:
                        if najnizsza_pasujaca is None or zgodnosc < najnizsza_pasujaca:
                            najnizsza_pasujaca = zgodnosc
                    else:
                        if najwyzsza_niepasujaca is None or zgodnosc > najwyzsza_niepasujaca:
                            najwyzsza_niepasujaca = zgodnosc
                    if najlepsza_zgodnosc is None or zgodnosc > najlepsza_zgodnosc:
                        najlepsza_zgodnosc = zgodnosc
                        najlepszy_plik = wpis["plik"]
                        najlepsze_przesuniecie = przesuniecie

                if najlepszy_plik != plik_zrodlowy.name:
                    bledy_rozpoznania += 1
                else:
                    bledy_przesuniecia_ms.append(abs(najlepsze_przesuniecie - start_s) * 1000)

        bledy_tempa_procent = []
        for bpm_klik in range(60, 181, 10):
            wav = katalog / "klik_tempo.wav"
            generuj.klik(wav, bpm_klik, 10.0)
            dzwiek = analyze.analizuj_dzwiek(wav)
            tempo = dzwiek["tempo_bpm"]
            blad = min(abs(tempo * m - bpm_klik) for m in (0.5, 1.0, 2.0)) / bpm_klik
            bledy_tempa_procent.append(blad * 100)

    blad_przesuniecia_maks = round(max(bledy_przesuniecia_ms), 2) if bledy_przesuniecia_ms else None
    blad_przesuniecia_mediana = round(statistics.median(bledy_przesuniecia_ms), 2) if bledy_przesuniecia_ms else None
    blad_tempa_maks = round(max(bledy_tempa_procent), 3)

    wyniki = {
        "prob": prob,
        "bledy_rozpoznania": bledy_rozpoznania,
        "blad_przesuniecia_maks_ms": blad_przesuniecia_maks,
        "blad_przesuniecia_mediana_ms": blad_przesuniecia_mediana,
        "najnizsza_zgodnosc_pasujacej": najnizsza_pasujaca,
        "najwyzsza_zgodnosc_niepasujacej": najwyzsza_niepasujaca,
        "blad_tempa_maks_procent": blad_tempa_maks,
    }
    wyniki["progi"] = {
        "zero_bledow_rozpoznania": bledy_rozpoznania == 0,
        "przesuniecie_do_15ms": blad_przesuniecia_maks is not None and blad_przesuniecia_maks <= PROG_PRZESUNIECIA_MS,
        "blad_tempa_do_2_procent": blad_tempa_maks <= PROG_BLEDU_TEMPA_PROCENT,
    }
    print(f"A: {wyniki['progi']}, bledy rozpoznania {bledy_rozpoznania}/{prob}, przesuniecie maks {blad_przesuniecia_maks} ms")
    return wyniki


ROZSZERZENIA_WZOROW = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}


def znajdz_biblioteke_i_wzory():
    katalog_muzyki = KATALOG_REPO / "dane" / "muzyka"
    katalog_wzorow = KATALOG_REPO / "dane" / "probki" / "wzory"
    if not katalog_muzyki.is_dir() or not music.pliki_muzyki(katalog_muzyki):
        return None, []
    pliki_wzorow = sorted(p for p in katalog_wzorow.glob("*") if p.suffix.lower() in ROZSZERZENIA_WZOROW) if katalog_wzorow.is_dir() else []
    if not pliki_wzorow:
        return None, []
    return katalog_muzyki, pliki_wzorow


def wczytaj_lub_przeanalizuj_wzor(sciezka: Path) -> dict:
    nazwa = sciezka.stem
    cel = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
    if cel.is_file():
        dane = json.loads(cel.read_text(encoding="utf-8"))
        if dane.get("wersja") == analyze.WERSJA_WZORU:
            print(f"{nazwa}: wzor z cache ({cel.name})")
            return dane
    start = time.monotonic()
    dane = analyze.analizuj_wzor(sciezka, nazwa)
    czas = time.monotonic() - start
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    cel.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{nazwa}: analiza wzoru w {czas:.1f} s")
    return dane


def sekcja_b(katalog_muzyki, pliki_wzorow) -> dict:
    if katalog_muzyki is None:
        print("B pominieta: brak dane/muzyka lub dane/probki/wzory")
        return {"pominieta": True, "powod": "brak dane/muzyka lub dane/probki/wzory"}

    start = time.monotonic()
    indeks, przeanalizowane = music.indeksuj(katalog_muzyki)
    czas_indeksowania_s = round(time.monotonic() - start, 2)

    tabela_utworow = [
        {"plik": w["plik"], "czas_s": w["czas_s"], "tempo_bpm": w["tempo_bpm"], "liczba_uderzen": len(w["uderzenia_s"] or [])}
        for w in indeks["utwory"]
    ]

    wzory = []
    macierz = {}
    for sciezka in pliki_wzorow:
        nazwa = sciezka.stem
        wzor = wczytaj_lub_przeanalizuj_wzor(sciezka)
        odcisk_wzoru = wzor.get("odcisk_dzwieku")
        wiersz = {}
        if odcisk_wzoru is not None:
            for wpis in indeks["utwory"]:
                if wpis.get("odcisk") is None:
                    wiersz[wpis["plik"]] = None
                    continue
                dopasowanie = music.dopasuj_odcisk(odcisk_wzoru, wpis["odcisk"])
                wiersz[wpis["plik"]] = dopasowanie[0] if dopasowanie else None
        macierz[nazwa] = wiersz

        try:
            wybor = music.wybierz_utwor(wzor, indeks)
            wpis_wyboru = {
                "wzor": nazwa, "tryb": wybor["tryb"], "plik": wybor["plik"],
                "przesuniecie_s": wybor["przesuniecie_s"], "tempo_bpm": wybor["tempo_bpm"],
                "mnoznik": wybor["mnoznik"],
            }
        except ValueError as blad:
            wpis_wyboru = {"wzor": nazwa, "blad": str(blad)}
        wzory.append(wpis_wyboru)
        print(f"B {nazwa}: {wpis_wyboru}")

    wyniki = {
        "czas_indeksowania_s": czas_indeksowania_s,
        "przeanalizowane_przy_indeksowaniu": przeanalizowane,
        "utwory": tabela_utworow,
        "macierz_zgodnosci": macierz,
        "wybor": wzory,
    }
    wyniki["progi"] = {
        "wszystkie_wzory_dostaly_wybor": all("blad" not in w for w in wzory),
        "tryb_tempo_bo_dzwiek_wzoru_wylaczony": all(w.get("tryb") == "tempo" for w in wzory if "blad" not in w),
    }
    print(f"B: {wyniki['progi']}")
    return wyniki


def sekcja_c(katalog_muzyki, pliki_wzorow) -> dict:
    if katalog_muzyki is None:
        print("C pominieta: brak dane/muzyka lub dane/probki/wzory")
        return {"pominieta": True, "powod": "brak dane/muzyka lub dane/probki/wzory"}

    indeks, _ = music.indeksuj(katalog_muzyki)
    identyczne = True
    for sciezka in pliki_wzorow:
        wzor = wczytaj_lub_przeanalizuj_wzor(sciezka)
        try:
            w1 = music.wybierz_utwor(wzor, indeks)
            w2 = music.wybierz_utwor(wzor, indeks)
        except ValueError:
            continue
        if w1 != w2:
            identyczne = False

    wyniki = {"progi": {"identyczne": identyczne}}
    print(f"C: {wyniki['progi']}")
    return wyniki


def zbuduj_materialy_domyslne(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    for i in range(8):
        sciezka = katalog_materialow / f"{i + 1:010d}_m.jpg"
        generuj.zdjecie_testowe(sciezka, rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i))


def znajdz_katalog_materialow() -> Path | None:
    probki = KATALOG_REPO / "dane" / "probki" / "materialy"
    if probki.is_dir() and any(probki.iterdir()):
        return probki
    return None


def sekcja_d(katalog_muzyki, pliki_wzorow) -> dict:
    if katalog_muzyki is None:
        print("D pominieta: brak dane/muzyka lub dane/probki/wzory")
        return {"pominieta": True, "powod": "brak dane/muzyka lub dane/probki/wzory"}

    wpisy = []
    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        katalog_materialow_realny = znajdz_katalog_materialow()
        katalog_projektu = katalog_tymczasowy / "projekt"
        if katalog_materialow_realny is not None:
            (katalog_projektu / "materialy").mkdir(parents=True)
            for plik in katalog_materialow_realny.iterdir():
                if plik.is_file():
                    shutil.copy(plik, katalog_projektu / "materialy" / plik.name)
        else:
            zbuduj_materialy_domyslne(katalog_projektu / "materialy")

        for sciezka in pliki_wzorow:
            nazwa = sciezka.stem
            wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
            wyjscie = KATALOG_OUTPUTS / f"porownanie_zrodlo_muzyka_{nazwa}.mp4"
            try:
                render.renderuj(
                    wzor_json, katalog_projektu, None, wyjscie,
                    szerokosc=1080, wysokosc=1920, fps=30, limit_mb=200, muzyka=katalog_muzyki,
                )
            except Exception as blad:
                wpisy.append({"wzor": nazwa, "blad": str(blad)})
                print(f"D {nazwa}: BLAD {blad}")
                continue
            cel_arkusza = KATALOG_OUTPUTS / f"porownanie_muzyka_{nazwa}.png"
            arkusz.arkusz_porownawczy(sciezka, wyjscie, cel_arkusza)
            wpisy.append({"wzor": nazwa, "arkusz": cel_arkusza.name})
            print(f"D {nazwa}: arkusz {cel_arkusza.name}")

    wyniki = {"wzory": wpisy}
    wyniki["progi"] = {"arkusze_powstaly": bool(wpisy) and all("arkusz" in w for w in wpisy)}
    print(f"D: {wyniki['progi']}")
    return wyniki


def main() -> int:
    wyniki_a = sekcja_a()
    zapisz_sekcje("A", wyniki_a)

    katalog_muzyki, pliki_wzorow = znajdz_biblioteke_i_wzory()

    wyniki_b = sekcja_b(katalog_muzyki, pliki_wzorow)
    zapisz_sekcje("B", wyniki_b)

    wyniki_c = sekcja_c(katalog_muzyki, pliki_wzorow)
    zapisz_sekcje("C", wyniki_c)

    wyniki_d = sekcja_d(katalog_muzyki, pliki_wzorow)
    zapisz_sekcje("D", wyniki_d)

    zaliczone = all(wyniki_a["progi"].values())
    if not wyniki_b.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_b["progi"].values())
    if not wyniki_c.get("pominieta"):
        zaliczone = zaliczone and all(wyniki_c["progi"].values())
    print("WYNIK A (i B, C gdy dostepne):", "ZALICZONE" if zaliczone else "NIEZALICZONE")
    return 0 if zaliczone else 1


if __name__ == "__main__":
    sys.exit(main())
