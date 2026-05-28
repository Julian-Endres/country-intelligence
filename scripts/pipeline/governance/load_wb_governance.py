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

# WGI — World Governance Indicators (source=75)
wgi_indicators = [
    "CC.EST",     # Control of Corruption: Estimate
    "CC.PER.RNK", # Control of Corruption: Percentile Rank
    "GE.EST",     # Government Effectiveness: Estimate
    "GE.PER.RNK", # Government Effectiveness: Percentile Rank
    "PV.EST",     # Political Stability: Estimate
    "PV.PER.RNK", # Political Stability: Percentile Rank
    "RL.EST",     # Rule of Law: Estimate
    "RL.PER.RNK", # Rule of Law: Percentile Rank
    "RQ.EST",     # Regulatory Quality: Estimate
    "RQ.PER.RNK", # Regulatory Quality: Percentile Rank
    "VA.EST",     # Voice and Accountability: Estimate
    "VA.PER.RNK", # Voice and Accountability: Percentile Rank
]

DATE_RANGE = "1996:2024"
total_saved = 0
total_skipped = 0

def load_wb_indicator(indicator, source_num, date_range):
    saved = 0
    skipped = 0
    page = 1
    while True:
        try:
            url = (
                f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
                f"?format=json&date={date_range}&per_page=1000&page={page}&source={source_num}"
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
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso_code,))
                result = cur.fetchone()
                if result:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period)
                        DO NOTHING
                    """, (result[0], f"WB:{indicator}", 1, value, str(year)))
                    if cur.rowcount > 0:
                        saved += 1
                    else:
                        skipped += 1

        total_pages = data[0].get("pages", 1)
        if page >= total_pages:
            break
        page += 1
        time.sleep(0.1)

    conn.commit()
    return saved, skipped

print(f"Lade WGI Indikatoren ({DATE_RANGE}, source=75)...")
print("-" * 60)
for i, indicator in enumerate(wgi_indicators):
    print(f"[{i+1}/{len(wgi_indicators)}] {indicator}...")
    saved, skipped = load_wb_indicator(indicator, source_num=75, date_range=DATE_RANGE)
    total_saved += saved
    total_skipped += skipped
    print(f"  → {saved} neu, {skipped} bereits vorhanden")
    time.sleep(0.5)

cur.close()
conn.close()
print("-" * 60)
print(f"Fertig! Neu: {total_saved} | Bereits vorhanden: {total_skipped}")