import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

import tekst


@dataclass
class Konfiguracja:
    token: str
    wlasciciel_id: int
    katalog_danych: Path
    limit_pobierania_mb: int = 20
    limit_wysylki_mb: int = 50
    telegram_api_url: str | None = None
    sila_koloru: float = 0.6
    styl_tekstu: str = "szeryf"
    pozycja_tekstu: str = "dol"


def wczytaj(srodowisko: Mapping[str, str] | None = None) -> Konfiguracja:
    if srodowisko is None:
        load_dotenv(katalog_repo() / ".env")
        srodowisko = os.environ

    token = srodowisko.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN")

    wlasciciel_surowy = srodowisko.get("OWNER_ID")
    if not wlasciciel_surowy:
        raise ValueError("OWNER_ID")
    try:
        wlasciciel_id = int(wlasciciel_surowy)
    except ValueError:
        raise ValueError("OWNER_ID") from None

    katalog_danych_surowy = srodowisko.get("KATALOG_DANYCH", "dane")
    katalog_danych = Path(katalog_danych_surowy)
    if not katalog_danych.is_absolute():
        katalog_danych = katalog_repo() / katalog_danych

    limit_pobierania_mb = int(srodowisko.get("LIMIT_POBIERANIA_MB", 20))
    limit_wysylki_mb = int(srodowisko.get("LIMIT_WYSYLKI_MB", 50))
    telegram_api_url = srodowisko.get("TELEGRAM_API_URL") or None

    try:
        sila_koloru = float(srodowisko.get("SILA_KOLORU", "0.6").replace(",", "."))
    except ValueError:
        raise ValueError("SILA_KOLORU") from None
    if not 0.0 <= sila_koloru <= 1.0:
        raise ValueError("SILA_KOLORU")

    styl_tekstu = srodowisko.get("STYL_TEKSTU", "szeryf")
    if styl_tekstu not in tekst.PRESETY:
        raise ValueError("STYL_TEKSTU")

    pozycja_tekstu = srodowisko.get("POZYCJA_TEKSTU", "dol")
    if pozycja_tekstu not in tekst.POZYCJE:
        raise ValueError("POZYCJA_TEKSTU")

    return Konfiguracja(
        token=token,
        wlasciciel_id=wlasciciel_id,
        katalog_danych=katalog_danych,
        limit_pobierania_mb=limit_pobierania_mb,
        limit_wysylki_mb=limit_wysylki_mb,
        telegram_api_url=telegram_api_url,
        sila_koloru=sila_koloru,
        styl_tekstu=styl_tekstu,
        pozycja_tekstu=pozycja_tekstu,
    )


def katalog_repo() -> Path:
    return Path(__file__).resolve().parent.parent
