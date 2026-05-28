"""
load_epr.py — Ethnic Power Relations (EPR) 2023
================================================
Source:  ETH Zurich ICR — https://icr.ethz.ch/data/epr/core/
Domain:  History & Collective Memory
Tables:
  - history.ethnic_groups        (relational, group-level)
  - indicators                   (aggregated country-level indicators)

Defunct states (Yugoslavia, USSR, Czechoslovakia, etc.) are replicated
for their successor states in history.ethnic_groups only.
Aggregated indicators use only direct EPR entries (successors have own data).

Run:
  python3 scripts/pipeline/history/load_epr.py
"""

import requests
import psycopg2
import psycopg2.extras
import os
import csv
import io
import pycountry
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

EPR_URL = "https://icr.ethz.ch/data/epr/core/EPR-2023.csv"

# ─── GW → ISO3 Mapping ───────────────────────────────────────────────────────

GW_MANUAL = {
    "260": "DEU",   # German Federal Republic → Germany
    "265": None,    # GDR (defunct, absorbed by DEU)
    "315": None,    # Czechoslovakia (defunct → SUCCESSORS)
    "325": "ITA",   # Italy/Sardinia → Italy
    "343": "MKD",   # Macedonia (FYROM)
    "345": None,    # Yugoslavia (defunct → SUCCESSORS)
    "346": "BIH",   # Bosnia-Herzegovina
    "360": "ROU",   # Rumania
    "365": None,    # Soviet Union (defunct → SUCCESSORS)
    "370": "BLR",   # Belarus
    "402": "CPV",   # Cape Verde
    "439": "BFA",   # Burkina Faso
    "490": "COD",   # Congo DRC
    "510": "TZA",   # Tanzania
    "552": "ZWE",   # Zimbabwe
    "572": "SWZ",   # Eswatini
    "580": "MDG",   # Madagascar
    "630": "IRN",   # Iran
    "640": "TUR",   # Turkey
    "678": "YEM",   # Yemen (Arab Republic) → unified Yemen
    "680": None,    # South Yemen (defunct → SUCCESSORS)
    "711": None,    # Tibet (not a UN state)
    "731": "PRK",   # North Korea
    "775": "MMR",   # Myanmar
    "780": "LKA",   # Sri Lanka
    "811": "KHM",   # Cambodia
    "816": "VNM",   # Vietnam DRV → unified Vietnam
    "817": None,    # South Vietnam (defunct → SUCCESSORS)
    "860": "TLS",   # East Timor
}

# Defunct states → successor ISO3 codes
# Rows replicated for each successor in history.ethnic_groups only
SUCCESSORS = {
    "345": ["SRB", "HRV", "SVN", "BIH", "MKD", "MNE"],  # Yugoslavia
    "315": ["CZE", "SVK"],                                 # Czechoslovakia
    "365": ["RUS", "UKR", "BLR", "UZB", "KAZ", "AZE",
            "GEO", "LTU", "LVA", "EST", "MDA", "ARM",
            "TKM", "KGZ", "TJK"],                          # Soviet Union
    "680": ["YEM"],                                        # South Yemen
    "817": ["VNM"],                                        # South Vietnam
}

# ─── DB ──────────────────────────────────────────────────────────────────────

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# ─── Schema + Table ──────────────────────────────────────────────────────────

cur.execute("CREATE SCHEMA IF NOT EXISTS history")
cur.execute("""
    CREATE TABLE IF NOT EXISTS history.ethnic_groups (
        id SERIAL PRIMARY KEY,
        iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
        gw_id INT,
        country_name VARCHAR(100),
        group_name VARCHAR(200),
        group_id INT,
        year_from INT,
        year_to INT,
        size FLOAT,
        status VARCHAR(50),
        reg_aut BOOLEAN,
        is_successor BOOLEAN DEFAULT FALSE,
        UNIQUE(gw_id, group_id, year_from, iso_numeric)
    )
""")
conn.commit()
print("Schema + Tabelle erstellt.")

# ─── Country mapping ─────────────────────────────────────────────────────────

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1]: row[0] for row in cur.fetchall()}

def gw_to_iso3(gwid_str, statename):
    if gwid_str in GW_MANUAL:
        return GW_MANUAL[gwid_str]  # may be None
    try:
        results = pycountry.countries.search_fuzzy(statename)
        if results:
            return results[0].alpha_3
    except LookupError:
        pass
    return None

# ─── Download + Parse ────────────────────────────────────────────────────────

print("Lade EPR-2023.csv...")
r = requests.get(EPR_URL, timeout=60)
r.raise_for_status()
reader = csv.DictReader(io.StringIO(r.text))
rows = list(reader)
print(f"  {len(rows)} Zeilen geladen")

# ─── Build records ───────────────────────────────────────────────────────────

records = []
skipped = 0

for row in rows:
    gwid = row['gwid']
    statename = row['statename']
    size = float(row['size']) if row['size'].strip() else None
    reg_aut = row['reg_aut'].strip().lower() == 'true' if row['reg_aut'].strip() else False

    def make_record(iso_numeric, is_successor=False):
        return (
            iso_numeric, int(gwid), statename,
            row['group'], int(row['groupid']),
            int(row['from']), int(row['to']),
            size, row['status'], reg_aut, is_successor
        )

    iso3 = gw_to_iso3(gwid, statename)

    if iso3 is not None:
        # Direct mapping
        iso_numeric = iso3_to_numeric.get(iso3)
        if iso_numeric:
            records.append(make_record(iso_numeric, False))
        else:
            skipped += 1
    elif gwid in SUCCESSORS:
        # Replicate for all successors
        for succ_iso3 in SUCCESSORS[gwid]:
            iso_numeric = iso3_to_numeric.get(succ_iso3)
            if iso_numeric:
                records.append(make_record(iso_numeric, True))
    else:
        skipped += 1

print(f"  {len(records)} Records vorbereitet ({skipped} übersprungen)")

# ─── Insert ethnic_groups ────────────────────────────────────────────────────

psycopg2.extras.execute_values(cur, """
    INSERT INTO history.ethnic_groups
        (iso_numeric, gw_id, country_name, group_name, group_id,
         year_from, year_to, size, status, reg_aut, is_successor)
    VALUES %s
    ON CONFLICT (gw_id, group_id, year_from, iso_numeric) DO NOTHING
""", records)
inserted = cur.rowcount
conn.commit()
print(f"  {inserted} Zeilen in history.ethnic_groups eingefügt")

# ─── Source ──────────────────────────────────────────────────────────────────

cur.execute("SELECT id FROM sources WHERE short_code = 'EPR'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES ('Ethnic Power Relations Dataset', 'EPR',
                'https://icr.ethz.ch/data/epr/',
                'Politically relevant ethnic groups and their access to state power, 1946-2023.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# ─── Aggregated indicators metadata ──────────────────────────────────────────

epr_indicators = [
    ('EPR:n_groups',            'Number of politically relevant ethnic groups',        '%'),
    ('EPR:discriminated_share', 'Share of population under ethnic discrimination (%)', '%'),
    ('EPR:excluded_share',      'Share of population politically excluded (%)',         '%'),
]

for code, name, unit in epr_indicators:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            domain = EXCLUDED.domain,
            category = EXCLUDED.category,
            dimension = EXCLUDED.dimension
    """, (code, name, source_id,
          'History & Collective Memory', 'Ethnicity & Peoples', 'Ethnic Composition', unit))

conn.commit()

# ─── Aggregate per country-year (direct entries only, no successors) ─────────

print("\nBerechne aggregierte Indikatoren (nur direkte Einträge)...")

cur.execute("""
    SELECT iso_numeric, group_name, year_from, year_to, size, status
    FROM history.ethnic_groups
    WHERE iso_numeric IS NOT NULL
      AND is_successor = FALSE
""")

country_year_groups = defaultdict(list)
for iso, group, yr_from, yr_to, size, status in cur.fetchall():
    for year in range(yr_from, yr_to + 1):
        country_year_groups[(iso, year)].append((size or 0, status))

ind_saved = 0
for (iso, year), groups in country_year_groups.items():
    n_groups = len(groups)
    disc_share = sum(s for s, st in groups if st in ('DISCRIMINATED', 'POWERLESS'))
    excl_share = sum(s for s, st in groups if st in ('DISCRIMINATED', 'POWERLESS', 'IRRELEVANT'))

    for code, value in [
        ('EPR:n_groups',            float(n_groups)),
        ('EPR:discriminated_share', round(disc_share * 100, 2)),
        ('EPR:excluded_share',      round(excl_share * 100, 2)),
    ]:
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso, code, source_id, value, str(year)))
        ind_saved += 1

conn.commit()
print(f"  {ind_saved} aggregierte Indikator-Rows eingefügt")

cur.close()
conn.close()
print("\nFertig!")
