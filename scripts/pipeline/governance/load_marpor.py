"""
load_marpor.py — Manifesto Project (MARPOR) 2025a
===================================================
Source:  Manifesto Project / WZB Berlin
         https://manifesto-project.wzb.eu/
Domain:  Politics & Governance
Destination:
  - political_parties   (from parties_MPDataset_MPDS2025a.csv)
  - marpor_elections    (from MPDataset_MPDS2025a.csv)

Country mapping
---------------
MARPOR uses numeric country codes (11=Sweden, 41=Germany etc.)
We map via countryname using pycountry fuzzy matching + manual overrides.

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/governance/load_marpor.py
"""

import os
import logging
import pandas as pd
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PARTIES_FILE   = "data/raw/Manuell_27-05/parties_MPDataset_MPDS2025a.csv"
ELECTIONS_FILE = "data/raw/Manuell_27-05/MPDataset_MPDS2025a.csv"

# ─── Manual country name overrides ───────────────────────────────────────────

MARPOR_COUNTRY_MAP = {
    "sweden":               "SWE", "norway":               "NOR",
    "denmark":              "DNK", "finland":              "FIN",
    "iceland":              "ISL", "belgium":              "BEL",
    "netherlands":          "NLD", "luxembourg":           "LUX",
    "france":               "FRA", "italy":                "ITA",
    "spain":                "ESP", "greece":               "GRC",
    "portugal":             "PRT", "germany":              "DEU",
    "austria":              "AUT", "switzerland":          "CHE",
    "great britain":        "GBR", "northern ireland":     "GBR",
    "ireland":              "IRL", "malta":                "MLT",
    "cyprus":               "CYP", "united states":        "USA",
    "canada":               "CAN", "australia":            "AUS",
    "new zealand":          "NZL", "japan":                "JPN",
    "israel":               "ISR", "sri lanka":            "LKA",
    "turkey":               "TUR", "albania":              "ALB",
    "armenia":              "ARM", "azerbaijan":           "AZE",
    "belarus":              "BLR", "bosnia-herzegovina":   "BIH",
    "bulgaria":             "BGR", "croatia":              "HRV",
    "czech republic":       "CZE", "estonia":              "EST",
    "georgia":              "GEO", "german democratic republic": "DEU",
    "hungary":              "HUN", "latvia":               "LVA",
    "lithuania":            "LTU", "north macedonia":      "MKD",
    "moldova":              "MDA", "montenegro":           "MNE",
    "poland":               "POL", "romania":              "ROU",
    "russia":               "RUS", "serbia":               "SRB",
    "slovakia":             "SVK", "slovenia":             "SVN",
    "ukraine":              "UKR", "south korea":          "KOR",
    "argentina":            "ARG", "bolivia":              "BOL",
    "colombia":             "COL", "costa rica":           "CRI",
    "ecuador":              "ECU", "chile":                "CHL",
    "panama":               "PAN", "uruguay":              "URY",
    "dominican republic":   "DOM", "mexico":               "MEX",
    "peru":                 "PER", "brazil":               "BRA",
    "south africa":         "ZAF",
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

def build_iso3_map(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        return {r[0]: r[1] for r in cur.fetchall()}

def resolve_country(name: str, iso3_map: dict) -> str | None:
    iso3 = MARPOR_COUNTRY_MAP.get(name.lower().strip())
    if iso3:
        return iso3_map.get(iso3)
    try:
        result = pycountry.countries.search_fuzzy(name.strip())
        if result:
            return iso3_map.get(result[0].alpha_3)
    except Exception:
        pass
    return None

# ─── 1. Political Parties ─────────────────────────────────────────────────────

def load_parties(conn, iso3_map: dict):
    log.info("Loading political_parties...")
    df = pd.read_csv(PARTIES_FILE)
    log.info(f"  Rows: {len(df):,}")

    rows = []
    skipped = set()

    for _, row in df.iterrows():
        iso_num = resolve_country(str(row.get("countryname", "")), iso3_map)
        if not iso_num:
            skipped.add(row.get("countryname"))
            continue

        rows.append((
            int(row["party"]),
            iso_num,
            str(row.get("countryname", ""))[:100],
            str(row.get("name", ""))[:300] if pd.notna(row.get("name")) else None,
            str(row.get("name_english", ""))[:300] if pd.notna(row.get("name_english")) else None,
            str(row.get("abbrev", ""))[:50] if pd.notna(row.get("abbrev")) else None,
            None,  # parfam — not in short version
            int(row["year_min"]) if pd.notna(row.get("year_min")) else None,
            int(row["year_max"]) if pd.notna(row.get("year_max")) else None,
            bool(row.get("is_alliance", 0)),
            float(row["max_pervote"]) if pd.notna(row.get("max_pervote")) else None,
            float(row["max_presvote"]) if pd.notna(row.get("max_presvote")) else None,
            int(row["year_max_pervote"]) if pd.notna(row.get("year_max_pervote")) else None,
            int(row["year_max_presvote"]) if pd.notna(row.get("year_max_presvote")) else None,
        ))

    if skipped:
        log.info(f"  Skipped countries: {sorted(skipped)}")

    with conn.cursor() as cur:
        execute_values(cur, """
            INSERT INTO political_parties
                (party_id, iso_numeric, country_name, name, name_english, abbrev,
                 parfam, year_min, year_max, is_alliance, max_pervote, max_presvote,
                 year_max_pervote, year_max_presvote)
            VALUES %s
            ON CONFLICT (party_id) DO NOTHING
        """, rows, page_size=500)
    conn.commit()
    log.info(f"  Inserted: {len(rows):,} parties")

# ─── 2. MARPOR Elections ──────────────────────────────────────────────────────

PER_COLS = [
    'per101','per102','per103','per104','per105','per106','per107','per108','per109','per110',
    'per201','per202','per203','per204',
    'per301','per302','per303','per304','per305',
    'per401','per402','per403','per404','per405','per406','per407','per408',
    'per409','per410','per411','per412','per413','per414','per415','per416',
    'per501','per502','per503','per504','per505','per506','per507',
    'per601','per602','per603','per604','per605','per606','per607','per608',
    'per701','per702','per703','per704','per705','per706',
]

def parse_date(edate):
    """Parse MARPOR date format DD/MM/YYYY or YYYYMM."""
    if pd.isna(edate):
        return None
    s = str(edate).strip()
    try:
        if '/' in s:
            return pd.to_datetime(s, format='%d/%m/%Y').date()
        elif len(s) == 6:
            return pd.to_datetime(s, format='%Y%m').date()
    except Exception:
        pass
    return None

def load_elections(conn, iso3_map: dict):
    log.info("Loading marpor_elections...")
    df = pd.read_csv(ELECTIONS_FILE, low_memory=False)
    log.info(f"  Rows: {len(df):,}")

    # Update parfam in political_parties from elections dataset
    log.info("  Updating parfam in political_parties...")
    parfam_map = df.groupby("party")["parfam"].first().to_dict()
    for party_id, parfam in parfam_map.items():
        if pd.notna(parfam):
            with conn.cursor() as cur:
                cur.execute("UPDATE political_parties SET parfam = %s WHERE party_id = %s",
                           (int(parfam), int(party_id)))
    conn.commit()

    rows = []
    skipped_parties = set()

    for _, row in df.iterrows():
        iso_num = resolve_country(str(row.get("countryname", "")), iso3_map)
        if not iso_num:
            continue

        party_id = int(row["party"]) if pd.notna(row.get("party")) else None
        if not party_id:
            continue

        # Check party exists
        election_date = parse_date(row.get("edate"))
        election_year = int(str(row.get("date", ""))[:4]) if pd.notna(row.get("date")) else None

        def f(col):
            v = row.get(col)
            return float(v) if pd.notna(v) else None

        def i(col):
            v = row.get(col)
            return int(v) if pd.notna(v) else None

        per_vals = [f(c) for c in PER_COLS]

        rows.append((
            party_id, iso_num, election_date, election_year,
            f("pervote"), i("voteest"), f("presvote"),
            i("absseat"), i("totseats"),
            f("rile"), f("planeco"), f("markeco"), f("welfare"), f("intpeace"),
            *per_vals
        ))

    log.info(f"  Prepared: {len(rows):,} election rows")

    cols = """
        party_id, iso_numeric, election_date, election_year,
        pervote, voteest, presvote, absseat, totseats,
        rile, planeco, markeco, welfare, intpeace,
        per101,per102,per103,per104,per105,per106,per107,per108,per109,per110,
        per201,per202,per203,per204,
        per301,per302,per303,per304,per305,
        per401,per402,per403,per404,per405,per406,per407,per408,
        per409,per410,per411,per412,per413,per414,per415,per416,
        per501,per502,per503,per504,per505,per506,per507,
        per601,per602,per603,per604,per605,per606,per607,per608,
        per701,per702,per703,per704,per705,per706
    """

    with conn.cursor() as cur:
        execute_values(cur, f"""
            INSERT INTO marpor_elections ({cols})
            VALUES %s
            ON CONFLICT (party_id, election_date) DO NOTHING
        """, rows, page_size=500)
    conn.commit()
    log.info(f"  Inserted: {len(rows):,} election rows")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== MARPOR Loader ===")
    conn = get_conn()
    iso3_map = build_iso3_map(conn)
    log.info(f"ISO3 map: {len(iso3_map)} entries")

    load_parties(conn, iso3_map)
    load_elections(conn, iso3_map)

    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
