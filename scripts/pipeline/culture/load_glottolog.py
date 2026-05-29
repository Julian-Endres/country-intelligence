"""
load_glottolog.py — Glottolog Language Diversity
=================================================
Source:  Glottolog 5.3 — https://glottolog.org
Domain:  Culture & Identity → Identity & Values → Language Diversity

Run: python3 scripts/pipeline/culture/load_glottolog.py
"""

import psycopg2
import os
import requests
import io
import csv
import pycountry
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

GLOTTOLOG_URL = "https://raw.githubusercontent.com/glottolog/glottolog-cldf/v5.3/cldf/languages.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'GLOTTOLOG'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('GLOTTOLOG', 'Glottolog 5.3',
                'https://glottolog.org',
                'Comprehensive language catalog with geographic and genealogical information.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

for code, name, unit in [
    ('GLOTTOLOG:n_languages', 'Number of languages spoken',      'count'),
    ('GLOTTOLOG:n_families',  'Number of language families',     'count'),
    ('GLOTTOLOG:ldi',         'Linguistic Diversity Index (0-1)', 'index 0-1'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id,
          'Culture & Identity', 'Identity & Values', 'Language Diversity', unit))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

print("Lade Glottolog CLDF...")
r = requests.get(GLOTTOLOG_URL, timeout=60)
r.raise_for_status()
reader = csv.DictReader(io.StringIO(r.text))
rows = list(reader)
print(f"  {len(rows):,} Einträge")

# Aggregate per country
country_languages = defaultdict(set)
country_families  = defaultdict(set)

for row in rows:
    level = row.get('Level', '')
    if level != 'language':
        continue

    glottocode = row.get('Glottocode') or row.get('ID', '')
    family_id  = row.get('Family_ID', '') or 'isolate'
    countries  = row.get('Countries', '') or ''

    # Countries field: space or semicolon separated ISO3 codes
    for iso3 in countries.replace(';', ' ').split():
        iso3 = iso3.strip().upper()
        if len(iso3) == 2:
            # Convert ISO2 to ISO3
            try:
                c = pycountry.countries.get(alpha_2=iso3)
                if c:
                    iso3 = c.alpha_3
            except:
                continue
        if len(iso3) == 3:
            country_languages[iso3].add(glottocode)
            country_families[iso3].add(family_id)

print(f"  {len(country_languages)} Länder mit Sprachdaten")

total_saved = 0
for iso3, languages in country_languages.items():
    iso_numeric = iso3_to_numeric.get(iso3)
    if not iso_numeric:
        continue

    n_languages = len(languages)
    n_families  = len(country_families.get(iso3, set()))
    ldi = float(round(1.0 - 1.0 / n_languages, 4)) if n_languages > 1 else 0.0

    for code, value in [
        ('GLOTTOLOG:n_languages', float(n_languages)),
        ('GLOTTOLOG:n_families',  float(n_families)),
        ('GLOTTOLOG:ldi',         ldi),
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