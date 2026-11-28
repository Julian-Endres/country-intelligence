"""
laender.py — zentrale Länderzuordnung für alle Loader (CI-177, Entwurf 24./25.11.2026)
=======================================================================================

Ersetzt die kopierten Fassungen in load_ghi.py, load_polity5.py und load_hofstede.py
(norm(), OVERRIDES_ISO3, COW-Listen) und die unscharfen Wege der 17 gesperrten Loader (CI-172).

Regeln (Entwurf aus CI-172, wird nach dem Pilot FH/HENLEY in PIPELINE_STANDARD P9 festgeschrieben)
---------------------------------------------------------------------------------------------------
1. Code vor Name: Bringt die Quelle ISO3, ISO2, M49, COW oder GW mit, gilt der Code
   (Zuordnung(..., art="iso3") usw.).
2. Namen nur exakt nach Normalisierung (Kleinschreibung, Akzente, & → and, Apostrophe,
   Leerraum) gegen countries.name – oder über die Liste der Quelle.
3. Entschieden wird je Quelle und Rohwert: Die Liste der Quelle hat immer Vorrang, auch vor
   einem exakten Treffer.
4. Liste je Quelle: scripts/pipeline/lib/laender/QUELLE.csv
   Spalten: schluessel, name_quelle, iso3, aktion, grund, von, bis, beleg
   - aktion = zuordnen (iso3 Pflicht) oder verwerfen (grund Pflicht, iso3 leer)
   - von/bis = Jahre (einschließlich), leer = offen. Gilt für zuordnen und verwerfen.
5. Verwerfen nur mit Grund (und known_issue, das legt die Migration an). Wir summieren und
   teilen nie selbst auf.
6. Unbekannter Schlüssel → Abbruch mit vollständiger Namensliste (alle auf einmal, nicht nur
   der erste). Die Fehlermeldung nennt Vorschläge (difflib) – NUR als Hilfe beim Ausfüllen der
   Liste, nie als Ladeweg.
7. Eins zu eins je Jahr: Landen zwei verschiedene Rohwerte im selben Jahr auf demselben Land,
   bricht pruefe_eindeutig() ab (hätte Niger/Nigeria sofort gezeigt).
8. Keine Fuzzy-Suche, keine Pakete (pycountry, countrycode), keine Teilstrings im Ladeweg.

Benutzung im Loader
-------------------
    import sys; sys.path.insert(0, str(REPO / "scripts" / "pipeline"))
    from lib.laender import Zuordnung, LaenderFehler

    z = Zuordnung.aus_db(cur, quelle="FH", art="name")
    z.pruefe_alle([(name, jahr) for ...])     # Abbruch mit Liste, falls etwas fehlt
    iso = z.iso_numeric(name, jahr)            # None = laut Liste verworfen
    z.pruefe_eindeutig()                       # nach dem Parsen: eins zu eins je Jahr
    log.info(z.bericht_text())                 # Wege und Verworfenes, namentlich

Prüfen einer Liste ohne Loader (Shell, Repo-Wurzel, venv aktiv; liest nur):
    python scripts/pipeline/lib/laender.py FH
"""

from __future__ import annotations

import csv
import difflib
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

LISTEN_ORDNER = Path(__file__).resolve().parent / "laender"
SPALTEN = ["schluessel", "name_quelle", "iso3", "aktion", "grund", "von", "bis", "beleg"]
ARTEN = {"name", "iso3", "iso2", "m49", "cow", "gw"}


class LaenderFehler(Exception):
    """Zuordnung unvollständig oder widersprüchlich. Der Loader schreibt dann nichts."""


def norm(name) -> str:
    """Kleinbuchstaben, ohne Akzente, & → and, typografische Apostrophe vereinheitlicht,
    Leerraum zusammengefasst. Wie load_ghi.py (15.11.), aber mit korrigierter Apostroph-Reihenfolge."""
    # Apostrophe VOR dem ASCII-Schritt vereinheitlichen, sonst fällt ’ ersatzlos weg
    # („Côte d’Ivoire“ → „cote divoire“). Die Fassung in load_ghi.py hat diesen Fehler.
    s = str(name)
    for zeichen in ("’", "‘", "`", "´"):
        s = s.replace(zeichen, "'")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("&", "and").lower()
    return " ".join(s.split())


def _schluessel(wert, art: str) -> str:
    """Schlüssel in Vergleichsform: Namen normalisiert, Buchstabencodes groß, Zahlcodes ohne
    führende Nullen und ohne '.0' (Excel liefert 2.0 statt 2)."""
    if art == "name":
        return norm(wert)
    s = str(wert).strip()
    if art in ("iso3", "iso2"):
        return s.upper()
    if s.endswith(".0"):
        s = s[:-2]
    if not s.isdigit():
        raise LaenderFehler(f"Schlüssel {wert!r} ist kein Zahlcode (art={art})")
    return str(int(s))


@dataclass(frozen=True)
class Eintrag:
    schluessel: str        # in Vergleichsform
    roh: str               # wie in der CSV
    iso3: str | None
    aktion: str            # zuordnen | verwerfen
    grund: str
    von: int | None
    bis: int | None
    beleg: str
    zeile: int

    def gilt(self, jahr: int | None) -> bool:
        if jahr is None:
            # Ohne Jahr (z. B. time_period 'static') gilt nur ein Eintrag ohne Zeitgrenzen.
            return self.von is None and self.bis is None
        return (self.von is None or jahr >= self.von) and (self.bis is None or jahr <= self.bis)


def lade_liste(quelle: str, art: str, ordner: Path = LISTEN_ORDNER) -> list[Eintrag]:
    """Liest scripts/pipeline/lib/laender/QUELLE.csv. Fehlt die Datei, gilt eine leere Liste
    (dann nur Code bzw. exakter Name). Formfehler → Abbruch mit Zeilennummer."""
    pfad = ordner / f"{quelle}.csv"
    if not pfad.exists():
        return []
    fehler, out = [], []
    with pfad.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if r.fieldnames != SPALTEN:
            raise LaenderFehler(f"{pfad.name}: Kopfzeile {r.fieldnames} ≠ {SPALTEN}")
        for nr, z in enumerate(r, start=2):
            z = {k: (v or "").strip() for k, v in z.items()}
            aktion = z["aktion"]
            if aktion not in ("zuordnen", "verwerfen"):
                fehler.append(f"Z. {nr}: aktion {aktion!r} (erlaubt: zuordnen, verwerfen)")
                continue
            if aktion == "zuordnen" and not z["iso3"]:
                fehler.append(f"Z. {nr}: zuordnen ohne iso3 ({z['schluessel']!r})")
            if aktion == "verwerfen" and z["iso3"]:
                fehler.append(f"Z. {nr}: verwerfen mit iso3 ({z['schluessel']!r}) – entweder oder")
            if aktion == "verwerfen" and not z["grund"]:
                fehler.append(f"Z. {nr}: verwerfen ohne grund ({z['schluessel']!r})")
            try:
                von = int(z["von"]) if z["von"] else None
                bis = int(z["bis"]) if z["bis"] else None
            except ValueError:
                fehler.append(f"Z. {nr}: von/bis keine Jahreszahl ({z['von']!r}, {z['bis']!r})")
                continue
            if von is not None and bis is not None and von > bis:
                fehler.append(f"Z. {nr}: von {von} > bis {bis}")
            try:
                key = _schluessel(z["schluessel"], art)
            except LaenderFehler as e:
                fehler.append(f"Z. {nr}: {e}")
                continue
            out.append(Eintrag(key, z["schluessel"], z["iso3"].upper() or None, aktion,
                               z["grund"], von, bis, z["beleg"], nr))
    # Überlappende Zeiträume für denselben Schlüssel sind ein Widerspruch.
    je_key = defaultdict(list)
    for e in out:
        je_key[e.schluessel].append(e)
    for key, liste in je_key.items():
        for i, a in enumerate(liste):
            for b in liste[i + 1:]:
                a_von, a_bis = a.von if a.von is not None else -10**9, a.bis if a.bis is not None else 10**9
                b_von, b_bis = b.von if b.von is not None else -10**9, b.bis if b.bis is not None else 10**9
                if a_von <= b_bis and b_von <= a_bis:
                    fehler.append(f"Z. {a.zeile} und {b.zeile}: Zeiträume für {a.roh!r} überlappen")
    if fehler:
        raise LaenderFehler(f"{pfad.name}: {len(fehler)} Formfehler:\n  " + "\n  ".join(fehler))
    return out


class Zuordnung:
    """Zuordnung Rohwert (+ Jahr) → iso_numeric für genau eine Quelle und eine Schlüsselart."""

    def __init__(self, quelle: str, art: str, laender: list[dict], ordner: Path = LISTEN_ORDNER):
        if art not in ARTEN:
            raise LaenderFehler(f"art {art!r} unbekannt (erlaubt: {sorted(ARTEN)})")
        self.quelle, self.art = quelle, art
        self.liste = lade_liste(quelle, art, ordner)
        self._iso3 = {l["iso_code_3"].strip().upper(): l["iso_numeric"] for l in laender}
        self._name_von_iso = {l["iso_numeric"]: l["name"] for l in laender}
        self._index = self._baue_index(laender, art)
        # Liste gegen countries prüfen
        unbekannt = sorted({e.iso3 for e in self.liste if e.iso3 and e.iso3 not in self._iso3})
        if unbekannt:
            raise LaenderFehler(f"{quelle}.csv nennt ISO3, die nicht in countries stehen: {unbekannt}")
        self._liste_je_key = defaultdict(list)
        for e in self.liste:
            self._liste_je_key[e.schluessel].append(e)
        self.wege = Counter()                         # Weg → Anzahl Aufrufe
        self.verworfen = Counter()                    # (roh, grund) → Anzahl
        self._treffer = defaultdict(set)              # (iso, jahr) → {Rohschlüssel}
        self._benutzt = set()                         # Listenzeilen, die gegriffen haben

    # ── Aufbau ──────────────────────────────────────────────────────────────

    @staticmethod
    def _baue_index(laender: list[dict], art: str) -> dict:
        spalte = {"name": "name", "iso3": "iso_code_3", "iso2": "iso_code_2",
                  "m49": "iso_numeric", "cow": "cow_code", "gw": "gw_code"}[art]
        index, doppelt = {}, defaultdict(list)
        for l in laender:
            v = l.get(spalte)
            if v is None or str(v).strip() == "":
                continue
            key = _schluessel(v, art)
            if key in index and index[key] != l["iso_numeric"]:
                doppelt[key] += [index[key], l["iso_numeric"]]
            index[key] = l["iso_numeric"]
        if doppelt:
            # Z. B. ein COW-Code für zwei Länder: dann darf dieser Weg nicht automatisch greifen.
            for key in doppelt:
                del index[key]
        return index

    @classmethod
    def aus_db(cls, cur, quelle: str, art: str, ordner: Path = LISTEN_ORDNER) -> "Zuordnung":
        cur.execute("""SELECT iso_numeric, iso_code_3, iso_code_2, name, cow_code, gw_code
                       FROM countries""")
        spalten = [d[0] for d in cur.description]
        laender = [dict(zip(spalten, r)) for r in cur.fetchall()]
        if not laender:
            raise LaenderFehler("countries ist leer")
        return cls(quelle, art, laender, ordner)

    # ── Zuordnen ────────────────────────────────────────────────────────────

    def _finde(self, roh, jahr: int | None):
        """→ (weg, iso_numeric | None, eintrag | None). weg = None heißt unbekannt."""
        key = _schluessel(roh, self.art)
        kandidaten = self._liste_je_key.get(key, [])
        if kandidaten:
            passend = [e for e in kandidaten if e.gilt(jahr)]
            if len(passend) == 1:
                e = passend[0]
                if e.aktion == "verwerfen":
                    return "liste_verwerfen", None, e
                return "liste", self._iso3[e.iso3], e
            # Schlüssel steht in der Liste, aber nicht für dieses Jahr: bewusst KEIN Rückfall
            # auf den exakten Namen – die Liste ist für diesen Rohwert zuständig.
            return None, None, None
        if key in self._index:
            return ("code" if self.art != "name" else "name_exakt"), self._index[key], None
        return None, None, None

    def iso_numeric(self, roh, jahr: int | None = None):
        """iso_numeric oder None (laut Liste verworfen). Unbekannt → LaenderFehler.
        Merkt sich jeden Treffer für pruefe_eindeutig()."""
        weg, iso, e = self._finde(roh, jahr)
        if weg is None:
            raise LaenderFehler(self._unbekannt_text([(roh, jahr)]))
        self.wege[weg] += 1
        if e is not None:
            self._benutzt.add(e.zeile)
        if iso is None:
            self.verworfen[(str(roh), e.grund)] += 1
            return None
        self._treffer[(iso, jahr)].add(str(roh))
        return iso

    def pruefe_alle(self, paare) -> None:
        """Vorab alle (roh, jahr)-Paare prüfen; Abbruch mit VOLLSTÄNDIGER Liste der
        unbekannten Rohwerte. Zählt nichts (das macht iso_numeric beim eigentlichen Lauf)."""
        fehlend = []
        gesehen = set()
        for roh, jahr in paare:
            if (str(roh), jahr) in gesehen:
                continue
            gesehen.add((str(roh), jahr))
            if self._finde(roh, jahr)[0] is None:
                fehlend.append((roh, jahr))
        if fehlend:
            raise LaenderFehler(self._unbekannt_text(fehlend))

    def pruefe_eindeutig(self) -> None:
        """Eins zu eins je Jahr: ein Land darf je Jahr nur aus EINEM Rohwert kommen."""
        konflikte = {k: v for k, v in self._treffer.items() if len(v) > 1}
        if konflikte:
            zeilen = [f"{self._name_von_iso.get(iso, iso)} ({iso}) {jahr}: {sorted(v)}"
                      for (iso, jahr), v in sorted(konflikte.items(), key=lambda x: (x[0][0], str(x[0][1])))]
            raise LaenderFehler(f"{self.quelle}: {len(konflikte)} Land-Jahre aus mehreren Rohwerten "
                                f"(eins zu eins verletzt):\n  " + "\n  ".join(zeilen[:40]))

    # ── Berichte ────────────────────────────────────────────────────────────

    def _vorschlag(self, roh) -> str:
        """Nur Hilfe für die Liste, nie Ladeweg."""
        if self.art != "name":
            return ""
        namen = {norm(n): (n, iso) for iso, n in self._name_von_iso.items()}
        treffer = difflib.get_close_matches(norm(roh), list(namen), n=3, cutoff=0.6)
        iso3_von_num = {v: k for k, v in self._iso3.items()}
        return ", ".join(f"{namen[t][0]} ({iso3_von_num[namen[t][1]]})" for t in treffer)

    def _unbekannt_text(self, fehlend) -> str:
        je_roh = defaultdict(list)
        for roh, jahr in fehlend:
            je_roh[str(roh)].append(jahr)
        zeilen = []
        for roh, jahre in sorted(je_roh.items()):
            js = sorted(j for j in jahre if j is not None)
            spanne = f" (Jahre {js[0]}–{js[-1]})" if js else ""
            in_liste = " – steht in der Liste, aber nicht für diese Jahre" if _schluessel(roh, self.art) in self._liste_je_key else ""
            vor = self._vorschlag(roh)
            zeilen.append(f"{roh!r}{spanne}{in_liste}" + (f"   Vorschlag (nur Hilfe): {vor}" if vor else ""))
        return (f"{self.quelle}: {len(je_roh)} Rohwerte nicht zugeordnet. "
                f"Liste scripts/pipeline/lib/laender/{self.quelle}.csv ergänzen:\n  " + "\n  ".join(zeilen))

    def ungenutzte_listenzeilen(self) -> list[Eintrag]:
        """Listenzeilen, die in diesem Lauf nie gegriffen haben (Tippfehler im Schlüssel?)."""
        return [e for e in self.liste if e.zeile not in self._benutzt]

    def bericht_text(self) -> str:
        teile = [f"Länder {self.quelle}: Wege {dict(sorted(self.wege.items()))}"]
        if self.verworfen:
            teile.append("verworfen: " + "; ".join(f"{r} ×{n} ({g})" for (r, g), n in sorted(self.verworfen.items())))
        ungenutzt = self.ungenutzte_listenzeilen()
        if ungenutzt:
            teile.append("Listenzeilen ohne Treffer: " + ", ".join(f"Z. {e.zeile} {e.roh!r}" for e in ungenutzt))
        laender = {iso for iso, _ in self._treffer}
        teile.append(f"Länder zugeordnet: {len(laender)}")
        return " · ".join(teile)


# ── Kommandozeile: Liste einer Quelle prüfen (liest nur) ───────────────────────

def _main():
    import argparse
    import os
    ap = argparse.ArgumentParser(description="Länderliste einer Quelle gegen countries prüfen (liest nur).")
    ap.add_argument("quelle")
    ap.add_argument("--art", default="name", choices=sorted(ARTEN))
    args = ap.parse_args()
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    conn = psycopg2.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
                            database=os.getenv("DB_NAME", "country_intelligence"),
                            user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"))
    try:
        z = Zuordnung.aus_db(conn.cursor(), args.quelle, args.art)
        n_v = sum(1 for e in z.liste if e.aktion == "verwerfen")
        print(f"{args.quelle}.csv: {len(z.liste)} Zeilen ({len(z.liste) - n_v} zuordnen, {n_v} verwerfen), "
              f"alle ISO3 in countries, keine Formfehler.")
    except LaenderFehler as e:
        print(f"FEHLER: {e}")
        raise SystemExit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    _main()
