import pandas as pd
import psycopg2, os
from dotenv import load_dotenv

load_dotenv()

VDEM_FILE = '/home/julian/projects/country-intelligence/data/raw/V-Dem-CY-Full+Others-v16.csv'

# Erstmal nur Header laden um v2x_ Spalten zu finden
df_header = pd.read_csv(VDEM_FILE, nrows=0)
all_cols = df_header.columns.tolist()

# Alle v2x_ Indizes - keine statistischen Varianten
key_indicators = [
    c for c in all_cols 
    if c.startswith('v2x_') 
    and not any(c.endswith(s) for s in ['_codelow', '_codehigh', '_sd', '_osp', '_ord', '_mean', '_nr'])
]

print(f"v2x_ Indikatoren gefunden: {len(key_indicators)}")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source sicherstellen
cur.execute("""
    INSERT INTO sources (name, short_code, url, description)
    VALUES ('V-Dem Institute', 'VDEM', 'https://v-dem.net', 'Varieties of Democracy political indicators')
    ON CONFLICT (short_code) DO NOTHING
""")

cur.execute("SELECT id FROM sources WHERE short_code = 'VDEM'")
source_id = cur.fetchone()[0]

# Indicator Metadata - ohne Namen da zu viele
for code in key_indicators:
    full_code = f"VDEM:{code}"
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (full_code, code, source_id, 'Democracy', 'Politics & Governance', 'Democracy Indices'))

conn.commit()
print("Metadata geladen.")

# Ländercodes
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
country_map = {row[1]: row[0] for row in cur.fetchall()}

# Daten laden
print("Lade V-Dem CSV...")
df = pd.read_csv(
    VDEM_FILE,
    usecols=['country_text_id', 'year'] + key_indicators,
    low_memory=False
)

# Nur ab 1900 und gematchte Länder
df = df[df['year'] >= 1900]
df = df[df['country_text_id'].isin(country_map.keys())]

print(f"Zeilen zu laden: {len(df)}")

total_saved = 0
for _, row in df.iterrows():
    iso_numeric = country_map[row['country_text_id']]

    for ind_code in key_indicators:
        value = row[ind_code]
        if pd.isna(value):
            continue

        full_code = f"VDEM:{ind_code}"
        cur.execute("""
            INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
        """, (iso_numeric, full_code, source_id, float(value), str(row['year'])))
        total_saved += 1

    if total_saved % 10000 == 0:
        conn.commit()
        print(f"{total_saved} Datenpunkte gespeichert...")

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved} Datenpunkte geladen.")