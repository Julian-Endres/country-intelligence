"""
load_caf_wgi.py — CAF World Giving Index
=========================================
Source:  Charities Aid Foundation (CAF)
         https://www.cafonline.org/research-and-policy/caf-world-giving-index
Domain:  Social Fabric & Daily Life
Destination: indicators table (source_code = 'CAF_WGI')

Indicators loaded (% of respondents)
--------------------------------------
CAF_WGI:total_score          Overall World Giving Index score (%)
CAF_WGI:helping_stranger     % who helped a stranger in the past month
CAF_WGI:donating_money       % who donated money in the past month
CAF_WGI:volunteering_time    % who volunteered time in the past month

Years available:
  ZIP archive: 2010–2018, 2021, 2022  (2019/2020 missing — COVID gap)
  Separate CSVs: 2023, 2024

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/social/load_caf_wgi.py
"""

import os
import zipfile
import io
import logging
import pandas as pd
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ZIP_PATH  = "data/raw/Manuell_27-05/archive_CAF World Giving Index.zip"
CSV_2023  = "data/raw/Manuell_27-05/world_giving_2023_complete.csv"
CSV_2024  = "data/raw/Manuell_27-05/world_giving_2024_complete.csv"

INDICATORS = [
    ("CAF_WGI:total_score",       "World Giving Index total score (%)",          "%", "social", "Overall CAF World Giving Index score: average of helping stranger, donating money and volunteering. Source: CAF."),
    ("CAF_WGI:helping_stranger",  "Helped a stranger in past month (%)",         "%", "social", "% of respondents who helped a stranger in the past month. Source: CAF World Giving Index."),
    ("CAF_WGI:donating_money",    "Donated money in past month (%)",             "%", "social", "% of respondents who donated money to a charity in the past month. Source: CAF World Giving Index."),
    ("CAF_WGI:volunteering_time", "Volunteered time in past month (%)",          "%", "social", "% of respondents who volunteered time in the past month. Source: CAF World Giving Index."),
]

# Manual country name overrides → ISO3
CAF_NAME_OVERRIDES = {
    "bolivia":                          "BOL",
    "congo":                            "COG",
    "democratic republic of congo":     "COD",
    "dr congo":                         "COD",
    "hong kong":                        "HKG",
    "iran":                             "IRN",
    "ivory coast":                      "CIV",
    "kosovo":                           "XKX",
    "kyrgyzstan":                       "KGZ",
    "laos":                             "LAO",
    "moldova":                          "MDA",
    "myanmar":                          "MMR",
    "palestine":                        "PSE",
    "russia":                           "RUS",
    "south korea":                      "KOR",
    "syria":                            "SYR",
    "taiwan":                           "TWN",
    "tanzania":                         "TZA",
    "trinidad & tobago":                "TTO",
    "trinidad and tobago":              "TTO",
    "united kingdom":                   "GBR",
    "united states":                    "USA",
    "venezuela":                        "VEN",
    "vietnam":                          "VNM",
}

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

def build_maps(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        iso3_map = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT LOWER(name), iso_numeric FROM countries")
        name_map = {r[0]: r[1] for r in cur.fetchall()}
    return iso3_map, name_map

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('CAF_WGI', 'CAF World Giving Index',
                    'https://www.cafonline.org/research-and-policy/caf-world-giving-index',
                    'Annual survey of giving behaviour: helping strangers, donating money, volunteering time. ~140 countries via Gallup World Poll.')
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
                        (SELECT id FROM sources WHERE short_code = 'CAF_WGI'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

# ─── Parse ───────────────────────────────────────────────────────────────────

def parse_pct(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace("%", "").replace(",", ".")
    if s in ("", "-", "nan", "N/A", "n/a"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def resolve_country(name: str, iso3_map: dict, name_map: dict) -> str | None:
    clean = name.strip().lower()
    # Manual override
    iso3 = CAF_NAME_OVERRIDES.get(clean)
    if iso3:
        return iso3_map.get(iso3)
    # Direct name match
    iso_num = name_map.get(clean)
    if iso_num:
        return iso_num
    # pycountry fuzzy
    try:
        result = pycountry.countries.search_fuzzy(name.strip())
        if result:
            return iso3_map.get(result[0].alpha_3)
    except Exception:
        pass
    return None

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names across different CSV formats."""
    # Handle BOM in column names
    df.columns = [c.strip().lstrip('\ufeff') for c in df.columns]

    # If single column with semicolons → split
    if len(df.columns) == 1:
        df = df.iloc[:, 0].str.split(";", expand=True)
        df.columns = ["Country", "Total Ranking", "Total Score",
                      "Helping a stranger Ranking", "Helping a stranger Score",
                      "Donating money Ranking", "Donating money Score",
                      "Volunteering time Ranking", "Volunteering time Score"]

    # Normalize column names
    rename = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl in ("country",):
            rename[col] = "country"
        elif "total" in cl and "score" in cl:
            rename[col] = "total_score"
        elif "helping" in cl and "score" in cl:
            rename[col] = "helping_score"
        elif "donat" in cl and "score" in cl:
            rename[col] = "donating_score"
        elif "volunteer" in cl and "score" in cl:
            rename[col] = "volunteering_score"
    df = df.rename(columns=rename)
    return df

# ─── Load files ───────────────────────────────────────────────────────────────

def load_from_zip(zip_path: str) -> list[tuple]:
    """Returns list of (country_name, year, col_name, value)"""
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.endswith(".csv"):
                continue
            year = name.replace(".csv", "").strip()
            if not year.isdigit():
                continue
            with z.open(name) as f:
                df = pd.read_csv(f, sep=None, engine="python")
            df = normalize_df(df)
            for _, row in df.iterrows():
                country = str(row.get("country", "")).strip()
                if not country:
                    continue
                rows.append((country, int(year), "total_score",       parse_pct(row.get("total_score"))))
                rows.append((country, int(year), "helping_score",     parse_pct(row.get("helping_score"))))
                rows.append((country, int(year), "donating_score",    parse_pct(row.get("donating_score"))))
                rows.append((country, int(year), "volunteering_score",parse_pct(row.get("volunteering_score"))))
    return rows

def load_from_csv(path: str, year: int) -> list[tuple]:
    rows = []
    df = pd.read_csv(path, sep=None, engine="python")
    df = normalize_df(df)
    for _, row in df.iterrows():
        country = str(row.get("country", "")).strip()
        if not country:
            continue
        rows.append((country, year, "total_score",        parse_pct(row.get("total_score"))))
        rows.append((country, year, "helping_score",      parse_pct(row.get("helping_score"))))
        rows.append((country, year, "donating_score",     parse_pct(row.get("donating_score"))))
        rows.append((country, year, "volunteering_score", parse_pct(row.get("volunteering_score"))))
    return rows

# ─── Insert ───────────────────────────────────────────────────────────────────

COL_TO_CODE = {
    "total_score":        "CAF_WGI:total_score",
    "helping_score":      "CAF_WGI:helping_stranger",
    "donating_score":     "CAF_WGI:donating_money",
    "volunteering_score": "CAF_WGI:volunteering_time",
}

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def main():
    log.info("=== CAF World Giving Index Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)
    iso3_map, name_map = build_maps(conn)

    # Collect all raw rows
    all_raw = []
    all_raw += load_from_zip(ZIP_PATH)
    all_raw += load_from_csv(CSV_2023, 2023)
    all_raw += load_from_csv(CSV_2024, 2024)
    log.info(f"Total raw rows: {len(all_raw):,}")

    db_rows = []
    skipped = set()

    for country, year, col, value in all_raw:
        if value is None:
            continue
        indicator_code = COL_TO_CODE.get(col)
        if not indicator_code:
            continue
        iso_num = resolve_country(country, iso3_map, name_map)
        if not iso_num:
            skipped.add(country)
            continue
        db_rows.append((iso_num, indicator_code, str(year), value, "A"))

    if skipped:
        log.info(f"Skipped ({len(skipped)}): {sorted(skipped)[:15]}")

    log.info(f"DB rows prepared: {len(db_rows):,}")

    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, db_rows, page_size=1000)
    conn.commit()

    log.info(f"Inserted: {len(db_rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
