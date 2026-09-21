import json
import os
import re
from datetime import datetime
from pathlib import Path

ROZSZERZENIA_ZDJECIE = {"jpg", "jpeg", "png", "webp", "heic", "heif"}
ROZSZERZENIA_KLIP = {"mp4", "mov", "m4v", "webm", "mkv"}


def teraz() -> datetime:
    return datetime.now()


def nowy_identyfikator(katalog_bazowy: Path) -> str:
    baza = teraz().strftime("%Y%m%d_%H%M%S")
    kandydat = baza
    licznik = 2
    while (katalog_bazowy / kandydat).exists():
        kandydat = f"{baza}_{licznik}"
        licznik += 1
    return kandydat


def nowy_projekt(katalog_danych: Path) -> Path:
    katalog_projektow = Path(katalog_danych) / "projekty"
    katalog_projektow.mkdir(parents=True, exist_ok=True)
    identyfikator = nowy_identyfikator(katalog_projektow)
    katalog_projektu = katalog_projektow / identyfikator
    (katalog_projektu / "materialy").mkdir(parents=True)
    dane = {
        "id": identyfikator,
        "utworzony": teraz().isoformat(timespec="seconds"),
        "stan": "zbieranie",
        "teksty": [],
        "wzor_id": None,
        "wynik": None,
        "blad": None,
    }
    zapisz_projekt(katalog_projektu, dane)
    return katalog_projektu


def nowy_wzor(katalog_danych: Path) -> Path:
    katalog_wzorow = Path(katalog_danych) / "wzory"
    katalog_wzorow.mkdir(parents=True, exist_ok=True)
    identyfikator = nowy_identyfikator(katalog_wzorow)
    katalog_wzoru = katalog_wzorow / identyfikator
    katalog_wzoru.mkdir(parents=True)
    return katalog_wzoru


def sciezka_materialu(katalog_projektu: Path, message_id: int, file_unique_id: str, rozszerzenie: str) -> Path:
    nazwa = f"{message_id:010d}_{file_unique_id}.{rozszerzenie}"
    return Path(katalog_projektu) / "materialy" / nazwa


def typ_pliku(nazwa: str | None, mime: str | None) -> str | None:
    rozszerzenie = Path(nazwa).suffix.lstrip(".").lower() if nazwa else ""
    if rozszerzenie:
        if rozszerzenie in ROZSZERZENIA_ZDJECIE:
            return "zdjecie"
        if rozszerzenie in ROZSZERZENIA_KLIP:
            return "klip"
        return None
    if mime:
        if mime.startswith("image/"):
            return "zdjecie"
        if mime.startswith("video/"):
            return "klip"
    return None


def lista_materialow(katalog_projektu: Path) -> list[dict]:
    katalog_materialow = Path(katalog_projektu) / "materialy"
    wpisy = []
    if not katalog_materialow.exists():
        return wpisy
    for plik in katalog_materialow.iterdir():
        if not plik.is_file() or plik.suffix == ".part":
            continue
        dopasowanie = re.match(r"^(\d{10})_", plik.name)
        if not dopasowanie:
            continue
        typ = typ_pliku(plik.name, None)
        if typ is None:
            continue
        wpisy.append({"plik": plik, "typ": typ, "message_id": int(dopasowanie.group(1))})
    wpisy.sort(key=lambda wpis: wpis["message_id"])
    return wpisy


def wczytaj_projekt(katalog_projektu: Path) -> dict:
    sciezka = Path(katalog_projektu) / "projekt.json"
    with open(sciezka, "r", encoding="utf-8") as plik:
        return json.load(plik)


def zapisz_projekt(katalog_projektu: Path, dane: dict) -> None:
    katalog_projektu = Path(katalog_projektu)
    katalog_projektu.mkdir(parents=True, exist_ok=True)
    sciezka = katalog_projektu / "projekt.json"
    sciezka_tymczasowa = katalog_projektu / "projekt.json.tmp"
    with open(sciezka_tymczasowa, "w", encoding="utf-8") as plik:
        json.dump(dane, plik, ensure_ascii=False, indent=2)
    os.replace(sciezka_tymczasowa, sciezka)
