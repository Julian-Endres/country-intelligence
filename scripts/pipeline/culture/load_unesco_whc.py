import os
import requests
import psycopg2
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/whc001/records"

VARIABLES = [
    ("UNESCO_WHC:total",    "UNESCO World Heritage Sites - Total",    "count", "Culture & Identity"),
    ("UNESCO_WHC:cultural", "UNESCO World Heritage Sites - Cultural", "count", "Culture & Identity"),
    ("UNESCO_WHC:natural",  "UNESCO World Heritage Sites - Natural",  "count", "Culture & Identity"),
    ("UNESCO_WHC:mixed",    "UNESCO World Heritage Sites - Mixed",    "count", "Culture & Identity"),
]

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'UNESCO_WHC'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('UNESCO World Heritage Centre', 'UNESCO_WHC',
          'https://whc.unesco.org',
          'UNESCO World Heritage Sites by country - cultural, natural, mixed'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'UNESCO_WHC'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def fetch_all_sites():
    all_records = []
    offset = 0
    limit = 100

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "select": "id_no,category,iso_codes,date_inscribed",
        }
        r = requests.get(API_URL, params=params, timeout=30)
        if r.status_code != 200:
            print(f"API Fehler: {r.status_code} – {r.text[:200]}")
            break

        data = r.json()
        records = data.get("results", [])
        if not records:
            break

        all_records.extend(records)
        total = data.get("total_count", 0)
        print(f"  {len(all_records)}/{total} Sites geladen...")

        if len(all_records) >= total:
            break
        offset += limit

    return all_records

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lade UNESCO World Heritage Sites...")
        sites = fetch_all_sites()
        print(f"{len(sites)} Sites geladen.")

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_2 FROM countries")
        country_map = {row[1].upper(): row[0] for row in cur.fetchall()}

        # Aggregieren pro Land und Kategorie
        counts = defaultdict(lambda: defaultdict(int))

        for site in sites:
            iso_codes = site.get("iso_codes", "")
            category = site.get("category", "").strip()

            if not iso_codes:
                continue

            # Manche Sites gehören mehreren Ländern (kommagetrennt)
            for iso2 in str(iso_codes).split(","):
                iso2 = iso2.strip().upper()
                if len(iso2) != 2:
                    continue

                iso_numeric = country_map.get(iso2)
                if not iso_numeric:
                    continue

                counts[iso_numeric]["total"] += 1
                if category == "Cultural":
                    counts[iso_numeric]["cultural"] += 1
                elif category == "Natural":
                    counts[iso_numeric]["natural"] += 1
                elif category == "Mixed":
                    counts[iso_numeric]["mixed"] += 1

        # In DB laden
        total_saved = 0
        TIME_PERIOD = "2024"

        for iso_numeric, cat_counts in counts.items():
            for cat, count in cat_counts.items():
                indicator_code = f"UNESCO_WHC:{cat}"
                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, float(count), TIME_PERIOD))
                total_saved += 1

        conn.commit()
        print(f"\nFertig! {total_saved} Datenpunkte geladen.")

    except Exception as e:
        conn.rollback()
        print(f"Fehler: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()