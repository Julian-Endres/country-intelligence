import os
import time
import requests
import psycopg2
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://data.unesco.org/api/explore/v2.1/catalog/datasets/ich001/records"

VARIABLES = [
    ("UNESCO_ICH:total", "UNESCO Intangible Cultural Heritage – Total Elements",     "count", "Culture & Identity"),
    ("UNESCO_ICH:rl",    "UNESCO ICH – Representative List Elements",                "count", "Culture & Identity"),
    ("UNESCO_ICH:usl",   "UNESCO ICH – Urgent Safeguarding List Elements",           "count", "Culture & Identity"),
    ("UNESCO_ICH:rsp",   "UNESCO ICH – Register of Good Safeguarding Practices",     "count", "Culture & Identity"),
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
    print("Registriere Quelle 'UNESCO_ICH'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('UNESCO Intangible Cultural Heritage', 'UNESCO_ICH',
          'https://ich.unesco.org',
          'UNESCO ICH – traditional practices, dances, rituals, crafts by country'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'UNESCO_ICH'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def fetch_all_elements():
    all_records = []
    offset = 0
    limit = 100

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "select": "uuid,inscription_year,type_acronym,countries",
        }
        r = requests.get(API_URL, params=params, timeout=30)
        if r.status_code != 200:
            print(f"API Fehler: {r.status_code}")
            break

        data = r.json()
        records = data.get("results", [])
        if not records:
            break

        all_records.extend(records)
        total = data.get("total_count", 0)
        print(f"  {len(all_records)}/{total} Elemente geladen...")

        if len(all_records) >= total:
            break
        offset += limit
        time.sleep(0.1)

    return all_records

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lade UNESCO ICH Elemente...")
        elements = fetch_all_elements()
        print(f"{len(elements)} Elemente geladen.")

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_2 FROM countries")
        country_map = {row[1].upper(): row[0] for row in cur.fetchall()}

        counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        for el in elements:
            countries = el.get("countries")
            year = str(el.get("inscription_year", "") or "2024")
            type_code = (el.get("type_acronym") or "").strip().upper()

            if not countries:
                continue

            # countries ist eine Liste von ISO2-Codes
            if isinstance(countries, list):
                iso2_list = [str(c).strip().upper() for c in countries]
            else:
                iso2_list = [str(countries).strip().upper()]

            for iso2 in iso2_list:
                if len(iso2) != 2:
                    continue

                iso_numeric = country_map.get(iso2)
                if not iso_numeric:
                    continue

                counts[iso_numeric][year]["total"] += 1
                if type_code == "RL":
                    counts[iso_numeric][year]["rl"] += 1
                elif type_code == "USL":
                    counts[iso_numeric][year]["usl"] += 1
                elif type_code == "RSP":
                    counts[iso_numeric][year]["rsp"] += 1

        total_saved = 0
        for iso_numeric, years in counts.items():
            for year, type_counts in years.items():
                for type_key, count in type_counts.items():
                    indicator_code = f"UNESCO_ICH:{type_key}"
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, indicator_code, source_id, float(count), year))
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