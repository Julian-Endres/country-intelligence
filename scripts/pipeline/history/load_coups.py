"""
load_ddr.py — Diplometrics Diplomatic Representation 1960-2024
===============================================================
Source:  Moyer, Turner, Meisel — University of Denver / Pardee Center
Domain:  International Relations
Destination: diplomatic_representation table

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/international/load_ddr.py
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

ZIP_PATH  = "data/raw/Manuell_27-05/dataverse_files_Diplometric.zip"
XLSX_FILE = "Diplometrics_Diplomatic-Representation_1960-2024_20250825.xlsx"

OVERRIDES = {
    "bolivia":                          "BOL",
    "cabo verde":                       "CPV",
    "congo, democratic republic":       "COD",
    "congo, republic":                  "COG",
    "congo-brazzaville":                "COG",
    "congo-kinshasa":                   "COD",
    "czech republic":                   "CZE",
    "czechia":                          "CZE",
    "c\xf4te d\x92ivoire":              "CIV",
    "côte d\x92ivoire":                 "CIV",
    "côte d'ivoire":                    "CIV",
    "ivory coast":                      "CIV",
    "east germany":                     "DEU",
    "west germany":                     "DEU",
    "germany, east":                    "DEU",
    "germany, west":                    "DEU",
    "eswatini":                         "SWZ",
    "swaziland":                        "SWZ",
    "gambia":                           "GMB",
    "gambia, the":                      "GMB",
    "hong kong":                        "HKG",
    "iran":                             "IRN",
    "korea, north":                     "PRK",
    "korea, south":                     "KOR",
    "kosovo":                           "XKX",
    "kyrgyzstan":                       "KGZ",
    "laos":                             "LAO",
    "moldova":                          "MDA",
    "myanmar":                          "MMR",
    "north korea":                      "PRK",
    "north macedonia":                  "MKD",
    "occupied palestinian territory":   "PSE",
    "palestine":                        "PSE",
    "russia":                           "RUS",
    "s. africa":                        "ZAF",
    "s. korea":                         "KOR",
    "saudi arabia":                     "SAU",
    "south korea":                      "KOR",
    "south sudan":                      "SSD",
    "syria":                            "SYR",
    "taiwan":                           "TWN",
    "tanzania":                         "TZA",
    "timor-leste":                      "TLS",
    "east timor":                       "TLS",
    "ussr":                             "RUS",
    "soviet union":                     "RUS",
    "venezuela":                        "VEN",
    "vietnam":                          "VNM",
    "viet nam":                         "VNM",
    "viet nam, democratic rep":         "VNM",
    "viet nam, republic of":            "VNM",
    "yemen, north":                     "YEM",
    "yemen, south":                     "YEM",
    "yemen, people's democratic republic of": "YEM",
    "yugoslavia":                       "SRB",
    "czechoslovakia":                   "CZE",
    "serbia and montenegro":            "SRB",
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

_cache = {}
def resolve(name, iso3_map, name_map):
    if not name or str(name).strip() in ("-", "nan", ""):
        return None
    clean = str(name).strip().lower()
    if clean in _cache: return _cache[clean]
    iso3 = OVERRIDES.get(clean)
    if iso3:
        result = iso3_map.get(iso3)
        _cache[clean] = result
        return result
    iso_num = name_map.get(clean)
    if iso_num:
        _cache[clean] = iso_num
        return iso_num
    try:
        r = pycountry.countries.search_fuzzy(str(name).strip())
        if r:
            result = iso3_map.get(r[0].alpha_3)
            _cache[clean] = result
            return result
    except: pass
    _cache[clean] = None
    return None

def main():
    log.info("=== DDR Loader ===")
    conn = get_conn()
    iso3_map, name_map = build_maps(conn)

    log.info("Reading xlsx from zip...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open(XLSX_FILE) as f:
            df = pd.read_excel(io.BytesIO(f.read()))

    log.info(f"Rows: {len(df):,}")

    rows = []
    skipped = set()

    for _, row in df.iterrows():
        sending = resolve(row.get("SendingCountry"), iso3_map, name_map)
        dest    = resolve(row.get("Destination"), iso3_map, name_map)

        if not sending:
            skipped.add(str(row.get("SendingCountry", "")))
            continue
        if not dest:
            skipped.add(str(row.get("Destination", "")))
            continue

        year = row.get("Year")
        if pd.isna(year):
            continue

        def iv(col):
            v = row.get(col)
            return int(v) if pd.notna(v) else None

        def fv(col):
            v = row.get(col)
            return float(v) if pd.notna(v) else None

        rows.append((
            sending, dest,
            str(row.get("SendingCountry", ""))[:150],
            str(row.get("Destination", ""))[:150],
            int(year),
            iv("Embassy"), iv("Focus"), iv("EmbassyFocus"),
            fv("LOR"),
        ))

    if skipped:
        log.info(f"Skipped ({len(skipped)}): {sorted(skipped)[:15]}")

    log.info(f"Prepared: {len(rows):,} rows")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO diplomatic_representation
                (sending_iso, destination_iso, sending_name, destination_name,
                 year, embassy, focus, embassy_focus, lor)
            VALUES %s
            ON CONFLICT (sending_iso, destination_iso, year) DO NOTHING
        """, rows, page_size=2000)
    conn.commit()
    log.info(f"Inserted: {len(rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()