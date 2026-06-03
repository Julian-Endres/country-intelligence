"""
Comtrade Batched Loader
=======================
Lädt Trade-Daten von UN Comtrade API v1 mit Batching-Strategie.

Pipeline 1: Produktstruktur (HS-4, alle Partner aggregiert)
Pipeline 2: Partnerstruktur (TOTAL, alle Partner aufgelöst)

Batching: 5 Länder × 5 Jahre pro Call → ~300 Calls für 25 Jahre
Limit: 500 Calls/Tag (Free Tier)

Setup:
    1. API Key in .env eintragen: COMTRADE_KEY=your_key_here
    2. Script nach scripts/pipeline/load_comtrade.py kopieren
    3. python3 scripts/pipeline/load_comtrade.py

Tag 1: YEAR_BATCHES = [(2020,2024)]
Tag 2: YEAR_BATCHES = [(2000,2004), (2005,2009)]
"""

import requests
import psycopg2
import psycopg2.extras
import os
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv()

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# ─── Konfiguration ───────────────────────────────────────────────────────────

API_KEY      = os.getenv("COMTRADE_KEY")
BASE_URL     = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
STATE_FILE   = ".comtrade_state.json"
PARTNER_CODES_URL = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"

# Tag 1: 2010-2024
YEAR_BATCHES = [
    (2020, 2025),
]

# Tag 2: ersetze mit:
# YEAR_BATCHES = [
#     (2000, 2004),
#     (2005, 2009),
# ]

COUNTRIES_PER_BATCH = 5
PARTNERS_PER_BATCH  = 50   # Höher = weniger Calls, aber größere Responses
SLEEP_BETWEEN_CALLS = 2

# ─── DB ──────────────────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def setup_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trade.trade_products (
            id SERIAL PRIMARY KEY,
            iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
            year INT NOT NULL,
            flow_code CHAR(1) NOT NULL,
            hs4_code VARCHAR(10) NOT NULL,
            fob_value FLOAT,
            qty FLOAT,
            net_weight FLOAT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(iso_numeric, year, flow_code, hs4_code)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trade.trade_partners (
            id SERIAL PRIMARY KEY,
            iso_numeric CHAR(3) REFERENCES countries(iso_numeric),
            year INT NOT NULL,
            flow_code CHAR(1) NOT NULL,
            partner_code INT NOT NULL,
            partner_iso VARCHAR(3),
            partner_name VARCHAR(200),
            fob_value FLOAT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(iso_numeric, year, flow_code, partner_code)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tp_iso_year ON trade.trade_products(iso_numeric, year)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tpar_iso_year ON trade.trade_partners(iso_numeric, year)")
    log.info("Tabellen erstellt/geprüft.")

def get_all_countries(cur):
    cur.execute("""
        SELECT iso_numeric, iso_code_3, name
        FROM countries
        WHERE iso_numeric != '000'
        ORDER BY iso_numeric
    """)
    return cur.fetchall()

# ─── State Management ────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "completed_batches_p1": [],
        "completed_batches_p2": [],
        "total_calls": 0,
        "total_rows_p1": 0,
        "total_rows_p2": 0,
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ─── API ─────────────────────────────────────────────────────────────────────

def api_call(params, retries=3):
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    for attempt in range(retries):
        try:
            r = requests.get(BASE_URL, params=params, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json().get("data", [])
            elif r.status_code == 429:
                log.warning(f"  Rate limit (429) – warte 60s...")
                time.sleep(60)
            elif r.status_code == 400:
                log.warning(f"  Bad request: {r.text[:200]}")
                return []
            else:
                log.warning(f"  HTTP {r.status_code} – Versuch {attempt+1}/{retries}")
                time.sleep(5)
        except Exception as e:
            log.warning(f"  Exception (Versuch {attempt+1}): {e}")
            time.sleep(5)
    return []

# ─── Partner Codes ───────────────────────────────────────────────────────────

def load_partner_codes():
    """
    Lädt alle gültigen Partner-Codes von der Comtrade Referenz-API.
    Filtert Aggregate (isGroup=true) raus – nur echte Länder.
    """
    log.info("Lade Partner-Codes von Referenz-API...")
    r = requests.get(PARTNER_CODES_URL, timeout=30)
    data = r.json().get("results", [])
    codes = [
        entry["PartnerCode"]
        for entry in data
        if not entry.get("isGroup", True) and entry.get("PartnerCode", 0) > 0
    ]
    log.info(f"Partner-Codes geladen: {len(codes)} echte Länder")
    return codes

# ─── Pipeline 1: Produktstruktur ─────────────────────────────────────────────

def run_pipeline1(cur, reporter_codes, iso_map, year_start, year_end, state):
    batch_key = f"p1_{','.join(map(str, reporter_codes))}_{year_start}_{year_end}"
    if batch_key in state["completed_batches_p1"]:
        log.info(f"    P1: bereits geladen, überspringe")
        return 0

    params = {
        "reporterCode": ",".join(str(r) for r in reporter_codes),
        "period":       ",".join(str(y) for y in range(year_start, year_end + 1)),
        "partnerCode":  0,
        "cmdCode":      "AG4",
        "flowCode":     "X,M",
        "maxRecords":   100000,
        "format":       "JSON",
        "includeDesc":  "False",
    }

    rows = api_call(params)
    records = []
    for row in rows:
        iso_numeric = iso_map.get(row.get("reporterCode"))
        if not iso_numeric:
            continue
        year = row.get("period")
        flow = row.get("flowCode")
        hs4  = row.get("cmdCode", "")
        fob  = row.get("primaryValue")
        if not all([year, flow, hs4, fob is not None]):
            continue
        records.append((iso_numeric, year, flow, hs4, fob, row.get("qty"), row.get("netWgt")))

    # Deduplizieren
    seen = {}
    for r in records:
        key = (r[0], r[1], r[2], r[3])
        seen[key] = r
    records = list(seen.values())

    if records:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO trade.trade_products (iso_numeric, year, flow_code, hs4_code, fob_value, qty, net_weight)
            VALUES %s
            ON CONFLICT (iso_numeric, year, flow_code, hs4_code) DO UPDATE
            SET fob_value  = EXCLUDED.fob_value,
                qty        = EXCLUDED.qty,
                net_weight = EXCLUDED.net_weight,
                last_updated = CURRENT_TIMESTAMP
        """, records)

    state["completed_batches_p1"].append(batch_key)
    state["total_rows_p1"] += len(records)
    return len(records)

# ─── Pipeline 2: Partnerstruktur ─────────────────────────────────────────────

def run_pipeline2(cur, reporter_codes, iso_map, year_start, year_end, state, partner_codes):
    """
    Partnerstruktur: TOTAL Produkte, alle Partner aufgelöst.
    Batcht Partner-Codes in Gruppen à PARTNERS_PER_BATCH.
    """
    batch_key = f"p2_{','.join(map(str, reporter_codes))}_{year_start}_{year_end}"
    if batch_key in state["completed_batches_p2"]:
        log.info(f"    P2: bereits geladen, überspringe")
        return 0

    total_records = []

    partner_batches = [
        partner_codes[i:i + PARTNERS_PER_BATCH]
        for i in range(0, len(partner_codes), PARTNERS_PER_BATCH)
    ]

    for partner_batch in partner_batches:
        params = {
            "reporterCode": ",".join(str(r) for r in reporter_codes),
            "period":       ",".join(str(y) for y in range(year_start, year_end + 1)),
            "partnerCode":  ",".join(str(p) for p in partner_batch),
            "cmdCode":      "TOTAL",
            "flowCode":     "X,M",
            "maxRecords":   100000,
            "format":       "JSON",
            "includeDesc":  "True",
        }

        rows = api_call(params)

        for row in rows:
            iso_numeric  = iso_map.get(row.get("reporterCode"))
            if not iso_numeric:
                continue
            year         = row.get("period")
            flow         = row.get("flowCode")
            partner_code = row.get("partnerCode")
            fob          = row.get("primaryValue")
            if not all([year, flow, partner_code is not None, fob is not None]):
                continue
            total_records.append((
                iso_numeric, year, flow, partner_code,
                row.get("partnerISO", ""), row.get("partnerDesc", ""), fob
            ))

        time.sleep(SLEEP_BETWEEN_CALLS)

    # Deduplizieren
    seen = {}
    for r in total_records:
        key = (r[0], r[1], r[2], r[3])
        seen[key] = r
    records = list(seen.values())

    if records:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO trade.trade_partners
                (iso_numeric, year, flow_code, partner_code, partner_iso, partner_name, fob_value)
            VALUES %s
            ON CONFLICT (iso_numeric, year, flow_code, partner_code) DO UPDATE
            SET fob_value    = EXCLUDED.fob_value,
                partner_iso  = EXCLUDED.partner_iso,
                partner_name = EXCLUDED.partner_name,
                last_updated = CURRENT_TIMESTAMP
        """, records)

    state["completed_batches_p2"].append(batch_key)
    state["total_rows_p2"] += len(records)
    return len(records)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        log.error("COMTRADE_KEY nicht in .env! Bitte eintragen: COMTRADE_KEY=dein_key")
        return

    log.info("=== Comtrade Batched Loader ===")
    log.info(f"Jahr-Batches: {YEAR_BATCHES}")

    conn = get_connection()
    cur = conn.cursor()
    setup_tables(cur)
    conn.commit()

    countries = get_all_countries(cur)
    log.info(f"{len(countries)} Länder gefunden")

    iso_map = {}
    reporter_list = []
    for iso_numeric, iso_code_3, name in countries:
        try:
            reporter_code = int(iso_numeric)
            iso_map[reporter_code] = iso_numeric
            reporter_list.append(reporter_code)
        except:
            continue

    # Partner-Codes einmalig laden
    partner_codes = load_partner_codes()

    batches = [reporter_list[i:i+COUNTRIES_PER_BATCH] for i in range(0, len(reporter_list), COUNTRIES_PER_BATCH)]
    total_batches = len(batches) * len(YEAR_BATCHES)
    log.info(f"{len(batches)} Länder-Batches × {len(YEAR_BATCHES)} Jahr-Batches = {total_batches} Runden")

    state = load_state()
    total_calls = state.get("total_calls", 0)

    for year_start, year_end in YEAR_BATCHES:
        log.info(f"\n--- Jahre {year_start}-{year_end} ---")

        for i, batch in enumerate(batches):
            log.info(f"  Batch {i+1}/{len(batches)} | Calls bisher: {total_calls}")

            # Pipeline 1
            rows_p1 = run_pipeline1(cur, batch, iso_map, year_start, year_end, state)
            conn.commit()
            total_calls += 1
            state["total_calls"] = total_calls
            save_state(state)
            log.info(f"    P1: {rows_p1} Zeilen gespeichert")
            time.sleep(SLEEP_BETWEEN_CALLS)

            # Pipeline 2
            rows_p2 = run_pipeline2(cur, batch, iso_map, year_start, year_end, state, partner_codes)
            conn.commit()
            # P2 verbraucht mehrere Calls (partner_batches)
            p2_calls = -(-len(partner_codes) // PARTNERS_PER_BATCH)  # ceiling division
            total_calls += p2_calls
            state["total_calls"] = total_calls
            save_state(state)
            log.info(f"    P2: {rows_p2} Zeilen gespeichert ({p2_calls} Calls)")
            time.sleep(SLEEP_BETWEEN_CALLS)

            # Sicherheitsstopp
            if total_calls >= 490:
                log.warning("490 Calls erreicht – Tageslimit fast erreicht. Morgen weitermachen.")
                log.info(f"Produktzeilen gesamt: {state['total_rows_p1']:,}")
                log.info(f"Partnerzeilen gesamt: {state['total_rows_p2']:,}")
                cur.close()
                conn.close()
                return

    log.info(f"\n=== Fertig! ===")
    log.info(f"Total Calls: {total_calls}")
    log.info(f"Produktzeilen: {state['total_rows_p1']:,}")
    log.info(f"Partnerzeilen: {state['total_rows_p2']:,}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()