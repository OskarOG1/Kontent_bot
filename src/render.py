import analyze


def znajdz_start_uderzenia(c0: float, uderzenia: list[float]) -> int:
    s = 0
    if analyze.czas_z_pozycji(s + c0, uderzenia) >= 0:
        while analyze.czas_z_pozycji((s - 1) + c0, uderzenia) >= 0:
            s -= 1
        return s
    while analyze.czas_z_pozycji(s + c0, uderzenia) < 0:
        s += 1
    return s


def wstawki(materialy: list[dict], dlugosc_wstawki_s: float, minimum_s: float = 0.3) -> list[dict]:
    kolejki = []
    for material in materialy:
        if material["typ"] != "klip":
            kolejki.append([dict(material)])
            continue
        czas_s = material["czas_s"]
        kawalki = []
        indeks = 0
        while True:
            start = round(indeks * dlugosc_wstawki_s, 6)
            if start >= czas_s:
                break
            koniec = min(start + dlugosc_wstawki_s, czas_s)
            dlugosc = round(koniec - start, 6)
            if kawalki and dlugosc < minimum_s:
                kawalki[-1]["czas_s"] = round(kawalki[-1]["czas_s"] + dlugosc, 6)
            else:
                kawalki.append({
                    "plik": material["plik"],
                    "typ": "klip",
                    "message_id": material["message_id"],
                    "czas_s": dlugosc,
                    "od_s": start,
                })
            indeks += 1
        kolejki.append(kawalki)
    wynik = []
    maks_dlugosc = max((len(kolejka) for kolejka in kolejki), default=0)
    for i in range(maks_dlugosc):
        for kolejka in kolejki:
            if i < len(kolejka):
                wynik.append(kolejka[i])
    return wynik


def plan_ujec(
    wzor: dict,
    uderzenia_utworu: list[float],
    materialy: list[dict],
    fps: int,
    start_uderzenie: int | None = None,
) -> dict:
    ciecia_uderzenia = wzor.get("ciecia_uderzenia") or []
    if ciecia_uderzenia and len(uderzenia_utworu) >= 2:
        c0 = ciecia_uderzenia[0]
        s = start_uderzenie if start_uderzenie is not None else znajdz_start_uderzenia(c0, uderzenia_utworu)
        pozycje = list(ciecia_uderzenia) + [wzor["koniec_uderzenia"]]
        czasy = [analyze.czas_z_pozycji(s + p, uderzenia_utworu) for p in pozycje]
    else:
        czasy = list(wzor["ciecia_s"]) + [wzor["zrodlo"]["czas_s"]]

    start_audio_s = czasy[0]
    liczba_klatek = round((czasy[-1] - czasy[0]) * fps)
    if liczba_klatek <= 0:
        raise ValueError("Utwór za krótki na całe okno wzoru")

    granice = [round((t - czasy[0]) * fps) for t in czasy]
    ujecia = []
    for k in range(len(granice) - 1):
        klatka_od = granice[k]
        dlugosc = granice[k + 1] - klatka_od
        if dlugosc <= 0:
            continue
        kawalek = materialy[k % len(materialy)]
        ujecia.append({
            "material": str(kawalek["plik"]),
            "typ": kawalek["typ"],
            "klatka_od": klatka_od,
            "liczba_klatek": dlugosc,
            "start_w_klipie_s": kawalek["od_s"] if kawalek["typ"] == "klip" else 0.0,
        })

    return {
        "fps": fps,
        "start_audio_s": round(start_audio_s, 6),
        "liczba_klatek": liczba_klatek,
        "ujecia": ujecia,
    }
