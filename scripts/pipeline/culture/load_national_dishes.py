"""
load_national_dishes.py — National Dishes per Country
======================================================
Source:  samayo/country-json (GitHub)
         https://github.com/samayo/country-json
Domain:  Culture & Identity → Cultural Production → Food Culture

Stores as text in a new table culture.national_dishes
Also creates a simple indicator: CULTURE:has_national_dish (1/0)

Run: python3 scripts/pipeline/culture/load_national_dishes.py
"""

import psycopg2
import os
import requests
import json
import pycountry
from dotenv import load_dotenv

load_dotenv()

URL = "https://raw.githubusercontent.com/samayo/country-json/master/src/country-by-national-dish.json"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Create table
cur.execute("""
    CREATE SCHEMA IF NOT EXISTS culture
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS culture.national_dishes (
        id SERIAL PRIMARY KEY,
        iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
        country_name VARCHAR(100),
        dish TEXT,
        UNIQUE(iso_numeric)
    )
""")
conn.commit()
print("Tabelle erstellt.")

# Source + Metadata
cur.execute("SELECT id FROM sources WHERE short_code = 'SAMAYO'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('SAMAYO', 'samayo/country-json',
                'https://github.com/samayo/country-json',
                'Curated country data including national dishes, flags, capitals etc.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

cur.execute("""
    INSERT INTO indicator_metadata
        (indicator_code, name, source_id, domain, category, dimension, unit)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (indicator_code) DO NOTHING
""", ('CULTURE:has_national_dish', 'Has recognized national dish (1=yes)',
      source_id, 'Culture & Identity', 'Cultural Production', 'Food Culture', 'binary'))
conn.commit()

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

# Load data
print("Lade National Dishes...")
r = requests.get(URL, timeout=30)
r.raise_for_status()
data = json.loads(r.text)
print(f"  {len(data)} Länder")

inserted_dishes = 0
inserted_indicators = 0
skipped = []

for entry in data:
    country = entry.get('country', '')
    dish = entry.get('dish')

    iso_numeric = resolve(country)
    if not iso_numeric:
        skipped.append(country)
        continue

    # Insert into culture.national_dishes
    cur.execute("""
        INSERT INTO culture.national_dishes (iso_numeric, country_name, dish)
        VALUES (%s, %s, %s)
        ON CONFLICT (iso_numeric) DO UPDATE SET dish = EXCLUDED.dish
    """, (iso_numeric, country, dish))
    inserted_dishes += 1

    # Insert indicator
    has_dish = 1.0 if dish else 0.0
    cur.execute("""
        INSERT INTO indicators
            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
        VALUES (%s, %s, %s, %s, %s, 'A')
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
    """, (iso_numeric, 'CULTURE:has_national_dish', source_id, has_dish, 'static'))
    if cur.rowcount > 0:
        inserted_indicators += 1

conn.commit()

if skipped:
    print(f"  Nicht gemappt: {skipped[:10]}")

cur.close()
conn.close()
print(f"\nFertig!")
print(f"  culture.national_dishes: {inserted_dishes} Länder")
print(f"  indicators: {inserted_indicators} rows")

# Quick preview
conn2 = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur2 = conn2.cursor()
cur2.execute("SELECT country_name, dish FROM culture.national_dishes WHERE dish IS NOT NULL ORDER BY country_name LIMIT 10")
print("\nBeispiele:")
for row in cur2.fetchall():
    print(f"  {row[0]}: {row[1]}")
cur2.close()
conn2.close()
