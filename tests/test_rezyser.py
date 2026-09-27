import json
from pathlib import Path

import cv2
import generuj
import rezyser


class OdpowiedzTestowa:
    def __init__(self, status_code, dane=None):
        self.status_code = status_code
        self._dane = dane or {}

    def json(self):
        return self._dane


class KlientTestowy:
    def __init__(self, odpowiedzi):
        self.odpowiedzi = list(odpowiedzi)
        self.wywolania = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.wywolania.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        odpowiedz = self.odpowiedzi.pop(0)
        if isinstance(odpowiedz, Exception):
            raise odpowiedz
        return odpowiedz


SCHEMAT_PROSTY = {
    "title": "TestSchemat",
    "type": "object",
    "properties": {"ocena": {"type": "integer"}},
    "required": ["ocena"],
}


def odpowiedz_ok(tresc_json, prompt_tokens=100, completion_tokens=50, koszt=None):
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}
    if koszt is not None:
        usage["cost"] = koszt
    return OdpowiedzTestowa(200, {
        "model": "anthropic/claude-opus-5.5",
        "usage": usage,
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(tresc_json)}}],
    })


def test_wywolaj_model_odpowiedz_poprawna(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([odpowiedz_ok({"ocena": 8})])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "anthropic/claude-opus-5.5", {"tekst": "opis"}, SCHEMAT_PROSTY)
    assert wynik == {"ocena": 8}
    assert zuzycie["wejscie"] == 100
    assert zuzycie["wyjscie"] == 50
    assert zuzycie["powod"] is None


def test_wywolaj_model_koszt_z_usage(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([odpowiedz_ok({"ocena": 8}, koszt=0.42)])
    _, zuzycie = rezyser.wywolaj_model(klient, "anthropic/claude-opus-5.5", {"tekst": "opis"}, SCHEMAT_PROSTY)
    assert zuzycie["koszt_usd"] == 0.42


def test_wywolaj_model_odpowiedz_ucieta(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    odpowiedz = OdpowiedzTestowa(200, {
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "choices": [{"finish_reason": "length", "message": {"content": "{}"}}],
    })
    klient = KlientTestowy([odpowiedz])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert "ucięta" in zuzycie["powod"]


def test_wywolaj_model_odmowa(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    odpowiedz = OdpowiedzTestowa(200, {
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "choices": [{"finish_reason": "content_filter", "message": {"content": "{}"}}],
    })
    klient = KlientTestowy([odpowiedz])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert "odmowa" in zuzycie["powod"]


def test_wywolaj_model_blad_http(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([OdpowiedzTestowa(401, {})])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert "401" in zuzycie["powod"]


def test_wywolaj_model_przekroczony_czas(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([TimeoutError("timeout"), TimeoutError("timeout")])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert zuzycie["powod"] is not None


def test_wywolaj_model_json_niezgodny_ze_schematem(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([odpowiedz_ok({"cos_innego": 1})])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert "schemat" in zuzycie["powod"]


def test_wywolaj_model_5xx_ponawia_raz(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    klient = KlientTestowy([OdpowiedzTestowa(503, {}), odpowiedz_ok({"ocena": 9})])
    wynik, _ = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik == {"ocena": 9}
    assert len(klient.wywolania) == 2


def test_wywolaj_model_brak_klucza(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    klient = KlientTestowy([])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert zuzycie["powod"] == "brak klucza"
    assert klient.wywolania == []


def test_wywolaj_model_zadanie_ma_obrazy_przed_tekstem_i_wysoki_wysilek(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-tajny-klucz")
    obraz = tmp_path / "obraz.jpg"
    generuj.zdjecie_testowe(obraz, rozmiar=(80, 140))
    klient = KlientTestowy([odpowiedz_ok({"ocena": 8})])
    rezyser.wywolaj_model(klient, "model-z-konfiguracji", {"obrazy": [obraz], "tekst": "opis wzoru"}, SCHEMAT_PROSTY)

    zadanie = klient.wywolania[0]
    assert zadanie["url"] == rezyser.OPENROUTER_URL
    assert zadanie["json"]["model"] == "model-z-konfiguracji"
    assert zadanie["json"]["reasoning"] == {"effort": "high"}
    assert zadanie["json"]["response_format"]["type"] == "json_schema"
    tresc = zadanie["json"]["messages"][0]["content"]
    assert tresc[0]["type"] == "image_url"
    assert tresc[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert tresc[-1] == {"type": "text", "text": "opis wzoru"}
    assert zadanie["headers"]["Authorization"] == "Bearer sk-tajny-klucz"
    assert "sk-tajny-klucz" not in json.dumps(zadanie["json"])


def test_koszt_usd_opus_5_5():
    assert rezyser.koszt_usd("anthropic/claude-opus-5.5", 15000, 6000) == 0.18


def test_koszt_usd_model_nieznany():
    assert rezyser.koszt_usd("model/nieznany", 1000, 1000) is None


def przygotuj_zdjecia_i_klipy(tmp_path, liczba_zdjec=5, liczba_klipow=2):
    materialy = []
    for i in range(liczba_zdjec):
        plik = tmp_path / f"zdjecie_{i}.jpg"
        generuj.zdjecie_testowe(plik, rozmiar=(300, 500))
        materialy.append({"plik": str(plik), "typ": "zdjecie", "plik_roboczy": str(plik)})
    for i in range(liczba_klipow):
        plik = tmp_path / f"klip_{i}.mp4"
        generuj.klip_testowy(plik, czas_s=3.0, rozmiar=(320, 180))
        materialy.append({"plik": str(plik), "typ": "klip", "czas_s": 3.0})
    return materialy


def test_arkusze_materialow_zadna_strona_nad_limitem(tmp_path):
    materialy = przygotuj_zdjecia_i_klipy(tmp_path, liczba_zdjec=9, liczba_klipow=1)
    sciezki = rezyser.arkusze_materialow(materialy, [], tmp_path / "arkusze")
    assert sciezki
    for sciezka in sciezki:
        obraz = cv2.imread(str(sciezka))
        assert max(obraz.shape[:2]) <= rezyser.BOK_MAKSYMALNY_ARKUSZA


def test_arkusze_materialow_liczba_numerow_rowna_liczbie_materialow(tmp_path):
    materialy = przygotuj_zdjecia_i_klipy(tmp_path, liczba_zdjec=5, liczba_klipow=3)
    sciezki = rezyser.arkusze_materialow(materialy, [], tmp_path / "arkusze")

    arkusze_klipow = [s for s in sciezki if s.name.startswith("arkusz_klip_")]
    assert len(arkusze_klipow) == 3

    zdjecia = [m for m in materialy if m["typ"] == "zdjecie"]
    assert len(zdjecia) == 5


def test_arkusze_materialow_klip_ma_6_klatek(tmp_path):
    plik = tmp_path / "klip.mp4"
    generuj.klip_testowy(plik, czas_s=4.0, rozmiar=(320, 180))
    klatki = rezyser.klatki_klipu(plik, rezyser.LICZBA_KLATEK_KLIPU, 4.0, *rezyser.KOMORKA_KLATKI_KLIPU)
    assert len(klatki) == 6


def test_arkusze_materialow_wycinki_szachownica(tmp_path):
    wycinek_plik = tmp_path / "wycinek.png"
    generuj.zdjecie_kwadrat_na_przezroczystym(wycinek_plik, rozmiar=(300, 500))
    sciezki = rezyser.arkusze_materialow([], [{"plik": str(wycinek_plik)}], tmp_path / "arkusze")
    assert len(sciezki) == 1
    assert sciezki[0].name == "arkusz_wycinki.jpg"


def test_opis_wzoru_zawiera_klucze_kontraktu():
    wzor = {"sekcje": None}
    plan = {"liczba_klatek": 100, "fps": 30, "ujecia": [
        {"klatka_od": 0, "liczba_klatek": 50, "typ": "zdjecie"},
        {"klatka_od": 50, "liczba_klatek": 50, "typ": "klip"},
    ]}
    materialy = [{"typ": "zdjecie"}, {"typ": "klip", "czas_s": 5.0}]
    opis = rezyser.opis_wzoru(wzor, plan, [0, 15, 30], materialy, {"slowa": []})
    dane = json.loads(opis)
    assert dane["dlugosc_klatek"] == 100
    assert dane["fps"] == 30
    assert dane["klatki_uderzen"] == [0, 15, 30]
    assert dane["poczatek_planszy"] == 50
    assert dane["granice_ujec_wzoru"] == [0, 50]
    assert len(dane["materialy"]) == 2
    assert dane["materialy"][1]["dlugosc_s"] == 5.0
