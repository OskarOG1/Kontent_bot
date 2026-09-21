import json
from datetime import datetime
from pathlib import Path

import pytest

import magazyn


def test_nowy_projekt_tworzy_projekt_json(tmp_path):
    katalog_projektu = magazyn.nowy_projekt(tmp_path)
    dane = magazyn.wczytaj_projekt(katalog_projektu)
    assert dane["stan"] == "zbieranie"
    assert dane["teksty"] == []
    assert dane["wzor_id"] is None
    assert dane["wynik"] is None
    assert dane["blad"] is None
    assert (katalog_projektu / "materialy").is_dir()


def test_nowy_wzor_tworzy_katalog(tmp_path):
    katalog_wzoru = magazyn.nowy_wzor(tmp_path)
    assert katalog_wzoru.is_dir()
    assert katalog_wzoru.parent.name == "wzory"


def test_nowy_projekt_kolizja_w_tej_samej_sekundzie(tmp_path, monkeypatch):
    chwila = datetime(2026, 9, 21, 15, 30, 12)
    monkeypatch.setattr(magazyn, "teraz", lambda: chwila)
    pierwszy = magazyn.nowy_projekt(tmp_path)
    drugi = magazyn.nowy_projekt(tmp_path)
    assert pierwszy != drugi
    assert pierwszy.name == "20260921_153012"
    assert drugi.name == "20260921_153012_2"


def test_sciezka_materialu_message_id_zero_rozne_pliki(tmp_path):
    sciezka1 = magazyn.sciezka_materialu(tmp_path, 0, "abc", "jpg")
    sciezka2 = magazyn.sciezka_materialu(tmp_path, 0, "xyz", "jpg")
    assert sciezka1 != sciezka2
    assert sciezka1.name == "0000000000_abc.jpg"
    assert sciezka2.name == "0000000000_xyz.jpg"


def test_typ_pliku_z_nazwy_i_z_mime():
    assert magazyn.typ_pliku("IMG_1.HEIC", None) == "zdjecie"
    assert magazyn.typ_pliku(None, "video/quicktime") == "klip"
    assert magazyn.typ_pliku(None, "application/pdf") is None


def test_typ_pliku_nieznane_rozszerzenie_bez_mime():
    assert magazyn.typ_pliku("plik.xyz", None) is None


def test_lista_materialow_pomija_part_i_nieznane_sortuje_po_message_id(tmp_path):
    katalog_projektu = tmp_path / "projekt"
    katalog_materialow = katalog_projektu / "materialy"
    katalog_materialow.mkdir(parents=True)
    (katalog_materialow / "0000000010_aaa.jpg").write_bytes(b"x")
    (katalog_materialow / "0000000009_bbb.mp4").write_bytes(b"x")
    (katalog_materialow / "0000000011_ccc.jpg.part").write_bytes(b"x")
    (katalog_materialow / "0000000012_ddd.xyz").write_bytes(b"x")

    wpisy = magazyn.lista_materialow(katalog_projektu)

    assert [wpis["message_id"] for wpis in wpisy] == [9, 10]
    assert wpisy[0]["typ"] == "klip"
    assert wpisy[1]["typ"] == "zdjecie"
    assert all(isinstance(wpis["plik"], Path) for wpis in wpisy)


def test_zapisz_projekt_po_sukcesie_bez_pliku_tymczasowego(tmp_path):
    katalog_projektu = tmp_path / "projekt"
    magazyn.zapisz_projekt(katalog_projektu, {"stan": "start"})
    assert not (katalog_projektu / "projekt.json.tmp").exists()
    assert (katalog_projektu / "projekt.json").exists()


def test_zapisz_projekt_przerwanie_nie_psuje_pliku(tmp_path, monkeypatch):
    katalog_projektu = tmp_path / "projekt"
    magazyn.zapisz_projekt(katalog_projektu, {"stan": "start"})
    sciezka = katalog_projektu / "projekt.json"
    tresc_przed = sciezka.read_text(encoding="utf-8")

    def psuty_dump(dane, plik, **kwargs):
        plik.write("{niepelny")
        raise RuntimeError("przerwanie")

    monkeypatch.setattr(magazyn.json, "dump", psuty_dump)
    with pytest.raises(RuntimeError):
        magazyn.zapisz_projekt(katalog_projektu, {"stan": "polowa"})

    assert sciezka.read_text(encoding="utf-8") == tresc_przed
    assert json.loads(sciezka.read_text(encoding="utf-8"))["stan"] == "start"


def test_najnowszy_wzor_pomija_katalog_bez_wzor_json(tmp_path):
    starszy = tmp_path / "wzory" / "20260921_100000"
    nowszy = tmp_path / "wzory" / "20260921_110000"
    najnowszy = tmp_path / "wzory" / "20260921_120000"
    for katalog in (starszy, nowszy, najnowszy):
        katalog.mkdir(parents=True)
    (starszy / "wzor.json").write_text("{}", encoding="utf-8")
    (nowszy / "wzor.json").write_text("{}", encoding="utf-8")
    assert magazyn.najnowszy_wzor(tmp_path) == nowszy / "wzor.json"


def test_najnowszy_wzor_kolizja_w_tej_samej_sekundzie(tmp_path):
    for nazwa in ("20260921_100000", "20260921_100000_2"):
        katalog = tmp_path / "wzory" / nazwa
        katalog.mkdir(parents=True)
        (katalog / "wzor.json").write_text("{}", encoding="utf-8")
    assert magazyn.najnowszy_wzor(tmp_path).parent.name == "20260921_100000_2"


def test_najnowszy_wzor_bez_wzorow(tmp_path):
    assert magazyn.najnowszy_wzor(tmp_path) is None
    (tmp_path / "wzory").mkdir()
    assert magazyn.najnowszy_wzor(tmp_path) is None
