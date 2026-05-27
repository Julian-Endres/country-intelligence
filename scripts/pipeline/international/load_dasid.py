"""
load_dasid.py — DASID Dyadic Annual State Interactions Dataset
===============================================================
Source:  Moyer, Turner, Meisel (2021) — University of Denver / Pardee Center
Domain:  International Relations
Destination: diplomatic_relations table

Files:
  DASID.zip/New folder/dyad_year_balanced_1985_2000.csv
  DASID.zip/New folder/dyad_year_balanced_2001_2019.csv

Country mapping: iso3_src / iso3_tgt → iso_numeric directly.

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/international/load_dasid.py
"""

import os
import zipfile
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ZIP_PATH = "data/raw/Manuell_27-05/DASID.zip"
FILES = [
    "New folder/dyad_year_balanced_1985_2000.csv",
    "New folder/dyad_year_balanced_2001_2019.csv",
]

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"),
    )

def build_iso3_map(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        return {r[0]: r[1] for r in cur.fetchall()}

def f(v):
    return float(v) if pd.notna(v) else None

def i(v):
    return int(v) if pd.notna(v) else None

def main():
    log.info("=== DASID Loader ===")
    conn = get_conn()
    iso3_map = build_iso3_map(conn)

    total = 0
    skipped = set()

    with zipfile.ZipFile(ZIP_PATH) as z:
        for fname in FILES:
            log.info(f"Processing {fname}...")
            with z.open(fname) as f_:
                df = pd.read_csv(f_)
            log.info(f"  Rows: {len(df):,}")

            rows = []
            for _, row in df.iterrows():
                src = iso3_map.get(str(row.get("iso3_src", "")).strip())
                tgt = iso3_map.get(str(row.get("iso3_tgt", "")).strip())
                if not src or not tgt:
                    skipped.add(f"{row.get('iso3_src')}→{row.get('iso3_tgt')}")
                    continue

                year = i(row.get("year"))
                if not year:
                    continue

                rows.append((
                    src, tgt, year,
                    f(row.get("positive_score")),
                    i(row.get("positive_count")),
                    f(row.get("negative_score")),
                    i(row.get("negative_count")),
                    i(row.get("ambiguous_count")),
                    i(row.get("event_count")),
                    i(row.get("num_state_visits")),
                ))

            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO diplomatic_relations
                        (source_iso, target_iso, year, positive_score, positive_count,
                         negative_score, negative_count, ambiguous_count,
                         event_count, num_state_visits)
                    VALUES %s
                    ON CONFLICT (source_iso, target_iso, year) DO NOTHING
                """, rows, page_size=2000)
            conn.commit()
            log.info(f"  Inserted: {len(rows):,}")
            total += len(rows)

    if skipped:
        log.info(f"Skipped pairs (no ISO match): {len(skipped)}")
    log.info(f"Total inserted: {total:,}")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
