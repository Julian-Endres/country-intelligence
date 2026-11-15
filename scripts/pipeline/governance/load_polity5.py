"""
load_polity5.py — Polity5 Annual Time-Series (p5v2018)
======================================================
Quelle:  Center for Systemic Peace, Polity5 Annual Time-Series 1776–2018 (USA bis 2020)
Datei:   data/raw/history/p5v2018_Polity5_Annual Time-Series, 1946-2018.xls
Ziel:    indicators, 6 Codes POLITY5:* (source_id aus sources.short_code = 'POLITY5')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/governance/load_polity5.py
      Trockenlauf (Standard): liest die Datei, prüft, vergleicht mit der DB, schreibt NICHTS.
      Listet alle verworfenen Polity-Einheiten mit Jahren und Wertezahl.
  python scripts/pipeline/governance/load_polity5.py --schreiben
      schreibt in die DB (alles oder nichts, eine Transaktion), frischt indicator_coverage auf

Regeln (Neufassung 15.11.2026, Backlog #1 und #89, Pipeline-Standard Fall „Datei")
--------------------------------------------------------------------------------
- Länder NUR über die ausdrückliche Liste SCODE_ISO3 (Polity-Kürzel scode → ISO3).
  Kein countrycode-Paket, keine Ersatztabelle. Der alte Loader hat über seine Ersatztabelle
  u. a. Baden → Barbados, Modena → Moldau, Sardinien → Saudi-Arabien, Parma → Panama,
  Zentralamerika → Uganda sowie DDR und BRD beide → Deutschland geschrieben.
- Die Einheit bestimmt die Quelle: Ein scode, den Polity für einen heutigen Staat führt, wird
  mit seiner ganzen Reihe übernommen (z. B. GMY: Preußen/Reich 1800–1945 und Deutschland ab 1990).
- Vorgängerstaaten und historische Einheiten (VERWERFEN) werden für DB v1.0 nicht geladen,
  sondern mit Grund, Jahren und Wertezahl ausgegeben (Entscheidung Julian 15.11.: verwerfen,
  dokumentieren, später als eigene historische Einheiten nach #105 nachladen).
- Ein scode, der in keiner der beiden Listen steht → Abbruch.
- Sondercodes -66 (Fremdherrschaft), -77 (Interregnum), -88 (Übergang) sind keine Werte.
  Sie werden in KEINEM Indikator geladen, sondern je Code gezählt (known_issue).
  polity2 enthält sie nicht (Polity ersetzt sie dort selbst bzw. lässt den Wert leer).
- Genau ein Wert je Land, Indikator und Jahr, sonst Abbruch (z. B. Überlappung zweier scodes).
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt werden neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert, löscht der Loader NICHT, er meldet sie
  (u. a. die alten Zeilen ohne source_id; die entfernt eine Migration mit Liste).
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import csv
import datetime as dt
import hashlib
import logging
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("polity5")

REPO = Path(__file__).resolve().parents[3]
RAW_FILE = REPO / "data" / "raw" / "history" / "p5v2018_Polity5_Annual Time-Series, 1946-2018.xls"  # Pfad zentral: #135
SOURCE_CODE = "POLITY5"
SPECIAL = {-66, -77, -88}
PFLICHTSPALTEN = ["scode", "country", "year", "democ", "autoc", "polity2", "durable", "xconst", "polcomp"]

INDICATOR_COLS = {
    "POLITY5:polity2": "polity2",
    "POLITY5:democ": "democ",
    "POLITY5:autoc": "autoc",
    "POLITY5:durable": "durable",
    "POLITY5:xconst": "xconst",
    "POLITY5:polcomp": "polcomp",
}

# Polity-Einheiten, die einem heutigen Staat entsprechen. Ganze Reihe des scode wird übernommen.
SCODE_ISO3 = {
    "AFG": "AFG", "ALB": "ALB", "ALG": "DZA", "ANG": "AGO", "ARG": "ARG", "ARM": "ARM",
    "AUL": "AUS", "AUS": "AUT", "AZE": "AZE", "BAH": "BHR", "BEL": "BEL", "BEN": "BEN",
    "BFO": "BFA", "BHU": "BTN", "BLR": "BLR", "BNG": "BGD", "BOL": "BOL", "BOS": "BIH",
    "BOT": "BWA", "BRA": "BRA", "BUI": "BDI", "BUL": "BGR", "CAM": "KHM", "CAN": "CAN",
    "CAO": "CMR", "CAP": "CPV", "CEN": "CAF", "CHA": "TCD", "CHL": "CHL", "CHN": "CHN",
    "COL": "COL", "COM": "COM", "CON": "COG", "COS": "CRI", "CRO": "HRV", "CUB": "CUB",
    "CYP": "CYP", "CZR": "CZE", "DEN": "DNK", "DJI": "DJI", "DOM": "DOM", "ECU": "ECU",
    "EGY": "EGY", "EQG": "GNQ", "ERI": "ERI", "EST": "EST", "ETI": "ETH", "ETM": "TLS",
    "FIN": "FIN", "FJI": "FJI", "FRN": "FRA", "GAB": "GAB", "GAM": "GMB", "GHA": "GHA",
    "GMY": "DEU", "GNB": "GNB", "GRC": "GRC", "GRG": "GEO", "GUA": "GTM", "GUI": "GIN",
    "GUY": "GUY", "HAI": "HTI", "HON": "HND", "HUN": "HUN", "IND": "IND", "INS": "IDN",
    "IRE": "IRL", "IRN": "IRN", "IRQ": "IRQ", "ISR": "ISR", "ITA": "ITA", "IVO": "CIV",
    "JAM": "JAM", "JOR": "JOR", "JPN": "JPN", "KEN": "KEN", "KUW": "KWT", "KYR": "KGZ",
    "KZK": "KAZ", "LAO": "LAO", "LAT": "LVA", "LBR": "LBR", "LEB": "LBN", "LES": "LSO",
    "LIB": "LBY", "LIT": "LTU", "LUX": "LUX", "MAA": "MRT", "MAC": "MKD", "MAG": "MDG",
    "MAL": "MYS", "MAS": "MUS", "MAW": "MWI", "MEX": "MEX", "MLD": "MDA", "MLI": "MLI",
    "MNT": "MNE", "MON": "MNG", "MOR": "MAR", "MYA": "MMR", "MZM": "MOZ", "NAM": "NAM",
    "NEP": "NPL", "NEW": "NZL", "NIC": "NIC", "NIG": "NGA", "NIR": "NER", "NOR": "NOR",
    "NTH": "NLD", "OMA": "OMN", "PAK": "PAK", "PAN": "PAN", "PAR": "PRY", "PER": "PER",
    "PHI": "PHL", "PNG": "PNG", "POL": "POL", "POR": "PRT", "PRK": "PRK", "QAT": "QAT",
    "ROK": "KOR", "RUM": "ROU", "RUS": "RUS", "RWA": "RWA", "SAF": "ZAF", "SAL": "SLV",
    "SAU": "SAU", "SDN": "SDN", "SEN": "SEN", "SER": "SRB", "SIE": "SLE", "SIN": "SGP",
    "SLO": "SVK", "SLV": "SVN", "SOL": "SLB", "SOM": "SOM", "SPN": "ESP", "SRI": "LKA",
    "SSU": "SSD", "SUR": "SUR", "SWA": "SWZ", "SWD": "SWE", "SWZ": "CHE", "SYR": "SYR",
    "TAJ": "TJK", "TAW": "TWN", "TAZ": "TZA", "THI": "THA", "TKM": "TKM", "TOG": "TGO",
    "TRI": "TTO", "TUN": "TUN", "TUR": "TUR", "UAE": "ARE", "UGA": "UGA", "UKG": "GBR",
    "UKR": "UKR", "URU": "URY", "USA": "USA", "UZB": "UZB", "VEN": "VEN", "VIE": "VNM",
    "YEM": "YEM", "ZAI": "COD", "ZAM": "ZMB", "ZIM": "ZWE",
}

# Nicht geladen (DB v1.0). Grund steht im Protokoll und später im known_issue.
VORGAENGER = "Vorgängerstaat (eigene Einheit erst mit #105)"
HISTORISCH = "historische Einheit ohne heutigen Staat"
VERWERFEN = {
    "GDR": VORGAENGER, "GFR": VORGAENGER,          # DDR, BRD 1945–1990
    "USR": VORGAENGER,                             # UdSSR 1922–1991
    "YUG": VORGAENGER, "YGS": VORGAENGER,          # Jugoslawien 1921–1991, BR Jugoslawien/Serbien-Montenegro 1991–2006
    "CZE": VORGAENGER,                             # Tschechoslowakei 1918–1992
    "YAR": VORGAENGER, "YPR": VORGAENGER,          # Nord-/Südjemen
    "DRV": VORGAENGER, "RVN": VORGAENGER,          # Nord-/Südvietnam
    "ETH": VORGAENGER,                             # Äthiopien mit Eritrea 1855–1993 (heute: ETI)
    "PKS": VORGAENGER,                             # Pakistan mit Bangladesch 1947–1971 (heute: PAK)
    "SUD": VORGAENGER,                             # Sudan mit Südsudan 1956–2011 (heute: SDN)
    "KOR": HISTORISCH,                             # Korea 1800–1910
    "BAD": HISTORISCH, "BAV": HISTORISCH, "SAX": HISTORISCH, "WRT": HISTORISCH,   # dt. Einzelstaaten
    "MOD": HISTORISCH, "PMA": HISTORISCH, "PAP": HISTORISCH, "SAR": HISTORISCH,
    "SIC": HISTORISCH, "TUS": HISTORISCH,           # ital. Einzelstaaten
    "GCL": HISTORISCH, "UPC": HISTORISCH, "OFS": HISTORISCH,   # Großkolumbien, Zentralamerika, Oranje-Freistaat
    "KOS": "Kosovo fehlt in countries (CL-105, wie ILO)",
}


class LadeFehler(Exception):
    pass


def get_conn():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


# ─── Datei lesen und prüfen ───────────────────────────────────────────────────

def read_file(pfad: Path) -> tuple[pd.DataFrame, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    df = pd.read_excel(pfad)
    fehlend = [c for c in PFLICHTSPALTEN if c not in df.columns]
    if fehlend:
        raise LadeFehler(f"Pflichtspalten fehlen: {fehlend}")
    if len(df) == 0:
        raise LadeFehler("0 Zeilen in der Datei")
    return df, sha


def parse(df: pd.DataFrame, iso3_map: dict) -> tuple[dict, Counter, dict, Counter]:
    """Gibt {(iso_numeric, code, jahr): wert}, Zählbericht, Verworfen-Liste und Sondercodes zurück."""
    out, bericht, sonder = {}, Counter(), Counter()
    verworfen = defaultdict(lambda: {"namen": set(), "jahre": [], "werte": 0})
    unbekannt, mehrfach, nicht_numerisch = set(), [], []
    herkunft = {}   # (iso, code, jahr) → scode, für Fehlermeldung bei Überlappung

    for _, row in df.iterrows():
        scode = str(row["scode"]).strip()
        try:
            jahr = str(int(row["year"]))
        except (TypeError, ValueError):
            raise LadeFehler(f"Jahr nicht ganzzahlig: {row['year']!r} ({scode})")

        if scode in VERWERFEN:
            v = verworfen[scode]
            v["namen"].add(str(row["country"]).strip())
            v["jahre"].append(int(jahr))
            v["werte"] += sum(1 for col in INDICATOR_COLS.values()
                              if pd.notna(row[col]) and int(row[col]) not in SPECIAL)
            continue
        if scode not in SCODE_ISO3:
            unbekannt.add(f"{scode} ({str(row['country']).strip()})")
            continue
        iso = iso3_map.get(SCODE_ISO3[scode])
        if iso is None:
            unbekannt.add(f"{scode} → {SCODE_ISO3[scode]} fehlt in countries")
            continue

        for code, col in INDICATOR_COLS.items():
            v = row[col]
            if pd.isna(v):
                bericht["leer"] += 1
                continue
            try:
                wert = float(v)
            except (TypeError, ValueError):
                nicht_numerisch.append((scode, jahr, col, v))
                continue
            if wert in SPECIAL:
                sonder[(code, int(wert))] += 1
                continue
            key = (iso, code, jahr)
            if key in out:
                mehrfach.append((SCODE_ISO3[scode], code, jahr, herkunft[key], scode))
                continue
            out[key] = wert
            herkunft[key] = scode

    if unbekannt:
        raise LadeFehler(f"{len(unbekannt)} scodes weder in SCODE_ISO3 noch in VERWERFEN: {sorted(unbekannt)}")
    if nicht_numerisch:
        raise LadeFehler(f"{len(nicht_numerisch)} nicht numerische Werte, z. B. {nicht_numerisch[:5]}")
    if mehrfach:
        raise LadeFehler(f"{len(mehrfach)} Land/Code/Jahr mehrfach (Überlappung von scodes), z. B. {mehrfach[:10]}")
    if not out:
        raise LadeFehler("0 Werte gelesen")

    bericht["werte"] = len(out)
    bericht["laender"] = len({k[0] for k in out})
    for code in INDICATOR_COLS:
        bericht[f"werte_{code}"] = sum(1 for k in out if k[1] == code)
    return out, bericht, verworfen, sonder


def zeige_verworfen(verworfen: dict):
    log.info(f"  Verworfene Polity-Einheiten ({len(verworfen)}, Summe Werte "
             f"{sum(v['werte'] for v in verworfen.values())}):")
    for scode in sorted(verworfen, key=lambda s: (VERWERFEN[s], s)):
        v = verworfen[scode]
        log.info(f"    {scode:4} {min(v['jahre'])}–{max(v['jahre'])} {len(v['jahre']):4} Jahre "
                 f"{v['werte']:5} Werte · {' / '.join(sorted(v['namen']))} · {VERWERFEN[scode]}")


# ─── Vergleich mit der DB ─────────────────────────────────────────────────────

def compare(cur, source_id: int, neu: dict) -> dict:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE indicator_code LIKE 'POLITY5:%%' AND source_id = %s""", (source_id,))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    c = defaultdict(Counter)
    for (iso, code, jahr), w in neu.items():
        a = alt.get((iso, code, jahr), "fehlt")
        if a == "fehlt":
            c[code]["neu"] += 1
        elif a is None or abs(a - w) > 1e-9:
            c[code]["wert_geaendert"] += 1
        else:
            c[code]["gleich"] += 1
    for k in set(alt) - set(neu):
        c[k[1]]["nur_in_db"] += 1
    return {k: dict(v) for k, v in sorted(c.items())}


def compare_altbestand(cur, neu: dict, csv_pfad: Path | None) -> dict:
    """Info: alte Zeilen OHNE source_id (Ladung 27.05., mit Dubletten) gegen die neuen Werte.
    gleich = neuer Wert ist unter den alten Werten des Land-Jahrs; alt_ohne_entsprechung wird
    je Land als CSV geschrieben (Grundlage für die Migration)."""
    cur.execute("""SELECT i.iso_numeric, c.iso_code_3, i.indicator_code, i.time_period, i.value
                   FROM indicators i LEFT JOIN countries c USING (iso_numeric)
                   WHERE i.indicator_code LIKE 'POLITY5:%%' AND i.source_id IS NULL""")
    alt = defaultdict(list)
    iso3_von = {}
    n_zeilen = 0
    for iso, iso3, code, jahr, w in cur.fetchall():
        alt[(iso, code, jahr)].append(w)
        iso3_von[iso] = iso3
        n_zeilen += 1
    c = defaultdict(Counter)
    for k, w in neu.items():
        werte = alt.get(k)
        if werte is None:
            c[k[1]]["neu_gegenueber_alt"] += 1
        elif any(a is not None and abs(a - w) <= 1e-9 for a in werte):
            c[k[1]]["gleich_wie_alt" if len(werte) == 1 else "gleich_alt_hatte_dubletten"] += 1
        else:
            c[k[1]]["abweichend_von_alt"] += 1
    nur_alt = sorted(set(alt) - set(neu))
    for k in nur_alt:
        c[k[1]]["alt_ohne_entsprechung"] += len(alt[k])
    # je Land zusammengefasst
    je_land = defaultdict(lambda: {"zeilen": 0, "jahre": set()})
    for iso, code, jahr in nur_alt:
        je_land[iso]["zeilen"] += len(alt[(iso, code, jahr)])
        je_land[iso]["jahre"].add(int(jahr))
    log.info(f"  Altbestand ohne source_id: {n_zeilen} Zeilen; davon ohne Entsprechung im Neuladen "
             f"{sum(v['zeilen'] for v in je_land.values())} Zeilen in {len(je_land)} Ländern:")
    for iso, v in sorted(je_land.items(), key=lambda x: -x[1]["zeilen"]):
        log.info(f"    {iso3_von.get(iso) or iso} {min(v['jahre'])}–{max(v['jahre'])}: {v['zeilen']} Zeilen")
    if csv_pfad:
        csv_pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_pfad, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["iso_numeric", "iso3", "indicator_code", "time_period", "werte_alt"])
            for iso, code, jahr in nur_alt:
                w.writerow([iso, iso3_von.get(iso), code, jahr, "|".join(str(x) for x in alt[(iso, code, jahr)])])
        log.info(f"  Liste: {csv_pfad.relative_to(REPO)}")
    return {k: dict(v) for k, v in sorted(c.items())}


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true", help="in die DB schreiben (sonst nur Trockenlauf)")
    ap.add_argument("--datei", type=Path, default=RAW_FILE, help="abweichender Pfad zur Polity-Datei")
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources. Der Loader legt sie nicht an.")
        source_id = r[0]
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)",
                    (list(INDICATOR_COLS),))
        meta = dict(cur.fetchall())
        fehlt = [c for c in INDICATOR_COLS if c not in meta]
        falsch = {c: s for c, s in meta.items() if s != source_id}
        if fehlt:
            raise LadeFehler(f"Metadaten fehlen für {fehlt}. Der Loader legt sie nicht an.")
        if falsch:
            raise LadeFehler(f"Metadaten zeigen nicht auf source_id {source_id}: {falsch}")
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        iso3_map = dict(cur.fetchall())

        df, sha = read_file(args.datei)
        log.info(f"=== POLITY5 {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {len(df)} Zeilen, {df.scode.nunique()} scodes, "
                 f"{df.year.min()}–{df.year.max()} ===")
        neu, bericht, verworfen, sonder = parse(df, iso3_map)
        log.info(f"  Gelesen: { {k: v for k, v in sorted(bericht.items())} }")
        log.info(f"  Sondercodes nicht geladen (je Code): "
                 f"{ {f'{c} {s}': n for (c, s), n in sorted(sonder.items())} } · Summe {sum(sonder.values())}")
        zeige_verworfen(verworfen)
        log.info(f"  Vergleich DB (source_id {source_id}): {compare(cur, source_id, neu)}")
        csv_pfad = None if args.schreiben else \
            REPO / "logs" / "migrations" / f"{dt.date.today()}_polity5_altbestand_ohne_entsprechung.csv"
        log.info(f"  Info Altbestand: {compare_altbestand(cur, neu, csv_pfad)}")
    except LadeFehler as e:
        log.error(f"FEHLER: {e}")
        log.error("=== Es wird NICHTS geschrieben. ===")
        conn.rollback()
        conn.close()
        sys.exit(1)

    if not args.schreiben:
        log.info("=== Trocken: geprüft, nichts geschrieben. Schreiben mit --schreiben. ===")
        conn.rollback()
        conn.close()
        return

    from psycopg2.extras import execute_values
    rows = [(iso, code, source_id, jahr, w, "A") for (iso, code, jahr), w in neu.items()]
    res = execute_values(cur, """
        INSERT INTO indicators (iso_numeric, indicator_code, source_id, time_period, value, obs_status)
        VALUES %s
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO UPDATE
        SET value = EXCLUDED.value, obs_status = EXCLUDED.obs_status, last_updated = CURRENT_TIMESTAMP
        WHERE indicators.value IS DISTINCT FROM EXCLUDED.value
           OR indicators.obs_status IS DISTINCT FROM EXCLUDED.obs_status
        RETURNING (xmax = 0)
    """, rows, page_size=2000, fetch=True)
    n_neu = sum(1 for x in res if x[0])
    n_geaendert = len(res) - n_neu
    n_gleich = len(rows) - len(res)
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"p5v2018 xls sha256:{sha}", source_id))   # varchar(50)
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. "
             f"sources.loaded_at/loaded_version gesetzt, indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
