import os
import requests
import psycopg2
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.nobelprize.org/2.1/laureates"

CATEGORIES = {
    "phy": "Physics",
    "che": "Chemistry",
    "med": "Medicine",
    "lit": "Literature",
    "pea": "Peace",
    "eco": "Economics",
}

VARIABLES = [
    ("NOBEL:phy",   "Nobel Prize Laureates – Physics",    "count", "Communication & Media"),
    ("NOBEL:che",   "Nobel Prize Laureates – Chemistry",  "count", "Communication & Media"),
    ("NOBEL:med",   "Nobel Prize Laureates – Medicine",   "count", "Communication & Media"),
    ("NOBEL:lit",   "Nobel Prize Laureates – Literature", "count", "Communication & Media"),
    ("NOBEL:pea",   "Nobel Prize Laureates – Peace",      "count", "Politics & Governance"),
    ("NOBEL:eco",   "Nobel Prize Laureates – Economics",  "count", "Economy & Infrastructure"),
    ("NOBEL:total", "Nobel Prize Laureates – Total",      "count", "Communication & Media"),
]

# Manuelle Overrides für häufige Nobel-API Ländernamen
NAME_OVERRIDES = {
    "usa": "840",
    "uk": "826",
    "united kingdom": "826",
    "great britain": "826",
    "west germany": "276",
    "germany": "276",
    "france": "250",
    "sweden": "752",
    "switzerland": "756",
    "russia": "643",
    "soviet union": "643",
    "ussr": "643",
    "japan": "392",
    "china": "156",
    "india": "356",
    "canada": "124",
    "australia": "036",
    "israel": "376",
    "austria": "040",
    "netherlands": "528",
    "denmark": "208",
    "norway": "578",
    "italy": "380",
    "poland": "616",
    "hungary": "348",
    "argentina": "032",
    "south africa": "710",
    "egypt": "818",
    "pakistan": "586",
    "mexico": "484",
    "belgium": "056",
    "spain": "724",
    "portugal": "620",
    "ireland": "372",
    "finland": "246",
    "czech republic": "203",
    "czechoslovakia": "203",
    "romania": "642",
    "ukraine": "804",
    "turkey": "792",
    "iran": "364",
    "iraq": "368",
    "kenya": "404",
    "nigeria": "566",
    "ghana": "288",
    "myanmar": "104",
    "burma": "104",
    "new zealand": "554",
    "colombia": "170",
    "chile": "152",
    "peru": "604",
    "east timor": "626",
    "timor-leste": "626",
    "taiwan": "158",
    "south korea": "410",
    "north korea": "408",
    "uk": "826",
    "scotland": "826",
    "england": "826",
    "wales": "826",
    "northern ireland": "826",
}

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'NOBEL'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Nobel Prize API', 'NOBEL', 'https://api.nobelprize.org',
          'Nobel Prize laureates by country and category 1901+'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'NOBEL'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def fetch_all_laureates():
    all_laureates = []
    offset = 0
    limit = 100
    headers = {"User-Agent": "Mozilla/5.0 (country-intelligence research project)"}

    while True:
        r = requests.get(BASE_URL, params={"offset": offset, "limit": limit, "format": "json"},
                         headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"API Fehler: {r.status_code}")
            break

        data = r.json()
        laureates = data.get("laureates", [])
        if not laureates:
            break

        all_laureates.extend(laureates)
        total = data.get("meta", {}).get("count", 0)
        print(f"  {len(all_laureates)}/{total} Laureaten geladen...")

        if len(all_laureates) >= total:
            break
        offset += limit

    return all_laureates

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, name FROM countries")
        country_map_name = {row[1].lower(): row[0] for row in cur.fetchall()}

        def resolve_country(name_en):
            if not name_en:
                return None
            name_lower = name_en.lower().strip()
            if name_lower in NAME_OVERRIDES:
                return NAME_OVERRIDES[name_lower]
            if name_lower in country_map_name:
                return country_map_name[name_lower]
            # Partial match
            for db_name, iso_num in country_map_name.items():
                if name_lower in db_name or db_name in name_lower:
                    return iso_num
            return None

        print("Lade Nobel Prize Laureaten...")
        laureates = fetch_all_laureates()
        print(f"{len(laureates)} Laureaten geladen.")

        counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        unmatched = set()

        for laureate in laureates:
            birth = laureate.get("birth", {})
            if not isinstance(birth, dict):
                continue

            place = birth.get("place", {})
            if not isinstance(place, dict):
                continue

            # countryNow bevorzugen (aktueller Landesname)
            country_now = place.get("countryNow", {})
            country_birth = place.get("country", {})

            name_en = None
            if isinstance(country_now, dict):
                name_en = country_now.get("en")
            if not name_en and isinstance(country_birth, dict):
                name_en = country_birth.get("en")

            iso_numeric = resolve_country(name_en)

            if not iso_numeric:
                if name_en:
                    unmatched.add(name_en)
                continue

            for prize in laureate.get("nobelPrizes", []):
                year = str(prize.get("awardYear", ""))
                category = prize.get("category", {}).get("en", "").lower()

                cat_code = None
                for code, label in CATEGORIES.items():
                    if label.lower() in category:
                        cat_code = code
                        break

                if not year or not cat_code:
                    continue

                counts[iso_numeric][year][cat_code] += 1
                counts[iso_numeric][year]["total"] += 1

        # In DB laden
        total_saved = 0

        for iso_numeric, years in counts.items():
            for year, categories in years.items():
                for cat_code, count in categories.items():
                    indicator_code = f"NOBEL:{cat_code}"
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, indicator_code, source_id, float(count), year))
                    total_saved += 1

        conn.commit()

        if unmatched:
            print(f"Nicht gematchte Ländernamen: {sorted(unmatched)}")

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