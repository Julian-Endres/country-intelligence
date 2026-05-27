"""
load_polity5.py — Polity5 Democracy & Governance Scores
========================================================
Source:  Polity5 Annual Time-Series 1946-2018 (p5v2018.xls)
         Center for Systemic Peace (systemicpeace.org)
Domain:  Politics & Governance / History
Destination: indicators table (source_code = 'POLITY5')

Country mapping: COW scode → ISO3 via countrycode package + manual fallback.

Indicators loaded
-----------------
POLITY5:polity2   Revised Combined Polity Score (-10 to +10)
POLITY5:democ     Institutionalized Democracy (0-10)
POLITY5:autoc     Institutionalized Autocracy (0-10)
POLITY5:durable   Regime Durability (years)
POLITY5:xconst    Executive Constraints (1-7)
POLITY5:polcomp   Political Competition (1-10)

Special codes in polity2 (-66/-77/-88) are excluded.

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/governance/load_polity5.py
"""

import os
import logging
import pandas as pd
import countrycode
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FILE = "data/raw/history/p5v2018_Polity5_Annual Time-Series, 1946-2018.xls"

POLITY_SPECIAL = {-66, -77, -88}

COW_FALLBACK = {
    "BAD": "BRB",  "BAV": None,   "CZE": "CZE",  "ETI": "ETH",
    "FJI": "FJI",  "GCL": None,   "GDR": "DEU",  "GFR": "DEU",
    "IVO": "CIV",  "KOR": "KOR",  "KOS": "XKX",  "MNT": "MNE",
    "MOD": "MDA",  "OFS": None,   "PKS": "PAK",  "PMA": "PAN",
    "RUM": "ROU",  "RVN": "VNM",  "SAR": "SAU",  "SAX": None,
    "SDN": "SDN",  "SER": "SRB",  "SIC": None,   "SSU": "SSD",
    "TUS": None,   "UPC": "UGA",  "USR": "RUS",  "VIE": "VNM",
    "WRT": None,   "YAR": "YEM",  "YGS": "SRB",  "YPR": "YEM",
    "YUG": "SRB",  "ZAI": "COD",
}

INDICATORS = [
    ("POLITY5:polity2", "Polity2 Combined Democracy Score",  "score", "governance", "Revised combined Polity score (-10=full autocracy to +10=full democracy). Source: Polity5."),
    ("POLITY5:democ",   "Institutionalized Democracy Score", "score", "governance", "Institutionalized democracy component (0-10). Source: Polity5."),
    ("POLITY5:autoc",   "Institutionalized Autocracy Score", "score", "governance", "Institutionalized autocracy component (0-10). Source: Polity5."),
    ("POLITY5:durable", "Regime Durability (years)",         "years", "governance", "Years since last regime transition. Source: Polity5."),
    ("POLITY5:xconst",  "Executive Constraints",             "score", "governance", "Constraints on chief executive (1-7). Source: Polity5."),
    ("POLITY5:polcomp", "Political Competition",             "score", "governance", "Competitiveness of political participation (1-10). Source: Polity5."),
]

INDICATOR_COLS = {
    "POLITY5:polity2": "polity2", "POLITY5:democ":   "democ",
    "POLITY5:autoc":   "autoc",   "POLITY5:durable": "durable",
    "POLITY5:xconst":  "xconst",  "POLITY5:polcomp": "polcomp",
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

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('POLITY5', 'Polity5 – Center for Systemic Peace',
                    'https://www.systemicpeace.org/inscrdata.html',
                    'Annual cross-national political regime characteristics 1776-2018.')
            ON CONFLICT (short_code) DO NOTHING
        """)
    conn.commit()

def ensure_metadata(conn):
    for code, name, unit, cat, desc in INDICATORS:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO indicator_metadata
                    (indicator_code, name, unit, category, description, source_id)
                VALUES (%s, %s, %s, %s, %s,
                        (SELECT id FROM sources WHERE short_code = 'POLITY5'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

def build_scode_map(scodes, iso3_map):
    results = countrycode.countrycode(scodes, origin='cowc', destination='iso3c')
    mapping = {}
    for scode, iso3 in zip(scodes, results):
        if iso3 and iso3 in iso3_map:
            mapping[scode] = iso3_map[iso3]
        elif scode in COW_FALLBACK:
            fallback = COW_FALLBACK[scode]
            if fallback and fallback in iso3_map:
                mapping[scode] = iso3_map[fallback]
    return mapping

def main():
    log.info("=== Polity5 Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)
    iso3_map = build_iso3_map(conn)

    df = pd.read_excel(FILE)
    log.info(f"Rows: {len(df):,} | Countries: {df.scode.nunique()} | Years: {df.year.min()}–{df.year.max()}")

    scodes = df['scode'].dropna().unique().tolist()
    scode_map = build_scode_map(scodes, iso3_map)
    unmatched = set(scodes) - set(scode_map.keys())
    log.info(f"Mapped {len(scode_map)}/{len(scodes)} scodes")
    if unmatched:
        log.info(f"Unmatched (historical/skip): {sorted(unmatched)}")

    rows = []
    for _, row in df.iterrows():
        scode = str(row.get("scode", "")).strip()
        iso_num = scode_map.get(scode)
        if not iso_num:
            continue
        year = str(int(row["year"])) if pd.notna(row.get("year")) else None
        if not year:
            continue
        for indicator_code, col in INDICATOR_COLS.items():
            val = row.get(col)
            if pd.isna(val):
                continue
            val = float(val)
            if indicator_code == "POLITY5:polity2" and int(val) in POLITY_SPECIAL:
                continue
            if indicator_code == "POLITY5:durable" and val < 0:
                continue
            rows.append((iso_num, indicator_code, year, val, "A"))

    log.info(f"DB rows prepared: {len(rows):,}")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
            VALUES %s
            ON CONFLICT DO NOTHING
        """, rows, page_size=2000)
    conn.commit()
    log.info(f"Inserted: {len(rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
