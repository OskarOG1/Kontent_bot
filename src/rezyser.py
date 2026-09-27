import base64
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

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
            ostatni_powod = f"błąd sieci: {wyjatek}"
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
    tekst = str(numer)
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


def klatki_klipu(plik: Path, liczba_klatek: int, czas_s: float, kx: int, ky: int) -> list[np.ndarray]:
    czas_s = max(czas_s, 1.0 / 30)
    fps = liczba_klatek / czas_s
    filtr = f"fps={fps:.10f},scale={kx}:{ky}:force_original_aspect_ratio=increase,crop={kx}:{ky}"
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


def arkusze_materialow(materialy: list[dict], wycinki: list[dict], katalog_pracy: Path) -> list[Path]:
    katalog_pracy = Path(katalog_pracy)
    katalog_pracy.mkdir(parents=True, exist_ok=True)
    sciezki = []

    kx, ky = KOMORKA_ZDJECIA
    zdjecia = [(numer, material) for numer, material in enumerate(materialy) if material["typ"] == "zdjecie"]
    if zdjecia:
        pozycje = []
        for numer, material in zdjecia:
            zrodlo = material.get("plik_roboczy", material["plik"])
            obraz = cv2.imread(str(zrodlo))
            if obraz is None:
                obraz = np.full((ky, kx, 3), 64, dtype=np.uint8)
            pozycje.append((numer, obraz))
        siatka = siatka_ponumerowana(pozycje, kx, ky, KOLUMNY_ZDJEC)
        siatka = ogranicz_bok(siatka, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / "arkusz_zdjecia.jpg"
        zapisz_jpeg(siatka, sciezka)
        sciezki.append(sciezka)

    kkx, kky = KOMORKA_KLATKI_KLIPU
    for numer, material in enumerate(materialy):
        if material["typ"] != "klip":
            continue
        czas_s = float(material.get("czas_s", 1.0))
        klatki = klatki_klipu(Path(material["plik"]), LICZBA_KLATEK_KLIPU, czas_s, kkx, kky)
        if not klatki:
            continue
        naglowek = np.full((24, kkx * len(klatki), 3), 32, dtype=np.uint8)
        cv2.putText(
            naglowek, f"klip {numer}, {czas_s:.1f} s", (4, 17),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA,
        )
        obraz = np.vstack([naglowek, np.hstack(klatki)])
        obraz = ogranicz_bok(obraz, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / f"arkusz_klip_{numer}.jpg"
        zapisz_jpeg(obraz, sciezka)
        sciezki.append(sciezka)

    if wycinki:
        wkx, wky = KOMORKA_WYCINKA
        pozycje = [(numer, wczytaj_z_alfa(Path(wycinek["plik"]), wkx, wky)) for numer, wycinek in enumerate(wycinki)]
        siatka = siatka_ponumerowana(pozycje, wkx, wky, KOLUMNY_WYCINKOW)
        siatka = ogranicz_bok(siatka, BOK_MAKSYMALNY_ARKUSZA)
        sciezka = katalog_pracy / "arkusz_wycinki.jpg"
        zapisz_jpeg(siatka, sciezka)
        sciezki.append(sciezka)

    return sciezki


def opis_wzoru(wzor: dict, plan: dict, uderzenia: list[int], materialy: list[dict], okna_tekstow: dict | None) -> str:
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
        "materialy": [
            {"numer": i, "typ": material["typ"]} if material["typ"] != "klip"
            else {"numer": i, "typ": "klip", "dlugosc_s": round(float(material.get("czas_s", 0.0)), 3)}
            for i, material in enumerate(materialy)
        ],
    }
    return json.dumps(opis, ensure_ascii=False)
