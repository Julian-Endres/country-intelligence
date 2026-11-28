"""
load_gitoc.py — Global Organized Crime Index (GI-TOC), Ausgaben 2021, 2023, 2025
================================================================================
ENTWURF #140/#151 (Claude, Nacht 24./25.11.2026). Ersetzt den GITOC-Teil von load_fsi_gitoc_owid.py.

Datei:   data/raw/governance/global_oc_index.xlsx, Blätter 2021_dataset, 2023_dataset, 2025_dataset
Ziel:    indicators, 17 Codes GITOC:* (source_id aus sources.short_code = 'GITOC'), time_period = Ausgabejahr

Aufruf (Shell, Repo-Wurzel, venv aktiv)
---------------------------------------
  python scripts/pipeline/governance/load_gitoc.py               Trockenlauf, schreibt NICHTS
  python scripts/pipeline/governance/load_gitoc.py --schreiben   schreibt (eine Transaktion)

Befunde, die dieser Loader behebt
---------------------------------
- #140: Namen über countries.name + NAME_OVERRIDES, nicht Zugeordnetes still übersprungen: 8 Länder fehlen in
  allen Ausgaben (beide Koreas, Côte d'Ivoire, São Tomé, St. Kitts, St. Lucia, St. Vincent, Mikronesien),
  2023 zusätzlich beide Kongos ("Congo, Dem, Rep,"). Neu: laender.py + Liste GITOC.csv, Abbruch bei Unbekanntem.
- #151: Spaltennamen wechseln je Ausgabe ("Criminality avg," 2021, "Criminal actors avg," 2023, "Resilience" 2021).
  Der alte Loader verglich exakt und verlor still: criminality/criminal_markets 2021, criminal_actors/resilience
  2021 und 2023. Neu: SPALTEN je Ausgabe ausdrücklich; jede Spalte ist entweder zugeordnet oder steht in
  NICHT_GELADEN (Codes ohne Metadaten, Entscheidung Julian) – sonst Abbruch.

Regeln: Werte 1–10, sonst Abbruch. Eins zu eins je Land und Ausgabe. DO UPDATE nur bei Änderung,
gezählt neu / geändert / unverändert. Werte, die die Datei nicht liefert, werden gemeldet, nicht gelöscht.
Quelle und Metadaten legt der Loader nicht an.
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
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
log = logging.getLogger("gitoc")

RAW_FILE = REPO / "data" / "raw" / "governance" / "global_oc_index.xlsx"   # #135
SOURCE_CODE = "GITOC"
BLAETTER = {2021: "2021_dataset", 2023: "2023_dataset", 2025: "2025_dataset"}
META = {"Continent", "Region", "Country"}

# Gemeinsame Spalten (in allen Ausgaben gleich geschrieben)
GLEICH = {
    "Human trafficking": "GITOC:human_trafficking",
    "Human smuggling": "GITOC:human_smuggling",
    "Arms trafficking": "GITOC:arms_trafficking",
    "Heroin trade": "GITOC:heroin",
    "Cocaine trade": "GITOC:cocaine",
    "Cannabis trade": "GITOC:cannabis",
    "Synthetic drug trade": "GITOC:synthetic_drugs",
    "Mafia-style groups": "GITOC:mafia",
    "State-embedded actors": "GITOC:state_actors",
    "Political leadership and governance": "GITOC:governance",
    "Law enforcement": "GITOC:law_enforcement",
    "Anti-money laundering": "GITOC:aml",
}
# Spalten mit wechselnder Schreibweise, je Ausgabe ausdrücklich
SPALTEN = {
    2021: {**GLEICH,
           "Criminality avg,": "GITOC:criminality",
           "Criminal markets avg,": "GITOC:criminal_markets",
           "Criminal actors": "GITOC:criminal_actors",
           "Resilience": "GITOC:resilience"},
    2023: {**GLEICH,
           "Criminality avg.": "GITOC:criminality",
           "Criminal markets avg.": "GITOC:criminal_markets",
           "Criminal actors avg,": "GITOC:criminal_actors",
           "Resilience avg,": "GITOC:resilience",
           "Financial crimes": "GITOC:financial_crimes"},
    2025: {**GLEICH,
           "Criminality avg.": "GITOC:criminality",
           "Criminal markets avg.": "GITOC:criminal_markets",
           "Criminal actors avg.": "GITOC:criminal_actors",
           "Resilience avg.": "GITOC:resilience",
           "Financial crimes": "GITOC:financial_crimes"},
}
# In der Datei vorhanden, aber (noch) ohne Code und Metadaten. Bewusst nicht geladen – Entscheidung Julian (#151).
NICHT_GELADEN = {
    "Extortion and protection racketeering", "Trade in counterfeit goods", "Illicit trade in excisable goods",
    "Flora crimes", "Fauna crimes", "Non-renewable resource crimes", "Cyber-dependent crimes",
    "Criminal networks", "Foreign actors", "Private sector actors",
    "Government transparency and accountability", "International cooperation", "National policies and laws",
    "Judicial system and detention", "Territorial integrity", "Economic regulatory capacity",
    "Victim and witness support", "Prevention", "Non-state actors",
}
CODES = sorted({c for m in SPALTEN.values() for c in m.values()})


class LadeFehler(Exception):
    pass


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "country_intelligence"),
        user=os.getenv("DB_USER", "postgres"), password=os.getenv("DB_PASSWORD"),
    )


def read_file(pfad: Path) -> tuple[dict, str]:
    if not pfad.exists() or pfad.stat().st_size == 0:
        raise LadeFehler(f"Datei fehlt oder ist leer: {pfad}")
    sha = hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]
    xl = pd.ExcelFile(pfad, engine="openpyxl")
    fehlend = [b for b in BLAETTER.values() if b not in xl.sheet_names]
    if fehlend:
        raise LadeFehler(f"Blätter fehlen: {fehlend}")
    return {j: pd.read_excel(xl, b) for j, b in BLAETTER.items()}, sha


def parse(blaetter: dict, z: Zuordnung) -> tuple[dict, Counter]:
    out, bericht = {}, Counter()
    alle = [(str(n).strip(), j) for j, df in blaetter.items() for n in df["Country"].dropna()]
    z.pruefe_alle(alle)                      # alle Ausgaben auf einmal, Abbruch mit voller Liste
    for jahr, df in blaetter.items():
        spalten = [str(c) for c in df.columns]
        unbekannt = [c for c in spalten if c not in META and c not in SPALTEN[jahr] and c not in NICHT_GELADEN]
        fehlt = [c for c in SPALTEN[jahr] if c not in spalten]
        if unbekannt or fehlt:
            raise LadeFehler(f"{jahr}: Spalten unbekannt {unbekannt}, erwartet aber fehlend {fehlt}")
        bericht[f"{jahr}_nicht_geladen_spalten"] = sum(1 for c in spalten if c in NICHT_GELADEN)
        df = df[df["Country"].notna()]
        namen = [str(n).strip() for n in df["Country"]]
        if len(namen) != len(set(namen)):
            raise LadeFehler(f"{jahr}: Länder mehrfach")
        kaputt = []
        for name, (_, row) in zip(namen, df.iterrows()):
            iso = z.iso_numeric(name, jahr)
            if iso is None:
                bericht[f"{jahr}_verworfen"] += 1
                continue
            for spalte, code in SPALTEN[jahr].items():
                v = row[spalte]
                if pd.isna(v):
                    bericht["ohne_wert"] += 1
                    continue
                try:
                    w = float(v)
                except ValueError:
                    kaputt.append((name, jahr, spalte, v))
                    continue
                if not 1 <= w <= 10:
                    kaputt.append((name, jahr, spalte, v))
                    continue
                out[(iso, code, str(jahr))] = w
            bericht[f"{jahr}_laender"] += 1
        if kaputt:
            raise LadeFehler(f"{len(kaputt)} Werte nicht lesbar oder außerhalb 1–10: {kaputt[:10]}")
    z.pruefe_eindeutig()
    bericht["werte"] = len(out)
    return out, bericht


def compare(cur, source_id: int, neu: dict) -> tuple[Counter, list]:
    cur.execute("""SELECT iso_numeric, indicator_code, time_period, value FROM indicators
                   WHERE source_id = %s AND indicator_code = ANY(%s)""", (source_id, CODES))
    alt = {(r[0], r[1], r[2]): r[3] for r in cur.fetchall()}
    cur.execute("SELECT iso_numeric, iso_code_3 FROM countries")
    i3 = dict(cur.fetchall())
    c, bsp = Counter(), []
    for k, w in neu.items():
        if k not in alt:
            c[f"neu_{k[2]}"] += 1
        elif abs(alt[k] - w) > 1e-9:
            c["geaendert"] += 1
            bsp.append(("geaendert", i3[k[0]], k[1], k[2], alt[k], w))
        else:
            c["gleich"] += 1
    nur_db = sorted(set(alt) - set(neu))
    c["nur_in_db"] = len(nur_db)
    c["db_vorher"] = len(alt)
    return c, bsp[:20] + [("nur_in_db", i3[k[0]], k[1], k[2], alt[k]) for k in nur_db[:20]]


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
        cur.execute("SELECT indicator_code, source_id FROM indicator_metadata WHERE indicator_code = ANY(%s)", (CODES,))
        meta = dict(cur.fetchall())
        fehlend = [c for c in CODES if c not in meta]
        falsch = [c for c in CODES if c in meta and meta[c] != source_id]
        if fehlend or falsch:
            raise LadeFehler(f"Metadaten fehlen {fehlend} oder zeigen auf andere Quelle {falsch}")
        z = Zuordnung.aus_db(cur, SOURCE_CODE, "name")
        blaetter, sha = read_file(args.datei)
        log.info(f"=== GITOC {'SCHREIBEN' if args.schreiben else 'TROCKEN'} · source_id {source_id} · {args.datei.name} (sha256 {sha}…) ===")
        neu, bericht = parse(blaetter, z)
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
    cur.execute("UPDATE sources SET loaded_at = %s, loaded_version = %s WHERE id = %s",
                (dt.date.today(), f"OC Index 2021-2025 xlsx sha256:{sha}", source_id))
    conn.commit()
    cur.execute("REFRESH MATERIALIZED VIEW indicator_coverage")
    conn.commit()
    conn.close()
    log.info(f"=== Geschrieben: {n_neu} neu, {len(res) - n_neu} geändert, {len(rows) - len(res)} unverändert. ===")


if __name__ == "__main__":
    main()
