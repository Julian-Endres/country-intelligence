"""
load_whr.py — World Happiness Report 2026, Daten zu Abbildung 2.1 (2011–2025)
==============================================================================
Quelle:  World Happiness Report 2026, „Data for Figure 2.1 (2011–2025)"
Datei:   data/raw/culture/WHR26_Data_Figure_2.1.xlsx (erstes und einziges Blatt)
Ziel:    indicators, 7 Codes WHR:* (source_id aus sources.short_code = 'WHR')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/culture/load_whr.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/culture/load_whr.py --schreiben   schreibt (eine Transaktion)

Regeln (Neufassung CI-177, Entwurf 25.11.2026)
----------------------------------------------
- Bisher: Namen über NAME_OVERRIDES, sonst Teilstring in beide Richtungen („congo" ⊂ „dr congo"):
  DR Kongo trug 52 von 56 Werten der Republik Kongo, Zypern 2014–2017 die von Nordzypern (CI-172).
- Neu: Länder nur über scripts/pipeline/lib/laender.py (exakter Name oder Liste
  scripts/pipeline/lib/laender/WHR.csv). Unbekannter Name → Abbruch mit Namensliste.
- time_period = Spalte „Year" (wie bisher). Werte numerisch, sonst Abbruch. Leer → kein Wert.
- Genau eine Zeile je Land und Jahr, ein Land je Jahr nur aus einem Rohnamen.
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
log = logging.getLogger("whr")

RAW_FILE = REPO / "data" / "raw" / "culture" / "WHR26_Data_Figure_2.1.xlsx"   # #135
SOURCE_CODE = "WHR"
SPALTEN = {
    "Life evaluation (3-year average)":           "WHR:life_evaluation",
    "Explained by: Log GDP per capita":           "WHR:gdp_component",
    "Explained by: Social support":               "WHR:social_support",
    "Explained by: Healthy life expectancy":      "WHR:health",
    "Explained by: Freedom to make life choices": "WHR:freedom",
    "Explained by: Generosity":                   "WHR:generosity",
    "Explained by: Perceptions of corruption":    "WHR:corruption",
}
CODES = tuple(SPALTEN.values())


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


def read_file(pfad: Path) -> tuple[pd.DataFrame, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    xl = pd.ExcelFile(pfad, engine="openpyxl")
    if len(xl.sheet_names) != 1:
        raise LadeFehler(f"Erwartet genau ein Blatt, gefunden {xl.sheet_names}")
    df = pd.read_excel(xl, xl.sheet_names[0])
    fehlend = [c for c in ["Year", "Country name", *SPALTEN] if c not in df.columns]
    if fehlend:
        raise LadeFehler(f"Spalten fehlen: {fehlend}")
    return df, sha


def parse(df: pd.DataFrame, z: Zuordnung) -> tuple[dict, Counter]:
    df = df[df["Country name"].notna() & df["Year"].notna()]
    if df.duplicated(["Year", "Country name"]).any():
        raise LadeFehler("Land-Jahr mehrfach in der Datei")
    jahre = df["Year"].astype(float)
    if not (jahre == jahre.round()).all():
        raise LadeFehler("Year nicht ganzzahlig")
    paare = [(str(n).strip(), int(j)) for n, j in zip(df["Country name"], df["Year"])]
    z.pruefe_alle(paare)
    out, bericht, kaputt = {}, Counter(), []
    for (name, jahr), (_, row) in zip(paare, df.iterrows()):
        iso = z.iso_numeric(name, jahr)
        if iso is None:
            bericht["verworfen_zeilen"] += 1
            continue
        for spalte, code in SPALTEN.items():
            v = row[spalte]
            if pd.isna(v):
                bericht["ohne_wert"] += 1
                continue
            try:
                w = float(v)
            except ValueError:
                kaputt.append((name, jahr, spalte, v))
                continue
            out[(iso, code, str(jahr))] = w
            bericht[code] += 1
    if kaputt:
        raise LadeFehler(f"{len(kaputt)} Werte nicht numerisch: {kaputt[:20]}")
    z.pruefe_eindeutig()
    if not out:
        raise LadeFehler("0 Werte gelesen")
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, list(CODES)))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
    i3 = dict(cur.fetchall())
    c, bsp = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c["neu"] += 1
            c[f"neu_{i3[k[0]]}"] += 1
        elif alt[k] is None or abs(alt[k] - w) > 1e-9:
            c["wert_geaendert"] += 1
            c[f"geaendert_{i3[k[0]]}"] += 1
            if len(bsp) < 20:
                bsp.append(("geaendert", i3[k[0]], k[1], k[2], alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    for k in nur_db:
        c[f"nur_in_db_{i3[k[0]]}"] += 1
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return c, bsp + [("nur_in_db", i3[k[0]], k[1], k[2], alt[k]) for k in nur_db[:20]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true")
    ap.add_argument("--datei", type=Path, default=RAW_FILE)
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources.")
        source_id = r[0]
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (list(CODES),))
        meta = dict(cur.fetchall())
        fehlend = [c for c in CODES if c not in meta]
        falsch = [c for c in CODES if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "name")
        df, sha = read_file(args.datei)
        log.info(f"=== WHR {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {len(df)} Zeilen ===")
        neu, bericht = parse(df, z)
        log.info(f"  Gelesen: {dict(sorted(bericht.items()))}")
        log.info(f"  {z.bericht_text()}")
        vergleich, bsp = compare(cur, source_id, neu)
        log.info(f"  Vergleich DB: {dict(sorted(vergleich.items()))}")
        for b in bsp:
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
                (dt.date.today(), f"WHR26 Fig 2.1 xlsx sha256:{sha}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. ===")


if __name__ == "__main__":
    main()
