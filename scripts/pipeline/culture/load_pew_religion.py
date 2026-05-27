"""
load_pew_religion.py — Pew Research Religious Composition 2010–2020
=====================================================================
Source:  Pew Research Center – Global Religious Composition Dataset
         Updated Feb 12, 2026 (includes Religious Diversity Index)
Domain:  Culture & Identity / Social Fabric
Destination: indicators table (source_code = 'PEW_REL')

Indicators loaded
-----------------
Percentages (% of population) for 2010 and 2020:
  PEW_REL:christians        % Christians
  PEW_REL:muslims           % Muslims
  PEW_REL:unaffiliated      % Religiously unaffiliated
  PEW_REL:buddhists         % Buddhists
  PEW_REL:hindus            % Hindus
  PEW_REL:jews              % Jews
  PEW_REL:other_religions   % Other religions

Diversity (single year per country):
  PEW_REL:rdi               Religious Diversity Index (0–1)

Coverage: 201 countries/territories with population >= 100k
Country mapping: UN M49 (Countrycode) = iso_numeric (direct match)

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/culture/load_pew_religion.py
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

ZIP_PATH = "data/raw/Manuell_27-05/Religious-Composition-2010-2020-dataset_Pew Research.zip"

INDICATORS = [
    ("PEW_REL:christians",     "Christians (% of population)",               "%",     "culture", "Share of Christians in total population. Source: Pew Research Center."),
    ("PEW_REL:muslims",        "Muslims (% of population)",                  "%",     "culture", "Share of Muslims in total population. Source: Pew Research Center."),
    ("PEW_REL:unaffiliated",   "Religiously unaffiliated (% of population)", "%",     "culture", "Share of religiously unaffiliated in total population. Source: Pew Research Center."),
    ("PEW_REL:buddhists",      "Buddhists (% of population)",                "%",     "culture", "Share of Buddhists in total population. Source: Pew Research Center."),
    ("PEW_REL:hindus",         "Hindus (% of population)",                   "%",     "culture", "Share of Hindus in total population. Source: Pew Research Center."),
    ("PEW_REL:jews",           "Jews (% of population)",                     "%",     "culture", "Share of Jews in total population. Source: Pew Research Center."),
    ("PEW_REL:other_religions","Other religions (% of population)",          "%",     "culture", "Share of other religions in total population. Source: Pew Research Center."),
    ("PEW_REL:rdi",            "Religious Diversity Index (RDI)",            "index", "culture", "Pew RDI: probability that two randomly selected people belong to different religious groups (0=no diversity, 1=max diversity). Source: Pew Research Center 2026."),
]

PCT_COL_MAP = {
    "PEW_REL:christians":     "Christians",
    "PEW_REL:muslims":        "Muslims",
    "PEW_REL:unaffiliated":   "Religiously_unaffiliated",
    "PEW_REL:buddhists":      "Buddhists",
    "PEW_REL:hindus":         "Hindus",
    "PEW_REL:jews":           "Jews",
    "PEW_REL:other_religions":"Other_religions",
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

def build_m49_map(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT iso_numeric FROM countries WHERE iso_numeric IS NOT NULL")
        return {r[0]: r[0] for r in cur.fetchall()}

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('PEW_REL', 'Pew Research Center – Global Religious Composition',
                    'https://www.pewresearch.org/religion/',
                    'Religious composition by country 2010 and 2020: Christians, Muslims, Buddhists, Hindus, Jews, unaffiliated, other. Includes Religious Diversity Index (2026 update).')
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
                        (SELECT id FROM sources WHERE short_code = 'PEW_REL'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def m49_to_iso(code, m49_map):
    return m49_map.get(str(int(code)).zfill(3))

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Pew Religious Composition Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)
    m49_map = build_m49_map(conn)
    log.info(f"M49 map: {len(m49_map)} entries")

    db_rows = []
    skipped = set()

    # ── 1. Percentages (2010 + 2020) ─────────────────────────────────────────
    log.info("Loading percentages CSV...")
    with zipfile.ZipFile(ZIP_PATH) as z:
        with z.open("Religious Composition 2010-2020 dataset/Religious Composition 2010-2020 (percentages).csv") as f:
            df_pct = pd.read_csv(f)

    df_pct = df_pct[df_pct["Level"] == 1].copy()
    log.info(f"  Country-level rows: {len(df_pct):,}")

    for _, row in df_pct.iterrows():
        iso_num = m49_to_iso(row["Countrycode"], m49_map)
        if not iso_num:
            skipped.add(f"{row['Country']} ({row['Countrycode']})")
            continue
        year = str(int(row["Year"]))
        for code, col in PCT_COL_MAP.items():
            val = row.get(col)
            if pd.notna(val):
                db_rows.append((iso_num, code, year, float(val), "A"))

    # ── 2. Religious Diversity Index ──────────────────────────────────────────
    log.info("Loading diversity statistics CSV...")
    try:
        with zipfile.ZipFile(ZIP_PATH) as z:
            with z.open("Religious Composition 2010-2020 dataset/Religious Composition 2010-2020 (diversity statistics).csv") as f:
                df_div = pd.read_csv(f)

        log.info(f"  Diversity columns: {df_div.columns.tolist()}")
        log.info(f"  Rows: {len(df_div):,}")

        # Filter country-level only
        if "Level" in df_div.columns:
            df_div = df_div[df_div["Level"] == 1]

        # Find RDI column (flexible naming)
        rdi_col = None
        for col in df_div.columns:
            if "rdi" in col.lower() or "diversity_index" in col.lower() or "index" in col.lower():
                rdi_col = col
                break

        year_col = "Year" if "Year" in df_div.columns else None

        if rdi_col:
            log.info(f"  RDI column: {rdi_col}")
            for _, row in df_div.iterrows():
                iso_num = m49_to_iso(row["Countrycode"], m49_map)
                if not iso_num:
                    continue
                val = row.get(rdi_col)
                if pd.isna(val):
                    continue
                # Use year if available, else use 2020 as reference
                year = str(int(row[year_col])) if year_col and pd.notna(row.get(year_col)) else "2020"
                db_rows.append((iso_num, "PEW_REL:rdi", year, float(val), "A"))
        else:
            log.warning("  RDI column not found — skipping diversity index")

    except Exception as e:
        log.warning(f"  Could not load diversity CSV: {e}")

    if skipped:
        log.info(f"Skipped ({len(skipped)}): {sorted(skipped)[:10]}")

    log.info(f"Total DB rows: {len(db_rows):,}")

    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, db_rows, page_size=1000)
    conn.commit()

    log.info(f"Inserted: {len(db_rows):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
