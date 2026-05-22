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

BASE_URL = "https://ghoapi.azureedge.net/api"

# Alle gültigen Ländercodes einmal laden
cur.execute("SELECT iso_code_3 FROM countries")
valid_countries = {row[0] for row in cur.fetchall()}
print(f"Bekannte Länder: {len(valid_countries)}")

# Alle WHO Indikatoren ohne Coverage holen
cur.execute("""
    SELECT source_code FROM indicator_catalog
    WHERE source_code LIKE 'WHO:%'
    AND country_coverage IS NULL
    ORDER BY source_code
""")
indicators = [row[0] for row in cur.fetchall()]
print(f"Prüfe {len(indicators)} WHO Indikatoren...")

def fetch_all_data(who_code):
    """Holt alle Daten mit Pagination ($skip)"""
    all_data = []
    skip = 0
    page_size = 1000

    while True:
        url = (
            f"{BASE_URL}/{who_code}"
            f"?$select=SpatialDim,TimeDim,NumericValue"
            f"&$top={page_size}&$skip={skip}"
        )
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                break
            batch = r.json().get("value", [])
            if not batch:
                break
            all_data.extend(batch)
            if len(batch) < page_size:
                break  # Letzte Seite
            skip += page_size
            time.sleep(0.1)
        except Exception as e:
            break

    return all_data

for i, full_code in enumerate(indicators):
    who_code = full_code[4:]  # WHO: prefix entfernen

    try:
        data = fetch_all_data(who_code)

        if not data:
            cur.execute("""
                UPDATE indicator_catalog
                SET country_coverage = 0, coverage_recent = 0,
                    last_checked = CURRENT_DATE
                WHERE source_code = %s
            """, (full_code,))
            continue

        countries = set()
        recent_countries = set()
        latest_year = 0

        for entry in data:
            spatial = entry.get("SpatialDim", "")
            year = entry.get("TimeDim")
            value = entry.get("NumericValue")

            if spatial and len(spatial) == 3 and spatial in valid_countries and value is not None:
                countries.add(spatial)
                try:
                    y = int(year)
                    if y > latest_year:
                        latest_year = y
                    if y >= 2015:
                        recent_countries.add(spatial)
                except:
                    pass

        cur.execute("""
            UPDATE indicator_catalog
            SET country_coverage = %s,
                coverage_recent = %s,
                latest_year = %s,
                last_checked = CURRENT_DATE
            WHERE source_code = %s
        """, (
            len(countries),
            len(recent_countries),
            latest_year if latest_year > 0 else None,
            full_code
        ))

        if i % 25 == 0:
            conn.commit()
            print(f"[{i}/{len(indicators)}] {full_code}: {len(countries)} Länder, {len(data)} Datenpunkte")

        time.sleep(0.2)

    except Exception as e:
        print(f"Fehler bei {full_code}: {e}")
        continue

conn.commit()
cur.close()
conn.close()
print("\nFertig!")
