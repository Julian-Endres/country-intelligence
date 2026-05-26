import os
import time
import psycopg2
from pygbif import occurrences as occ
from dotenv import load_dotenv

load_dotenv()

# -- Konfiguration ------------------------------------------------------------
# Taxon-Keys: GBIF Backbone Taxonomy
TAXON_GROUPS = [
    ("total",      None,     "Total Species Occurrences",    "count"),
    ("birds",      212,      "Bird Species Occurrences",     "count"),
    ("mammals",    359,      "Mammal Species Occurrences",   "count"),
    ("plants",     6,        "Plant Species Occurrences",    "count"),
    ("insects",    216,      "Insect Species Occurrences",   "count"),
    ("amphibians", 131,      "Amphibian Species Occurrences","count"),
    ("reptiles",   11418114, "Reptile Species Occurrences",  "count"),
    ("fungi",      5,        "Fungi Species Occurrences",    "count"),
    ("fish",       204,      "Fish Species Occurrences",     "count"),
]

CATEGORY = "Geography & Environment"

# -- DB-Verbindung ------------------------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

# -- Source & Metadata --------------------------------------------------------
def setup_source_and_metadata(cur):
    print("Registriere Quelle 'GBIF'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Global Biodiversity Information Facility', 'GBIF',
          'https://www.gbif.org',
          'Species occurrence counts per country by taxonomic group'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'GBIF'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for group, _, name, unit in TAXON_GROUPS:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (f"GBIF:{group}", name, unit, source_id, CATEGORY))

    return source_id

# -- Main ---------------------------------------------------------------------
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
            WHERE indicator_code = 'GBIF:total'
        """)
        already_loaded = set(r[0] for r in cur.fetchall())
        print(f"{len(already_loaded)} Länder bereits geladen.")

        total_saved = 0
        # GBIF Daten sind statisch (kein Jahreswert) → time_period = aktuelles Jahr
        TIME_PERIOD = "2024"

        for i, (iso_numeric, iso2, name) in enumerate(countries):
            if iso_numeric in already_loaded:
                continue

            print(f"[{i+1}/{len(countries)}] {name} ({iso2})...")
            country_saved = 0

            for group, taxon_key, _, _ in TAXON_GROUPS:
                try:
                    if taxon_key is None:
                        count = occ.count(country=iso2)
                    else:
                        count = occ.count(country=iso2, taxonKey=taxon_key)

                    if count is None or count == 0:
                        continue

                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, f"GBIF:{group}", source_id, float(count), TIME_PERIOD))
                    country_saved += 1
                    total_saved += 1

                except Exception as e:
                    print(f"    Fehler bei {group}: {e}")
                    continue

                time.sleep(0.2)  # Rate Limit

            conn.commit()
            print(f"    {country_saved} Indikatoren gespeichert. Total: {total_saved}")

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