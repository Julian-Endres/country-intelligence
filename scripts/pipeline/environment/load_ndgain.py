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
    print("Registriere Quelle 'NDGAIN'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Notre Dame Global Adaptation Initiative', 'NDGAIN', 'https://gain.nd.edu', 'ND-GAIN Country Index measuring climate vulnerability and readiness'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", ('NDGAIN',))
        source_id = cur.fetchone()[0]

    print(f"Source ID für NDGAIN ist {source_id}")

    indicators_meta = [
        ('NDGAIN:gain', 'Overall ND-GAIN Score', 'score', 'Climate Risk'),
        ('NDGAIN:vulnerability', 'Climate Vulnerability Score', 'score', 'Climate Risk'),
        ('NDGAIN:readiness', 'Readiness Score', 'score', 'Climate Risk')
    ]

    print("Registriere Indikator-Metadaten...")
    for code, name, unit, category in indicators_meta:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def get_iso_numeric(cur, iso3):
    cur.execute("SELECT iso_numeric FROM countries WHERE iso_code_3 = %s", (iso3.upper().strip(),))
    result = cur.fetchone()
    return result[0] if result else None

def process_ndgain_wide_csv(cur, source_id, file_path, indicator_code):
    """
    ND-GAIN Downloads kommen als Wide-Format CSVs:
    Zeilen = Länder, Spalten = Jahre (1995–2023)
    """
    print(f"Verarbeite Datei {file_path} für Indikator {indicator_code}...")
    df = pd.read_csv(file_path)

    df.columns = [str(c).strip().lower() for c in df.columns]

    iso_col = None
    for col in df.columns:
        if col in ['iso3', 'iso', 'code', 'country code', 'id']:
            iso_col = col
            break

    if not iso_col:
        first_valid_val = df.iloc[:, 0].dropna().astype(str).tolist()
        if first_valid_val and len(first_valid_val[0]) == 3:
            iso_col = df.columns[0]
        else:
            print(f"Fehler: Keine ISO3-Spalte in {file_path} gefunden.")
            return 0

    year_cols = []
    for col in df.columns:
        try:
            year = int(float(col))
            if 1995 <= year <= 2023:
                year_cols.append((col, str(year)))
        except ValueError:
            continue

    if not year_cols:
        print(f"Warnung: Keine Jahres-Spalten (1995-2023) gefunden in {file_path}.")
        return 0

    count = 0
    iso_cache = {}

    for _, row in df.iterrows():
        iso3 = str(row[iso_col]).upper().strip()
        if len(iso3) != 3:
            continue

        if iso3 not in iso_cache:
            iso_cache[iso3] = get_iso_numeric(cur, iso3)

        iso_numeric = iso_cache[iso3]
        if not iso_numeric:
            continue

        for orig_col, year_str in year_cols:
            val_raw = row[orig_col]
            try:
                val = float(val_raw)
                if pd.isna(val):
                    continue
            except (ValueError, TypeError):
                continue

            cur.execute("""
                INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                VALUES (%s, %s, %s, %s, %s, 'A')
                ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
            """, (iso_numeric, indicator_code, source_id, val, year_str))
            count += 1

    return count

def main():
    parser = argparse.ArgumentParser(description="ND-GAIN Country Index Data Loader Pipeline")
    parser.add_argument("--gain", help="Pfad zur Gesamt-Score Datei (gain.csv)")
    parser.add_argument("--vulnerability", help="Pfad zur Vulnerability Datei (vulnerability.csv)")
    parser.add_argument("--readiness", help="Pfad zur Readiness Datei (readiness.csv)")
    args = parser.parse_args()

    if not (args.gain or args.vulnerability or args.readiness):
        print("Fehler: Bitte mindestens ein CSV angeben (--gain, --vulnerability, --readiness).")
        sys.exit(1)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        if args.gain:
            cnt = process_ndgain_wide_csv(cur, source_id, args.gain, 'NDGAIN:gain')
            conn.commit()
            print(f"NDGAIN:gain abgeschlossen. {cnt} Datensätze verarbeitet.")

        if args.vulnerability:
            cnt = process_ndgain_wide_csv(cur, source_id, args.vulnerability, 'NDGAIN:vulnerability')
            conn.commit()
            print(f"NDGAIN:vulnerability abgeschlossen. {cnt} Datensätze verarbeitet.")

        if args.readiness:
            cnt = process_ndgain_wide_csv(cur, source_id, args.readiness, 'NDGAIN:readiness')
            conn.commit()
            print(f"NDGAIN:readiness abgeschlossen. {cnt} Datensätze verarbeitet.")

    except Exception as e:
        conn.rollback()
        print(f"Kritischer Fehler: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
        print("Datenbankverbindung geschlossen.")

if __name__ == "__main__":
    main()