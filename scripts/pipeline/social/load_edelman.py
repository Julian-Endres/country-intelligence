"""
load_edelman.py — Edelman Trust Barometer 2012-2025
=====================================================
Source:  Edelman Trust Institute
         https://www.edelman.com/trust/trust-barometer
Domain:  Social Fabric & Daily Life
Destination: indicators table (source_code = 'EDELMAN')

Indicators loaded (% trust, top-4-box on 9-point scale)
---------------------------------------------------------
EDELMAN:trust_business:<segment>
EDELMAN:trust_government:<segment>
EDELMAN:trust_media:<segment>
EDELMAN:trust_ngo:<segment>

Segments:
  total, age18_34, age35_54, age55plus,
  high_income, middle_income, low_income,
  men, women

Format per file:
  Row 1: Citation header
  Then blocks: "Country-Segment" label row, year header row, 4 institution rows
  Multiple countries per file

Run
---
  cd ~/projects/country-intelligence
  source venv/bin/activate
  python scripts/pipeline/social/load_edelman.py
"""

import os
import re
import glob
import logging
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EDELMAN_DIR = "data/raw/Manuell_27-05/Edelman"

# Segment label → clean code
SEGMENT_MAP = {
    "total":           "total",
    "ages 18-34":      "age18_34",
    "ages 35-54":      "age35_54",
    "ages 55+":        "age55plus",
    "high income":     "high_income",
    "middle income":   "middle_income",
    "low income":      "low_income",
    "men":             "men",
    "women":           "women",
    # fallbacks
    "informed public": "informed_public",
    "mass population": "mass_population",
    "college educated":"college_educated",
    "non-college":     "non_college",
}

# Institution label → indicator suffix
INSTITUTION_MAP = {
    "business":   "trust_business",
    "government": "trust_government",
    "media":      "trust_media",
    "ngos":       "trust_ngo",
    "ngo":        "trust_ngo",
}

OVERRIDES = {
    "u.s.":         "USA", "usa":          "USA", "united states": "USA",
    "u.k.":         "GBR", "uk":           "GBR", "united kingdom": "GBR",
    "south korea":  "KOR", "uae":          "ARE",
    "russia":       "RUS", "saudi arabia": "SAU",
    "hong kong":    "HKG", "taiwan":       "TWN",
    "s. africa":    "ZAF", "s. korea":     "KOR",
    "global":       None,  # skip global aggregates
}

# ─── DB ──────────────────────────────────────────────────────────────────────

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
    clean = name.strip().lower()
    if clean in _cache: return _cache[clean]
    # Check override
    if clean in OVERRIDES:
        iso3 = OVERRIDES[clean]
        result = iso3_map.get(iso3) if iso3 else None
        _cache[clean] = result
        return result
    # Direct name
    iso_num = name_map.get(clean)
    if iso_num:
        _cache[clean] = iso_num
        return iso_num
    # Fuzzy
    try:
        r = pycountry.countries.search_fuzzy(name.strip())
        if r:
            result = iso3_map.get(r[0].alpha_3)
            _cache[clean] = result
            return result
    except: pass
    _cache[clean] = None
    return None

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES ('EDELMAN', 'Edelman Trust Barometer',
                    'https://www.edelman.com/trust/trust-barometer',
                    'Annual survey of trust in institutions (Business, Government, Media, NGOs) by country and demographic segment. 2012-2025.')
            ON CONFLICT (short_code) DO NOTHING
        """)
    conn.commit()

def ensure_metadata(conn):
    institutions = [
        ("trust_business",   "Trust in Business (%)",    "Trust in business institutions, % top-4-box on 9-point scale."),
        ("trust_government", "Trust in Government (%)",  "Trust in government institutions, % top-4-box on 9-point scale."),
        ("trust_media",      "Trust in Media (%)",       "Trust in media institutions, % top-4-box on 9-point scale."),
        ("trust_ngo",        "Trust in NGOs (%)",        "Trust in NGO institutions, % top-4-box on 9-point scale."),
    ]
    segments = list(SEGMENT_MAP.values())

    for inst_code, inst_name, inst_desc in institutions:
        for seg in segments:
            code = f"EDELMAN:{inst_code}:{seg}"
            seg_label = {v: k.title() for k, v in SEGMENT_MAP.items()}.get(seg, seg)
            name = f"{inst_name} — {seg_label}"
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO indicator_metadata
                        (indicator_code, name, unit, category, description, source_id)
                    VALUES (%s, %s, %s, %s, %s,
                        (SELECT id FROM sources WHERE short_code = 'EDELMAN'))
                    ON CONFLICT (indicator_code) DO NOTHING
                """, (code, name, '%', 'social', inst_desc))
    conn.commit()

# ─── Parse files ─────────────────────────────────────────────────────────────

def parse_country_segment(label: str) -> tuple[str, str] | None:
    """Parse 'Argentina-Total' → ('Argentina', 'total')"""
    label = label.strip().strip('"')

    # Known segments to split on
    for seg_label in sorted(SEGMENT_MAP.keys(), key=len, reverse=True):
        if label.lower().endswith(f"-{seg_label}"):
            country = label[:-(len(seg_label) + 1)].strip()
            return country, SEGMENT_MAP[seg_label]

    # Try splitting on last '-'
    if '-' in label:
        parts = label.rsplit('-', 1)
        seg_clean = parts[1].strip().lower()
        if seg_clean in SEGMENT_MAP:
            return parts[0].strip(), SEGMENT_MAP[seg_clean]

    return None

def parse_file(filepath: str) -> list[tuple]:
    """Parse one Edelman CSV file. Returns list of (country, segment, institution, year, value)"""
    results = []

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    i = 0
    current_country = None
    current_segment = None

    while i < len(lines):
        line = lines[i].strip()

        # Detect country-segment header: line with content only around col 7
        # Format: ,,,,,,"Country-Segment",,,,,,,
        cols = line.split(',')
        if len(cols) >= 8:
            # Find the non-empty value
            non_empty = [(j, c.strip().strip('"')) for j, c in enumerate(cols) if c.strip().strip('"')]
            if len(non_empty) == 1 and non_empty[0][1] and '-' in non_empty[0][1]:
                parsed = parse_country_segment(non_empty[0][1])
                if parsed:
                    current_country, current_segment = parsed
                    i += 1
                    continue

        # Detect year header row
        if current_country and line.startswith(',2') or (line.startswith(',') and '2012' in line):
            year_cols = [c.strip() for c in line.split(',')]
            years = []
            for c in year_cols:
                if c.isdigit() and 2000 < int(c) < 2030:
                    years.append(int(c))

            if years:
                # Read next 4 institution rows
                for j in range(1, 5):
                    if i + j >= len(lines):
                        break
                    inst_line = lines[i + j].strip()
                    if not inst_line:
                        break
                    inst_cols = [c.strip() for c in inst_line.split(',')]
                    if not inst_cols:
                        break

                    inst_name = inst_cols[0].strip().strip('"').lower()
                    inst_code = INSTITUTION_MAP.get(inst_name)
                    if not inst_code:
                        continue

                    # Extract values aligned with years
                    values = []
                    for c in inst_cols[1:]:
                        c = c.strip()
                        if c == '':
                            values.append(None)
                        else:
                            try:
                                values.append(float(c))
                            except ValueError:
                                values.append(None)

                    for k, year in enumerate(years):
                        if k < len(values) and values[k] is not None:
                            results.append((
                                current_country,
                                current_segment,
                                inst_code,
                                year,
                                values[k],
                            ))

        i += 1

    return results

# ─── Insert ───────────────────────────────────────────────────────────────────

INSERT_SQL = """
    INSERT INTO indicators (iso_numeric, indicator_code, time_period, value, obs_status)
    VALUES %s
    ON CONFLICT DO NOTHING
"""

def main():
    log.info("=== Edelman Trust Barometer Loader ===")
    conn = get_conn()
    ensure_source(conn)
    ensure_metadata(conn)

    iso3_map, name_map = build_maps(conn)

    files = sorted(glob.glob(os.path.join(EDELMAN_DIR, "*.csv")))
    log.info(f"Files found: {len(files)}")

    all_rows = []
    skipped_countries = set()
    skipped_segments = set()

    for filepath in files:
        raw = parse_file(filepath)
        for country, segment, inst_code, year, value in raw:
            iso_num = resolve(country, iso3_map, name_map)
            if not iso_num:
                skipped_countries.add(country)
                continue
            if not segment:
                skipped_segments.add(f"{country}-?")
                continue

            indicator_code = f"EDELMAN:{inst_code}:{segment}"
            all_rows.append((iso_num, indicator_code, str(year), value, "A"))

    log.info(f"Total rows prepared: {len(all_rows):,}")
    if skipped_countries:
        log.info(f"Skipped countries ({len(skipped_countries)}): {sorted(skipped_countries)[:15]}")

    # Deduplicate
    seen = {}
    for row in all_rows:
        key = (row[0], row[1], row[2])
        seen[key] = row
    deduped = list(seen.values())
    log.info(f"After dedup: {len(deduped):,}")

    with conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, deduped, page_size=1000)
    conn.commit()
    log.info(f"Inserted: {len(deduped):,} rows")

    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()
