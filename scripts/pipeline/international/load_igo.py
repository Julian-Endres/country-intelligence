"""
load_igo.py — COW IGO Membership Data v3.0
===========================================
Chunk-basiert um RAM zu schonen.
Run: python3 scripts/pipeline/international/load_igo.py
"""

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

IGO_FILE = "data/raw/Manuell_27-05/IGO Membership/dyadic_formatv3.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'IGO'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('IGO', 'COW IGO Membership Data v3.0',
                'https://correlatesofwar.org/data-sets/igo/',
                'State memberships in international governmental organizations, 1816-2014.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

for code, name, unit in [
    ('IGO:n_memberships', 'Number of IGO memberships (total)',        'count'),
    ('IGO:n_full',        'Number of full IGO memberships',           'count'),
    ('IGO:n_observer',    'Number of observer/associate memberships', 'count'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id,
          'International Relations & Global Integration',
          'Multilateral Integration', 'IGO Membership', unit))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT cow_code, iso_numeric FROM countries WHERE cow_code IS NOT NULL")
cow_to_iso_map = {row[0]: row[1] for row in cur.fetchall()}

def cow_to_iso(ccode):
    if pd.isna(ccode):
        return None
    return cow_to_iso_map.get(int(ccode))

# Read header to get IGO columns
print("Lese Header...")
header_df = pd.read_csv(IGO_FILE, nrows=0)
meta_cols = {'ccode1', 'country1', 'ccode2', 'country2', 'year', 'state'}
igo_cols = [c for c in header_df.columns if c not in meta_cols]
print(f"  {len(igo_cols)} IGO Spalten")

# Process in chunks — aggregate per (ccode1, year)
# Use dict to track max membership per state-year
print("Verarbeite in Chunks...")
state_year_full     = defaultdict(set)  # (ccode1, year) → set of IGOs with full membership
state_year_observer = defaultdict(set)  # (ccode1, year) → set of IGOs with observer

CHUNK_SIZE = 50000
chunk_num = 0

for chunk in pd.read_csv(IGO_FILE, chunksize=CHUNK_SIZE, low_memory=False):
    chunk_num += 1
    if chunk_num % 5 == 0:
        print(f"  Chunk {chunk_num} ({chunk_num * CHUNK_SIZE:,} Zeilen)...")

    for _, row in chunk.iterrows():
        ccode1 = row.get('ccode1')
        year   = row.get('year')
        if pd.isna(ccode1) or pd.isna(year):
            continue

        key = (int(ccode1), int(year))

        for igo in igo_cols:
            val = row.get(igo, 0)
            if val == 1:
                state_year_full[key].add(igo)
            elif val in (2, 3):
                state_year_observer[key].add(igo)

print(f"  {len(state_year_full):,} State-Year Kombinationen mit Mitgliedschaften")

# Insert aggregated indicators
total_saved = 0
all_keys = set(state_year_full.keys()) | set(state_year_observer.keys())

for i, (ccode1, year) in enumerate(sorted(all_keys)):
    if i % 5000 == 0 and i > 0:
        conn.commit()
        print(f"  {i:,}/{len(all_keys):,} | {total_saved:,} gespeichert")

    iso_numeric = cow_to_iso(ccode1)
    if not iso_numeric:
        continue

    n_full     = len(state_year_full.get((ccode1, year), set()))
    n_observer = len(state_year_observer.get((ccode1, year), set()))
    n_total    = n_full + n_observer

    for code, value in [
        ('IGO:n_memberships', float(n_total)),
        ('IGO:n_full',        float(n_full)),
        ('IGO:n_observer',    float(n_observer)),
    ]:
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, code, source_id, value, str(year)))
        if cur.rowcount > 0:
            total_saved += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved:,} rows gespeichert.")