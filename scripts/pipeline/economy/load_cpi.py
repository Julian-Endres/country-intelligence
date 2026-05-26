import psycopg2
import pycountry
import os
from dotenv import load_dotenv
from owid.catalog import search, fetch

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("""
    INSERT INTO sources (name, short_code, url, description)
    VALUES ('Transparency International', 'TI', 'https://transparency.org', 'Corruption Perceptions Index')
    ON CONFLICT (short_code) DO NOTHING
""")
cur.execute("SELECT id FROM sources WHERE short_code = 'TI'")
source_id = cur.fetchone()[0]

# Metadata
cur.execute("""
    INSERT INTO indicator_metadata (indicator_code, name, description, source_id, domain, dimension, category)
    VALUES ('TI:CPI', 'Corruption Perceptions Index', 
            'Average score across 13 expert and business surveys. 0=highly corrupt, 100=very clean.',
            %s, 'Politics & Governance', 'Corruption', 'Governance')
    ON CONFLICT (indicator_code) DO NOTHING
""", (source_id,))
conn.commit()
print("Metadata geladen.")

# Ländercodes
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
code3_to_iso = {row[1]: row[0] for row in cur.fetchall()}

manual_mapping = {
    'Congo': 'COG',
    'Democratic Republic of Congo': 'COD',
    'Czechia': 'CZE',
    'Turkey': 'TUR',
    'North Macedonia': 'MKD',
    'Eswatini': 'SWZ',
    'Timor-Leste': 'TLS',
    'Cape Verde': 'CPV',
    'East Timor': 'TLS',
}

def get_iso_numeric(country_name):
    if country_name in manual_mapping:
        return code3_to_iso.get(manual_mapping[country_name])
    try:
        result = pycountry.countries.search_fuzzy(country_name)
        return code3_to_iso.get(result[0].alpha_3)
    except:
        return None

# Daten laden
print("Lade CPI von OWID...")
results = search("corruption")
df = fetch(results.to_frame().iloc[0]['url'])
df = df.reset_index()

print(f"Zeilen: {len(df)}")

total_saved = 0
unmatched = set()

for _, row in df.iterrows():
    country_name = row['entities']
    year = str(row['years'])
    value = row['cpi_score']

    if not value or str(value) == 'nan':
        continue

    iso_numeric = get_iso_numeric(country_name)
    if not iso_numeric:
        unmatched.add(country_name)
        continue

    cur.execute("""
        INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
        VALUES (%s, 'TI:CPI', %s, %s, %s, 'A')
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
    """, (iso_numeric, source_id, float(value), year))
    total_saved += 1

conn.commit()
print(f"\nFertig! {total_saved} Datenpunkte geladen.")
if unmatched:
    print(f"Unmatched ({len(unmatched)}): {sorted(unmatched)}")

cur.close()
conn.close()