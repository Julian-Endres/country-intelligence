"""
load_kof.py — KOF Globalisation Index (Version 2020-Methodik), 1970–2023
========================================================================
ENTWURF CI-179 / CI-172 (Claude, Nacht 24./25.11.2026). Ersetzt load_kof.py.

Datei:   data/raw/Manuell_27-05/KOF/kof_data_export_2026-05-28_22_06_58.xlsx (Werte, breit: eine Spalte je
         ch.kof.globidx.v2020.{teilindex}.{code}, Zeilen = Jahre „1970-01“ …)
         data/raw/Manuell_27-05/KOF/kof_data_export_2026-05-28_22_07_53.xlsx (Schlüssel → Ländername, Beleg)
Ziel:    indicators, 9 Codes KOF:* (gesamt und Teilindizes, nur die Spalten ohne df/dj-Zusatz),
         source_id aus sources.short_code = 'KOF'

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/international/load_kof.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/international/load_kof.py --schreiben   schreibt (eine Transaktion)

Befund (CI-172): Die Datei nutzt teils alte Codes (zar, rom, tmp, ado, wbg). Der alte Loader kannte nur heutige
ISO3 und übersprang still → DR Kongo, Rumänien, Timor-Leste, Andorra, Palästina ohne Werte.
Neu: Code vor Name über laender.py (art="iso3"), Liste KOF.csv für alte Codes und Aggregate; unbekannter
Code → Abbruch. Werte 0–100, sonst Abbruch. DO UPDATE nur bei Änderung. Nichts wird gelöscht.
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import re
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
log = logging.getLogger("kof")

RAW_FILE = REPO / "data" / "raw" / "Manuell_27-05" / "KOF" / "kof_data_export_2026-05-28_22_06_58.xlsx"   # #135
SOURCE_CODE = "KOF"
TEILINDIZES = {"gi": "KOF:gi", "ecgi": "KOF:ecgi", "trgi": "KOF:trgi", "figi": "KOF:figi", "sogi": "KOF:sogi",
               "pogi": "KOF:pogi", "cugi": "KOF:cugi", "ingi": "KOF:ingi", "ipgi": "KOF:ipgi"}
NICHT_GELADEN = {f"{t}{s}" for t in TEILINDIZES for s in ("df", "dj")}   # de facto / de jure: keine Codes
SPALTE = re.compile(r"ch\.kof\.globidx\.v2020\.([a-z]+)\.([a-z]{3})")
CODES = sorted(TEILINDIZES.values())


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
    df = pd.read_excel(pfad, engine="openpyxl")
    if df.columns[0] != "date":
        raise LadeFehler(f"Erste Spalte {df.columns[0]!r} statt 'date'")
    return df, sha


def parse(df: pd.DataFrame, z: Zuordnung) -> tuple[dict, Counter]:
    jahre = df["date"].astype(str)
    if not jahre.str.fullmatch(r"\d{4}-01").all():
        raise LadeFehler(f"date nicht im Format JJJJ-01: {jahre[~jahre.str.fullmatch(r'\d{4}-01')].tolist()[:5]}")
    jahre = jahre.str[:4].astype(int)
    spalten, bericht = [], Counter()
    for c in df.columns[1:]:
        m = SPALTE.fullmatch(c)
        if not m:
            raise LadeFehler(f"Spalte {c!r} passt nicht zum Muster ch.kof.globidx.v2020.TEIL.CODE")
        teil, code = m.groups()
        if teil in NICHT_GELADEN:
            bericht["spalten_df_dj_nicht_geladen"] += 1
            continue
        if teil not in TEILINDIZES:
            raise LadeFehler(f"Teilindex {teil!r} unbekannt")
        spalten.append((c, TEILINDIZES[teil], code))
    z.pruefe_alle([(code, int(j)) for _, _, code in spalten for j in jahre])
    out, kaputt = {}, []
    for c, ind, code in spalten:
        for j, v in zip(jahre, df[c]):
            if pd.isna(v):
                bericht["ohne_wert"] += 1
                continue
            iso = z.iso_numeric(code, int(j))
            if iso is None:
                bericht["verworfen_aggregat"] += 1
                continue
            w = float(v)
            if not 0 <= w <= 100:
                kaputt.append((code, ind, j, v))
                continue
            out[(iso, ind, str(j))] = w
    if kaputt:
        raise LadeFehler(f"{len(kaputt)} Werte außerhalb 0–100: {kaputt[:10]}")
    z.pruefe_eindeutig()
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, CODES))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
    i3 = dict(cur.fetchall())
    c, bsp = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c[f"neu_{i3[k[0]]}"] += 1
        elif abs(alt[k] - w) > 1e-9:
            c["geaendert"] += 1
            bsp.append(("geaendert", i3[k[0]], k[1], k[2], alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return c, bsp[:20] + [("nur_in_db", i3[k[0]], k[1], k[2], alt[k]) for k in nur_db[:20]]


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
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "iso3")
        df, sha = read_file(args.datei)
        log.info(f"=== KOF {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · {args.datei.name} (sha256 {sha}…) ===")
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
    """, rows, page_size=5000, fetch=True)
    n_neu = sum(1 for x in res if x[0])
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"KOFGI v2020 xlsx sha256:{sha}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {len(res) - n_neu} geändert, {len(rows) - len(res)} unverändert. ===")


if __name__ == "__main__":
    main()
