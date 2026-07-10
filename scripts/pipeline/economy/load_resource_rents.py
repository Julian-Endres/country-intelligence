"""
Resource Rents Loader — für Economy Domain, Category "Energy & Resources"
Angepasst an aktuelles Pipeline-Pattern (Fehlerbehandlung, DATE_RANGE, Rate-Limiting).

Lädt 5 WB-Indikatoren, 2000-2024:
- NY.GDP.TOTL.RT.ZS  — Total natural resources rents (% GDP)
- NY.GDP.NGAS.RT.ZS  — Natural gas rents (% GDP)
- NY.GDP.PETR.RT.ZS  — Oil rents (% GDP)
- NY.GDP.MINR.RT.ZS  — Mineral rents (% GDP)
- TX.VAL.FUEL.ZS.UN  — Fuel exports (% of merchandise exports)

Ablage: scripts/pipeline/economy/load_resource_rents.py
"""

import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# ------------------------------------------------------------------
# 0. Metadata-Einträge anlegen
#    domain/category/dimension nach SIF v2:
#    04 Economy, Wealth & Labor -> Energy & Resources -> Resource Dependency
#    Falls dein FK-Setup das nicht braucht oder ein anderes Script
#    das übernimmt: diesen Block einfach löschen.
# ------------------------------------------------------------------
metadata = {
    "WB:NY.GDP.TOTL.RT.ZS": ("Total natural resources rents (% of GDP)", "%"),
    "WB:NY.GDP.NGAS.RT.ZS": ("Natural gas rents (% of GDP)", "%"),
    "WB:NY.GDP.PETR.RT.ZS": ("Oil rents (% of GDP)", "%"),
    "WB:NY.GDP.MINR.RT.ZS": ("Mineral rents (% of GDP)", "%"),
    "WB:TX.VAL.FUEL.ZS.UN": ("Fuel exports (% of merchandise exports)", "%"),
}

for code, (name, unit) in metadata.items():
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category, domain, dimension)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, unit, 1, "Energy & Resources",
          "Economy, Wealth & Labor", "Resource Dependency"))

conn.commit()
print("Metadata-Einträge geprüft/angelegt.")
print("-" * 60)

# ------------------------------------------------------------------
# 1. Indikatoren laden
# ------------------------------------------------------------------
indicators = [
    "NY.GDP.TOTL.RT.ZS",
    "NY.GDP.NGAS.RT.ZS",
    "NY.GDP.PETR.RT.ZS",
    "NY.GDP.MINR.RT.ZS",
    "TX.VAL.FUEL.ZS.UN",
]

DATE_RANGE = "2000:2024"
total_saved = 0
total_skipped = 0

print(f"Lade {len(indicators)} Resource-Rents-Indikatoren ({DATE_RANGE})...")
print("-" * 60)

for i, indicator in enumerate(indicators):
    print(f"[{i+1}/{len(indicators)}] {indicator}...")
    page = 1
    indicator_count = 0

    while True:
        try:
            url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
                f"?format=json&date={DATE_RANGE}&per_page=1000&page={page}"
            )
            response = requests.get(url, timeout=30)
            if response.status_code != 200 or not response.text:
                print(f"  Leere Antwort Seite {page}, überspringe...")
                break
            data = response.json()
        except Exception as e:
            print(f"  Fehler: {e}")
            break

        if len(data) < 2 or not data[1]:
            break

        for entry in data[1]:
            iso_code = entry.get("countryiso3code")
            value = entry.get("value")
            year = entry.get("date")

            if iso_code and value is not None:
                cur.execute(
                    "SELECT iso_numeric FROM countries WHERE iso_code_3 = %s",
                    (iso_code,)
                )
                result = cur.fetchone()

                if result:
                    iso_numeric = result[0]
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                        DO NOTHING
                    """, (iso_numeric, f"WB:{indicator}", 1, value, str(year), "A"))
                    if cur.rowcount > 0:
                        indicator_count += 1
                        total_saved += 1
                    else:
                        total_skipped += 1

        total_pages = data[0].get("pages", 1)
        if page >= total_pages:
            break
        page += 1

    conn.commit()
    print(f"  → {indicator_count} neue Datenpunkte")
    time.sleep(0.5)

cur.close()
conn.close()

print("-" * 60)
print("Fertig!")
print(f"  Neu gespeichert:   {total_saved}")
print(f"  Bereits vorhanden: {total_skipped}")

# ------------------------------------------------------------------
# 2. Quick-Check danach (in DBeaver/psql):
#
# SELECT time_period,
#     ROUND(MAX(CASE WHEN indicator_code='WB:NY.GDP.NGAS.RT.ZS' THEN value END)::numeric,2) AS gas_rents,
#     ROUND(MAX(CASE WHEN indicator_code='WB:NY.GDP.TOTL.RT.ZS' THEN value END)::numeric,2) AS total_rents,
#     ROUND(MAX(CASE WHEN indicator_code='WB:TX.VAL.FUEL.ZS.UN' THEN value END)::numeric,2) AS fuel_exports_pct
# FROM indicators
# WHERE indicator_code IN ('WB:NY.GDP.NGAS.RT.ZS','WB:NY.GDP.TOTL.RT.ZS','WB:TX.VAL.FUEL.ZS.UN')
# AND iso_numeric = '068'
# AND time_period ~ '^\d{4}$'
# GROUP BY time_period ORDER BY time_period;
# ------------------------------------------------------------------
