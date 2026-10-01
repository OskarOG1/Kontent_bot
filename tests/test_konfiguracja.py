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
    assert konf.sila_koloru == 0.6
    assert konf.styl_tekstu == "szeryf"
    assert konf.pozycja_tekstu == "dol"
    assert konf.dlugosc_nakladki_krycie_s == 2.5


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


def test_telegram_api_url_domyslnie_brak():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123"})
    assert konf.telegram_api_url is None


def test_telegram_api_url_ustawiony():
    konf = wczytaj({
        "BOT_TOKEN": "token",
        "OWNER_ID": "123",
        "TELEGRAM_API_URL": "http://bot-api:8081",
    })
    assert konf.telegram_api_url == "http://bot-api:8081"


def test_sila_koloru_kropka_i_przecinek():
    konf_kropka = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "SILA_KOLORU": "0.6"})
    konf_przecinek = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "SILA_KOLORU": "0,6"})
    assert konf_kropka.sila_koloru == 0.6
    assert konf_przecinek.sila_koloru == 0.6


def test_sila_koloru_poza_zakresem():
    with pytest.raises(ValueError, match="SILA_KOLORU"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "SILA_KOLORU": "1.5"})


def test_styl_tekstu_niepoprawny():
    with pytest.raises(ValueError, match="STYL_TEKSTU"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "STYL_TEKSTU": "kursywa"})


def test_pozycja_tekstu_niestandardowa():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "STYL_TEKSTU": "blok", "POZYCJA_TEKSTU": "gora"})
    assert konf.styl_tekstu == "blok"
    assert konf.pozycja_tekstu == "gora"


def test_dlugosc_nakladki_krycie_niestandardowa():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "DLUGOSC_NAKLADKI_KRYCIE_S": "3,5"})
    assert konf.dlugosc_nakladki_krycie_s == 3.5


def test_dlugosc_nakladki_krycie_niepoprawna():
    with pytest.raises(ValueError, match="DLUGOSC_NAKLADKI_KRYCIE_S"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "DLUGOSC_NAKLADKI_KRYCIE_S": "abc"})


def test_ai_domyslne_wartosci():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123"})
    assert konf.openrouter_api_key is None
    assert konf.model_ai == "anthropic/claude-opus-5.5"
    assert konf.model_ai_zapas is None
    assert konf.ai_rezyser is True
    assert konf.ai_krytyk is True
    assert konf.prog_oceny_ai == 7


def test_ai_klucz_pusty_oznacza_brak():
    konf = wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "OPENROUTER_API_KEY": ""})
    assert konf.openrouter_api_key is None


def test_ai_klucz_i_model_niestandardowe():
    konf = wczytaj({
        "BOT_TOKEN": "token",
        "OWNER_ID": "123",
        "OPENROUTER_API_KEY": "sk-or-abc",
        "MODEL_AI": "anthropic/claude-opus-4.5",
        "MODEL_AI_ZAPAS": "anthropic/claude-sonnet-5",
        "AI_REZYSER": "nie",
        "AI_KRYTYK": "nie",
        "PROG_OCENY_AI": "5",
    })
    assert konf.openrouter_api_key == "sk-or-abc"
    assert konf.model_ai == "anthropic/claude-opus-4.5"
    assert konf.model_ai_zapas == "anthropic/claude-sonnet-5"
    assert konf.ai_rezyser is False
    assert konf.ai_krytyk is False
    assert konf.prog_oceny_ai == 5


def test_ai_rezyser_niepoprawna_wartosc():
    with pytest.raises(ValueError, match="AI_REZYSER"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "AI_REZYSER": "moze"})


def test_prog_oceny_ai_poza_zakresem():
    with pytest.raises(ValueError, match="PROG_OCENY_AI"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "PROG_OCENY_AI": "11"})


def test_gwiazdy_w_haku_domyslnie_tak_i_nie_z_srodowiska():
    assert wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123"}).gwiazdy_w_haku is True
    assert wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "GWIAZDY_W_HAKU": "nie"}).gwiazdy_w_haku is False
    assert wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "GWIAZDY_W_HAKU": "tak"}).gwiazdy_w_haku is True


def test_gwiazdy_w_haku_niepoprawne():
    with pytest.raises(ValueError, match="GWIAZDY_W_HAKU"):
        wczytaj({"BOT_TOKEN": "token", "OWNER_ID": "123", "GWIAZDY_W_HAKU": "moze"})
