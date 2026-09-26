import json
import os
import re
from datetime import datetime
from pathlib import Path

ROZSZERZENIA_ZDJECIE = {"jpg", "jpeg", "png", "webp", "heic", "heif"}
ROZSZERZENIA_KLIP = {"mp4", "mov", "m4v", "webm", "mkv", "gif"}
ROZSZERZENIA_NAKLADEK = {"webm", "mov", "mp4", "png", "gif"}


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


def najnowszy_wzor(katalog_danych: Path) -> Path | None:
    katalog_wzorow = Path(katalog_danych) / "wzory"
    if not katalog_wzorow.is_dir():
        return None
    for katalog in sorted(katalog_wzorow.iterdir(), key=lambda k: k.name, reverse=True):
        sciezka = katalog / "wzor.json"
        if katalog.is_dir() and sciezka.is_file():
            return sciezka
    return None


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


def zapisz_nazwe_wzoru(katalog_wzoru: Path, podpis: str | None) -> None:
    if not podpis:
        return
    (Path(katalog_wzoru) / "nazwa.txt").write_text(podpis[:60], encoding="utf-8")


def nazwa_wzoru(katalog_wzoru: Path) -> str:
    katalog_wzoru = Path(katalog_wzoru)
    sciezka = katalog_wzoru / "nazwa.txt"
    if sciezka.is_file():
        nazwa = sciezka.read_text(encoding="utf-8").strip()
        if nazwa:
            return nazwa
    return katalog_wzoru.name


def lista_wzorow(katalog_danych: Path) -> list[Path]:
    katalog_wzorow = Path(katalog_danych) / "wzory"
    if not katalog_wzorow.is_dir():
        return []
    wyniki = []
    for katalog in sorted(katalog_wzorow.iterdir(), key=lambda k: k.name, reverse=True):
        sciezka = katalog / "wzor.json"
        if katalog.is_dir() and sciezka.is_file():
            wyniki.append(sciezka)
    return wyniki


def wczytaj_ustawienia(katalog_danych: Path) -> dict:
    sciezka = Path(katalog_danych) / "ustawienia.json"
    if not sciezka.is_file():
        return {"aktywny_wzor": None}
    with open(sciezka, "r", encoding="utf-8") as plik:
        return json.load(plik)


def zapisz_ustawienia(katalog_danych: Path, dane: dict) -> None:
    katalog_danych = Path(katalog_danych)
    katalog_danych.mkdir(parents=True, exist_ok=True)
    sciezka = katalog_danych / "ustawienia.json"
    sciezka_tymczasowa = katalog_danych / "ustawienia.json.tmp"
    with open(sciezka_tymczasowa, "w", encoding="utf-8") as plik:
        json.dump(dane, plik, ensure_ascii=False, indent=2)
    os.replace(sciezka_tymczasowa, sciezka)


def ustaw_aktywny_wzor(katalog_danych: Path, wzor_id: str | None) -> None:
    dane = wczytaj_ustawienia(katalog_danych)
    dane["aktywny_wzor"] = wzor_id
    zapisz_ustawienia(katalog_danych, dane)


def aktywny_wzor(katalog_danych: Path) -> Path | None:
    katalog_danych = Path(katalog_danych)
    wzor_id = wczytaj_ustawienia(katalog_danych).get("aktywny_wzor")
    if wzor_id:
        sciezka = katalog_danych / "wzory" / wzor_id / "wzor.json"
        if sciezka.is_file():
            return sciezka
    return najnowszy_wzor(katalog_danych)


def plik_zasobu(katalog_danych: Path, rodzaj: str, wzor_id: str) -> Path | None:
    katalog = Path(katalog_danych) / rodzaj
    if not katalog.is_dir():
        return None
    rozszerzenia = ROZSZERZENIA_NAKLADEK if rodzaj == "nakladki" else ROZSZERZENIA_ZDJECIE | ROZSZERZENIA_KLIP

    def najnowszy_dla(nazwa_bazowa: str) -> Path | None:
        kandydaci = [
            plik for plik in katalog.iterdir()
            if plik.is_file() and plik.stem == nazwa_bazowa and plik.suffix.lstrip(".").lower() in rozszerzenia
        ]
        if not kandydaci:
            return None
        return max(kandydaci, key=lambda plik: plik.stat().st_mtime)

    return najnowszy_dla(wzor_id) or najnowszy_dla("domyslna")


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
