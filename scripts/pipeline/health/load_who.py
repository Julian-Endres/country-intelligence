import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://ghoapi.azureedge.net/api"

who_indicators = [
    # Environment
    ('WHO:SDGPM25', 'Concentrations of fine particulate matter (PM2.5)', 'Geography & Environment', 'Air Quality', '%'),
    ('WHO:WSH_WATER_BASIC', 'Population using at least basic drinking-water services', 'Social Fabric & Daily Life', 'WASH', '%'),
    ('WHO:WSH_SANITATION_BASIC', 'Population using at least basic sanitation services', 'Social Fabric & Daily Life', 'WASH', '%'),

    # Child & Maternal Health
    ('WHO:MDG_0000000001', 'Infant mortality rate (per 1000 live births)', 'Health, Body & Behavior', 'Child Health', 'per 1000'),
    ('WHO:MDG_0000000007', 'Under-five mortality rate (per 1000 live births)', 'Health, Body & Behavior', 'Child Health', 'per 1000'),
    ('WHO:WHOSIS_000014', 'Stillbirth rate (per 1000 total births)', 'Health, Body & Behavior', 'Child Health', 'per 1000'),
    ('WHO:CHILDMORT5TO14', 'Mortality rate 5-14 years (per 1000)', 'Health, Body & Behavior', 'Child Health', 'per 1000'),
    ('WHO:MDG_0000000003', 'Adolescent birth rate (per 1000 women)', 'Health, Body & Behavior', 'Reproductive Health', 'per 1000'),

    # Adult Nutrition
    ('WHO:NCD_BMI_30A', 'Prevalence of obesity among adults (age-standardized)', 'Health, Body & Behavior', 'Nutrition', '%'),
    ('WHO:NCD_BMI_25A', 'Prevalence of overweight among adults (age-standardized)', 'Health, Body & Behavior', 'Nutrition', '%'),
    ('WHO:NCD_BMI_18A', 'Prevalence of underweight among adults (age-standardized)', 'Health, Body & Behavior', 'Nutrition', '%'),
    ('WHO:NCD_DIABETES_PREVALENCE_AGESTD', 'Prevalence of diabetes (age-standardized)', 'Health, Body & Behavior', 'NCDs', '%'),
    ('WHO:NCD_DIABETES_TREATMENT_AGESTD', 'Diabetes treatment coverage (age-standardized)', 'Health, Body & Behavior', 'NCDs', '%'),

    # Children Nutrition
    ('WHO:NCD_BMI_PLUS1C', 'Prevalence of overweight among children (crude)', 'Health, Body & Behavior', 'Nutrition', '%'),
    ('WHO:NCD_BMI_MINUS2C', 'Prevalence of thinness among children (crude)', 'Health, Body & Behavior', 'Nutrition', '%'),

    # Vaccine-preventable diseases
    ('WHO:WHS3_62', 'Measles - reported cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),
    ('WHO:WHS3_57', 'Rubella - reported cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),
    ('WHO:WHS3_41', 'Diphtheria - reported cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),
    ('WHO:WHS3_43', 'Pertussis - reported cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),
    ('WHO:WHS3_53', 'Mumps - reported cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),

    # TB
    ('WHO:TB_c_newinc', 'Tuberculosis - new and relapse cases', 'Health, Body & Behavior', 'Infectious Disease', 'cases'),
    ('WHO:TB_c_new_tsr', 'TB treatment success rate', 'Health, Body & Behavior', 'Infectious Disease', '%'),
]

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
for code, name, domain, dimension, unit in who_indicators:
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, domain, dimension, unit, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, source_id, domain, dimension, unit, 'WHO'))

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

for code, name, domain, dimension, unit in who_indicators:
    who_code = code[4:]  # WHO: prefix entfernen
    print(f"Lade {code}...")

    data = fetch_all_data(who_code)
    print(f"  {len(data)} Datenpunkte gefunden")

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
            total_saved += 1
        except Exception as e:
            continue

    conn.commit()
    print(f"  Gespeichert. Total: {total_saved}")
    time.sleep(0.3)

cur.close()
conn.close()
print(f"\nFertig! {total_saved} Datenpunkte geladen.")