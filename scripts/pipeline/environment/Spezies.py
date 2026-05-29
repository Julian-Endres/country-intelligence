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
    
    # Länderliste abrufen
    cur.execute("SELECT iso_numeric, iso_code_2, name FROM countries WHERE iso_code_2 IS NOT NULL")
    countries = cur.fetchall()

    print(f"Starte Import der Top 10 Spezies in das Schema 'biodiversity' für {len(countries)} Länder...")

    for iso_numeric, iso2, name in countries:
        print(f"Lade Top 10 für {name}...")
        
        try:
            # Facet-Suche bei GBIF
            r = occ.search(country=iso2, facet="scientificName", limit=0, facetLimit=10)
            
            # Fehlerbehebung: Prüfen ob 'r' ein Dictionary ist
            if isinstance(r, dict):
                facets = r.get('facets', {})
                # Prüfen ob 'scientificName' existiert und eine Liste ist
                species_data = facets.get('scientificName', [])
                
                if isinstance(species_data, list):
                    for entry in species_data:
                        s_name = entry.get('name')
                        count = entry.get('count')
                        
                        if s_name and count:
                            cur.execute("""
                                INSERT INTO biodiversity.species_occurrences 
                                    (iso_numeric, year, scientific_name, occurrence_count)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (iso_numeric, year, scientific_name) DO NOTHING
                            """, (iso_numeric, 2024, s_name, count))
                else:
                    print(f"    Warnung: Keine Arten-Liste für {name} gefunden (Antwort: {type(species_data)})")
            else:
                print(f"    Warnung: Unerwartetes Antwortformat für {name}")

            conn.commit()
            time.sleep(0.3)
            
        except Exception as e:
            print(f"    Fehler bei {name}: {e}")
            continue

    cur.close()
    conn.close()
    print("Fertig! Daten erfolgreich in 'biodiversity.species_occurrences' gespeichert.")

if __name__ == "__main__":
    main()