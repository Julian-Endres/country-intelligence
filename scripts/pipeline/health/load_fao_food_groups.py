import os
import zipfile
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

# Ausgewählte Lebensmittelgruppen – repräsentativ für Ernährungskultur
ITEMS = {
    # Grundnahrungsmittel
    "Cereals - Excluding Beer":     ("FAO_FOOD:cereals",        "Cereals Supply per Capita",           "kg/cap/yr"),
    "Rice and products":            ("FAO_FOOD:rice",            "Rice Supply per Capita",              "kg/cap/yr"),
    "Wheat and products":           ("FAO_FOOD:wheat",           "Wheat Supply per Capita",             "kg/cap/yr"),
    "Maize and products":           ("FAO_FOOD:maize",           "Maize Supply per Capita",             "kg/cap/yr"),
    "Starchy Roots":                ("FAO_FOOD:starchy_roots",   "Starchy Roots Supply per Capita",     "kg/cap/yr"),
    "Potatoes and products":        ("FAO_FOOD:potatoes",        "Potatoes Supply per Capita",          "kg/cap/yr"),
    # Proteine
    "Meat":                         ("FAO_FOOD:meat",            "Meat Supply per Capita",              "kg/cap/yr"),
    "Bovine Meat":                  ("FAO_FOOD:beef",            "Beef Supply per Capita",              "kg/cap/yr"),
    "Pigmeat":                      ("FAO_FOOD:pork",            "Pork Supply per Capita",              "kg/cap/yr"),
    "Poultry Meat":                 ("FAO_FOOD:poultry",         "Poultry Supply per Capita",           "kg/cap/yr"),
    "Mutton & Goat Meat":           ("FAO_FOOD:mutton_goat",     "Mutton & Goat Supply per Capita",     "kg/cap/yr"),
    "Fish, Seafood":                ("FAO_FOOD:fish",            "Fish & Seafood Supply per Capita",    "kg/cap/yr"),
    "Eggs":                         ("FAO_FOOD:eggs",            "Eggs Supply per Capita",              "kg/cap/yr"),
    "Milk - Excluding Butter":      ("FAO_FOOD:milk",            "Milk Supply per Capita",              "kg/cap/yr"),
    # Pflanzen
    "Vegetables":                   ("FAO_FOOD:vegetables",      "Vegetables Supply per Capita",        "kg/cap/yr"),
    "Fruits - Excluding Wine":      ("FAO_FOOD:fruits",          "Fruits Supply per Capita",            "kg/cap/yr"),
    "Pulses":                       ("FAO_FOOD:pulses",          "Pulses Supply per Capita",            "kg/cap/yr"),
    "Sugar & Sweeteners":           ("FAO_FOOD:sugar",           "Sugar & Sweeteners per Capita",       "kg/cap/yr"),
    # Getränke
    "Alcoholic Beverages":          ("FAO_FOOD:alcohol",         "Alcoholic Beverages per Capita",      "kg/cap/yr"),
    "Wine":                         ("FAO_FOOD:wine",            "Wine Supply per Capita",              "kg/cap/yr"),
    "Beer":                         ("FAO_FOOD:beer",            "Beer Supply per Capita",              "kg/cap/yr"),
    "Coffee and products":          ("FAO_FOOD:coffee",          "Coffee Supply per Capita",            "kg/cap/yr"),
    "Tea (including mate)":         ("FAO_FOOD:tea",             "Tea Supply per Capita",               "kg/cap/yr"),
    # Öle & Fette
    "Vegetable Oils":               ("FAO_FOOD:vegetable_oils",  "Vegetable Oils per Capita",           "kg/cap/yr"),
    "Olive Oil":                    ("FAO_FOOD:olive_oil",       "Olive Oil per Capita",                "kg/cap/yr"),
    "Palm Oil":                     ("FAO_FOOD:palm_oil",        "Palm Oil per Capita",                 "kg/cap/yr"),
}

# Wir wollen nur den "Food supply quantity (kg/capita/yr)" Element
TARGET_ELEMENT = "Food supply quantity (kg/capita/yr)"
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
    print("Registriere Quelle 'FAO_FOOD_GRP'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('FAOSTAT Food Balance Sheets – Food Groups', 'FAO_FOOD_GRP',
          'https://www.fao.org/faostat/en/#data/FBS',
          'FAO per capita food supply by food group 1961+'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'FAO_FOOD_GRP'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, (code, name, unit) in ITEMS.items():
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, CATEGORY))

    return source_id

def main():
    parser = argparse.ArgumentParser(description="FAO Food Groups Loader")
    parser.add_argument("file", help="Pfad zur ZIP-Datei")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lese FAO Food Balance Sheets...")
        with zipfile.ZipFile(args.file) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv') and 'Normalized' in f]
            with z.open(csv_files[0]) as f:
                df = pd.read_csv(f, encoding='latin-1', low_memory=False)

        print(f"{len(df)} Zeilen geladen.")

        # Nur relevante Items + Element filtern
        df = df[df['Item'].isin(ITEMS.keys())]
        df = df[df['Element'] == TARGET_ELEMENT]

        # M49 Code bereinigen
        df['iso_numeric'] = df['Area Code (M49)'].astype(str).str.replace("'", "").str.strip().str.zfill(3)

        cur.execute("SELECT iso_numeric FROM countries")
        valid_iso = set(row[0] for row in cur.fetchall())
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

            indicator_code, _, _ = ITEMS[item]

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
