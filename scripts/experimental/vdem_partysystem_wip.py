"""
VDEM Nachladung — Party System Variablen
Für Politics Domain, Category "Democracy & Elections",
Sub-Category "Party Systems" (Struktur-Kennzahlen, Ergänzung zu V-Party-Ersatz)

Lädt 4 zusätzliche VDEM-Variablen, die im ursprünglichen load_vdem.py
(nur v2x_ Präfix) nicht erfasst wurden:
- v2xps_party    — Party System Institutionalization Index
- v2cacpol       — Political Polarization (Achtung: echter Variablenname
                    ist v2cacamps oder v2cacpol, nicht v2cacpols — vor dem
                    Laden gegen Header prüfen!)
- v2psbars       — Barriers to Party Registration
- v2psparban_ord — Party ban (ordinal Variante, da v2psparban selbst evtl.
                    C-Klasse-Rohvariable ist)

WICHTIG: Vor dem Ausführen die exakten Spaltennamen im VDEM-CSV-Header
prüfen (siehe Schritt 0 unten) — Variablennamen in Sekundärquellen
sind nicht immer exakt.

Ablage: scripts/pipeline/governance/load_vdem_partysystem.py
"""

import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

VDEM_FILE = '/home/julian/projects/country-intelligence/data/raw/governance/V-Dem-CY-Full+Others-v16.csv'

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# --- Schritt 0: Header prüfen, welche Kandidaten-Spalten wirklich existieren ---
df_header = pd.read_csv(VDEM_FILE, nrows=0)
all_cols = df_header.columns.tolist()

candidates = ['v2xps_party', 'v2cacpol', 'v2cacamps', 'v2cacpols',
              'v2psbars', 'v2psparban', 'v2psparban_ord']

found = [c for c in candidates if c in all_cols]
missing = [c for c in candidates if c not in all_cols]

print("Gefundene Spalten:", found)
print("NICHT gefundene Spalten (Namen ggf. falsch):", missing)
print("-" * 60)

if not found:
    print("Keine der Kandidaten-Spalten gefunden. Skript abgebrochen.")
    print("Bitte Header manuell durchsuchen, z.B.:")
    print("  [c for c in all_cols if 'party' in c.lower() or 'polar' in c.lower()]")
    exit()

key_indicators = found

# --- Source ---
cur.execute("SELECT id FROM sources WHERE short_code = 'VDEM'")
source_id = cur.fetchone()[0]

# --- Metadata anlegen (analog zum Originalskript-Muster) ---
metadata_info = {
    'v2xps_party': ("Party System Institutionalization Index", "Party Systems"),
    'v2cacpol': ("Political Polarization", "Party Systems"),
    'v2cacamps': ("Societal/Political Polarization (Camps)", "Party Systems"),
    'v2cacpols': ("Political Polarization", "Party Systems"),
    'v2psbars': ("Barriers to Party Registration", "Party Systems"),
    'v2psparban': ("Party Ban", "Party Systems"),
    'v2psparban_ord': ("Party Ban (ordinal)", "Party Systems"),
}

for code in key_indicators:
    full_code = f"VDEM:{code}"
    name, dimension = metadata_info.get(code, (code, "Party Systems"))
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, category, domain, dimension)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (full_code, name, source_id, 'Democracy & Elections',
          'Politics, Governance & Law', dimension))

conn.commit()
print("Metadata angelegt.")

# --- Ländercodes ---
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
country_map = {row[1]: row[0] for row in cur.fetchall()}

# --- Daten laden ---
print("Lade V-Dem CSV (nur benötigte Spalten)...")
df = pd.read_csv(
    VDEM_FILE,
    usecols=['country_text_id', 'year'] + key_indicators,
    low_memory=False
)

df = df[df['year'] >= 1900]
df = df[df['country_text_id'].isin(country_map.keys())]

print(f"Zeilen zu verarbeiten: {len(df)}")

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
