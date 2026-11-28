"""
load_freedom_house.py — Freedom in the World (Freedom House), Länder 1972–2024
==============================================================================
Quelle:  Freedom House, „Country and Territory Ratings and Statuses, 1973–2024"
Datei:   data/raw/governance/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx
         Blatt „Country Ratings, Statuses " (Gebiete im Blatt „Territory …" werden nicht geladen)
Ziel:    indicators, Codes FH:PR, FH:CL, FH:STATUS (source_id aus sources.short_code = 'FH')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/governance/load_freedom_house.py
      Trockenlauf (Standard): liest die Datei, prüft, vergleicht mit der DB, schreibt NICHTS
  python scripts/pipeline/governance/load_freedom_house.py --schreiben
      schreibt in die DB (alles oder nichts, eine Transaktion), frischt indicator_coverage auf
  Zusatz --ohne-1982-1989: die acht Ausgaben mit Berichtszeitraum statt Jahr weglassen (Altverhalten)

Regeln (Neufassung CI-177, Entwurf 25.11.2026; Pipeline-Standard Fall „Datei")
------------------------------------------------------------------------------
- Länder NUR über scripts/pipeline/lib/laender.py: exakter Name oder Liste
  scripts/pipeline/lib/laender/FH.csv. Unbekannter Name → Abbruch mit Namensliste.
  Der alte Loader nutzte pycountry.search_fuzzy: Niger → Nigeria, Kosovo → Serbien (CI-172).
- time_period = Jahr des Berichtszeitraums („Year(s) Under Review"), nicht die Ausgabe.
  Für die Ausgaben 1982 bis 1989-90 steht dort ein Zeitraum (z. B. „Aug.1982-Nov.1983").
  Sie werden mit dem Endjahr geladen (Empfehlung Claude, Julian: „umsetzen“ 24.11.); 1981 bleibt leer.
  Der alte Loader übersprang sie still (int() scheiterte, except: pass).
- Werte: PR und CL 1–7, Status F/PF/NF → FH:STATUS 1/2/3 (Entscheidung Julian 24.11., CI-63).
  "-" = keine Bewertung → kein Wert. Alles andere → Abbruch, außer den Einträgen in SONDERWERTE.
- Genau ein Wert je Land, Code und Jahr; ein Land je Jahr nur aus einem Rohnamen (laender.py).
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt: neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert, löscht der Loader NICHT, er meldet sie.
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "pipeline"))
from lib.laender import LaenderFehler, Zuordnung  # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fh")

RAW_FILE = REPO / "data" / "raw" / "governance" / "Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx"  # #135
SHEET = "Country Ratings, Statuses "
SOURCE_CODE = "FH"
CODES = ("FH:PR", "FH:CL", "FH:STATUS")
STATUS_WERT = {"F": 1.0, "PF": 2.0, "NF": 3.0}

# Ausgaben, deren „Year(s) Under Review" ein Zeitraum ist → Endjahr des Zeitraums.
# Empfehlung Claude, umgesetzt nach Julians „umsetzen“ (24.11.): Endjahr, weil die Bewertung den Stand am Ende des
# Zeitraums beschreibt. 1981 bleibt leer (die Ausgabe 1982 deckt Jan. 1981 bis Aug. 1982).
ZEITRAUM_JAHR = {
    "Jan.1981-Aug. 1982": 1982,
    "Aug.1982-Nov.1983": 1983,
    "Nov.1983-Nov.1984": 1984,
    "Nov.1984-Nov.1985": 1985,
    "Nov.1985-Nov.1986": 1986,
    "Nov.1986-Nov.1987": 1987,
    "Nov.1987-Nov.1988": 1988,
    "Nov.1988-Dec.1989": 1989,
}

# Ausdrücklich behandelte Nicht-Standardwerte: (Rohname, Jahr, Spalte, Rohwert) → Behandlung.
# Südafrika 1972: zwei Bewertungen (weiße / schwarze Bevölkerung), z. B. "2(5)". Wir teilen und
# wählen nicht selbst → verwerfen (wie bisher, damals still über except: pass).
SONDERWERTE = {
    ("South Africa", 1972, "PR", "2(5)"): "verwerfen",
    ("South Africa", 1972, "CL", "3(6)"): "verwerfen",
    ("South Africa", 1972, "Status", "F (NF)"): "verwerfen",
}


class LadeFehler(Exception):
    pass


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ─── Datei lesen und prüfen ───────────────────────────────────────────────────

def read_file(pfad: Path) -> tuple[pd.DataFrame, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    df = pd.read_excel(pfad, sheet_name=SHEET, header=None, engine="openpyxl")
    return df, sha


def spalten(df: pd.DataFrame, mit_zeitraum: bool) -> tuple[list, Counter]:
    """Kopf prüfen. → [(jahr, spalte_pr, spalte_cl, spalte_status)], Zählung übersprungener Ausgaben."""
    if str(df.iloc[0, 0]).strip() != "Survey Edition" or not str(df.iloc[1, 0]).startswith("Year(s) Under Review"):
        raise LadeFehler(f"Kopf unerwartet: {df.iloc[0, 0]!r} / {df.iloc[1, 0]!r}")
    if (df.shape[1] - 1) % 3:
        raise LadeFehler(f"{df.shape[1] - 1} Datenspalten, nicht durch 3 teilbar")
    out, info, jahre = [], Counter(), []
    for c in range(1, df.shape[1], 3):
        teile = [str(df.iloc[2, c + k]).strip() for k in range(3)]
        if teile != ["PR", "CL", "Status"]:
            raise LadeFehler(f"Spalten {c}–{c + 2}: {teile} statt PR/CL/Status")
        roh = df.iloc[1, c]
        if isinstance(roh, (int, float)) and not pd.isna(roh) and float(roh).is_integer():
            jahr = int(roh)
        elif str(roh).strip() in ZEITRAUM_JAHR:
            if not mit_zeitraum:
                info["ausgaben_zeitraum_uebersprungen"] += 1
                continue
            jahr = ZEITRAUM_JAHR[str(roh).strip()]
        else:
            raise LadeFehler(f"Spalte {c}: Berichtszeitraum {roh!r} unbekannt (ZEITRAUM_JAHR ergänzen)")
        if not 1970 <= jahr <= dt.date.today().year:
            raise LadeFehler(f"Spalte {c}: Jahr {jahr} unplausibel")
        jahre.append(jahr)
        out.append((jahr, c, c + 1, c + 2))
    doppelt = [j for j, n in Counter(jahre).items() if n > 1]
    if doppelt:
        raise LadeFehler(f"Jahre mehrfach im Kopf: {doppelt}")
    info["ausgaben"] = len(out)
    return out, info


def parse(df: pd.DataFrame, cols: list, z: Zuordnung) -> tuple[dict, Counter]:
    """→ {(iso_numeric, code, jahr): wert}, Zählbericht."""
    body = df.iloc[3:]
    namen = [str(n).strip() for n in body.iloc[:, 0] if not pd.isna(n)]
    if len(namen) != len(set(namen)):
        raise LadeFehler(f"Ländernamen mehrfach: {[n for n, k in Counter(namen).items() if k > 1]}")
    z.pruefe_alle([(n, j) for n in namen for j, *_ in cols])   # Abbruch mit voller Liste

    out, bericht, unbekannt = {}, Counter(), []
    for _, row in body.iterrows():
        if pd.isna(row.iloc[0]):
            continue
        name = str(row.iloc[0]).strip()
        for jahr, c_pr, c_cl, c_st in cols:
            iso = z.iso_numeric(name, jahr)
            werte = {"PR": row.iloc[c_pr], "CL": row.iloc[c_cl], "Status": row.iloc[c_st]}
            if iso is None:
                bericht["verworfen_land_werte"] += sum(1 for v in werte.values() if str(v).strip() not in ("-", "nan"))
                continue
            for teil, code in (("PR", "FH:PR"), ("CL", "FH:CL"), ("Status", "FH:STATUS")):
                v = werte[teil]
                s = "" if pd.isna(v) else str(v).strip()
                if s in ("", "-"):
                    bericht["ohne_wert"] += 1
                    continue
                sonder = SONDERWERTE.get((name, jahr, teil, s))
                if sonder == "verwerfen":
                    bericht["sonderwert_verworfen"] += 1
                    continue
                if teil == "Status":
                    if s not in STATUS_WERT:
                        unbekannt.append((name, jahr, teil, s))
                        continue
                    wert = STATUS_WERT[s]
                else:
                    try:
                        wert = float(s)
                    except ValueError:
                        unbekannt.append((name, jahr, teil, s))
                        continue
                    if not (wert.is_integer() and 1 <= wert <= 7):
                        unbekannt.append((name, jahr, teil, s))
                        continue
                key = (iso, code, str(jahr))
                if key in out:
                    raise LadeFehler(f"Doppelt: {key}")
                out[key] = wert
                bericht[code] += 1
    if unbekannt:
        raise LadeFehler(f"{len(unbekannt)} Werte nicht lesbar (SONDERWERTE ergänzen oder klären): {unbekannt[:20]}")
    z.pruefe_eindeutig()
    if not out:
        raise LadeFehler("0 Werte gelesen")
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, list(CODES)))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    c, beispiele = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c[f"neu_{k[1]}"] += 1
        elif alt[k] is None or abs(alt[k] - w) > 1e-9:
            c["wert_geaendert"] += 1
            if len(beispiele) < 15:
                beispiele.append((k, alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return c, beispiele + [("nur_in_db", k, alt[k]) for k in nur_db[:15]]


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true", help="in die DB schreiben (sonst nur Trockenlauf)")
    ap.add_argument("--ohne-1982-1989", action="store_true", help="Ausgaben mit Berichtszeitraum weglassen")
    ap.add_argument("--datei", type=Path, default=RAW_FILE)
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources. Der Loader legt sie nicht an.")
        source_id = r[0]
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (list(CODES),))
        meta = dict(cur.fetchall())
        fehlend = [c for c in CODES if c not in meta]
        falsch = [c for c in CODES if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "name")

        df, sha = read_file(args.datei)
        cols, info = spalten(df, not args.ohne_1982_1989)
        log.info(f"=== FH {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {dict(info)} ===")
        neu, bericht = parse(df, cols, z)
        log.info(f"  Gelesen: {dict(sorted(bericht.items()))}")
        log.info(f"  {z.bericht_text()}")
        vergleich, beispiele = compare(cur, source_id, neu)
        log.info(f"  Vergleich DB: {dict(sorted(vergleich.items()))}")
        for b in beispiele:
            log.info(f"    {b}")
    except (LadeFehler, LaenderFehler) as e:
        log.error(f"FEHLER: {e}")
        log.error("=== Es wird NICHTS geschrieben. ===")
        conn.rollback()
        conn.close()
        sys.exit(1)

    if not args.schreiben:
        log.info("=== Trocken: geprüft, nichts geschrieben. Schreiben mit --schreiben. ===")
        conn.rollback()
        conn.close()
        return

    rows = [(iso, code, source_id, jahr, w, "A") for (iso, code, jahr), w in neu.items()]
    res = execute_values(cur, """
        INSERT INTO indicators (iso_numeric, indicator_code, source_id, time_period, value, obs_status)
        VALUES %s
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO UPDATE
        SET value = EXCLUDED.value, obs_status = EXCLUDED.obs_status, last_updated = CURRENT_TIMESTAMP
        WHERE indicators.value IS DISTINCT FROM EXCLUDED.value
           OR indicators.obs_status IS DISTINCT FROM EXCLUDED.obs_status
        RETURNING (xmax = 0)
    """, rows, page_size=2000, fetch=True)
    n_neu = sum(1 for x in res if x[0])
    n_geaendert = len(res) - n_neu
    n_gleich = len(rows) - len(res)
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"FIW 1973-2024 xlsx sha256:{sha}", source_id))   # varchar(50)
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. "
             f"sources.loaded_at/loaded_version gesetzt, indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
