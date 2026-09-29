import base64
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LIMIT_TOKENOW_WYJSCIA = 16000
LIMIT_CZASU_S = 180.0
BOK_MAKSYMALNY_ARKUSZA = 1568
LICZBA_KLATEK_KLIPU = 6
KOMORKA_ZDJECIA = (96, 171)
KOMORKA_KLATKI_KLIPU = (128, 72)
KOMORKA_WYCINKA = (96, 171)
KOLUMNY_ZDJEC = 4
KOLUMNY_WYCINKOW = 4

CENY_USD_NA_MILION_TOKENOW = {
    "anthropic/claude-opus-5.5": (4.0, 20.0),
}


def koszt_usd(model: str, wejscie: int, wyjscie: int) -> float | None:
    ceny = CENY_USD_NA_MILION_TOKENOW.get(model)
    if ceny is None:
        return None
    cena_wejscia, cena_wyjscia = ceny
    return round(wejscie / 1_000_000 * cena_wejscia + wyjscie / 1_000_000 * cena_wyjscia, 6)


def zuzycie(wejscie: int = 0, wyjscie: int = 0, koszt: float | None = None, powod: str | None = None) -> dict:
    return {"wejscie": wejscie, "wyjscie": wyjscie, "koszt_usd": koszt, "powod": powod}


def zakoduj_obraz_jpeg(sciezka: Path) -> str:
    dane = Path(sciezka).read_bytes()
    zakodowane = base64.b64encode(dane).decode("ascii")
    return f"data:image/jpeg;base64,{zakodowane}"


def wywolaj_model(klient, model: str | list[str], tresc: dict, schemat: dict) -> tuple[dict | None, dict]:
    klucz = os.environ.get("OPENROUTER_API_KEY")
    if not klucz:
        return None, zuzycie(powod="brak klucza")

    czesci = [
        {"type": "image_url", "image_url": {"url": zakoduj_obraz_jpeg(obraz)}}
        for obraz in tresc.get("obrazy", [])
    ]
    czesci.append({"type": "text", "text": tresc.get("tekst", "")})

    zadanie = {
        "messages": [{"role": "user", "content": czesci}],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": schemat.get("title", "odpowiedz"),
                "strict": True,
                "schema": schemat,
            },
        },
        "reasoning": {"effort": "high"},
        "max_tokens": LIMIT_TOKENOW_WYJSCIA,
    }
    if isinstance(model, list):
        zadanie["models"] = model
        model_do_kosztu = model[0] if model else None
    else:
        zadanie["model"] = model
        model_do_kosztu = model

    naglowki = {"Authorization": f"Bearer {klucz}", "Content-Type": "application/json"}

    odpowiedz = None
    ostatni_powod = None
    for probe in range(2):
        try:
            odpowiedz = klient.post(OPENROUTER_URL, headers=naglowki, json=zadanie, timeout=LIMIT_CZASU_S)
        except Exception as wyjatek:
            ostatni_powod = f"błąd sieci: {type(wyjatek).__name__}"
            odpowiedz = None
            continue
        if odpowiedz.status_code >= 500:
            ostatni_powod = f"błąd HTTP {odpowiedz.status_code}"
            odpowiedz = None
            continue
        break

    if odpowiedz is None:
        return None, zuzycie(powod=ostatni_powod or "błąd sieci")

    if odpowiedz.status_code >= 400:
        return None, zuzycie(powod=f"błąd HTTP {odpowiedz.status_code}")

    try:
        dane = odpowiedz.json()
    except ValueError:
        return None, zuzycie(powod="odpowiedź nie jest poprawnym JSON")
    if not isinstance(dane, dict):
        return None, zuzycie(powod="odpowiedź nie jest poprawnym JSON")

    uzycie = dane.get("usage") or {}
    wejscie_tokenow = int(uzycie.get("prompt_tokens", 0) or 0)
    wyjscie_tokenow = int(uzycie.get("completion_tokens", 0) or 0)
    model_uzyty = dane.get("model") or model_do_kosztu
    koszt = uzycie.get("cost")
    if koszt is None:
        koszt = koszt_usd(model_uzyty, wejscie_tokenow, wyjscie_tokenow)

    wybory = dane.get("choices") or []
    if not wybory:
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "brak odpowiedzi modelu")

    wybor = wybory[0]
    powod_zakonczenia = wybor.get("finish_reason")
    if powod_zakonczenia == "length":
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "odpowiedź ucięta limitem długości")
    if powod_zakonczenia in ("content_filter", "refusal"):
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "odmowa modelu")

    wiadomosc = wybor.get("message") or {}
    if wiadomosc.get("refusal"):
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "odmowa modelu")

    tresc_odpowiedzi = wiadomosc.get("content")
    if not tresc_odpowiedzi:
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "brak odpowiedzi modelu")

    try:
        odpowiedz_json = json.loads(tresc_odpowiedzi)
    except (ValueError, TypeError):
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "JSON niezgodny ze schematem")

    if not isinstance(odpowiedz_json, dict):
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "JSON niezgodny ze schematem")

    wymagane = schemat.get("required") or []
    if any(klucz_pola not in odpowiedz_json for klucz_pola in wymagane):
        return None, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, "JSON niezgodny ze schematem")

    return odpowiedz_json, zuzycie(wejscie_tokenow, wyjscie_tokenow, koszt, None)


def skaluj_pokryj(obraz: np.ndarray, kx: int, ky: int) -> np.ndarray:
    wysokosc, szerokosc = obraz.shape[:2]
    skala = max(kx / szerokosc, ky / wysokosc)
    nowa_szerokosc = max(1, round(szerokosc * skala))
    nowa_wysokosc = max(1, round(wysokosc * skala))
    zmieniony = cv2.resize(obraz, (nowa_szerokosc, nowa_wysokosc), interpolation=cv2.INTER_AREA)
    x0 = (nowa_szerokosc - kx) // 2
    y0 = (nowa_wysokosc - ky) // 2
    return zmieniony[y0:y0 + ky, x0:x0 + kx]


def narysuj_numer(obraz: np.ndarray, numer: int) -> np.ndarray:
    return narysuj_etykiete(obraz, str(numer))


def narysuj_etykiete(obraz: np.ndarray, tekst: str) -> np.ndarray:
    obraz = np.ascontiguousarray(obraz)
    cv2.rectangle(obraz, (0, 0), (12 + 11 * len(tekst), 20), (0, 0, 0), -1)
    cv2.putText(obraz, tekst, (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    return obraz


def ogranicz_bok(obraz: np.ndarray, limit: int) -> np.ndarray:
    wysokosc, szerokosc = obraz.shape[:2]
    najdluzszy = max(wysokosc, szerokosc)
    if najdluzszy <= limit:
        return obraz
    skala = limit / najdluzszy
    return cv2.resize(
        obraz, (max(1, round(szerokosc * skala)), max(1, round(wysokosc * skala))), interpolation=cv2.INTER_AREA,
    )


def zapisz_jpeg(obraz: np.ndarray, sciezka: Path) -> None:
    ok, bufor = cv2.imencode(".jpg", obraz, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("nie udalo sie zakodowac arkusza")
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_bytes(bufor.tobytes())


def siatka_ponumerowana(pozycje: list[tuple[int, np.ndarray]], kx: int, ky: int, kolumny: int) -> np.ndarray:
    wiersze = math.ceil(len(pozycje) / kolumny)
    siatka = np.full((wiersze * ky, kolumny * kx, 3), 32, dtype=np.uint8)
    for indeks, (numer, obraz) in enumerate(pozycje):
        komorka = narysuj_numer(skaluj_pokryj(obraz, kx, ky).copy(), numer)
        kolumna, wiersz = indeks % kolumny, indeks // kolumny
        siatka[wiersz * ky:(wiersz + 1) * ky, kolumna * kx:(kolumna + 1) * kx] = komorka
    return siatka


def szachownica(kx: int, ky: int, rozmiar_kratki: int = 8) -> np.ndarray:
    plansza = np.zeros((ky, kx, 3), dtype=np.uint8)
    for y in range(0, ky, rozmiar_kratki):
        for x in range(0, kx, rozmiar_kratki):
            jasna = ((x // rozmiar_kratki) + (y // rozmiar_kratki)) % 2 == 0
            plansza[y:y + rozmiar_kratki, x:x + rozmiar_kratki] = 200 if jasna else 140
    return plansza


def wczytaj_z_alfa(sciezka: Path, kx: int, ky: int) -> np.ndarray:
    obraz = cv2.imread(str(sciezka), cv2.IMREAD_UNCHANGED)
    if obraz is None:
        return szachownica(kx, ky)
    obraz = skaluj_pokryj(obraz, kx, ky)
    if obraz.ndim == 3 and obraz.shape[2] == 4:
        tlo = szachownica(kx, ky).astype(np.float32)
        alfa = obraz[:, :, 3:4].astype(np.float32) / 255.0
        kolor = obraz[:, :, :3].astype(np.float32)
        wynik = kolor * alfa + tlo * (1 - alfa)
        return wynik.astype(np.uint8)
    return obraz[:, :, :3]


def klatki_klipu(plik: Path, liczba_klatek: int, czas_s: float, kx: int, ky: int, przyciecie: str = "") -> list[np.ndarray]:
    czas_s = max(czas_s, 1.0 / 30)
    fps = liczba_klatek / czas_s
    filtr = f"fps={fps:.10f},{przyciecie}scale={kx}:{ky}:force_original_aspect_ratio=increase,crop={kx}:{ky}"
    with tempfile.TemporaryDirectory() as katalog:
        surowy = Path(katalog) / "klatki.raw"
        wynik = subprocess.run(
            [
                "ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-i", str(plik),
                "-vf", filtr, "-frames:v", str(liczba_klatek),
                "-pix_fmt", "bgr24", "-f", "rawvideo", str(surowy),
            ],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
        if wynik.returncode != 0:
            raise RuntimeError(f"ffmpeg zakonczyl sie kodem {wynik.returncode}: {wynik.stderr.decode('utf-8', errors='replace')}")
        dane = np.fromfile(surowy, dtype=np.uint8)
    liczba_odczytana = dane.size // (ky * kx * 3)
    if liczba_odczytana == 0:
        return []
    klatki = dane[: liczba_odczytana * ky * kx * 3].reshape(liczba_odczytana, ky, kx, 3)
    return [klatki[i].copy() for i in range(liczba_odczytana)]


def numeracja(materialy: list[dict], wycinki: list[dict]) -> tuple[dict[int, dict], dict[int, dict]]:
    zwykle = {numer: material for numer, material in enumerate(materialy)}
    wyciete = {len(materialy) + numer: wycinek for numer, wycinek in enumerate(wycinki)}
    return zwykle, wyciete


def lista_materialow(materialy: list[dict], wycinki: list[dict]) -> list[dict]:
    zwykle, wyciete = numeracja(materialy, wycinki)
    lista = []
    for numer, material in zwykle.items():
        if material["typ"] == "klip":
            lista.append({"numer": numer, "typ": "klip", "dlugosc_s": round(float(material.get("czas_s", 0.0)), 3)})
        else:
            lista.append({"numer": numer, "typ": material["typ"]})
    lista += [{"numer": numer, "typ": "wycinek"} for numer in wyciete]
    return lista


def z_naglowkiem(obraz: np.ndarray, tekst: str) -> np.ndarray:
    naglowek = np.full((24, obraz.shape[1], 3), 32, dtype=np.uint8)
    cv2.putText(naglowek, tekst, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    return np.vstack([naglowek, obraz])


def arkusze_materialow(materialy: list[dict], wycinki: list[dict], katalog_pracy: Path) -> list[Path]:
    import render as render_modul

    katalog_pracy = Path(katalog_pracy)
    katalog_pracy.mkdir(parents=True, exist_ok=True)
    sciezki = []
    zwykle, wyciete = numeracja(materialy, wycinki)

    kx, ky = KOMORKA_ZDJECIA
    zdjecia = [(numer, material) for numer, material in zwykle.items() if material["typ"] == "zdjecie"]
    if zdjecia:
        pozycje = []
        for numer, material in zdjecia:
            zrodlo = material.get("plik_roboczy", material["plik"])
            obraz = cv2.imread(str(zrodlo))
            if obraz is None:
                obraz = np.full((ky, kx, 3), 64, dtype=np.uint8)
            pozycje.append((numer, obraz))
        siatka = z_naglowkiem(siatka_ponumerowana(pozycje, kx, ky, KOLUMNY_ZDJEC), "zdjecia: numer do pola material")
        siatka = ogranicz_bok(siatka, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / "arkusz_zdjecia.jpg"
        zapisz_jpeg(siatka, sciezka)
        sciezki.append(sciezka)

    kkx, kky = KOMORKA_KLATKI_KLIPU
    for numer, material in zwykle.items():
        if material["typ"] != "klip":
            continue
        czas_s = float(material.get("czas_s", 1.0))
        klatki = klatki_klipu(
            Path(material["plik"]), LICZBA_KLATEK_KLIPU, czas_s, kkx, kky,
            przyciecie=render_modul.filtr_kadru(material.get("kadr")),
        )
        if not klatki:
            continue
        obraz = z_naglowkiem(np.hstack(klatki), f"klip {numer}, {czas_s:.1f} s")
        obraz = ogranicz_bok(obraz, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / f"arkusz_klip_{numer}.jpg"
        zapisz_jpeg(obraz, sciezka)
        sciezki.append(sciezka)

    if wyciete:
        wkx, wky = KOMORKA_WYCINKA
        pozycje = [(numer, wczytaj_z_alfa(Path(wycinek["plik"]), wkx, wky)) for numer, wycinek in wyciete.items()]
        siatka = z_naglowkiem(siatka_ponumerowana(pozycje, wkx, wky, KOLUMNY_WYCINKOW), "wycinki: numer do pola kolaz")
        siatka = ogranicz_bok(siatka, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / "arkusz_wycinki.jpg"
        zapisz_jpeg(siatka, sciezka)
        sciezki.append(sciezka)

    return sciezki


def opis_wzoru(
    wzor: dict, plan: dict, uderzenia: list[int], materialy: list[dict], okna_tekstow: dict | None,
    wycinki: list[dict] | None = None,
) -> str:
    import render as render_modul

    sekcje = wzor.get("sekcje")
    plan_ujecia = plan.get("ujecia", [])
    try:
        klatka_dropu = render_modul.koniec_haka(plan, sekcje) if sekcje and sekcje.get("drop_ujecie") is not None else None
    except Exception:
        klatka_dropu = None

    opis = {
        "dlugosc_klatek": plan["liczba_klatek"],
        "fps": plan["fps"],
        "klatki_uderzen": list(uderzenia),
        "klatka_dropu": klatka_dropu,
        "poczatek_planszy": plan_ujecia[-1]["klatka_od"] if plan_ujecia else None,
        "granice_ujec_wzoru": [u["klatka_od"] for u in plan_ujecia],
        "okna_tekstow": okna_tekstow or {},
        "materialy": lista_materialow(materialy, wycinki or []),
    }
    return json.dumps(opis, ensure_ascii=False)


LICZBA_WYCINKOW_KOLAZU_SCENARIUSZA = 3
LIMIT_UZASADNIENIA = 300
LICZBA_MOCNYCH_STRON = 3
POLA_POMIJANE_W_SCHEMACIE = ("title", "default")


class Ujecie(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: int = Field(description="numer zdjęcia albo klipu z listy materiałów, nigdy numer wycinka")
    od_s: float = Field(default=0.0, description="początek fragmentu klipu w sekundach, dla zdjęcia 0")
    uderzenia: Literal[1, 2, 3, 4, 5, 6, 7, 8] = Field(description="długość ujęcia w uderzeniach")
    uderzenie: bool = Field(default=False, description="krótki zoom na początku ujęcia")
    blysk_s: Literal[0.0, 0.1, 0.3] = Field(default=0.0, description="biały błysk na początku ujęcia w sekundach")
    wstrzas: bool = Field(default=False, description="wstrząs kadru przez pierwsze pół sekundy")
    przejscie: Literal["brak", "smuga", "najazd"] = Field(default="brak", description="wejście ujęcia")
    kolaz: list[int] = Field(default_factory=list, description="najwyżej 3 numery wycinków, tylko na klipach")

    @field_validator("kolaz", mode="before")
    @classmethod
    def przytnij_kolaz(cls, wartosc):
        if isinstance(wartosc, list):
            return wartosc[:LICZBA_WYCINKOW_KOLAZU_SCENARIUSZA]
        return wartosc


class Scenariusz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ujecia: list[Ujecie] = Field(description="ujęcia w kolejności odtwarzania od pierwszej klatki")
    uzasadnienie: str = Field(default="", description="najwyżej 300 znaków")

    @field_validator("uzasadnienie", mode="before")
    @classmethod
    def przytnij_uzasadnienie(cls, wartosc):
        if isinstance(wartosc, str):
            return wartosc[:LIMIT_UZASADNIENIA]
        return wartosc


class Poprawka(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ujecie: int = Field(description="numer ujęcia z listy ujęć wyniku")
    problem: str
    zmiana: Ujecie


class Ocena(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ocena: Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    mocne: list[str] = Field(default_factory=list, description="najwyżej 3 krótkie punkty")
    poprawki: list[Poprawka] = Field(default_factory=list)

    @field_validator("mocne", mode="before")
    @classmethod
    def przytnij_mocne(cls, wartosc):
        if isinstance(wartosc, list):
            return wartosc[:LICZBA_MOCNYCH_STRON]
        return wartosc


def oczysc_schemat(wezel):
    if isinstance(wezel, list):
        return [oczysc_schemat(element) for element in wezel]
    if not isinstance(wezel, dict):
        return wezel
    wynik = {}
    for klucz, wartosc in wezel.items():
        if klucz in POLA_POMIJANE_W_SCHEMACIE:
            continue
        if klucz in ("properties", "$defs"):
            wynik[klucz] = {nazwa: oczysc_schemat(podschemat) for nazwa, podschemat in wartosc.items()}
        else:
            wynik[klucz] = oczysc_schemat(wartosc)
    if "properties" in wynik:
        wynik["required"] = list(wynik["properties"])
        wynik["additionalProperties"] = False
    return wynik


def schemat_dla_modelu(klasa) -> dict:
    schemat = oczysc_schemat(klasa.model_json_schema())
    return {"title": klasa.__name__, **schemat}


def zbuduj_scenariusz(dane: dict) -> "Scenariusz | None":
    try:
        return Scenariusz.model_validate(dane)
    except ValidationError:
        return None


def zbuduj_ocene(dane: dict) -> "Ocena | None":
    try:
        return Ocena.model_validate(dane)
    except ValidationError:
        return None


def schemat_scenariusza() -> dict:
    return schemat_dla_modelu(Scenariusz)


def schemat_oceny() -> dict:
    return schemat_dla_modelu(Ocena)


POLECENIE_REZYSERA = (
    "Jesteś reżyserem montażu pionowych edytów 9:16 na TikToka dla marki czapek 1993 Supply. "
    "Wzór ma stałą strukturę: hak (pierwsze sekundy, naturalne kolory, bez nakładki), drop "
    "(od niego pełnoekranowa nakładka i mocny grading), montaż i plansza końcowa z produktem. "
    "Z materiałów użytkownika ułóż scenariusz zgodny ze strukturą i rytmem wzoru opisanym w danych. "
    "Nic z obrazu ani dźwięku wzoru nie trafia do wyniku, wzór pokazuje tylko strukturę i styl.\n"
    "Obrazy: arkusz zdjęć z numerem w rogu, pasek klatek każdego klipu z numerem i sekundami w nagłówku "
    "oraz arkusz wycinków na szachownicy. Lista materiałów w danych podaje typ każdego numeru i długość "
    "klipów. Pole material to numer zdjęcia albo klipu. Wycinki nie są ujęciami, ich numery wolno podać "
    "tylko w polu kolaz.\n"
    "Czas: dane podają klatki uderzeń, klatkę dropu, początek planszy, granice ujęć wzoru i okna napisów, "
    "słów i napisu pionowego. Ujęcia idą po kolei od pierwszej klatki, a długość ujęcia to liczba uderzeń. "
    "Drop i początek planszy to twarde cięcia: ujęcie, które przez nie przechodzi, zostanie na nich ucięte. "
    "Od początku planszy do końca editu stoi plansza końcowa, więc tam nie planuj ważnych ujęć. "
    "Brakujący koniec uzupełni automat, a nadmiar ujęć odpada.\n"
    "Styl: wzorcowy edit właściciela, do którego masz się zbliżyć rytmem i sposobem użycia efektów, bez "
    "kopiowania jego treści. Trwa 26 s przy 131 BPM, ma 18 ujęć, drop w 43% długości i planszę przez "
    "ostatnie 3 uderzenia. Proporcje przenieś na wzór z danych (jego uderzenia, drop i planszę). Energię "
    "daje ruch w kadrze i to, co dzieje się na uderzeniach, a nie sama liczba cięć.\n"
    "- Otwarcie (pierwsze 3 do 4 uderzeń) działa jak plansza tytułowa: spokojny klip z mocnym tłem (flaga, "
    "niebo, pejzaż, mur, sztandar), na który wskakują posągi, po jednym na uderzenie, pod napisem haka.\n"
    "- Dalej w haku 4 ujęcia po 2 do 4 uderzenia i jedno dłuższe (do 8 uderzeń) z serią obrazów na spokojnym "
    "tle: postacie w ruchu albo z emocją (ktoś idzie w stronę kamery, zbliżenie twarzy, scena z filmu, "
    "zwierzę). Na każdym coś dzieje się w rytmie: napis, słowa, napis pionowy albo wskakujące wycinki.\n"
    "- Na dropie ujęcie z największym ruchem w kadrze (lądowanie, zryw, start, szarża).\n"
    "- Montaż po dropie: 10 do 11 ujęć po 2 do 6 uderzeń, głównie klipy z ruchem (jazda, szarża, lot, "
    "marsz, kamera w ruchu), przeplatane krótkimi mocnymi obrazami po 1 do 2 uderzenia. W ostatnich "
    "3 sekundach przed planszą 2 do 3 bardzo krótkie ujęcia po 1 uderzeniu.\n"
    "- Posągi i inne wycinki (pole kolaz) stawiaj tylko na spokojnych klipach z pustym tłem (niebo, pejzaż, "
    "woda, flaga, mur, sztandar, grafika), 1 do 3 wycinki na jednym ujęciu, 3 do 4 takie ujęcia w edicie: "
    "otwarcie, jedno w haku i 1 do 2 w montażu. Nigdy na twarzach, tłumie, ruchliwej ulicy, klipie z akcją "
    "ani na dropie. Wycinki wskakują na kolejnych uderzeniach wewnątrz ujęcia, więc ujęcie z kolażem trwa "
    "co najmniej o 1 uderzenie dłużej, niż ma wycinków. Stoją w stałych miejscach kadru: lewa góra (30% "
    "szerokości, 30% wysokości), prawa strona (70%, 47%) i lewy dół (38%, 66%), więc wybieraj klipy, "
    "w których te miejsca nie zasłaniają twarzy ani głównej postaci.\n"
    "- Nie powtarzaj materiału, dopóki nie użyjesz wszystkich, a powtórki nigdy w sąsiednich ujęciach. Gdy "
    "materiałów jest mało, wydłuż klipy z akcją do 6 do 8 uderzeń zamiast powtarzać zdjęcia.\n"
    "- Zdjęcia bez ruchu (obrazy, grafiki, plakaty, mapy) trwają 1 do 2 uderzeń, klipy 2 do 6 uderzeń. "
    "Wybieraj klipy z ruchem w kadrze i bez czarnych pasów kinowych, jeśli widać je na pasku klatek. "
    "od_s ustaw na najmocniejszej akcji, nie na pierwszej sekundzie klipu; od_s plus długość ujęcia musi "
    "zmieścić się w klipie.\n"
    "Efekty na początku ujęcia: uderzenie (krótki zoom w rytmie), blysk_s (biały błysk 0, 0.1 albo 0.3 s), "
    "wstrzas (wstrząs kadru przez pół sekundy), przejscie (brak albo smuga, czyli rozmycie ruchu na pierwszych "
    "klatkach; najazd działa tylko na planszy). Automat daje każdemu ujęciu uderzenie, klipom błysk 0.1, "
    "a co trzeciemu zdjęciu po dropie smugę. Ujęcie na dropie i tak dostaje błysk 0.3 i wstrząs.\n"
    "Zwróć wyłącznie JSON zgodny z podanym schematem: listę ujęć w kolejności odtwarzania i krótkie "
    "uzasadnienie wyboru (najwyżej 300 znaków)."
)

KOMORKA_ARKUSZA_KRYTYKA = (108, 192)
KOLUMNY_ARKUSZA_KRYTYKA = 16
KLATEK_NA_S_ARKUSZA_KRYTYKA = 2.0


def czas_trwania_pliku(sciezka: Path) -> float:
    wynik = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(sciezka)],
        stdin=subprocess.DEVNULL, capture_output=True,
    )
    return float(wynik.stdout.decode("utf-8", errors="replace").strip())


def klatki_o_stalej_czestosci(plik: Path, klatki_na_s: float, czas_pliku_s: float, kx: int, ky: int) -> list[np.ndarray]:
    liczba_klatek = max(1, math.ceil(czas_pliku_s * klatki_na_s))
    return klatki_klipu(plik, liczba_klatek, czas_pliku_s, kx, ky)


def arkusz_krytyka(
    wynik: Path, zrodlo_wzoru: Path, cel: Path,
    klatki_na_s: float = KLATEK_NA_S_ARKUSZA_KRYTYKA, kolumny: int = KOLUMNY_ARKUSZA_KRYTYKA,
    komorka: tuple[int, int] = KOMORKA_ARKUSZA_KRYTYKA,
) -> Path:
    kx, ky = komorka
    czas_wynik = czas_trwania_pliku(wynik)
    czas_wzoru = czas_trwania_pliku(zrodlo_wzoru)
    n = max(1, math.ceil(max(czas_wynik, czas_wzoru) * klatki_na_s))

    klatki_wyniku = klatki_o_stalej_czestosci(wynik, klatki_na_s, czas_wynik, kx, ky)
    klatki_wzoru = klatki_o_stalej_czestosci(zrodlo_wzoru, klatki_na_s, czas_wzoru, kx, ky)

    puste = np.zeros((ky, kx, 3), dtype=np.uint8)
    while len(klatki_wyniku) < n:
        klatki_wyniku.append(puste)
    while len(klatki_wzoru) < n:
        klatki_wzoru.append(puste)

    wiersze_grup = math.ceil(n / kolumny)
    grubosc_linii = 2
    linia = np.full((grubosc_linii, kolumny * kx, 3), 230, dtype=np.uint8)

    czesci = []
    for grupa in range(wiersze_grup):
        wycinek_wzoru = list(klatki_wzoru[grupa * kolumny:(grupa + 1) * kolumny])
        wycinek_wyniku = list(klatki_wyniku[grupa * kolumny:(grupa + 1) * kolumny])
        while len(wycinek_wzoru) < kolumny:
            wycinek_wzoru.append(puste)
        while len(wycinek_wyniku) < kolumny:
            wycinek_wyniku.append(puste)
        if grupa > 0:
            czesci.append(linia)
        czesci.append(narysuj_etykiete(np.hstack(wycinek_wyniku), "WYNIK"))
        czesci.append(narysuj_etykiete(np.hstack(wycinek_wzoru), "WZOR"))

    siatka = np.vstack(czesci) if czesci else np.zeros((ky, kolumny * kx, 3), dtype=np.uint8)
    siatka = ogranicz_bok(siatka, BOK_MAKSYMALNY_ARKUSZA)
    zapisz_jpeg(siatka, cel)
    return cel


def opis_montazu(
    plan: dict, fps: int, materialy: list[dict] | None = None, wycinki: list[dict] | None = None,
    plansza_uzyta: bool = False,
) -> str:
    zwykle, _ = numeracja(materialy or [], wycinki or [])
    numery = {str(material["plik"]): numer for numer, material in zwykle.items()}
    ujecia = []
    for i, u in enumerate(plan.get("ujecia", [])):
        wpis = {
            "ujecie": i,
            "start_s": round(u["klatka_od"] / fps, 3),
            "koniec_s": round((u["klatka_od"] + u["liczba_klatek"]) / fps, 3),
            "typ": u["typ"],
            "material": numery.get(str(u["material"])),
            "efekt": u.get("efekt_scenariusza"),
        }
        if u["typ"] == "klip":
            wpis["od_s"] = round(float(u.get("start_w_klipie_s", 0.0)), 3)
        if u.get("kolaz_scenariusza"):
            wpis["kolaz"] = list(u["kolaz_scenariusza"])
        ujecia.append(wpis)
    if plansza_uzyta and ujecia:
        ujecia[-1]["plansza"] = True
    opis = {
        "fps": fps,
        "dlugosc_klatek": plan["liczba_klatek"],
        "ujecia": ujecia,
        "materialy": lista_materialow(materialy or [], wycinki or []),
    }
    return json.dumps(opis, ensure_ascii=False)


POLECENIE_KRYTYKA = (
    "Jesteś krytykiem gotowego edytu 9:16 na TikToka dla marki czapek 1993 Supply. Dostajesz arkusz "
    "klatek, 2 na sekundę, w tej samej skali czasu dla wyniku i wzoru: w każdej parze wierszy górny wiersz "
    "z podpisem WYNIK to oceniany edit, a dolny z podpisem WZOR to wzór. Wzór pokazuje tylko strukturę i "
    "styl, jego obraz i dźwięk nie trafiają do wyniku, więc nie oceniaj podobieństwa treści, tylko rytm, "
    "dynamikę i jakość wyboru materiałów. Sprawdź zwłaszcza, czy otwarcie przyciąga, czy klipy mają ruch "
    "w kadrze, czy materiały się nie powtarzają i czy posągi oraz inne wycinki leżą na spokojnym tle "
    "(niebo, pejzaż, flaga, mur), a nie na twarzach, tłumie albo ruchliwej ulicy.\n"
    "Dane podają listę ujęć wyniku (czas w edicie start_s i koniec_s, typ, numer materiału, początek "
    "fragmentu klipu od_s, efekty, kolaż, plansza) i listę materiałów z numerami, typami i długością klipów.\n"
    "Oceń wynik w skali 1 do 10, wypisz do 3 mocnych stron i listę poprawek (najwyżej po jednej na "
    "problem): numer ujęcia z listy, opis problemu i nowe ujęcie zgodne ze schematem Ujecie. W zmianie "
    "podaj numer zdjęcia albo klipu z listy materiałów (numery wycinków tylko w polu kolaz), a dla klipu "
    "od_s tak, żeby fragment o długości ujęcia zmieścił się w klipie. Poprawka zachowuje czas ujęcia "
    "w edicie, więc pole uderzenia nie zmienia jego długości. Ujęcia z planszą nie poprawiaj.\n"
    "Zwróć wyłącznie JSON zgodny z podanym schematem."
)
