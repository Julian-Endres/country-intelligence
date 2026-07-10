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
    # Disease
    "SH.STA.DIAB.ZS",
    "SH.TBS.INCD",
    "SH.TBS.DTEC.ZS",
    "SH.TBS.CURE.ZS",
    "SH.DYN.NCOM.ZS",
    "SH.DYN.NCOM.FE.ZS",
    "SH.DYN.NCOM.MA.ZS",
    "SH.MLR.INCD.P3",
    # HIV/AIDS
    "SH.DYN.AIDS.ZS",
    "SH.DYN.AIDS.FE.ZS",
    "SH.HIV.1524.FE.ZS",
    "SH.HIV.1524.MA.ZS",
    "SH.HIV.INCD.ZS",
    "SH.HIV.ARTC.ZS",
    # Nutrition
    "SH.ANM.ALLW.ZS",
    "SH.ANM.NPRG.ZS",
    "SH.ANM.CHLD.ZS",
    "SH.PRG.ANEM",
    "SH.STA.STNT.ME.ZS",
    "SH.STA.STNT.ME.FE.ZS",
    "SH.STA.STNT.ME.MA.ZS",
    "SH.STA.OWGH.ME.ZS",
    "SH.STA.OWGH.ME.FE.ZS",
    "SH.STA.OWGH.ME.MA.ZS",
    # WASH
    "SH.H2O.BASW.ZS",
    "SH.H2O.BASW.RU.ZS",
    "SH.H2O.BASW.UR.ZS",
    "SH.H2O.SMDW.ZS",
    "SH.STA.BASS.ZS",
    "SH.STA.BASS.RU.ZS",
    "SH.STA.BASS.UR.ZS",
    "SH.STA.SMSS.ZS",
    "SH.STA.WASH.P5",
    # Immunization
    "SH.IMM.IDPT",
    "SH.IMM.MEAS",
    "SH.IMM.HEPB",
    # Healthcare system
    "SH.MED.BEDS.ZS",
    "SH.MED.PHYS.ZS",
    "SH.MED.NUMW.P3",
    "SH.XPD.CHEX.GD.ZS",
    "SH.XPD.CHEX.PC.CD",
]

DATE_RANGE = "2000:2024"
total_saved = 0
total_skipped = 0

print(f"Lade {len(indicators)} Health-Indikatoren ({DATE_RANGE})...")
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
