import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"
DATE_RANGE = "2000:2024"

# (indicator_code, name, domain, category, dimension, unit)
indicators = [
    # Logistics Performance Index (alle 2 Jahre)
    ('WB:LP.LPI.OVRL.XQ',    'Logistics Performance Index (overall)',              'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'score 1-5'),
    ('WB:LP.LPI.INFR.XQ',    'LPI: Quality of trade and transport infrastructure', 'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'score 1-5'),

    # Air transport
    ('WB:IS.AIR.PSGR',       'Air transport, passengers carried',                  'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'passengers'),
    ('WB:IS.AIR.GOOD.MT.K1', 'Air transport, freight (million ton-km)',             'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'million ton-km'),

    # Land transport
    ('WB:IS.RRS.TOTL.KM',    'Railway lines, total route (km)',                    'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'km'),
    ('WB:IS.ROD.TOTL.KM',    'Roads, total network (km)',                          'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'km'),

    # Ports
    ('WB:IS.SHP.GCNW.XQ',    'Container port traffic (TEU)',                       'Economy & Infrastructure', 'Public Finance & Energy', 'Infrastructure', 'TEU'),
]

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Source
cur.execute("SELECT id FROM sources WHERE short_code = 'WB'")
source_id = cur.fetchone()[0]

# Metadata
for code, name, domain, category, dimension, unit in indicators:
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            category  = EXCLUDED.category,
            dimension = EXCLUDED.dimension,
            domain    = EXCLUDED.domain
    """, (code, name, source_id, domain, category, dimension, unit))

conn.commit()
print("Metadata geladen.")

# Ländercodes
cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
country_map = {row[1]: row[0] for row in cur.fetchall()}

def load_wb_indicator(wb_code, date_range):
    saved = 0
    skipped = 0
    page = 1
    while True:
        try:
            url = (
                f"{BASE_URL}/{wb_code}"
                f"?format=json&date={date_range}&per_page=1000&page={page}"
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
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
                result = cur.fetchone()
                if result:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                        DO NOTHING
                    """, (result[0], f"WB:{wb_code}", source_id, value, str(year)))
                    if cur.rowcount > 0:
                        saved += 1
                    else:
                        skipped += 1

        total_pages = data[0].get("pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.1)

    conn.commit()
    return saved, skipped

total_saved = 0
total_skipped = 0

print(f"Lade Infrastructure Indikatoren ({DATE_RANGE})...")
print("-" * 60)
for i, (code, name, domain, category, dimension, unit) in enumerate(indicators):
    wb_code = code[3:]  # WB: prefix entfernen
    print(f"[{i+1}/{len(indicators)}] {wb_code}...")
    saved, skipped = load_wb_indicator(wb_code, DATE_RANGE)
    total_saved += saved
    total_skipped += skipped
    print(f"  → {saved} neu, {skipped} bereits vorhanden")
    time.sleep(0.5)

cur.close()
conn.close()
print("-" * 60)
print(f"Fertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")
