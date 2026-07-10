"""
UCDP GED Kontext-Erweiterung — Top-Schlagzeile pro Land-Jahr

Ergänzt die bestehende GED-Aggregation (aus load_ucdp_ged_aggregate.py)
um einen Kontext-Text: die Schlagzeile des schwersten Einzelereignisses
(höchste 'best' Fatality-Zahl) pro Land-Jahr. Löst das Problem, dass
UCDP:ged_deaths_total nur eine nackte Zahl ist, ohne zu erklären WAS
eigentlich passiert ist.

Beispiel: Bolivien 2000 -> "New clashes in longstanding Bolivian Indian
feud kill 29" statt nur "50 Tote".

Datei: data/raw/governance/UCDP/GEDEvent_v26_1.csv
Ablage: scripts/pipeline/governance/load_ucdp_ged_context.py
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

# --- Zusatztabelle anlegen ---
cur.execute("""
CREATE TABLE IF NOT EXISTS conflict_context (
    id SERIAL PRIMARY KEY,
    country_iso VARCHAR(3),
    year INT,
    top_headline TEXT,
    where_description TEXT,
    max_fatalities INT,
    UNIQUE(country_iso, year)
);
""")
conn.commit()
print("Tabelle conflict_context angelegt.")

# --- GED laden, nur benötigte Spalten ---
print("Lade GED (Kontext-Extraktion)...")
usecols = ['country_id', 'year', 'source_headline', 'where_description', 'best']

chunks = []
for chunk in pd.read_csv(f"{DATA_DIR}/GEDEvent_v26_1.csv", usecols=usecols, chunksize=50000):
    chunks.append(chunk)
df = pd.concat(chunks, ignore_index=True)
print(f"{len(df)} Rohereignisse geladen")

# Pro Land-Jahr: Zeile mit dem höchsten 'best'-Wert behalten
df = df.sort_values('best', ascending=False)
top_per_year = df.drop_duplicates(subset=['country_id', 'year'], keep='first')
print(f"{len(top_per_year)} Land-Jahr-Kombinationen mit Top-Ereignis")

# --- GW -> ISO Mapping ---
cur.execute("SELECT gw_code, iso_code_3 FROM countries WHERE gw_code IS NOT NULL")
gw_to_iso = {row[0]: row[1] for row in cur.fetchall()}

inserted = 0
no_match = 0
for _, row in top_per_year.iterrows():
    iso3 = gw_to_iso.get(int(row['country_id']))
    if not iso3:
        no_match += 1
        continue

    headline = row['source_headline'] if pd.notna(row['source_headline']) else None
    where_desc = row['where_description'] if pd.notna(row['where_description']) else None
    fatalities = int(row['best']) if pd.notna(row['best']) else None

    cur.execute("""
        INSERT INTO conflict_context (country_iso, year, top_headline, where_description, max_fatalities)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (country_iso, year) DO UPDATE SET
            top_headline = EXCLUDED.top_headline,
            where_description = EXCLUDED.where_description,
            max_fatalities = EXCLUDED.max_fatalities
    """, (iso3, int(row['year']), headline, where_desc, fatalities))
    inserted += 1

conn.commit()
print(f"{inserted} Kontext-Einträge geladen, {no_match} ohne Match")

# --- Ins richtige Schema verschieben ---
cur.execute("ALTER TABLE conflict_context SET SCHEMA politics;")
conn.commit()
print("Tabelle nach politics-Schema verschoben.")

# --- Metadaten-Eintrag ---
cur.execute("""
    INSERT INTO relational_table_metadata 
    (table_name, schema_name, description, domain, category, dimension, data_type)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (table_name) DO NOTHING
""", (
    'conflict_context', 'politics',
    'Kontext-Schlagzeile des schwersten Gewaltereignisses pro Land-Jahr, aus UCDP GED Rohdaten (Nachrichtenquellen-Metadaten)',
    'Politics, Governance & Law', 'Security & Conflict', 'Armed Conflict', 'reference'
))
conn.commit()
print("Metadaten-Eintrag angelegt.")

cur.close()
conn.close()
print("Fertig!")
