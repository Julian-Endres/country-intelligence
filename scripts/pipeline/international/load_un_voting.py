"""
load_un_voting.py — UN General Assembly Voting Data
=====================================================
Source:  UN Digital Library
         https://digitallibrary.un.org/
Domain:  International Relations & Global Integration
Coverage: 202 countries, 1946-2025

Indicators:
  Voting behaviour:
    UNVOTE:yes_share        — Share of Yes votes (%)
    UNVOTE:no_share         — Share of No votes (%)
    UNVOTE:abstain_share    — Share of Abstentions (%)
    UNVOTE:nonvote_share    — Share of Non-voting (%)
    UNVOTE:minority_share   — % of votes on losing side
    UNVOTE:n_votes          — Total votes cast

  Alignment with blocs:
    UNVOTE:agree_usa        — Agreement with USA (%)
    UNVOTE:agree_rus        — Agreement with Russia (%)
    UNVOTE:agree_chn        — Agreement with China (%)
    UNVOTE:agree_eu         — Agreement with EU core (FRA+DEU+ITA avg, %)
    UNVOTE:agree_brics      — Agreement with BRICS (BRA+RUS+IND+CHN avg, %)

  Thematic yes-rates:
    UNVOTE:yes_disarmament  — Yes-rate on Disarmament resolutions (%)
    UNVOTE:yes_human_rights — Yes-rate on Human Rights resolutions (%)
    UNVOTE:yes_palestine    — Yes-rate on Palestine resolutions (%)
    UNVOTE:yes_decolonize   — Yes-rate on Decolonization resolutions (%)
    UNVOTE:yes_environment  — Yes-rate on Sustainable Development resolutions (%)

Run:
  python3 scripts/pipeline/international/load_un_voting.py
"""

import psycopg2
import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

VOTING_FILE = "data/raw/Manuell_27-05/2026_02_06_ga_voting.csv"

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'UNVOTE'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (short_code, name, url, description)
        VALUES ('UNVOTE', 'UN General Assembly Voting Data',
                'https://digitallibrary.un.org/',
                'UN General Assembly vote records by country and resolution, 1946-2025.')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# Metadata
indicators = [
    ('UNVOTE:yes_share',        'UN GA: Share of Yes votes (%)',                    '%'),
    ('UNVOTE:no_share',         'UN GA: Share of No votes (%)',                     '%'),
    ('UNVOTE:abstain_share',    'UN GA: Share of Abstentions (%)',                  '%'),
    ('UNVOTE:nonvote_share',    'UN GA: Share of Non-voting (%)',                   '%'),
    ('UNVOTE:minority_share',   'UN GA: Share of votes on losing side (%)',         '%'),
    ('UNVOTE:n_votes',          'UN GA: Total votes cast',                          'count'),
    ('UNVOTE:agree_usa',        'UN GA: Voting agreement with USA (%)',             '%'),
    ('UNVOTE:agree_rus',        'UN GA: Voting agreement with Russia (%)',          '%'),
    ('UNVOTE:agree_chn',        'UN GA: Voting agreement with China (%)',           '%'),
    ('UNVOTE:agree_eu',         'UN GA: Voting agreement with EU core (%)',         '%'),
    ('UNVOTE:agree_brics',      'UN GA: Voting agreement with BRICS (%)',           '%'),
    ('UNVOTE:yes_disarmament',  'UN GA: Yes-rate on Disarmament resolutions (%)',   '%'),
    ('UNVOTE:yes_human_rights', 'UN GA: Yes-rate on Human Rights resolutions (%)', '%'),
    ('UNVOTE:yes_palestine',    'UN GA: Yes-rate on Palestine resolutions (%)',     '%'),
    ('UNVOTE:yes_decolonize',   'UN GA: Yes-rate on Decolonization resolutions (%)','%'),
    ('UNVOTE:yes_environment',  'UN GA: Yes-rate on Environment resolutions (%)',   '%'),
]

for code, name, unit in indicators:
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
          'Diplomatic Alignment',
          'UN Voting',
          unit))

conn.commit()
print("Metadata geladen.")

# Country mapping
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
iso3_to_numeric = {row[1].upper(): row[0] for row in cur.fetchall()}

# Load CSV
print(f"Lade {VOTING_FILE}...")
df = pd.read_csv(VOTING_FILE, low_memory=False)
print(f"  {len(df):,} Zeilen geladen")

# Parse year
df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
df = df.dropna(subset=['year', 'ms_code', 'ms_vote'])
df['year'] = df['year'].astype(int)

# Standardize vote codes
# Y=Yes, N=No, A=Abstain, X=Non-voting/Absent
vote_map = {'Y': 'yes', 'N': 'no', 'A': 'abstain', 'X': 'nonvote'}
df['vote_clean'] = df['ms_vote'].map(vote_map)
df = df[df['vote_clean'].notna()]

print(f"  {len(df):,} Zeilen nach Filterung")
print(f"  Jahre: {df['year'].min()} - {df['year'].max()}")

# Subject classification
THEMES = {
    'disarmament':  ['DISARMAMENT'],
    'human_rights': ['HUMAN RIGHTS'],
    'palestine':    ['PALESTINE', 'TERRITORIES OCCUPIED BY ISRAEL'],
    'decolonize':   ['DECOLONIZATION', 'SELF-DETERMINATION', 'NON-SELF-GOVERNING'],
    'environment':  ['SUSTAINABLE DEVELOPMENT', 'CLIMATE', 'ENVIRONMENT'],
}

def matches_theme(subject_str, keywords):
    if pd.isna(subject_str):
        return False
    return any(kw in subject_str.upper() for kw in keywords)

# Pre-classify resolutions by theme
res_subjects = df[['undl_id', 'subjects']].drop_duplicates('undl_id')
for theme, keywords in THEMES.items():
    res_subjects[f'theme_{theme}'] = res_subjects['subjects'].apply(
        lambda s: matches_theme(s, keywords)
    )

df = df.merge(res_subjects[['undl_id'] + [f'theme_{t}' for t in THEMES]], on='undl_id', how='left')

# Reference country votes per resolution
def get_ref_votes(iso3):
    return df[df['ms_code'] == iso3][['undl_id', 'vote_clean']].rename(
        columns={'vote_clean': f'ref_{iso3.lower()}'}
    ).drop_duplicates('undl_id')

print("Lade Referenzland-Votes...")
ref_usa = get_ref_votes('USA')
ref_rus = get_ref_votes('RUS')
ref_chn = get_ref_votes('CHN')
ref_fra = get_ref_votes('FRA')
ref_deu = get_ref_votes('DEU')
ref_ita = get_ref_votes('ITA')
ref_bra = get_ref_votes('BRA')
ref_ind = get_ref_votes('IND')

def agreement_rate(grp, ref_df, ref_col):
    merged = grp[['undl_id', 'vote_clean']].merge(ref_df, on='undl_id', how='inner')
    merged = merged[merged['vote_clean'].isin(['yes', 'no', 'abstain'])]
    merged = merged[merged[ref_col].isin(['yes', 'no', 'abstain'])]
    if len(merged) < 3:
        return None
    return round((merged['vote_clean'] == merged[ref_col]).sum() / len(merged) * 100, 2)

def multi_agreement(grp, refs):
    rates = [r for r in refs if r is not None]
    return round(float(np.mean(rates)), 2) if rates else None

print("Aggregiere pro Land und Jahr...")
total_saved = 0
total_skipped = 0

groups = list(df.groupby(['ms_code', 'year']))
print(f"  {len(groups):,} Länder-Jahr Kombinationen")

for i, ((ms_code, year), grp) in enumerate(groups):
    if i % 5000 == 0 and i > 0:
        conn.commit()
        print(f"  {i:,}/{len(groups):,} verarbeitet, {total_saved:,} gespeichert...")

    iso_numeric = iso3_to_numeric.get(ms_code.upper())
    if not iso_numeric:
        continue

    n_total = len(grp)
    if n_total < 3:
        continue

    castable = grp[grp['vote_clean'].isin(['yes', 'no', 'abstain'])]
    n_cast = len(castable)
    n_nonvote = (grp['vote_clean'] == 'nonvote').sum()

    if n_cast == 0:
        continue

    yes_share    = round((castable['vote_clean'] == 'yes').sum() / n_total * 100, 2)
    no_share     = round((castable['vote_clean'] == 'no').sum() / n_total * 100, 2)
    abstain_share= round((castable['vote_clean'] == 'abstain').sum() / n_total * 100, 2)
    nonvote_share= round(n_nonvote / n_total * 100, 2)

    # Minority share
    try:
        res_totals = df[df['undl_id'].isin(grp['undl_id'])][['undl_id', 'total_yes', 'total_no']].drop_duplicates('undl_id')
        res_totals['total_yes'] = pd.to_numeric(res_totals['total_yes'], errors='coerce')
        res_totals['total_no'] = pd.to_numeric(res_totals['total_no'], errors='coerce')
        minority_merged = castable[castable['vote_clean'].isin(['yes', 'no'])].merge(res_totals, on='undl_id', how='left')
        minority_merged = minority_merged.dropna(subset=['total_yes', 'total_no'])
        if len(minority_merged) > 0:
            on_losing = (
                ((minority_merged['vote_clean'] == 'yes') & (minority_merged['total_yes'] < minority_merged['total_no'])) |
                ((minority_merged['vote_clean'] == 'no') & (minority_merged['total_no'] < minority_merged['total_yes']))
            ).sum()
            minority_share = round(on_losing / len(minority_merged) * 100, 2)
        else:
            minority_share = None
    except Exception:
        minority_share = None

    # Agreement rates
    ag_usa = agreement_rate(grp, ref_usa, 'ref_usa')
    ag_rus = agreement_rate(grp, ref_rus, 'ref_rus')
    ag_chn = agreement_rate(grp, ref_chn, 'ref_chn')
    ag_fra = agreement_rate(grp, ref_fra, 'ref_fra')
    ag_deu = agreement_rate(grp, ref_deu, 'ref_deu')
    ag_ita = agreement_rate(grp, ref_ita, 'ref_ita')
    ag_bra = agreement_rate(grp, ref_bra, 'ref_bra')
    ag_ind = agreement_rate(grp, ref_ind, 'ref_ind')

    ag_eu = multi_agreement(grp, [ag_fra, ag_deu, ag_ita])
    ag_brics = multi_agreement(grp, [ag_bra, ag_rus, ag_ind, ag_chn])

    # Thematic yes-rates
    theme_rates = {}
    for theme in THEMES:
        theme_grp = grp[grp[f'theme_{theme}'] == True]
        theme_cast = theme_grp[theme_grp['vote_clean'].isin(['yes', 'no', 'abstain'])]
        if len(theme_cast) >= 3:
            theme_rates[theme] = round(
                (theme_cast['vote_clean'] == 'yes').sum() / len(theme_cast) * 100, 2
            )

    # Build values dict
    values = [
        ('UNVOTE:yes_share',     yes_share),
        ('UNVOTE:no_share',      no_share),
        ('UNVOTE:abstain_share', abstain_share),
        ('UNVOTE:nonvote_share', nonvote_share),
        ('UNVOTE:n_votes',       float(n_total)),
    ]
    if minority_share is not None:
        values.append(('UNVOTE:minority_share', minority_share))
    if ag_usa is not None:
        values.append(('UNVOTE:agree_usa', ag_usa))
    if ag_rus is not None:
        values.append(('UNVOTE:agree_rus', ag_rus))
    if ag_chn is not None:
        values.append(('UNVOTE:agree_chn', ag_chn))
    if ag_eu is not None:
        values.append(('UNVOTE:agree_eu', ag_eu))
    if ag_brics is not None:
        values.append(('UNVOTE:agree_brics', ag_brics))
    for theme, rate in theme_rates.items():
        values.append((f'UNVOTE:yes_{theme}', rate))

    for code, value in values:
        value = float(value) if value is not None else None
        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, code, source_id, value, str(year)))
        if cur.rowcount > 0:
            total_saved += 1
        else:
            total_skipped += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! Neu: {total_saved:,} | Bereits vorhanden: {total_skipped:,}")
