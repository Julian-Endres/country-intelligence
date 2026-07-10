"""
ACLED Loader — für Politics Domain, Category "Security & Conflict"
Angepasst an etabliertes Pipeline-Pattern (siehe load_resource_rents.py).

Lädt 5 ACLED Country-Year Indikatoren, 2017-2026:
- political_violence_events
- fatalities
- demonstration_events
- civilian_targeting_events
- civilian_fatalities

Ablage: scripts/pipeline/governance/load_acled.py
"""

import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import country_converter as coco

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

DATA_DIR = "data/raw/governance/ACLED"
SOURCE_ID = 140  # ACLED, siehe sources-Tabelle

# ------------------------------------------------------------------
# 0. Metadata-Einträge anlegen
# ------------------------------------------------------------------
metadata = {
    "ACLED:political_violence_events": ("Political Violence Events (Count)", "count",
        "Battle, explosion/remote violence, and violence against civilians events per year"),
    "ACLED:fatalities": ("Reported Fatalities (Total)", "count",
        "All reported fatalities from political violence per year"),
    "ACLED:demonstration_events": ("Demonstration Events (Count)", "count",
        "Protest and violent demonstration events per year"),
    "ACLED:civilian_targeting_events": ("Events Targeting Civilians (Count)", "count",
        "All civilian targeting events including remote violence"),
    "ACLED:civilian_fatalities": ("Reported Civilian Fatalities (Total)", "count",
        "Reported fatalities from events targeting civilians"),
}

for code, (name, unit, desc) in metadata.items():
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, unit, description, source_id, category, domain, dimension)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, unit, desc, SOURCE_ID, "Security & Conflict",
          "Politics, Governance & Law", "Political Violence"))

conn.commit()
print("Metadata-Einträge geprüft/angelegt.")
print("-" * 60)

# ------------------------------------------------------------------
# 1. Datei -> Indikator-Code Mapping
# ------------------------------------------------------------------
file_map = {
    "number_of_political_violence_events_by_country-year_as-of-03Jul2026.xlsx": ("ACLED:political_violence_events", "EVENTS"),
    "number_of_reported_fatalities_by_country-year_as-of-03Jul2026.xlsx": ("ACLED:fatalities", "FATALITIES"),
    "number_of_demonstration_events_by_country-year_as-of-03Jul2026.xlsx": ("ACLED:demonstration_events", "EVENTS"),
    "number_of_events_targeting_civilians_by_country-year_as-of-03Jul2026.xlsx": ("ACLED:civilian_targeting_events", "EVENTS"),
    "number_of_reported_civilian_fatalities_by_country-year_as-of-03Jul2026.xlsx": ("ACLED:civilian_fatalities", "FATALITIES"),
}

cc = coco.CountryConverter()
total_saved = 0
total_skipped = 0
total_no_match = 0

for filename, (indicator_code, value_col) in file_map.items():
    print(f"Lade {indicator_code}...")
    df = pd.read_excel(f"{DATA_DIR}/{filename}", engine='calamine')

    # Länder-Mapping einmal pro Datei aufbauen (Name -> ISO3)
    countries = df['COUNTRY'].unique().tolist()
    name_to_iso3 = dict(zip(
        countries,
        cc.convert(names=countries, src='regex', to='ISO3', not_found=None)
    ))

    indicator_count = 0
    for _, row in df.iterrows():
        iso3 = name_to_iso3.get(row['COUNTRY'])
        if not iso3:
            total_no_match += 1
            continue

        # Pro-Zeile-Lookup wie im etablierten Pattern (robuster als Dict-Vorabbau)
        cur.execute(
            "SELECT iso_numeric FROM countries WHERE iso_code_3 = %s",
            (iso3,)
        )
        result = cur.fetchone()

        if result:
            iso_numeric = result[0]
            value = row[value_col]
            if pd.isna(value):
                continue

            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                DO UPDATE SET value = EXCLUDED.value
            """, (iso_numeric, indicator_code, SOURCE_ID, float(value), str(row['YEAR']), "A"))

            if cur.rowcount > 0:
                indicator_count += 1
                total_saved += 1
        else:
            total_no_match += 1

    conn.commit()
    print(f"  → {indicator_count} Datenpunkte geladen")

cur.close()
conn.close()

print("-" * 60)
print("Fertig!")
print(f"  Gesamt gespeichert: {total_saved}")
print(f"  Kein ISO-Match:     {total_no_match}")
