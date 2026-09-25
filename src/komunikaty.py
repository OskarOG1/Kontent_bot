import re
from pathlib import Path

POMOC = (
    "Cześć! Montuję edity wideo 9:16 według Twojego wzoru.\n"
    "/wzor, żeby wysłać nowy wzorcowy edit.\n"
    "/nakladka, żeby ustawić nakładkę graficzną od dropu (/nakladka usun, żeby ją usunąć).\n"
    "/plansza, żeby ustawić planszę końcową (/plansza usun, żeby ją usunąć).\n"
    "/znak, żeby ustawić znak wodny marki (/znak usun, żeby go usunąć).\n"
    "/nowy, żeby zacząć zbierać materiały do nowego editu.\n"
    "Zwykła wiadomość tekstowa w trakcie zbierania to linia napisu w haku editu.\n"
    "/slowa, żeby ustawić słowa w rytmie na dropie (/slowa bez tekstu, żeby je wyczyścić).\n"
    "/pionowo, żeby ustawić pionowy napis pisany literami (/pionowo bez tekstu, żeby go wyczyścić).\n"
    "/gotowe, żeby zamknąć zbieranie i wysłać projekt do kolejki.\n"
    "/anuluj, żeby porzucić bieżący projekt.\n"
    "/status, żeby sprawdzić stan bota."
)

KOMENDY = (
    ("start", "Pomoc i lista komend"),
    ("wzor", "Wyślij nowy wzorcowy edit"),
    ("nakladka", "Ustaw nakładkę graficzną wzoru"),
    ("plansza", "Ustaw planszę końcową wzoru"),
    ("znak", "Ustaw znak wodny marki"),
    ("nowy", "Zacznij nowy projekt"),
    ("slowa", "Ustaw słowa w rytmie na dropie"),
    ("pionowo", "Ustaw pionowy napis pisany literami"),
    ("gotowe", "Zamknij zbieranie i wyślij do kolejki"),
    ("anuluj", "Porzuć bieżący projekt"),
    ("status", "Sprawdź stan bota"),
)

WZOR_PROSBA = "Wyślij wideo, które ma być wzorem."
ANALIZA_PRZEKROCZONO_CZAS = "Analiza wzoru trwała zbyt długo i została przerwana. Plik wzoru został zapisany."
WZOR_NIEPOPRAWNY_TYP = "To nie jest wideo. Wyślij plik wideo jako wzór."

NOWY_PROJEKT = "Nowy projekt. Wysyłaj zdjęcia, klipy i teksty, na koniec /gotowe."

BRAK_STANU = "Najpierw użyj /nowy albo /wzor."

BRAK_MATERIALOW = "Nie masz jeszcze żadnych materiałów. Wyślij zdjęcia albo klipy, potem /gotowe."

BLAD_POBIERANIA = "Nie udało się pobrać pliku. Spróbuj wysłać go jeszcze raz."

PROJEKT_ANULOWANY = "Projekt anulowany."

STATUS_BRAK_PROJEKTU = "Nie zbierasz teraz żadnego projektu."

BRAK_WZORU = "Najpierw wyślij wzór przez /wzor."

BRAK_MUZYKI = "Biblioteka muzyki jest pusta. Dodaj utwory do dane/muzyka."

MATERIAL_NIEPOPRAWNY_TYP = "Nie rozpoznaję tego typu pliku. Wyślij zdjęcie albo klip."

MONTUJE = "Montuję."

BLAD_WYSYLKI = "Nie udało się wysłać wyniku. Spróbuj ponownie /gotowe."

NAKLADKA_WYSLIJ_JAKO_PLIK = "Zdjęcie albo wideo wysłane nie jako plik traci przezroczystość. Wyślij nakładkę jako plik."
NAKLADKA_NIEPOPRAWNY_TYP = "Nieobsługiwany format nakładki. Wyślij webm, mov, png, gif albo mp4."
NAKLADKA_USUNIETA = "Nakładka usunięta."

PLANSZA_NIEPOPRAWNY_TYP = "Nie rozpoznaję tego typu pliku. Wyślij zdjęcie albo klip jako planszę."
PLANSZA_USUNIETA = "Plansza usunięta."
PLANSZA_ZAPISANA = "Plansza zapisana."

ZNAK_PROSBA = "Wyślij znak wodny jako plik PNG."
ZNAK_NIEPOPRAWNY_TYP = "To nie jest PNG. Wyślij znak wodny jako plik PNG."
ZNAK_USUNIETY = "Znak wodny usunięty."
ZNAK_ZAPISANY = "Znak wodny zapisany."

SLOWA_WYCZYSZCZONE = "Słowa w rytmie wyczyszczone."


def slowa_zapisane(liczba: int) -> str:
    return f"Słowa w rytmie: {liczba}, ostatnie wchodzi na dropie."


def slowa_za_duzo(liczba: int, limit: int) -> str:
    return f"Za dużo słów ({liczba}), limit to {limit}. Nic nie zapisano."


PIONOWO_WYCZYSZCZONY = "Napis pionowy wyczyszczony."


def pionowo_zapisany(tresc: str) -> str:
    return f"Napis pionowy zapisany: {tresc}"


def pionowo_za_dlugi(liczba: int, limit: int) -> str:
    return f"Za długi napis pionowy ({liczba} znaków), limit to {limit}. Nic nie zapisano."


def nakladka_prosba(wzor_id: str) -> str:
    return (
        "Wyślij nakładkę jako plik: webm albo mov z przezroczystością, png, albo mp4 na zielonym lub czarnym tle, "
        "albo dowolny inny mp4, który dostanie krycie 50%. "
        f"Będzie użyta dla wzoru {wzor_id}."
    )


def nakladka_zapisana(tryb: str) -> str:
    opisy = {"alfa": "przezroczystość", "zielen": "zielone tło", "ekran": "czarne tło", "krycie": "krycie 50%"}
    return f"Nakładka zapisana: {opisy.get(tryb, tryb)}."


def plansza_prosba(wzor_id: str) -> str:
    return f"Wyślij planszę końcową jako zdjęcie albo klip. Będzie użyta dla wzoru {wzor_id}."


def status_zasobow_wzoru(wzor_id: str, ma_nakladke: bool, ma_plansze: bool) -> str:
    nakladka = "tak" if ma_nakladke else "nie"
    plansza = "tak" if ma_plansze else "nie"
    return f"Wzór {wzor_id}: nakładka {nakladka}, plansza {plansza}."


def formatuj_mb(wartosc: float) -> str:
    return f"{wartosc:.1f}".replace(".", ",")


def limit_rozmiaru(rozmiar_bajty: int | None, limit_mb: int) -> str:
    if rozmiar_bajty is None:
        return f"Plik jest za duży. Limit pobierania to {limit_mb} MB."
    rozmiar_mb = rozmiar_bajty / (1024 * 1024)
    return f"Plik ma {formatuj_mb(rozmiar_mb)} MB, limit pobierania to {limit_mb} MB."


def formatuj_liczbe(wartosc: float, miejsca: int) -> str:
    return f"{wartosc:.{miejsca}f}".replace(".", ",")


def analizuje_wzor(pozycja: int) -> str:
    if pozycja > 1:
        return f"Analizuję wzór. Pozycja w kolejce: {pozycja}."
    return "Analizuję wzór."


def blad_analizy(opis: str) -> str:
    return f"Analiza wzoru nie powiodła się: {opis}"


def linia_dropu(sekcje: dict | None) -> str:
    if not sekcje or sekcje.get("drop_ujecie") is None:
        return "bez dropu"
    return f"drop w {formatuj_liczbe(sekcje['drop_s'], 1)} s (ujęcie {sekcje['drop_ujecie']})"


def podsumowanie_wzoru(
    czas_s: float, liczba_ujec: int, srednia_s: float, tempo_bpm: float | None, ma_dzwiek: bool, sekcje: dict | None = None,
) -> str:
    if not ma_dzwiek:
        rytm = "brak dźwięku, więc bez tempa"
    elif tempo_bpm is None:
        rytm = "nie wykryto tempa"
    else:
        rytm = f"tempo {formatuj_liczbe(tempo_bpm, 1)} BPM"
    return (
        f"Wzór przeanalizowany: {formatuj_liczbe(czas_s, 1)} s, ujęć {liczba_ujec}, "
        f"średnia długość ujęcia {formatuj_liczbe(srednia_s, 2)} s, {rytm}, {linia_dropu(sekcje)}."
    )


def projekt_w_kolejce(zdjecia: int, klipy: int, linie: int, pozycja: int) -> str:
    baza = f"Projekt w kolejce: zdjęcia {zdjecia}, klipy {klipy}, linie tekstu {linie}."
    if pozycja > 1:
        return f"{baza} Pozycja w kolejce: {pozycja}."
    return baza


def blad_renderu(opis: str) -> str:
    return f"Montaż nie powiódł się: {opis}"


def linia_muzyki(dane_utworu: dict) -> str:
    nazwa = Path(dane_utworu["plik"]).stem
    tryb = dane_utworu.get("tryb")
    if tryb == "dzwiek_wzoru":
        return f"Muzyka: {nazwa}, dźwięk wzoru od {formatuj_liczbe(dane_utworu['start_s'], 1)} s."
    if tryb == "tempo":
        return f"Muzyka: {nazwa}, dobór po tempie {formatuj_liczbe(dane_utworu['tempo_bpm'], 1)} BPM, od {formatuj_liczbe(dane_utworu['start_s'], 1)} s."
    return f"Muzyka: {nazwa}, od początku."


def linia_tekstow(dane_tekstow: dict | None) -> str | None:
    if not dane_tekstow:
        return None
    linie = dane_tekstow.get("linie", 0)
    usuniete = dane_tekstow.get("usuniete_znaki", 0)
    if not linie and not usuniete:
        return None
    czesci = []
    if linie:
        czesci.append(f"Napisy: {linie}.")
    if usuniete:
        czesci.append(f"Usunięte znaki bez czcionki: {usuniete} (np. emoji).")
    return " ".join(czesci)


def wyciagnij_liczbe(komunikat: str) -> str:
    dopasowanie = re.search(r"(\d+)\s*$", komunikat)
    return dopasowanie.group(1) if dopasowanie else "0"


def linia_slow_pominietych(dane_slow: dict | None) -> str | None:
    if not dane_slow or "pominiete" not in dane_slow:
        return None
    liczba = wyciagnij_liczbe(dane_slow["pominiete"])
    return f"Słowa w rytmie pominięte: w haku tego wzoru mieści się najwyżej {liczba} słów."


def linia_pionowego_pominietego(dane_pionowo: dict | None) -> str | None:
    if not dane_pionowo or "pominiety" not in dane_pionowo:
        return None
    liczba = wyciagnij_liczbe(dane_pionowo["pominiety"])
    return f"Napis pionowy pominięty: w haku tego wzoru mieści się najwyżej {liczba} znaków."


def podsumowanie_renderu(dane: dict) -> str:
    liczba_pominietych = len(dane.get("materialy_pominiete", []))
    pierwsza_linia = (
        f"Gotowe: {formatuj_liczbe(dane['czas_s'], 1)} s, ujęć {dane['liczba_ujec']}, "
        f"materiałów użytych {dane['materialy_uzyte']}, pominiętych {liczba_pominietych}, "
        f"czas renderu {formatuj_liczbe(dane['czas_renderu_s'], 1)} s."
    )
    linie = [pierwsza_linia, linia_muzyki(dane["utwor"])]
    tekst_napisow = linia_tekstow(dane.get("teksty"))
    if tekst_napisow:
        linie.append(tekst_napisow)
    linia_slow = linia_slow_pominietych(dane.get("slowa"))
    if linia_slow:
        linie.append(linia_slow)
    linia_pionowo = linia_pionowego_pominietego(dane.get("pionowo"))
    if linia_pionowo:
        linie.append(linia_pionowo)
    return "\n".join(linie)


def status_projektu(projekt_id: str, liczba_materialow: int, liczba_linii: int) -> str:
    return f"Projekt {projekt_id}, materiałów {liczba_materialow}, linii tekstu {liczba_linii}."


def status_kolejki(dlugosc_kolejki: int, liczba_wzorow: int) -> str:
    return f"Kolejka zadań: {dlugosc_kolejki}, wzorów zapisanych: {liczba_wzorow}."


def status_muzyki(liczba_utworow: int) -> str:
    return f"Muzyka: {liczba_utworow} utworów."


def status_znaku(ma_znak: bool) -> str:
    return f"Znak wodny: {'tak' if ma_znak else 'nie'}."
