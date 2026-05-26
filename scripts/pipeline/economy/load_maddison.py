import os
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

# Variablen: Sheet 'Full data' hat countrycode, country, region, year, gdppc, pop
VARIABLES = [
    ("gdppc", "MADDISON:gdppc", "Real GDP per capita (2011 USD)", "USD 2011", "Economy & Infrastructure"),
    ("pop",   "MADDISON:pop",   "Population",                      "millions", "Population & Demographics"),
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
    print("Registriere Quelle 'MADDISON'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Maddison Project Database 2023', 'MADDISON',
          'https://www.rug.nl/ggdc/historicaldevelopment/maddison/',
          'Historical GDP per capita and population, Year 1 to 2022, 169 countries'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'MADDISON'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def main():
    parser = argparse.ArgumentParser(description="Maddison Project Database Loader")
    parser.add_argument("file", help="Pfad zur mpd2023_web.xlsx Datei")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lese Maddison Project Database...")
        df = pd.read_excel(args.file, sheet_name='Full data', engine='openpyxl')
        print(f"{len(df)} Zeilen geladen.")

        # Ländercodes laden – Maddison nutzt ISO3
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        country_map = {row[1]: row[0] for row in cur.fetchall()}

        # Nur echte Jahreszahlen (nicht Jahr 1, 730 etc. – optional: alle laden)
        # Wir laden alles – time_period als String
        df = df[df['countrycode'].notna()]

        total_saved = 0

        for _, row in df.iterrows():
            iso3 = str(row['countrycode']).upper().strip()
            year = row['year']

            if pd.isna(year):
                continue

            year_str = str(int(year))
            iso_numeric = country_map.get(iso3)
            if not iso_numeric:
                continue

            for col, indicator_code, _, _, _ in VARIABLES:
                value = row[col]
                if pd.isna(value):
                    continue

                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, float(value), year_str))
                total_saved += 1

            if total_saved % 20000 == 0 and total_saved > 0:
                conn.commit()
                print(f"{total_saved} Datenpunkte gespeichert...")

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
