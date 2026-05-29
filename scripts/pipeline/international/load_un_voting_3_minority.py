"""
load_un_voting_3_minority.py — UN Voting: Minority Share
=========================================================
Etappe 3: How often does a country vote on the losing side?
Run: python3 scripts/pipeline/international/load_un_voting_3_minority.py
"""

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

VOTING_FILE = "data/raw/Manuell_27-05/2026_02_06_ga_voting.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'UNVOTE'")
source_id = cur.fetchone()[0]

cur.execute("""
    INSERT INTO indicator_metadata
        (indicator_code, name, source_id, domain, category, dimension, unit)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (indicator_code) DO NOTHING
""", ('UNVOTE:minority_share', 'UN GA: Share of votes on losing side (%)',
      source_id, 'International Relations & Global Integration',
      'Diplomatic Alignment', 'UN Voting', '%'))
conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

print("Lade CSV...")
df = pd.read_csv(VOTING_FILE,
                 usecols=['ms_code', 'ms_vote', 'date', 'undl_id', 'total_yes', 'total_no'],
                 low_memory=False)
print(f"  {len(df):,} Zeilen")

df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
df = df.dropna(subset=['year', 'ms_code', 'ms_vote'])
df['year'] = df['year'].astype(int)
df['total_yes'] = pd.to_numeric(df['total_yes'], errors='coerce')
df['total_no']  = pd.to_numeric(df['total_no'],  errors='coerce')

vote_map = {'Y': 'yes', 'N': 'no'}
df['vote_clean'] = df['ms_vote'].map(vote_map)
df = df[df['vote_clean'].notna()]
df = df.dropna(subset=['total_yes', 'total_no'])

# Pre-compute majority per resolution
res_majority = df[['undl_id', 'total_yes', 'total_no']].drop_duplicates('undl_id').copy()
res_majority['majority'] = (res_majority['total_yes'] >= res_majority['total_no']).map(
    {True: 'yes', False: 'no'}
)
majority_map = res_majority.set_index('undl_id')['majority']

total_saved = 0
groups = list(df.groupby(['ms_code', 'year']))
print(f"  {len(groups):,} Länder-Jahr Kombinationen")

for i, ((ms_code, year), grp) in enumerate(groups):
    if i % 2000 == 0 and i > 0:
        conn.commit()
        print(f"  {i:,}/{len(groups):,} | {total_saved:,} gespeichert")

    iso_numeric = iso3_to_numeric.get(str(ms_code).upper())
    if not iso_numeric:
        continue

    if len(grp) < 3:
        continue

    # Compare each vote to majority
    res_maj = majority_map.reindex(grp['undl_id'])
    valid = res_maj.notna()
    if valid.sum() < 3:
        continue

    on_losing = (grp['vote_clean'].values[valid.values] != res_maj.values[valid.values]).sum()
    minority_share = float(round(on_losing / valid.sum() * 100, 2))

    cur.execute("""
        INSERT INTO indicators
            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
        VALUES (%s, %s, %s, %s, %s, 'A')
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
    """, (iso_numeric, 'UNVOTE:minority_share', source_id, minority_share, str(year)))
    if cur.rowcount > 0:
        total_saved += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved:,} rows gespeichert.")
