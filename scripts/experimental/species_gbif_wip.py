import os
import time
import psycopg2
from pygbif import occurrences as occ
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT iso_numeric, iso_code_2, name FROM countries WHERE iso_code_2 IS NOT NULL")
    countries = cur.fetchall()

    print(f"Starte Import in 'biodiversity.species_occurrences' für {len(countries)} Länder...")

    for iso_numeric, iso2, name in countries:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                res = occ.search(country=iso2, facet="scientificName", limit=0, facetLimit=10)
                
                if isinstance(res, dict) and 'facets' in res:
                    facets = res['facets']
                    species_counts = []
                    
                    # WICHTIG: facets ist eine Liste! Wir müssen das richtige Feld suchen.
                    if isinstance(facets, list):
                        for f in facets:
                            if isinstance(f, dict) and str(f.get('field', '')).upper() == 'SCIENTIFIC_NAME':
                                species_counts = f.get('counts', [])
                                break
                    
                    # Wenn wir Daten gefunden haben, in die DB schreiben
                    if isinstance(species_counts, list) and len(species_counts) > 0:
                        for entry in species_counts:
                            if isinstance(entry, dict):
                                s_name = entry.get('name')
                                count = entry.get('count')
                                
                                if s_name and count is not None:
                                    cur.execute("""
                                        INSERT INTO biodiversity.species_occurrences 
                                            (iso_numeric, year, scientific_name, occurrence_count)
                                        VALUES (%s, %s, %s, %s)
                                        ON CONFLICT (iso_numeric, year, scientific_name) DO NOTHING
                                    """, (iso_numeric, 2024, s_name, count))
                        
                        conn.commit()
                        print(f"    Erfolgreich: Top 10 für {name} geladen.")
                        break # Erfolgreich, raus aus dem Retry-Loop
                    else:
                        print(f"    Keine Arten-Daten für {name}.")
                        break # Kein Fehler, nur keine Daten -> raus aus dem Retry

                else:
                    print(f"    Unerwartetes Antwortformat für {name}.")
                    break

            except Exception as e:
                print(f"    Fehler bei {name} (Versuch {attempt+1}/{max_retries}): {e}")
                time.sleep(2 ** attempt) # Exponential Backoff (1s, 2s, 4s)
                if attempt == max_retries - 1:
                    conn.rollback() # Nach 3 Versuchen aufgeben und mit nächstem Land weitermachen

    cur.close()
    conn.close()
    print("Fertig! Pipeline abgeschlossen.")

if __name__ == "__main__":
    main()