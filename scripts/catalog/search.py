import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Suchbegriff aus Terminal
if len(sys.argv) < 2:
    print("Verwendung: python3 search.py <suchbegriff>")
    print("Beispiel:   python3 search.py education")
    sys.exit(1)

search_term = " ".join(sys.argv[1:]).lower()

print(f"\n🔍 Suche nach: '{search_term}'")
print("-" * 80)

cur.execute("""
    SELECT 
        source_code,
        name,
        category,
        country_coverage,
        source
    FROM indicator_catalog
    WHERE 
        LOWER(name) LIKE %s OR
        LOWER(description) LIKE %s OR
        LOWER(category) LIKE %s
    ORDER BY 
        country_coverage DESC NULLS LAST,
        name ASC
    LIMIT 20
""", (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))

results = cur.fetchall()

if not results:
    print("Keine Ergebnisse gefunden.")
else:
    print(f"{'Code':<35} {'Name':<45} {'Kategorie':<25} {'Länder'}")
    print("-" * 80)
    for row in results:
        code = row[0] or ""
        name = (row[1] or "")[:43]
        category = (row[2] or "")[:23]
        coverage = row[3] or "?"
        print(f"{code:<35} {name:<45} {category:<25} {coverage}")

cur.close()
conn.close()