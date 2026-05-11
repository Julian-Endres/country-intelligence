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

# Alle Indikatoren holen - auch die bereits gecheckt wurden
cur.execute("""
    SELECT source_code FROM indicator_catalog 
    WHERE source = 'World Bank'
    AND latest_year IS NULL
    ORDER BY source_code
""")
indicators = [row[0] for row in cur.fetchall()]

print(f"Prüfe {len(indicators)} Indikatoren...")

for i, full_code in enumerate(indicators):
    wb_code = full_code[3:]
    
    try:
        url = f"https://api.worldbank.org/v2/country/all/indicator/{wb_code}?format=json&mrv=1&per_page=300"
        response = requests.get(url, timeout=30)
        data = response.json()

        if len(data) < 2 or not data[1]:
            continue

        coverage_total = 0
        coverage_recent = 0
        latest_year = 0

        for entry in data[1]:
            iso_code = entry.get('countryiso3code')
            value = entry.get('value')
            year = entry.get('date')

            if iso_code and value:
                cur.execute("SELECT 1 FROM countries WHERE iso_code_3 = %s", (iso_code,))
                if cur.fetchone():
                    coverage_total += 1
                    try:
                        year_int = int(year)
                        if year_int > latest_year:
                            latest_year = year_int
                        if year_int >= 2015:
                            coverage_recent += 1
                    except:
                        pass

        cur.execute("""
            UPDATE indicator_catalog 
            SET country_coverage = %s,
                latest_year = %s,
                coverage_recent = %s,
                last_checked = CURRENT_DATE
            WHERE source_code = %s
        """, (coverage_total, latest_year if latest_year > 0 else None, coverage_recent, full_code))

        if i % 50 == 0:
            conn.commit()
            print(f"[{i}/{len(indicators)}] {full_code}: {coverage_total} Länder, neuestes Jahr: {latest_year}")

        time.sleep(0.5)

    except Exception as e:
        print(f"Fehler bei {full_code}: {e}")
        continue

conn.commit()
cur.close()
conn.close()
print("Fertig!")