"""
load_ccp.py — Comparative Constitutions Project v6
====================================================
Source:  Elkins, Ginsburg, Melton (2026) — CCP Version 6
Domain:  History & Collective Memory / Politics
Destination: constitutional_events table

Country mapping: COW numeric → ISO3 via countrycode + manual fallback.

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/history/load_ccp.py
"""

import os
import zipfile
import logging
import pandas as pd
import countrycode
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ZIP_PATH = "data/raw/history/ccpcce_v6_Comparative Constitutions Project.zip"

CCP_FALLBACK = {
    89:  None,   240: "DEU",  245: "DEU",  260: "DEU",
    265: "DEU",  267: "DEU",  269: "DEU",  271: "DEU",
    273: "DEU",  275: "DEU",  280: "DEU",  99:  None,
    300: "AUT",  315: "CZE",  329: "ITA",  332: "ITA",
    335: "ITA",  337: "ITA",  340: "SRB",  347: "XKX",
    396: None,   397: None,   511: "TZA",  563: "ZAF",
    564: "ZAF",  678: "YEM",  680: "YEM",  711: None,
    730: "KOR",  815: "VNM",  817: "VNM",
}

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

def build_cowcode_map(cowcodes, iso3_map):
    results = countrycode.countrycode(cowcodes, origin='cown', destination='iso3c')
    mapping = {}
    for code, iso3 in zip(cowcodes, results):
        if iso3 and iso3 in iso3_map:
            mapping[code] = iso3_map[iso3]
        elif code in CCP_FALLBACK:
            fallback = CCP_FALLBACK[code]
            if fallback and fallback in iso3_map:
                mapping[code] = iso3_map[fallback]
    return mapping

def main():
    log.info("=== CCP Loader ===")
    conn = get_conn()
    iso3_map = build_iso3_map(conn)

    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open("ccpcce_v6/ccpcce/ccpcce_v6.csv") as f:
            df = pd.read_csv(f)

    df.columns = [c.lower() for c in df.columns]
    log.info(f"Rows: {len(df):,} | Years: {df.year.min()}–{df.year.max()}")

    cowcodes = df['cowcode'].dropna().unique().astype(int).tolist()
    cow_map = build_cowcode_map(cowcodes, iso3_map)
    unmatched = set(cowcodes) - set(cow_map.keys())
    log.info(f"Mapped {len(cow_map)}/{len(cowcodes)} COW codes")
    if unmatched:
        log.info(f"Unmatched (historical/skip): {sorted(unmatched)}")

    rows = []
    for _, row in df.iterrows():
        cowcode = int(row["cowcode"]) if pd.notna(row.get("cowcode")) else None
        if not cowcode:
            continue
        iso_num = cow_map.get(cowcode)
        if not iso_num:
            continue

        year = int(row["year"]) if pd.notna(row.get("year")) else None
        if not year:
            continue

        evnt_type = str(row.get("evnttype", "")).strip().lower()
        if evnt_type == "non-event":
            continue

        evnt_id = int(row["evntid"]) if pd.notna(row.get("evntid")) else None

        rows.append((
            iso_num,
            str(row.get("country", ""))[:150],
            year,
            int(row["systid"]) if pd.notna(row.get("systid")) else None,
            evnt_id,
            evnt_type[:50] if evnt_type else None,
        ))

    log.info(f"Prepared: {len(rows):,} rows")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO constitutional_events
                (iso_numeric, country_name, year, syst_id, evnt_id, evnt_type)
            VALUES %s
            ON CONFLICT (iso_numeric, year, evnt_id) DO NOTHING
        """, rows, page_size=1000)
    conn.commit()
    log.info(f"Inserted: {len(rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()