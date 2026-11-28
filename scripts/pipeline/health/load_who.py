"""
load_who.py — WHO Global Health Observatory (GHO OData API), 23 Codes
=====================================================================
ENTWURF CI-174 (Claude, Nacht 24./25.11.2026). Ersetzt load_who.py UND load_who_quickwins.py.
Nicht gegen die API getestet (die API ist aus dem Cloud-Arbeitsbereich gesperrt); die Auswahl je Code
stützt sich auf das Prüfskript vom 24.11. (logs/2026-11-24_who_dims.csv und _nachlauf.csv), die
Logik ist mit Testdaten geprüft (scripts/pipeline/health/test_load_who.py).

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/health/load_who.py                     Trockenlauf aller Codes, schreibt NICHTS
  python scripts/pipeline/health/load_who.py --codes WHO:MDG_0000000003 WHO:NCD_BMI_30A
                                                                 nur diese Codes
  python scripts/pipeline/health/load_who.py --schreiben         schreibt (alles oder nichts)
  python scripts/pipeline/health/load_who.py --rohdaten DIR      API-Antworten als JSON in DIR ablegen
                                                                 (Beleg; empfohlen beim Schreiblauf)

Befund (CI-174), den dieser Loader behebt
-----------------------------------------
- Der alte Loader holte nur SpatialDim, TimeDim, NumericValue. Bei 15 Codes liefert die API je Land-Jahr
  mehrere Zeilen (Geschlecht, Alter, Wohlstandsfünftel, Stadt/Land). Mit ON CONFLICT DO NOTHING gewann die
  ERSTE Zeile – Geschlechter und Altersgruppen sind in der DB gemischt (#92: Teenager-Geburten 10–14 statt 15–19).
- HTTP ≠ 200 oder Ausnahme beendete den Abruf still (Mai: NCD_BMI_MINUS2C, TB_c_newinc leer, #63);
  except: continue beim Insert.

Regeln
------
- AUSWAHL legt je Code fest, welche Dim1/Dim2/Dim3-Werte gelten (None = Dimension muss leer sein).
  Danach muss es GENAU EINE Zeile je Land und Jahr geben, sonst Abbruch (P8).
  Vorschlag Claude laut CI-174, ENTSCHEIDUNG JULIAN: Gesamtbevölkerung (SEX_BTSX, RESIDENCEAREATYPE_TOTL,
  WEALTHQUINTILE_TOTL); Teenager-Geburten 15–19; Diabetes-Häufigkeit und Bewegungsmangel 18+;
  Diabetes-Behandlung 30+ (die API hat nur 30+); Kinder-BMI 5–19.
- Kommt in der API eine Dimensionskombination vor, die in AUSWAHL nicht vorgesehen ist, wird sie gezählt
  und gemeldet (nicht still verworfen).
- Nur SpatialDimType = COUNTRY. Länder über die ISO3-Spalte der Quelle (scripts/pipeline/lib/laender.py,
  art="iso3", Liste scripts/pipeline/lib/laender/WHO.csv für Abweichungen). Unbekannter Code → Abbruch.
- Nur TimeDimType = YEAR, sonst Abbruch. NumericValue leer → kein Wert (gezählt).
- Abruf: 3 Versuche je Seite mit Pause; danach Abbruch mit Code und Seite. 0 Zeilen von der API → Abbruch
  (ein leeres Ergebnis ist ein Befund), außer der Code steht in AUSGESETZT.
- ON CONFLICT … DO UPDATE nur bei echter Änderung; gezählt je Code: neu / geändert / unverändert.
- Werte in der DB, die die Auswahl nicht liefert, löscht der Loader NICHT, er meldet sie je Code.
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
"""

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts" / "pipeline"))
from lib.laender import LaenderFehler, Zuordnung  # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("who")

BASE_URL = "https://ghoapi.azureedge.net/api"
SOURCE_CODE = "WHO"
SEITE = 1000
VERSUCHE = 3

BTSX = "SEX_BTSX"
TOTL = "RESIDENCEAREATYPE_TOTL"

# Code → (Dim1, Dim2, Dim3). None = die Dimension muss in der API leer sein.
# Grundlage: logs/2026-11-24_who_dims.csv / _nachlauf.csv (Julian, 24.11.). ENTSCHEIDUNG JULIAN offen.
AUSWAHL = {
    "WHO:SDGPM25":                       (TOTL, None, None),
    "WHO:WSH_WATER_BASIC":               (TOTL, None, None),
    "WHO:WSH_SANITATION_BASIC":          (TOTL, None, None),
    "WHO:MDG_0000000001":                (BTSX, "AGEGROUP_MONTHS0-11", None),
    "WHO:MDG_0000000007":                (BTSX, "AGEGROUP_YEARSUNDER5", "WEALTHQUINTILE_TOTL"),
    "WHO:WHOSIS_000014":                 (BTSX, None, None),
    "WHO:CHILDMORT5TO14":                (BTSX, "AGEGROUP_YEARS05-14", None),
    "WHO:MDG_0000000003":                ("SEX_FMLE", "AGEGROUP_YEARS15-19", None),
    "WHO:NCD_BMI_30A":                   (BTSX, "AGEGROUP_YEARS18-PLUS", None),
    "WHO:NCD_BMI_25A":                   (BTSX, "AGEGROUP_YEARS18-PLUS", None),
    "WHO:NCD_BMI_18A":                   (BTSX, "AGEGROUP_YEARS18-PLUS", None),
    "WHO:NCD_DIABETES_PREVALENCE_AGESTD": (BTSX, "AGEGROUP_YEARS18-PLUS", None),
    "WHO:NCD_DIABETES_TREATMENT_AGESTD": (BTSX, "AGEGROUP_YEARS30-PLUS", None),
    "WHO:NCD_BMI_PLUS1C":                (BTSX, "AGEGROUP_YEARS05-19", None),
    "WHO:NCD_BMI_MINUS2C":               (BTSX, "AGEGROUP_YEARS05-19", None),
    "WHO:NCD_PAA":                       (BTSX, "AGEGROUP_YEARS18-PLUS", None),
    "WHO:WHS3_62":                       (None, None, None),
    "WHO:WHS3_57":                       (None, None, None),
    "WHO:WHS3_41":                       (None, None, None),
    "WHO:WHS3_43":                       (None, None, None),
    "WHO:WHS3_53":                       (None, None, None),
    "WHO:TB_c_newinc":                   (None, None, None),
    "WHO:UHC_INDEX_REPORTED":            (None, None, None),
}
# Liefert die API heute 0 Zeilen (Prüfskript 24.11.); vermutlich umgestellt (#66). DB-Werte bleiben.
AUSGESETZT = {"WHO:TB_c_new_tsr": "API liefert 0 Zeilen (24.11.), Code vermutlich umgestellt, #66"}


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


# ─── Abruf ────────────────────────────────────────────────────────────────────

def hole(who_code: str, session=None) -> list[dict]:
    """Alle Zeilen eines Codes. Fehler werden laut (LadeFehler), nie still."""
    s = session or requests.Session()
    felder = "SpatialDimType,SpatialDim,TimeDimType,TimeDim,Dim1,Dim2,Dim3,NumericValue"
    alle, skip = [], 0
    while True:
        url = f"{BASE_URL}/{who_code}?$select={felder}&$top={SEITE}&$skip={skip}"
        for versuch in range(1, VERSUCHE + 1):
            try:
                r = s.get(url, timeout=60)
                if r.status_code == 200:
                    batch = r.json().get("value")
                    if batch is None:
                        raise LadeFehler(f"{who_code}: Antwort ohne 'value' (skip {skip})")
                    break
                fehler = f"HTTP {r.status_code}"
            except (requests.RequestException, ValueError) as e:
                fehler = f"{type(e).__name__}: {e}"
            log.warning(f"  {who_code} skip {skip}: Versuch {versuch}/{VERSUCHE} fehlgeschlagen ({fehler})")
            time.sleep(2 * versuch)
        else:
            raise LadeFehler(f"{who_code}: Abruf nach {VERSUCHE} Versuchen fehlgeschlagen (skip {skip}, {fehler})")
        alle.extend(batch)
        if len(batch) < SEITE:
            return alle
        skip += SEITE
        time.sleep(0.1)


# ─── Auswahl und Prüfung ─────────────────────────────────────────────────────

def waehle(code: str, zeilen: list[dict], z: Zuordnung) -> tuple[dict, Counter]:
    """→ {(iso_numeric, jahr): wert}, Zählbericht. Abbruch bei mehr als einer Zeile je Land-Jahr."""
    soll = AUSWAHL[code]
    bericht, kombis = Counter(), Counter()
    treffer = defaultdict(list)
    for r in zeilen:
        if r.get("SpatialDimType") != "COUNTRY":
            bericht["nicht_land"] += 1
            continue
        if r.get("TimeDimType") != "YEAR":
            raise LadeFehler(f"{code}: TimeDimType {r.get('TimeDimType')!r} (nur YEAR erwartet), Beispiel {r}")
        ist = (r.get("Dim1"), r.get("Dim2"), r.get("Dim3"))
        kombis[ist] += 1
        if ist != soll:
            bericht["andere_dimension"] += 1
            continue
        treffer[(r["SpatialDim"], int(r["TimeDim"]))].append(r.get("NumericValue"))
    if not treffer:
        raise LadeFehler(f"{code}: 0 Zeilen mit Auswahl {soll}. Kombinationen in der API: {dict(kombis)}")
    mehrfach = {k: v for k, v in treffer.items() if len(v) > 1}
    if mehrfach:
        raise LadeFehler(f"{code}: {len(mehrfach)} Land-Jahre mehrfach trotz Auswahl {soll}, z. B. {list(mehrfach.items())[:5]}")
    z.pruefe_alle(list(treffer))
    out = {}
    for (iso3, jahr), (wert,) in treffer.items():
        if wert is None:
            bericht["ohne_wert"] += 1
            continue
        iso = z.iso_numeric(iso3, jahr)
        if iso is None:
            bericht["verworfen"] += 1
            continue
        out[(iso, str(jahr))] = float(wert)
    bericht["werte"] = len(out)
    bericht["kombinationen_api"] = len(kombis)
    return out, bericht


def vergleiche(cur, source_id: int, code: str, neu: dict) -> Counter:
    cur.execute("""SELECT iso_numeric, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = %s""", (source_id, code))
    alt = {(r[0], r[1]): r[2] for r in cur.fetchall()}
    c = Counter()
    for k, w in neu.items():
        if k not in alt:
            c["neu"] += 1
        elif alt[k] is None or abs(alt[k] - w) > 1e-9:
            c["geaendert"] += 1
        else:
            c["gleich"] += 1
    c["nur_in_db"] = len(set(alt) - set(neu))
    c["db_vorher"] = len(alt)
    return c


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schreiben", action="store_true")
    ap.add_argument("--codes", nargs="*", help="nur diese Codes (Standard: alle in AUSWAHL)")
    ap.add_argument("--rohdaten", type=Path, help="Ordner für die API-Antworten (JSON je Code)")
    args = ap.parse_args()
    codes = args.codes or list(AUSWAHL)
    unbekannt = [c for c in codes if c not in AUSWAHL]
    if unbekannt:
        sys.exit(f"Codes ohne AUSWAHL: {unbekannt} (ausgesetzt: {AUSGESETZT})")

    conn = get_conn()
    cur = conn.cursor()
    ergebnis = {}
    try:
        cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
        r = cur.fetchone()
        if not r:
            raise LadeFehler(f"Quelle {SOURCE_CODE} fehlt in sources.")
        source_id = r[0]
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (codes,))
        meta = dict(cur.fetchall())
        fehlend = [c for c in codes if c not in meta]
        falsch = [c for c in codes if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "iso3")
        log.info(f"=== WHO {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · {len(codes)} Codes ===")
        if AUSGESETZT:
            log.warning(f"  ausgesetzt (nicht geladen, DB-Werte bleiben): {AUSGESETZT}")
        sess = requests.Session()
        for code in codes:
            zeilen = hole(code.split(":", 1)[1], sess)
            if args.rohdaten:
                args.rohdaten.mkdir(parents=True, exist_ok=True)
                (args.rohdaten / f"{code.replace(':', '_')}.json").write_text(json.dumps(zeilen), encoding="utf-8")
            neu, bericht = waehle(code, zeilen, z)
            v = vergleiche(cur, source_id, code, neu)
            ergebnis[code] = neu
            log.info(f"  {code:36s} API {len(zeilen):6d} · {dict(sorted(bericht.items()))} · DB {dict(sorted(v.items()))}")
        z.pruefe_eindeutig()
        log.info(f"  {z.bericht_text()}")
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

    summe = Counter()
    for code, neu in ergebnis.items():
        rows = [(iso, code, source_id, jahr, w, "A") for (iso, jahr), w in neu.items()]
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
        summe.update(neu=n_neu, geaendert=len(res) - n_neu, unveraendert=len(rows) - len(res))
        log.info(f"  {code:36s} geschrieben: {n_neu} neu, {len(res) - n_neu} geändert, {len(rows) - len(res)} unverändert")
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"GHO API {dt.date.today().isoformat()}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben gesamt: {dict(summe)}. indicator_coverage aufgefrischt. ===")


if __name__ == "__main__":
    main()
