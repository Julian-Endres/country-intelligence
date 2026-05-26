import os
import psycopg2
import pandas as pd
import argparse
from dotenv import load_dotenv

load_dotenv()

# ── Konfiguration ────────────────────────────────────────────────────────────

# Missing-Codes in WVS – alle als NaN behandeln
MISSING_CODES = [-1, -2, -3, -4, -5]

# Variablen die wir laden (csv_spalte, indicator_code, name, category)
VARIABLES = [
    # Inglehart-Welzel Indizes (bereits aggregiert)
    ("tradrat5",  "WVS:tradrat5",   "Traditional vs. Secular-Rational Values",     "Culture & Identity"),
    ("TradAgg",   "WVS:tradagg",    "Traditional Values Aggregate",                 "Culture & Identity"),
    ("SurvSAgg",  "WVS:survsagg",   "Survival vs. Self-Expression Aggregate",       "Culture & Identity"),

    # Block A – Perceptions of Life
    ("A008",  "WVS:A008",  "Feeling of Happiness",                                 "Culture & Identity"),
    ("A165",  "WVS:A165",  "Interpersonal Trust",                                  "Culture & Identity"),
    ("A001",  "WVS:A001",  "Importance of Family",                                 "Culture & Identity"),
    ("A002",  "WVS:A002",  "Importance of Friends",                                "Culture & Identity"),
    ("A006",  "WVS:A006",  "Importance of Religion",                               "Culture & Identity"),

    # Block E – Politics & Society
    ("E035",      "WVS:E035",      "Income Equality vs. Incentives",               "Politics & Governance"),
    ("E069_01",   "WVS:E069_01",   "Confidence: Churches",                         "Politics & Governance"),
    ("E069_02",   "WVS:E069_02",   "Confidence: Armed Forces",                     "Politics & Governance"),
    ("E069_07",   "WVS:E069_07",   "Confidence: Government",                       "Politics & Governance"),
    ("E069_11",   "WVS:E069_11",   "Confidence: Major Companies",                  "Politics & Governance"),
    ("E069_12",   "WVS:E069_12",   "Confidence: Environmental Organizations",      "Politics & Governance"),

    # Block F – Religion & Morale
    ("F034",  "WVS:F034",  "Self-identification as Religious Person",              "Culture & Identity"),
    ("F063",  "WVS:F063",  "Importance of God in Life",                            "Culture & Identity"),
    ("F118",  "WVS:F118",  "Homosexuality Justifiable",                            "Culture & Identity"),
    ("F120",  "WVS:F120",  "Abortion Justifiable",                                 "Culture & Identity"),
    ("F121",  "WVS:F121",  "Divorce Justifiable",                                  "Culture & Identity"),

    # Block D – Family & Gender
    ("D006",  "WVS:D006",  "Men Make Better Political Leaders",                    "Culture & Identity"),
    ("D019",  "WVS:D019",  "University More Important for Boy than Girl",          "Culture & Identity"),
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
    print("Registriere Quelle 'WVS'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('World Values Survey', 'WVS', 'https://www.worldvaluessurvey.org',
          'Cross-national survey of values, beliefs and attitudes 1981-2022'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'WVS'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    for _, code, name, category in VARIABLES:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, source_id, category)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, source_id, category))

    return source_id

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="World Values Survey Data Loader")
    parser.add_argument("file", help="Pfad zur WVS CSV Datei (Individual-Level)")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        print(f"Lese WVS CSV von {args.file}...")
        print("(Das kann einen Moment dauern – große Datei)")

        # Nur benötigte Spalten laden
        needed_cols = ["COUNTRY_ALPHA", "S020"] + [v[0] for v in VARIABLES]
        # Nur Spalten laden die tatsächlich in der CSV vorhanden sind
        all_cols = pd.read_csv(args.file, nrows=0).columns.tolist()
        load_cols = [c for c in needed_cols if c in all_cols]
        missing = [c for c in needed_cols if c not in all_cols]
        if missing:
            print(f"Warnung: Folgende Spalten nicht in CSV gefunden: {missing}")

        df = pd.read_csv(args.file, usecols=load_cols, low_memory=False)
        print(f"{len(df)} Zeilen geladen.")

        # Missing-Codes als NaN setzen
        df.replace(MISSING_CODES, pd.NA, inplace=True)

        # Erhebungsjahr bereinigen
        df["S020"] = pd.to_numeric(df["S020"], errors="coerce")
        df = df.dropna(subset=["COUNTRY_ALPHA", "S020"])
        df["S020"] = df["S020"].astype(int).astype(str)

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        country_map = {row[1]: row[0] for row in cur.fetchall()}

        # Aggregation: Mittelwert pro Land + Erhebungsjahr
        print("Aggregiere auf Länderebene...")
        var_cols = [v[0] for v in VARIABLES if v[0] in df.columns]
        for col in var_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        grouped = df.groupby(["COUNTRY_ALPHA", "S020"])[var_cols].mean().reset_index()
        print(f"{len(grouped)} Land-Jahr Kombinationen nach Aggregation.")

        # In DB laden
        total_saved = 0
        skipped_countries = set()

        for _, row in grouped.iterrows():
            iso3 = str(row["COUNTRY_ALPHA"]).upper().strip()
            year = str(row["S020"])

            iso_numeric = country_map.get(iso3)
            if not iso_numeric:
                skipped_countries.add(iso3)
                continue

            for csv_col, indicator_code, _, _ in VARIABLES:
                if csv_col not in row.index:
                    continue
                value = row[csv_col]
                if pd.isna(value):
                    continue

                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, %s, %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, indicator_code, source_id, round(float(value), 6), year))
                total_saved += 1

            if total_saved % 5000 == 0 and total_saved > 0:
                conn.commit()
                print(f"{total_saved} Datenpunkte gespeichert...")

        conn.commit()

        if skipped_countries:
            print(f"Nicht gematchte Länder-Codes: {sorted(skipped_countries)}")

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
