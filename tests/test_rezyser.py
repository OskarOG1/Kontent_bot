import json
import subprocess
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


def zbierz_klucze(wezel, klucze):
    if isinstance(wezel, dict):
        for klucz, wartosc in wezel.items():
            klucze.add(klucz)
            zbierz_klucze(wartosc, klucze)
    elif isinstance(wezel, list):
        for element in wezel:
            zbierz_klucze(element, klucze)
    return klucze


def obiekty_schematu(wezel):
    if isinstance(wezel, dict):
        if "properties" in wezel:
            yield wezel
        for klucz, wartosc in wezel.items():
            if klucz == "properties":
                for podschemat in wartosc.values():
                    yield from obiekty_schematu(podschemat)
            else:
                yield from obiekty_schematu(wartosc)
    elif isinstance(wezel, list):
        for element in wezel:
            yield from obiekty_schematu(element)


def test_schematy_bez_ograniczen_nieobslugiwanych_i_ze_wszystkimi_polami_wymaganymi():
    nieobslugiwane = {
        "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
        "minLength", "maxLength", "minItems", "maxItems", "default",
    }
    for schemat in (rezyser.schemat_scenariusza(), rezyser.schemat_oceny()):
        assert not zbierz_klucze(schemat, set()) & nieobslugiwane
        obiekty = list(obiekty_schematu(schemat))
        assert obiekty
        for obiekt in obiekty:
            assert obiekt["additionalProperties"] is False
            assert sorted(obiekt["required"]) == sorted(obiekt["properties"])


def test_schemat_scenariusza_ma_dozwolone_wartosci_efektow_i_uderzen():
    ujecie = rezyser.schemat_scenariusza()["$defs"]["Ujecie"]["properties"]
    assert ujecie["przejscie"]["enum"] == ["brak", "smuga", "najazd", "rozciagniecie"]
    assert ujecie["blysk_s"]["enum"] == [0.0, 0.1, 0.3]
    assert ujecie["uderzenia"]["enum"] == list(range(1, 9))
    assert rezyser.schemat_oceny()["properties"]["ocena"]["enum"] == list(range(1, 11))


def test_polecenie_rezysera_wymienia_efekty_i_numeracje():
    for fraza in ("smuga", "najazd", "rozciagniecie", "0.1", "0.3", "kolaz", "Wycinki nie są ujęciami"):
        assert fraza in rezyser.POLECENIE_REZYSERA


def test_scenariusz_przycina_kolaz_i_uzasadnienie_zamiast_odrzucac():
    scenariusz = rezyser.zbuduj_scenariusz({
        "ujecia": [{"material": 0, "uderzenia": 4, "kolaz": [5, 6, 7, 8, 9, 10]}],
        "uzasadnienie": "x" * 400,
    })
    assert scenariusz is not None
    assert scenariusz.ujecia[0].kolaz == [5, 6, 7, 8, 9]
    assert len(scenariusz.uzasadnienie) == rezyser.LIMIT_UZASADNIENIA


def test_scenariusz_z_przejsciem_spoza_listy_odrzucony():
    assert rezyser.zbuduj_scenariusz({"ujecia": [{"material": 0, "uderzenia": 1, "przejscie": "zoom"}]}) is None


def test_wywolaj_model_powod_bledu_sieci_bez_tresci_wyjatku(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-tajny-klucz")
    blad = ValueError("Illegal header value b'Bearer sk-tajny-klucz'")
    klient = KlientTestowy([blad, blad])
    wynik, zuzycie = rezyser.wywolaj_model(klient, "m", {"tekst": "x"}, SCHEMAT_PROSTY)
    assert wynik is None
    assert zuzycie["powod"] == "błąd sieci: ValueError"


def test_numeracja_wycinki_po_zdjeciach_i_klipach():
    zwykle, wyciete = rezyser.numeracja([{"typ": "zdjecie"}, {"typ": "klip"}], [{"plik": "a.png"}, {"plik": "b.png"}])
    assert list(zwykle) == [0, 1]
    assert list(wyciete) == [2, 3]


def test_opis_wzoru_podaje_wycinki_i_okna_tekstow():
    plan = {"liczba_klatek": 60, "fps": 30, "ujecia": [
        {"klatka_od": 0, "liczba_klatek": 30, "typ": "zdjecie"},
        {"klatka_od": 30, "liczba_klatek": 30, "typ": "zdjecie"},
    ]}
    materialy = [{"typ": "zdjecie"}, {"typ": "klip", "czas_s": 4.0}]
    okna = {"napisy": [[0, 30]], "slowa": [[10, 15], [15, 20]], "pionowy": None}
    dane = json.loads(rezyser.opis_wzoru({"sekcje": None}, plan, [], materialy, okna, [{"plik": "w.png"}]))
    assert dane["materialy"][-1] == {"numer": 2, "typ": "wycinek"}
    assert dane["okna_tekstow"] == okna


def klip_w_kolorze(sciezka, kolor, czas_s=2.0):
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={kolor}:s=270x480:r=30:d={czas_s}",
            "-pix_fmt", "yuv420p", str(sciezka),
        ],
        check=True, stdin=subprocess.DEVNULL,
    )


def test_arkusz_krytyka_wynik_nad_wzorem(tmp_path):
    wynik = tmp_path / "wynik.mp4"
    wzor = tmp_path / "wzor.mp4"
    klip_w_kolorze(wynik, "red")
    klip_w_kolorze(wzor, "blue")

    obraz = cv2.imread(str(rezyser.arkusz_krytyka(wynik, wzor, tmp_path / "arkusz.jpg")))

    x = int(obraz.shape[1] * 2.5 / rezyser.KOLUMNY_ARKUSZA_KRYTYKA)
    niebieski, _, czerwony = (int(v) for v in obraz[int(obraz.shape[0] * 0.25), x])
    assert czerwony > 150 and niebieski < 100
    niebieski, _, czerwony = (int(v) for v in obraz[int(obraz.shape[0] * 0.75), x])
    assert niebieski > 150 and czerwony < 100
    assert "górny wiersz" in rezyser.POLECENIE_KRYTYKA and "WYNIK" in rezyser.POLECENIE_KRYTYKA


def test_opis_montazu_ma_numery_materialow_fragment_klipu_i_plansze():
    materialy = [{"plik": "/p/a.jpg", "typ": "zdjecie"}, {"plik": "/p/k.mp4", "typ": "klip", "czas_s": 6.0}]
    plan = {"liczba_klatek": 60, "fps": 30, "ujecia": [
        {"material": "/p/a.jpg", "typ": "zdjecie", "klatka_od": 0, "liczba_klatek": 30},
        {"material": "/p/k.mp4", "typ": "klip", "klatka_od": 30, "liczba_klatek": 30, "start_w_klipie_s": 1.5},
    ]}

    dane = json.loads(rezyser.opis_montazu(plan, 30, materialy, [{"plik": "/p/w.png"}], plansza_uzyta=True))

    assert [u["material"] for u in dane["ujecia"]] == [0, 1]
    assert dane["ujecia"][1]["od_s"] == 1.5
    assert dane["ujecia"][1]["start_s"] == 1.0
    assert dane["ujecia"][1]["plansza"] is True
    assert dane["materialy"] == [
        {"numer": 0, "typ": "zdjecie"}, {"numer": 1, "typ": "klip", "dlugosc_s": 6.0}, {"numer": 2, "typ": "wycinek"},
    ]


def test_polecenie_rezysera_opisuje_styl_wzorcowego_editu():
    for fraza in (
        "Otwarcie", "Na dropie ujęcie z największym ruchem", "spokojnych klipach z pustym tłem",
        "Nigdy na twarzach", "Nie powtarzaj materiału", "o 1 uderzenie dłużej",
    ):
        assert fraza in rezyser.POLECENIE_REZYSERA


def test_polecenie_rezysera_opisuje_nowy_kolaz_bez_stalych_miejsc():
    import render

    polecenie = rezyser.POLECENIE_REZYSERA
    for x_pola, y_pola in render.POLA_KOLAZU:
        assert f"({round(x_pola * 100)}%, {round(y_pola * 100)}%)" not in polecenie
    assert "lewa góra" not in polecenie
    for fraza in ("Render mierzy ruch tła", "miejsce_kolazu", "kafel", "powiekszenie", "gwiazdy", "co pół uderzenia", "12 złotych gwiazd"):
        assert fraza in polecenie


def test_schemat_ujecia_ma_nowe_pola_z_wartosciami_z_kontraktu():
    ujecie = rezyser.schemat_scenariusza()["$defs"]["Ujecie"]["properties"]
    assert ujecie["wejscie_kolazu"]["enum"] == ["wjazd", "wskok", "powiekszenie"]
    assert ujecie["miejsce_kolazu"]["enum"] == ["auto", "gora", "dol", "lewo", "prawo"]
    assert ujecie["gwiazdy"]["type"] == "boolean"
    assert ujecie["kolaz"]["type"] == "array"


def test_opis_montazu_ma_wejscie_miejsca_ruch_tla_kolazu_i_gwiazdy():
    plan = {"liczba_klatek": 90, "fps": 30, "ujecia": [
        {"material": "/p/k.mp4", "typ": "klip", "klatka_od": 0, "liczba_klatek": 60, "start_w_klipie_s": 0.0,
         "efekt_scenariusza": {"uderzenie": False, "blysk_s": 0.0, "wstrzas": False, "przejscie": "smuga"},
         "kolaz_scenariusza": [2, 1], "gwiazdy": True},
        {"material": "/p/k.mp4", "typ": "klip", "klatka_od": 60, "liczba_klatek": 30, "start_w_klipie_s": 0.0,
         "efekt_scenariusza": None, "kolaz_scenariusza": [2]},
    ]}
    kolaze = [{"ujecie": 0, "wycinki": ["w.png"], "ruch": 1.65, "wejscie": "powiekszenie", "miejsca": [[0.1, 0.2]]}]

    dane = json.loads(rezyser.opis_montazu(
        plan, 30, [{"plik": "/p/k.mp4", "typ": "klip", "czas_s": 6.0}, {"plik": "/p/a.jpg", "typ": "zdjecie"}], [{"plik": "/p/w.png"}],
        kolaze=kolaze, kolaze_pominiete=[{"ujecie": 1, "ruch": 9.0}], gwiazdy={"od_s": 0.0, "do_s": 2.0},
    ))

    pierwsze, drugie = dane["ujecia"]
    assert pierwsze["kolaz"] == {"elementy": [2, 1], "wejscie": "powiekszenie", "miejsca": [[0.1, 0.2]], "ruch_tla": 1.65}
    assert pierwsze["przejscie"] == "smuga" and pierwsze["gwiazdy"] is True
    assert drugie["kolaz"] == {"elementy": [2], "pominiety_ruch_tla": 9.0}
    assert dane["gwiazdy"] == {"od_s": 0.0, "do_s": 2.0}


def test_polecenie_krytyka_sprawdza_powtorki_i_miejsce_posagow():
    assert "powtarzają" in rezyser.POLECENIE_KRYTYKA
    assert "posągi" in rezyser.POLECENIE_KRYTYKA


def test_polecenie_krytyka_sprawdza_tlo_rozmiary_miejsca_i_gwiazdy():
    for fraza in ("ruch tła", "rozmiary elementów", "miejsca", "12 złotych gwiazd"):
        assert fraza in rezyser.POLECENIE_KRYTYKA
