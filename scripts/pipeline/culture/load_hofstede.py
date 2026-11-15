"""
load_hofstede.py — Hofstede 6 Dimensions (Dimension Data Matrix)
================================================================
Quelle:  Geert Hofstede, Dimension Data Matrix, Datei „6 dimensions for website.csv“
         (Seite nennt „version 2015 12 08“, Dateiname der Download-URL 2015-08-16)
         https://geerthofstede.com/research-and-vsm/dimension-data-matrix/
Datei:   data/raw/culture/6-dimensions.csv (identisch mit data/raw/reference/hofstede_6dimensions_2015-08-16.csv)
Ziel:    indicators, 6 Codes HOFSTEDE:* (source_id aus sources.short_code = 'HOFSTEDE'), time_period '2015'

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/culture/load_hofstede.py
      Trockenlauf (Standard): liest die Datei, prüft, vergleicht mit der DB, schreibt NICHTS.
      Zeigt außerdem, welche alten Werte (time_period 'static') falsch zugeordnet waren.
  python scripts/pipeline/culture/load_hofstede.py --schreiben
      schreibt in die DB (alles oder nichts, eine Transaktion), frischt indicator_coverage auf

Regeln (Neufassung 15.11.2026, Backlog #102, Pipeline-Standard Fall 5.4)
-----------------------------------------------------------------------
- Die Datei nutzt EIGENE Dreibuchstaben-Kürzel (Spalte ctr), keine ISO-Codes. Viele sehen aus
  wie ISO3, meinen aber ein anderes Land (BEN = Belgien flämisch, nicht Benin; CAF = Kanada
  französisch, nicht Zentralafrika; MNG = Montenegro, nicht Mongolei; SLV = Slowenien, nicht
  El Salvador). Länder deshalb NUR über die ausdrückliche Liste CTR_ISO3, mit Kontrolle des
  Ländernamens. Der alte Loader nahm die ersten 2 Buchstaben des Namens als ISO2
  (Denmark → DE = Deutschland, Bangladesh → BA = Bosnien …).
- Regionen (Africa East, Arab countries …) und Teilgruppen eines Landes (Belgium French,
  South Africa white …) werden nicht geladen, sondern mit Grund ausgegeben (VERWERFEN).
- Ein ctr, der in keiner der beiden Listen steht, oder ein abweichender Name → Abbruch.
- #NULL! = kein Wert (die Quelle hat für das Land diese Dimension nicht).
- Werte werden wie geliefert geladen (Fassung ohne 0–100-Begrenzung, Höchstwert 112).
  Werte außerhalb 0–120 oder nicht ganzzahlig → Abbruch.
- time_period = '2015' (Jahr der Ausgabe; Regel P19, Entscheidung Julian 14.11.).
- HOFSTEDE:lto kommt aus der Spalte ltowvs (LTO-Fassung auf Basis des World Values Survey).
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt werden neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert (u. a. die alten Zeilen mit time_period 'static'),
  löscht der Loader NICHT, er meldet sie. Entfernt werden sie per Migration mit Liste.
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
log = logging.getLogger("hofstede")

REPO = Path(__file__).resolve().parents[3]
RAW_FILE = REPO / "data" / "raw" / "culture" / "6-dimensions.csv"  # Pfad zentral: #135
SOURCE_CODE = "HOFSTEDE"
TIME_PERIOD = "2015"
KOPF = ["ctr", "country", "pdi", "idv", "mas", "uai", "ltowvs", "ivr"]
WERTEBEREICH = (0, 120)

INDICATOR_COLS = {
    "HOFSTEDE:pdi": "pdi",
    "HOFSTEDE:idv": "idv",
    "HOFSTEDE:mas": "mas",
    "HOFSTEDE:uai": "uai",
    "HOFSTEDE:lto": "ltowvs",
    "HOFSTEDE:ivr": "ivr",
}

# Hofstede-Kürzel → (ISO3, Name genau wie in der Datei). Der Name wird beim Lesen geprüft.
CTR_ISO3 = {
    "ALB": ("ALB", "Albania"),          "ALG": ("DZA", "Algeria"),         "AND": ("AND", "Andorra"),
    "ARG": ("ARG", "Argentina"),        "ARM": ("ARM", "Armenia"),         "AUL": ("AUS", "Australia"),
    "AUT": ("AUT", "Austria"),          "AZE": ("AZE", "Azerbaijan"),      "BAN": ("BGD", "Bangladesh"),
    "BLR": ("BLR", "Belarus"),          "BEL": ("BEL", "Belgium"),         "BOS": ("BIH", "Bosnia"),
    "BRA": ("BRA", "Brazil"),           "BUL": ("BGR", "Bulgaria"),        "BUF": ("BFA", "Burkina Faso"),
    "CAN": ("CAN", "Canada"),           "CHL": ("CHL", "Chile"),           "CHI": ("CHN", "China"),
    "COL": ("COL", "Colombia"),         "COS": ("CRI", "Costa Rica"),      "CRO": ("HRV", "Croatia"),
    "CYP": ("CYP", "Cyprus"),           "CZE": ("CZE", "Czech Rep"),       "DEN": ("DNK", "Denmark"),
    "DOM": ("DOM", "Dominican Rep"),    "ECA": ("ECU", "Ecuador"),         "EGY": ("EGY", "Egypt"),
    "ETH": ("ETH", "Ethiopia"),         "SAL": ("SLV", "El Salvador"),     "EST": ("EST", "Estonia"),
    "FIN": ("FIN", "Finland"),          "FRA": ("FRA", "France"),          "GEO": ("GEO", "Georgia"),
    "GER": ("DEU", "Germany"),          "GHA": ("GHA", "Ghana"),           "GBR": ("GBR", "Great Britain"),
    "GRE": ("GRC", "Greece"),           "GUA": ("GTM", "Guatemala"),       "HOK": ("HKG", "Hong Kong"),
    "HUN": ("HUN", "Hungary"),          "ICE": ("ISL", "Iceland"),         "IND": ("IND", "India"),
    "IDO": ("IDN", "Indonesia"),        "IRA": ("IRN", "Iran"),            "IRQ": ("IRQ", "Iraq"),
    "IRE": ("IRL", "Ireland"),          "ISR": ("ISR", "Israel"),          "ITA": ("ITA", "Italy"),
    "JAM": ("JAM", "Jamaica"),          "JPN": ("JPN", "Japan"),           "JOR": ("JOR", "Jordan"),
    "KOR": ("KOR", "Korea South"),      "KYR": ("KGZ", "Kyrgyz Rep"),      "LAT": ("LVA", "Latvia"),
    "LIT": ("LTU", "Lithuania"),        "LUX": ("LUX", "Luxembourg"),      "MAC": ("MKD", "Macedonia Rep"),
    "MAL": ("MYS", "Malaysia"),         "MLI": ("MLI", "Mali"),            "MLT": ("MLT", "Malta"),
    "MEX": ("MEX", "Mexico"),           "MOL": ("MDA", "Moldova"),         "MNG": ("MNE", "Montenegro"),
    "MOR": ("MAR", "Morocco"),          "NET": ("NLD", "Netherlands"),     "NZL": ("NZL", "New Zealand"),
    "NIG": ("NGA", "Nigeria"),          "NOR": ("NOR", "Norway"),          "PAK": ("PAK", "Pakistan"),
    "PAN": ("PAN", "Panama"),           "PER": ("PER", "Peru"),            "PHI": ("PHL", "Philippines"),
    "POL": ("POL", "Poland"),           "POR": ("PRT", "Portugal"),        "PUE": ("PRI", "Puerto Rico"),
    "ROM": ("ROU", "Romania"),          "RUS": ("RUS", "Russia"),          "RWA": ("RWA", "Rwanda"),
    "SAU": ("SAU", "Saudi Arabia"),     "SER": ("SRB", "Serbia"),          "SIN": ("SGP", "Singapore"),
    "SLK": ("SVK", "Slovak Rep"),       "SLV": ("SVN", "Slovenia"),        "SAF": ("ZAF", "South Africa"),
    "SPA": ("ESP", "Spain"),            "SUR": ("SUR", "Suriname"),        "SWE": ("SWE", "Sweden"),
    "SWI": ("CHE", "Switzerland"),      "TAI": ("TWN", "Taiwan"),          "TAN": ("TZA", "Tanzania"),
    "THA": ("THA", "Thailand"),         "TRI": ("TTO", "Trinidad and Tobago"), "TUR": ("TUR", "Turkey"),
    "USA": ("USA", "U.S.A."),           "UGA": ("UGA", "Uganda"),          "UKR": ("UKR", "Ukraine"),
    "URU": ("URY", "Uruguay"),          "VEN": ("VEN", "Venezuela"),       "VIE": ("VNM", "Vietnam"),
    "ZAM": ("ZMB", "Zambia"),           "ZIM": ("ZWE", "Zimbabwe"),
}

# Nicht geladen. Grund steht im Protokoll und im known_issue.
REGION = "Region aus mehreren Ländern"
TEILGRUPPE = "Teilgruppe eines Landes (Landeswert steht in eigener Zeile)"
VERWERFEN = {
    "AFE": ("Africa East", REGION),        "AFW": ("Africa West", REGION),
    "ARA": ("Arab countries", REGION),
    "BEF": ("Belgium French", TEILGRUPPE), "BEN": ("Belgium Netherl", TEILGRUPPE),
    "CAF": ("Canada French", TEILGRUPPE),  "GEE": ("Germany East", TEILGRUPPE),
    "SAW": ("South Africa white", TEILGRUPPE),
    "SWF": ("Switzerland French", TEILGRUPPE), "SWG": ("Switzerland German", TEILGRUPPE),
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
    df = pd.read_csv(pfad, sep=";", dtype=str, keep_default_na=False)
    kopf = [c.strip() for c in df.columns]
    if kopf != KOPF:
        raise LadeFehler(f"Kopfzeile weicht ab: {kopf} (erwartet {KOPF})")
    df.columns = kopf
    if len(df) == 0:
        raise LadeFehler("0 Zeilen in der Datei")
    return df, sha


def parse(df: pd.DataFrame, iso3_map: dict) -> tuple[dict, Counter, dict]:
    """Gibt {(iso_numeric, code): wert}, Zählbericht und Verworfen-Liste zurück."""
    out, bericht = {}, Counter()
    verworfen = {}
    unbekannt, name_falsch, mehrfach, ungueltig = [], [], [], []
    gesehen = set()

    for _, row in df.iterrows():
        ctr, name = row["ctr"].strip(), row["country"].strip()
        if ctr in gesehen:
            mehrfach.append(ctr)
            continue
        gesehen.add(ctr)

        if ctr in VERWERFEN:
            soll, grund = VERWERFEN[ctr]
            if name != soll:
                name_falsch.append(f"{ctr}: Datei '{name}', Liste '{soll}'")
            werte = sum(1 for col in INDICATOR_COLS.values() if row[col].strip() not in ("", "#NULL!"))
            verworfen[ctr] = (name, grund, werte)
            continue
        if ctr not in CTR_ISO3:
            unbekannt.append(f"{ctr} ({name})")
            continue
        iso3, soll = CTR_ISO3[ctr]
        if name != soll:
            name_falsch.append(f"{ctr}: Datei '{name}', Liste '{soll}'")
            continue
        iso = iso3_map.get(iso3)
        if iso is None:
            unbekannt.append(f"{ctr} → {iso3} fehlt in countries")
            continue

        for code, col in INDICATOR_COLS.items():
            roh = row[col].strip()
            if roh in ("", "#NULL!"):
                bericht["leer"] += 1
                continue
            try:
                wert = float(roh)
            except ValueError:
                ungueltig.append((ctr, col, roh))
                continue
            if not wert.is_integer() or not WERTEBEREICH[0] <= wert <= WERTEBEREICH[1]:
                ungueltig.append((ctr, col, roh))
                continue
            out[(iso, code)] = wert
            if wert > 100:
                bericht["ueber_100"] += 1

    if mehrfach:
        raise LadeFehler(f"ctr mehrfach in der Datei: {mehrfach}")
    if unbekannt:
        raise LadeFehler(f"{len(unbekannt)} Kürzel weder in CTR_ISO3 noch in VERWERFEN: {unbekannt}")
    if name_falsch:
        raise LadeFehler(f"Ländername passt nicht zum Kürzel (Datei geändert?): {name_falsch}")
    if ungueltig:
        raise LadeFehler(f"{len(ungueltig)} Werte nicht ganzzahlig oder außerhalb {WERTEBEREICH}: {ungueltig[:10]}")
    if not out:
        raise LadeFehler("0 Werte gelesen")

    bericht["werte"] = len(out)
    bericht["laender"] = len({k[0] for k in out})
    for code in INDICATOR_COLS:
        bericht[f"werte_{code}"] = sum(1 for k in out if k[1] == code)
    return out, bericht, verworfen


def zeige_verworfen(verworfen: dict):
    log.info(f"  Nicht geladen ({len(verworfen)} Einheiten, Summe Werte {sum(v[2] for v in verworfen.values())}):")
    for ctr, (name, grund, werte) in sorted(verworfen.items(), key=lambda x: (x[1][1], x[0])):
        log.info(f"    {ctr} {name:22} {werte} Werte · {grund}")


# ─── Vergleich mit der DB ─────────────────────────────────────────────────────

def compare(cur, source_id: int, neu: dict) -> dict:
    cur.execute("""SELECT iso_numeric, indicator_code, value FROM indicators
                   WHERE indicator_code LIKE 'HOFSTEDE:%%' AND source_id = %s AND time_period = %s""",
                (source_id, TIME_PERIOD))
    alt = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    c = defaultdict(Counter)
    for (iso, code), w in neu.items():
        a = alt.get((iso, code), "fehlt")
        if a == "fehlt":
            c[code]["neu"] += 1
        elif a is None or abs(a - w) > 1e-9:
            c[code]["wert_geaendert"] += 1
        else:
            c[code]["gleich"] += 1
    for k in set(alt) - set(neu):
        c[k[1]]["nur_in_db"] += 1
    return {k: dict(v) for k, v in sorted(c.items())}


def compare_altbestand(cur, source_id: int, neu: dict, csv_pfad: Path | None) -> dict:
    """Alte Zeilen mit anderem time_period (Ladung 25.05., 'static') gegen die neuen Werte.
    richtig = gleicher Wert am gleichen Land; falsch = anderer Wert; ohne_hofstede = das Land hat in
    der Quelle für diese Dimension gar keinen Wert. Liste als CSV (Grundlage der Migration)."""
    cur.execute("""SELECT i.iso_numeric, c.iso_code_3, c.name, i.indicator_code, i.time_period, i.value
                   FROM indicators i LEFT JOIN countries c USING (iso_numeric)
                   WHERE i.indicator_code LIKE 'HOFSTEDE:%%' AND i.source_id = %s AND i.time_period <> %s
                   ORDER BY i.indicator_code, c.iso_code_3""", (source_id, TIME_PERIOD))
    zeilen = cur.fetchall()
    c = defaultdict(Counter)
    liste = []
    for iso, iso3, name, code, tp, w in zeilen:
        n = neu.get((iso, code))
        if n is None:
            urteil = "ohne_hofstede"
        elif abs(n - w) <= 1e-9:
            urteil = "richtig"
        else:
            urteil = "falsch"
        c[code][urteil] += 1
        liste.append((iso, iso3, name, code, tp, w, n, urteil))
    tps = sorted({z[4] for z in zeilen})
    laender = {z[0] for z in zeilen}
    log.info(f"  Altbestand (time_period {tps}): {len(zeilen)} Zeilen, {len(laender)} Länder; "
             f"richtig {sum(1 for z in liste if z[7] == 'richtig')}, "
             f"falsch {sum(1 for z in liste if z[7] == 'falsch')}, "
             f"ohne Wert der Quelle {sum(1 for z in liste if z[7] == 'ohne_hofstede')}")
    ohne = sorted({f"{z[1]} {z[2]}" for z in liste if z[7] == "ohne_hofstede"})
    if ohne:
        log.info(f"    Länder mit DB-Werten, für die die Quelle (in mind. einer Dimension) keinen Wert hat: {', '.join(ohne)}")
    if csv_pfad:
        csv_pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_pfad, "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["iso_numeric", "iso3", "land", "indicator_code", "time_period", "value_db", "wert_quelle", "urteil"])
            for z in liste:
                wr.writerow(["" if v is None else v for v in z])
        log.info(f"  Liste: {csv_pfad.relative_to(REPO)}")
    return {k: dict(v) for k, v in sorted(c.items())}


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true", help="in die DB schreiben (sonst nur Trockenlauf)")
    ap.add_argument("--datei", type=Path, default=RAW_FILE, help="abweichender Pfad zur Hofstede-CSV")
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
        log.info(f"=== HOFSTEDE {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {len(df)} Zeilen · time_period {TIME_PERIOD} ===")
        neu, bericht, verworfen = parse(df, iso3_map)
        log.info(f"  Gelesen: { {k: v for k, v in sorted(bericht.items())} }")
        zeige_verworfen(verworfen)
        log.info(f"  Vergleich DB (source_id {source_id}, time_period {TIME_PERIOD}): {compare(cur, source_id, neu)}")
        csv_pfad = None if args.schreiben else \
            REPO / "logs" / "migrations" / f"{dt.date.today()}_hofstede_altbestand.csv"
        log.info(f"  Info Altbestand: {compare_altbestand(cur, source_id, neu, csv_pfad)}")
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
    rows = [(iso, code, source_id, TIME_PERIOD, w, "A") for (iso, code), w in neu.items()]
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
                (dt.date.today(), f"2015 csv sha256:{sha}", source_id))   # varchar(50)
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. "
             f"sources.loaded_at/loaded_version gesetzt, indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
