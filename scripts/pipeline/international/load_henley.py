"""
load_henley.py — Passport Index (Henley)
=========================================
Source:  ilyankou/passport-index-dataset (GitHub)
         Based on Henley & Partners data
Domain:  International Relations & Global Integration

Indicators:
  HENLEY:visa_free_total  — Destinations accessible without prior visa
  HENLEY:visa_required    — Destinations requiring visa
  HENLEY:evisa            — Destinations with e-visa available
  HENLEY:visa_on_arrival  — Destinations with visa on arrival

Run: python3 scripts/pipeline/international/load_henley.py
"""

import psycopg2
import os
import requests
import io
import pandas as pd
import pycountry
from dotenv import load_dotenv

load_dotenv()

URL = "https://raw.githubusercontent.com/ilyankou/passport-index-dataset/master/passport-index-tidy.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'HENLEY'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('HENLEY', 'Passport Index (Henley & Partners)',
                'https://www.henleyglobal.com/passport-index',
                'Passport strength by number of visa-free destinations. ~199 countries.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

for code, name in [
    ('HENLEY:visa_free_total', 'Passport: Total accessible destinations (no prior visa)'),
    ('HENLEY:visa_required',   'Passport: Destinations requiring advance visa'),
    ('HENLEY:evisa',           'Passport: Destinations with e-visa'),
    ('HENLEY:visa_on_arrival', 'Passport: Destinations with visa on arrival'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id,
          'International Relations & Global Integration',
          'Globalisation', 'Passport Freedom', 'count'))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, name FROM countries")
name_to_numeric = {row[1].lower(): row[0] for row in cur.fetchall()}

_cache = {}
def resolve(name):
    key = name.lower().strip()
    if key in _cache:
        return _cache[key]
    result = name_to_numeric.get(key)
    if not result:
        try:
            r = pycountry.countries.search_fuzzy(name)
            if r:
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (r[0].alpha_3,))
                row = cur.fetchone()
                result = row[0] if row else None
        except:
            result = None
    _cache[key] = result
    return result

print("Lade Passport Index...")
r = requests.get(URL, timeout=30)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text))
print(f"  {len(df):,} Zeilen, {df['Passport'].nunique()} Länder")

# Classify requirements
def classify(req):
    req = str(req).lower().strip()
    if req == 'visa required':
        return 'visa_required'
    elif req == 'e-visa':
        return 'evisa'
    elif req == 'visa on arrival':
        return 'visa_on_arrival'
    elif req == '-1':
        return None  # same country
    else:
        return 'visa_free'  # numeric days or 'visa free', 'eta'

df['category'] = df['Requirement'].apply(classify)
df = df[df['category'].notna()]

total_saved = 0

for passport, grp in df.groupby('Passport'):
    iso_numeric = resolve(passport)
    if not iso_numeric:
        continue

    counts = grp['category'].value_counts()
    visa_free_total = int(counts.get('visa_free', 0) + counts.get('evisa', 0) + counts.get('visa_on_arrival', 0))

    for code, value in [
        ('HENLEY:visa_free_total', float(visa_free_total)),
        ('HENLEY:visa_required',   float(counts.get('visa_required', 0))),
        ('HENLEY:evisa',           float(counts.get('evisa', 0))),
        ('HENLEY:visa_on_arrival', float(counts.get('visa_on_arrival', 0))),
    ]:
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, code, source_id, value, 'static'))
        if cur.rowcount > 0:
            total_saved += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved:,} rows gespeichert.")