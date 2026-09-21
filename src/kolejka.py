import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

import psutil

log = logging.getLogger("kolejka")


@dataclass
class Wynik:
    kod: int | None
    stdout: str
    stderr: str
    czas_s: float
    przekroczono_czas: bool


async def uruchom(argumenty: list[str], limit_s: float | None = None, katalog: Path | None = None) -> Wynik:
    start = monotonic()
    proces = await asyncio.create_subprocess_exec(
        *argumenty,
        cwd=str(katalog) if katalog else None,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    przekroczono_czas = False
    stdout_bajty = b""
    stderr_bajty = b""
    try:
        stdout_bajty, stderr_bajty = await asyncio.wait_for(proces.communicate(), timeout=limit_s)
    except asyncio.TimeoutError:
        przekroczono_czas = True
        zabij_drzewo(proces.pid)
        await proces.wait()
    czas_s = monotonic() - start
    return Wynik(
        kod=proces.returncode,
        stdout=stdout_bajty.decode("utf-8", errors="replace"),
        stderr=stderr_bajty.decode("utf-8", errors="replace"),
        czas_s=czas_s,
        przekroczono_czas=przekroczono_czas,
    )


def zabij_drzewo(pid: int) -> None:
    try:
        rodzic = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    procesy = rodzic.children(recursive=True)
    procesy.append(rodzic)
    for proces in procesy:
        try:
            proces.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(procesy, timeout=5)


class Kolejka:
    def __init__(self) -> None:
        self._kolejka: asyncio.Queue = asyncio.Queue()
        self._dlugosc = 0
        self._zadanie_pracownika: asyncio.Task | None = None

    def start(self) -> None:
        if self._zadanie_pracownika is None:
            self._zadanie_pracownika = asyncio.create_task(self._pracownik())

    async def dodaj(self, zadanie) -> int:
        self._dlugosc += 1
        pozycja = self._dlugosc
        await self._kolejka.put(zadanie)
        return pozycja

    def dlugosc(self) -> int:
        return self._dlugosc

    async def _pracownik(self) -> None:
        while True:
            zadanie = await self._kolejka.get()
            try:
                await zadanie()
            except Exception:
                log.exception("zadanie w kolejce rzucilo wyjatek")
            finally:
                self._dlugosc -= 1
                self._kolejka.task_done()
