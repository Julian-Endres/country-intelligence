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

# Kernindikatoren für historische Analyse
indicators = [
    "SP.URB.TOTL", "SP.POP.TOTL", "SP.URB.GROW", "SP.POP.GROW",
    "EN.POP.DNST", "SP.DYN.CBRT.IN", "SP.DYN.CDRT.IN", "SP.URB.TOTL.IN.ZS",
    "SP.POP.1564.TO.ZS", "SP.POP.0014.TO.ZS", "SP.POP.DPND", "SP.POP.65UP.TO",
    "SP.POP.65UP.TO.ZS", "SP.DYN.TFRT.IN", "SP.DYN.LE00.FE.IN", "SP.POP.TOTL.FE.ZS",
    "SP.DYN.LE00.MA.IN", "SP.DYN.LE00.IN", "SM.POP.TOTL", "SM.POP.NETM",
    "SM.POP.TOTL.ZS", "SP.RUR.TOTL.ZG", "SP.RUR.TOTL", "SP.RUR.TOTL.ZS",
    "SH.DYN.MORT", "SP.DYN.IMRT.IN", "SH.STA.MMRT", "NY.GDP.PCAP.CD",
    "SH.STA.SUIC.P5", "SH.ALC.PCAP.FE.LI", "SL.UEM.TOTL.MA.ZS",
    "SL.UEM.TOTL.FE.ZS", "SL.TLF.CACT.ZS", "SH.ALC.PCAP.MA.LI",
]

# Zeitraum
DATE_RANGE = "2000:2024"

total_saved = 0

for indicator in indicators:
    print(f"Lade {indicator} ({DATE_RANGE})...")
    page = 1

    while True:
        try:
            url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&date={DATE_RANGE}&per_page=1000&page={page}"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200 or not response.text:
                print(f"  Leere Antwort bei Seite {page}, überspringe...")
                break
                
            data = response.json()
        except Exception as e:
            print(f"  Fehler bei {indicator} Seite {page}: {e}")
            break

        if len(data) < 2 or not data[1]:
            break

        for entry in data[1]:
            iso_code = entry['countryiso3code']
            value = entry['value']
            year = entry['date']

            if iso_code and value:
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
                result = cur.fetchone()

                if result:
                    iso_numeric = result[0]
                    cur.execute("""
                        INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, f"WB:{indicator}", 1, value, str(year), 'A'))
                    total_saved += 1

        total_pages = data[0]['pages']
        if page >= total_pages:
            break
        page += 1
        
    import time
    time.sleep(0.5)

    conn.commit()
    print(f"{indicator} fertig.")

cur.close()
conn.close()
print(f"\nFertig! {total_saved} historische Datenpunkte gespeichert.")