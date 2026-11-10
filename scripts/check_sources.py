"""
Checks docs/SOURCES_AVAILABLE.md and docs/SOURCES_CANDIDATES.md for errors.

Usage (repo folder, venv active):
    python3 scripts/check_sources.py          # check the files only
    python3 scripts/check_sources.py --db     # also compare against the database (read-only)

Exit code 0 = no errors, 1 = errors. Warnings do not change the exit code.

Checks:
  Structure  - every table row has as many columns as its header, no empty tables,
               no skipped heading levels, required sections present
  Unique     - each code appears once in the source tables of AVAILABLE,
               each source name appears once in CANDIDATES
  Separated  - no available source shows up in CANDIDATES (names and codes)
  DB (--db)  - codes in AVAILABLE = sources.short_code; codes and values per source still match;
               relational tables exist and row counts match
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_VOR = os.path.join(ROOT, "docs", "SOURCES_AVAILABLE.md")
F_POT = os.path.join(ROOT, "docs", "SOURCES_CANDIDATES.md")

# Names and codes under which available sources could show up in CANDIDATES (lower case, word match)
ALIASE = {
    "ACLED": ["acled"], "ATOP": ["atop"], "CAF_WGI": ["world giving"], "COW": ["correlates of war"],
    "EDELMAN": ["edelman trust"], "EI": ["energy institute", "statistical review of world energy"],
    "EIA": ["energy information administration"], "Ember": ["ember"], "EPR": ["ethnic power relations"],
    "FAO_FOOD": ["food balance sheets"], "FAO_FOOD_GRP": ["food groups"], "FAO_LAND": ["faostat land"], "FH": ["freedom in the world", "freedom house fiw"],
    "FSI": ["fragile states"], "GBIF": ["gbif"], "GHI": ["global hunger index"],
    "GITOC": ["gi-toc", "gitoc", "organized crime index", "global crime index"], "GLOTTOLOG": ["glottolog"],
    "HENLEY": ["henley"], "HOFSTEDE": ["hofstede"], "IGO": ["igo membership"], "ILO": ["ilostat"],
    "IMDB": ["imdb"], "KOF": ["kof"], "MADDISON": ["maddison"], "NOBEL": ["nobel"],
    "OPENMETEO": ["open-meteo"], "OWID_CO2": ["owid co2"], "PEW_REL": ["religious composition", "religious landscape"],
    "POLITY5": ["polity"], "PWT": ["penn world"], "REST": ["restcountries"], "RSF": ["press freedom index"],
    "SAMAYO": ["samayo"], "SIPRI": ["sipri"], "TI": ["cpi (transparency", "corruption perceptions"],
    "UCDP": ["ucdp"], "UNDP": ["undp hdr", "human development report"], "UNESCO_ICH": ["intangible cultural heritage", "unesco ich"],
    "UNESCO_WHC": ["world heritage list", "unesco world heritage"], "UNHCR": ["unhcr"], "UNODC": ["unodc cts"],
    "UNVOTE": ["general assembly voting", "unga voting"], "VDEM": ["v-dem v1"], "WB": ["world development indicators", "wdi"],
    "WEF_GGGI": ["global gender gap"], "WHO": ["who gho"], "WHR": ["world happiness"],
    "WID": ["wid.world", "world inequality database"], "WVS": ["world values survey"],
    "COMTRADE": ["comtrade"], "MARPOR": ["marpor", "manifesto project"], "CCP": ["comparative constitutions"],
    "CLINE": ["cline center"], "COLDAT": ["coldat"], "DASID": ["dasid"], "DDR": ["diplometrics"],
    "NDGAIN": ["nd-gain"], "OWID_SOCIAL": ["owid social"], "OLYMPICS": ["olympic games – owid"],
}

fehler, warnungen = [], []


def err(datei, zeile, text):
    fehler.append(f"ERROR   {os.path.basename(datei)}:{zeile}  {text}")


def warn(datei, zeile, text):
    warnungen.append(f"WARNING {os.path.basename(datei)}:{zeile}  {text}")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def tables(path):
    """Returns tables as a list of (start line, header, [(line, cells)], heading)."""
    lines = open(path, encoding="utf-8").read().split("\n")
    out, i, heading, in_code = [], 0, "", False
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            in_code = not in_code
        if not in_code and l.startswith("#"):
            heading = l
        if not in_code and l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|?\s*$", lines[i + 1]):
            head, rows, j = cells(l), [], i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append((j + 1, cells(lines[j])))
                j += 1
            out.append((i + 1, head, rows, heading))
            i = j
            continue
        i += 1
    return lines, out


def check_aufbau(path, pflicht):
    lines, tabs = tables(path)
    for start, head, rows, _ in tabs:
        if not rows:
            err(path, start, "table without rows")
        for z, c in rows:
            if len(c) != len(head):
                err(path, z, f"{len(c)} columns instead of {len(head)}")
    level, in_code = 1, False
    for n, l in enumerate(lines, 1):
        if l.startswith("```"):
            in_code = not in_code
        m = re.match(r"^(#+) ", l)
        if m and not in_code:
            neu = len(m.group(1))
            if neu > level + 1:
                err(path, n, f"heading jumps from level {level} to {neu}")
            level = neu
        if re.search(r"sub-categor", l, re.I):
            err(path, n, "term 'Sub-Category' (use: Dimension)")
    for p in pflicht:
        if not any(l.strip() == p for l in lines):
            err(path, 0, f"required section missing: {p}")
    return lines, tabs


def main():
    use_db = "--db" in sys.argv
    for f in (F_VOR, F_POT):
        if not os.path.exists(f):
            print(f"ERROR   file missing: {f}")
            sys.exit(1)

    pflicht = ["## Summary", "## Provenance and rules"]
    _, tv = check_aufbau(F_VOR, pflicht)
    lp, tp = check_aufbau(F_POT, pflicht)

    # AVAILABLE: codes unique per table type
    quellen, relational = {}, {}
    for start, head, rows, _ in tv:
        if not head or head[0] != "Code":
            continue
        art = "rel" if "Tables" in head else ("verloren" if len(head) == 4 else "quelle")
        for z, c in rows:
            k = c[0].strip("`")
            ziel = quellen if art != "rel" else relational
            if k in ziel:
                err(F_VOR, z, f"code {k} duplicated (also line {ziel[k]['zeile']})")
            ziel[k] = {"zeile": z, "zellen": dict(zip(head, c)), "art": art}
    if not quellen:
        err(F_VOR, 0, "no source tables found")

    # CANDIDATES: names unique, no available source
    namen = {}
    alle_vorhanden = set(quellen) | set(relational)
    for start, head, rows, _ in tp:
        for z, c in rows:
            zeile = "|".join(c)
            m = re.search(r"\*\*(.+?)\*\*", zeile)
            if not m:
                continue
            n = m.group(1).strip().lower()
            if n in namen:
                err(F_POT, z, f"source duplicated: {m.group(1)} (also line {namen[n]})")
            namen[n] = z
            for k in alle_vorhanden:
                for a in ALIASE.get(k, [k.lower()]):
                    if re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", n):
                        err(F_POT, z, f"'{m.group(1)}' is available ({k}) - belongs in SOURCES_AVAILABLE.md")
                        break
    fehlende_aliase = sorted(alle_vorhanden - set(ALIASE))
    if fehlende_aliase:
        warn(F_VOR, 0, f"codes without search terms in ALIASE, separation checked by code only: {', '.join(fehlende_aliase)}")

    if use_db:
        check_db(quellen, relational)

    for w in warnungen:
        print(w)
    for e in fehler:
        print(e)
    print(f"\nChecked: {len(quellen)} sources + {len(relational)} relational entries in AVAILABLE, "
          f"{len(namen)} sources in CANDIDATES{' + database' if use_db else ''}.")
    print(f"Result: {len(fehler)} errors, {len(warnungen)} warnings.")
    sys.exit(1 if fehler else 0)


def zahl(s):
    s = s.replace(",", "").replace(".", "").strip()
    return int(s) if s.isdigit() else None


def check_db(quellen, relational):
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    user = os.getenv("DB_AGENT_USER") or os.getenv("DB_USER")
    pw = os.getenv("DB_AGENT_PASSWORD") if os.getenv("DB_AGENT_USER") else os.getenv("DB_PASSWORD")
    conn = psycopg2.connect(host=os.getenv("DB_HOST"), dbname=os.getenv("DB_NAME"), user=user,
                            password=pw, port=os.getenv("DB_PORT"))
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute("""
        WITH v AS (SELECT indicator_code, count(*) n FROM indicators GROUP BY 1)
        SELECT s.short_code, count(m.indicator_code), coalesce(sum(v.n), 0)
        FROM sources s LEFT JOIN indicator_metadata m ON m.source_id = s.id
        LEFT JOIN v USING (indicator_code) GROUP BY s.short_code""")
    db = {k: (c, w) for k, c, w in cur.fetchall()}
    datei = {k for k, v in quellen.items() if v["art"] == "quelle"}
    for k in sorted(set(db) - datei - set(relational)):
        err(F_VOR, 0, f"source {k} is in sources but missing from the file")
    for k in sorted(datei - set(db)):
        err(F_VOR, quellen[k]["zeile"], f"source {k} is in the file but not in sources")
    for k in sorted(datei & set(db)):
        z = quellen[k]["zellen"]
        c, w = db[k]
        if zahl(z.get("Codes", "")) != c or zahl(z.get("Values", "")) != w:
            warn(F_VOR, quellen[k]["zeile"], f"{k}: file {z.get('Codes')} codes / {z.get('Values')} values, DB {c} / {w} - regenerate the file")
    for k, v in relational.items():
        tabs = re.findall(r"`([a-z_]+\.[a-z_]+)`", v["zellen"].get("Tables", ""))
        summe = 0
        for t in tabs:
            s, r = t.split(".")
            cur.execute("SELECT to_regclass(%s)", (t,))
            if cur.fetchone()[0] is None:
                err(F_VOR, v["zeile"], f"table {t} does not exist")
                continue
            cur.execute(f'SELECT count(*) FROM "{s}"."{r}"')
            summe += cur.fetchone()[0]
        if zahl(v["zellen"].get("Rows", "")) != summe:
            warn(F_VOR, v["zeile"], f"{k}: file {v['zellen'].get('Rows')} rows, DB {summe}")
    cur.execute("""SELECT schemaname || '.' || relname FROM pg_stat_user_tables WHERE schemaname <> 'public'""")
    in_datei = {t for v in relational.values() for t in re.findall(r"`([a-z_]+\.[a-z_]+)`", v["zellen"].get("Tables", ""))}
    for (t,) in cur.fetchall():
        if t not in in_datei:
            err(F_VOR, 0, f"relational table {t} missing from the file")
    conn.close()


if __name__ == "__main__":
    main()
