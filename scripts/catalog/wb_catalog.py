import requests
import psycopg2
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Alle WDI Indikatoren laden (source=2 = World Development Indicators)
print("Lade World Bank Indicator Catalog...")
page = 1
total_saved = 0

while True:
    url = f"https://api.worldbank.org/v2/indicator?format=json&source=2&per_page=300&page={page}"
    response = requests.get(url)
    data = response.json()

    if len(data) < 2 or not data[1]:
        break

    for indicator in data[1]:
        code = indicator.get('id')
        name = indicator.get('name')
        description = indicator.get('sourceNote', '')
        unit = indicator.get('unit', '')
        category = indicator.get('topics', [{}])[0].get('value', '') if indicator.get('topics') else ''

        if code and name:
            cur.execute("""
                INSERT INTO indicator_catalog 
                (source_code, name, description, unit, source, category, last_checked)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    unit = EXCLUDED.unit,
                    category = EXCLUDED.category,
                    last_checked = EXCLUDED.last_checked
            """, (f"WB:{code}", name, description, unit, 'World Bank', category, date.today()))
            total_saved += 1

    total_pages = data[0]['pages']
    print(f"Seite {page}/{total_pages}")
    if page >= total_pages:
        break
    page += 1

conn.commit()
cur.close()
conn.close()
print(f"\nFertig! {total_saved} Indikatoren gespeichert.")