POMOC = (
    "Cześć! Montuję edity wideo 9:16 według Twojego wzoru.\n"
    "/wzor, żeby wysłać nowy wzorcowy edit.\n"
    "/nowy, żeby zacząć zbierać materiały do nowego editu.\n"
    "/gotowe, żeby zamknąć zbieranie i wysłać projekt do kolejki.\n"
    "/anuluj, żeby porzucić bieżący projekt.\n"
    "/status, żeby sprawdzić stan bota."
)

KOMENDY = (
    ("start", "Pomoc i lista komend"),
    ("wzor", "Wyślij nowy wzorcowy edit"),
    ("nowy", "Zacznij nowy projekt"),
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


def podsumowanie_wzoru(czas_s: float, liczba_ujec: int, srednia_s: float, tempo_bpm: float | None, ma_dzwiek: bool) -> str:
    if not ma_dzwiek:
        rytm = "brak dźwięku, więc bez tempa"
    elif tempo_bpm is None:
        rytm = "nie wykryto tempa"
    else:
        rytm = f"tempo {formatuj_liczbe(tempo_bpm, 1)} BPM"
    return (
        f"Wzór przeanalizowany: {formatuj_liczbe(czas_s, 1)} s, ujęć {liczba_ujec}, "
        f"średnia długość ujęcia {formatuj_liczbe(srednia_s, 2)} s, {rytm}."
    )


def projekt_w_kolejce(zdjecia: int, klipy: int, linie: int) -> str:
    return f"Projekt w kolejce: zdjęcia {zdjecia}, klipy {klipy}, linie tekstu {linie}."


def status_projektu(projekt_id: str, liczba_materialow: int) -> str:
    return f"Projekt {projekt_id}, materiałów {liczba_materialow}."


def status_kolejki(dlugosc_kolejki: int, liczba_wzorow: int) -> str:
    return f"Kolejka zadań: {dlugosc_kolejki}, wzorów zapisanych: {liczba_wzorow}."
