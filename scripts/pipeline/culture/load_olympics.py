import os
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────
# OWID Olympics Datasets – direkt von GitHub
DATASETS = [
    {
        "url": "https://ourworldindata.org/grapher/olympic-games-gold-medals.csv?v=1&csvType=full&useColumnShortNames=false",
        "indicator_code": "OLY:gold",
        "name": "Olympic Gold Medals",
        "unit": "count",
    },
    {
        "url": "https://ourworldindata.org/grapher/olympic-games-silver-medals.csv?v=1&csvType=full&useColumnShortNames=false",
        "indicator_code": "OLY:silver",
        "name": "Olympic Silver Medals",
        "unit": "count",
    },
    {
        "url": "https://ourworldindata.org/grapher/olympic-games-bronze-medals.csv?v=1&csvType=full&useColumnShortNames=false",
        "indicator_code": "OLY:bronze",
        "name": "Olympic Bronze Medals",
        "unit": "count",
    },
    {
        "url": "https://ourworldindata.org/grapher/olympic-games-total-medals.csv?v=1&csvType=full&useColumnShortNames=false",
        "indicator_code": "OLY:total",
        "name": "Olympic Total Medals",
        "unit": "count",
    },
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
    print("Registriere Quelle 'OLYMPICS'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Olympic Games – OWID', 'OLYMPICS',
          'https://ourworldindata.org/olympics',
          'Olympic medals by country per year, Summer + Winter Games'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'OLYMPICS'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for ds in DATASETS:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (ds["indicator_code"], ds["name"], ds["unit"], source_id, "Culture & Identity"))

    return source_id

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        country_map = {row[1]: row[0] for row in cur.fetchall()}

        total_saved = 0

        for ds in DATASETS:
            print(f"\nLade {ds['name']}...")

            try:
                df = pd.read_csv(ds["url"], low_memory=False)
            except Exception as e:
                print(f"  Fehler beim Laden: {e}")
                continue

            print(f"  {len(df)} Zeilen, Spalten: {list(df.columns)}")

            # Spalten identifizieren
            # OWID Format: Entity, Code, Year, <value_column>
            if "Code" not in df.columns or "Year" not in df.columns:
                print(f"  Unerwartetes Format – überspringe.")
                continue

            # Wert-Spalte ist die 4te Spalte
            value_col = [c for c in df.columns if c not in ["Entity", "Code", "Year"]][0]

            skipped = set()
            ds_saved = 0

            for _, row in df.iterrows():
                iso3 = str(row["Code"]).upper().strip()
                if len(iso3) != 3 or iso3 == "NAN":
                    continue

                year = str(int(row["Year"]))
                value = row[value_col]

                if pd.isna(value):
                    continue

                iso_numeric = country_map.get(iso3)
                if not iso_numeric:
                    skipped.add(iso3)
                    continue

                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, ds["indicator_code"], source_id, float(value), year))
                ds_saved += 1
                total_saved += 1

            conn.commit()
            print(f"  {ds_saved} Datenpunkte gespeichert.")
            if skipped:
                print(f"  Nicht gematchte Codes: {sorted(skipped)[:10]}")

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
