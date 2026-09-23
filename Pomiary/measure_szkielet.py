import asyncio
import json
import random
import statistics
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Skrypt mierzy dwie ciche awarie szkieletu bota: zablokowana petle zdarzen
# (sekcja A) i zgubione pliki albumu przy /gotowe (sekcja B). Sekcja C to
# narzut techniczny uruchom(), tylko do raportu, bez progu.

KATALOG_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KATALOG_REPO / "src"))
sys.path.insert(0, str(KATALOG_REPO / "tests"))

from aiogram import Bot  # noqa: E402
from aiogram.fsm.storage.base import StorageKey  # noqa: E402

import bot  # noqa: E402
import kolejka  # noqa: E402
import magazyn  # noqa: E402
import pomocnicze  # noqa: E402
from konfiguracja import Konfiguracja  # noqa: E402

KATALOG_OUTPUTS = KATALOG_REPO / "outputs"
PLIK_WYNIKOW = KATALOG_OUTPUTS / "pomiar_szkielet.json"


def percentyl(wartosci: list[float], p: float) -> float:
    if not wartosci:
        return 0.0
    posortowane = sorted(wartosci)
    indeks = min(len(posortowane) - 1, int(round((p / 100) * (len(posortowane) - 1))))
    return posortowane[indeks]


def zapisz_wyniki(wyniki: dict) -> None:
    KATALOG_OUTPUTS.mkdir(parents=True, exist_ok=True)
    with open(PLIK_WYNIKOW, "w", encoding="utf-8") as plik:
        json.dump(wyniki, plik, ensure_ascii=False, indent=2)


async def sekcja_a() -> dict:
    print("Sekcja A: opoznienie petli zdarzen podczas dlugiego zadania w kolejce")
    zadanie = asyncio.create_task(
        kolejka.uruchom([sys.executable, "-c", "import time; time.sleep(3)"], limit_s=10)
    )
    opoznienia_ms = []
    poprzedni = time.perf_counter()
    while not zadanie.done():
        await asyncio.sleep(0.01)
        teraz = time.perf_counter()
        odstep_ms = (teraz - poprzedni) * 1000
        opoznienia_ms.append(max(0.0, odstep_ms - 10))
        poprzedni = teraz
    await zadanie

    wynik = {
        "p50_ms": statistics.median(opoznienia_ms),
        "p99_ms": percentyl(opoznienia_ms, 99),
        "max_ms": max(opoznienia_ms),
        "prog_max_ms": 50,
        "prog_ok": max(opoznienia_ms) < 50,
    }
    print(f"  p50 {wynik['p50_ms']:.2f} ms, p99 {wynik['p99_ms']:.2f} ms, max {wynik['max_ms']:.2f} ms")
    return wynik


class SesjaAlbumowa(pomocnicze.SesjaTestowa):
    async def stream_content(self, url, headers=None, timeout=30, chunk_size=65536, raise_for_status=True):
        await asyncio.sleep(random.uniform(0, 1))
        yield self.tresc_pliku


def klucz_stanu(bot_obiekt: Bot) -> StorageKey:
    return StorageKey(bot_id=bot_obiekt.id, chat_id=pomocnicze.CZAT_ID, user_id=pomocnicze.WLASCICIEL_ID)


async def jedna_proba_albumu(katalog_bazowy: Path) -> bool:
    konf = Konfiguracja(
        token=pomocnicze.TOKEN_TESTOWY,
        wlasciciel_id=pomocnicze.WLASCICIEL_ID,
        katalog_danych=katalog_bazowy,
        limit_pobierania_mb=20,
        limit_wysylki_mb=50,
    )
    kolejka_obiekt = kolejka.Kolejka()
    dyspozytor = bot.utworz_dispatcher(konf, kolejka_obiekt)
    bot_obiekt = Bot(token=pomocnicze.TOKEN_TESTOWY, session=SesjaAlbumowa())

    await dyspozytor.feed_update(bot_obiekt, pomocnicze.zbuduj_update(pomocnicze.zbuduj_wiadomosc(text="/nowy")))
    dane_stanu = await dyspozytor.storage.get_data(key=klucz_stanu(bot_obiekt))
    projekt_id = dane_stanu["projekt_id"]

    grupa = "album_pomiar"
    zadania = []
    for numer in range(10):
        wiadomosc = pomocnicze.zbuduj_wiadomosc(
            photo=pomocnicze.zdjecie(f"f_{numer}", f"u_{numer}", file_size=1000),
            media_group_id=grupa,
        )
        zadania.append(asyncio.create_task(dyspozytor.feed_update(bot_obiekt, pomocnicze.zbuduj_update(wiadomosc))))

    await dyspozytor.feed_update(bot_obiekt, pomocnicze.zbuduj_update(pomocnicze.zbuduj_wiadomosc(text="/gotowe")))
    await asyncio.gather(*zadania)

    katalog_projektu = konf.katalog_danych / "projekty" / projekt_id
    materialy = magazyn.lista_materialow(katalog_projektu)
    return len(materialy) == 10


async def sekcja_b(powtorzenia: int = 20) -> dict:
    print("Sekcja B: /gotowe zaraz po albumie 10 plikow, powtorzenia losowe opoznienia")
    udane = 0
    for numer in range(powtorzenia):
        with TemporaryDirectory() as katalog_tymczasowy:
            if await jedna_proba_albumu(Path(katalog_tymczasowy)):
                udane += 1
        print(f"  proba {numer + 1}/{powtorzenia}: {'10 z 10' if udane else 'w toku'}", end="\r")

    wynik = {
        "udane": udane,
        "powtorzenia": powtorzenia,
        "prog_ok": udane == powtorzenia,
    }
    print(f"\n  udane {udane} z {powtorzenia}")
    return wynik


async def sekcja_c(powtorzenia: int = 20) -> dict:
    print("Sekcja C: narzut uruchom() na procesie konczacym sie od razu")
    czasy_ms = []
    for _ in range(powtorzenia):
        start = time.perf_counter()
        await kolejka.uruchom([sys.executable, "-c", "pass"], limit_s=10)
        czasy_ms.append((time.perf_counter() - start) * 1000)

    wynik = {
        "mediana_ms": statistics.median(czasy_ms),
        "min_ms": min(czasy_ms),
        "max_ms": max(czasy_ms),
        "powtorzenia": powtorzenia,
    }
    print(f"  mediana {wynik['mediana_ms']:.2f} ms")
    return wynik


async def main() -> None:
    wyniki = {}

    wyniki["sekcja_a"] = await sekcja_a()
    zapisz_wyniki(wyniki)

    wyniki["sekcja_b"] = await sekcja_b()
    zapisz_wyniki(wyniki)

    wyniki["sekcja_c"] = await sekcja_c()
    zapisz_wyniki(wyniki)

    print(f"Wyniki zapisane w {PLIK_WYNIKOW}")
    print(f"Prog A (max < 50ms): {'OK' if wyniki['sekcja_a']['prog_ok'] else 'BLAD'}")
    print(f"Prog B (20 z 20): {'OK' if wyniki['sekcja_b']['prog_ok'] else 'BLAD'}")


if __name__ == "__main__":
    asyncio.run(main())
