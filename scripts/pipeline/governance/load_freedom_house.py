import pandas as pd
import psycopg2
import pycountry
import os
from dotenv import load_dotenv

load_dotenv()

FILE = '/home/julian/projects/country-intelligence/data/raw/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx'

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("""
    INSERT INTO sources (name, short_code, url, description)
    VALUES ('Freedom House', 'FH', 'https://freedomhouse.org', 'Freedom in the World annual ratings')
    ON CONFLICT (short_code) DO NOTHING
""")
cur.execute("SELECT id FROM sources WHERE short_code = 'FH'")
source_id = cur.fetchone()[0]

# Indicator Metadata
for code, name, desc in [
    ('FH:PR', 'Political Rights', 'Political Rights score 1-7 (1=most free)'),
    ('FH:CL', 'Civil Liberties', 'Civil Liberties score 1-7 (1=most free)'),
    ('FH:STATUS', 'Freedom Status', 'Free / Partly Free / Not Free'),
]:
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, description, source_id, domain, dimension, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, desc, source_id, 'Politics & Governance', 'Civil Liberties', 'Freedom'))

conn.commit()
print("Metadata geladen.")

# Ländercodes aus DB
cur.execute("SELECT iso_numeric, iso_code_3, name FROM countries")
db_countries = cur.fetchall()
name_to_iso = {row[2].lower(): row[0] for row in db_countries}
code3_to_iso = {row[1]: row[0] for row in db_countries}

manual_mapping = {
    'Congo (Brazzaville)': 'COG',
    'Congo (Kinshasa)': 'COD',
    'St. Kitts and Nevis': 'KNA',
    'St. Lucia': 'LCA',
    'St. Vincent and the Grenadines': 'VCT',
    'Turkey': 'TUR',
}

def get_iso_numeric(country_name):
    # Manuelles Mapping zuerst
    if country_name in manual_mapping:
        return code3_to_iso.get(manual_mapping[country_name])
    # Dann pycountry
    try:
        result = pycountry.countries.search_fuzzy(country_name)
        alpha3 = result[0].alpha_3
        return code3_to_iso.get(alpha3)
    except:
        return None

# Excel laden
print("Lade Excel...")
df = pd.read_excel(FILE, sheet_name='Country Ratings, Statuses ', header=[0,1])
df.columns = ['_'.join([str(a).strip(), str(b).strip()]) for a, b in df.columns]
df = df[df.iloc[:,0].notna()]
country_col = df.columns[0]
df = df.rename(columns={country_col: 'country_name'})
df = df[df['country_name'] != 'nan']

print(f"Länder: {len(df)}")

# Spalten parsen - jede Gruppe ist PR, CL, Status
cols = df.columns.tolist()
year_groups = []
for i in range(1, len(cols), 3):
    col = cols[i]
    year_str = col.split('_')[-1]
    try:
        year = int(year_str.split('-')[-1]) if '-' in year_str else int(year_str)
        if 1970 <= year <= 2030:
            year_groups.append((year, cols[i], cols[i+1] if i+1 < len(cols) else None))
    except:
        pass

print(f"Jahre: {len(year_groups)}")

total_saved = 0
unmatched_countries = set()

for _, row in df.iterrows():
    country_name = str(row['country_name']).strip()
    iso_numeric = get_iso_numeric(country_name)

    if not iso_numeric:
        unmatched_countries.add(country_name)
        continue

    for year, pr_col, cl_col in year_groups:
        pr_val = row[pr_col]
        cl_val = row[cl_col] if cl_col else None

        # PR
        if pd.notna(pr_val) and str(pr_val) not in ['-', '..', 'nan']:
            try:
                cur.execute("""
                    INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, 'FH:PR', %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, source_id, float(pr_val), str(year)))
                total_saved += 1
            except:
                pass

        # CL
        if cl_col and pd.notna(cl_val) and str(cl_val) not in ['-', '..', 'nan']:
            try:
                cur.execute("""
                    INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, 'FH:CL', %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, source_id, float(cl_val), str(year)))
                total_saved += 1
            except:
                pass

    if total_saved % 5000 == 0 and total_saved > 0:
        conn.commit()
        print(f"{total_saved} Datenpunkte gespeichert...")

conn.commit()
print(f"\nFertig! {total_saved} Datenpunkte geladen.")
print(f"Unmatched Länder ({len(unmatched_countries)}): {sorted(unmatched_countries)[:20]}")

cur.close()
conn.close()
