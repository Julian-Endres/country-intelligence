"""
load_fsi.py — Fragile States Index (Fund for Peace), Blatt "FSI 2006-2022"
==========================================================================
ENTWURF #140 (Claude, Nacht 24./25.11.2026). Ersetzt den FSI-Teil von load_fsi_gitoc_owid.py.

Datei:   data/raw/governance/fragile_states_index.xlsx, Blatt "FSI 2006-2022"
         (der alte Loader suchte data/raw/fragile_states_index.xlsx – den Pfad gibt es nicht mehr, #135).
         Das Blatt enthält trotz Namen nur das Jahr 2022 (179 Länder); die Historie fehlt in der Datei (Befund 15.11.).
Ziel:    indicators, 13 Codes FSI:* (source_id aus sources.short_code = 'FSI'), time_period = Jahr aus Spalte Year

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/governance/load_fsi.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/governance/load_fsi.py --schreiben   schreibt (eine Transaktion)

Befund #140: 6 Länder still verworfen (beide Kongos, Guinea-Bissau, Côte d'Ivoire, São Tomé, Brunei).
Neu: laender.py + Liste FSI.csv, Abbruch bei Unbekanntem. Werte: Total 0–120, Teilindikatoren 0–10, sonst Abbruch.
Eins zu eins je Land und Jahr. DO UPDATE nur bei Änderung. Nichts wird gelöscht, Fehlendes gemeldet.
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
log = logging.getLogger("fsi")

RAW_FILE = REPO / "data" / "raw" / "governance" / "fragile_states_index.xlsx"   # #135
SHEET = "FSI 2006-2022"
SOURCE_CODE = "FSI"
SPALTEN = {
    "Total": "FSI:total",
    "C1: Security Apparatus": "FSI:c1_security",
    "C2: Factionalized Elites": "FSI:c2_elites",
    "C3: Group Grievance": "FSI:c3_grievance",
    "E1: Economy": "FSI:e1_economy",
    "E2: Economic Inequality": "FSI:e2_inequality",
    "E3: Human Flight and Brain Drain": "FSI:e3_brain_drain",
    "P1: State Legitimacy": "FSI:p1_legitimacy",
    "P2: Public Services": "FSI:p2_services",
    "P3: Human Rights": "FSI:p3_rights",
    "S1: Demographic Pressures": "FSI:s1_demographics",
    "S2: Refugees and IDPs": "FSI:s2_refugees",
    "X1: External Intervention": "FSI:x1_external",
}
CODES = sorted(SPALTEN.values())


class LadeFehler(Exception):
    pass


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"),
    )


def read_file(pfad: Path) -> tuple[pd.DataFrame, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    df = pd.read_excel(pfad, sheet_name=SHEET, engine="openpyxl")
    fehlt = [c for c in ["Country", "Year", *SPALTEN] if c not in df.columns]
    if fehlt:
        raise LadeFehler(f"Spalten fehlen: {fehlt}")
    return df, sha


def parse(df: pd.DataFrame, z: Zuordnung) -> tuple[dict, Counter]:
    df = df[df["Country"].notna()]
    jahre = pd.to_datetime(df["Year"], errors="raise").dt.year
    paare = [(str(n).strip(), int(j)) for n, j in zip(df["Country"], jahre)]
    if len(paare) != len(set(paare)):
        raise LadeFehler("Land-Jahr mehrfach")
    z.pruefe_alle(paare)
    out, bericht, kaputt = {}, Counter(), []
    for (name, jahr), (_, row) in zip(paare, df.iterrows()):
        iso = z.iso_numeric(name, jahr)
        if iso is None:
            bericht["verworfen"] += 1
            continue
        for spalte, code in SPALTEN.items():
            v = row[spalte]
            if pd.isna(v):
                bericht["ohne_wert"] += 1
                continue
            w = float(v)
            grenze = 120 if code == "FSI:total" else 10
            if not 0 <= w <= grenze:
                kaputt.append((name, jahr, spalte, v))
                continue
            out[(iso, code, str(jahr))] = w
        bericht[f"jahr_{jahr}"] += 1
    if kaputt:
        raise LadeFehler(f"{len(kaputt)} Werte außerhalb der Skala: {kaputt[:10]}")
    z.pruefe_eindeutig()
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> Counter:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, CODES))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    c = Counter()
    for k, w in neu.items():
        c["neu" if k not in alt else ("gleich" if abs(alt[k] - w) <= 1e-9 else "geaendert")] += 1
    c["nur_in_db"] = len(set(alt) - set(neu))
    c["db_vorher"] = len(alt)
    return c


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
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (CODES,))
        meta = dict(cur.fetchall())
        fehlend = [c for c in CODES if c not in meta]
        falsch = [c for c in CODES if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "name")
        df, sha = read_file(args.datei)
        log.info(f"=== FSI {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · {args.datei.name} (sha256 {sha}…) ===")
        neu, bericht = parse(df, z)
        log.info(f"  Gelesen: {dict(sorted(bericht.items()))}")
        log.info(f"  {z.bericht_text()}")
        log.info(f"  Vergleich DB: {dict(sorted(compare(cur, source_id, neu).items()))}")
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
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"FSI 2022 xlsx sha256:{sha}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {len(res) - n_neu} geändert, {len(rows) - len(res)} unverändert. ===")


if __name__ == "__main__":
    main()
