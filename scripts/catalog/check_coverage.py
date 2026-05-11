import requests
import psycopg2
import os
import sys
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

# Code aus Terminal
if len(sys.argv) < 2:
    print("Verwendung: python3 check_coverage.py <indicator_code>")
    print("Beispiel:   python3 check_coverage.py WB:SE.PRM.TENR")
    sys.exit(1)

full_code = sys.argv[1]

# WB: Präfix entfernen für API Call
if full_code.startswith("WB:"):
    wb_code = full_code[3:]
else:
    wb_code = full_code

print(f"\n🔍 Prüfe Abdeckung für: {full_code}")

# World Bank API abfragen
url = f"https://api.worldbank.org/v2/country/all/indicator/{wb_code}?format=json&mrv=1&per_page=300"
response = requests.get(url)
data = response.json()

if len(data) < 2 or not data[1]:
    print("Keine Daten gefunden.")
    sys.exit(1)

# Nur echte Länder zählen (die in unserer countries Tabelle sind)
real_countries = 0
total_entries = 0

for entry in data[1]:
    iso_code = entry.get('countryiso3code')
    value = entry.get('value')
    
    if iso_code and value:
        cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
        result = cur.fetchone()
        if result:
            real_countries += 1
        total_entries += 1

# Coverage in Datenbank updaten
cur.execute("""
    UPDATE indicator_catalog 
    SET country_coverage = %s
    WHERE source_code = %s
""", (real_countries, full_code))

conn.commit()

# Ergebnis anzeigen
print(f"✅ Echte Länder mit Daten: {real_countries}/249")
print(f"📊 Abdeckung: {round(real_countries/249*100, 1)}%")

# Indikator Info aus Datenbank
cur.execute("SELECT name, category, description FROM indicator_catalog WHERE source_code = %s", (full_code,))
info = cur.fetchone()
if info:
    print(f"\n📋 Name: {info[0]}")
    print(f"📁 Kategorie: {info[1]}")
    print(f"📝 Beschreibung: {info[2][:200]}..." if info[2] else "")

cur.close()
conn.close()