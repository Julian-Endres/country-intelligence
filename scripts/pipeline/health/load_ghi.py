"""
load_ghi.py — Global Hunger Index (GHI), nur Bericht 2025
=========================================================
Quelle:  Welthungerhilfe / Concern Worldwide, GHI-Bericht 2025, Tabelle „GHI Scores 2025"
Datei:   data/raw/health/2025_global Hunger index.xlsx (Blatt „GHI Scores 2025 ")
Ziel:    indicators, Code GHI:score (source_id aus sources.short_code = 'GHI')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/health/load_ghi.py
      Trockenlauf (Standard): liest die Datei, prüft, vergleicht mit der DB, schreibt NICHTS
  python scripts/pipeline/health/load_ghi.py --schreiben
      schreibt in die DB (alles oder nichts, eine Transaktion), frischt indicator_coverage auf

Regeln (Neufassung 15.11.2026, Backlog #1, Pipeline-Standard #110 Fall 2 „Datei")
-------------------------------------------------------------------------------
- NUR der Bericht 2025 (Jahre 2000, 2008, 2016, 2025). GHI-Werte sind nur innerhalb eines
  Berichts vergleichbar, jeder Bericht rechnet die Referenzjahre neu (Entscheidung Julian 15.11.,
  Begründung des Herausgebers). Ältere Berichte bleiben in data/raw/health, werden nicht geladen.
- "<5" (niedriger Hunger, kein Wert veröffentlicht) → 2.5 mit obs_status 'E' (Schätzung,
  Mitte von 0–5). "—" = keine Daten → kein Wert. Alles andere Nicht-Numerische → Abbruch.
- Länder nur über exakten Namen oder die ausdrückliche Liste OVERRIDES_ISO3.
  KEINE unscharfe Suche (pycountry fuzzy hat bei CAF „Columbia" → Kanada gemacht).
  Nicht zugeordnete Namen → Abbruch mit Namensliste.
- Kopfzeile wird geprüft (Jahre 2000/2008/2016/2025 in Spalten 1–4), sonst Abbruch.
- Genau eine Zeile je Land und Jahr, sonst Abbruch.
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt werden neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert, löscht der Loader NICHT, er meldet sie
  (u. a. die alten Zeilen ohne source_id; die entfernt eine Migration mit Liste).
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ghi")

REPO = Path(__file__).resolve().parents[3]
RAW_FILE = REPO / "data" / "raw" / "health" / "2025_global Hunger index.xlsx"   # Pfad zentral: #135
SHEET = "GHI Scores 2025 "
SOURCE_CODE = "GHI"
CODE = "GHI:score"
REPORT = "GHI-Bericht 2025"
YEAR_COLS = {1: "2000", 2: "2008", 3: "2016", 4: "2025"}
HEADER_ROW = 2          # Zeile mit „Country … 2000 … 2025"
LOW_VALUE = 2.5         # "<5"
LOW_STATUS = "E"

# GHI-Schreibweise → ISO3. Nur Namen, die nicht exakt in countries.name (RestCountries) stehen.
OVERRIDES_ISO3 = {
    "bolivia (plurinat. state of)": "BOL",
    "bosnia and herzegovina": "BIH",
    "cabo verde": "CPV",
    "congo (republic of)": "COG",
    "cote d'ivoire": "CIV",
    "dem. rep. of the congo": "COD",
    "iran (islamic republic of)": "IRN",
    "korea (dpr)": "PRK",
    "lao pdr": "LAO",
    "moldova (rep. of)": "MDA",
    "russian federation": "RUS",
    "syrian arab republic": "SYR",
    "tanzania (united rep. of)": "TZA",
    "trinidad and tobago": "TTO",
    "turkiye": "TUR",
    "venezuela (boliv. rep. of)": "VEN",
    "viet nam": "VNM",
}


class LadeFehler(Exception):
    pass


def norm(name: str) -> str:
    """Kleinbuchstaben, ohne Akzente, & → and, typografische Apostrophe vereinheitlicht."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = s.replace("’", "'").replace("&", "and").lower()
    return " ".join(s.split())


def get_conn():
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
    df = pd.read_excel(pfad, sheet_name=SHEET, header=None, engine="openpyxl")
    kopf = [str(x) for x in df.iloc[HEADER_ROW, :5]]
    if not kopf[0].lower().startswith("country"):
        raise LadeFehler(f"Kopfzeile unerwartet, Spalte 0: {kopf[0]!r}")
    for col, jahr in YEAR_COLS.items():
        if not kopf[col].startswith(jahr):
            raise LadeFehler(f"Kopfzeile unerwartet, Spalte {col}: {kopf[col]!r} (erwartet {jahr})")
    return df.iloc[HEADER_ROW + 1:], sha


def parse(body: pd.DataFrame, name_map: dict, iso3_map: dict) -> tuple[dict, Counter]:
    """Gibt {(iso_numeric, jahr): (wert, status)} und einen Zählbericht zurück."""
    out, bericht = {}, Counter()
    nicht_zugeordnet, mehrfach = [], []
    for _, row in body.iterrows():
        roh = row.iloc[0]
        if pd.isna(roh):
            continue
        name = str(roh).strip()
        if name.lower().startswith("note") or name.lower().startswith("their present borders"):
            bericht["fussnoten_zeilen"] += 1
            continue
        n = norm(name)
        iso3 = OVERRIDES_ISO3.get(n)
        iso = iso3_map.get(iso3) if iso3 else name_map.get(n)
        if not iso:
            nicht_zugeordnet.append(name)
            continue
        bericht["laender"] += 1
        for col, jahr in YEAR_COLS.items():
            v = row.iloc[col]
            s = "" if pd.isna(v) else str(v).strip()
            if s in ("", "—", "-"):
                bericht["ohne_wert"] += 1
                continue
            if s == "<5":
                wert, status = LOW_VALUE, LOW_STATUS
            else:
                try:
                    wert, status = float(s), "A"
                except ValueError:
                    raise LadeFehler(f"Wert nicht numerisch: {s!r} ({name} {jahr})")
            key = (iso, jahr)
            if key in out:
                mehrfach.append((name, jahr))
                continue
            out[key] = (wert, status)
            bericht[f"status_{status}"] += 1
    if nicht_zugeordnet:
        raise LadeFehler(f"{len(nicht_zugeordnet)} Länder nicht zugeordnet (OVERRIDES_ISO3 ergänzen): {nicht_zugeordnet}")
    if mehrfach:
        raise LadeFehler(f"{len(mehrfach)} Land-Jahre mehrfach: {mehrfach[:10]}")
    if not out:
        raise LadeFehler("0 Werte gelesen")
    bericht["werte"] = len(out)
    for jahr in YEAR_COLS.values():
        bericht[f"jahr_{jahr}"] = sum(1 for k in out if k[1] == jahr)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> Counter:
    cur.execute("""SELECT iso_numeric, time_period, value, obs_status FROM indicators
                   WHERE indicator_code = %s AND source_id = %s""", (CODE, source_id))
    alt = {(r[0], r[1]): (r[2], r[3]) for r in cur.fetchall()}
    c = Counter()
    for k, (w, s) in neu.items():
        if k not in alt:
            c["neu"] += 1
        elif alt[k][0] is None or abs(alt[k][0] - w) > 1e-9:
            c["wert_geaendert"] += 1
        elif alt[k][1] != s:
            c["nur_status_geaendert"] += 1
        else:
            c["gleich"] += 1
    c["nur_in_db"] = len(set(alt) - set(neu))
    c["db_vorher"] = len(alt)
    return c


def compare_altbestand(cur, neu: dict) -> Counter:
    """Info: alte Zeilen OHNE source_id (Ladung 28.05.) gegen die neuen Werte, je Paar die jüngste."""
    cur.execute("""SELECT DISTINCT ON (iso_numeric, time_period) iso_numeric, time_period, value
                   FROM indicators WHERE indicator_code = %s AND source_id IS NULL
                   ORDER BY iso_numeric, time_period, last_updated DESC, id DESC""", (CODE,))
    alt = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    c = Counter()
    for k, (w, _) in neu.items():
        if k not in alt:
            c["neu_gegenueber_alt"] += 1
        elif abs(alt[k] - w) > 1e-9:
            c["abweichend_von_alt"] += 1
        else:
            c["gleich_wie_alt"] += 1
    c["alt_paare_ohne_entsprechung"] = len(set(alt) - set(neu))
    cur.execute("SELECT count(*) FROM indicators WHERE indicator_code = %s AND source_id IS NULL", (CODE,))
    c["alt_zeilen_ohne_source_id"] = cur.fetchone()[0]
    return c


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true", help="in die DB schreiben (sonst nur Trockenlauf)")
    ap.add_argument("--datei", type=Path, default=RAW_FILE, help="abweichender Pfad zur Berichtsdatei")
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources. Der Loader legt sie nicht an.")
        source_id = r[0]
        cur.execute("SELECT source_id FROM indicator_metadata WHERE indicator_code = %s", (CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Metadaten für {CODE} fehlen. Der Loader legt sie nicht an.")
        if r[0] != source_id:
            raise LadeFehler(f"Metadaten von {CODE} zeigen auf source_id {r[0]}, sources.{SOURCE_CODE} ist {source_id}")
        cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
        iso3_map = dict(cur.fetchall())
        cur.execute("SELECT name, iso_numeric FROM countries")
        name_map = {norm(n): i for n, i in cur.fetchall()}
        fehlende_iso3 = sorted(set(OVERRIDES_ISO3.values()) - set(iso3_map))
        if fehlende_iso3:
            raise LadeFehler(f"OVERRIDES_ISO3 nennt Codes, die nicht in countries stehen: {fehlende_iso3}")

        body, sha = read_file(args.datei)
        log.info(f"=== GHI {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) ===")
        neu, bericht = parse(body, name_map, iso3_map)
        log.info(f"  Gelesen: { {k: v for k, v in sorted(bericht.items())} }")
        log.info(f"  Vergleich DB (source_id {source_id}): {dict(compare(cur, source_id, neu))}")
        log.info(f"  Info Altbestand ohne source_id: {dict(compare_altbestand(cur, neu))}")
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

    rows = [(iso, CODE, source_id, jahr, w, s) for (iso, jahr), (w, s) in neu.items()]
    res = execute_values(cur, """
        INSERT INTO indicators (iso_numeric, indicator_code, source_id, time_period, value, obs_status)
        VALUES %s
        ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO UPDATE
        SET value = EXCLUDED.value, obs_status = EXCLUDED.obs_status, last_updated = CURRENT_TIMESTAMP
        WHERE indicators.value IS DISTINCT FROM EXCLUDED.value
           OR indicators.obs_status IS DISTINCT FROM EXCLUDED.obs_status
        RETURNING (xmax = 0)
    """, rows, page_size=1000, fetch=True)
    n_neu = sum(1 for x in res if x[0])
    n_geaendert = len(res) - n_neu
    n_gleich = len(rows) - len(res)
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"GHI 2025 xlsx sha256:{sha}", source_id))   # varchar(50)
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. "
             f"sources.loaded_at/loaded_version gesetzt, indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
