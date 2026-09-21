import asyncio
import logging
import sys
import time
import uuid

import psutil
import pytest

import kolejka


async def test_uruchom_nie_blokuje_petli_zdarzen():
    zadanie = asyncio.create_task(
        kolejka.uruchom([sys.executable, "-c", "import time; time.sleep(2)"], limit_s=10)
    )
    opoznienia = []
    poprzedni = time.monotonic()
    while not zadanie.done():
        await asyncio.sleep(0.01)
        teraz = time.monotonic()
        opoznienia.append(teraz - poprzedni)
        poprzedni = teraz
    wynik = await zadanie
    assert wynik.przekroczono_czas is False
    assert max(opoznienia) < 0.1


async def test_uruchom_zabija_cale_drzewo_po_limicie():
    znacznik = f"znacznik_{uuid.uuid4().hex}"
    skrypt = (
        "import subprocess, sys;"
        f"znacznik = '{znacznik}';"
        "dziecko = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)', znacznik]);"
        "dziecko.wait()"
    )
    zadanie = asyncio.create_task(kolejka.uruchom([sys.executable, "-c", skrypt], limit_s=1))

    znalezione_pidy = set()
    while not zadanie.done():
        for proces in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = proces.info["cmdline"] or []
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if any(znacznik in czesc for czesc in cmdline):
                znalezione_pidy.add(proces.info["pid"])
        await asyncio.sleep(0.05)

    wynik = await zadanie
    assert wynik.przekroczono_czas is True
    assert znalezione_pidy

    await asyncio.sleep(0.3)
    for pid in znalezione_pidy:
        assert not psutil.pid_exists(pid)


async def test_uruchom_zamyka_stdin_dziecka():
    start = time.monotonic()
    wynik = await kolejka.uruchom([sys.executable, "-c", "import sys; sys.stdin.read()"], limit_s=10)
    czas = time.monotonic() - start
    assert wynik.przekroczono_czas is False
    assert czas < 3


async def test_kolejka_wyjatek_nie_zatrzymuje_pracownika(caplog):
    kol = kolejka.Kolejka()
    kol.start()
    wynik = {}

    async def psute_zadanie():
        raise ValueError("blad testowy")

    async def kolejne_zadanie():
        wynik["wykonano"] = True

    with caplog.at_level(logging.ERROR, logger="kolejka"):
        await kol.dodaj(psute_zadanie)
        await kol.dodaj(kolejne_zadanie)
        await asyncio.sleep(0.1)

    assert wynik.get("wykonano") is True
    assert "blad testowy" in caplog.text


async def test_kolejka_pozycje_i_jeden_pracownik():
    kol = kolejka.Kolejka()
    kol.start()
    aktywne = 0
    maks_aktywnych = 0
    kolejnosc = []

    async def wykonaj(numer):
        nonlocal aktywne, maks_aktywnych
        aktywne += 1
        maks_aktywnych = max(maks_aktywnych, aktywne)
        kolejnosc.append(numer)
        await asyncio.sleep(0.05)
        aktywne -= 1

    pozycje = []
    for numer in range(3):
        pozycja = await kol.dodaj((lambda numer=numer: wykonaj(numer)))
        pozycje.append(pozycja)

    await asyncio.sleep(0.3)

    assert pozycje == [1, 2, 3]
    assert maks_aktywnych == 1
    assert kolejnosc == [0, 1, 2]
