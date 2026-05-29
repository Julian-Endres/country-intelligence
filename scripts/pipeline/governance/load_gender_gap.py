"""
load_gender_gap.py — WEF Global Gender Gap Index via QoG
=========================================================
Source:  World Economic Forum / Quality of Government Dataset
Domain:  Politics & Governance → Democracy & Elections → Gender & Political Equality

Indicators:
  WEF:gggi_ggi — Overall Gender Gap Index (0-1)
  WEF:gggi_eas — Educational Attainment subindex
  WEF:gggi_hss — Health & Survival subindex
  WEF:gggi_pes — Economic Participation subindex
  WEF:gggi_pos — Political Empowerment subindex

Run: python3 scripts/pipeline/governance/load_gender_gap.py
"""

import psycopg2
import os
import requests
import io
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

QOG_URL = "https://www.qogdata.pol.gu.se/data/qog_std_cs_jan25.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'WEF_GGGI'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('WEF_GGGI', 'WEF Global Gender Gap Index',
                'https://www.weforum.org/publications/series/global-gender-gap-report/',
                'Annual index measuring gender parity across economic, education, health and political dimensions. 146 countries, 2006-2024.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

INDICATORS = [
    ('WEF:gggi_ggi', 'gggi_ggi', 'Global Gender Gap Index (Overall)',              'Politics & Governance',  'Rule of Law & Rights',          'Gender & Political Equality'),
    ('WEF:gggi_eas', 'gggi_eas', 'Gender Gap: Educational Attainment subindex',    'Population & Demographics', 'Education & Literacy',         'Gender & Education'),
    ('WEF:gggi_hss', 'gggi_hss', 'Gender Gap: Health & Survival subindex',         'Health, Body & Behavior',   'Survival & Mortality',         'Gender & Health'),
    ('WEF:gggi_pes', 'gggi_pes', 'Gender Gap: Economic Participation subindex',    'Economy & Infrastructure',  'Labour & Employment',          'Gender & Labour'),
    ('WEF:gggi_pos', 'gggi_pos', 'Gender Gap: Political Empowerment subindex',     'Politics & Governance',  'Democracy & Elections',         'Gender & Political Equality'),
]

for code, col, name, domain, category, dimension in INDICATORS:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id, domain, category, dimension, 'score 0-1'))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

print("Lade QoG CSV...")
r = requests.get(QOG_URL, timeout=60)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text), low_memory=False)
print(f"  {len(df):,} Zeilen, {len(df.columns)} Spalten")

# QoG cross-section has 'ccodealp' (ISO3) and 'year'
iso_col  = 'ccodealp' if 'ccodealp' in df.columns else 'iso3'
year_col = 'year'     if 'year' in df.columns else None

total_saved = 0

for _, row in df.iterrows():
    iso3 = str(row.get(iso_col, '')).upper().strip()
    iso_numeric = iso3_to_numeric.get(iso3)
    if not iso_numeric:
        continue

    year = str(int(row[year_col])) if year_col and pd.notna(row.get(year_col)) else 'static'

    for code, col, *_ in INDICATORS:
        val = row.get(col)
        if pd.isna(val):
            continue
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, code, source_id, float(val), year))
        if cur.rowcount > 0:
            total_saved += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved:,} rows gespeichert.")
