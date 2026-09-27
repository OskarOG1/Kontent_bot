import json
import os
import shutil
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Pomiar czesci 11 (rezyser i krytyk AI), zadanie 11.4.
# Bez OPENROUTER_API_KEY w srodowisku caly pomiar konczy sie natychmiast, wynik
#   {"pominiety": "brak klucza"}, kod 0 (pomiar wydaje prawdziwe pieniadze, wiec
#   nigdy nie probuje wywolania bez klucza).
# Przed pierwszym wywolaniem modelu drukowany jest szacunek kosztu jednego edytu
#   z rezyser.koszt_usd na przewidywanych tokenach z planu czesci 11 (rezyser
#   ok. 15000 wejscia/6000 wyjscia, krytyk ok. 8000/3000).
# Sekcja A: na kazdym z 5 prawdziwych wzorow (dane/wzory/*.mp4) dwa montaze —
#   automatyczny (bez --ai) i z AI (--ai) — na tej samej bibliotece i muzyce.
#   Automat tez dostaje ocene krytyka (do porownania, mimo ze model ocenia
#   material, ktory sam nie wybieral). Zapisywane: liczba ujec, uzyte materialy,
#   liczba ostrzezen scenariusza, tokeny wejscia/wyjscia, koszt USD, czas zegara.
#   Progi: scenariusz poprawny (bez przejscia na automat, tzn. podsumowanie["ai"]
#   ma rezyser=true) na co najmniej 4 z 5 wzorow; koszt jednego edytu z AI ponizej
#   1 USD.
# Sekcja C: dla kazdego wzoru outputs/porownanie_rezyser_<wzor>_auto.png i
#   outputs/porownanie_rezyser_<wzor>_ai.png (Pomiary/arkusz.py, ta sama warstwa
#   co czesci 4 do 9), do tego probny edit outputs/rezyser_0923.mp4 (kopia
#   wyniku AI dla wzoru 0923, jesli byl w probce). Werdykt na arkuszach i probnym
#   edicie wydaje wlasciciel, ocena krytyka to tylko dodatek.
# Wyniki zapisywane do outputs/pomiar_rezyser.json po kazdym wzorze.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

from PIL import Image  # noqa: E402

import arkusz  # noqa: E402
import generuj  # noqa: E402
import music  # noqa: E402
import render  # noqa: E402
import rezyser  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_rezyser.json"
KATALOG_WZOROW = KATALOG_REPO / "dane" / "wzory"
KATALOG_MUZYKI = KATALOG_REPO / "dane" / "muzyka"

FPS = 30
LIMIT_RENDERU_S = 1800
WZOR_PROBNEGO_EDITU = "0923"
MODEL_AI = os.environ.get("MODEL_AI") or "anthropic/claude-opus-5.5"

WYNIKI_CALOSC: dict = {}


def zapisz_wyniki() -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(WYNIKI_CALOSC, plik, ensure_ascii=False, indent=2)


def zapisz_sekcje(nazwa: str, dane) -> None:
    WYNIKI_CALOSC[nazwa] = dane
    zapisz_wyniki()


def znajdz_wzory() -> list[Path]:
    if not KATALOG_WZOROW.is_dir():
        return []
    return sorted(p for p in KATALOG_WZOROW.glob("*.mp4"))


def ma_prawdziwa_alfa(sciezka: Path) -> bool:
    try:
        with Image.open(sciezka) as obraz:
            if obraz.mode != "RGBA":
                return False
            return obraz.getchannel("A").getextrema()[0] < 255
    except Exception:
        return False


def zbuduj_katalog_materialow(katalog_materialow: Path) -> None:
    katalog_materialow.mkdir(parents=True, exist_ok=True)
    katalog_zdjec = KATALOG_REPO / "dane" / "zdjęcia"
    katalog_nagran = KATALOG_REPO / "dane" / "nagrania"
    katalog_bez_tla = KATALOG_REPO / "dane" / "zdjęcia_bez_tła"

    zdjecia = sorted(p for p in katalog_zdjec.glob("*") if p.is_file())[:8] if katalog_zdjec.is_dir() else []
    nagrania = sorted(p for p in katalog_nagran.glob("*") if p.is_file())[:4] if katalog_nagran.is_dir() else []
    bez_tla = []
    if katalog_bez_tla.is_dir():
        bez_tla = [p for p in sorted(katalog_bez_tla.glob("*")) if p.is_file() and ma_prawdziwa_alfa(p)][:2]

    zrodla = zdjecia + nagrania + bez_tla
    if not zrodla:
        for i in range(8):
            generuj.zdjecie_testowe(
                katalog_materialow / f"{i + 1:010d}_m.jpg", rozmiar=(1200, 1600), kolor=generuj.kolor_ujecia(i),
            )
        return

    for i, plik in enumerate(zrodla):
        cel = katalog_materialow / f"{i + 1:010d}_m{plik.suffix.lower()}"
        try:
            os.link(plik, cel)
        except OSError:
            shutil.copy(plik, cel)


def zapisz_projekt_json(katalog_projektu: Path) -> None:
    dane = {"teksty": [], "slowa": "europe be like POLAND", "pionowo": "1993 supply made in poland"}
    (katalog_projektu / "projekt.json").write_text(json.dumps(dane, ensure_ascii=False), encoding="utf-8")


def znajdz_plansze() -> Path | None:
    katalog_plansz = KATALOG_REPO / "dane" / "plansze"
    if katalog_plansz.is_dir():
        znalezione = sorted(p for p in katalog_plansz.glob("domyslna.*") if p.is_file())
        if znalezione:
            return znalezione[0]
    katalog_promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if katalog_promocyjne.is_dir():
        for plik in sorted(katalog_promocyjne.iterdir()):
            if plik.suffix.lower() in (".jpg", ".jpeg", ".png") and not ma_prawdziwa_alfa(plik):
                return plik
    return None


def znajdz_znak() -> Path | None:
    katalog_promocyjne = KATALOG_REPO / "dane" / "promocyjne"
    if not katalog_promocyjne.is_dir():
        return None
    for plik in sorted(katalog_promocyjne.iterdir()):
        if plik.is_file() and "watermark" in plik.stem.lower():
            return plik
    return None


def znajdz_nakladke() -> Path | None:
    domyslna = KATALOG_REPO / "dane" / "nakladki" / "domyslna.mp4"
    return domyslna if domyslna.is_file() else None


def zrenderuj_wariant(wzor_json: Path, katalog_projektu: Path, wyjscie: Path, muzyka, nakladka, plansza, znak, ai: bool) -> tuple[dict, dict]:
    start = time.monotonic()
    podsumowanie = render.renderuj(
        wzor_json, katalog_projektu, None, wyjscie,
        szerokosc=1080, wysokosc=1920, fps=FPS, limit_mb=200, muzyka=muzyka,
        nakladka=nakladka, plansza=plansza, znak=znak,
        ai=ai, model_ai=MODEL_AI, prog_oceny_ai=7,
    )
    czasy = {"zegar_s": round(time.monotonic() - start, 2)}
    return podsumowanie, czasy


def sekcja_a_i_c() -> tuple[dict, dict]:
    pliki_wzorow = znajdz_wzory()
    if not pliki_wzorow:
        print("A/C pominiete: brak dane/wzory")
        return {"pominieta": True, "powod": "brak dane/wzory"}, {"pominieta": True, "powod": "brak dane/wzory"}
    if not KATALOG_MUZYKI.is_dir() or not any(KATALOG_MUZYKI.iterdir()):
        print("A/C pominiete: brak dane/muzyka")
        return {"pominieta": True, "powod": "brak dane/muzyka"}, {"pominieta": True, "powod": "brak dane/muzyka"}

    music.indeksuj(KATALOG_MUZYKI)

    nakladka = znajdz_nakladke()
    plansza = znajdz_plansze()
    znak = znajdz_znak()

    wpisy_a = []
    wpisy_c = []

    with TemporaryDirectory() as katalog_tymczasowy:
        katalog_tymczasowy = Path(katalog_tymczasowy)
        for wzor_mp4 in pliki_wzorow:
            nazwa = wzor_mp4.stem
            print(f"=== wzor {nazwa} ===")
            wzor_json = KATALOG_OUTPUTS / f"wzor_{nazwa}.json"
            if not wzor_json.is_file():
                print(f"{nazwa}: brak {wzor_json.name}, pomijam (analiza spoza tego pomiaru)")
                continue

            katalog_wzoru_zrodlo = katalog_tymczasowy / f"wzor_{nazwa}"
            katalog_wzoru_zrodlo.mkdir(parents=True, exist_ok=True)
            zrodlo_lokalne = katalog_wzoru_zrodlo / f"zrodlo{wzor_mp4.suffix}"
            if not zrodlo_lokalne.is_file():
                try:
                    os.link(wzor_mp4, zrodlo_lokalne)
                except OSError:
                    shutil.copy(wzor_mp4, zrodlo_lokalne)
            wzor_json_lokalny = katalog_wzoru_zrodlo / "wzor.json"
            shutil.copy(wzor_json, wzor_json_lokalny)

            wpis_wzoru = {"wzor": nazwa}
            try:
                for tryb, ai in (("auto", False), ("ai", True)):
                    katalog_projektu = katalog_tymczasowy / f"projekt_{nazwa}_{tryb}"
                    zbuduj_katalog_materialow(katalog_projektu / "materialy")
                    zapisz_projekt_json(katalog_projektu)
                    wyjscie = katalog_tymczasowy / f"wynik_{nazwa}_{tryb}.mp4"

                    podsumowanie, czasy = zrenderuj_wariant(
                        wzor_json_lokalny, katalog_projektu, wyjscie, KATALOG_MUZYKI, nakladka, plansza, znak, ai,
                    )
                    dane_ai = podsumowanie.get("ai") or {}
                    wpis_wzoru[tryb] = {
                        "liczba_ujec": podsumowanie["liczba_ujec"],
                        "materialy_uzyte": podsumowanie["materialy_uzyte"],
                        "ostrzezenia_scenariusza": len(dane_ai.get("ostrzezenia") or []),
                        "rezyser": dane_ai.get("rezyser"),
                        "ocena": dane_ai.get("ocena"),
                        "tokeny_wejscia": dane_ai.get("tokeny_wejscia"),
                        "tokeny_wyjscia": dane_ai.get("tokeny_wyjscia"),
                        "koszt_usd": dane_ai.get("koszt_usd"),
                        "powod_pominiecia": dane_ai.get("powod_pominiecia"),
                        "zegar_s": czasy["zegar_s"],
                    }

                    arkusz_cel = KATALOG_OUTPUTS / f"porownanie_rezyser_{nazwa}_{tryb}.png"
                    try:
                        arkusz.arkusz_porownawczy(zrodlo_lokalne, wyjscie, arkusz_cel)
                        wpis_wzoru.setdefault("arkusze", []).append(arkusz_cel.name)
                    except Exception as blad:
                        print(f"{nazwa} {tryb}: arkusz nie powstal: {blad}")

                    if ai and nazwa == WZOR_PROBNEGO_EDITU:
                        cel_probny = KATALOG_OUTPUTS / "rezyser_0923.mp4"
                        shutil.copy(wyjscie, cel_probny)
                        wpisy_c.append(cel_probny.name)
            except Exception as blad:
                wpis_wzoru["blad"] = str(blad)
                print(f"{nazwa}: blad {blad}")

            wpisy_a.append(wpis_wzoru)
            zapisz_sekcje("A", {"w_toku": True, "wzory": wpisy_a})

    return {"wzory": wpisy_a}, {"pliki": wpisy_c}


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Pomiar pominiety: brak OPENROUTER_API_KEY (pomiar wydaje prawdziwe pieniadze)")
        zapisz_sekcje("wynik", {"pominiety": "brak klucza"})
        return 0

    szacunek_rezysera = rezyser.koszt_usd(MODEL_AI, 15000, 6000)
    szacunek_krytyka = rezyser.koszt_usd(MODEL_AI, 8000, 3000)
    print(f"Szacunek kosztu: rezyser {szacunek_rezysera} USD, krytyk {szacunek_krytyka} USD za edit (jedna poprawka podwaja krytyka)")

    wyniki_a, wyniki_c = sekcja_a_i_c()
    zapisz_sekcje("A", wyniki_a)
    zapisz_sekcje("C", wyniki_c)

    if not wyniki_a.get("pominieta"):
        wzory = wyniki_a.get("wzory", [])
        poprawne = sum(1 for w in wzory if (w.get("ai") or {}).get("rezyser"))
        koszty = [w["ai"]["koszt_usd"] for w in wzory if w.get("ai", {}).get("koszt_usd") is not None]
        progi = {
            "scenariusz_poprawny_co_najmniej_4_z_5": poprawne >= 4,
            "koszt_edytu_ai_ponizej_1_usd": all(k < 1.0 for k in koszty) if koszty else None,
        }
        zapisz_sekcje("progi", progi)
        print(f"Progi: {progi}")

    print("Pomiar zakonczony.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
