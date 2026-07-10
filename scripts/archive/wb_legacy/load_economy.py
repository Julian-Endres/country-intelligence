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

indicators = [
    # GDP & Growth
    "NY.GDP.MKTP.CD",
    "NY.GDP.MKTP.KD",
    "NY.GDP.MKTP.KD.ZG",
    "NY.GDP.PCAP.KD",
    "NY.GDP.PCAP.KD.ZG",
    "NY.GDP.PCAP.PP.CD",
    "NY.GDP.PCAP.PP.KD",
    "NY.GNP.MKTP.CD",
    "NY.GNP.PCAP.CD",
    # Inflation & Prices
    "NY.GDP.DEFL.KD.ZG",
    "FP.CPI.TOTL.ZG",
    "FP.CPI.TOTL",
    "PA.NUS.FCRF",
    # Trade
    "TG.VAL.TOTL.GD.ZS",
    "TM.VAL.MRCH.CD.WT",
    "TX.VAL.MRCH.CD.WT",
    "BX.KLT.DINV.CD.WD",
    "BN.CAB.XOKA.GD.ZS",
    "TX.QTY.MRCH.XD.WD",
    "TM.QTY.MRCH.XD.WD",
    # Investment & Capital
    "NE.GDI.TOTL.ZS",
    "NE.GDI.TOTL.CD",
    # Government & Military
    "MS.MIL.XPND.GD.ZS",
    "MS.MIL.XPND.CD",
    # Infrastructure
    "EG.ELC.ACCS.ZS",
    "EG.ELC.ACCS.UR.ZS",
    "EG.ELC.ACCS.RU.ZS",
    "EG.ELC.RNEW.ZS",
    "EG.ELC.RNWX.ZS",
    # Poverty & Inequality
    "SI.POV.NAHC",
    "SI.POV.DDAY",
    "SI.POV.GAPS",
    "SI.DST.FRST.20",
    "SI.DST.10TH.10",
    "NY.ADJ.AEDU.GN.ZS",
]

DATE_RANGE = "2000:2024"
total_saved = 0
total_skipped = 0

print(f"Lade {len(indicators)} Economy-Indikatoren ({DATE_RANGE})...")
print("-" * 60)

for i, indicator in enumerate(indicators):
    print(f"[{i+1}/{len(indicators)}] {indicator}...")
    page = 1
    indicator_count = 0

    while True:
        try:
            url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
                f"?format=json&date={DATE_RANGE}&per_page=1000&page={page}"
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
                cur.execute(
                    "SELECT iso_numeric FROM countries WHERE iso_code_3 = %s",
                    (iso_code,)
                )
                result = cur.fetchone()

                if result:
                    iso_numeric = result[0]
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                        DO NOTHING
                    """, (iso_numeric, f"WB:{indicator}", 1, value, str(year), "A"))

                    if cur.rowcount > 0:
                        indicator_count += 1
                        total_saved += 1
                    else:
                        total_skipped += 1

        total_pages = data[0].get("pages", 1)
        if page >= total_pages:
            break
        page += 1

    conn.commit()
    print(f"  → {indicator_count} neue Datenpunkte")
    time.sleep(0.5)

cur.close()
conn.close()

print("-" * 60)
print(f"Fertig!")
print(f"  Neu gespeichert:  {total_saved}")
print(f"  Bereits vorhanden: {total_skipped}")
