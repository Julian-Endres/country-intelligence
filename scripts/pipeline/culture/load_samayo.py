"""
load_samayo.py — samayo/country-json bulk loader
=================================================
Source:  https://github.com/samayo/country-json
Loads multiple country fact files into indicators + text tables.

Indicators (numeric):
  SAMAYO:independence_year  — Year of independence
  SAMAYO:avg_male_height    — Average male height (cm)
  SAMAYO:coastline_km       — Coastline length (km)
  SAMAYO:landlocked         — Landlocked (1=yes, 0=no)

Text tables:
  culture.country_facts     — government_type, driving_side, national_symbol,
                               currency_name, calling_code

Run: python3 scripts/pipeline/culture/load_samayo.py
"""

import psycopg2
import os
import requests
import json
import pycountry
from dotenv import load_dotenv

load_dotenv()

BASE = "https://raw.githubusercontent.com/samayo/country-json/master/src/"

FILES = {
    'independence':   'country-by-independence-date.json',
    'height':         'country-by-avg-male-height.json',
    'coastline':      'country-by-coastline.json',
    'landlocked':     'country-by-landlocked.json',
    'government':     'country-by-government-type.json',
    'driving':        'country-by-driving-side.json',
    'symbol':         'country-by-national-symbol.json',
    'currency':       'country-by-currency-name.json',
    'calling_code':   'country-by-calling-code.json',
}

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Schema + Table
cur.execute("CREATE SCHEMA IF NOT EXISTS culture")
cur.execute("""
    CREATE TABLE IF NOT EXISTS culture.country_facts (
        iso_numeric  CHAR(3) PRIMARY KEY REFERENCES countries(iso_numeric),
        country_name VARCHAR(100),
        government_type  TEXT,
        driving_side     VARCHAR(10),
        national_symbol  TEXT,
        currency_name    TEXT,
        calling_code     TEXT,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'SAMAYO'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('SAMAYO', 'samayo/country-json',
                'https://github.com/samayo/country-json',
                'Curated country data: national symbols, government types, independence dates, etc.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# Numeric indicator metadata
NUMERIC_INDICATORS = [
    ('SAMAYO:independence_year', 'Year of independence',          'History & Collective Memory', 'State & Sovereignty', 'State Age',     'year'),
    ('SAMAYO:avg_male_height',   'Average male height (cm)',      'Health, Body & Behavior',     'Survival & Mortality','Body Metrics',  'cm'),
    ('SAMAYO:coastline_km',      'Coastline length (km)',         'Geography & Environment',     'Land & Ecosystems',   'Land Use',      'km'),
    ('SAMAYO:landlocked',        'Landlocked country (1=yes)',    'Geography & Environment',     'Land & Ecosystems',   'Land Use',      'binary'),
]

for code, name, domain, category, dimension, unit in NUMERIC_INDICATORS:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id, domain, category, dimension, unit))

conn.commit()
print("Metadata geladen.")

# Country mapping
cur.execute("SELECT iso_numeric, name FROM countries")
name_to_numeric = {row[1].lower(): row[0] for row in cur.fetchall()}
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

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
                result = iso3_to_numeric.get(r[0].alpha_3)
        except:
            result = None
    _cache[key] = result
    return result

# Download all files
print("Lade Dateien...")
data = {}
for key, filename in FILES.items():
    r = requests.get(BASE + filename, timeout=15)
    if r.status_code == 200:
        data[key] = json.loads(r.text)
        print(f"  ✅ {filename}: {len(data[key])} Einträge")
    else:
        print(f"  ❌ {filename}: {r.status_code}")

# Build per-country dict
countries_data = {}
for key, entries in data.items():
    for entry in entries:
        country = entry.get('country', '')
        if not country:
            continue
        iso_numeric = resolve(country)
        if not iso_numeric:
            continue
        if iso_numeric not in countries_data:
            countries_data[iso_numeric] = {'name': country}
        # Store each field
        for field, val in entry.items():
            if field != 'country':
                countries_data[iso_numeric][f'{key}_{field}'] = val

print(f"\n{len(countries_data)} Länder aufgelöst")

# Insert indicators + facts
ind_saved = 0
facts_saved = 0

for iso_numeric, fields in countries_data.items():
    # Numeric indicators
    for code, field_key, cast in [
        ('SAMAYO:independence_year', 'independence_independence', int),
        ('SAMAYO:avg_male_height',   'height_height',             float),
        ('SAMAYO:coastline_km',      'coastline_coastline',       float),
        ('SAMAYO:landlocked',        'landlocked_landlocked',     lambda x: float(int(str(x)))),
    ]:
        val = fields.get(field_key)
        if val is None:
            continue
        try:
            value = cast(val)
            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, code, source_id, value, 'static'))
            if cur.rowcount > 0:
                ind_saved += 1
        except (ValueError, TypeError):
            continue

    # Text facts
    govt     = fields.get('government_government')
    driving  = fields.get('driving_side')
    symbol   = fields.get('symbol_symbol')
    currency = fields.get('currency_currency')
    calling  = str(fields.get('calling_code_call_code', '') or '')

    cur.execute("""
        INSERT INTO culture.country_facts
            (iso_numeric, country_name, government_type, driving_side,
             national_symbol, currency_name, calling_code)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (iso_numeric) DO UPDATE SET
            government_type = EXCLUDED.government_type,
            driving_side    = EXCLUDED.driving_side,
            national_symbol = EXCLUDED.national_symbol,
            currency_name   = EXCLUDED.currency_name,
            calling_code    = EXCLUDED.calling_code,
            updated_at      = CURRENT_TIMESTAMP
    """, (iso_numeric, fields['name'], govt, driving, symbol, currency, calling or None))
    facts_saved += 1

conn.commit()
cur.close()
conn.close()

print(f"\nFertig!")
print(f"  indicators: {ind_saved} rows")
print(f"  culture.country_facts: {facts_saved} Länder")
