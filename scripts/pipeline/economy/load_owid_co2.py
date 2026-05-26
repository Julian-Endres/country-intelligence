import os
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────
CSV_URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"

VARIABLES = [
    ("co2",                       "OWID_CO2:co2",                   "CO2 Emissions (Total)",                    "Mt CO2",        "Geography & Environment"),
    ("co2_per_capita",            "OWID_CO2:co2_per_capita",        "CO2 Emissions per Capita",                 "t CO2/person",  "Geography & Environment"),
    ("co2_per_gdp",               "OWID_CO2:co2_per_gdp",           "CO2 Emissions per GDP",                    "kg CO2/$",      "Geography & Environment"),
    ("share_global_co2",          "OWID_CO2:share_global_co2",      "Share of Global CO2 Emissions",            "%",             "Geography & Environment"),
    ("methane",                   "OWID_CO2:methane",               "Methane Emissions",                        "Mt CO2eq",      "Geography & Environment"),
    ("nitrous_oxide",             "OWID_CO2:nitrous_oxide",         "Nitrous Oxide Emissions",                  "Mt CO2eq",      "Geography & Environment"),
    ("primary_energy_consumption","OWID_CO2:primary_energy",        "Primary Energy Consumption",               "TWh",           "Geography & Environment"),
    ("renewables_share_energy",   "OWID_CO2:renewables_share",      "Renewables Share of Energy",               "%",             "Geography & Environment"),
    ("fossil_fuel_consumption",   "OWID_CO2:fossil_fuel",           "Fossil Fuel Consumption",                  "TWh",           "Geography & Environment"),
    ("coal_co2",                  "OWID_CO2:coal_co2",              "CO2 from Coal",                            "Mt CO2",        "Geography & Environment"),
    ("oil_co2",                   "OWID_CO2:oil_co2",               "CO2 from Oil",                             "Mt CO2",        "Geography & Environment"),
    ("gas_co2",                   "OWID_CO2:gas_co2",               "CO2 from Gas",                             "Mt CO2",        "Geography & Environment"),
]

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
    print("Registriere Quelle 'OWID_CO2'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Our World in Data – CO2 & GHG Emissions', 'OWID_CO2',
          'https://github.com/owid/co2-data',
          'CO2 and greenhouse gas emissions, energy mix, 1750–2024'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'OWID_CO2'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, code, name, unit, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print(f"Lade CSV von GitHub...")
        df = pd.read_csv(CSV_URL, low_memory=False)
        print(f"{len(df)} Zeilen geladen.")

        # Nur Länder mit ISO3-Code (keine Regionen/Aggregate)
        df = df[df["iso_code"].notna()]
        df = df[df["iso_code"].str.len() == 3]
        df = df[~df["iso_code"].str.startswith("OWID")]  # OWID-Aggregate raus

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        country_map = {row[1]: row[0] for row in cur.fetchall()}

        total_saved = 0
        skipped = set()

        for _, row in df.iterrows():
            iso3 = str(row["iso_code"]).upper().strip()
            year = str(int(row["year"]))

            iso_numeric = country_map.get(iso3)
            if not iso_numeric:
                skipped.add(iso3)
                continue

            for csv_col, indicator_code, _, _, _ in VARIABLES:
                value = row.get(csv_col)
                if pd.isna(value):
                    continue

                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, float(value), year))
                total_saved += 1

            if total_saved % 20000 == 0 and total_saved > 0:
                conn.commit()
                print(f"{total_saved} Datenpunkte gespeichert...")

        conn.commit()

        if skipped:
            print(f"Nicht gematchte ISO-Codes: {sorted(skipped)}")

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
