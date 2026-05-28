import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://ghoapi.azureedge.net/api"

# NCD_PAA: Insufficient physical activity among adults (age-standardized, %)
# UHC_INDEX_REPORTED: UHC Service Coverage Index (0-100)
who_indicators = [
    ('WHO:NCD_PAA', 'Prevalence of insufficient physical activity among adults (age-standardized)', 'Health, Body & Behavior', 'Risk Behavior', 'Substance Use', '%'),
    ('WHO:UHC_INDEX_REPORTED', 'UHC Service Coverage Index', 'Health, Body & Behavior', 'Health System', 'Healthcare System', 'score 0-100'),
]

# category = SIF 4-level hierarchy (Survival & Mortality / Disease & Burden / etc.)
# dimension = sub-dimension within category

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'WHO'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES ('World Health Organization', 'WHO', 'https://www.who.int/data', 'Health and disease statistics worldwide')
        RETURNING id
    """)
    source_id = cur.fetchone()[0]
else:
    source_id = row[0]

# Metadata
for code, name, domain, category, dimension, unit in who_indicators:
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            name = EXCLUDED.name,
            domain = EXCLUDED.domain,
            category = EXCLUDED.category,
            dimension = EXCLUDED.dimension,
            unit = EXCLUDED.unit
    """, (code, name, source_id, domain, category, dimension, unit))

conn.commit()
print("Metadata geladen.")

# Ländercodes
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
country_map = {row[1]: row[0] for row in cur.fetchall()}

def fetch_all_data(who_code):
    all_data = []
    skip = 0
    while True:
        url = f"{BASE_URL}/{who_code}?$select=SpatialDim,TimeDim,NumericValue&$top=1000&$skip={skip}"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} bei skip={skip}")
                break
            batch = r.json().get("value", [])
            if not batch:
                break
            all_data.extend(batch)
            if len(batch) < 1000:
                break
            skip += 1000
            time.sleep(0.1)
        except Exception as e:
            print(f"  Fehler beim Laden: {e}")
            break
    return all_data

total_saved = 0

for code, name, domain, category, dimension, unit in who_indicators:
    who_code = code[4:]  # WHO: prefix entfernen
    print(f"Lade {code}...")

    data = fetch_all_data(who_code)
    print(f"  {len(data)} Datenpunkte gefunden")

    saved = 0
    for entry in data:
        spatial = entry.get("SpatialDim", "")
        year = entry.get("TimeDim")
        value = entry.get("NumericValue")

        if not spatial or len(spatial) != 3:
            continue
        if spatial not in country_map:
            continue
        if value is None:
            continue

        iso_numeric = country_map[spatial]

        try:
            cur.execute("""
                INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, code, source_id, float(value), str(year)))
            saved += 1
            total_saved += 1
        except Exception as e:
            continue

    conn.commit()
    print(f"  {saved} Zeilen gespeichert. Total: {total_saved}")
    time.sleep(0.3)

cur.close()
conn.close()
print(f"\nFertig! {total_saved} Datenpunkte geladen.")
