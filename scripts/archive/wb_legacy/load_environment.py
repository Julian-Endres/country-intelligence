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

indicators = [
    # Land use
    "AG.LND.TOTL.K2",
    "AG.LND.FRST.ZS",
    "AG.LND.FRST.K2",
    "AG.LND.AGRI.ZS",
    "AG.LND.ARBL.ZS",
    "AG.LND.CROP.ZS",
    # Protected areas
    "ER.LND.PTLD.ZS",
    "ER.PTD.TOTL.ZS",
    # Emissions
    "EN.GHG.ALL.MT.CE.AR5",
    "EN.GHG.ALL.PC.CE.AR5",
    "EN.GHG.TOT.ZG.AR5",
    "EN.GHG.CO2.MT.CE.AR5",
    "EN.GHG.CO2.PC.CE.AR5",
    "EN.GHG.CO2.ZG.AR5",
    "EN.GHG.CH4.MT.CE.AR5",
    "EN.GHG.N2O.MT.CE.AR5",
    # Air quality
    "EN.ATM.PM25.MC.M3",
    "EN.ATM.PM25.MC.ZS",
    # Adjusted savings
    "NY.ADJ.DCO2.CD",
]

DATE_RANGE = "2000:2024"
total_saved = 0
total_skipped = 0

print(f"Lade {len(indicators)} Environment-Indikatoren ({DATE_RANGE})...")
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
print(f"Fertig!")
print(f"  Neu gespeichert:  {total_saved}")
print(f"  Bereits vorhanden: {total_skipped}")
