from pathlib import Path

import pytest

from konfiguracja import wczytaj


def test_brak_tokenu():
    with pytest.raises(ValueError, match="BOT_TOKEN"):
        wczytaj({"OWNER_ID": "123"})


def test_brak_wlasciciela():
    with pytest.raises(ValueError, match="OWNER_ID"):
        wczytaj({"BOT_TOKEN": "token"})


def test_wlasciciel_nie_liczba():
    with pytest.raises(ValueError, match="OWNER_ID"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "abc"})


def test_domyslne_wartosci():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123"})
    assert konf.token == "token"
    assert konf.wlasciciel_id == 123
    assert konf.limit_pobierania_mb == 20
    assert konf.limit_wysylki_mb == 50


def test_katalog_danych_wzgledny_niezalezny_od_biezacego(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "KATALOG_DANYCH": "dane"})
    oczekiwany = Path(__file__).resolve().parent.parent / "dane"
    assert konf.katalog_danych == oczekiwany


def test_katalog_danych_bezwzgledny(tmp_path):
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "KATALOG_DANYCH": str(tmp_path)})
    assert konf.katalog_danych == tmp_path


def test_limity_niestandardowe():
    konf = wczytaj({
        "BOT_TOKEN": "token",
        "OWNER_ID": "123",
        "LIMIT_POBIERANIA_MB": "30",
        "LIMIT_WYSYLKI_MB": "60",
    })
    assert konf.limit_pobierania_mb == 30
    assert konf.limit_wysylki_mb == 60
