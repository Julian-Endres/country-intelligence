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

# Indikatoren die wir laden wollen
indicators = [
    # Demographie Kern
    "SP.POP.GROW",
    "SP.POP.TOTL.FE.ZS",
    "SP.DYN.TFRT.IN",
    "SP.DYN.CBRT.IN",
    "SP.DYN.CDRT.IN",
    "SP.POP.DPND",
    "EN.POP.DNST",
    "SP.DYN.LE00.FE.IN",
    "SP.DYN.LE00.MA.IN",
    # Mortalität
    "SP.DYN.IMRT.IN",
    "SH.DYN.MORT",
    "SH.STA.MMRT",
    "SH.STA.SUIC.P5",
    # Arbeit
    "SL.UEM.TOTL.MA.ZS",
    "SL.UEM.TOTL.FE.ZS",
    "SL.TLF.CACT.ZS",
    # Alkohol
    "SH.ALC.PCAP.MA.LI",
    "SH.ALC.PCAP.FE.LI",
]

total_saved = 0

for indicator in indicators:
    print(f"Lade {indicator}...")
    page = 1

    while True:
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}?format=json&mrv=1&per_page=300&page={page}"
        response = requests.get(url)
        data = response.json()

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

    conn.commit()
    print(f"{indicator} fertig.")

cur.close()
conn.close()
print(f"\nFertig! {total_saved} Datenpunkte gespeichert.")