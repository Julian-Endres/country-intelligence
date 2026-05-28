import os
import time
import psycopg2
from pygbif import occurrences as occ
from dotenv import load_dotenv

load_dotenv()

# -- Konfiguration ------------------------------------------------------------
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

YEARS = range(2000, 2025)

# -- DB-Verbindung ------------------------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source(cur):
    cur.execute("SELECT id FROM sources WHERE short_code = 'GBIF'")
    row = cur.fetchone()
    if row: return row[0]
    
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES ('Global Biodiversity Information Facility', 'GBIF', 
                'https://www.gbif.org', 'Historical species occurrence counts')
        RETURNING id
    """)
    return cur.fetchone()[0]

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    source_id = setup_source(cur)
    conn.commit()

    # Länder abrufen
    cur.execute("SELECT iso_numeric, iso_code_2, name FROM countries WHERE iso_code_2 IS NOT NULL")
    countries = cur.fetchall()

    print(f"Starte historischen GBIF-Import für {len(countries)} Länder über {len(YEARS)} Jahre.")

    for year in YEARS:
        year_str = str(year)
        
        for iso_numeric, iso2, name in countries:
            # Check: Ist dieses Land/Jahr bereits vorhanden? 
            # WICHTIG: '%%' wird zu einem '%' in der DB-Abfrage
            cur.execute("""
                SELECT 1 FROM indicators 
                WHERE iso_numeric = %s 
                AND indicator_code LIKE 'GBIF:%%' 
                AND time_period = %s 
                LIMIT 1
            """, (iso_numeric, year_str))
            
            if cur.fetchone():
                continue # Bereits erledigt

            data_saved = 0
            for group, taxon_key, _, _ in TAXON_GROUPS:
                try:
                    if taxon_key is None:
                        count = occ.count(country=iso2, year=year)
                    else:
                        count = occ.count(country=iso2, taxonKey=taxon_key, year=year)

                    if count and count > 0:
                        cur.execute("""
                            INSERT INTO indicators 
                                (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                            VALUES (%s, %s, %s, %s, %s, 'A')
                            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                        """, (iso_numeric, f"GBIF:{group}", source_id, float(count), year_str))
                        data_saved += 1
                        
                except Exception as e:
                    print(f"    Fehler bei {group} ({name}, {year}): {e}")
            
            if data_saved > 0:
                conn.commit()
                print(f"  → {name} ({year}): {data_saved} Indikatoren gespeichert.")
            
            time.sleep(0.3) # Rate Limit

    cur.close()
    conn.close()
    print("Historischer Import abgeschlossen.")

if __name__ == "__main__":
    main()