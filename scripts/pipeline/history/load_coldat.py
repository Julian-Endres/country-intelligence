"""
load_coldat.py — COLDAT Colonial Dates Dataset
================================================
Source:  Bastian Becker, University of Bremen
         Harvard Dataverse DOI: 10.7910/DVN/T9SDEW
Domain:  History & Collective Memory / International Relations
Destination: colonial_history table

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/history/load_coldat.py
"""

import os
import logging
import pandas as pd
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DYADS_FILE = "data/raw/Manuell_27-05/COLDAT_dyads.csv"

OVERRIDES = {
    "bolivia (plurinational state of)": "BOL",
    "cabo verde":                       "CPV",
    "congo":                            "COG",
    "democratic republic of the congo": "COD",
    "côte d'ivoire":                    "CIV",
    "eswatini":                         "SWZ",
    "gambia":                           "GMB",
    "guinea-bissau":                    "GNB",
    "iran (islamic republic of)":       "IRN",
    "lao people's democratic republic": "LAO",
    "myanmar":                          "MMR",
    "papua new guinea":                 "PNG",
    "solomon islands":                  "SLB",
    "south sudan":                      "SSD",
    "timor-leste":                      "TLS",
    "tanzania":                         "TZA",
    "united republic of tanzania":      "TZA",
    "viet nam":                         "VNM",
    "venezuela (bolivarian republic of)": "VEN",
    "occupied palestinian territory":   "PSE",
    "antigua & barbuda":                "ATG",
    "congo - brazzaville":              "COG",
    "congo - kinshasa":                 "COD",
    "micronesia (federated states of)": "FSM",
    "myanmar (burma)":                  "MMR",
    "st. kitts & nevis":                "KNA",
    "st. lucia":                        "LCA",
    "st. vincent & grenadines":         "VCT",
    "são tomé & príncipe":              "STP",
    "trinidad & tobago":                "TTO",
    "c\u00f4te d\u2019ivoire":          "CIV",
}

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"),
    )

def build_maps(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        iso3 = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT LOWER(name), iso_numeric FROM countries")
        names = {r[0]: r[1] for r in cur.fetchall()}
    return iso3, names

def resolve(name, iso3_map, name_map):
    clean = name.strip().lower()
    iso3 = OVERRIDES.get(clean)
    if iso3: return iso3_map.get(iso3)
    iso_num = name_map.get(clean)
    if iso_num: return iso_num
    try:
        r = pycountry.countries.search_fuzzy(name.strip())
        if r: return iso3_map.get(r[0].alpha_3)
    except: pass
    return None

def main():
    log.info("=== COLDAT Loader ===")
    conn = get_conn()
    iso3_map, name_map = build_maps(conn)

    df = pd.read_csv(DYADS_FILE)
    log.info(f"Total rows: {len(df):,}")

    df = df[df["col"] == 1].copy()
    log.info(f"Colonial relationships: {len(df):,}")

    rows = []
    skipped = set()

    for _, row in df.iterrows():
        iso_num = resolve(str(row["country"]), iso3_map, name_map)
        if not iso_num:
            skipped.add(row["country"])
            continue

        def f(col):
            v = row.get(col)
            return float(v) if pd.notna(v) else None

        start = f("colstart_mean")
        end   = f("colend_mean")
        duration = round(end - start, 1) if start and end else None

        rows.append((
            iso_num,
            str(row["country"])[:150],
            str(row["colonizer"])[:50],
            int(f("colstart_max")) if f("colstart_max") else None,
            int(f("colend_max"))   if f("colend_max")   else None,
            start, end, duration,
        ))

    if skipped:
        log.info(f"Skipped ({len(skipped)}): {sorted(skipped)}")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO colonial_history
                (colony_iso, colony_name, colonizer, col_start_max, col_end_max,
                 col_start_mean, col_end_mean, duration_years)
            VALUES %s
            ON CONFLICT (colony_iso, colonizer) DO NOTHING
        """, rows)
    conn.commit()
    log.info(f"Inserted: {len(rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()