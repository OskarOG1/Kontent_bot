import asyncio
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KATALOG_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(KATALOG_SRC))

import bot

KATALOG_OUTPUTS = Path(__file__).resolve().parent.parent / "outputs"
KAWALKI_B = {"64 KB": 64 * 1024, "1 MB": 1024 * 1024}
PROG_OPOZNIENIA_S = 0.05


def utworz_plik(sciezka: Path, rozmiar_b: int) -> None:
    bufor = os.urandom(1024 * 1024)
    with open(sciezka, "wb") as plik:
        zapisano = 0
        while zapisano < rozmiar_b:
            ile = min(len(bufor), rozmiar_b - zapisano)
            plik.write(bufor[:ile] if ile < len(bufor) else bufor)
            zapisano += ile


async def kopiuj_z_pomiarem(zrodlo: Path, cel: Path, rozmiar_kawalka: int) -> tuple[float, float]:
    maks_opoznienie = 0.0
    zakonczono = asyncio.Event()

    async def znacznik() -> None:
        nonlocal maks_opoznienie
        while not zakonczono.is_set():
            start = time.perf_counter()
            await asyncio.sleep(0.01)
            opoznienie = time.perf_counter() - start - 0.01
            if opoznienie > maks_opoznienie:
                maks_opoznienie = opoznienie

    zadanie_znacznika = asyncio.create_task(znacznik())
    start_kopii = time.perf_counter()
    await asyncio.to_thread(bot.kopiuj_plik, zrodlo, cel, rozmiar_kawalka)
    czas_kopii = time.perf_counter() - start_kopii
    zakonczono.set()
    await zadanie_znacznika
    return czas_kopii, maks_opoznienie


async def zmierz_rozmiar(nazwa: str, rozmiar_b: int, katalog: Path) -> dict:
    zrodlo = katalog / f"zrodlo_{nazwa.replace(' ', '_')}.bin"
    cel = katalog / f"cel_{nazwa.replace(' ', '_')}.bin"
    utworz_plik(zrodlo, rozmiar_b)

    kolejnosc = ["64 KB", "1 MB"] * 3
    wyniki = {"64 KB": [], "1 MB": []}
    for etykieta in kolejnosc:
        czas_kopii, opoznienie = await kopiuj_z_pomiarem(zrodlo, cel, KAWALKI_B[etykieta])
        wyniki[etykieta].append({"czas_s": czas_kopii, "opoznienie_s": opoznienie})
        cel.unlink(missing_ok=True)

    zrodlo.unlink(missing_ok=True)
    return wyniki


def podsumuj(wyniki: dict) -> dict:
    podsumowanie = {}
    for etykieta, przebiegi in wyniki.items():
        czasy = [p["czas_s"] for p in przebiegi]
        podsumowanie[etykieta] = {
            "sredni_czas_s": statistics.mean(czasy),
            "odchylenie_czasu_s": statistics.stdev(czasy) if len(czasy) > 1 else 0.0,
            "maks_opoznienie_s": max(p["opoznienie_s"] for p in przebiegi),
        }
    return podsumowanie


def wypisz_sekcje(nazwa: str, podsumowanie: dict) -> None:
    print(f"== {nazwa} ==")
    for etykieta, dane in podsumowanie.items():
        print(
            f"{etykieta}: sredni czas {dane['sredni_czas_s']:.3f} s "
            f"(odchylenie {dane['odchylenie_czasu_s']:.3f} s), "
            f"maks opoznienie petli {dane['maks_opoznienie_s'] * 1000:.1f} ms"
        )
    maks_opoznienie_sekcji = max(dane["maks_opoznienie_s"] for dane in podsumowanie.values())
    werdykt = "PASS" if maks_opoznienie_sekcji < PROG_OPOZNIENIA_S else "FAIL"
    print(f"prog opoznienia {PROG_OPOZNIENIA_S * 1000:.0f} ms: {werdykt}")

    roznica = abs(podsumowanie["1 MB"]["sredni_czas_s"] - podsumowanie["64 KB"]["sredni_czas_s"])
    rozrzut = podsumowanie["1 MB"]["odchylenie_czasu_s"] + podsumowanie["64 KB"]["odchylenie_czasu_s"]
    if roznica > rozrzut:
        szybszy = "1 MB" if podsumowanie["1 MB"]["sredni_czas_s"] < podsumowanie["64 KB"]["sredni_czas_s"] else "64 KB"
        print(f"roznica ({roznica:.3f} s) przekracza rozrzut powtorzen ({rozrzut:.3f} s): kawalek {szybszy} szybszy")
    else:
        print(f"roznica ({roznica:.3f} s) nie przekracza rozrzutu powtorzen ({rozrzut:.3f} s): bez zmiany")
    print()


def zapisz_wyniki(wszystkie_wyniki: dict) -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    sciezka = KATALOG_OUTPUTS / "measure_pobieranie.json"
    sciezka.write_text(json.dumps(wszystkie_wyniki, indent=2, ensure_ascii=False), encoding="utf-8")


async def main() -> None:
    wszystkie_wyniki = {}
    with tempfile.TemporaryDirectory(prefix="measure_pobieranie_") as katalog_tekst:
        katalog = Path(katalog_tekst)

        print("Sekcja A: pliki 100 MB")
        wyniki_a = await zmierz_rozmiar("100 MB", 100 * 1024 * 1024, katalog)
        podsumowanie_a = podsumuj(wyniki_a)
        wypisz_sekcje("Sekcja A: 100 MB", podsumowanie_a)
        wszystkie_wyniki["100_MB"] = {"przebiegi": wyniki_a, "podsumowanie": podsumowanie_a}
        zapisz_wyniki(wszystkie_wyniki)

        print("Sekcja B: pliki 1 GB")
        wyniki_b = await zmierz_rozmiar("1 GB", 1024 * 1024 * 1024, katalog)
        podsumowanie_b = podsumuj(wyniki_b)
        wypisz_sekcje("Sekcja B: 1 GB", podsumowanie_b)
        wszystkie_wyniki["1_GB"] = {"przebiegi": wyniki_b, "podsumowanie": podsumowanie_b}
        zapisz_wyniki(wszystkie_wyniki)


if __name__ == "__main__":
    asyncio.run(main())
