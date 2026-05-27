"""
load_wid.py — World Inequality Database (WID.world)
=====================================================
Source:  WID.world — World Inequality Lab (Piketty, Saez, Chancel et al.)
         https://wid.world/
Domain:  Economy / Inequality / Elites
Destination: indicators table (source_code = 'WID')

Variables loaded
----------------
Shares (s*) — income/wealth share held by percentile group:
  sptincj992   Pre-tax national income share
  sdiincj992   Post-tax national income share
  shwealj992   Net personal wealth share
  sfiinct992   Fiscal income share
  scaincj992   Post-tax private income share
  spllinf992   Pre-tax labor income share

Gini coefficients (g*):
  gptincj992   Gini pre-tax national income
  gdiincj992   Gini post-tax national income
  ghwealj992   Gini net personal wealth
  gcaincj992   Gini post-tax private income

Top10/Bottom50 ratio (r*):
  rptincj992   Pre-tax income T10/B50 ratio
  rdiincj992   Post-tax income T10/B50 ratio
  rhwealj992   Wealth T10/B50 ratio

Thresholds (t*) — minimum income/wealth to belong to group:
  tptincj992   Pre-tax income threshold
  tdiincj992   Post-tax income threshold
  thwealj992   Wealth threshold

Percentiles loaded
------------------
Shares:     p0p50 (bottom 50%), p90p100 (top 10%), p99p100 (top 1%)
Gini:       p0p100 (total population)
Ratios:     p0p100
Thresholds: p90p100, p99p100

Country mapping
---------------
WID uses ISO 3166-1 alpha-2 codes (mostly). Some are WID-specific
(e.g. 'CN-RU' for rural China). We skip non-standard codes.

Theoretical potential (not loaded)
-----------------------------------
- 692 Average variables: avg income/wealth per percentile group
- 327 % of GDP macro aggregates (overlaps with WB/PWT)
- 26 Emissions-by-income-group variables (CO2 of top 10% vs bottom 50%)
  → unique dataset, strong visualization potential, load in future sprint

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/economy/load_wid.py
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

ZIP_PATH = "data/raw/Manuell_27-05/wid_all_data.zip"

# ─── Target variables & percentiles ──────────────────────────────────────────

TARGET_VARS = {
    # Shares
    "sptincj992", "sdiincj992", "shwealj992", "sfiinct992",
    "scaincj992", "spllinf992",
    # Gini
    "gptincj992", "gdiincj992", "ghwealj992", "gcaincj992",
    # T10/B50 ratio
    "rptincj992", "rdiincj992", "rhwealj992",
    # Thresholds
    "tptincj992", "tdiincj992", "thwealj992",
    # Emissions (unique — not available elsewhere)
    "lpfghgi999",   # avg per capita GHG by income group
    "ehfcari999",   # total household carbon footprint
    "khfcari999",   # per capita household carbon footprint
    "khfghgi999",   # per capita household GHG
}

SHARE_PCTS     = {"p0p50", "p90p100", "p99p100"}
GINI_PCTS      = {"p0p100"}
RATIO_PCTS     = {"p0p100"}
THRESHOLD_PCTS = {"p90p100", "p99p100"}
EMISS_GROUP    = {"p0p50", "p90p100", "p99p100", "p0p100"}
EMISS_TOTAL    = {"p0p100"}

VAR_PCT_MAP = {
    "sptincj992": SHARE_PCTS, "sdiincj992": SHARE_PCTS,
    "shwealj992": SHARE_PCTS, "sfiinct992": SHARE_PCTS,
    "scaincj992": SHARE_PCTS, "spllinf992": SHARE_PCTS,
    "gptincj992": GINI_PCTS,  "gdiincj992": GINI_PCTS,
    "ghwealj992": GINI_PCTS,  "gcaincj992": GINI_PCTS,
    "rptincj992": RATIO_PCTS, "rdiincj992": RATIO_PCTS,
    "rhwealj992": RATIO_PCTS,
    "tptincj992": THRESHOLD_PCTS, "tdiincj992": THRESHOLD_PCTS,
    "thwealj992": THRESHOLD_PCTS,
    # Emissions
    "lpfghgi999": EMISS_GROUP,
    "ehfcari999": EMISS_TOTAL,
    "khfcari999": EMISS_TOTAL,
    "khfghgi999": EMISS_TOTAL,
}

# ─── Indicator metadata ───────────────────────────────────────────────────────

INDICATORS = [
    # Shares
    ("WID:sptincj992", "Pre-tax national income share by percentile",        "share", "economy", "Share of pre-tax national income held by percentile group (p0p50/p90p100/p99p100). Source: WID.world."),
    ("WID:sdiincj992", "Post-tax national income share by percentile",       "share", "economy", "Share of post-tax national income held by percentile group. Source: WID.world."),
    ("WID:shwealj992", "Net personal wealth share by percentile",            "share", "economy", "Share of net personal wealth held by percentile group. Source: WID.world."),
    ("WID:sfiinct992", "Fiscal income share by percentile",                  "share", "economy", "Share of fiscal income held by percentile group. Source: WID.world."),
    ("WID:scaincj992", "Post-tax private income share by percentile",        "share", "economy", "Share of post-tax private income held by percentile group. Source: WID.world."),
    ("WID:spllinf992", "Pre-tax labor income share by percentile",           "share", "economy", "Share of pre-tax labor income held by percentile group. Source: WID.world."),
    # Gini
    ("WID:gptincj992", "Gini coefficient — pre-tax national income",         "gini",  "economy", "Gini coefficient of pre-tax national income distribution. Source: WID.world."),
    ("WID:gdiincj992", "Gini coefficient — post-tax national income",        "gini",  "economy", "Gini coefficient of post-tax national income distribution. Source: WID.world."),
    ("WID:ghwealj992", "Gini coefficient — net personal wealth",             "gini",  "economy", "Gini coefficient of net personal wealth distribution. Source: WID.world."),
    ("WID:gcaincj992", "Gini coefficient — post-tax private income",         "gini",  "economy", "Gini coefficient of post-tax private income distribution. Source: WID.world."),
    # Ratios
    ("WID:rptincj992", "Top 10% / Bottom 50% ratio — pre-tax income",        "ratio", "economy", "Ratio of average pre-tax income of top 10% to bottom 50%. Source: WID.world."),
    ("WID:rdiincj992", "Top 10% / Bottom 50% ratio — post-tax income",       "ratio", "economy", "Ratio of average post-tax income of top 10% to bottom 50%. Source: WID.world."),
    ("WID:rhwealj992", "Top 10% / Bottom 50% ratio — wealth",                "ratio", "economy", "Ratio of average wealth of top 10% to bottom 50%. Source: WID.world."),
    # Thresholds
    ("WID:tptincj992", "Pre-tax income threshold (local currency)",          "LCU",   "economy", "Minimum pre-tax income to belong to top 10%/top 1% (local currency). Source: WID.world."),
    ("WID:tdiincj992", "Post-tax income threshold (local currency)",         "LCU",   "economy", "Minimum post-tax income to belong to top 10%/top 1% (local currency). Source: WID.world."),
    ("WID:thwealj992", "Wealth threshold (local currency)",                  "LCU",       "economy",     "Minimum wealth to belong to top 10%/top 1% (local currency). Source: WID.world."),
    # Emissions by income group (unique — not in OWID/WB)
    ("WID:lpfghgi999", "Avg per capita GHG emissions by income group",       "tCO2eq/yr", "environment", "Average per capita GHG emissions by income percentile group. Source: WID.world / Chancel et al."),
    ("WID:ehfcari999", "Total household carbon footprint",                   "MtCO2",     "environment", "Total carbon footprint of households. Source: WID.world."),
    ("WID:khfcari999", "Per capita household carbon footprint",              "tCO2/yr",   "environment", "Per capita household carbon footprint. Source: WID.world."),
    ("WID:khfghgi999", "Per capita household GHG emissions",                 "tCO2eq/yr", "environment", "Per capita household greenhouse gas emissions. Source: WID.world."),
]

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )

def build_iso2_map(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_2, iso_numeric FROM countries WHERE iso_code_2 IS NOT NULL")
        return {r[0]: r[1] for r in cur.fetchall()}

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('WID', 'WID.world — World Inequality Database',
                    'https://wid.world/',
                    'Income and wealth inequality data: pre/post-tax income shares, wealth shares, Gini coefficients, T10/B50 ratios. Piketty, Saez, Chancel et al.')
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
                        (SELECT id FROM sources WHERE short_code = 'WID'))
                ON CONFLICT (indicator_code) DO NOTHING
            """, (code, name, unit, cat, desc))
    conn.commit()

# ─── Load & insert ────────────────────────────────────────────────────────────

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def process_file(fname: str, z: zipfile.ZipFile, iso2_map: dict) -> list[tuple]:
    """Process one WID_data_XX.csv file, return DB rows."""
    # Extract ISO2 from filename: WID_data_DE.csv → DE
    iso2 = fname.replace("WID_data_", "").replace(".csv", "").strip()

    # Skip regional/subregional codes (contain '-', digits, or are >2 chars non-standard)
    if len(iso2) != 2 or not iso2.isalpha():
        return []

    iso_numeric = iso2_map.get(iso2.upper())
    if not iso_numeric:
        return []

    with z.open(fname) as f:
        df = pd.read_csv(f, sep=";", low_memory=False)

    rows = []
    for var, allowed_pcts in VAR_PCT_MAP.items():
        subset = df[(df["variable"] == var) & (df["percentile"].isin(allowed_pcts))]
        for _, row in subset.iterrows():
            val = row.get("value")
            if pd.isna(val):
                continue
            year = str(int(row["year"])) if pd.notna(row.get("year")) else None
            if not year:
                continue
            pct = row["percentile"]
            indicator_code = f"WID:{var}:{pct}"
            rows.append((iso_numeric, indicator_code, year, float(val), "A"))

    return rows

def ensure_percentile_metadata(conn):
    """Create indicator_metadata entries for each var:percentile combo."""
    base = {ind[0].split(":")[1]: ind for ind in INDICATORS}  # var → (code, name, unit, cat, desc)

    for var, pcts in VAR_PCT_MAP.items():
        base_entry = base.get(var)
        if not base_entry:
            continue
        _, base_name, unit, cat, desc = base_entry
        for pct in pcts:
            code = f"WID:{var}:{pct}"
            pct_label = {
                "p0p50":    "Bottom 50%",
                "p90p100":  "Top 10%",
                "p99p100":  "Top 1%",
                "p0p100":   "Total population",
            }.get(pct, pct)
            name = f"{base_name} — {pct_label}"
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO indicator_metadata
                        (indicator_code, name, unit, category, description, source_id)
                    VALUES (%s, %s, %s, %s, %s,
                            (SELECT id FROM sources WHERE short_code = 'WID'))
                    ON CONFLICT (indicator_code) DO NOTHING
                """, (code, name, unit, cat, desc))
    conn.commit()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== WID.world Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)
    ensure_percentile_metadata(conn)

    iso2_map = build_iso2_map(conn)
    log.info(f"ISO2 map: {len(iso2_map)} entries")

    total = 0
    batch = []
    BATCH_SIZE = 50000

    with zipfile.ZipFile(ZIP_PATH) as z:
        data_files = [f for f in z.namelist() if f.startswith("WID_data_") and f.endswith(".csv")]
        log.info(f"Data files: {len(data_files)}")

        for i, fname in enumerate(data_files):
            rows = process_file(fname, z, iso2_map)
            batch.extend(rows)

            if len(batch) >= BATCH_SIZE:
                with conn.cursor() as cur:
                    execute_values(cur, INSERT_SQL, batch, page_size=2000)
                conn.commit()
                total += len(batch)
                log.info(f"  [{i+1}/{len(data_files)}] Committed {total:,} rows so far...")
                batch = []

        # Final batch
        if batch:
            with conn.cursor() as cur:
                execute_values(cur, INSERT_SQL, batch, page_size=2000)
            conn.commit()
            total += len(batch)

    log.info(f"\n=== Done. Total inserted: {total:,} rows ===")
    conn.close()

if __name__ == "__main__":
    main()
