"""
Comtrade Loader v2
==================
Ersetzt load_comtrade.py (bleibt als Referenz liegen). Behebt die Fehler aus
dem DB-Audit 10.11.2026 (Backlog #88):

  1. Ländercodes: Comtrade nutzt eigene Melder-Codes (USA 842, FRA 251,
     IND 699, NOR 579, CHE 757). v2 holt die Comtrade-Melderliste und ordnet
     über ISO3 zu, statt die ISO-Nummer zu schicken.
  2. Nur Gesamtwerte: partner2Code=0, customsCode=C00, motCode=0.
  3. Zeilengrenze: Antwort mit >= MAX_RECORDS Zeilen gilt als abgeschnitten,
     der Batch wird geteilt (erst Jahre, dann Länder) und neu abgefragt.
  4. Fehler: Ein Batch gilt nur nach erfolgreicher Antwort als erledigt.
     Fehlgeschlagene Batches stehen in der State-Datei und werden beim
     nächsten Lauf wiederholt.
  5. Zähler: nur echte API-Calls, je Kalendertag (UTC). Stopp bei DAILY_LIMIT,
     am nächsten Tag einfach neu starten.
  6. Doppelte Zeilen je Schlüssel werden gezählt und gemeldet, nicht still
     überschrieben.

P1 = Produktstruktur (HS4, Partner Welt)  -> trade.trade_products
P2 = Partnerstruktur (TOTAL, alle Partner) -> trade.trade_partners

Aufruf:
    # Trockenlauf (schreibt nichts in die DB, zeigt Zeilen und Summen):
    python3 scripts/pipeline/economy/load_comtrade_v2.py --laender USA,DEU --jahre 2008-2010 --trocken
    # Testlauf mit Schreiben:
    python3 scripts/pipeline/economy/load_comtrade_v2.py --laender USA,DEU --jahre 2008-2010
    # Voller Lauf (mehrere Tage, jeden Tag neu starten):
    caffeinate -i python3 scripts/pipeline/economy/load_comtrade_v2.py --jahre 2000-2025

Optionen: --pipeline p1|p2|beide (Standard beide), --state <datei>
Vorher Backup:  pg_dump -n trade -Fc -f backups/trade_<datum>.dump
"""

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("comtrade_v2")

# ─── Konfiguration ───────────────────────────────────────────────────────────

API_KEY        = os.getenv("COMTRADE_KEY")
BASE_URL       = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
REPORTERS_URL  = "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json"
PARTNERS_URL   = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
STATE_FILE     = ".comtrade_state_v2.json"
LOG_DIR        = "logs"
REF_DIR        = "data/raw/comtrade/reference"
REF_MAX_AGE_DAYS = 30

MAX_RECORDS        = 100000   # Obergrenze je Call (Free Tier)
DAILY_LIMIT        = 490      # Free Tier: 500 Calls/Tag, etwas Puffer
COUNTRIES_PER_BATCH = 5
YEARS_PER_BATCH    = 5
SLEEP              = 2        # Sekunden zwischen Calls

TOTALS = {"partner2Code": 0, "customsCode": "C00", "motCode": 0}


class QuotaExhausted(Exception):
    pass


class ServerAbort(Exception):
    """Server bricht die Antwort ab (Reset, Lese-Timeout) – meist bei zu großen Antworten. Batch wird geteilt."""
    pass


def _own_network_down(exc):
    """Eigene Verbindung weg (DNS, kein Netz) – nicht der Comtrade-Server."""
    t = str(exc)
    return any(s in t for s in ("NameResolutionError", "Failed to resolve", "nodename nor servname",
                                "Network is unreachable", "NewConnectionError"))


def _wait_for_network(max_minutes=30):
    """Wartet, bis die API wieder erreichbar ist (Laptop zugeklappt, WLAN weg). Kein API-Call."""
    for i in range(max_minutes):
        try:
            requests.head("https://comtradeapi.un.org", timeout=15)
            if i:
                log.info(f"    Netz wieder da nach ~{i} min")
            return
        except requests.RequestException:
            if i == 0:
                log.warning("    Eigene Verbindung weg – warte auf Netz (max. 30 min) ...")
            time.sleep(60)
    raise RuntimeError("Netz seit 30 min weg – Lauf abgebrochen, später einfach neu starten")


# ─── State ───────────────────────────────────────────────────────────────────

def load_state(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"erledigt": [], "fehlgeschlagen": {}, "tag": None, "calls_heute": 0,
            "calls_gesamt": 0, "zeilen_p1": 0, "zeilen_p2": 0, "dubletten": 0}


def save_state(state, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def today_utc():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


# ─── Referenzlisten ──────────────────────────────────────────────────────────

def _get_results(url, max_age_days=REF_MAX_AGE_DAYS, retries=3):
    """Referenzliste lesen: lokale Kopie, solange jünger als max_age_days, sonst neu holen.
    Der Comtrade-Server antwortet auf die Referenzdateien langsam (gemessen 19 s für 81 KB)."""
    os.makedirs(REF_DIR, exist_ok=True)
    path = os.path.join(REF_DIR, os.path.basename(url))
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < max_age_days * 86400:
        log.info(f"Referenz aus lokaler Kopie: {path}")
        with open(path) as f:
            data = json.load(f)
    else:
        data, letzter_fehler = None, None
        for versuch in range(1, retries + 1):
            try:
                log.info(f"Lade Referenz {os.path.basename(url)} (Versuch {versuch}/{retries}) ...")
                r = requests.get(url, timeout=180)
                r.raise_for_status()
                data = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                letzter_fehler = e
                time.sleep(15 * versuch)
        if data is None:
            sys.exit(f"Referenzliste nicht abrufbar ({url}): {letzter_fehler}")
        with open(path, "w") as f:
            json.dump(data, f)
    return data.get("results", data) if isinstance(data, dict) else data


def _key(entry, *names):
    """Feld unabhängig von Groß-/Kleinschreibung lesen."""
    low = {k.lower(): v for k, v in entry.items()}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def _year(s, default):
    return int(str(s)[:4]) if s else default


def load_reporters(iso3_to_num):
    """Comtrade-Melder -> unsere iso_numeric, über ISO3.
    Gibt ({comtrade_code: iso_numeric}, {comtrade_code: (von_jahr, bis_jahr)}).
    Historische Codes (z. B. 280 BRD bis 1990, 841 USA bis 1980) werden nur für ihre Gültigkeitsjahre abgefragt."""
    entries = _get_results(REPORTERS_URL)
    if not entries:
        sys.exit("Melderliste leer – Abbruch.")
    log.info(f"Beispiel-Eintrag Melderliste: {entries[0]}")
    mapping, validity, ohne_treffer = {}, {}, []
    for e in entries:
        if _key(e, "isGroup"):
            continue
        code = _key(e, "reporterCode")
        iso3 = _key(e, "reporterCodeIsoAlpha3")
        name = _key(e, "reporterDesc", "text")
        if code is None:
            continue
        if iso3 in iso3_to_num:
            mapping[int(code)] = iso3_to_num[iso3]
            validity[int(code)] = (_year(_key(e, "entryEffectiveDate"), 1900),
                                   _year(_key(e, "entryExpiredDate"), 9999))
        else:
            ohne_treffer.append(f"{code} {iso3} {name}")
    if not mapping:
        sys.exit("Keine Melder zugeordnet – Feldnamen der Melderliste prüfen (siehe Beispiel-Eintrag).")
    log.info(f"Melder zugeordnet: {len(mapping)} Codes, ohne Treffer in countries: {len(ohne_treffer)}")
    if ohne_treffer:
        log.info("Ohne Treffer (Auszug): " + "; ".join(ohne_treffer[:25]))
    # Mehrere Comtrade-Codes für ein Land (historische Codes) sichtbar machen
    per_iso = {}
    for c, iso in mapping.items():
        per_iso.setdefault(iso, []).append(c)
    mehrfach = {iso: cs for iso, cs in per_iso.items() if len(cs) > 1}
    if mehrfach:
        log.info(f"Länder mit mehreren Comtrade-Codes: {mehrfach}")
    return mapping, validity


def load_partner_groups():
    """Comtrade-Partnercodes, die Gruppen/Aggregate sind (für P2 herausfiltern)."""
    groups, names = set(), {}
    for e in _get_results(PARTNERS_URL):
        code = _key(e, "PartnerCode", "id")
        if code is None:
            continue
        code = int(code)
        names[code] = (_key(e, "PartnerCodeIsoAlpha3"), _key(e, "PartnerDesc", "text"))
        if _key(e, "isGroup"):
            groups.add(code)
    groups.add(0)  # Welt
    log.info(f"Partnerliste: {len(names)} Codes, davon {len(groups)} Gruppen/Welt")
    return groups, names


# ─── API ─────────────────────────────────────────────────────────────────────

def api_call(params, state, state_path, retries=3):
    """Gibt die Datenzeilen zurück oder wirft eine Exception. Nie still leer bei Fehler."""
    if state["tag"] != today_utc():
        state["tag"], state["calls_heute"] = today_utc(), 0
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    letzter_fehler = None
    server_abbrueche = 0
    versuch = 0
    while versuch < retries:
        versuch += 1
        if state["calls_heute"] >= DAILY_LIMIT:
            raise QuotaExhausted()
        state["calls_heute"] += 1
        state["calls_gesamt"] += 1
        save_state(state, state_path)
        try:
            r = requests.get(BASE_URL, params=params, headers=headers, timeout=180)
        except requests.RequestException as e:
            if _own_network_down(e):
                # Call hat den Server nie erreicht: nicht zählen, auf Netz warten, gleichen Versuch wiederholen
                state["calls_heute"] -= 1
                state["calls_gesamt"] -= 1
                save_state(state, state_path)
                versuch -= 1
                _wait_for_network()
                continue
            server_abbrueche += 1
            letzter_fehler = f"Server-Abbruch: {e}"
            if server_abbrueche >= 2:
                raise ServerAbort(letzter_fehler)
            time.sleep(30)
            continue
        if r.status_code == 200:
            body = r.json()
            if body.get("error"):
                raise RuntimeError(f"API-Fehler: {body['error']}")
            return body.get("data") or []
        if r.status_code in (403, 429) and "quota" in r.text.lower():
            raise QuotaExhausted()
        if r.status_code == 429:
            letzter_fehler = "429 Rate limit"
            time.sleep(60)
            continue
        if r.status_code in (400, 401):
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        letzter_fehler = f"HTTP {r.status_code}: {r.text[:200]}"
        time.sleep(10 * versuch)
    raise RuntimeError(f"Nach {retries} Versuchen gescheitert: {letzter_fehler}")


def fetch(pipeline, reporters, years, state, state_path):
    """Holt einen Batch. Teilt ihn bei abgeschnittener Antwort und ruft sich selbst auf."""
    params = {
        "reporterCode": ",".join(map(str, reporters)),
        "period": ",".join(map(str, years)),
        "flowCode": "X,M",
        "maxRecords": MAX_RECORDS,
        "format": "JSON",
        "includeDesc": "False",
        **TOTALS,
    }
    if pipeline == "p1":
        params.update({"partnerCode": 0, "cmdCode": "AG4"})
    else:
        params.update({"cmdCode": "TOTAL"})  # partnerCode weggelassen = alle Partner

    try:
        rows = api_call(params, state, state_path)
        time.sleep(SLEEP)
        if len(rows) < MAX_RECORDS:
            return rows
        grund = f"{len(rows)} Zeilen = Grenze erreicht"
    except ServerAbort as e:
        if len(years) == 1 and len(reporters) == 1:
            raise RuntimeError(f"Server bricht auch bei 1 Land × 1 Jahr ab: {e}")
        grund = "Server bricht ab"

    log.warning(f"    {pipeline}: {grund}, teile Batch ({len(reporters)} Länder × {len(years)} Jahre)")
    if len(years) > 1:
        mid = len(years) // 2
        return (fetch(pipeline, reporters, years[:mid], state, state_path)
                + fetch(pipeline, reporters, years[mid:], state, state_path))
    if len(reporters) > 1:
        mid = len(reporters) // 2
        return (fetch(pipeline, reporters[:mid], years, state, state_path)
                + fetch(pipeline, reporters[mid:], years, state, state_path))
    raise RuntimeError(f"1 Land × 1 Jahr übersteigt {MAX_RECORDS} Zeilen – Abfrage prüfen")


# ─── Umwandeln ───────────────────────────────────────────────────────────────

def build_p1(rows, reporter_map, state):
    seen = {}
    for r in rows:
        iso = reporter_map.get(r.get("reporterCode"))
        year, flow, hs4, fob = r.get("period"), r.get("flowCode"), r.get("cmdCode"), r.get("primaryValue")
        if not iso or not year or flow not in ("X", "M") or not hs4 or fob is None:
            continue
        key = (iso, int(year), flow, hs4)
        rec = key + (fob, r.get("qty"), r.get("netWgt"))
        if key in seen:
            state["dubletten"] += 1
            if seen[key][4] != fob and state["dubletten"] <= 20:
                log.warning(f"    Dublette mit anderem Wert: {key} {seen[key][4]} vs {fob} "
                            f"(Melder {r.get('reporterCode')})")
            continue  # erste Zeile behalten, nicht still überschreiben
        seen[key] = rec
    return list(seen.values())


def build_p2(rows, reporter_map, partner_groups, partner_names, state):
    seen = {}
    for r in rows:
        iso = reporter_map.get(r.get("reporterCode"))
        year, flow, pc, fob = r.get("period"), r.get("flowCode"), r.get("partnerCode"), r.get("primaryValue")
        if not iso or not year or flow not in ("X", "M") or pc is None or fob is None:
            continue
        if int(pc) in partner_groups:
            continue
        key = (iso, int(year), flow, int(pc))
        p_iso, p_name = partner_names.get(int(pc), (None, None))
        rec = key + (p_iso or "", (p_name or "")[:200], fob)
        if key in seen:
            state["dubletten"] += 1
            continue
        seen[key] = rec
    return list(seen.values())


SQL_P1 = """
    INSERT INTO trade.trade_products (iso_numeric, year, flow_code, hs4_code, fob_value, qty, net_weight)
    VALUES %s
    ON CONFLICT (iso_numeric, year, flow_code, hs4_code) DO UPDATE
    SET fob_value = EXCLUDED.fob_value, qty = EXCLUDED.qty, net_weight = EXCLUDED.net_weight,
        last_updated = CURRENT_TIMESTAMP
"""
SQL_P2 = """
    INSERT INTO trade.trade_partners (iso_numeric, year, flow_code, partner_code, partner_iso, partner_name, fob_value)
    VALUES %s
    ON CONFLICT (iso_numeric, year, flow_code, partner_code) DO UPDATE
    SET fob_value = EXCLUDED.fob_value, partner_iso = EXCLUDED.partner_iso,
        partner_name = EXCLUDED.partner_name, last_updated = CURRENT_TIMESTAMP
"""


def summary(records, pipeline):
    """Kurzer Überblick je Land und Jahr (Zeilen, Exportsumme in Mrd. USD)."""
    agg = {}
    for rec in records:
        iso, year, flow = rec[0], rec[1], rec[2]
        fob = rec[4] if pipeline == "p1" else rec[6]
        a = agg.setdefault((iso, year), [0, 0.0])
        a[0] += 1
        if flow == "X":
            a[1] += fob or 0
    for (iso, year), (n, x) in sorted(agg.items()):
        log.info(f"      {pipeline} {iso} {year}: {n} Zeilen, Export {x / 1e9:.1f} Mrd")


# ─── Main ────────────────────────────────────────────────────────────────────

def parse_years(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def chunks(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jahre", default="2000-2025")
    ap.add_argument("--laender", help="ISO3-Liste, z. B. USA,DEU (Standard: alle)")
    ap.add_argument("--pipeline", choices=["p1", "p2", "beide"], default="beide")
    ap.add_argument("--trocken", action="store_true", help="nichts in die DB schreiben")
    ap.add_argument("--state", default=STATE_FILE)
    args = ap.parse_args()

    if not API_KEY:
        sys.exit("COMTRADE_KEY fehlt in .env")

    os.makedirs(LOG_DIR, exist_ok=True)
    fh = logging.FileHandler(os.path.join(LOG_DIR, f"comtrade_v2_{today_utc()}.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(fh)

    # Test- und Trockenläufe bekommen eine eigene State-Datei, damit sie den vollen Lauf nicht beeinflussen
    state_path = args.state
    if (args.trocken or args.laender) and args.state == STATE_FILE:
        state_path = ".comtrade_state_v2_test.json"
    state = load_state(state_path)

    conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
                            user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
                            port=os.getenv("DB_PORT"))
    cur = conn.cursor()
    cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_numeric <> '000'")
    iso3_to_num = dict(cur.fetchall())

    reporter_map, validity = load_reporters(iso3_to_num)
    partner_groups, partner_names = load_partner_groups()

    codes = sorted(reporter_map)
    if args.laender:
        wanted = {iso3_to_num[x.strip().upper()] for x in args.laender.split(",")
                  if x.strip().upper() in iso3_to_num}
        codes = [c for c in codes if reporter_map[c] in wanted]
        log.info(f"Auswahl: {args.laender} -> Comtrade-Codes {codes}")
    if not codes:
        sys.exit("Keine Melder ausgewählt.")

    years = parse_years(args.jahre)
    pipelines = ["p1", "p2"] if args.pipeline == "beide" else [args.pipeline]
    batches = []
    for yc in chunks(years, YEARS_PER_BATCH):
        # nur Codes, die in diesen Jahren gültig sind (280 BRD nur bis 1990, 841 USA nur bis 1980 …)
        active = [c for c in codes if validity[c][0] <= yc[-1] and validity[c][1] >= yc[0]]
        for rc in chunks(active, COUNTRIES_PER_BATCH):
            for p in pipelines:
                batches.append((p, rc, yc))
    offen = [b for b in batches if f"{b[0]}|{','.join(map(str, b[1]))}|{b[2][0]}-{b[2][-1]}"
             not in state["erledigt"]]
    log.info(f"{len(batches)} Batches, davon offen: {len(offen)} | Calls heute bisher: "
             f"{state['calls_heute'] if state['tag'] == today_utc() else 0}"
             + (" | TROCKENLAUF" if args.trocken else ""))

    neu_fehler = 0
    try:
        for i, (p, rc, yc) in enumerate(offen, 1):
            key = f"{p}|{','.join(map(str, rc))}|{yc[0]}-{yc[-1]}"
            log.info(f"  [{i}/{len(offen)}] {key}")
            try:
                rows = fetch(p, rc, yc, state, state_path)
            except QuotaExhausted:
                raise
            except Exception as e:
                neu_fehler += 1
                state["fehlgeschlagen"][key] = f"{today_utc()}: {e}"
                save_state(state, state_path)
                log.error(f"    FEHLER, Batch bleibt offen: {e}")
                continue

            if p == "p1":
                records = build_p1(rows, reporter_map, state)
            else:
                records = build_p2(rows, reporter_map, partner_groups, partner_names, state)
            log.info(f"    {len(rows)} API-Zeilen -> {len(records)} Datensätze")

            if args.trocken:
                summary(records, p)
            else:
                if records:
                    psycopg2.extras.execute_values(cur, SQL_P1 if p == "p1" else SQL_P2,
                                                   records, page_size=5000)
                conn.commit()
                state["zeilen_" + p] += len(records)
                state["erledigt"].append(key)
                state["fehlgeschlagen"].pop(key, None)
            save_state(state, state_path)
    except QuotaExhausted:
        log.warning(f"Tageslimit erreicht ({state['calls_heute']} Calls). Morgen einfach neu starten.")
    finally:
        cur.close()
        conn.close()

    offen_rest = len([b for b in batches if f"{b[0]}|{','.join(map(str, b[1]))}|{b[2][0]}-{b[2][-1]}"
                      not in state["erledigt"]])
    log.info(f"=== Ende: offen {offen_rest}/{len(batches)}, neue Fehler {neu_fehler}, "
             f"fehlgeschlagen gesamt {len(state['fehlgeschlagen'])}, Dubletten {state['dubletten']}, "
             f"Calls heute {state['calls_heute']}, gesamt {state['calls_gesamt']} ===")


if __name__ == "__main__":
    main()
