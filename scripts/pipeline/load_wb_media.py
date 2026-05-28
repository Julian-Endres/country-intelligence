import requests
import psycopg2
import os
import time
from dotenv import load_dotenv

load_dotenv()

DATE_RANGE = "2000:2024"

indicators = [
    ('WB:IT.CEL.SETS.P2', 'Mobile cellular subscriptions (per 100 people)',  'Communication & Media', 'Digital Access', 'Internet & ICT', 'per 100'),
    ('WB:IT.NET.BBND.P2', 'Fixed broadband subscriptions (per 100 people)',   'Communication & Media', 'Digital Access', 'Internet & ICT', 'per 100'),
]

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

cur.execute("SELECT id FROM sources WHERE short_code = 'WB'")
source_id = cur.fetchone()[0]

for code, name, domain, category, dimension, unit in indicators:
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, source_id, domain, category, dimension, unit)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO UPDATE SET
            domain = EXCLUDED.domain, category = EXCLUDED.category, dimension = EXCLUDED.dimension
    """, (code, name, source_id, domain, category, dimension, unit))

conn.commit()
print("Metadata geladen.")

cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
country_map = {row[1]: row[0] for row in cur.fetchall()}

total_saved = 0
total_skipped = 0

print(f"Lade Communication & Media Indikatoren ({DATE_RANGE})...")
print("-" * 60)

for code, name, domain, category, dimension, unit in indicators:
    wb_code = code[3:]
    print(f"{wb_code}...")
    saved = 0
    skipped = 0
    page = 1

    while True:
        try:
            url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{wb_code}"
                f"?format=json&date={DATE_RANGE}&per_page=1000&page={page}"
            )
            r = requests.get(url, timeout=30)
            if r.status_code != 200 or not r.text:
                break
            data = r.json()
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
                    """, (result[0], code, source_id, value, str(year)))
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
    total_saved += saved
    total_skipped += skipped
    print(f"  → {saved} neu, {skipped} bereits vorhanden")
    time.sleep(0.5)

cur.close()
conn.close()
print("-" * 60)
print(f"Fertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")
