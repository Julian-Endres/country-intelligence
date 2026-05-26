import os
import zipfile
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────
# Download:
# curl -L "https://fenixservices.fao.org/faostat/static/bulkdownloads/FoodBalanceSheets_E_All_Data_(Normalized).zip" -o data/raw/fao_food.zip

# Item = Grand Total, Elemente die wir laden
ELEMENTS = {
    "Food supply (kcal/capita/day)":          ("FAO_FOOD:kcal_per_capita",     "Food Supply (kcal per capita per day)",   "kcal/cap/day"),
    "Protein supply quantity (g/capita/day)": ("FAO_FOOD:protein_per_capita",  "Protein Supply (g per capita per day)",   "g/cap/day"),
    "Fat supply quantity (g/capita/day)":     ("FAO_FOOD:fat_per_capita",      "Fat Supply (g per capita per day)",       "g/cap/day"),
}

TARGET_ITEM = "Grand Total"
CATEGORY = "Health, Body & Behavior"

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'FAO_FOOD'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('FAOSTAT Food Balance Sheets', 'FAO_FOOD',
          'https://www.fao.org/faostat/en/#data/FBS',
          'FAO Food Balance Sheets – caloric supply, protein, fat per capita 1961+'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'FAO_FOOD'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for element, (code, name, unit) in ELEMENTS.items():
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, CATEGORY))

    return source_id

def main():
    parser = argparse.ArgumentParser(description="FAOSTAT Food Balance Sheets Loader")
    parser.add_argument("file", help="Pfad zur ZIP-Datei")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lese FAOSTAT Food Balance Sheets...")
        with zipfile.ZipFile(args.file) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv') and 'Normalized' in f]
            print(f"CSV Datei: {csv_files[0]}")
            with z.open(csv_files[0]) as f:
                df = pd.read_csv(f, encoding='latin-1', low_memory=False)

        print(f"{len(df)} Zeilen geladen.")

        # Nur Grand Total + relevante Elemente
        df = df[df['Item'] == TARGET_ITEM]
        df = df[df['Element'].isin(ELEMENTS.keys())]

        # M49 Code bereinigen
        df['iso_numeric'] = df['Area Code (M49)'].astype(str).str.replace("'", "").str.strip().str.zfill(3)

        # Ländercodes aus DB laden
        cur.execute("SELECT iso_numeric FROM countries")
        valid_iso = set(row[0] for row in cur.fetchall())
        df = df[df['iso_numeric'].isin(valid_iso)]

        print(f"{len(df)} Zeilen nach Filterung.")

        total_saved = 0

        for _, row in df.iterrows():
            iso_numeric = row['iso_numeric']
            element = row['Element']
            year = str(int(row['Year']))
            value = row['Value']

            if pd.isna(value):
                continue

            indicator_code, _, _ = ELEMENTS[element]

            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, indicator_code, source_id, float(value), year))
            total_saved += 1

            if total_saved % 10000 == 0:
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