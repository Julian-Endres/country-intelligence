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

BASE_URL = "https://ghoapi.azureedge.net/api"

# ── 1. WHO als Source eintragen falls noch nicht vorhanden ────────────────────
cur.execute("""
    INSERT INTO sources (name, short_code, url, description)
    VALUES ('World Health Organization', 'WHO', 'https://www.who.int/data/gho', 
            'Global Health Observatory – health statistics worldwide')
    ON CONFLICT (short_code) DO NOTHING
""")
conn.commit()
print("Source WHO gesetzt.")

# ── 2. Alle GHO Indikatoren laden ─────────────────────────────────────────────
print("Lade GHO Indicator Liste...")

url = f"{BASE_URL}/Indicator"
all_indicators = []
page_url = url

while page_url:
    try:
        r = requests.get(page_url, timeout=30)
        if r.status_code != 200:
            print(f"Fehler: HTTP {r.status_code}")
            break
        data = r.json()
    except Exception as e:
        print(f"Fehler: {e}")
        break

    indicators = data.get("value", [])
    all_indicators.extend(indicators)

    # OData pagination
    page_url = data.get("@odata.nextLink", None)
    print(f"  {len(all_indicators)} Indikatoren geladen...")
    time.sleep(0.3)

print(f"\nGesamt: {len(all_indicators)} Indikatoren gefunden")

# ── 3. In indicator_catalog speichern ─────────────────────────────────────────
print("Speichere in indicator_catalog...")
saved = 0
skipped = 0

for ind in all_indicators:
    code = ind.get("IndicatorCode")
    name = ind.get("IndicatorName", "")
    language = ind.get("Language", "")

    # Nur englische Einträge
    if language and language.lower() not in ["en", "eng", ""]:
        skipped += 1
        continue

    if not code:
        skipped += 1
        continue

    full_code = f"WHO:{code}"

    cur.execute("""
        INSERT INTO indicator_catalog
            (source_code, name, source, last_checked)
        VALUES (%s, %s, %s, CURRENT_DATE)
        ON CONFLICT (source_code) DO UPDATE SET
            name = EXCLUDED.name,
            last_checked = EXCLUDED.last_checked
    """, (full_code, name[:500] if name else full_code, 'WHO'))
    saved += 1

conn.commit()
cur.close()
conn.close()

print(f"\nFertig!")
print(f"  Gespeichert: {saved}")
print(f"  Übersprungen: {skipped}")
print(f"\nNächster Schritt: who_check_coverage.py ausführen")
