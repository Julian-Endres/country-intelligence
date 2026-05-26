import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

URL = "https://ourworldindata.org/grapher/press-freedom-index-rsf.csv?v=1&csvType=full&useColumnShortNames=false"

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

    try:
        # Source
        cur.execute("""
            INSERT INTO sources (name, short_code, url, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (short_code) DO NOTHING
            RETURNING id
        """, ('Reporters Without Borders – Press Freedom Index', 'RSF',
              'https://rsf.org/en/index',
              'Press Freedom Index – 180 countries, 2013–2025'))
        result = cur.fetchone()
        if result:
            source_id = result[0]
        else:
            cur.execute("SELECT id FROM sources WHERE short_code = 'RSF'")
            source_id = cur.fetchone()[0]

        # Metadata
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, ('RSF:press_freedom', 'Press Freedom Index', 'score 0-100', source_id, 'Communication & Media'))
        conn.commit()

        # Ländercodes
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        country_map = {row[1]: row[0] for row in cur.fetchall()}

        print("Lade Press Freedom Index von OWID...")
        df = pd.read_csv(URL, storage_options={'User-Agent': 'country-intelligence/1.0'})
        print(f"{len(df)} Zeilen geladen.")

        total_saved = 0
        skipped = set()

        for _, row in df.iterrows():
            iso3 = str(row['Code']).upper().strip()
            year = str(int(row['Year']))
            value = row['Press Freedom Index']

            if pd.isna(value):
                continue

            iso_numeric = country_map.get(iso3)
            if not iso_numeric:
                skipped.add(iso3)
                continue

            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, 'RSF:press_freedom', %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, source_id, float(value), year))
            total_saved += 1

        conn.commit()
        if skipped:
            print(f"Nicht gematchte Codes: {sorted(skipped)}")
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
