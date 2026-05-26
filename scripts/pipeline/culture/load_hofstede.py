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
    print("Registriere Quelle 'HOFSTEDE'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Hofstede Cultural Dimensions', 'HOFSTEDE', 'https://geerthofstede.com', 'Geert Hofstede 6 Cultural Dimensions Model Data'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", ('HOFSTEDE',))
        source_id = cur.fetchone()[0]

    print(f"Source ID für HOFSTEDE ist {source_id}")

    indicators_meta = [
        ('HOFSTEDE:pdi', 'Power Distance Index', 'score', 'Culture'),
        ('HOFSTEDE:idv', 'Individualism', 'score', 'Culture'),
        ('HOFSTEDE:mas', 'Masculinity', 'score', 'Culture'),
        ('HOFSTEDE:uai', 'Uncertainty Avoidance', 'score', 'Culture'),
        ('HOFSTEDE:lto', 'Long-Term Orientation', 'score', 'Culture'),
        ('HOFSTEDE:ivr', 'Indulgence vs. Restraint', 'score', 'Culture')
    ]

    print("Registriere Indikator-Metadaten...")
    for code, name, unit, category in indicators_meta:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def get_iso_numeric_from_iso2(cur, iso2):
    cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_2 = %s", (iso2.upper().strip(),))
    result = cur.fetchone()
    return result[0] if result else None

def main():
    parser = argparse.ArgumentParser(description="Hofstede 6 Dimensions Data Loader Pipeline")
    parser.add_argument("file", help="Pfad zur Hofstede CSV/Excel Download Datei")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Fehler: Datei {args.file} existiert nicht.")
        sys.exit(1)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print(f"Lese Hofstede-Daten von {args.file}...")
        if args.file.endswith('.xlsx') or args.file.endswith('.xls'):
            df = pd.read_excel(args.file)
        else:
            df = pd.read_csv(args.file, sep=None, engine='python')

        df.columns = [c.strip().lower() for c in df.columns]

        iso2_col = None
        for col in df.columns:
            if 'iso' in col or 'code' in col or col == 'iso2' or col == 'cc':
                iso2_col = col
                break

        if not iso2_col:
            if 'iso2' in df.columns:
                iso2_col = 'iso2'
            else:
                print("Warnung: Keine eindeutige ISO2 Spalte gefunden. Erwarte Spalte 'iso2'.")
                df['iso2'] = df['country'].str[:2]
                iso2_col = 'iso2'

        indicator_cols = {
            'pdi': 'HOFSTEDE:pdi',
            'idv': 'HOFSTEDE:idv',
            'mas': 'HOFSTEDE:mas',
            'uai': 'HOFSTEDE:uai',
            'lto': 'HOFSTEDE:lto',
            'ltowvs': 'HOFSTEDE:lto',  # Häufiger Alias im Download-File
            'ivr': 'HOFSTEDE:ivr'
        }

        print("Starte Datenimport...")

        for col_name, indicator_code in indicator_cols.items():
            if col_name not in df.columns:
                continue

            print(f"Importiere Indikator: {indicator_code}...")
            count = 0

            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            valid_rows = df[df[col_name].notna() & df[iso2_col].notna()]

            iso_cache = {}

            for _, row in valid_rows.iterrows():
                iso2 = str(row[iso2_col]).upper().strip()
                if len(iso2) != 2:
                    continue

                val = float(row[col_name])

                if iso2 not in iso_cache:
                    iso_cache[iso2] = get_iso_numeric_from_iso2(cur, iso2)

                iso_numeric = iso_cache[iso2]

                if not iso_numeric:
                    continue

                cur.execute("""
                    INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, 'static', 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, val))
                count += 1

            conn.commit()
            print(f"Indikator {indicator_code} abgeschlossen. {count} Datensätze verarbeitet.")

    except Exception as e:
        conn.rollback()
        print(f"Kritischer Fehler während des Hofstede Imports: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
        print("Datenbankverbindung geschlossen.")

if __name__ == "__main__":
    main()