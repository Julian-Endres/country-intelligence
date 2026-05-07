import requests
import psycopg2

import os
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

# World Bank API - BIP pro Kopf
url = "https://api.worldbank.org/v2/country/BOL;DEU;COL;KOR;GBR/indicator/NY.GDP.PCAP.CD?format=json&mrv=1"

response = requests.get(url)
data = response.json()

# Daten extrahieren und speichern
for entry in data[1]:
    iso_code = entry['countryiso3code']
    gdp = entry['value']
    year = entry['date']
    
    if iso_code and gdp:
        cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
        result = cur.fetchone()
        
        if result:
            iso_numeric = result[0]
            cur.execute("""
                INSERT INTO indicators (iso_numeric, indicator_code, value, year)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (iso_numeric, indicator_code, year) DO NOTHING
            """, (iso_numeric, 'NY.GDP.PCAP.CD', gdp, int(year)))
            print(f"Gespeichert: {iso_code} - {gdp}")
            
conn.commit()
cur.close()
conn.close()
print("Fertig!")