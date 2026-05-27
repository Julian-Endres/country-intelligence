"""
load_ilostat.py — ILOSTAT Labour Indicators
============================================
Source:  ILOSTAT REST API  (rplumber.ilo.org/data/indicator/)
Domain:  Economy / Labour Market
Destination: indicators table (source_code = 'ILO')

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/economy/load_ilostat.py

Resume: safe to re-run — uses ON CONFLICT DO NOTHING.
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

# ─── DB connection ────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

# ─── Indicators ───────────────────────────────────────────────────────────────
# All IDs verified against ILOSTAT TOC (rplumber.ilo.org/metadata/toc/indicator)
# Suffix _A = annual data
# sex filter: keep 'SEX_T' (Total) only
# classif1 filter: None = no classification dimension for this indicator

INDICATORS = [
    {
        "code":          "ILO:EAP_DWAP_SEX_AGE_RT",
        "ilo_id":        "EAP_DWAP_SEX_AGE_RT_A",
        "name":          "Labour force participation rate by sex and age (%)",
        "unit":          "%",
        "category":      "economy",
        "description":   "Labour force participation rate (%), annual, by sex and age. Total = AGE_YTHADULT_YGE15 (15+). Source: ILOSTAT.",
        "classif1_keep": ["AGE_YTHADULT_YGE15"],
    },
    {
        "code":          "ILO:SDG_0852_SEX_AGE_RT",
        "ilo_id":        "SDG_0852_SEX_AGE_RT_A",
        "name":          "Unemployment rate by sex and age — SDG 8.5.2 (%)",
        "unit":          "%",
        "category":      "economy",
        "description":   "SDG 8.5.2 Unemployment rate (%), annual, by sex and age. Total = AGE_YTHADULT_YGE15 (15+). Source: ILOSTAT.",
        "classif1_keep": ["AGE_YTHADULT_YGE15"],
    },
    {
        "code":          "ILO:SDG_0831_SEX_ECO_RT",
        "ilo_id":        "SDG_0831_SEX_ECO_RT_A",
        "name":          "Informal employment rate — SDG 8.3.1 (%)",
        "unit":          "%",
        "category":      "economy",
        "description":   "SDG 8.3.1 Proportion of informal employment in total employment (%), by sex and economic activity. Total economy. Source: ILOSTAT.",
        "classif1_keep": ["ECO_AGGREGATE_TOTAL"],
    },
    {
        "code":          "ILO:EAR_EHRA_SEX_NB",
        "ilo_id":        "EAR_EHRA_SEX_NB_A",
        "name":          "Average hourly earnings of employees by sex (local currency)",
        "unit":          "LCU/hour",
        "category":      "economy",
        "description":   "Average hourly earnings of employees (local currency), annual, by sex. Total = both sexes. Source: ILOSTAT.",
        "classif1_keep": None,
    },
    {
        "code":          "ILO:ILR_TUMT_NOC_RT",
        "ilo_id":        "ILR_TUMT_NOC_RT",
        "name":          "Trade union density rate (%)",
        "unit":          "%",
        "category":      "economy",
        "description":   "Trade union density rate: union members as % of employees. Source: ILOSTAT.",
        "classif1_keep": None,
        "no_sex_filter": True,   # this indicator has no sex dimension
    },
    {
        "code":          "ILO:EMP_2EMP_SEX_STE_NB",
        "ilo_id":        "EMP_2EMP_SEX_STE_NB_A",
        "name":          "Employment by sex and status in employment — ILO modelled (thousands)",
        "unit":          "thousands",
        "category":      "economy",
        "description":   "Employment by sex and status in employment, ILO modelled estimates Nov. 2025 (thousands). Includes employees, self-employed, contributing family workers. Source: ILOSTAT.",
        "classif1_keep": None,   # discover on first run
    },
    {
        "code":          "ILO:EMP_TEMP_SEX_ECO_NB",
        "ilo_id":        "EMP_TEMP_SEX_ECO_NB",
        "name":          "Employment by sex and economic activity (thousands)",
        "unit":          "thousands",
        "category":      "economy",
        "description":   "Employment by sex and economic activity (ISIC Rev.4). Total economy. Source: ILOSTAT.",
        "classif1_keep": ["ECO_ISIC4_TOTAL"],
    },
    {
        "code":          "ILO:HOW_2TOT_SEX_NB",
        "ilo_id":        "HOW_2TOT_SEX_NB_A",
        "name":          "Total weekly hours worked — ILO modelled (thousands of hours)",
        "unit":          "thousands of hours",
        "category":      "economy",
        "description":   "Total weekly hours worked of employed persons by sex, ILO modelled estimates Nov. 2025 (thousands). Source: ILOSTAT.",
        "classif1_keep": None,
    },
]

# ─── ILOSTAT API ──────────────────────────────────────────────────────────────

BASE_URL = "https://rplumber.ilo.org/data/indicator/"

def fetch_indicator(ilo_id: str, timefrom: int = 2000) -> list[dict]:
    params = {
        "id":       ilo_id,
        "timefrom": timefrom,
        "lang":     "en",
        "type":     "code",    # returns ISO3 ref_area codes
        "format":   "json",
    }
    log.info(f"  Fetching {ilo_id} ...")
    r = requests.get(BASE_URL, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()
    log.info(f"  → {len(data):,} raw rows")
    return data

# ─── Country mapping ──────────────────────────────────────────────────────────

def build_country_map(conn) -> dict[str, str]:
    """ISO3 alpha → iso_numeric"""
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        rows = cur.fetchall()
    return {iso3: iso_num for iso3, iso_num in rows}

# ─── Source & metadata ────────────────────────────────────────────────────────

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('ILO', 'ILOSTAT – International Labour Organization',
                    'https://ilostat.ilo.org/',
                    'ILO labour statistics: employment, unemployment, wages, working time, trade unions.')
            ON CONFLICT (short_code) DO NOTHING
        """)
    conn.commit()

def ensure_metadata(conn, ind: dict):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO indicator_metadata
                (indicator_code, name, unit, category, description, source_id)
            VALUES (%s, %s, %s, %s, %s,
                    (SELECT id FROM sources WHERE short_code = 'ILO'))
            ON CONFLICT (indicator_code) DO NOTHING
        """, (ind["code"], ind["name"], ind["unit"], ind["category"], ind["description"]))
    conn.commit()

# ─── Filter & convert ─────────────────────────────────────────────────────────

def filter_rows(raw: list[dict], ind: dict) -> list[dict]:
    no_sex = ind.get("no_sex_filter", False)
    classif1_keep = ind.get("classif1_keep")
    out = []
    classif1_seen = set()

    for row in raw:
        # Sex filter
        if not no_sex and row.get("sex") != "SEX_T":
            continue

        # classif1 discovery logging
        c1 = row.get("classif1", "")
        classif1_seen.add(c1)

        if classif1_keep and c1 not in classif1_keep:
            continue

        val = row.get("obs_value")
        if val is None or val == "":
            continue
        try:
            float(val)
        except (ValueError, TypeError):
            continue

        out.append(row)

    # Log classif1 values seen (helps tune classif1_keep)
    if classif1_keep is None and classif1_seen - {None, ""}:
        log.info(f"  classif1 values: {sorted(str(x) for x in classif1_seen if x)[:10]}")

    return out

def to_db_rows(filtered: list[dict], indicator_code: str, country_map: dict) -> list[tuple]:
    db_rows = []
    skipped = set()
    for row in filtered:
        iso3 = row.get("ref_area", "")
        iso_numeric = country_map.get(iso3)
        if not iso_numeric:
            skipped.add(iso3)
            continue
        year = str(row.get("time", "")).strip()
        if not year.isdigit():
            continue
        value = float(row["obs_value"])
        obs_status = str(row.get("obs_status") or "A")[:10]
        db_rows.append((iso_numeric, indicator_code, year, value, obs_status))

    if skipped:
        log.debug(f"  Skipped ISO3 (no match): {sorted(skipped)[:10]}")
    return db_rows

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

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== ILOSTAT Loader ===")
    conn = get_conn()
    ensure_source(conn)
    country_map = build_country_map(conn)
    log.info(f"Country map: {len(country_map)} ISO3 entries")

    total = 0
    for ind in INDICATORS:
        log.info(f"\n[{ind['code']}] {ind['name']}")
        ensure_metadata(conn, ind)

        try:
            raw = fetch_indicator(ind["ilo_id"])
        except Exception as e:
            log.error(f"  FETCH ERROR: {e}")
            continue

        filtered = filter_rows(raw, ind)
        log.info(f"  After filter: {len(filtered):,} rows")

        db_rows = to_db_rows(filtered, ind["code"], country_map)
        log.info(f"  Mapped to countries: {len(db_rows):,} rows")

        inserted = insert_rows(conn, db_rows)
        log.info(f"  Inserted: {inserted:,}")
        total += inserted
        time.sleep(1.5)

    log.info(f"\n=== Done. Total inserted: {total:,} rows ===")
    conn.close()

if __name__ == "__main__":
    main()