"""
UCDP GED Aggregation Loader — für Politics Domain,
Category "Security & Conflict", Dimension "Armed Conflict"

Aggregiert das granulare GED Event-Dataset (506k Einzelereignisse) zu
Country-Year Zeitreihen-Indikatoren. Die Rohdaten selbst werden NICHT
geladen (zu granular für Country-Encyclopedia), nur die Aggregate.

Datei: data/raw/governance/UCDP/GEDEvent_v26_1.csv
Ablage: scripts/pipeline/governance/load_ucdp_ged_aggregate.py
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
SOURCE_ID = None  # wird gleich nachgeschlagen/angelegt

# --- UCDP als Quelle sicherstellen ---
cur.execute("SELECT id FROM sources WHERE short_code = 'UCDP'")
result = cur.fetchone()
if result:
    SOURCE_ID = result[0]
else:
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, ('Uppsala Conflict Data Program', 'UCDP', 'https://ucdp.uu.se',
          'Globale Daten zu bewaffneten Konflikten, organisierter Gewalt und Friedensprozessen.'))
    SOURCE_ID = cur.fetchone()[0]
    conn.commit()
print(f"UCDP source_id = {SOURCE_ID}")

# --- Metadaten anlegen ---
metadata = {
    "UCDP:ged_deaths_total": ("Organized Violence Deaths (Total, GED)", "count",
        "Alle Todesfälle aus staatsbasierten, nicht-staatlichen und einseitigen Gewaltereignissen, aggregiert aus GED Einzelereignissen"),
    "UCDP:ged_deaths_civilians": ("Civilian Deaths from Organized Violence (GED)", "count",
        "Zivile Todesfälle aus allen Gewaltformen, aggregiert aus GED Einzelereignissen"),
    "UCDP:ged_events": ("Organized Violence Events (Count, GED)", "count",
        "Anzahl einzelner Gewaltereignisse pro Land-Jahr, aus GED"),
}

for code, (name, unit, desc) in metadata.items():
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, unit, description, source_id, category, domain, dimension)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, unit, desc, SOURCE_ID, "Security & Conflict",
          "Politics, Governance & Law", "Armed Conflict"))
conn.commit()
print("Metadaten angelegt.")

# --- GED laden und aggregieren (chunk-basiert wegen Größe) ---
print("Lade und aggregiere GED (kann etwas dauern)...")
usecols = ['country_id', 'year', 'deaths_a', 'deaths_b', 'deaths_civilians', 'deaths_unknown', 'best']

chunks = []
for chunk in pd.read_csv(f"{DATA_DIR}/GEDEvent_v26_1.csv", usecols=usecols, chunksize=50000):
    chunks.append(chunk)
df = pd.concat(chunks, ignore_index=True)
print(f"{len(df)} Rohereignisse geladen")

# country_id in GED = Gleditsch-Ward Code (wie gwno in anderen UCDP-Files)
agg = df.groupby(['country_id', 'year']).agg(
    deaths_total=('best', 'sum'),
    deaths_civilians=('deaths_civilians', 'sum'),
    n_events=('best', 'count')
).reset_index()

print(f"{len(agg)} Land-Jahr-Kombinationen nach Aggregation")

# --- GW -> ISO Mapping ---
cur.execute("SELECT gw_code, iso_code_3 FROM countries WHERE gw_code IS NOT NULL")
gw_to_iso = {row[0]: row[1] for row in cur.fetchall()}

inserted = 0
no_match = 0
for _, row in agg.iterrows():
    iso3 = gw_to_iso.get(int(row['country_id']))
    if not iso3:
        no_match += 1
        continue

    cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso3,))
    result = cur.fetchone()
    if not result:
        no_match += 1
        continue
    iso_numeric = result[0]
    year = str(int(row['year']))

    for code, val in [
        ("UCDP:ged_deaths_total", row['deaths_total']),
        ("UCDP:ged_deaths_civilians", row['deaths_civilians']),
        ("UCDP:ged_events", row['n_events']),
    ]:
        cur.execute("""
            INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
            DO UPDATE SET value = EXCLUDED.value
        """, (iso_numeric, code, SOURCE_ID, float(val), year, "A"))
        inserted += 1

conn.commit()
print(f"{inserted} Datenpunkte geladen, {no_match} Land-Jahr-Kombis ohne Match")

cur.close()
conn.close()
print("Fertig!")
