"""
load_owid_energy.py — OWID Energy Dataset
==========================================
Source:  Our World in Data / GitHub
Original sources:
  - Ember (Yearly Electricity Data)
  - Energy Institute Statistical Review of World Energy
  - EIA International Energy Statistics

Run:
  python3 scripts/pipeline/environment/load_owid_energy.py
"""

import requests
import psycopg2
import os
import io
import time
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"

# (col, indicator_code, name, domain, category, dimension, unit, source_short)
INDICATORS = [
    # Geography & Environment — Strommix
    ("fossil_share_energy",    "EI:fossil_share_energy",    "Fossil fuels share of primary energy (%)",          "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EI"),
    ("renewables_share_energy","EMBER:renewables_share_energy","Renewables share of primary energy (%)",          "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EMBER"),
    ("solar_share_elec",       "EMBER:solar_share_elec",    "Solar share of electricity generation (%)",         "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EMBER"),
    ("wind_share_elec",        "EMBER:wind_share_elec",     "Wind share of electricity generation (%)",          "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EMBER"),
    ("hydro_share_elec",       "EMBER:hydro_share_elec",    "Hydropower share of electricity generation (%)",   "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EMBER"),
    ("nuclear_share_elec",     "EMBER:nuclear_share_elec",  "Nuclear share of electricity generation (%)",      "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EMBER"),
    ("coal_share_energy",      "EI:coal_share_energy",      "Coal share of primary energy (%)",                 "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EI"),
    ("gas_share_energy",       "EI:gas_share_energy",       "Gas share of primary energy (%)",                  "Geography & Environment", "Climate & Emissions", "Emissions & Climate", "%",    "EI"),
    # Economy & Infrastructure — Produktion & Verbrauch
    ("coal_production",        "EI:coal_production",        "Coal production (TWh)",                            "Economy & Infrastructure", "Economic Structure",  "Sectoral Composition","TWh",  "EI"),
    ("gas_production",         "EI:gas_production",         "Gas production (TWh)",                             "Economy & Infrastructure", "Economic Structure",  "Sectoral Composition","TWh",  "EI"),
    ("oil_production",         "EI:oil_production",         "Oil production (TWh)",                             "Economy & Infrastructure", "Economic Structure",  "Sectoral Composition","TWh",  "EI"),
    ("energy_per_capita",      "EIA:energy_per_capita",     "Primary energy consumption per capita (kWh)",      "Economy & Infrastructure", "Public Finance & Energy","Energy & Electricity","kWh","EIA"),
]

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# ─── Sources ─────────────────────────────────────────────────────────────────

sources_data = {
    "EMBER": ("Ember", "Ember – Yearly Electricity Data",
              "https://ember-climate.org/data/",
              "Global electricity generation data by source, updated annually."),
    "EI":    ("EI",   "Energy Institute – Statistical Review of World Energy",
              "https://www.energyinst.org/statistical-review/",
              "Annual global data on energy production, consumption, and trade by fuel type."),
    "EIA":   ("EIA",  "U.S. Energy Information Administration – International Energy Statistics",
              "https://www.eia.gov/international/data/world",
              "International energy statistics including consumption, production, and trade."),
}

source_ids = {}
for short, (code, name, url, desc) in sources_data.items():
    cur.execute("SELECT id FROM sources WHERE short_code = %s", (code,))
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO sources (short_code, name, url, description)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (code, name, url, desc))
        source_ids[short] = cur.fetchone()[0]
    else:
        source_ids[short] = row[0]

conn.commit()
print("Sources geladen.")

# ─── Metadata ────────────────────────────────────────────────────────────────

for col, code, name, domain, category, dimension, unit, src in INDICATORS:
    cur.execute("""
        INSERT INTO indicator_metadata
            (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            domain = EXCLUDED.domain,
            category = EXCLUDED.category,
            dimension = EXCLUDED.dimension
    """, (code, name, source_ids[src], domain, category, dimension, unit))

conn.commit()
print("Metadata geladen.")

# ─── Download CSV ────────────────────────────────────────────────────────────

print("Lade OWID Energy CSV...")
r = requests.get(OWID_URL, timeout=120,
                 headers={"User-Agent": "Our World In Data data fetch/1.0"})
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text))
print(f"  {len(df)} Zeilen, {len(df.columns)} Spalten")

# Nur echte Länder (iso_code vorhanden + 3 Zeichen)
df = df[df["iso_code"].notna() & (df["iso_code"].str.len() == 3)]
print(f"  {len(df)} Zeilen nach ISO-Filter")

# ─── Country mapping ─────────────────────────────────────────────────────────

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries WHERE iso_code_3 IS NOT NULL")
country_map = {row[1]: row[0] for row in cur.fetchall()}

# ─── Insert ──────────────────────────────────────────────────────────────────

total_saved = 0
total_skipped = 0

print(f"\nLade {len(INDICATORS)} Indikatoren...")
print("-" * 60)

for col, code, name, domain, category, dimension, unit, src in INDICATORS:
    source_id = source_ids[src]
    saved = 0
    skipped = 0

    subset = df[["iso_code", "year", col]].dropna(subset=[col])
    print(f"{code}: {len(subset)} Datenpunkte...")

    for _, row in subset.iterrows():
        iso3 = row["iso_code"]
        iso_numeric = country_map.get(iso3)
        if not iso_numeric:
            continue
        year = str(int(row["year"]))
        value = float(row[col])

        cur.execute("""
            INSERT INTO indicators
                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
            VALUES (%s, %s, %s, %s, %s, 'A')
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
            DO NOTHING
        """, (iso_numeric, code, source_id, value, year))

        if cur.rowcount > 0:
            saved += 1
        else:
            skipped += 1

    conn.commit()
    total_saved += saved
    total_skipped += skipped
    print(f"  → {saved} neu, {skipped} bereits vorhanden")
    time.sleep(0.1)

cur.close()
conn.close()
print("-" * 60)
print(f"Fertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")
