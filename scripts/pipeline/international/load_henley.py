"""
load_henley.py — Passport Index Dataset (ilyankou, Community-Datensatz zu passportindex.org)
============================================================================================
Hinweis zum Namen: Der Code heißt aus historischen Gründen HENLEY. Die Daten stammen NICHT vom
Henley Passport Index, sondern aus dem archivierten GitHub-Datensatz ilyankou/passport-index-dataset
(Quelle laut README: passportindex.org, letzter Stand 12.01.2025). Siehe Leitfaden der Quelle.

Datei:   data/raw/reference/passport-index-tidy.csv (lokaler Abzug des archivierten Repos)
Ziel:    indicators, Codes HENLEY:visa_free_total, :visa_required, :evisa, :visa_on_arrival
         (source_id aus sources.short_code = 'HENLEY'), time_period 'static' (Entscheidung #87)

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/international/load_henley.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/international/load_henley.py --schreiben   schreibt (eine Transaktion)

Regeln (Neufassung CI-177, Entwurf 25.11.2026)
----------------------------------------------
- Länder NUR über scripts/pipeline/lib/laender.py: exakter Name oder Liste
  scripts/pipeline/lib/laender/HENLEY.csv. Unbekannter Name → Abbruch mit Namensliste.
  Der alte Loader nutzte pycountry.search_fuzzy: Kosovo → Serbien, Swaziland still verworfen (CI-172).
- Zählung je Pass wie bisher (Semantik bewusst NICHT geändert, damit der Pilot nur die
  Länderzuordnung prüft):
    visa_required   = "visa required"
    evisa           = "e-visa"
    visa_on_arrival = "visa on arrival"
    visa_free_total = alle Ziele außer "visa required" und -1 (also inkl. e-visa, visa on arrival,
                      eta, visa free, Tageszahlen UND "no admission")
  "no admission" als zugänglich zu zählen ist ein bekannter Mangel (Metadaten-Lauf 23.11. key_info).
  Der Loader zählt ihn getrennt und meldet ihn; Änderung nur nach Entscheidung Julian (NO_ADMISSION).
- Unbekannte Requirement-Werte → Abbruch (P10). Jede Pass-Ziel-Kombination genau einmal.
- Pass und Ziel stehen im selben Namensraum: Auch die ZIELE müssen zugeordnet werden, sonst
  zählt der Loader Ziele, die es bei uns nicht gibt, ohne es zu merken (geprüft, nicht gefiltert).
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt: neu / geändert / unverändert.
- Werte in der DB, die die Datei nicht liefert, löscht der Loader NICHT, er meldet sie.
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
from collections import Counter, defaultdict
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
log = logging.getLogger("henley")

RAW_FILE = REPO / "data" / "raw" / "reference" / "passport-index-tidy.csv"   # #135
SOURCE_CODE = "HENLEY"
TIME_PERIOD = "static"
CODES = ("HENLEY:visa_free_total", "HENLEY:visa_required", "HENLEY:evisa", "HENLEY:visa_on_arrival")
FESTE_WERTE = {"visa required", "e-visa", "visa on arrival", "visa free", "eta", "no admission", "-1"}
NO_ADMISSION = "zugaenglich"   # bisheriges Verhalten; Alternative "nicht_zugaenglich" (Entscheidung Julian)


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
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    df = pd.read_csv(pfad, dtype=str, keep_default_na=False)
    if list(df.columns) != ["Passport", "Destination", "Requirement"]:
        raise LadeFehler(f"Spalten unerwartet: {list(df.columns)}")
    return df, sha


def klasse(req: str) -> str:
    r = req.strip().lower()
    if r.isdigit():
        return "visa_free"
    if r not in FESTE_WERTE:
        raise LadeFehler(f"Requirement {req!r} unbekannt")
    return {"visa required": "visa_required", "e-visa": "evisa", "visa on arrival": "visa_on_arrival",
            "visa free": "visa_free", "eta": "eta", "no admission": "no_admission", "-1": "selbst"}[r]


def parse(df: pd.DataFrame, z: Zuordnung) -> tuple[dict, Counter]:
    dup = df.duplicated(["Passport", "Destination"]).sum()
    if dup:
        raise LadeFehler(f"{dup} Pass-Ziel-Paare mehrfach")
    namen = sorted(set(df.Passport) | set(df.Destination))
    z.pruefe_alle([(n, None) for n in namen])           # Pässe UND Ziele, Abbruch mit voller Liste

    df = df.assign(klasse=[klasse(r) for r in df.Requirement])
    selbst_falsch = df[(df.klasse == "selbst") != (df.Passport == df.Destination)]
    if len(selbst_falsch):
        raise LadeFehler(f"-1 nicht genau bei Pass = Ziel: {selbst_falsch.head(5).values.tolist()}")

    ziel_iso = {n: z.iso_numeric(n) for n in sorted(set(df.Destination))}   # zählt Wege der Ziele
    bericht = Counter()
    bericht["ziele_verworfen_paare"] = int(df.Destination.map(lambda n: ziel_iso[n] is None).sum())

    out, verteilung = {}, defaultdict(Counter)
    for passport, grp in df.groupby("Passport"):
        iso = z.iso_numeric(passport)
        if iso is None:
            bericht["paesse_verworfen"] += 1
            continue
        k = grp.klasse.value_counts()
        verteilung[iso] = k
        zugaenglich = int(k.get("visa_free", 0) + k.get("eta", 0) + k.get("evisa", 0) + k.get("visa_on_arrival", 0))
        if NO_ADMISSION == "zugaenglich":
            zugaenglich += int(k.get("no_admission", 0))
        werte = {
            "HENLEY:visa_free_total": zugaenglich,
            "HENLEY:visa_required": int(k.get("visa_required", 0)),
            "HENLEY:evisa": int(k.get("evisa", 0)),
            "HENLEY:visa_on_arrival": int(k.get("visa_on_arrival", 0)),
        }
        for code, w in werte.items():
            key = (iso, code, TIME_PERIOD)
            if key in out:
                raise LadeFehler(f"Doppelt: {key}")
            out[key] = float(w)
        bericht["paesse"] += 1
        if k.get("no_admission", 0):
            bericht["paesse_mit_no_admission"] += 1
            bericht["no_admission_paare"] += int(k.get("no_admission", 0))
    z.pruefe_eindeutig()
    if not out:
        raise LadeFehler("0 Werte gelesen")
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, list(CODES)))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    c, beispiele = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c["neu"] += 1
            beispiele.append(("neu", k, w))
        elif alt[k] is None or abs(alt[k] - w) > 1e-9:
            c["wert_geaendert"] += 1
            beispiele.append(("geaendert", k, alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return c, beispiele[:30] + [("nur_in_db", k, alt[k]) for k in nur_db[:15]]


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
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources. Der Loader legt sie nicht an.")
        source_id = r[0]
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (list(CODES),))
        meta = dict(cur.fetchall())
        fehlend = [c for c in CODES if c not in meta]
        falsch = [c for c in CODES if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "name")

        df, sha = read_file(args.datei)
        log.info(f"=== HENLEY {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · "
                 f"{args.datei.name} (sha256 {sha}…) · {len(df)} Zeilen ===")
        neu, bericht = parse(df, z)
        log.info(f"  Gelesen: {dict(sorted(bericht.items()))}")
        if bericht.get("no_admission_paare"):
            log.warning(f"  'no admission' zählt als zugänglich (NO_ADMISSION={NO_ADMISSION!r}): "
                        f"{bericht['no_admission_paare']} Paare bei {bericht['paesse_mit_no_admission']} Pässen")
        log.info(f"  {z.bericht_text()}")
        vergleich, beispiele = compare(cur, source_id, neu)
        log.info(f"  Vergleich DB: {dict(sorted(vergleich.items()))}")
        for b in beispiele:
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

    rows = [(iso, code, source_id, tp, w, "A") for (iso, code, tp), w in neu.items()]
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
                (dt.date.today(), f"passport-index 2025-01-12 sha256:{sha}", source_id))   # varchar(50)
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {n_geaendert} geändert, {n_gleich} unverändert. "
             f"sources.loaded_at/loaded_version gesetzt, indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
