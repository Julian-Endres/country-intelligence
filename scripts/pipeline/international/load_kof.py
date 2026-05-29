"""
load_kof.py — KOF Globalisation Index
======================================
Source:  KOF Swiss Economic Institute, ETH Zurich
         https://kof.ethz.ch/en/forecasts-and-indicators/indicators/kof-globalisation-index.html
Domain:  International Relations & Global Integration
Coverage: ~200 countries, 1970-2023

Indicators loaded:
  KOF:gi    — Overall Globalisation Index
  KOF:ecgi  — Economic Globalisation
  KOF:trgi  — Trade Globalisation
  KOF:figi  — Financial Globalisation
  KOF:sogi  — Social Globalisation
  KOF:pogi  — Political Globalisation
  KOF:cugi  — Cultural Globalisation
  KOF:ingi  — Informational Globalisation
  KOF:ipgi  — Interpersonal Globalisation

Run:
  python3 scripts/pipeline/international/load_kof.py
"""

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

KOF_FILE = "data/raw/Manuell_27-05/KOF/kof_data_export_2026-05-28_22_06_58.xlsx"

# KOF subindex codes we want to load (overall + main subindices, de facto only)
INDICATORS = {
    "gi":   ("KOF:gi",   "KOF Globalisation Index (Overall)",         "score 0-100"),
    "ecgi": ("KOF:ecgi", "KOF Economic Globalisation Index",          "score 0-100"),
    "trgi": ("KOF:trgi", "KOF Trade Globalisation Index",             "score 0-100"),
    "figi": ("KOF:figi", "KOF Financial Globalisation Index",         "score 0-100"),
    "sogi": ("KOF:sogi", "KOF Social Globalisation Index",            "score 0-100"),
    "pogi": ("KOF:pogi", "KOF Political Globalisation Index",         "score 0-100"),
    "cugi": ("KOF:cugi", "KOF Cultural Globalisation Index",          "score 0-100"),
    "ingi": ("KOF:ingi", "KOF Informational Globalisation Index",     "score 0-100"),
    "ipgi": ("KOF:ipgi", "KOF Interpersonal Globalisation Index",     "score 0-100"),
}

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'KOF'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('KOF', 'KOF Swiss Economic Institute – Globalisation Index',
                'https://kof.ethz.ch/en/forecasts-and-indicators/indicators/kof-globalisation-index.html',
                'Annual globalisation index measuring economic, social and political integration. ~200 countries, 1970-2023.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# Metadata
for subidx, (code, name, unit) in INDICATORS.items():
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
          'Globalisation',
          'Globalisation Index',
          unit))

conn.commit()
print("Metadata geladen.")

# Country mapping
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].lower(): row[0] for row in cur.fetchall()}

# Load Excel
print(f"Lade {KOF_FILE}...")
df = pd.read_excel(KOF_FILE)
print(f"  {df.shape[0]} Jahre, {df.shape[1]} Spalten")

# Reshape: wide → long
# Column format: ch.kof.globidx.v2020.{subidx}.{iso3}
total_saved = 0
total_skipped = 0

for subidx, (code, name, unit) in INDICATORS.items():
    saved = 0
    skipped = 0

    # Find all columns for this subindex
    cols = [c for c in df.columns if f'.{subidx}.' in c and c != 'date']

    for col in cols:
        iso3 = col.split('.')[-1].lower()
        iso_numeric = iso3_to_numeric.get(iso3)
        if not iso_numeric:
            continue

        for _, row in df[['date', col]].dropna(subset=[col]).iterrows():
            year = str(row['date'])[:4]  # '1970-01' → '1970'
            value = float(row[col])

            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, code, source_id, value, year))

            if cur.rowcount > 0:
                saved += 1
            else:
                skipped += 1

    conn.commit()
    total_saved += saved
    total_skipped += skipped
    print(f"  {code}: {saved} neu, {skipped} bereits vorhanden")

cur.close()
conn.close()
print(f"\nFertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")
