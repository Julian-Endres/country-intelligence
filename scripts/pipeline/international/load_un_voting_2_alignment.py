"""
load_un_voting_2_alignment.py — UN Voting: Bloc Alignment
==========================================================
Etappe 2: Agreement rates USA, RUS, CHN, EU core, BRICS
Run: python3 scripts/pipeline/international/load_un_voting_2_alignment.py
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

for code, name in [
    ('UNVOTE:agree_usa',   'UN GA: Voting agreement with USA (%)'),
    ('UNVOTE:agree_rus',   'UN GA: Voting agreement with Russia (%)'),
    ('UNVOTE:agree_chn',   'UN GA: Voting agreement with China (%)'),
    ('UNVOTE:agree_eu',    'UN GA: Voting agreement with EU core (FRA+DEU+ITA, %)'),
    ('UNVOTE:agree_brics', 'UN GA: Voting agreement with BRICS (BRA+RUS+IND+CHN, %)'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id,
          'International Relations & Global Integration',
          'Diplomatic Alignment', 'UN Voting', '%'))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

# Load only needed columns
print("Lade CSV...")
df = pd.read_csv(VOTING_FILE, usecols=['ms_code', 'ms_vote', 'date', 'undl_id'],
                 low_memory=False)
print(f"  {len(df):,} Zeilen")

df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
df = df.dropna(subset=['year', 'ms_code', 'ms_vote'])
df['year'] = df['year'].astype(int)

vote_map = {'Y': 'yes', 'N': 'no', 'A': 'abstain', 'X': 'nonvote'}
df['vote_clean'] = df['ms_vote'].map(vote_map)
df = df[df['vote_clean'].isin(['yes', 'no', 'abstain'])]

# Build reference lookup: undl_id → vote for each reference country
print("Baue Referenz-Lookups...")
REF_COUNTRIES = {
    'USA': 'usa', 'RUS': 'rus', 'CHN': 'chn',
    'FRA': 'fra', 'DEU': 'deu', 'ITA': 'ita',
    'BRA': 'bra', 'IND': 'ind',
}

ref_votes = {}
for iso3, key in REF_COUNTRIES.items():
    ref_df = df[df['ms_code'] == iso3][['undl_id', 'vote_clean']].copy()
    ref_df = ref_df.drop_duplicates('undl_id').set_index('undl_id')['vote_clean']
    ref_votes[key] = ref_df
    print(f"  {iso3}: {len(ref_df):,} Resolutionen")

def agree_rate(grp_ids, grp_votes, ref_series):
    common = grp_ids.isin(ref_series.index)
    if common.sum() < 3:
        return None
    grp_sub = grp_votes[common]
    ref_sub = ref_series[grp_ids[common]]
    matches = (grp_sub.values == ref_sub.values).sum()
    return float(round(matches / len(grp_sub) * 100, 2))

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

    grp_ids   = grp['undl_id'].reset_index(drop=True)
    grp_votes = grp['vote_clean'].reset_index(drop=True)

    ag_usa = agree_rate(grp_ids, grp_votes, ref_votes['usa'])
    ag_rus = agree_rate(grp_ids, grp_votes, ref_votes['rus'])
    ag_chn = agree_rate(grp_ids, grp_votes, ref_votes['chn'])
    ag_fra = agree_rate(grp_ids, grp_votes, ref_votes['fra'])
    ag_deu = agree_rate(grp_ids, grp_votes, ref_votes['deu'])
    ag_ita = agree_rate(grp_ids, grp_votes, ref_votes['ita'])
    ag_bra = agree_rate(grp_ids, grp_votes, ref_votes['bra'])
    ag_ind = agree_rate(grp_ids, grp_votes, ref_votes['ind'])

    eu_rates  = [r for r in [ag_fra, ag_deu, ag_ita] if r is not None]
    brics_rates = [r for r in [ag_bra, ag_rus, ag_ind, ag_chn] if r is not None]

    ag_eu    = float(round(sum(eu_rates)    / len(eu_rates), 2))    if eu_rates    else None
    ag_brics = float(round(sum(brics_rates) / len(brics_rates), 2)) if brics_rates else None

    for code, value in [
        ('UNVOTE:agree_usa',   ag_usa),
        ('UNVOTE:agree_rus',   ag_rus),
        ('UNVOTE:agree_chn',   ag_chn),
        ('UNVOTE:agree_eu',    ag_eu),
        ('UNVOTE:agree_brics', ag_brics),
    ]:
        if value is None:
            continue
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
