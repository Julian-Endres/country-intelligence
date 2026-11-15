"""
WB-Abgleich: DB gegen Weltbank-API, nur lesend. Für lange Läufe ohne Aufsicht.

Bezug Backlog: #106 (Datenstand veraltet?), #80 (Einheiten fehlen),
#118 (WGI im WDI-Archiv), #3 / #91 (falsche Namen).

Was das Skript tut:
  1. Liest über ci_agent_readonly alle WB-Indikatoren (Metadaten) und
     alle WB-Werte der Jahre --von bis --bis (eine Abfrage, kein Scan je Code).
  2. Holt je Indikator aus der Weltbank-API die Metadaten (Name, Quelle,
     sourceNote) und alle Länderwerte für denselben Zeitraum.
  3. Vergleicht Wert für Wert (Land × Jahr) und die Metadaten.
  4. Schreibt Ergebnisdateien. In die DB schreibt es NICHTS.

Ergebnis in scripts/agent/output/<datum>_wb_abgleich/:
  abgleich.csv          eine Zeile je Indikator (Kennzahlen + Flags)
  abweichungen.csv      die größten Wertabweichungen je Indikator (max. 20)
  fehler.csv            Indikatoren, bei denen die API nicht geantwortet hat
  einheiten_vorschlag.sql  UPDATEs für leere Einheiten, OHNE COMMIT
  zusammenfassung.md    Überblick zum Lesen
  cache.jsonl           Zwischenstand; ein Neustart am selben Tag macht dort weiter

Aufruf aus der Repo-Wurzel (Shell auf dem Mac):
  caffeinate -i python3 scripts/agent/helpers/wb_abgleich.py
  Optionen: --von 2015 --bis 2024 --limit 5 (Testlauf) --neu (Cache ignorieren)
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

REPO = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = REPO / "scripts" / "agent" / "output"
META_URL = "https://api.worldbank.org/v2/indicator/{code}?format=json"
DATA_URL = ("https://api.worldbank.org/v2/country/all/indicator/{code}"
            "?format=json&date={von}:{bis}&per_page=20000&page={page}&source={source}")
PREFIX = "WB:"
WDI_SOURCE_ID = "2"
TOL_GLEICH = 0.001   # bis 0,1 % relative Abweichung gilt als gleich
TOL_GROSS = 0.05     # ab 5 % gilt als große Abweichung
UNIT_MAX_LEN = 50    # indicator_metadata.unit ist VARCHAR(50)


# ---------------------------------------------------------------- DB (nur lesen)

def get_readonly_connection():
    user, password = os.getenv("DB_AGENT_USER"), os.getenv("DB_AGENT_PASSWORD")
    if not user or not password:
        sys.exit("DB_AGENT_USER / DB_AGENT_PASSWORD fehlen in .env")
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
                            database=os.getenv("DB_NAME"), user=user, password=password)
    conn.set_session(readonly=True)
    return conn


def load_db(conn, von, bis):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.indicator_code, m.name, m.unit,
                   (m.description IS NULL OR TRIM(m.description) = '') AS ohne_beschreibung
            FROM indicator_metadata m
            JOIN sources s ON s.id = m.source_id
            WHERE s.short_code = 'WB'
            ORDER BY m.indicator_code;
        """)
        meta = {r[0]: {"name": r[1] or "", "unit": r[2], "ohne_beschreibung": r[3]}
                for r in cur.fetchall()}

        # Jahre als Text: nur reine Jahreszahlen vergleichen (siehe #79, #87)
        cur.execute("""
            SELECT i.indicator_code, c.iso_code_3, i.time_period::int, i.value
            FROM indicators i
            JOIN sources s ON s.id = i.source_id
            JOIN countries c ON c.iso_numeric = i.iso_numeric
            WHERE s.short_code = 'WB'
              AND i.time_period ~ '^\\d{4}$'
              AND i.time_period::int BETWEEN %s AND %s;
        """, (von, bis))
        werte = {}
        for code, iso3, jahr, wert in cur.fetchall():
            werte.setdefault(code, {})[(iso3, jahr)] = wert

        cur.execute("SELECT iso_code_3 FROM countries;")
        laender = {r[0] for r in cur.fetchall()}
    return meta, werte, laender


# ---------------------------------------------------------------- API

class ApiFehler(Exception):
    pass


def get_json(url, versuche=4):
    """GET mit Wiederholung. Wirft ApiFehler, schluckt nichts."""
    letzter = None
    for n in range(versuche):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                raise ApiFehler(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError, ApiFehler) as e:
            letzter = e
            time.sleep(5 * 2 ** n)   # 5, 10, 20, 40 s
    raise ApiFehler(f"{type(letzter).__name__}: {letzter}")


def api_meta(api_code):
    data = get_json(META_URL.format(code=api_code))
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        msg = data[0].get("message") if isinstance(data, list) and data and isinstance(data[0], dict) else data
        raise ApiFehler(f"Kein Indikator in der API: {str(msg)[:200]}")
    item = data[1][0]
    src = item.get("source") or {}
    return {
        "name": (item.get("name") or "").strip(),
        "unit_feld": (item.get("unit") or "").strip(),
        "source_id": str(src.get("id") or ""),
        "source_name": (src.get("value") or "").strip(),
        "hat_sourcenote": bool((item.get("sourceNote") or "").strip()),
    }


def api_werte(api_code, source_id, von, bis, laender):
    werte, page, pages, lastupdated = {}, 1, 1, ""
    while page <= pages:
        data = get_json(DATA_URL.format(code=api_code, von=von, bis=bis, page=page, source=source_id))
        if not isinstance(data, list) or len(data) < 2:
            msg = data[0].get("message") if isinstance(data, list) and data and isinstance(data[0], dict) else data
            raise ApiFehler(f"Datenabruf ohne Werte: {str(msg)[:200]}")
        kopf = data[0]
        pages = int(kopf.get("pages") or 1)
        lastupdated = kopf.get("lastupdated") or lastupdated
        for obs in data[1] or []:
            iso3, jahr, wert = obs.get("countryiso3code"), obs.get("date"), obs.get("value")
            if iso3 in laender and wert is not None and str(jahr).isdigit():
                werte[(iso3, int(jahr))] = float(wert)
        page += 1
        time.sleep(0.3)
    return werte, lastupdated


# ---------------------------------------------------------------- Vergleich

def einheit_aus_name(name):
    """Letzte Klammer im Namen, z. B. 'GDP per capita (current US$)' -> 'current US$'."""
    m = re.search(r"\(([^()]*)\)\s*$", name or "")
    return m.group(1).strip() if m else ""


def rel_abw(a, b):
    if a == b:
        return 0.0
    basis = max(abs(a), abs(b))
    return abs(a - b) / basis if basis else 0.0


def vergleiche(db, api):
    k = Counter()
    abw = []
    for key in db.keys() | api.keys():
        d, a = db.get(key), api.get(key)
        if d is None and a is None:
            continue
        if a is None:
            k["nur_db"] += 1
        elif d is None:
            k["nur_api"] += 1
        else:
            k["beide"] += 1
            r = rel_abw(d, a)
            if r <= TOL_GLEICH:
                k["gleich"] += 1
            else:
                k["abweichend"] += 1
                if r >= TOL_GROSS:
                    k["gross"] += 1
                abw.append((r, key[0], key[1], d, a))
    abw.sort(reverse=True)
    return k, abw[:20]


def pruefe_indikator(code, m_db, db_werte, laender, von, bis):
    api_code = code[len(PREFIX):] if code.startswith(PREFIX) else code
    meta = api_meta(api_code)
    api_vals, lastupdated = api_werte(api_code, meta["source_id"] or WDI_SOURCE_ID, von, bis, laender)
    k, top = vergleiche(db_werte, api_vals)
    db_unit = (m_db["unit"] or "").strip()
    vorschlag = meta["unit_feld"] or einheit_aus_name(meta["name"])
    jahre_db = [j for (_, j) in db_werte]
    jahre_api = [j for (_, j) in api_vals]
    return {
        "indicator_code": code,
        "db_name": m_db["name"],
        "api_name": meta["name"],
        "name_weicht_ab": meta["name"] != "" and meta["name"].strip() != m_db["name"].strip(),
        "api_source_id": meta["source_id"],
        "api_source": meta["source_name"],
        "nicht_wdi": meta["source_id"] != WDI_SOURCE_ID,
        "api_lastupdated": lastupdated,
        "db_unit": db_unit,
        "einheit_vorschlag": vorschlag,
        "einheit_fehlt": db_unit == "",
        "ohne_beschreibung": m_db["ohne_beschreibung"],
        "api_hat_sourcenote": meta["hat_sourcenote"],
        "werte_db": len(db_werte),
        "werte_api": len(api_vals),
        "beide": k["beide"],
        "gleich": k["gleich"],
        "abweichend": k["abweichend"],
        "gross_abweichend": k["gross"],
        "nur_db": k["nur_db"],
        "nur_api": k["nur_api"],
        "anteil_gleich": round(k["gleich"] / k["beide"], 4) if k["beide"] else None,
        "letztes_jahr_db": max(jahre_db) if jahre_db else None,
        "letztes_jahr_api": max(jahre_api) if jahre_api else None,
        "top_abweichungen": [
            {"iso3": i, "jahr": j, "db": d, "api": a, "rel": round(r, 4)} for r, i, j, d, a in top
        ],
    }


# ---------------------------------------------------------------- Ausgabe

def sql_literal(text):
    return "'" + text.replace("'", "''") + "'"


def schreibe_ergebnisse(out, ergebnisse, fehler, von, bis, gesamt, start):
    felder = [f for f in ergebnisse[0].keys() if f != "top_abweichungen"] if ergebnisse else []
    with open(out / "abgleich.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        w.writerows(ergebnisse)

    with open(out / "abweichungen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["indicator_code", "iso3", "jahr", "db", "api", "rel_abweichung"])
        for e in ergebnisse:
            for t in e["top_abweichungen"]:
                w.writerow([e["indicator_code"], t["iso3"], t["jahr"], t["db"], t["api"], t["rel"]])

    with open(out / "fehler.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["indicator_code", "fehler"])
        w.writerows(sorted(fehler.items()))

    # Einheiten-Vorschlag: nur leere Einheiten, nur mit Vorschlag, ohne COMMIT
    zeilen = [
        f"-- Einheiten-Vorschlag aus der Weltbank-API ({datetime.now():%Y-%m-%d %H:%M}, wb_abgleich.py)",
        "-- Quelle: API-Feld 'unit', sonst letzte Klammer im API-Namen. PRÜFEN vor COMMIT.",
        "-- Jedes UPDATE greift nur, wenn unit noch leer ist.",
        "BEGIN;", "",
    ]
    ohne, zu_lang = [], []
    for e in ergebnisse:
        if not e["einheit_fehlt"]:
            continue
        v = e["einheit_vorschlag"]
        if not v:
            ohne.append(e["indicator_code"])
            continue
        if len(v) > UNIT_MAX_LEN:
            zu_lang.append((e["indicator_code"], v))
            continue
        zeilen += [f"-- {e['indicator_code']} | API-Name: {e['api_name']}",
                   f"UPDATE indicator_metadata SET unit = {sql_literal(v)}",
                   f"WHERE indicator_code = {sql_literal(e['indicator_code'])}",
                   "  AND (unit IS NULL OR TRIM(unit) = '');", ""]
    zeilen.append("-- COMMIT;   <- erst nach Prüfung selbst ausführen")
    if ohne:
        zeilen += ["", "-- ===== OHNE VORSCHLAG (keine Klammer im Namen, API-Feld leer) ====="]
        zeilen += [f"-- {c}" for c in ohne]
    if zu_lang:
        zeilen += ["", f"-- ===== VORSCHLAG LÄNGER ALS {UNIT_MAX_LEN} ZEICHEN ====="]
        zeilen += [f"-- {c} | {v}" for c, v in zu_lang]
    (out / "einheiten_vorschlag.sql").write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    # Zusammenfassung
    s = lambda key: sum(e[key] for e in ergebnisse)
    n = lambda key: sum(1 for e in ergebnisse if e[key])
    alle_gleich = sum(1 for e in ergebnisse if e["beide"] and e["abweichend"] == 0)
    dauer = (time.time() - start) / 60
    md = [
        f"# WB-Abgleich DB ↔ Weltbank-API ({datetime.now():%d.%m.%Y %H:%M})",
        "",
        f"Zeitraum {von}–{bis} · {gesamt} WB-Indikatoren in der DB · "
        f"**{len(ergebnisse)} geprüft, {len(fehler)} mit API-Fehler** · Dauer dieses Laufs {dauer:.0f} min",
        "",
        "## Werte",
        f"- Wertpaare in beiden: {s('beide'):,}, davon gleich (≤ {TOL_GLEICH:.1%}): {s('gleich'):,}, "
        f"abweichend: {s('abweichend'):,}, davon ≥ {TOL_GROSS:.0%}: {s('gross_abweichend'):,}",
        f"- Nur in der DB: {s('nur_db'):,} · nur in der API (fehlt bei uns): {s('nur_api'):,}",
        f"- Indikatoren ganz ohne Abweichung: {alle_gleich} von {len(ergebnisse)}",
        "",
        "## Metadaten",
        f"- Name weicht ab: {n('name_weicht_ab')}",
        f"- Nicht im aktuellen WDI (andere API-Quelle): {n('nicht_wdi')}",
        f"- Einheit leer in der DB: {n('einheit_fehlt')} (Vorschläge in einheiten_vorschlag.sql)",
        f"- Ohne Beschreibung in der DB: {n('ohne_beschreibung')}",
        "",
        "## Die 15 Indikatoren mit den meisten großen Abweichungen",
        "| Code | gleich | abweichend | ≥ 5 % | nur API | letztes Jahr DB / API |",
        "|---|---|---|---|---|---|",
    ]
    for e in sorted(ergebnisse, key=lambda e: -e["gross_abweichend"])[:15]:
        md.append(f"| {e['indicator_code']} | {e['gleich']} | {e['abweichend']} | {e['gross_abweichend']} "
                  f"| {e['nur_api']} | {e['letztes_jahr_db']} / {e['letztes_jahr_api']} |")
    if fehler:
        md += ["", f"## API-Fehler ({len(fehler)}) – Neustart macht nur diese erneut", ""]
        md += [f"- {c}: {f}" for c, f in sorted(fehler.items())]
    if not ergebnisse:
        md += ["", "**Kein Indikator erfolgreich geprüft. Das ist ein Befund, kein Erfolg.**"]
    (out / "zusammenfassung.md").write_text("\n".join(md) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Ablauf

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--von", type=int, default=2015)
    ap.add_argument("--bis", type=int, default=2024)
    ap.add_argument("--limit", type=int, default=0, help="nur die ersten N Indikatoren (Testlauf)")
    ap.add_argument("--neu", action="store_true", help="Cache ignorieren und von vorn beginnen")
    args = ap.parse_args()

    out = OUTPUT_ROOT / f"{datetime.now():%Y-%m-%d}_wb_abgleich"
    out.mkdir(parents=True, exist_ok=True)
    cache_file = out / "cache.jsonl"

    erledigt = {}
    if cache_file.exists() and not args.neu:
        for line in cache_file.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if (e.get("_von"), e.get("_bis")) == (args.von, args.bis):
                erledigt[e["indicator_code"]] = e
    elif args.neu and cache_file.exists():
        cache_file.rename(out / f"cache_alt_{datetime.now():%H%M%S}.jsonl")

    print(f"Lese DB (nur lesend) … Zeitraum {args.von}–{args.bis}")
    conn = get_readonly_connection()
    try:
        meta, werte, laender = load_db(conn, args.von, args.bis)
    finally:
        conn.close()
    if not meta:
        sys.exit("FEHLER: Keine WB-Indikatoren in der DB gefunden – Abbruch (leeres Ergebnis ist ein Befund).")

    codes = sorted(meta)
    if args.limit:
        codes = codes[:args.limit]
    offen = [c for c in codes if c not in erledigt]
    print(f"{len(meta)} WB-Indikatoren, {sum(len(v) for v in werte.values()):,} DB-Werte im Zeitraum, "
          f"{len(laender)} Länder. Schon im Cache: {len(codes) - len(offen)}, offen: {len(offen)}")
    print(f"Ausgabe: {out}\n")

    fehler, start = {}, time.time()
    with open(cache_file, "a", encoding="utf-8") as cache:
        for n, code in enumerate(offen, 1):
            t0 = time.time()
            try:
                e = pruefe_indikator(code, meta[code], werte.get(code, {}), laender, args.von, args.bis)
            except ApiFehler as ex:
                fehler[code] = str(ex)
                print(f"[{n}/{len(offen)}] ✗ {code}: {ex}")
                continue
            e["_von"], e["_bis"] = args.von, args.bis
            erledigt[code] = e
            cache.write(json.dumps(e, ensure_ascii=False) + "\n")
            cache.flush()
            rest = (time.time() - start) / n * (len(offen) - n) / 60
            flag = " ⚠ große Abweichungen" if e["gross_abweichend"] else ""
            print(f"[{n}/{len(offen)}] ✓ {code}: {e['gleich']}/{e['beide']} gleich, "
                  f"{e['nur_api']} nur API ({time.time() - t0:.0f} s, noch ca. {rest:.0f} min){flag}")

    ergebnisse = [erledigt[c] for c in codes if c in erledigt]
    schreibe_ergebnisse(out, ergebnisse, fehler, args.von, args.bis, len(meta), start)
    print(f"\nFertig: {len(ergebnisse)} geprüft, {len(fehler)} API-Fehler.")
    print(f"Lesen: {out / 'zusammenfassung.md'}")
    if fehler:
        print("Es gab API-Fehler. Gleichen Befehl erneut starten: Er macht nur die fehlenden.")
        sys.exit(2)


if __name__ == "__main__":
    main()
