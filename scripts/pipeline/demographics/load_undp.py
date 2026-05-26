import os
import sys
import argparse
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'UNDP'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('UN Development Programme', 'UNDP', 'https://hdr.undp.org', 'Human Development Index and related metrics'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", ('UNDP',))
        source_id = cur.fetchone()[0]

    indicators_meta = [
        ('UNDP:hdi', 'Human Development Index', 'index 0-1', 'Human Development'),
        ('UNDP:gii', 'Gender Inequality Index', 'index 0-1', 'Gender Inequality'),
        ('UNDP:le', 'Life Expectancy', 'years', 'Health'),
        ('UNDP:eys', 'Expected Years of Schooling', 'years', 'Education'),
        ('UNDP:mys', 'Mean Years of Schooling', 'years', 'Education'),
        ('UNDP:gnipc', 'GNI per capita', 'USD PPP', 'Economic'),
        ('UNDP:mpi', 'Multidimensional Poverty Index', 'index 0-1', 'Poverty'),
        ('UNDP:mpi_intensity', 'MPI Intensity of Deprivation', '%', 'Poverty'),
        ('UNDP:mpi_headcount', 'MPI Headcount Ratio', '%', 'Poverty'),
        ('UNDP:mpi_child_mortality', 'MPI Deprivation: Child Mortality', '%', 'Poverty'),
        ('UNDP:mpi_nutrition', 'MPI Deprivation: Nutrition', '%', 'Poverty'),
        ('UNDP:mpi_schooling', 'MPI Deprivation: Years of Schooling', '%', 'Poverty'),
        ('UNDP:mpi_attendance', 'MPI Deprivation: School Attendance', '%', 'Poverty'),
        ('UNDP:mpi_sanitation', 'MPI Deprivation: Sanitation', '%', 'Poverty'),
        ('UNDP:mpi_drinking_water', 'MPI Deprivation: Drinking Water', '%', 'Poverty'),
        ('UNDP:mpi_cooking_fuel', 'MPI Deprivation: Cooking Fuel', '%', 'Poverty'),
        ('UNDP:mpi_housing', 'MPI Deprivation: Housing', '%', 'Poverty'),
        ('UNDP:mpi_electricity', 'MPI Deprivation: Electricity', '%', 'Poverty'),
        ('UNDP:mpi_assets', 'MPI Deprivation: Assets', '%', 'Poverty'),
    ]

    for code, name, unit, category in indicators_meta:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def load_data(file_path):
    print(f"Lese CSV-Datei von {file_path}...")
    df = pd.read_csv(
        file_path,
        sep=';',
        on_bad_lines='skip',
        engine='python'
    )
    return df

def main():
    parser = argparse.ArgumentParser(description="UNDP Data Loader Pipeline")
    parser.add_argument("file", help="Pfad zur UNDP CSV Datei")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        df = load_data(args.file)

        print("Starte Datenimport...")

        indicator_map = {
            'hdi': 'UNDP:hdi',
            'gii': 'UNDP:gii',
            'mpi': 'UNDP:mpi',
            'le': 'UNDP:le',
            'eys': 'UNDP:eys',
            'mys': 'UNDP:mys',
            'gnipc': 'UNDP:gnipc',
            'mpi_value':      'UNDP:mpi',
            'mpi_intensity':  'UNDP:mpi_intensity',
            'mpi_headcount':  'UNDP:mpi_headcount',
            'child_mortality': 'UNDP:mpi_child_mortality',
            'nutrition':      'UNDP:mpi_nutrition',
            'years_of_schooling': 'UNDP:mpi_schooling',
            'school_attendance':  'UNDP:mpi_attendance',
            'sanitation':     'UNDP:mpi_sanitation',
            'drinking_water': 'UNDP:mpi_drinking_water',
            'cooking_fuel':   'UNDP:mpi_cooking_fuel',
            'housing':        'UNDP:mpi_housing',
            'electricity':    'UNDP:mpi_electricity',
            'assets':         'UNDP:mpi_assets',
        }

        iso_cache = {}
        total_saved = 0

        for _, row in df.iterrows():
            iso3 = str(row['countryIsoCode']).upper().strip()
            indicator_csv_code = str(row['indicatorCode']).lower().strip()

            if indicator_csv_code not in indicator_map:
                continue

            internal_code = indicator_map[indicator_csv_code]
            if pd.isna(row['year']):
                continue
            year = str(int(float(row['year'])))
            val = float(row['value'])

            if iso3 not in iso_cache:
                cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso3,))
                res = cur.fetchone()
                iso_cache[iso3] = res[0] if res else None

            iso_numeric = iso_cache[iso3]

            if iso_numeric:
                cur.execute("""
                    INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, internal_code, source_id, val, year))
                total_saved += 1

            if total_saved % 10000 == 0 and total_saved > 0:
                conn.commit()
                print(f"{total_saved} Datenpunkte gespeichert...")

        conn.commit()
        print(f"Import abgeschlossen. {total_saved} Datenpunkte geladen.")

    except Exception as e:
        conn.rollback()
        print(f"Fehler: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()