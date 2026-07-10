"""
load_atop.py — ATOP Alliance Treaty Obligations and Provisions v5.1
====================================================================
Source:  Alliance Treaty Obligations and Provisions (ATOP)
         http://www.atopdata.org
Domain:  International Relations & Global Integration
Coverage: ~160 countries, 1815-2018

Uses state-year dataset (atop5_1sy.csv).

Indicators:
  ATOP:n_alliances     — Total number of active alliances
  ATOP:has_defense     — Has at least one defense pact (1/0)
  ATOP:has_offense     — Has at least one offense pact (1/0)
  ATOP:has_neutral     — Has at least one neutrality pact (1/0)
  ATOP:has_nonagg      — Has at least one nonaggression pact (1/0)
  ATOP:has_consul      — Has at least one consultation pact (1/0)

Run:
  python3 scripts/pipeline/international/load_atop.py
"""

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

ATOP_FILE = "data/raw/Manuell_27-05/ATOP 5.1 (.csv)/atop5_1sy.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'ATOP'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('ATOP', 'Alliance Treaty Obligations and Provisions (ATOP)',
                'http://www.atopdata.org',
                'Formal military alliances and their obligations, 1815-2018. Rice University.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# Metadata
for code, name, unit in [
    ('ATOP:n_alliances', 'Number of active military alliances',         'count'),
    ('ATOP:has_defense', 'Has active defense pact (1=yes)',             'binary'),
    ('ATOP:has_offense', 'Has active offense pact (1=yes)',             'binary'),
    ('ATOP:has_neutral', 'Has active neutrality pact (1=yes)',          'binary'),
    ('ATOP:has_nonagg',  'Has active nonaggression pact (1=yes)',       'binary'),
    ('ATOP:has_consul',  'Has active consultation pact (1=yes)',        'binary'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            domain = EXCLUDED.domain,
            category = EXCLUDED.category,
            dimension = EXCLUDED.dimension
    """, (code, name, source_id,
          'International Relations & Global Integration',
          'Security Alliances',
          'Military Alliances',
          unit))

conn.commit()
print("Metadata geladen.")

# COW → ISO numeric mapping (zentral aus countries.cow_code)
cur.execute("SELECT cow_code, iso_numeric FROM countries WHERE cow_code IS NOT NULL")
cow_to_iso_map = {row[0]: row[1] for row in cur.fetchall()}

def cow_to_iso(ccode):
    if pd.isna(ccode):
        return None
    return cow_to_iso_map.get(int(ccode))

# Load
print(f"Lade {ATOP_FILE}...")
df = pd.read_csv(ATOP_FILE, low_memory=False)
print(f"  {len(df):,} Zeilen | Jahre: {df['year'].min()}-{df['year'].max()}")

total_saved = 0
total_skipped = 0

for _, row in df.iterrows():
    iso_numeric = cow_to_iso(row['state'])
    if not iso_numeric:
        continue

    year = str(int(row['year']))

    values = [
        ('ATOP:n_alliances', float(row['number'])),
        ('ATOP:has_defense', float(row['defense'])),
        ('ATOP:has_offense', float(row['offense'])),
        ('ATOP:has_neutral', float(row['neutral'])),
        ('ATOP:has_nonagg',  float(row['nonagg'])),
        ('ATOP:has_consul',  float(row['consul'])),
    ]

    for code, value in values:
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, code, source_id, value, year))
        if cur.rowcount > 0:
            total_saved += 1
        else:
            total_skipped += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")
