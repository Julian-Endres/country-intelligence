import os
import zipfile
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────
# Download: https://fenixservices.fao.org/faostat/static/bulkdownloads/Inputs_LandUse_E_All_Data_(Normalized).zip

VARIABLES = {
    "Country area":                     ("FAO_LAND:country_area",        "Country Area",                         "1000 ha"),
    "Land area":                        ("FAO_LAND:land_area",            "Land Area",                            "1000 ha"),
    "Agricultural land":                ("FAO_LAND:agricultural_land",    "Agricultural Land",                    "1000 ha"),
    "Cropland":                         ("FAO_LAND:cropland",             "Cropland",                             "1000 ha"),
    "Arable land":                      ("FAO_LAND:arable_land",          "Arable Land",                          "1000 ha"),
    "Permanent crops":                  ("FAO_LAND:permanent_crops",      "Permanent Crops",                      "1000 ha"),
    "Permanent meadows and pastures":   ("FAO_LAND:pastures",             "Permanent Meadows and Pastures",       "1000 ha"),
    "Forest land":                      ("FAO_LAND:forest_land",          "Forest Land",                          "1000 ha"),
    "Primary Forest":                   ("FAO_LAND:primary_forest",       "Primary Forest",                       "1000 ha"),
    "Naturally regenerating forest":    ("FAO_LAND:nat_regen_forest",     "Naturally Regenerating Forest",        "1000 ha"),
    "Planted Forest":                   ("FAO_LAND:planted_forest",       "Planted Forest",                       "1000 ha"),
    "Other land":                       ("FAO_LAND:other_land",           "Other Land",                           "1000 ha"),
    "Inland waters":                    ("FAO_LAND:inland_waters",        "Inland Waters",                        "1000 ha"),
}

CATEGORY = "Geography & Environment"

# ── DB-Verbindung ────────────────────────────────────────────────────────────
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

# ── Source & Metadata ────────────────────────────────────────────────────────
def setup_source_and_metadata(cur):
    print("Registriere Quelle 'FAO_LAND'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('FAOSTAT Land Use', 'FAO_LAND',
          'https://www.fao.org/faostat/en/#data/RL',
          'FAO Land Use statistics – forest, cropland, pastures, 1961+'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'FAO_LAND'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for item_name, (code, name, unit) in VARIABLES.items():
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, CATEGORY))

    return source_id

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="FAO Land Use Loader")
    parser.add_argument("file", help="Pfad zur ZIP-Datei (Inputs_LandUse_E_All_Data_(Normalized).zip)")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lese FAO Land Use Daten...")
        with zipfile.ZipFile(args.file) as z:
            with z.open('Inputs_LandUse_E_All_Data_(Normalized).csv') as f:
                df = pd.read_csv(f, encoding='latin-1', low_memory=False)

        print(f"{len(df)} Zeilen geladen.")

        # Nur relevante Items
        df = df[df['Item'].isin(VARIABLES.keys())]

        # Nur Element = "Area" (nicht Prozent-Varianten)
        df = df[df['Element'] == 'Area']

        # M49 Code bereinigen – FAO nutzt '004 Format mit führendem Apostroph
        df['iso_numeric'] = df['Area Code (M49)'].astype(str).str.replace("'", "").str.strip().str.zfill(3)

        # Ländercodes aus DB laden
        cur.execute("SELECT iso_numeric FROM countries")
        valid_iso = set(row[0] for row in cur.fetchall())

        # Nur echte Länder (keine Regionen/Aggregate)
        df = df[df['iso_numeric'].isin(valid_iso)]

        print(f"{len(df)} Zeilen nach Filterung.")

        total_saved = 0

        for _, row in df.iterrows():
            iso_numeric = row['iso_numeric']
            item = row['Item']
            year = str(int(row['Year']))
            value = row['Value']

            if pd.isna(value):
                continue

            indicator_code, _, _ = VARIABLES[item]

            cur.execute("""
                INSERT INTO indicators
                    (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, indicator_code, source_id, float(value), year))
            total_saved += 1

            if total_saved % 20000 == 0:
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
