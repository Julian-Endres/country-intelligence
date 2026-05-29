"""
load_un_voting_4_themes.py — UN Voting: Thematic Yes-Rates
===========================================================
Etappe 4: Yes-rates by topic (Disarmament, Human Rights, etc.)
Run: python3 scripts/pipeline/international/load_un_voting_4_themes.py
"""

import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

VOTING_FILE = "data/raw/Manuell_27-05/2026_02_06_ga_voting.csv"

THEMES = {
    'disarmament':  ['DISARMAMENT'],
    'human_rights': ['HUMAN RIGHTS'],
    'palestine':    ['PALESTINE', 'TERRITORIES OCCUPIED BY ISRAEL'],
    'decolonize':   ['DECOLONIZATION', 'SELF-DETERMINATION', 'NON-SELF-GOVERNING'],
    'environment':  ['SUSTAINABLE DEVELOPMENT', 'CLIMATE', 'ENVIRONMENT'],
}

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'UNVOTE'")
source_id = cur.fetchone()[0]

for theme in THEMES:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (f'UNVOTE:yes_{theme}',
          f'UN GA: Yes-rate on {theme.replace("_", " ").title()} resolutions (%)',
          source_id,
          'International Relations & Global Integration',
          'Diplomatic Alignment', 'UN Voting', '%'))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

print("Lade CSV...")
df = pd.read_csv(VOTING_FILE,
                 usecols=['ms_code', 'ms_vote', 'date', 'undl_id', 'subjects'],
                 low_memory=False)
print(f"  {len(df):,} Zeilen")

df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
df = df.dropna(subset=['year', 'ms_code', 'ms_vote'])
df['year'] = df['year'].astype(int)

vote_map = {'Y': 'yes', 'N': 'no', 'A': 'abstain'}
df['vote_clean'] = df['ms_vote'].map(vote_map)
df = df[df['vote_clean'].notna()]

# Pre-classify resolutions by theme
print("Klassifiziere Resolutionen nach Thema...")
res_subjects = df[['undl_id', 'subjects']].drop_duplicates('undl_id').copy()
for theme, keywords in THEMES.items():
    res_subjects[f'theme_{theme}'] = res_subjects['subjects'].apply(
        lambda s: any(kw in str(s).upper() for kw in keywords) if pd.notna(s) else False
    )

# Merge theme flags back
df = df.merge(
    res_subjects[['undl_id'] + [f'theme_{t}' for t in THEMES]],
    on='undl_id', how='left'
)

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

    for theme in THEMES:
        theme_grp = grp[grp[f'theme_{theme}'] == True]
        if len(theme_grp) < 3:
            continue
        yes_rate = float(round(
            (theme_grp['vote_clean'] == 'yes').sum() / len(theme_grp) * 100, 2
        ))
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, f'UNVOTE:yes_{theme}', source_id, yes_rate, str(year)))
        if cur.rowcount > 0:
            total_saved += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved:,} rows gespeichert.")
