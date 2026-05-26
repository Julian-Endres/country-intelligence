import os
import time
import psycopg2
from pygbif import occurrences as occ
from dotenv import load_dotenv

load_dotenv()

# IUCN Red List Kategorien
IUCN_CATEGORIES = [
    ("CR", "GBIF:iucn_cr", "IUCN Critically Endangered Species Occurrences", "count"),
    ("EN", "GBIF:iucn_en", "IUCN Endangered Species Occurrences",            "count"),
    ("VU", "GBIF:iucn_vu", "IUCN Vulnerable Species Occurrences",            "count"),
    ("NT", "GBIF:iucn_nt", "IUCN Near Threatened Species Occurrences",       "count"),
]

CATEGORY = "Geography & Environment"
TIME_PERIOD = "2024"

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    cur.execute("SELECT id FROM sources WHERE short_code = 'GBIF'")
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO sources (name, short_code, url, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, ('Global Biodiversity Information Facility', 'GBIF',
              'https://www.gbif.org',
              'Species occurrence counts per country by taxonomic group'))
        source_id = cur.fetchone()[0]
    else:
        source_id = row[0]

    print(f"Source ID: {source_id}")

    for _, code, name, unit in IUCN_CATEGORIES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, CATEGORY))

    return source_id

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Alle Länder mit ISO2-Code laden
        cur.execute("SELECT iso_numeric, iso_code_2, name FROM countries WHERE iso_code_2 IS NOT NULL")
        countries = cur.fetchall()
        print(f"{len(countries)} Länder geladen.")

        # Resume: bereits geladene Länder checken
        cur.execute("""
            SELECT DISTINCT iso_numeric FROM indicators
            WHERE indicator_code = 'GBIF:iucn_cr'
        """)
        already_loaded = set(r[0] for r in cur.fetchall())
        print(f"{len(already_loaded)} Länder bereits geladen.")

        total_saved = 0

        for i, (iso_numeric, iso2, name) in enumerate(countries):
            if iso_numeric in already_loaded:
                continue

            print(f"[{i+1}/{len(countries)}] {name} ({iso2})...")
            country_saved = 0

            for iucn_cat, indicator_code, _, _ in IUCN_CATEGORIES:
                try:
                    r = occ.search(country=iso2, iucnRedListCategory=iucn_cat, limit=0)
                    count = r.get('count', 0)

                    if not count:
                        continue

                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, indicator_code, source_id, float(count), TIME_PERIOD))
                    country_saved += 1
                    total_saved += 1

                except Exception as e:
                    print(f"    Fehler bei {iucn_cat}: {e}")
                    continue

                time.sleep(0.3)

            conn.commit()
            print(f"    {country_saved} Indikatoren. Total: {total_saved}")

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
