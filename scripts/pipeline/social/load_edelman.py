"""
load_edelman.py — Edelman Trust Barometer 2012-2025
=====================================================
Source:  Edelman Trust Institute
         https://www.edelman.com/trust/trust-barometer
Domain:  Social Fabric & Daily Life

Run:
  cd ~/projects/country-intelligence
  python scripts/pipeline/social/load_edelman.py
"""

import os
import glob
import logging
import pycountry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EDELMAN_DIR = "data/raw/social/Edelman"

# Nur diese Segmente laden — leere raus
SEGMENT_MAP = {
    "total":        "total",
    "ages 18-34":   "age18_34",
    "ages 35-54":   "age35_54",
    "ages 55+":     "age55plus",
    "high income":  "high_income",
    "middle income":"middle_income",
    "low income":   "low_income",
    "men":          "men",
    "women":        "women",
}

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
    "global":       None,
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
    if clean in _cache:
        return _cache[clean]
    if clean in OVERRIDES:
        iso3 = OVERRIDES[clean]
        result = iso3_map.get(iso3) if iso3 else None
        _cache[clean] = result
        return result
    iso_num = name_map.get(clean)
    if iso_num:
        _cache[clean] = iso_num
        return iso_num
    try:
        r = pycountry.countries.search_fuzzy(name.strip())
        if r:
            result = iso3_map.get(r[0].alpha_3)
            _cache[clean] = result
            return result
    except:
        pass
    _cache[clean] = None
    return None

def ensure_source(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM sources WHERE short_code = 'EDELMAN'")
        row = cur.fetchone()
        if not row:
            cur.execute("""
                INSERT INTO sources (short_code, name, url, description)
                VALUES ('EDELMAN', 'Edelman Trust Barometer',
                        'https://www.edelman.com/trust/trust-barometer',
                        'Annual survey of trust in institutions (Business, Government, Media, NGOs) by country and demographic segment. 2012-2025.')
                RETURNING id
            """)
            source_id = cur.fetchone()[0]
        else:
            source_id = row[0]
    conn.commit()
    return source_id

def ensure_metadata(conn, source_id):
    institutions = [
        ("trust_business",   "Trust in Business (%)"),
        ("trust_government", "Trust in Government (%)"),
        ("trust_media",      "Trust in Media (%)"),
        ("trust_ngo",        "Trust in NGOs (%)"),
    ]
    seg_labels = {v: k.title() for k, v in SEGMENT_MAP.items()}

    with conn.cursor() as cur:
        for inst_code, inst_name in institutions:
            for seg_code, seg_label in seg_labels.items():
                code = f"EDELMAN:{inst_code}:{seg_code}"
                name = f"{inst_name} — {seg_label}"
                cur.execute("""
                    INSERT INTO indicator_metadata
                        (indicator_code, name, unit, source_id, domain, category, dimension)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (indicator_code) DO NOTHING
                """, (code, name, '%', source_id,
                      'Social Fabric & Daily Life', 'Trust & Institutions', 'Institutional Trust'))
    conn.commit()

# ─── Parse files ─────────────────────────────────────────────────────────────

def parse_country_segment(label: str):
    label = label.strip().strip('"')
    for seg_label in sorted(SEGMENT_MAP.keys(), key=len, reverse=True):
        if label.lower().endswith(f"-{seg_label}"):
            country = label[:-(len(seg_label) + 1)].strip()
            return country, SEGMENT_MAP[seg_label]
    if '-' in label:
        parts = label.rsplit('-', 1)
        seg_clean = parts[1].strip().lower()
        if seg_clean in SEGMENT_MAP:
            return parts[0].strip(), SEGMENT_MAP[seg_clean]
    return None

def parse_file(filepath: str) -> list:
    results = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    i = 0
    current_country = None
    current_segment = None

    while i < len(lines):
        line = lines[i].strip()
        cols = line.split(',')

        if len(cols) >= 8:
            non_empty = [(j, c.strip().strip('"')) for j, c in enumerate(cols) if c.strip().strip('"')]
            if len(non_empty) == 1 and non_empty[0][1] and '-' in non_empty[0][1]:
                parsed = parse_country_segment(non_empty[0][1])
                if parsed:
                    current_country, current_segment = parsed
                    i += 1
                    continue

        if current_country and (line.startswith(',2') or (line.startswith(',') and '2012' in line)):
            year_cols = [c.strip() for c in line.split(',')]
            years = [int(c) for c in year_cols if c.isdigit() and 2000 < int(c) < 2030]

            if years:
                for j in range(1, 5):
                    if i + j >= len(lines):
                        break
                    inst_line = lines[i + j].strip()
                    if not inst_line:
                        break
                    inst_cols = [c.strip() for c in inst_line.split(',')]
                    inst_name = inst_cols[0].strip().strip('"').lower()
                    inst_code = INSTITUTION_MAP.get(inst_name)
                    if not inst_code:
                        continue

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
                            results.append((current_country, current_segment, inst_code, year, values[k]))
        i += 1

    return results

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    log.info("=== Edelman Trust Barometer Loader ===")
    conn = get_conn()
    source_id = ensure_source(conn)
    ensure_metadata(conn, source_id)
    iso3_map, name_map = build_maps(conn)

    files = sorted(glob.glob(os.path.join(EDELMAN_DIR, "*.csv")))
    log.info(f"Files found: {len(files)}")

    all_rows = []
    skipped_countries = set()

    for filepath in files:
        raw = parse_file(filepath)
        for country, segment, inst_code, year, value in raw:
            if not segment:
                continue
            iso_num = resolve(country, iso3_map, name_map)
            if not iso_num:
                skipped_countries.add(country)
                continue
            indicator_code = f"EDELMAN:{inst_code}:{segment}"
            all_rows.append((iso_num, indicator_code, source_id, str(year), value, "A"))

    log.info(f"Total rows prepared: {len(all_rows):,}")
    if skipped_countries:
        log.info(f"Skipped countries ({len(skipped_countries)}): {sorted(skipped_countries)[:15]}")

    # Deduplizieren
    seen = {}
    for row in all_rows:
        key = (row[0], row[1], row[3])  # iso, code, year
        seen[key] = row
    deduped = list(seen.values())
    log.info(f"After dedup: {len(deduped):,}")

    # Erst alles löschen und sauber neu laden
    with conn.cursor() as cur:
        cur.execute("DELETE FROM indicators WHERE indicator_code LIKE 'EDELMAN:%'")
        deleted = cur.rowcount
        log.info(f"Deleted {deleted} existing Edelman rows")
        execute_values(cur, """
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, time_period, value, obs_status)
            VALUES %s
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, deduped, page_size=1000)
    conn.commit()
    log.info(f"Inserted: {len(deduped):,} rows")
    conn.close()
    log.info("=== Done ===")

if __name__ == "__main__":
    main()