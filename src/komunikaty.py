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
WZOR_ZAPISANY = "Wzór zapisany."
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


def projekt_w_kolejce(zdjecia: int, klipy: int, linie: int) -> str:
    return f"Projekt w kolejce: zdjęcia {zdjecia}, klipy {klipy}, linie tekstu {linie}."


def status_projektu(projekt_id: str, liczba_materialow: int) -> str:
    return f"Projekt {projekt_id}, materiałów {liczba_materialow}."


def status_kolejki(dlugosc_kolejki: int, liczba_wzorow: int) -> str:
    return f"Kolejka zadań: {dlugosc_kolejki}, wzorów zapisanych: {liczba_wzorow}."
