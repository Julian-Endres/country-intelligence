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

url = "https://restcountries.com/v3.1/all?fields=name,ccn3,cca3,cca2,subregion,capital,area,landlocked,latlng,flags"
response = requests.get(url)
data = response.json()

count = 0

for country in data:
    try:
        name = country.get('name', {}).get('common', None)
        iso_numeric = country.get('ccn3', None)
        iso_code_3 = country.get('cca3', None)
        iso_code_2 = country.get('cca2', None)
        region = None
        subregion = country.get('subregion', None)
        capital = country.get('capital', [None])[0] if country.get('capital') else None
        area_km2 = country.get('area', None)
        is_landlocked = country.get('landlocked', False)
        is_island = False
        flag_url = country.get('flags', {}).get('png', None)
        
        latlng = country.get('latlng', [None, None])
        latitude = latlng[0] if len(latlng) > 0 else None
        longitude = latlng[1] if len(latlng) > 1 else None

        if name and iso_numeric and iso_code_3 and iso_code_2:
            cur.execute("""
                INSERT INTO countries 
                (iso_numeric, name, iso_code_3, iso_code_2, region, subregion,
                capital, latitude, longitude, area_km2, is_landlocked,
                is_island, flag_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (iso_numeric) DO NOTHING
            """, (iso_numeric, name, iso_code_3, iso_code_2, region, subregion,
                  capital, latitude, longitude, area_km2, is_landlocked,
                  is_island, flag_url))
            count += 1

    except Exception as e:
        print(f"Fehler: {e}")

conn.commit()
cur.close()
conn.close()
print(f"Fertig! {count} Länder gespeichert.")