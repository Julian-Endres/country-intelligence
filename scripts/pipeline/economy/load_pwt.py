"""
load_pwt.py — Penn World Table 11.0
====================================
Source:  Penn World Table 11.0 (pwt110.xlsx)
         Groningen Growth and Development Centre
Domain:  Economy / Labour / Productivity
Destination: indicators table (source_code = 'PWT')

Indicators loaded
-----------------
PWT:rgdpe    Real GDP expenditure-side, chained PPPs (mil. 2021US$)
PWT:rgdpo    Real GDP output-side, chained PPPs (mil. 2021US$)
PWT:pop      Population (millions)
PWT:emp      Persons engaged (millions)
PWT:avh      Average annual hours worked per person
PWT:hc       Human capital index (years of schooling + returns to education)
PWT:ctfp     TFP level at current PPPs (USA=1)
PWT:cwtfp    Welfare-relevant TFP at current PPPs (USA=1)
PWT:labsh    Labour share in GDP at current national prices
PWT:delta    Average depreciation rate of capital stock
PWT:csh_c    Share of household consumption in GDP (current PPPs)
PWT:csh_i    Share of gross capital formation in GDP (current PPPs)
PWT:csh_g    Share of government consumption in GDP (current PPPs)
PWT:csh_x    Share of merchandise exports in GDP (current PPPs)
PWT:csh_m    Share of merchandise imports in GDP (current PPPs)

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/economy/load_pwt.py
"""

import os
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FILE = "data/raw/Manuell_27-05/pwt110_Penn World Table.xlsx"

INDICATORS = [
    ("PWT:rgdpe",  "Real GDP expenditure-side, chained PPPs (mil. 2021US$)", "mil. 2021US$", "economy",     "Expenditure-side real GDP at chained PPPs in millions of 2021 USD. Source: PWT 11.0."),
    ("PWT:rgdpo",  "Real GDP output-side, chained PPPs (mil. 2021US$)",      "mil. 2021US$", "economy",     "Output-side real GDP at chained PPPs in millions of 2021 USD. Source: PWT 11.0."),
    ("PWT:pop",    "Population (millions)",                                   "millions",     "demographics","Population in millions. Source: PWT 11.0."),
    ("PWT:emp",    "Persons engaged (millions)",                              "millions",     "economy",     "Number of persons engaged (employed) in millions. Source: PWT 11.0."),
    ("PWT:avh",    "Average annual hours worked per person",                  "hours",        "economy",     "Average annual hours worked by persons engaged. Source: PWT 11.0."),
    ("PWT:hc",     "Human capital index",                                     "index",        "economy",     "Human capital index based on years of schooling and returns to education (USA~3.7). Source: PWT 11.0."),
    ("PWT:ctfp",   "TFP level at current PPPs (USA=1)",                       "index",        "economy",     "Total factor productivity level at current PPPs relative to USA=1. Source: PWT 11.0."),
    ("PWT:cwtfp",  "Welfare-relevant TFP at current PPPs (USA=1)",            "index",        "economy",     "Welfare-relevant TFP levels at current PPPs, USA=1. Source: PWT 11.0."),
    ("PWT:labsh",  "Labour share in GDP",                                     "ratio",        "economy",     "Share of labour compensation in GDP at current national prices. Source: PWT 11.0."),
    ("PWT:delta",  "Average depreciation rate of capital stock",              "ratio",        "economy",     "Average depreciation rate of the capital stock. Source: PWT 11.0."),
    ("PWT:csh_c",  "Household consumption share of GDP",                      "ratio",        "economy",     "Share of household consumption in GDP at current PPPs. Source: PWT 11.0."),
    ("PWT:csh_i",  "Gross capital formation share of GDP",                    "ratio",        "economy",     "Share of gross capital formation in GDP at current PPPs. Source: PWT 11.0."),
    ("PWT:csh_g",  "Government consumption share of GDP",                     "ratio",        "economy",     "Share of government consumption in GDP at current PPPs. Source: PWT 11.0."),
    ("PWT:csh_x",  "Merchandise exports share of GDP",                        "ratio",        "economy",     "Share of merchandise exports in GDP at current PPPs. Source: PWT 11.0."),
    ("PWT:csh_m",  "Merchandise imports share of GDP",                        "ratio",        "economy",     "Share of merchandise imports in GDP at current PPPs. Source: PWT 11.0."),
    ("PWT:rgdpna", "Real GDP at constant 2021 national prices (mil. 2021US$)", "mil. 2021US$", "economy",     "Real GDP at constant 2021 national prices in millions of 2021 USD. Source: PWT 11.0."),
    ("PWT:cn",     "Capital stock at current PPPs (mil. 2021US$)",             "mil. 2021US$", "economy",     "Capital stock at current PPPs in millions of 2021 USD. Source: PWT 11.0."),
    ("PWT:ccon",   "Real consumption households+government (mil. 2021US$)",    "mil. 2021US$", "economy",     "Real consumption of households and government at current PPPs. Source: PWT 11.0."),
    ("PWT:irr",    "Real internal rate of return",                             "ratio",        "economy",     "Real internal rate of return on capital. Source: PWT 11.0."),
    ("PWT:xr",     "Exchange rate (national currency per USD)",                "LCU/USD",      "economy",     "Exchange rate, national currency per USD (market + estimated). Source: PWT 11.0."),
    ("PWT:pl_gdpo","Price level of GDP output-side (USA GDPo 2021=1)",         "index",        "economy",     "Price level of CGDPo (PPP/XR), price level of USA GDPo in 2021=1. Source: PWT 11.0."),
]

COLS = [ind[0].split(":")[1] for ind in INDICATORS]  # raw column names

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

def build_iso3_map(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        return {r[0]: r[1] for r in cur.fetchall()}

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('PWT', 'Penn World Table 11.0 – GGDC Groningen',
                    'https://www.rug.nl/ggdc/productivity/pwt/',
                    'National accounts data covering 183 countries 1950-2019: real GDP, TFP, human capital, employment, hours worked.')
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
                        (SELECT id FROM sources WHERE short_code = 'PWT'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

# ─── Load & transform ────────────────────────────────────────────────────────

def load_pwt(filepath: str) -> pd.DataFrame:
    df = pd.read_excel(filepath, sheet_name="Data")
    log.info(f"Loaded {len(df):,} rows | {df.countrycode.nunique()} countries | {df.year.min()}–{df.year.max()}")
    return df

def build_db_rows(df: pd.DataFrame, iso3_map: dict) -> list[tuple]:
    rows = []
    skipped = set()

    for _, row in df.iterrows():
        iso3 = str(row.get("countrycode", "")).strip()
        iso_numeric = iso3_map.get(iso3)
        if not iso_numeric:
            skipped.add(iso3)
            continue

        year = str(int(row["year"])) if pd.notna(row["year"]) else None
        if not year:
            continue

        for col in COLS:
            val = row.get(col)
            if pd.isna(val):
                continue
            indicator_code = f"PWT:{col}"
            rows.append((iso_numeric, indicator_code, year, float(val), "A"))

    if skipped:
        log.info(f"Skipped ISO3 codes (no match): {sorted(skipped)}")

    return rows

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def insert_rows(conn, rows: list[tuple]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, rows, page_size=2000)
    conn.commit()
    return len(rows)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Penn World Table 11.0 Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)

    iso3_map = build_iso3_map(conn)
    log.info(f"ISO3 map: {len(iso3_map)} entries")

    df = load_pwt(FILE)
    rows = build_db_rows(df, iso3_map)
    log.info(f"DB rows prepared: {len(rows):,}")

    inserted = insert_rows(conn, rows)
    log.info(f"Inserted: {inserted:,} rows")

    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
