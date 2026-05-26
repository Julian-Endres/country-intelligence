import os
import time
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────
START_YEAR = 2000
END_YEAR   = 2023
BASE_URL   = "https://archive-api.open-meteo.com/v1/archive"

# Variablen die wir laden – (api_name, indicator_code, name, unit, aggregation)
# aggregation: 'mean' für Temperatur, 'sum' für Niederschlag/Sonne
VARIABLES = [
    ("temperature_2m_mean",  "OPENMETEO:temp_mean",   "Mean Annual Temperature",    "°C",   "mean"),
    ("precipitation_sum",    "OPENMETEO:precip_sum",  "Annual Precipitation",        "mm",   "sum"),
    ("sunshine_duration",    "OPENMETEO:sunshine",    "Annual Sunshine Duration",    "hours","sum"),
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
    print("Registriere Quelle 'OPENMETEO'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Open-Meteo ERA5', 'OPENMETEO', 'https://open-meteo.com',
          'Historical climate reanalysis data (ERA5) – temperature, precipitation, sunshine'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'OPENMETEO'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, code, name, unit, _ in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, 'Geography & Environment'))

    return source_id

# ── API Call ─────────────────────────────────────────────────────────────────
def fetch_climate_data(lat, lon, year):
    """
    Lädt tägliche Daten für ein Jahr und gibt Jahresaggregate zurück.
    Gibt dict {api_var: aggregated_value} zurück oder None bei Fehler.
    """
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": f"{year}-01-01",
        "end_date":   f"{year}-12-31",
        "daily":      ",".join([v[0] for v in VARIABLES]),
        "timezone":   "UTC"
    }

    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        if r.status_code != 200:
            return None

        data = r.json()
        daily = data.get("daily", {})

        results = {}
        for api_var, _, _, _, agg in VARIABLES:
            values = daily.get(api_var, [])
            values_clean = [v for v in values if v is not None]
            if not values_clean:
                continue
            if agg == "mean":
                results[api_var] = round(sum(values_clean) / len(values_clean), 3)
            elif agg == "sum":
                results[api_var] = round(sum(values_clean), 1)

        return results

    except Exception as e:
        print(f"    API Fehler: {e}")
        return None

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Alle Länder mit Koordinaten laden
        cur.execute("""
            SELECT iso_numeric, name, latitude, longitude
            FROM countries
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY name
        """)
        countries = cur.fetchall()
        print(f"{len(countries)} Länder mit Koordinaten gefunden.")

        # Bereits geladene Kombinationen prüfen (für Resume)
        cur.execute("""
            SELECT DISTINCT iso_numeric, time_period
            FROM indicators
            WHERE indicator_code = 'OPENMETEO:temp_mean'
        """)
        already_loaded = set((r[0], r[1]) for r in cur.fetchall())
        print(f"{len(already_loaded)} bereits geladene Land-Jahr Kombinationen.")

        total_saved = 0
        years = list(range(START_YEAR, END_YEAR + 1))

        for i, (iso_numeric, name, lat, lon) in enumerate(countries):
            print(f"[{i+1}/{len(countries)}] {name}...")
            country_saved = 0

            for year in years:
                if (iso_numeric, str(year)) in already_loaded:
                    continue

                results = fetch_climate_data(lat, lon, year)
                if not results:
                    continue

                for api_var, indicator_code, _, _, _ in VARIABLES:
                    value = results.get(api_var)
                    if value is None:
                        continue

                    cur.execute("""
                        INSERT INTO indicators
                            (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                        VALUES (%s, %s, %s, %s, %s, 'A')
                        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                    """, (iso_numeric, indicator_code, source_id, value, str(year)))
                    total_saved += 1
                    country_saved += 1

                time.sleep(0.15)  # Rate Limit respektieren

            conn.commit()
            print(f"    {country_saved} Datenpunkte gespeichert. Total: {total_saved}")

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
