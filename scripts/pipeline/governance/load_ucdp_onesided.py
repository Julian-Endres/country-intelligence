"""
UCDP One-Sided Violence Loader — für Politics Domain, 
Category "Security & Conflict", Dimension "Armed Conflict"

Lädt gezielte Gewalt gegen Zivilisten durch Staat oder bewaffnete Gruppe.
Datei: data/raw/governance/UCDP/OneSided_v26_1.xlsx

Ablage: scripts/pipeline/governance/load_ucdp_onesided.py
"""

import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

DATA_DIR = "data/raw/governance/UCDP"

# --- Tabelle anlegen ---
cur.execute("""
CREATE TABLE IF NOT EXISTS conflicts_onesided (
    episode_id SERIAL PRIMARY KEY,
    conflict_id INT,
    dyad_id INT,
    country_iso VARCHAR(3),
    gwno_loc INT,
    year INT,
    actor_name TEXT,
    is_government_actor BOOLEAN,
    fatality_best INT,
    fatality_low INT,
    fatality_high INT,
    source VARCHAR(20) DEFAULT 'UCDP'
);
""")
conn.commit()
print("Tabelle angelegt.")

# --- GW-Code Mapping aus DB laden ---
cur.execute("SELECT gw_code, iso_code_3 FROM countries WHERE gw_code IS NOT NULL")
gw_to_iso = {row[0]: row[1] for row in cur.fetchall()}

def clean_int(val):
    if pd.isna(val):
        return None
    return int(val)

# --- Datei laden ---
df = pd.read_excel(f"{DATA_DIR}/OneSided_v26_1.xlsx", engine='openpyxl')
print(f"{len(df)} Zeilen in Rohdaten")

inserted = 0
no_match = 0
for _, row in df.iterrows():
    gw = str(row['gwno_location']).split(',')[0].strip()
    iso3 = gw_to_iso.get(clean_int(gw))
    if not iso3:
        no_match += 1
        continue

    cur.execute("""
        SELECT iso_numeric FROM countries WHERE iso_code_3 = %s
    """, (iso3,))
    result = cur.fetchone()
    if not result:
        no_match += 1
        continue

    cur.execute("""
        INSERT INTO conflicts_onesided
        (conflict_id, dyad_id, country_iso, gwno_loc, year, actor_name,
         is_government_actor, fatality_best, fatality_low, fatality_high)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        clean_int(row['conflict_id']), clean_int(row['dyad_id']),
        iso3, clean_int(gw), clean_int(row['year']),
        row['actor_name'], bool(row['is_government_actor']),
        clean_int(row['best_fatality_estimate']),
        clean_int(row['low_fatality_estimate']),
        clean_int(row['high_fatality_estimate'])
    ))
    inserted += 1

conn.commit()
print(f"{inserted} Zeilen geladen, {no_match} ohne Match")

# --- Ins richtige Schema verschieben ---
cur.execute("ALTER TABLE conflicts_onesided SET SCHEMA politics;")
conn.commit()
print("Tabelle nach politics-Schema verschoben.")

# --- Metadaten-Eintrag ---
cur.execute("""
    INSERT INTO relational_table_metadata 
    (table_name, schema_name, description, domain, category, dimension, data_type)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (table_name) DO NOTHING
""", (
    'conflicts_onesided', 'politics',
    'Gezielte Gewalt gegen Zivilisten durch Staat oder bewaffnete Gruppe, 1989-2025 (UCDP One-Sided Violence)',
    'Politics, Governance & Law', 'Security & Conflict', 'Armed Conflict', 'event-based'
))
conn.commit()
print("Metadaten-Eintrag angelegt.")

cur.close()
conn.close()
print("Fertig!")
