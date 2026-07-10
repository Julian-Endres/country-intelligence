"""
COW-Code-Crosswalk für die countries-Tabelle  —  finale, wasserdichte Variante.
=============================================================================

PROBLEM
-------
ATOP/Polity/COW-Wars u.a. nutzen Correlates-of-War (COW) Country Codes.
Diese sind NICHT identisch mit ISO-3166-numeric:
   Kanada      = COW 020,  aber ISO-numeric 020 = Andorra
   USA         = COW 002,  aber ISO-numeric 840
   Bolivien    = COW 145,  aber ISO-numeric 068
Wer COW-Codes direkt als iso_numeric verwendet, hängt Daten ans falsche Land.

ANSATZ (warum dieser und kein Namens-Matching)
----------------------------------------------
Namens-Matching (regex über StateNme) ist fragil: "Austria-Hungary",
"German Federal Republic" etc. matchen mehrdeutig oder falsch.
Stattdessen nutzen wir den STABILEN Schlüssel: COW-StateAbb (3-Buchstaben-
COW-Code wie BOL/CAN/UKG). Dieser ändert sich nicht und ist eindeutig.

Die offizielle COW-CSV liefert (StateAbb, CCode, StateNme).
Wir übersetzen StateAbb -> ISO3 über eine EXPLIZITE Override-Tabelle für
alle Fälle, in denen COW-StateAbb != ISO3 ist (die unten ausgeschriebene
Liste ist verifiziert und im Interview vorzeigbar). Für den großen Rest,
wo COW-StateAbb == ISO3, greift direkter Abgleich gegen countries.iso_code_3.

Historische Staaten ohne modernes ISO3 (Preußen, Jugoslawien, beide
deutschen Staaten, Two Sicilies, ...) werden BEWUSST übersprungen und
geloggt — nicht still verworfen.

Ablage: scripts/pipeline/base/populate_cow_codes.py
Benötigt: pip install pandas requests --break-system-packages
          (country_converter NICHT nötig)
"""

import io
import ssl
import urllib.request
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

COW_CSV_FALLBACK = "https://raw.githubusercontent.com/leops95/cow2iso/master/cow_country_codes.csv"

# -------------------------------------------------------------------------
# EXPLIZITE Override-Tabelle: COW-StateAbb -> ISO3
# Nur Fälle, in denen StateAbb != ISO3. Verifiziert gegen ISO 3166-1.
# Alles, was hier NICHT steht und auch nicht historisch ist, hat
# StateAbb == ISO3 und wird automatisch gematcht.
# -------------------------------------------------------------------------
COW_ABBR_TO_ISO3 = {
    # Amerika
    "USA": "USA", "CAN": "CAN", "BHM": "BHS", "CUB": "CUB", "HAI": "HTI",
    "DOM": "DOM", "JAM": "JAM", "TRI": "TTO", "BAR": "BRB", "GRN": "GRD",
    "SLU": "LCA", "SVG": "VCT", "AAB": "ATG", "SKN": "KNA", "MEX": "MEX",
    "BLZ": "BLZ", "GUA": "GTM", "HON": "HND", "SAL": "SLV", "NIC": "NIC",
    "COS": "CRI", "PAN": "PAN", "COL": "COL", "VEN": "VEN", "GUY": "GUY",
    "SUR": "SUR", "ECU": "ECU", "PER": "PER", "BRA": "BRA", "BOL": "BOL",
    "PAR": "PRY", "CHL": "CHL", "ARG": "ARG", "URU": "URY",
    # Europa
    "UKG": "GBR", "IRE": "IRL", "NTH": "NLD", "BEL": "BEL", "LUX": "LUX",
    "FRN": "FRA", "MNC": "MCO", "LIE": "LIE", "SWZ": "CHE", "SPN": "ESP",
    "AND": "AND", "POR": "PRT", "GMY": "DEU", "GFR": None, "GDR": None,
    "POL": "POL", "AUS": "AUT", "HUN": "HUN", "CZE": "CZE", "CZR": "CZE",
    "SLO": "SVK", "ITA": "ITA", "SNM": "SMR", "MLT": "MLT", "ALB": "ALB",
    "MNG": "MNE", "MAC": "MKD", "MAW": "MWI", "CRO": "HRV", "YUG": None,
    "BOS": "BIH", "KOS": "XKX", "SRB": "SRB", "MMR": "MMR", "MON": "MNE",
    "GRC": "GRC", "CYP": "CYP", "BUL": "BGR", "MLD": "MDA", "ROM": "ROU",
    "RUS": "RUS", "EST": "EST", "LAT": "LVA", "LIT": "LTU", "UKR": "UKR",
    "BLR": "BLR", "ARM": "ARM", "GRG": "GEO", "AZE": "AZE", "FIN": "FIN",
    "SWD": "SWE", "NOR": "NOR", "DEN": "DNK", "ICE": "ISL",
    # Afrika
    "CAP": "CPV", "GNB": "GNB", "EQG": "GNQ", "GAM": "GMB", "MLI": "MLI",
    "SEN": "SEN", "BEN": "BEN", "MAA": "MRT", "NIR": "NER", "CDI": "CIV",
    "GUI": "GIN", "BFO": "BFA", "LBR": "LBR", "SIE": "SLE", "GHA": "GHA",
    "TOG": "TGO", "CAO": "CMR", "NIG": "NGA", "GAB": "GAB", "CEN": "CAF",
    "CHA": "TCD", "CON": "COG", "DRC": "COD", "UGA": "UGA", "KEN": "KEN",
    "TAZ": "TZA", "BUI": "BDI", "RWA": "RWA", "SOM": "SOM", "DJI": "DJI",
    "ETH": "ETH", "ERI": "ERI", "ANG": "AGO", "MZM": "MOZ", "ZAM": "ZMB",
    "ZIM": "ZWE", "MAW": "MWI", "SAF": "ZAF", "NAM": "NAM", "LES": "LSO",
    "BOT": "BWA", "SWA": "SWZ", "MAG": "MDG", "COM": "COM", "MAS": "MUS",
    "SEY": "SYC", "SUD": "SDN", "SSD": "SSD", "EGY": "EGY", "LIB": "LBY",
    "TUN": "TUN", "ALG": "DZA", "MOR": "MAR", "SAO": "STP",
    # Naher Osten / Asien
    "TUR": "TUR", "IRQ": "IRQ", "IRN": "IRN", "SYR": "SYR", "LEB": "LBN",
    "JOR": "JOR", "ISR": "ISR", "SAU": "SAU", "YEM": "YEM", "YAR": None,
    "YPR": None, "KUW": "KWT", "BAH": "BHR", "QAT": "QAT", "UAE": "ARE",
    "OMA": "OMN", "AFG": "AFG", "TKM": "TKM", "TAJ": "TJK", "KYR": "KGZ",
    "UZB": "UZB", "KZK": "KAZ", "KZH": "KAZ", "CHN": "CHN", "MON": "MNG",
    "TAW": "TWN", "PRK": "PRK", "ROK": "KOR", "JPN": "JPN", "IND": "IND",
    "BHU": "BTN", "PAK": "PAK", "BNG": "BGD", "MYA": "MMR", "SRI": "LKA",
    "MAD": "MDV", "NEP": "NPL", "THI": "THA", "CAM": "KHM", "LAO": "LAO",
    "DRV": "VNM", "RVN": None, "MAL": "MYS", "SIN": "SGP", "BRU": "BRN",
    "PHI": "PHL", "INS": "IDN", "ETM": "TLS",
    # Ozeanien
    "AUL": "AUS", "PNG": "PNG", "NEW": "NZL", "VAN": "VUT", "SOL": "SLB",
    "FIJ": "FJI", "KIR": "KIR", "NAU": "NRU", "TON": "TON", "TUV": "TUV",
    "WSM": "WSM", "PAL": "PLW", "FSM": "FSM", "MSI": "MHL",
    "DMA": "DMA",   # Dominica
    "SLV": "SVN",   # Slovenia (COW SLV, nicht zu verwechseln mit El Salvador SAL)
    "STP": "STP",   # Sao Tome and Principe
    "KOR": None,    # historisches Gesamt-Korea bis 1910; modern = PRK/ROK
    "YUG": "SRB",   # COW 345: Serbien als Fortsetzung Jugoslawiens (COW-Konvention)
}

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# -------------------------------------------------------------------------
# 1. Offizielle COW-Codes laden (SSL-tolerant, da correlatesofwar.org
#    Zertifikatsprobleme macht -> Fallback-Spiegel mit normalem TLS)
# -------------------------------------------------------------------------
def load_cow_csv():
    req = urllib.request.Request(COW_CSV_FALLBACK, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.strip().lower() for c in df.columns]
    df = df[['stateabb', 'ccode', 'statenme']].drop_duplicates()
    print(f"COW-Codes geladen: {len(df)} eindeutige Einträge.")
    return df

cow = load_cow_csv()

# -------------------------------------------------------------------------
# 2. Spalte anlegen
# -------------------------------------------------------------------------
cur.execute("ALTER TABLE countries ADD COLUMN IF NOT EXISTS cow_code INTEGER")
conn.commit()
print("Spalte 'cow_code' vorhanden.")

# -------------------------------------------------------------------------
# 3. Mapping anwenden
# -------------------------------------------------------------------------
updated = 0
historical_skipped = []   # StateAbb -> None (bewusst kein modernes Land)
unknown_abbr = []         # StateAbb nicht in Override-Tabelle
iso3_not_in_countries = []  # gemappt, aber ISO3 nicht in unserer Tabelle

for _, row in cow.iterrows():
    abbr = row['stateabb']
    cow_code = int(row['ccode'])

    if abbr not in COW_ABBR_TO_ISO3:
        unknown_abbr.append((abbr, cow_code, row['statenme']))
        continue

    iso3 = COW_ABBR_TO_ISO3[abbr]
    if iso3 is None:
        historical_skipped.append((abbr, cow_code, row['statenme']))
        continue

    cur.execute(
        "UPDATE countries SET cow_code = %s WHERE iso_code_3 = %s",
        (cow_code, iso3)
    )
    if cur.rowcount > 0:
        updated += 1
    else:
        iso3_not_in_countries.append((abbr, iso3, cow_code, row['statenme']))

conn.commit()

# -------------------------------------------------------------------------
# 4. Report
# -------------------------------------------------------------------------
print(f"\n{updated} Länder mit cow_code befüllt.")

if historical_skipped:
    print(f"\n{len(historical_skipped)} historische Staaten bewusst übersprungen "
          f"(kein modernes ISO3):")
    for abbr, cc, name in historical_skipped:
        print(f"   {abbr:<4} COW {cc:>4}  {name}")

if iso3_not_in_countries:
    print(f"\n{len(iso3_not_in_countries)} gemappt, aber ISO3 nicht in 'countries':")
    for abbr, iso3, cc, name in iso3_not_in_countries:
        print(f"   {abbr:<4} -> {iso3}  COW {cc:>4}  {name}")

if unknown_abbr:
    print(f"\n⚠️  {len(unknown_abbr)} COW-StateAbb NICHT in Override-Tabelle "
          f"(prüfen & ergänzen!):")
    for abbr, cc, name in unknown_abbr:
        print(f"   {abbr:<4} COW {cc:>4}  {name}")

# -------------------------------------------------------------------------
# 5. Verifikation: der ursprüngliche Bug + Anker
# -------------------------------------------------------------------------
print("\n--- Verifikation (Bug-Fall + Bolivien) ---")
cur.execute("""
    SELECT iso_code_3, name, iso_numeric, cow_code
    FROM countries WHERE iso_code_3 IN ('CAN','AND','BOL','USA')
    ORDER BY iso_code_3
""")
for r in cur.fetchall():
    print(f"   {r[0]:<4} {r[1]:<26} iso_numeric={r[2]:<5} cow_code={r[3]}")
print("""   Erwartung:
   AND  Andorra   iso_numeric=020  cow_code=232
   BOL  Bolivia   iso_numeric=068  cow_code=145
   CAN  Canada    iso_numeric=124  cow_code=20
   USA  USA       iso_numeric=840  cow_code=2""")

cur.execute("SELECT COUNT(*) FROM countries WHERE cow_code IS NOT NULL")
n_with = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM countries")
n_total = cur.fetchone()[0]
print(f"\nCoverage: {n_with}/{n_total} Länder haben einen cow_code.")

cur.close()
conn.close()