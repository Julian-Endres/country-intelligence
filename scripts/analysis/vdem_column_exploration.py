import pandas as pd
import psycopg2, os
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv(
    '/home/julian/projects/country-intelligence/data/raw/V-Dem-CY-Full+Others-v16.csv',
    nrows=5000,
    low_memory=False
)

print(f"Spalten gesamt: {len(df.columns)}")
print(f"Zeilen in Sample: {len(df)}")
print(f"\nJahre: {df['year'].min()} - {df['year'].max()}")
print(f"Länder: {df['country_text_id'].nunique()}")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()
cur.execute("SELECT iso_code_3 FROM countries")
db_countries = {row[0] for row in cur.fetchall()}

vdem_countries = set(df['country_text_id'].dropna().unique())
matched = vdem_countries & db_countries
unmatched = vdem_countries - db_countries

print(f"\nV-Dem Länder: {len(vdem_countries)}")
print(f"Match mit DB: {len(matched)}")
print(f"Kein Match: {len(unmatched)}")
if unmatched:
    print(f"Unmatched: {sorted(unmatched)}")

# Spalten nach Präfix gruppieren
cols = df.columns.tolist()
v2_cols = [c for c in cols if c.startswith('v2')]
e_cols = [c for c in cols if c.startswith('e_')]
meta_cols = [c for c in cols if not c.startswith('v2') and not c.startswith('e_')]

print(f"\nv2* Indikatoren (V-Dem Kern): {len(v2_cols)}")
print(f"e_* Indikatoren (External): {len(e_cols)}")
print(f"Meta-Spalten: {len(meta_cols)}")
print(f"\nMeta-Spalten: {meta_cols[:20]}")
print(f"\nErste 20 v2* Spalten: {v2_cols[:20]}")

# Nur Haupt-Indikatoren ohne statistische Varianten
main_v2 = [c for c in v2_cols if not any(
    c.endswith(s) for s in ['_codelow', '_codehigh', '_sd', '_osp', '_ord', '_mean', '_nr']
)]

print(f"\nv2* Haupt-Indikatoren (ohne stat. Varianten): {len(main_v2)}")
print(f"\nErste 30: {main_v2[:30]}")

# v2x_ sind die wichtigsten - das sind die Indizes
v2x_cols = [c for c in main_v2 if c.startswith('v2x_')]
print(f"\nv2x_ Indizes (Top-Level): {len(v2x_cols)}")
print(v2x_cols)

cur.close()
conn.close()