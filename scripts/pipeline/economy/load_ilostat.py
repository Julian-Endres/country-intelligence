"""
load_ilostat.py — ILOSTAT, 9 Arbeitsmarkt-Indikatoren
=====================================================
Quelle:  ILOSTAT, rplumber.ilo.org/data/indicator/?id=<ID>&format=.csv
Ziel:    indicators (source_id aus sources.short_code = 'ILO')

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/economy/load_ilostat.py --trocken
      lädt herunter, speichert Rohdaten, prüft, vergleicht mit der DB, schreibt NICHTS
  python scripts/pipeline/economy/load_ilostat.py --trocken --rohdaten 2026-11-14
      wie oben, aber aus gespeicherten Rohdaten statt neu herunterladen
  python scripts/pipeline/economy/load_ilostat.py --rohdaten 2026-11-14
      schreibt in die DB (nur aus geprüften Rohdaten, alles oder nichts)

Regeln (Umbau 14.11.2026, Backlog-Bezug #1, #86, #110)
------------------------------------------------------
- Rohdaten je Abruf nach data/raw/ilo/<datum>/<ID>.csv.
- Die ILO-Schnittstelle (Cloudflare) liefert ohne Browser-Kennung 0 Bytes bei HTTP 200.
  Deshalb fester User-Agent, und 0 Zeilen sind ein FEHLER, kein leeres Ergebnis.
- Je Land und Jahr genau eine Zeile nach dem Filter, sonst Abbruch.
- Aggregate (ref_area beginnt mit X) werden gezählt, andere nicht zugeordnete Codes aufgelistet.
- ON CONFLICT … DO UPDATE. Werte in der DB, die in der Lieferung fehlen, werden nur gemeldet.
- Quelle und Metadaten legt der Loader nicht an. Fehlen sie, bricht er ab.
- obs_status: wie geliefert, leer → 'A'. Flags und Prognosen klärt #86, nicht dieser Loader.
"""

import argparse
import csv
import datetime as dt
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

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ilo")

REPO = Path(__file__).resolve().parents[3]
RAW_DIR = REPO / "data" / "raw" / "ilo"
BASE_URL = "https://rplumber.ilo.org/data/indicator/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"
SOURCE_CODE = "ILO"
YEAR_FROM = 2000
REQUIRED_COLS = {"ref_area", "time", "obs_value"}  # sex/classif1/obs_status je nach Datensatz, siehe prepare()

# code = Code in der DB, ilo_id = ILOSTAT-Datensatz.
# sex: nur SEX_T, außer no_sex_filter. classif1_keep: None = keine Einschränkung.
# Name, Einheit, Beschreibung stehen in indicator_metadata (dort pflegen, nicht hier).
INDICATORS = [
    {"code": "ILO:EAP_DWAP_SEX_AGE_RT", "ilo_id": "EAP_DWAP_SEX_AGE_RT_A", "classif1_keep": ["AGE_YTHADULT_YGE15"]},
    {"code": "ILO:SDG_0852_SEX_AGE_RT", "ilo_id": "SDG_0852_SEX_AGE_RT_A", "classif1_keep": ["AGE_YTHADULT_YGE15"]},
    {"code": "ILO:SDG_0831_SEX_ECO_RT", "ilo_id": "SDG_0831_SEX_ECO_RT_A", "classif1_keep": ["ECO_AGGREGATE_TOTAL"]},
    {"code": "ILO:EAR_EHRA_SEX_NB",     "ilo_id": "EAR_EHRA_SEX_NB_A",     "classif1_keep": None},
    {"code": "ILO:ILR_TUMT_NOC_RT",     "ilo_id": "ILR_TUMT_NOC_RT",       "classif1_keep": None, "no_sex_filter": True},
    {"code": "ILO:EMP_2EMP_SEX_STE_NB", "ilo_id": "EMP_2EMP_SEX_STE_NB_A", "classif1_keep": ["STE_AGGREGATE_TOTAL"]},
    {"code": "ILO:EMP_TEMP_SEX_ECO_NB", "ilo_id": "EMP_TEMP_SEX_ECO_NB",   "classif1_keep": ["ECO_ISIC4_TOTAL"]},
    {"code": "ILO:HOW_2TOT_SEX_NB",     "ilo_id": "HOW_2TOT_SEX_NB_A",     "classif1_keep": None},
    {"code": "ILO:HOW_TEMP_SEX_ECO_NB", "ilo_id": "HOW_TEMP_SEX_ECO_NB_A", "classif1_keep": ["ECO_ISIC4_TOTAL"]},
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


# ─── Abruf und Rohdaten ───────────────────────────────────────────────────────

def download(ilo_id: str, ziel: Path) -> None:
    url = f"{BASE_URL}?id={ilo_id}&format=.csv"
    letzter = None
    for versuch in range(1, 4):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=180)
            r.raise_for_status()
            if not r.content:
                raise LadeFehler(f"{ilo_id}: HTTP {r.status_code}, 0 Bytes (Bot-Sperre oder ID unbekannt)")
            ziel.write_bytes(r.content)
            log.info(f"  Rohdaten: {ziel.relative_to(REPO)} ({len(r.content):,} Bytes)")
            return
        except requests.RequestException as e:
            letzter = e
            log.warning(f"  Versuch {versuch}/3 fehlgeschlagen: {e}")
            time.sleep(5 * versuch)
    raise LadeFehler(f"{ilo_id}: Abruf nach 3 Versuchen gescheitert: {letzter}")


def read_raw(pfad: Path) -> list[dict]:
    """Liest die CSV. Pflicht sind nur ref_area, time, obs_value; weitere Spalten prüft prepare()."""
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Rohdatei fehlt oder ist leer: {pfad.relative_to(REPO)}")
    with pfad.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fehlend = REQUIRED_COLS - set(reader.fieldnames or [])
        if fehlend:
            raise LadeFehler(f"{pfad.name}: Spalten fehlen: {sorted(fehlend)}")
        rows = list(reader)
    if not rows:
        raise LadeFehler(f"{pfad.name}: 0 Datenzeilen")
    return rows


# ─── Filter und Zuordnung ─────────────────────────────────────────────────────

def prepare(raw: list[dict], ind: dict, country_map: dict, source_id: int) -> tuple[dict, dict]:
    """Gibt {(iso_numeric, jahr): (wert, status)} und einen Zählbericht zurück."""
    keep = ind["classif1_keep"]
    spalten = set(raw[0])
    if not ind.get("no_sex_filter") and "sex" not in spalten:
        raise LadeFehler(f"{ind['code']}: Spalte sex fehlt, Geschlechterfilter nicht möglich")
    if keep and "classif1" not in spalten:
        raise LadeFehler(f"{ind['code']}: Spalte classif1 fehlt, Filter {keep} nicht möglich")
    if ind.get("no_sex_filter") and "sex" in spalten:
        raise LadeFehler(f"{ind['code']}: no_sex_filter gesetzt, aber Datei hat eine Spalte sex")
    out, bericht = {}, Counter()
    nicht_zugeordnet, aggregate, mehrfach = set(), set(), []
    classif1_gesehen = Counter()

    for row in raw:
        if not ind.get("no_sex_filter") and row["sex"] != "SEX_T":
            continue
        c1 = row.get("classif1", "")
        classif1_gesehen[c1] += 1
        if keep and c1 not in keep:
            continue
        jahr = row["time"].strip()
        if not jahr.isdigit():
            raise LadeFehler(f"{ind['code']}: Zeitangabe nicht jährlich: {jahr!r}")
        if int(jahr) < YEAR_FROM:
            bericht["vor_" + str(YEAR_FROM)] += 1
            continue
        if row["obs_value"] in ("", None):
            bericht["ohne_wert"] += 1
            continue
        try:
            wert = float(row["obs_value"])
        except ValueError:
            raise LadeFehler(f"{ind['code']}: Wert nicht numerisch: {row['obs_value']!r} ({row['ref_area']} {jahr})")
        area = row["ref_area"]
        iso = country_map.get(area)
        if not iso:
            (aggregate if area.startswith("X") else nicht_zugeordnet).add(area)
            continue
        key = (iso, jahr)
        if key in out:
            mehrfach.append((area, jahr))
            continue
        out[key] = (wert, (row.get("obs_status") or "A")[:10])
        bericht["status_" + out[key][1]] += 1

    if mehrfach:
        raise LadeFehler(f"{ind['code']}: {len(mehrfach)} Land-Jahre mehrfach, z. B. {mehrfach[:5]}. "
                         f"classif1 gesehen: {dict(classif1_gesehen.most_common(8))}")
    if not out:
        raise LadeFehler(f"{ind['code']}: 0 Zeilen nach Filter. classif1 gesehen: {dict(classif1_gesehen.most_common(8))}")

    bericht["zeilen"] = len(out)
    bericht["laender"] = len({k[0] for k in out})
    bericht["aggregate_verworfen"] = len(aggregate)
    jahre = sorted({k[1] for k in out})
    bericht["von"], bericht["bis"] = jahre[0], jahre[-1]
    bericht["ab_laufendem_jahr"] = sum(1 for k in out if int(k[1]) >= dt.date.today().year)
    bericht["nicht_zugeordnet"] = sorted(nicht_zugeordnet)
    return out, bericht


def compare(cur, code: str, source_id: int, neu: dict) -> Counter:
    cur.execute("""SELECT iso_numeric, time_period, value, obs_status FROM indicators
                   WHERE indicator_code = %s AND source_id = %s""", (code, source_id))
    alt = {(r[0], r[1]): (float(r[2]) if r[2] is not None else None, r[3]) for r in cur.fetchall()}
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


# ─── Hauptlauf ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trocken", action="store_true", help="nichts in die DB schreiben")
    ap.add_argument("--rohdaten", metavar="DATUM", help="gespeicherte Rohdaten data/raw/ilo/DATUM nutzen statt herunterladen")
    args = ap.parse_args()

    if not args.trocken and not args.rohdaten:
        sys.exit("Schreiben nur aus gespeicherten, vorher trocken geprüften Rohdaten: --rohdaten DATUM angeben.")

    datum = args.rohdaten or dt.date.today().isoformat()
    ordner = RAW_DIR / datum
    if not args.rohdaten:
        ordner.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM sources WHERE short_code = %s", (SOURCE_CODE,))
    r = cur.fetchone()
    if not r:
        sys.exit(f"Quelle {SOURCE_CODE} fehlt in sources. Der Loader legt sie nicht an.")
    source_id = r[0]
    cur.execute("SELECT indicator_code FROM indicator_metadata WHERE indicator_code = ANY(%s)",
                ([i["code"] for i in INDICATORS],))
    fehlende_meta = {i["code"] for i in INDICATORS} - {x[0] for x in cur.fetchall()}
    if fehlende_meta:
        sys.exit(f"Metadaten fehlen für {sorted(fehlende_meta)}. Der Loader legt sie nicht an.")
    cur.execute("SELECT iso_code_3, iso_numeric FROM countries WHERE iso_code_3 IS NOT NULL")
    country_map = dict(cur.fetchall())

    log.info(f"=== ILOSTAT {'TROCKEN' if args.trocken else 'SCHREIBEN'} · source_id {source_id} · Rohdaten {ordner.relative_to(REPO)} ===")

    fertig, fehler = {}, []
    for ind in INDICATORS:
        log.info(f"[{ind['code']}]")
        pfad = ordner / f"{ind['ilo_id']}.csv"
        try:
            if not args.rohdaten:
                download(ind["ilo_id"], pfad)
                time.sleep(1.5)
            neu, bericht = prepare(read_raw(pfad), ind, country_map, source_id)
        except LadeFehler as e:
            log.error(f"  FEHLER: {e}")
            fehler.append(str(e))
            continue
        vergleich = compare(cur, ind["code"], source_id, neu)
        fertig[ind["code"]] = neu
        log.info(f"  {bericht['zeilen']:,} Zeilen · {bericht['laender']} Länder · {bericht['von']}–{bericht['bis']} · "
                 f"Aggregate verworfen {bericht['aggregate_verworfen']} · ab laufendem Jahr {bericht['ab_laufendem_jahr']}")
        log.info(f"  Status: { {k[7:]: v for k, v in bericht.items() if k.startswith('status_')} }")
        if bericht["nicht_zugeordnet"]:
            log.warning(f"  Nicht zugeordnet (kein Eintrag in countries): {bericht['nicht_zugeordnet']}")
        log.info(f"  Vergleich DB: {dict(vergleich)}")

    if fehler:
        log.error(f"=== {len(fehler)} von {len(INDICATORS)} Indikatoren fehlerhaft. Es wird NICHTS geschrieben. ===")
        conn.rollback()
        conn.close()
        sys.exit(1)

    if args.trocken:
        log.info("=== Trocken: alle Indikatoren geprüft, nichts geschrieben. ===")
        conn.rollback()
        conn.close()
        return

    # Schreiben: alles oder nichts in einer Transaktion
    eingefuegt = aktualisiert = 0
    for code, neu in fertig.items():
        rows = [(iso, code, source_id, jahr, w, s) for (iso, jahr), (w, s) in neu.items()]
        res = execute_values(cur, """
            INSERT INTO indicators (iso_numeric, indicator_code, source_id, time_period, value, obs_status)
            VALUES %s
            ON CONFLICT (iso_numeric, indicator_code, source_id, time_period) DO UPDATE
            SET value = EXCLUDED.value, obs_status = EXCLUDED.obs_status, last_updated = CURRENT_TIMESTAMP
            RETURNING (xmax = 0)
        """, rows, page_size=1000, fetch=True)
        neu_n = sum(1 for x in res if x[0])
        eingefuegt += neu_n
        aktualisiert += len(res) - neu_n
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"rplumber-Abruf {datum}", source_id))
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {eingefuegt:,} neu, {aktualisiert:,} aktualisiert. sources.loaded_at gesetzt. ===")


if __name__ == "__main__":
    main()
