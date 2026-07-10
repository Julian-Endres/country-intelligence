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

DATE_RANGE = "2000:2024"
total_saved = 0

def load_indicator(indicator, source_num=2, per_page=500):
    saved = 0
    page = 1
    while True:
        try:
            url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
                f"?format=json&date={DATE_RANGE}&per_page={per_page}&page={page}&source={source_num}"
            )
            response = requests.get(url, timeout=60)
            if response.status_code != 200 or not response.text:
                print(f"  Leere Antwort Seite {page}")
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
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
                result = cur.fetchone()
                if result:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                        DO NOTHING
                    """, (result[0], f"WB:{indicator}", 1, value, str(year), "A"))
                    if cur.rowcount > 0:
                        saved += 1

        total_pages = data[0].get("pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.3)

    conn.commit()
    return saved

# ── WGI (source=3, per_page=200) ──────────────────────────────────────────────
print("=== WGI Governance Indicators (source=3) ===")
wgi = [
    "RL.EST", "RL.PER.RNK",
    "GE.EST", "GE.PER.RNK",
    "RQ.EST", "RQ.PER.RNK",
    "CC.EST", "CC.PER.RNK",
    "VA.EST", "VA.PER.RNK",
    "PV.EST", "PV.PER.RNK",
]
for i, ind in enumerate(wgi):
    print(f"[{i+1}/{len(wgi)}] {ind}...")
    n = load_indicator(ind, source_num=3, per_page=200)
    print(f"  → {n} neue Datenpunkte")
    total_saved += n
    time.sleep(0.5)

# ── Timeouts & leere Seiten (source=2, per_page=500) ─────────────────────────
print("\n=== Timeout/Empty fixes (source=2) ===")
fixes = [
    "SH.STA.STNT.ME.MA.ZS",
    "SH.STA.BASS.UR.ZS",
    "TG.VAL.TOTL.GD.ZS",
    "ER.PTD.TOTL.ZS",
    "NV.IND.MANF.ZS",
    "DT.ODA.ALLD.CD",
    "SL.EMP.1524.SP.ZS",
    "SL.EMP.1524.SP.FE.ZS",
    "SL.UEM.1524.FE.ZS",
    "SL.UEM.1524.MA.ZS",
]
for i, ind in enumerate(fixes):
    print(f"[{i+1}/{len(fixes)}] {ind}...")
    n = load_indicator(ind, source_num=2, per_page=500)
    print(f"  → {n} neue Datenpunkte")
    total_saved += n
    time.sleep(0.5)

cur.close()
conn.close()
print(f"\nFertig! Gesamt neu gespeichert: {total_saved}")
