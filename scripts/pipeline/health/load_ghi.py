"""
load_ghi.py — Global Hunger Index
===================================
Source:  Concern Worldwide / Welthungerhilfe
Domain:  Health / Food Security
Destination: indicators table (source_code = 'GHI')

Files:
  data/raw/health/2022_global hunger index.csv     (latin-1 encoding)
  data/raw/health/2023 global hunger index.csv
  data/raw/health/2024_global hunger index.xlsx    (sheet: '2024 GHI Scores')
  data/raw/health/2025_global Hunger index.xlsx    (sheet: 'GHI Scores 2025 ')
  data/raw/health/archive_global hunger index.zip  (historical OWID CSVs)

GHI:score  — GHI Score (0=no hunger, 100=extreme hunger)
             '<5' stored as 2.5

Run
---
  python scripts/pipeline/health/load_ghi.py
"""

import os
import zipfile
import logging
import pandas as pd
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

RAW_DIR = "data/raw/health"

OVERRIDES = {
    "bolivia (plurinational state of)": "BOL",
    "bosnia & herzegovina":             "BIH",
    "cabo verde":                       "CPV",
    "central african republic":         "CAF",
    "congo (republic of)":              "COG",
    "côte d'ivoire":                    "CIV",
    "cote d'ivoire":                    "CIV",
    "dem. rep. of the congo":           "COD",
    "democratic republic of the congo": "COD",
    "dominican republic":               "DOM",
    "dpr korea":                        "PRK",
    "eswatini":                         "SWZ",
    "gambia":                           "GMB",
    "guinea-bissau":                    "GNB",
    "iran (islamic republic of)":       "IRN",
    "korea (democratic people's rep.)": "PRK",
    "kyrgyzstan":                       "KGZ",
    "lao pdr":                          "LAO",
    "lao people's democratic republic": "LAO",
    "laos":                             "LAO",
    "moldova (republic of)":            "MDA",
    "myanmar":                          "MMR",
    "north korea":                      "PRK",
    "papua new guinea":                 "PNG",
    "sao tome & principe":              "STP",
    "sao tome and principe":            "STP",
    "solomon islands":                  "SLB",
    "south sudan":                      "SSD",
    "sri lanka":                        "LKA",
    "state of palestine":               "PSE",
    "syria":                            "SYR",
    "syrian arab republic":             "SYR",
    "tanzania":                         "TZA",
    "tanzania (united rep. of)":        "TZA",
    "timor-leste":                      "TLS",
    "trinidad & tobago":                "TTO",
    "united republic of tanzania":      "TZA",
    "venezuela (bolivarian rep. of)":   "VEN",
    "venezuela (boliv. rep. of)":       "VEN",
    "bolivia (plurinat. state of)":     "BOL",
    "democratic republic of congo":     "COD",
    "korea (dpr)":                      "PRK",
    "moldova (rep. of)":                "MDA",
    "viet nam":                         "VNM",
    "vietnam":                          "VNM",
    "yemen":                            "YEM",
    "zambia":                           "ZMB",
    "zimbabwe":                         "ZWE",
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

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('GHI', 'Global Hunger Index – Concern Worldwide / Welthungerhilfe',
                    'https://www.globalhungerindex.org/',
                    'Annual GHI scores: undernourishment, child wasting, stunting, child mortality.')
            ON CONFLICT (short_code) DO NOTHING
        """)
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, category, description, source_id)
            VALUES ('GHI:score', 'Global Hunger Index Score', 'score', 'health',
                    'GHI score (0=no hunger to 100=extreme hunger). Scores <5 stored as 2.5.',
                    (SELECT id FROM sources WHERE short_code = 'GHI'))
            ON CONFLICT (indicator_code) DO NOTHING
        """)
    conn.commit()

def resolve(name, iso3_map, name_map):
    clean = str(name).strip().lower()
    iso3 = OVERRIDES.get(clean)
    if iso3: return iso3_map.get(iso3)
    r = name_map.get(clean)
    if r: return r
    try:
        res = pycountry.countries.search_fuzzy(str(name).strip())
        if res: return iso3_map.get(res[0].alpha_3)
    except: pass
    return None

def parse_val(v):
    if v is None: return None
    s = str(v).strip()
    if s in ('—', '-', '', 'nan', 'NaN', '*', 'N/A'): return None
    if s == '<5': return 2.5
    try: return float(s)
    except: return None

def collect_rows(raw_rows, iso3_map, name_map):
    out = {}
    skipped = set()
    for country, year, value in raw_rows:
        if value is None: continue
        iso_num = resolve(country, iso3_map, name_map)
        if not iso_num:
            skipped.add(country)
            continue
        key = (iso_num, str(year))
        out[key] = value
    return out, skipped

# ── Loaders ──────────────────────────────────────────────────────────────────

def load_2022_csv(path):
    rows = []
    df = pd.read_csv(path, encoding='latin-1')  # kein skiprows!
    # Erste Zeile ist ein Sub-Header (since 2014) — überspringen
    df = df[df['Country'].notna() & (df['Country'] != 'NaN')]
    for _, row in df.iterrows():
        country = str(row.get('Country', '')).strip()
        if not country or country.lower() == 'nan': continue
        for yr in ['2000', '2007', '2014', '2022']:
            v = parse_val(row.get(yr))
            if v is not None:
                rows.append((country, int(yr), v))
    return rows

def load_2023_csv(path):
    rows = []
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        country = str(row.get('Country', '')).strip()
        if not country or country.lower() == 'nan': continue
        for yr in ['2000', '2008', '2015', '2023']:
            v = parse_val(row.get(yr))
            if v is not None:
                rows.append((country, int(yr), v))
    return rows

def load_xlsx(path, score_sheet, report_year):
    rows = []
    df = pd.read_excel(path, sheet_name=score_sheet, skiprows=2, header=None, engine='openpyxl')
    # Cols: 0=country, 1=2000, 2=2008/2007, 3=2015/2016, 4=report_year
    years_map = {1: 2000, 2: 2008, 3: 2016, 4: report_year}
    if report_year == 2024:
        years_map = {1: 2000, 2: 2008, 3: 2016, 4: 2024}
    if report_year == 2025:
        years_map = {1: 2000, 2: 2008, 3: 2016, 4: 2025}

    for _, row in df.iterrows():
        country = str(row.iloc[0]).strip()
        if not country or country.lower() in ('nan', 'country'): continue
        for col_idx, yr in years_map.items():
            if col_idx < len(row):
                v = parse_val(row.iloc[col_idx])
                if v is not None:
                    rows.append((country, yr, v))
    return rows

def load_archive_zip(path):
    rows = []
    with zipfile.ZipFile(path) as z:
        if 'global-hunger-index.csv' in z.namelist():
            with z.open('global-hunger-index.csv') as f:
                df = pd.read_csv(f)
            # Cols: Entity, Code, Year, GHI score
            score_col = [c for c in df.columns if 'hunger' in c.lower() or 'ghi' in c.lower() or 'index' in c.lower()]
            if score_col:
                for _, row in df.iterrows():
                    country = str(row.get('Entity', '')).strip()
                    year = row.get('Year')
                    v = parse_val(row.get(score_col[0]))
                    if country and pd.notna(year) and v is not None:
                        rows.append((country, int(year), v))
    return rows

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Global Hunger Index Loader ===")
    conn = get_conn()
    ensure_source(conn)
    iso3_map, name_map = build_maps(conn)

    all_kv = {}
    all_skipped = set()

    # 2022 CSV
    log.info("Loading 2022 CSV...")
    r, s = collect_rows(load_2022_csv(f"{RAW_DIR}/2022_global hunger index.csv"), iso3_map, name_map)
    all_kv.update(r); all_skipped.update(s)
    log.info(f"  {len(r)} pairs")

    # 2023 CSV
    log.info("Loading 2023 CSV...")
    r, s = collect_rows(load_2023_csv(f"{RAW_DIR}/2023 global hunger index.csv"), iso3_map, name_map)
    all_kv.update(r); all_skipped.update(s)
    log.info(f"  {len(r)} pairs")

    # 2024 xlsx
    log.info("Loading 2024 xlsx...")
    r, s = collect_rows(load_xlsx(f"{RAW_DIR}/2024_global hunger index.xlsx", "2024 GHI Scores", 2024), iso3_map, name_map)
    all_kv.update(r); all_skipped.update(s)
    log.info(f"  {len(r)} pairs")

    # 2025 xlsx
    log.info("Loading 2025 xlsx...")
    r, s = collect_rows(load_xlsx(f"{RAW_DIR}/2025_global Hunger index.xlsx", "GHI Scores 2025 ", 2025), iso3_map, name_map)
    all_kv.update(r); all_skipped.update(s)
    log.info(f"  {len(r)} pairs")

    # Archive ZIP
    log.info("Loading archive ZIP...")
    r, s = collect_rows(load_archive_zip(f"{RAW_DIR}/archive_global hunger index.zip"), iso3_map, name_map)
    all_kv.update(r); all_skipped.update(s)
    log.info(f"  {len(r)} pairs")

    if all_skipped:
        log.info(f"Skipped ({len(all_skipped)}): {sorted(all_skipped)[:15]}")

    db_rows = [(iso_num, "GHI:score", year, value, "A") for (iso_num, year), value in all_kv.items()]
    log.info(f"Total unique pairs: {len(db_rows):,}")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
            VALUES %s ON CONFLICT DO NOTHING
        """, db_rows, page_size=500)
    conn.commit()
    log.info(f"Inserted: {len(db_rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()