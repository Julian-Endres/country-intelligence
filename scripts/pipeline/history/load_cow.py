import os
import psycopg2
import pandas as pd
import argparse
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# COW Ländercodes → ISO3 Mapping (COW nutzt eigene numerische Codes)
# Wichtigste Mappings – COW ccode → ISO3
COW_TO_ISO3 = {
    2: "USA", 20: "CAN", 40: "CUB", 41: "HTI", 42: "DOM", 51: "JAM",
    52: "TTO", 53: "BRB", 54: "DMA", 55: "GRD", 56: "ATG", 57: "VCT",
    58: "LCA", 60: "MEX", 70: "BLZ", 80: "GTM", 90: "HND", 91: "SLV",
    92: "NIC", 93: "CRI", 94: "PAN", 95: "COL", 100: "VEN", 101: "GUY",
    110: "ECU", 115: "PER", 130: "BRA", 135: "BOL", 140: "PRY", 145: "CHL",
    150: "ARG", 155: "URY", 200: "GBR", 205: "IRL", 210: "NLD", 211: "BEL",
    212: "LUX", 220: "FRA", 225: "CHE", 230: "ESP", 235: "PRT", 240: "HAN",
    245: "BAV", 255: "DEU", 260: "DEU", 265: "DEU", 267: "DEU", 269: "DEU",
    270: "DEU", 280: "HUN", 290: "POL", 300: "AUT", 305: "AUT", 310: "CZE",
    315: "SVK", 317: "SVK", 325: "ITA", 327: "ITA", 338: "MLT", 339: "ALB",
    340: "SRB", 341: "MNE", 343: "SVN", 344: "HRV", 345: "YUG", 346: "BIH",
    347: "MKD", 349: "KOS", 350: "GRC", 352: "CYP", 355: "BGR", 360: "ROU",
    365: "RUS", 366: "EST", 367: "LVA", 368: "LTU", 369: "FIN", 370: "BLR",
    371: "UKR", 372: "MDA", 373: "GEO", 374: "ARM", 375: "AZE", 380: "SWE",
    385: "NOR", 390: "DNK", 395: "ISL", 402: "CAP", 404: "GNB", 411: "EQG",
    420: "GMB", 432: "MLI", 433: "SEN", 434: "BEN", 435: "MRT", 436: "NER",
    437: "CIV", 438: "GIN", 439: "BFA", 450: "LBR", 451: "SLE", 452: "GHA",
    461: "TGO", 471: "CMR", 475: "NGA", 481: "GAB", 482: "CAF", 483: "COD",
    484: "COG", 490: "UGA", 500: "KEN", 501: "TZA", 510: "SOM", 516: "BDI",
    517: "RWA", 520: "ETH", 522: "ERI", 530: "DJI", 540: "MOZ", 541: "MWI",
    551: "ZMB", 552: "ZWE", 553: "BWA", 560: "ZAF", 565: "NAM", 570: "LSO",
    571: "SWZ", 572: "MDG", 580: "AGO", 600: "MAR", 615: "ALG", 616: "TUN",
    620: "LBY", 625: "SDN", 626: "SSD", 630: "IRN", 640: "TUR", 645: "IRQ",
    651: "EGY", 652: "SYR", 660: "LBN", 663: "JOR", 666: "ISR", 670: "SAU",
    678: "YEM", 680: "YEM", 690: "KWT", 694: "BHR", 696: "QAT", 698: "ARE",
    700: "AFG", 701: "PAK", 704: "BGD", 710: "CHN", 711: "TWN", 712: "MNG",
    713: "KOR", 731: "PRK", 732: "KOR", 740: "JPN", 750: "IND", 760: "BHU",
    770: "PAK", 771: "BGD", 775: "MMR", 780: "LKA", 790: "NPL", 800: "THA",
    811: "KHM", 812: "LAO", 816: "VNM", 817: "VNM", 820: "MYS", 830: "SGP",
    840: "PHL", 850: "IDN", 860: "TLS", 900: "AUS", 910: "PNG", 920: "NZL",
    935: "VUT", 940: "SLB", 946: "FJI",
}

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_source_and_metadata(cur):
    print("Registriere Quelle 'COW'...")
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, ('Correlates of War Project', 'COW',
          'https://correlatesofwar.org',
          'Interstate and intrastate war data 1816–2007'))

    result = cur.fetchone()
    if result:
        source_id = result[0]
    else:
        cur.execute("SELECT id FROM sources WHERE short_code = 'COW'")
        source_id = cur.fetchone()[0]

    print(f"Source ID: {source_id}")

    indicators = [
        ("COW:interstate_wars",  "Interstate Wars Participated",  "count", "History & Collective Memory"),
        ("COW:intrastate_wars",  "Intrastate Wars Participated",  "count", "History & Collective Memory"),
        ("COW:total_wars",       "Total Wars Participated",        "count", "History & Collective Memory"),
        ("COW:battle_deaths",    "Battle Deaths (Interstate Wars)","count", "History & Collective Memory"),
    ]

    for code, name, unit, category in indicators:
        cur.execute("""
            INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code) DO NOTHING
        """, (code, name, unit, source_id, category))

    return source_id

def main():
    parser = argparse.ArgumentParser(description="COW War Data Loader")
    parser.add_argument("--interstate", help="Pfad zur Inter-StateWarData_v4.0.csv")
    parser.add_argument("--intrastate", help="Pfad zur Intra-StateWarData_v5.1.csv")
    args = parser.parse_args()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        source_id = setup_source_and_metadata(cur)
        conn.commit()

        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
        iso3_map = {row[1]: row[0] for row in cur.fetchall()}

        def ccode_to_iso_numeric(ccode):
            iso3 = COW_TO_ISO3.get(int(ccode))
            if iso3:
                return iso3_map.get(iso3)
            return None

        total_saved = 0

        # Interstate Wars
        if args.interstate:
            print("Lade Interstate Wars...")
            df = pd.read_csv(args.interstate)

            # Aggregieren: Kriege pro Land pro Jahrzehnt + Battle Deaths
            war_counts = defaultdict(int)
            battle_deaths = defaultdict(int)

            for _, row in df.iterrows():
                ccode = row.get('ccode')
                year = row.get('StartYear1')
                deaths = row.get('BatDeath', 0)

                if pd.isna(ccode) or pd.isna(year):
                    continue

                iso_numeric = ccode_to_iso_numeric(ccode)
                if not iso_numeric:
                    continue

                year_str = str(int(year))
                war_counts[(iso_numeric, year_str)] += 1
                if not pd.isna(deaths) and deaths > 0:
                    battle_deaths[(iso_numeric, year_str)] += int(deaths)

            for (iso_numeric, year_str), count in war_counts.items():
                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, 'COW:interstate_wars', %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, source_id, float(count), year_str))
                total_saved += 1

            for (iso_numeric, year_str), deaths in battle_deaths.items():
                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, 'COW:battle_deaths', %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, source_id, float(deaths), year_str))
                total_saved += 1

            conn.commit()
            print(f"Interstate Wars geladen. Total: {total_saved}")

        # Intrastate Wars
        if args.intrastate:
            print("Lade Intrastate Wars...")
            df2 = pd.read_csv(args.intrastate)

            intra_counts = defaultdict(int)

            for _, row in df2.iterrows():
                ccode = row.get('ccode')
                year = row.get('StartYear1')

                if pd.isna(ccode) or pd.isna(year):
                    continue

                iso_numeric = ccode_to_iso_numeric(ccode)
                if not iso_numeric:
                    continue

                year_str = str(int(year))
                intra_counts[(iso_numeric, year_str)] += 1

            for (iso_numeric, year_str), count in intra_counts.items():
                cur.execute("""
                    INSERT INTO indicators
                        (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
                    VALUES (%s, 'COW:intrastate_wars', %s, %s, %s, 'A')
                    ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
                """, (iso_numeric, source_id, float(count), year_str))
                total_saved += 1

            conn.commit()
            print(f"Intrastate Wars geladen. Total: {total_saved}")

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
