"""
load_new_sources_batch.py
Lädt alle neuen Quellen in einem Script.

Quellen:
- OWID CSVs (Bezugsweg OWID, Werte unter der Quelle des Urhebers): WHO Alkohol/Tabak/Drogen, UNODC Gefängnis/Mord,
  SIPRI Militärausgaben. Stand 24.11.2026 (CI-171). FSI/GITOC: seit 25.11.2026 eigene Loader
  load_fsi.py und load_gitoc.py (CI-177); hier nicht mehr aufgerufen.
- Fragile States Index (Excel)
- World Bank Stability & Secrecy (Excel)
- GI-TOC Global Organized Crime Index (Excel)
"""

import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── DB ───────────────────────────────────────────────────────────────────────

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

# ── Quellen-Definitionen ─────────────────────────────────────────────────────

SOURCES = {
    "FSI": (
        "Fragile States Index (Fund for Peace)",
        "https://fragilestatesindex.org",
        "12 conflict risk indicators per country 2006–2025"
    ),
    "GITOC": (
        "GI-TOC Global Organized Crime Index",
        "https://ocindex.net",
        "Organized crime criminality, criminal markets, resilience – 193 countries, 2021/2023/2025"
    ),
}

# ── OWID CSV Definitionen ────────────────────────────────────────────────────

# Regel 24.11.2026 (CI-171, #2): Präfix = Urheber, Bezugsweg OWID steht in indicator_metadata.reference.
# Die Werte gehören zur Quelle des Urhebers ("source"), nicht zu OWID_SOCIAL.
# Nicht mehr geladen (bewusst, 24.11.):
#   migration_stock, urban_share, youth_unemployment -> direkt über WB (SM.POP.TOTL, SP.URB.TOTL.IN.ZS, SL.UEM.1524.ZS)
#   poverty_3_day -> deprecated, Doppelung zu WB:SI.POV.DDAY (#8)
OWID_FILES = [
    {"path": "data/raw/health/owid_alcohol_consumption_per_capita.csv", "value_col": "Alcohol consumption",
     "indicator_code": "WHO:alcohol_per_capita", "source": "WHO",
     "name": "Alcohol Consumption per Capita", "unit": "liters pure alcohol", "category": "Health, Body & Behavior"},
    {"path": "data/raw/health/owid_alcohol_binge_drinking.csv",
     "value_col": "Alcohol, heavy episodic drinking (15+), drinkers only, past 30 days (%) - Sex: both sexes",
     "indicator_code": "WHO:binge_drinking", "source": "WHO",
     "name": "Binge Drinking Prevalence (15+)", "unit": "%", "category": "Health, Body & Behavior"},
    {"path": "data/raw/health/owid_tobacco_prevalence.csv",
     "value_col": "Age-standardized prevalence of current tobacco use among persons aged 15 years and older, by sex (%) - Both sexes",
     "indicator_code": "WHO:tobacco_prevalence", "source": "WHO",
     "name": "Tobacco Use Prevalence (15+)", "unit": "%", "category": "Health, Body & Behavior"},
    {"path": "data/raw/health/owid_drug_deaths_who.csv",
     "value_col": "Total deaths from mental and substance use disorders among both sexes",
     "indicator_code": "WHO:drug_deaths", "source": "WHO",
     "name": "Deaths from Substance Use Disorders", "unit": "deaths", "category": "Health, Body & Behavior"},
    {"path": "data/raw/governance/owid_prison_population_rate.csv", "value_col": "Prison population rate",
     "indicator_code": "UNODC:prison_rate", "source": "UNODC",
     "name": "Prison Population Rate (per 100k)", "unit": "per 100k", "category": "Politics & Governance"},
    {"path": "data/raw/governance/owid_prison_occupancy_capacity.csv", "value_col": "Prison capacity percent",
     "indicator_code": "UNODC:prison_occupancy", "source": "UNODC",
     "name": "Prison Occupancy Rate (% of capacity)", "unit": "%", "category": "Politics & Governance"},
    {"path": "data/raw/governance/owid_homicide_rate.csv", "value_col": "Homicide rate per 100,000 population",
     "indicator_code": "UNODC:homicide_rate", "source": "UNODC",
     "name": "Homicide Rate (per 100k)", "unit": "per 100k", "category": "Politics & Governance"},
    {"path": "data/raw/governance/owid_homicide_count.csv", "value_col": "Homicides",
     "indicator_code": "UNODC:homicide_count", "source": "UNODC",
     "name": "Homicide Count", "unit": "count", "category": "Politics & Governance"},
    # SIPRI über OWID: Code in der DB heißt SIPRI:milex_gdp (nicht OWID_SOCIAL:military_expenditure)
    {"path": "data/raw/governance/sipri_military_expenditure.csv", "value_col": "Military expenditure (% of GDP)",
     "indicator_code": "SIPRI:milex_gdp", "source": "SIPRI",
     "name": "Military Expenditure (% of GDP)", "unit": "% of GDP", "category": "Politics & Governance"},
]

# FSI Indikatoren
FSI_INDICATORS = {
    "Total":                          ("FSI:total",           "Fragile States Index – Total Score",              "score"),
    "C1: Security Apparatus":         ("FSI:c1_security",     "FSI – Security Apparatus",                        "score"),
    "C2: Factionalized Elites":       ("FSI:c2_elites",       "FSI – Factionalized Elites",                      "score"),
    "C3: Group Grievance":            ("FSI:c3_grievance",    "FSI – Group Grievance",                           "score"),
    "E1: Economy":                    ("FSI:e1_economy",      "FSI – Economy",                                   "score"),
    "E2: Economic Inequality":        ("FSI:e2_inequality",   "FSI – Economic Inequality",                       "score"),
    "E3: Human Flight and Brain Drain":("FSI:e3_brain_drain", "FSI – Human Flight and Brain Drain",              "score"),
    "P1: State Legitimacy":           ("FSI:p1_legitimacy",   "FSI – State Legitimacy",                          "score"),
    "P2: Public Services":            ("FSI:p2_services",     "FSI – Public Services",                           "score"),
    "P3: Human Rights":               ("FSI:p3_rights",       "FSI – Human Rights",                              "score"),
    "S1: Demographic Pressures":      ("FSI:s1_demographics", "FSI – Demographic Pressures",                     "score"),
    "S2: Refugees and IDPs":          ("FSI:s2_refugees",     "FSI – Refugees and IDPs",                         "score"),
    "X1: External Intervention":      ("FSI:x1_external",     "FSI – External Intervention",                     "score"),
}

# GI-TOC Indikatoren
GITOC_INDICATORS = {
    "Criminality avg.":                        ("GITOC:criminality",       "GI-TOC – Criminality Score",                "score"),
    "Criminal markets avg.":                   ("GITOC:criminal_markets",  "GI-TOC – Criminal Markets",                 "score"),
    "Human trafficking":                       ("GITOC:human_trafficking", "GI-TOC – Human Trafficking",                "score"),
    "Human smuggling":                         ("GITOC:human_smuggling",   "GI-TOC – Human Smuggling",                  "score"),
    "Arms trafficking":                        ("GITOC:arms_trafficking",  "GI-TOC – Arms Trafficking",                 "score"),
    "Heroin trade":                            ("GITOC:heroin",            "GI-TOC – Heroin Trade",                     "score"),
    "Cocaine trade":                           ("GITOC:cocaine",           "GI-TOC – Cocaine Trade",                    "score"),
    "Cannabis trade":                          ("GITOC:cannabis",          "GI-TOC – Cannabis Trade",                   "score"),
    "Synthetic drug trade":                    ("GITOC:synthetic_drugs",   "GI-TOC – Synthetic Drug Trade",             "score"),
    "Financial crimes":                        ("GITOC:financial_crimes",  "GI-TOC – Financial Crimes",                 "score"),
    "Criminal actors avg.":                    ("GITOC:criminal_actors",   "GI-TOC – Criminal Actors",                  "score"),
    "Mafia-style groups":                      ("GITOC:mafia",             "GI-TOC – Mafia-style Groups",               "score"),
    "State-embedded actors":                   ("GITOC:state_actors",      "GI-TOC – State-embedded Actors",            "score"),
    "Resilience avg.":                         ("GITOC:resilience",        "GI-TOC – Resilience Score",                 "score"),
    "Political leadership and governance":     ("GITOC:governance",        "GI-TOC – Political Leadership & Governance","score"),
    "Law enforcement":                         ("GITOC:law_enforcement",   "GI-TOC – Law Enforcement",                  "score"),
    "Anti-money laundering":                   ("GITOC:aml",               "GI-TOC – Anti-Money Laundering",            "score"),
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def ensure_source(cur, short_code):
    name, url, desc = SOURCES[short_code]
    cur.execute("""
        INSERT INTO sources (name, short_code, url, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (short_code) DO NOTHING
        RETURNING id
    """, (name, short_code, url, desc))
    result = cur.fetchone()
    if result:
        return result[0]
    cur.execute("SELECT id FROM sources WHERE short_code = %s", (short_code,))
    return cur.fetchone()[0]

def existing_source_id(cur, short_code):
    """Quelle muss schon existieren (WHO, UNODC, SIPRI). Kein stilles Anlegen."""
    cur.execute("SELECT id FROM sources WHERE short_code = %s", (short_code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Quelle {short_code} fehlt in sources – Abbruch, nichts anlegen")
    return row[0]

def ensure_indicator(cur, code, name, unit, source_id, category):
    cur.execute("""
        INSERT INTO indicator_metadata (indicator_code, name, unit, source_id, category)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (indicator_code) DO NOTHING
    """, (code, name, unit, source_id, category))

def insert_value(cur, iso_numeric, indicator_code, source_id, value, year):
    cur.execute("""
        INSERT INTO indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status)
        VALUES (%s, %s, %s, %s, %s, 'A')
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO NOTHING
    """, (iso_numeric, indicator_code, source_id, float(value), str(year)))

# ── Loaders ──────────────────────────────────────────────────────────────────

def load_owid_csvs(cur, conn, country_map_iso3):
    total = 0
    for cfg in OWID_FILES:
        path = cfg["path"]
        if not os.path.exists(path):
            raise FileNotFoundError(f"OWID-Datei fehlt: {path}")
        source_id = existing_source_id(cur, cfg["source"])

        ensure_indicator(cur, cfg["indicator_code"], cfg["name"], cfg["unit"], source_id, cfg["category"])

        df = pd.read_csv(path, low_memory=False)   # Lesefehler -> Abbruch, nicht still weiter

        value_col = cfg["value_col"]
        if value_col not in df.columns:
            raise KeyError(f"Spalte nicht gefunden: {value_col} in {path}")

        count = 0
        for _, row in df.iterrows():
            iso3 = str(row.get("Code", "")).upper().strip()
            if len(iso3) != 3 or iso3 == "NAN":
                continue
            iso_numeric = country_map_iso3.get(iso3)
            if not iso_numeric:
                continue
            year = row.get("Year")
            value = row.get(value_col)
            if pd.isna(year) or pd.isna(value):
                continue
            try:
                year_int = int(float(year))
                if year_int < 1800 or year_int > 2030:
                    continue
            except:
                continue
            insert_value(cur, iso_numeric, cfg["indicator_code"], source_id, value, year_int)
            count += 1

        conn.commit()
        print(f"  ✅ {cfg['name']}: {count} Datenpunkte")
        total += count

    return total

def load_fsi(cur, conn, country_map_name):
    source_id = ensure_source(cur, "FSI")
    conn.commit()

    path = "data/raw/fragile_states_index.xlsx"
    if not os.path.exists(path):
        print("  ⏭️  FSI nicht gefunden")
        return 0

    df = pd.read_excel(path, sheet_name="FSI 2006-2022", engine='openpyxl')

    # Alle vorhandenen FSI-Spalten registrieren
    for col, (code, name, unit) in FSI_INDICATORS.items():
        if col in df.columns:
            ensure_indicator(cur, code, name, unit, source_id, "Politics & Governance")

    count = 0
    for _, row in df.iterrows():
        country = str(row.get("Country", "")).strip().lower()
        iso_numeric = country_map_name.get(country)
        if not iso_numeric:
            continue

        year = row.get("Year")
        try:
            year_int = int(pd.Timestamp(year).year) if pd.notna(year) else None
        except:
            continue
        if not year_int:
            continue

        for col, (code, name, unit) in FSI_INDICATORS.items():
            if col not in df.columns:
                continue
            value = row.get(col)
            if pd.isna(value):
                continue
            insert_value(cur, iso_numeric, code, source_id, value, year_int)
            count += 1

    conn.commit()
    print(f"  ✅ Fragile States Index: {count} Datenpunkte")
    return count

def load_gitoc(cur, conn, country_map_name):
    source_id = ensure_source(cur, "GITOC")
    conn.commit()

    path = "data/raw/global_oc_index.xlsx"
    if not os.path.exists(path):
        print("  ⏭️  GI-TOC nicht gefunden")
        return 0

    total = 0
    for sheet, year in [("2025_dataset", 2025), ("2023_dataset", 2023), ("2021_dataset", 2021)]:
        try:
            df = pd.read_excel(path, sheet_name=sheet, engine='openpyxl')
        except:
            continue

        for col, (code, name, unit) in GITOC_INDICATORS.items():
            if col in df.columns:
                ensure_indicator(cur, code, name, unit, source_id, "Politics & Governance")

        count = 0
        for _, row in df.iterrows():
            country = str(row.get("Country", "")).strip().lower()
            iso_numeric = country_map_name.get(country)
            if not iso_numeric:
                continue

            for col, (code, _, _) in GITOC_INDICATORS.items():
                if col not in df.columns:
                    continue
                value = row.get(col)
                if pd.isna(value):
                    continue
                insert_value(cur, iso_numeric, code, source_id, value, year)
                count += 1

        conn.commit()
        print(f"  ✅ GI-TOC {year}: {count} Datenpunkte")
        total += count

    return total

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Ländercodes laden
        cur.execute("SELECT iso_numeric, iso_code_3, name FROM countries")
        rows = cur.fetchall()
        country_map_iso3 = {row[1]: row[0] for row in rows}
        country_map_name = {row[2].lower(): row[0] for row in rows}

        # Manuelle Overrides für häufige Namensabweichungen
        NAME_OVERRIDES = {
            "united states": "840", "usa": "840",
            "united kingdom": "826", "uk": "826",
            "south korea": "410", "republic of korea": "410",
            "north korea": "408",
            "russia": "643", "russian federation": "643",
            "iran": "364", "syria": "760",
            "taiwan": "158", "vietnam": "704", "viet nam": "704",
            "bolivia": "068", "venezuela": "862",
            "tanzania": "834", "united republic of tanzania": "834",
            "congo, dem. rep.": "180", "democratic republic of congo": "180",
            "congo, rep.": "178", "republic of congo": "178",
            "ivory coast": "384", "cote d'ivoire": "384",
            "turkiye": "792", "turkey": "792",
            "czechia": "203", "czech republic": "203",
            "eswatini": "748", "swaziland": "748",
            "cabo verde": "132", "cape verde": "132",
            "north macedonia": "807", "timor-leste": "626",
            "laos": "418", "lao pdr": "418",
            "burma": "104", "myanmar": "104",
            "moldova": "498", "palestine": "275",
            "kosovo": None,  # nicht in DB
        }
        country_map_name.update({k: v for k, v in NAME_OVERRIDES.items() if v})

        print("\n=== OWID-Bezug (WHO, UNODC, SIPRI) ===")
        total_owid = load_owid_csvs(cur, conn, country_map_iso3)

        # FSI und GITOC laden seit 25.11.2026 eigene Loader (CI-177, #140, #151):
        #   scripts/pipeline/governance/load_fsi.py und load_gitoc.py (Länder über lib/laender.py).
        # Die Funktionen load_fsi/load_gitoc unten bleiben nur als Altbestand stehen und werden nicht mehr aufgerufen.
        grand_total = total_owid
        print(f"\n{'='*50}")
        print(f"✅ GESAMT: {grand_total:,} Datenpunkte geladen")

    except Exception as e:
        conn.rollback()
        print(f"Fehler: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
