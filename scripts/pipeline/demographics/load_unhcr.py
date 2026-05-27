"""
load_unhcr.py — UNHCR Refugee & Displacement Data
==================================================
Source:  UNHCR Global Public API  (https://api.unhcr.org/population/v1/)
Domain:  Demographics / Migration
Destination: indicators table (source_code = 'UNHCR')

Two separate API calls:
  1. coo_all=true  → data aggregated by country of ORIGIN
  2. coa_all=true  → data aggregated by country of ASYLUM

Indicators
----------
UNHCR:refugees_origin       Refugees by country of origin
UNHCR:refugees_asylum       Refugees hosted by country of asylum
UNHCR:asylum_seekers        Asylum seekers (hosted)
UNHCR:idps                  Internally displaced persons (by origin country)
UNHCR:stateless             Stateless persons (by asylum country)
UNHCR:returned_refugees     Returned refugees (to origin country)

Run
---
  python scripts/pipeline/demographics/load_unhcr.py
"""

import os
import time
import logging
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://api.unhcr.org/population/v1/population/"

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

def build_country_map(conn) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        return {iso3: iso_num for iso3, iso_num in cur.fetchall()}

# ─── Source & metadata ────────────────────────────────────────────────────────

INDICATORS = [
    ("UNHCR:refugees_origin",     "Refugees by country of origin",              "persons", "demographics", "Total refugees originating from this country. Source: UNHCR."),
    ("UNHCR:refugees_asylum",     "Refugees hosted by country of asylum",        "persons", "demographics", "Total refugees hosted in this country. Source: UNHCR."),
    ("UNHCR:asylum_seekers",      "Asylum seekers (pending cases, hosted)",      "persons", "demographics", "Pending asylum seeker cases in this country. Source: UNHCR."),
    ("UNHCR:idps",                "Internally displaced persons (IDPs)",         "persons", "demographics", "IDPs within this country. Source: UNHCR."),
    ("UNHCR:stateless",           "Stateless persons",                           "persons", "demographics", "Stateless persons in this country. Source: UNHCR."),
    ("UNHCR:returned_refugees",   "Returned refugees (during year)",             "persons", "demographics", "Refugees returned to country of origin during the year. Source: UNHCR."),
]

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('UNHCR', 'UNHCR – UN Refugee Agency',
                    'https://api.unhcr.org/population/v1/',
                    'UNHCR global displacement: refugees, asylum seekers, IDPs, stateless persons.')
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
                        (SELECT id FROM sources WHERE short_code = 'UNHCR'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch_all_pages(extra_params: dict, year_from=2000, year_to=2024) -> list[dict]:
    items = []
    page = 1
    max_pages = None
    while True:
        params = {"limit": 1000, "page": page,
                  "yearFrom": year_from, "yearTo": year_to,
                  **extra_params}
        r = requests.get(BASE_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        batch = data.get("items", [])
        items.extend(batch)
        max_pages = data.get("maxPages", 1)
        log.info(f"    page {page}/{max_pages} → {len(batch)} items")
        if page >= max_pages:
            break
        page += 1
        time.sleep(0.3)
    return items

# ─── Insert ───────────────────────────────────────────────────────────────────

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def insert_rows(conn, rows: list[tuple]) -> int:
    if not rows:
        return 0
    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, rows, page_size=1000)
    conn.commit()
    return len(rows)

def val(x):
    """Safe float conversion, None if missing or '-'."""
    if x is None or x == "-" or x == "0" or x == 0:
        return None
    try:
        v = float(x)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== UNHCR Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)
    country_map = build_country_map(conn)
    log.info(f"Country map: {len(country_map)} ISO3 entries")

    total = 0

    # ── 1. Country of Origin ─────────────────────────────────────────────────
    log.info("\nFetching by country of origin (coo_all) ...")
    coo_items = fetch_all_pages({"coo_all": "true"})
    log.info(f"Total COO rows: {len(coo_items):,}")

    coo_rows = []
    for row in coo_items:
        iso3 = row.get("coo_iso", "")
        if not iso3 or iso3 == "-":
            continue
        iso_num = country_map.get(iso3)
        if not iso_num:
            continue
        year = str(row.get("year", ""))
        if not year.isdigit():
            continue

        for code, field in [
            ("UNHCR:refugees_origin",   "refugees"),
            ("UNHCR:returned_refugees", "returned_refugees"),
            ("UNHCR:idps",              "idps"),
        ]:
            v = val(row.get(field))
            if v is not None:
                coo_rows.append((iso_num, code, year, v, "A"))

    inserted = insert_rows(conn, coo_rows)
    log.info(f"COO inserted: {inserted:,} rows")
    total += inserted

    # ── 2. Country of Asylum ──────────────────────────────────────────────────
    log.info("\nFetching by country of asylum (coa_all) ...")
    coa_items = fetch_all_pages({"coa_all": "true"})
    log.info(f"Total COA rows: {len(coa_items):,}")

    coa_rows = []
    for row in coa_items:
        iso3 = row.get("coa_iso", "")
        if not iso3 or iso3 == "-":
            continue
        iso_num = country_map.get(iso3)
        if not iso_num:
            continue
        year = str(row.get("year", ""))
        if not year.isdigit():
            continue

        for code, field in [
            ("UNHCR:refugees_asylum", "refugees"),
            ("UNHCR:asylum_seekers",  "asylum_seekers"),
            ("UNHCR:stateless",       "stateless"),
        ]:
            v = val(row.get(field))
            if v is not None:
                coa_rows.append((iso_num, code, year, v, "A"))

    inserted = insert_rows(conn, coa_rows)
    log.info(f"COA inserted: {inserted:,} rows")
    total += inserted

    log.info(f"\n=== Done. Total inserted: {total:,} rows ===")
    conn.close()

if __name__ == "__main__":
    main()