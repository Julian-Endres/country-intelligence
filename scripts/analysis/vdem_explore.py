import pandas as pd
import psycopg2, os
from dotenv import load_dotenv

load_dotenv()

VDEM_FILE = '/home/julian/projects/country-intelligence/data/raw/V-Dem-CY-Full+Others-v16.csv'

# Komplette Datei laden - nur relevante Spalten
key_indicators = [
    'v2x_polyarchy', 'v2x_libdem', 'v2x_partipdem', 'v2x_delibdem', 'v2x_egaldem',
    'v2x_corr', 'v2x_rule', 'v2x_civlib', 'v2x_gender', 'v2x_accountability',
    'v2x_freexp', 'v2x_regime', 'v2x_clphy', 'v2x_clpol', 'v2x_clpriv'
]

print("Lade V-Dem Datei...")
df = pd.read_csv(
    VDEM_FILE,
    usecols=['country_name', 'country_text_id', 'year'] + key_indicators,
    low_memory=False
)

print(f"Zeilen gesamt: {len(df)}")
print(f"Länder: {df['country_text_id'].nunique()}")
print(f"Jahre: {df['year'].min()} - {df['year'].max()}")

# Country Code Match
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

print(f"\nMatch mit DB: {len(matched)}/{len(vdem_countries)}")
if unmatched:
    print(f"Kein Match: {sorted(unmatched)}")

# Coverage ab 2000
print("\nCoverage pro Indikator (Länder mit Daten ab 2000):")
recent = df[df['year'] >= 2000]
for ind in key_indicators:
    n = recent[recent[ind].notna()]['country_text_id'].nunique()
    print(f"  {ind:<30} {n} Länder")

cur.close()
conn.close()