import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

indicators = [
    # Male/Female total
    "SP.POP.TOTL.FE.IN",
    "SP.POP.TOTL.MA.IN",
    "SP.POP.TOTL.MA.ZS",

    # Dependency ratio aufgeschlüsselt
    "SP.POP.DPND.OL",
    "SP.POP.DPND.YG",

    # Breite Brackets absolut male/female
    "SP.POP.0014.FE.IN",
    "SP.POP.0014.MA.IN",
    "SP.POP.1564.FE.IN",
    "SP.POP.1564.MA.IN",
    "SP.POP.65UP.FE.IN",
    "SP.POP.65UP.MA.IN",

    # Breite Brackets % male/female
    "SP.POP.0014.FE.ZS",
    "SP.POP.0014.MA.ZS",
    "SP.POP.1564.FE.ZS",
    "SP.POP.1564.MA.ZS",
    "SP.POP.65UP.FE.ZS",
    "SP.POP.65UP.MA.ZS",

    # 5-Jahres-Schritte % female
    "SP.POP.0004.FE.5Y",
    "SP.POP.0509.FE.5Y",
    "SP.POP.1014.FE.5Y",
    "SP.POP.1519.FE.5Y",
    "SP.POP.2024.FE.5Y",
    "SP.POP.2529.FE.5Y",
    "SP.POP.3034.FE.5Y",
    "SP.POP.3539.FE.5Y",
    "SP.POP.4044.FE.5Y",
    "SP.POP.4549.FE.5Y",
    "SP.POP.5054.FE.5Y",
    "SP.POP.5559.FE.5Y",
    "SP.POP.6064.FE.5Y",
    "SP.POP.6569.FE.5Y",
    "SP.POP.7074.FE.5Y",
    "SP.POP.7579.FE.5Y",
    "SP.POP.80UP.FE.5Y",

    # 5-Jahres-Schritte % male
    "SP.POP.0004.MA.5Y",
    "SP.POP.0509.MA.5Y",
    "SP.POP.1014.MA.5Y",
    "SP.POP.1519.MA.5Y",
    "SP.POP.2024.MA.5Y",
    "SP.POP.2529.MA.5Y",
    "SP.POP.3034.MA.5Y",
    "SP.POP.3539.MA.5Y",
    "SP.POP.4044.MA.5Y",
    "SP.POP.4549.MA.5Y",
    "SP.POP.5054.MA.5Y",
    "SP.POP.5559.MA.5Y",
    "SP.POP.6064.MA.5Y",
    "SP.POP.6569.MA.5Y",
    "SP.POP.7074.MA.5Y",
    "SP.POP.7579.MA.5Y",
    "SP.POP.80UP.MA.5Y",

    # Extras
    "SP.POP.BRTH.MF",
    "SP.ADO.TFRT",

    # Refugees
    "SM.POP.RHCR.EA",
    "SM.POP.RHCR.EO",
]

DATE_RANGE = "2000:2024"
total_saved = 0
total_skipped = 0

print(f"Lade {len(indicators)} Indikatoren ({DATE_RANGE})...")
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
print(f"  Neu gespeichert: {total_saved}")
print(f"  Bereits vorhanden (skipped): {total_skipped}")