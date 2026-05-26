import os
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

VARIABLES = {
    "Life evaluation (3-year average)":          ("WHR:life_evaluation",  "Life Evaluation (Cantril Ladder)",          "score 0-10"),
    "Explained by: Log GDP per capita":          ("WHR:gdp_component",    "WHR – GDP per capita component",            "score"),
    "Explained by: Social support":              ("WHR:social_support",   "WHR – Social Support component",            "score"),
    "Explained by: Healthy life expectancy":     ("WHR:health",           "WHR – Healthy Life Expectancy component",   "score"),
    "Explained by: Freedom to make life choices":("WHR:freedom",          "WHR – Freedom component",                   "score"),
    "Explained by: Generosity":                  ("WHR:generosity",       "WHR – Generosity component",                "score"),
    "Explained by: Perceptions of corruption":   ("WHR:corruption",       "WHR – Corruption Perception component",     "score"),
}

CATEGORY = "Social Fabric & Daily Life"

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'WHR'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('World Happiness Report', 'WHR',
          'https://worldhappiness.report',
          'Annual happiness scores and contributing factors, 2011–2025'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'WHR'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, (code, name, unit) in VARIABLES.items():
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, CATEGORY))

    return source_id

def main():
    parser = argparse.ArgumentParser(description="World Happiness Report Loader")
    parser.add_argument("file", help="Pfad zur WHR Excel-Datei")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print("Lese WHR Daten...")
        xl = pd.ExcelFile(args.file, engine='openpyxl')
        df = pd.read_excel(args.file, sheet_name=xl.sheet_names[0], engine='openpyxl')
        print(f"{len(df)} Zeilen geladen.")

        # Ländercodes laden – WHR hat Ländernamen, kein ISO
        cur.execute("SELECT iso_numeric, name FROM countries")
        country_map_name = {row[1].lower(): row[0] for row in cur.fetchall()}

        # Manuelle Overrides für WHR Ländernamen
        NAME_OVERRIDES = {
            "united states": "840",
            "united kingdom": "826",
            "south korea": "410",
            "north korea": "408",
            "taiwan province of china": "158",
            "hong kong s.a.r. of china": "344",
            "vietnam": "704",
            "iran": "364",
            "syria": "760",
            "laos": "418",
            "moldova": "498",
            "russia": "643",
            "bolivia": "068",
            "venezuela": "862",
            "tanzania": "834",
            "congo (brazzaville)": "178",
            "congo (kinshasa)": "180",
            "ivory coast": "384",
            "turkiye": "792",
            "turkey": "792",
            "palestine": "275",
            "state of palestine": "275",
            "eswatini": "748",
            "swaziland": "748",
            "c\u00f4te d'ivoire": "384",
            "cote d'ivoire": "384",
            "lao pdr": "418",
            "republic of korea": "410",
            "türkiye": "792",
            "viet nam": "704",
            "c\u00f4te d\u2019ivoire": "384",
        }

        def resolve_country(name):
            if not name:
                return None
            name_lower = str(name).lower().strip()
            if name_lower in NAME_OVERRIDES:
                return NAME_OVERRIDES[name_lower]
            if name_lower in country_map_name:
                return country_map_name[name_lower]
            for db_name, iso_num in country_map_name.items():
                if name_lower in db_name or db_name in name_lower:
                    return iso_num
            return None

        total_saved = 0
        skipped = set()

        for _, row in df.iterrows():
            country_name = row.get('Country name')
            year = row.get('Year')

            if pd.isna(year) or pd.isna(country_name):
                continue

            year_str = str(int(year))
            iso_numeric = resolve_country(country_name)

            if not iso_numeric:
                skipped.add(str(country_name))
                continue

            for col, (indicator_code, _, _) in VARIABLES.items():
                value = row.get(col)
                if pd.isna(value):
                    continue

                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, float(value), year_str))
                total_saved += 1

        conn.commit()

        if skipped:
            print(f"Nicht gematchte Länder: {sorted(skipped)}")
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
