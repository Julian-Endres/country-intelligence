import os
import gzip
import psycopg2
import pandas as pd
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Nur diese titleTypes
TARGET_TYPES = {"movie", "tvSeries", "tvMovie", "tvMiniSeries"}

VARIABLES = [
    ("IMDB:movies",     "IMDb – Movies Produced",          "count", "Communication & Media"),
    ("IMDB:tvseries",   "IMDb – TV Series Produced",       "count", "Communication & Media"),
    ("IMDB:total",      "IMDb – Total Titles Produced",    "count", "Communication & Media"),
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
    print("Registriere Quelle 'IMDB'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('IMDb Non-Commercial Datasets', 'IMDB',
          'https://datasets.imdbws.com',
          'Movies and TV series count by production country and year'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'IMDB'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_2 FROM countries WHERE iso_code_2 IS NOT NULL")
        country_map = {row[1].upper(): row[0] for row in cur.fetchall()}

        # Step 1: title.basics laden – nur relevante titleTypes + Jahr
        print("Lade title.basics (nur relevante Typen)...")
        title_info = {}  # tconst -> (titleType, year)

        with gzip.open('data/raw/imdb_basics.tsv.gz', 'rt', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue  # Header
                parts = line.strip().split('\t')
                if len(parts) < 6:
                    continue
                tconst, title_type, _, _, _, start_year = parts[:6]
                if title_type not in TARGET_TYPES:
                    continue
                if start_year == '\\N' or not start_year.isdigit():
                    continue
                year = int(start_year)
                if year < 1900 or year > 2025:
                    continue
                title_info[tconst] = (title_type, year)

        print(f"{len(title_info):,} relevante Titel geladen.")

        # Step 2: title.akas – nur Originaleinträge pro Titel mit Region
        print("Lade title.akas (Original-Einträge mit Region)...")
        counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        # counts[iso2][year][type] = count

        processed = set()  # Jeder Titel nur einmal pro Region zählen

        with gzip.open('data/raw/imdb_akas.tsv.gz', 'rt', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i == 0:
                    continue
                if i % 5000000 == 0:
                    print(f"  {i:,} Zeilen verarbeitet...")

                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue

                tconst = parts[0]
                region = parts[3]

                if tconst not in title_info:
                    continue
                if region == '\\N' or len(region) != 2:
                    continue
                if region not in country_map:
                    continue

                # Jeder Titel pro Region nur einmal zählen
                key = (tconst, region)
                if key in processed:
                    continue
                processed.add(key)

                title_type, year = title_info[tconst]
                counts[region][year][title_type] += 1

        print(f"Aggregation fertig. {len(counts)} Länder mit Daten.")

        # Step 3: In DB laden
        total_saved = 0

        for iso2, years in counts.items():
            iso_numeric = country_map.get(iso2.upper())
            if not iso_numeric:
                continue

            for year, types in years.items():
                year_str = str(year)

                # Movies
                movie_count = types.get('movie', 0) + types.get('tvMovie', 0)
                if movie_count > 0:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, 'IMDB:movies', %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, source_id, float(movie_count), year_str))
                    total_saved += 1

                # TV Series
                tv_count = types.get('tvSeries', 0) + types.get('tvMiniSeries', 0)
                if tv_count > 0:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, 'IMDB:tvseries', %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, source_id, float(tv_count), year_str))
                    total_saved += 1

                # Total
                total_count = movie_count + tv_count
                if total_count > 0:
                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, 'IMDB:total', %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, source_id, float(total_count), year_str))
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
