"""
load_cpi.py — Corruption Perceptions Index (Transparency International), 2012–2025
==================================================================================
Quelle:  Transparency International, CPI 2025, Blatt „CPI Timeseries 2012 - 2025"
Datei:   data/raw/economy/CPI2025_Results.xlsx (Strict-Open-XML; openpyxl liest das nicht direkt,
         read_file() setzt die Namensräume im Speicher um. Die Datei selbst bleibt unverändert.)
Ziel:    indicators, Code TI:CPI (source_id aus sources.short_code = 'TI')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/economy/load_cpi.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/economy/load_cpi.py --schreiben   schreibt (eine Transaktion)

Regeln (Neufassung CI-177, Entwurf 25.11.2026)
----------------------------------------------
- Bisher: OWID-Katalogsuche „corruption" + pycountry.search_fuzzy. Die Suche liefert inzwischen einen
  anderen Datensatz (KeyError 'cpi_score'); die Fuzzy-Suche legte Niger auf Nigeria (CI-172).
- Neu: die TI-Datei selbst. Länder über die ISO3-Spalte der Quelle (Code vor Name, laender.py art="iso3",
  Liste scripts/pipeline/lib/laender/TI.csv nur für Abweichungen). Unbekannter Code → Abbruch.
- Nur 2012–2025: TI erklärt die Werte erst ab 2012 für vergleichbar (neue Methode); ältere Ausgaben
  (Blatt „CPI Historical") werden nicht geladen.
- Werte 0–100, ganzzahlig. Leer = nicht bewertet → kein Wert. Alles andere → Abbruch.
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt: neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert, löscht der Loader NICHT, er meldet sie.
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import datetime as dt
import hashlib
import io
import logging
import os
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "pipeline"))
from lib.laender import LaenderFehler, Zuordnung  # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ti")

RAW_FILE = REPO / "data" / "raw" / "economy" / "CPI2025_Results.xlsx"   # #135
SHEET = "CPI Timeseries 2012 - 2025"
HEADER_ROW = 3
SOURCE_CODE = "TI"
CODE = "TI:CPI"
JAHRE = range(2012, 2026)

STRICT_NS = [
    (b"http://purl.oclc.org/ooxml/spreadsheetml/main", b"http://schemas.openxmlformats.org/spreadsheetml/2006/main"),
    (b"http://purl.oclc.org/ooxml/officeDocument/relationships", b"http://schemas.openxmlformats.org/officeDocument/2006/relationships"),
    (b"http://purl.oclc.org/ooxml/drawingml/main", b"http://schemas.openxmlformats.org/drawingml/2006/main"),
    (b"http://purl.oclc.org/ooxml/drawingml/chart", b"http://schemas.openxmlformats.org/drawingml/2006/chart"),
    (b"http://purl.oclc.org/ooxml/drawingml/spreadsheetDrawing", b"http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"),
    (b"http://purl.oclc.org/ooxml/officeDocument/extendedProperties", b"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"),
    (b' conformance="strict"', b""),
]


class LadeFehler(Exception):
    pass


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )


def read_file(pfad: Path) -> tuple[pd.DataFrame, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    roh = pfad.read_bytes()
    sha = hashlib.sha256(roh).hexdigest()[:16]
    ziel = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(roh)) as zi, zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            b = zi.read(it.filename)
            if it.filename.endswith((".xml", ".rels")):
                for a, c in STRICT_NS:
                    b = b.replace(a, c)
            zo.writestr(it, b)
    ziel.seek(0)
    xl = pd.ExcelFile(ziel, engine="openpyxl")
    if SHEET not in xl.sheet_names:
        raise LadeFehler(f"Blatt {SHEET!r} fehlt, vorhanden: {xl.sheet_names}")
    df = pd.read_excel(xl, SHEET, header=HEADER_ROW, dtype={"ISO3": str})
    if list(df.columns[:2]) != ["Country / Territory", "ISO3"]:
        raise LadeFehler(f"Kopf unerwartet: {list(df.columns[:3])}")
    return df, sha


def wertspalten(df: pd.DataFrame) -> dict:
    out = {}
    for c in df.columns:
        m = re.fullmatch(r"CPI [Ss]core (\d{4})", str(c).strip())
        if m:
            out[int(m.group(1))] = c
    if sorted(out) != list(JAHRE):
        raise LadeFehler(f"Jahresspalten {sorted(out)} ≠ {list(JAHRE)}")
    return out


def parse(df: pd.DataFrame, z: Zuordnung) -> tuple[dict, Counter]:
    spalten = wertspalten(df)
    df = df[df["ISO3"].notna()]
    if df["ISO3"].duplicated().any():
        raise LadeFehler(f"ISO3 mehrfach: {df.loc[df.ISO3.duplicated(), 'ISO3'].tolist()}")
    z.pruefe_alle([(c, j) for c in df["ISO3"] for j in JAHRE])
    out, bericht, kaputt = {}, Counter(), []
    for _, row in df.iterrows():
        for jahr, col in spalten.items():
            v = row[col]
            if pd.isna(v) or str(v).strip() in ("", "-"):
                bericht["ohne_wert"] += 1
                continue
            try:
                w = float(v)
            except ValueError:
                kaputt.append((row["ISO3"], jahr, v))
                continue
            if not (0 <= w <= 100 and w.is_integer()):
                kaputt.append((row["ISO3"], jahr, v))
                continue
            iso = z.iso_numeric(row["ISO3"], jahr)
            if iso is None:
                bericht["verworfen"] += 1
                continue
            out[(iso, str(jahr))] = w
    if kaputt:
        raise LadeFehler(f"{len(kaputt)} Werte nicht lesbar oder außerhalb 0–100: {kaputt[:20]}")
    z.pruefe_eindeutig()
    if not out:
        raise LadeFehler("0 Werte gelesen")
    bericht["werte"] = len(out)
    for j in JAHRE:
        bericht[f"jahr_{j}"] = sum(1 for k in out if k[1] == str(j))
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = %s""", (source_id, CODE))
    alt = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
    i3 = dict(cur.fetchall())
    c, bsp = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c["neu"] += 1
            c[f"neu_{k[1]}"] += 1 if k[1] == "2025" else 0
            if k[1] != "2025":
                bsp.append(("neu", i3[k[0]], k[1], w))
        elif abs(alt[k] - w) > 1e-9:
            c["wert_geaendert"] += 1
            bsp.append(("geaendert", i3[k[0]], k[1], alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return +c, bsp[:40] + [("nur_in_db", i3[k[0]], k[1], alt[k]) for k in nur_db[:20]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true")
    ap.add_argument("--datei", type=Path, default=RAW_FILE)
    args = ap.parse_args()

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources.")
        source_id = r[0]
        cur.execute("SELECT source_id FROM indicator_metadata WHERE indicator_code = %s", (CODE,))
        r = cur.fetchone()
        if not r or r[0] != source_id:
            raise LadeFehler(f"Metadaten für {CODE} fehlen oder zeigen auf andere Quelle ({r})")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "iso3")
        df, sha = read_file(args.datei)
        log.info(f"=== TI {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {len(df)} Zeilen ===")
        neu, bericht = parse(df, z)
        log.info(f"  Gelesen: {dict(sorted(bericht.items()))}")
        log.info(f"  {z.bericht_text()}")
        vergleich, bsp = compare(cur, source_id, neu)
        log.info(f"  Vergleich DB: {dict(sorted(vergleich.items()))}")
        for b in bsp:
            log.info(f"    {b}")
    except (LadeFehler, LaenderFehler) as e:
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

    rows = [(iso, CODE, source_id, jahr, w, "A") for (iso, jahr), w in neu.items()]
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
                (dt.date.today(), f"CPI 2025 xlsx sha256:{sha}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. ===")


if __name__ == "__main__":
    main()
