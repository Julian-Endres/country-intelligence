"""
fuzzy_laender_audit.py — CI-172: Welche Ländernamen landen per pycountry.search_fuzzy wo?
=======================================================================================
Nur lesend. Schreibt nichts in die DB.

Für jeden der 12 Loader mit `search_fuzzy` werden alle Ländernamen aus der Rohquelle
durch genau die Kette des Loaders geschickt (Override → exakter Name → Fuzzy [0]).
Bei den sechs Loadern mit main()-Schutz wird die Funktion des Loaders selbst benutzt,
bei den sechs Skript-Loadern ist die Kette nachgebaut (Override-Listen per ast aus der
Datei gelesen, damit sie nicht abweichen können).

Ausgabe (Ordner `Claude outputs/fuzzy_audit/`):
  audit_namen.csv   eine Zeile je Loader × Rohname: Weg, Kandidaten, Ergebnis, Flags
  audit_bericht.md  nur die Verdachtsfälle + Liste der verworfenen Namen

Flags je Fuzzy-Treffer:
  MEHRDEUTIG   search_fuzzy liefert mehr als ein Land, der Loader nimmt [0]
  NAME_WEICHT  der Rohname ist weder name, common_name noch official_name des Treffers
  KOLLISION    ein anderer Rohname desselben Loaders landet auf demselben Land
               (Signatur des stillen Überschreibens bei ON CONFLICT DO NOTHING)

Aufruf (Shell, Projektordner, venv aktiv):
  python scripts/analysis/fuzzy_laender_audit.py              # countries aus der DB (.env)
  python scripts/analysis/fuzzy_laender_audit.py --countries-csv pfad.csv   # ohne DB
"""

import argparse
import ast
import csv
import glob
import importlib.util
import io
import json
import os
import sys
import zipfile
from collections import defaultdict

import pandas as pd
import pycountry
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Claude outputs", "fuzzy_audit")
PIPE = os.path.join(ROOT, "scripts", "pipeline")

# ─── Fuzzy-Aufzeichnung ──────────────────────────────────────────────────────
_orig_fuzzy = pycountry.countries.search_fuzzy
CURRENT = {"loader": None}
FUZZY_LOG = defaultdict(dict)   # loader -> {name: [alpha3,...] | "LookupError"}


def _recording_fuzzy(query):
    try:
        res = _orig_fuzzy(query)
        FUZZY_LOG[CURRENT["loader"]][query] = [c.alpha_3 for c in res]
        return res
    except LookupError:
        FUZZY_LOG[CURRENT["loader"]][query] = "LookupError"
        raise


pycountry.countries.search_fuzzy = _recording_fuzzy


# ─── Hilfen ──────────────────────────────────────────────────────────────────
def find_raw(basename):
    hits = glob.glob(os.path.join(ROOT, "data", "raw", "**", basename), recursive=True)
    if not hits:
        raise FileNotFoundError(f"Rohdatei nicht gefunden: {basename}")
    return hits[0]


def literal_from_file(path, varname):
    """Liest ein Dict-Literal (Override-Liste) aus dem Loader, ohne ihn auszuführen."""
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == varname for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{varname} nicht in {path}")


def import_loader(relpath):
    path = os.path.join(PIPE, relpath)
    spec = importlib.util.spec_from_file_location("ldr_" + os.path.basename(relpath)[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_countries(args):
    if args.countries_csv:
        df = pd.read_csv(args.countries_csv, dtype=str)
    else:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
        conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
                                user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
                                port=os.getenv("DB_PORT"))
        df = pd.read_sql("SELECT iso_numeric, iso_code_3, name FROM countries", conn)
        conn.close()
    iso3_map = {r.iso_code_3: r.iso_numeric for r in df.itertuples() if r.iso_code_3}
    name_map = {str(r.name).lower(): r.iso_numeric for r in df.itertuples()}
    num_to_iso3 = {v: k for k, v in iso3_map.items()}
    return iso3_map, name_map, num_to_iso3


# ─── Je Loader: Rohnamen (mit Zeilenzahl) und Auflösung ──────────────────────
# Rückgabe je Loader: dict name -> (anzahl_zeilen, iso_numeric | None, weg)

def run_module_loader(relpath, names_with_counts, resolve_call, overrides_attr, name_map):
    mod = import_loader(relpath)
    overrides = {k.lower(): v for k, v in getattr(mod, overrides_attr).items()}
    out = {}
    for name, n in names_with_counts.items():
        clean = str(name).strip().lower()
        if clean in overrides:
            weg = "override"
        elif clean in name_map and overrides_attr != "MARPOR_COUNTRY_MAP":
            weg = "exakt"
        else:
            weg = "fuzzy"
        out[name] = (n, resolve_call(mod, name), weg)
    return out


def names_caf(maps):
    mod = import_loader("social/load_caf_wgi.py")
    rows = mod.load_from_zip(find_raw("archive_CAF World Giving Index.zip"))
    rows += mod.load_from_csv(find_raw("world_giving_2023_complete.csv"), 2023)
    rows += mod.load_from_csv(find_raw("world_giving_2024_complete.csv"), 2024)
    cnt = defaultdict(int)
    for country, _y, _c, v in rows:
        if v is not None:
            cnt[country] += 1
    iso3, names = maps
    return run_module_loader("social/load_caf_wgi.py", cnt,
                             lambda m, n: m.resolve_country(n, iso3, names),
                             "CAF_NAME_OVERRIDES", names)


def names_edelman(maps):
    mod = import_loader("social/load_edelman.py")
    cnt = defaultdict(int)
    files = glob.glob(os.path.join(ROOT, "data", "raw", "**", "Edelman", "*.csv"), recursive=True)
    if not files:
        raise FileNotFoundError("Edelman-CSV nicht gefunden")
    for f in files:
        for country, seg, _i, _y, _v in mod.parse_file(f):
            if seg:
                cnt[country] += 1
    iso3, names = maps
    return run_module_loader("social/load_edelman.py", cnt,
                             lambda m, n: m.resolve(n, iso3, names), "OVERRIDES", names)


def _ddr_counts():
    with zipfile.ZipFile(find_raw("dataverse_files_Diplometric.zip")) as z:
        xl = [n for n in z.namelist() if n.endswith(".xlsx") and "Diplomatic-Representation" in n][0]
        with z.open(xl) as f:
            df = pd.read_excel(io.BytesIO(f.read()), usecols=["SendingCountry", "Destination"])
    cnt = defaultdict(int)
    for col in ("SendingCountry", "Destination"):
        for k, v in df[col].value_counts(dropna=True).items():
            cnt[k] += int(v)
    return cnt


def names_ddr(maps, relpath):
    iso3, names = maps
    return run_module_loader(relpath, _ddr_counts(),
                             lambda m, n: m.resolve(n, iso3, names), "OVERRIDES", names)


def names_coldat(maps):
    df = pd.read_csv(find_raw("COLDAT_dyads.csv"))
    df = df[df["col"] == 1]
    cnt = df["country"].astype(str).value_counts().to_dict()
    iso3, names = maps
    return run_module_loader("history/load_coldat.py", cnt,
                             lambda m, n: m.resolve(n, iso3, names), "OVERRIDES", names)


def names_marpor(maps):
    cnt = defaultdict(int)
    for fn in ("parties_MPDataset_MPDS2025a.csv", "MPDataset_MPDS2025a.csv"):
        df = pd.read_csv(find_raw(fn), low_memory=False)
        for k, v in df["countryname"].astype(str).value_counts().items():
            cnt[k] += int(v)
    iso3, names = maps
    return run_module_loader("governance/load_marpor.py", cnt,
                             lambda m, n: m.resolve_country(n, iso3), "MARPOR_COUNTRY_MAP", names)


# Skript-Loader: Kette nachgebaut, Override-Listen aus der Datei
def chain_manual_then_fuzzy(name, manual, iso3):
    """load_cpi / load_freedom_house: manual_mapping (exakte Schreibung) → Fuzzy [0]."""
    if name in manual:
        return iso3.get(manual[name]), "override"
    try:
        return iso3.get(pycountry.countries.search_fuzzy(name)[0].alpha_3), "fuzzy"
    except LookupError:
        return None, "fuzzy"


def chain_name_then_fuzzy(name, names, iso3):
    """load_henley / load_national_dishes / load_samayo: Name (lower) → Fuzzy [0]."""
    key = name.lower().strip()
    if names.get(key):
        return names[key], "exakt"
    try:
        r = pycountry.countries.search_fuzzy(name)
        return (iso3.get(r[0].alpha_3) if r else None), "fuzzy"
    except LookupError:
        return None, "fuzzy"


def names_freedom_house(maps):
    iso3, names = maps
    manual = literal_from_file(os.path.join(PIPE, "governance/load_freedom_house.py"), "manual_mapping")
    df = pd.read_excel(find_raw("Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx"),
                       sheet_name="Country Ratings, Statuses ", header=[0, 1])
    col = df.iloc[:, 0].dropna().astype(str).str.strip()
    col = col[col != "nan"]
    out = {}
    for name, n in col.value_counts().items():
        iso, weg = chain_manual_then_fuzzy(name, manual, iso3)
        out[name] = (int(n) * (len(df.columns) - 1), iso, weg)   # Zeilen × Spalten (grob)
    return out


def names_cpi(maps):
    iso3, names = maps
    manual = literal_from_file(os.path.join(PIPE, "economy/load_cpi.py"), "manual_mapping")
    from owid.catalog import search, fetch      # wie im Loader; braucht Netz
    df = fetch(search("corruption").to_frame().iloc[0]["url"]).reset_index()
    df = df[df["cpi_score"].notna()]
    out = {}
    for name, n in df["entities"].astype(str).value_counts().items():
        iso, weg = chain_manual_then_fuzzy(name, manual, iso3)
        out[name] = (int(n), iso, weg)
    return out


def names_henley(maps):
    iso3, names = maps
    df = pd.read_csv(find_raw("passport-index-tidy.csv"))
    out = {}
    for name, n in df["Passport"].value_counts().items():
        iso, weg = chain_name_then_fuzzy(name, names, iso3)
        out[name] = (int(n), iso, weg)
    return out


def _samayo_json(fn):
    r = requests.get("https://raw.githubusercontent.com/samayo/country-json/master/src/" + fn, timeout=30)
    r.raise_for_status()
    return json.loads(r.text)


def names_dishes(maps):
    iso3, names = maps
    out = {}
    for e in _samayo_json("country-by-national-dish.json"):
        c = e.get("country", "")
        if c:
            iso, weg = chain_name_then_fuzzy(c, names, iso3)
            out[c] = (1, iso, weg)
    return out


def names_samayo(maps):
    iso3, names = maps
    files = literal_from_file(os.path.join(PIPE, "culture/load_samayo.py"), "FILES")
    cnt = defaultdict(int)
    for fn in files.values():
        for e in _samayo_json(fn):
            if e.get("country"):
                cnt[e["country"]] += 1
    out = {}
    for c, n in cnt.items():
        iso, weg = chain_name_then_fuzzy(c, names, iso3)
        out[c] = (n, iso, weg)
    return out


def names_epr(maps):
    iso3, names = maps
    gw_manual = literal_from_file(os.path.join(PIPE, "history/load_epr.py"), "GW_MANUAL")
    r = requests.get("https://icr.ethz.ch/data/epr/core/EPR-2023.csv", timeout=60)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    cnt = defaultdict(int)
    gw_of = {}
    for row in rows:
        cnt[row["statename"]] += 1
        gw_of[row["statename"]] = row["gwid"]
    out = {}
    for name, n in cnt.items():
        gw = gw_of[name]
        if gw in gw_manual:
            a3, weg = gw_manual[gw], "override"
        else:
            try:
                a3, weg = pycountry.countries.search_fuzzy(name)[0].alpha_3, "fuzzy"
            except LookupError:
                a3, weg = None, "fuzzy"
        out[name] = (n, iso3.get(a3) if a3 else None, weg)
    return out


LOADERS = [
    ("economy/load_cpi.py", names_cpi),
    ("social/load_caf_wgi.py", names_caf),
    ("social/load_edelman.py", names_edelman),
    ("history/load_coups.py", lambda m: names_ddr(m, "history/load_coups.py")),
    ("history/load_epr.py", names_epr),
    ("history/load_coldat.py", names_coldat),
    ("governance/load_marpor.py", names_marpor),
    ("governance/load_freedom_house.py", names_freedom_house),
    ("international/load_ddr.py", lambda m: names_ddr(m, "international/load_ddr.py")),
    ("international/load_henley.py", names_henley),
    ("culture/load_national_dishes.py", names_dishes),
    ("culture/load_samayo.py", names_samayo),
]


# ─── Bewertung ───────────────────────────────────────────────────────────────
def pyc_names(alpha3):
    c = pycountry.countries.get(alpha_3=alpha3)
    if not c:
        return set()
    return {getattr(c, a).lower() for a in ("name", "common_name", "official_name") if hasattr(c, a)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries-csv")
    ap.add_argument("--nur", help="nur diese Loader (Teilstring, kommagetrennt)")
    args = ap.parse_args()

    iso3_map, name_map, num_to_iso3 = load_countries(args)
    os.makedirs(OUT, exist_ok=True)
    records, fehler = [], []

    for relpath, fn in LOADERS:
        if args.nur and not any(s in relpath for s in args.nur.split(",")):
            continue
        CURRENT["loader"] = relpath
        try:
            res = fn((iso3_map, name_map))
        except Exception as e:                      # laut melden, nicht schlucken
            fehler.append((relpath, f"{type(e).__name__}: {e}"))
            print(f"FEHLER {relpath}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        by_iso = defaultdict(list)
        for name, (n, iso, weg) in res.items():
            by_iso[iso].append(name)
        for name, (n, iso, weg) in sorted(res.items(), key=lambda x: str(x[0])):
            kand = FUZZY_LOG[relpath].get(str(name).strip()) or FUZZY_LOG[relpath].get(name)
            flags = []
            if weg == "fuzzy" and isinstance(kand, list):
                if len(kand) > 1:
                    flags.append("MEHRDEUTIG")
                if str(name).strip().lower() not in pyc_names(kand[0]):
                    flags.append("NAME_WEICHT")
                if iso and len(by_iso[iso]) > 1:
                    flags.append("KOLLISION")
            records.append({
                "loader": relpath, "rohname": name, "zeilen": n, "weg": weg,
                "kandidaten": "|".join(kand) if isinstance(kand, list) else (kand or ""),
                "ergebnis_iso3": num_to_iso3.get(iso, "") if iso else "",
                "ergebnis_iso_numeric": iso or "",
                "andere_namen_gleiches_land": "|".join(sorted(str(x) for x in by_iso[iso] if x != name)) if iso else "",
                "flags": " ".join(flags),
            })

    pd.DataFrame(records).to_csv(os.path.join(OUT, "audit_namen.csv"), index=False)

    df = pd.DataFrame(records)
    with open(os.path.join(OUT, "audit_bericht.md"), "w", encoding="utf-8") as f:
        f.write("# CI-172 Fuzzy-Audit\n\n")
        f.write("| Loader | Namen | davon Fuzzy | Verdacht | verworfen |\n|---|---|---|---|---|\n")
        for relpath, _ in LOADERS:
            d = df[df.loader == relpath] if len(df) else df
            if not len(d):
                continue
            f.write(f"| {relpath} | {len(d)} | {(d.weg == 'fuzzy').sum()} | "
                    f"{(d['flags'] != '').sum()} | {(d.ergebnis_iso3 == '').sum()} |\n")
        if fehler:
            f.write("\n## Nicht geprüft (Fehler)\n\n")
            for r, e in fehler:
                f.write(f"- `{r}`: {e}\n")
        f.write("\n## Verdachtsfälle (Fuzzy mit Flag)\n\n")
        f.write("| Loader | Rohname | Zeilen | Kandidaten | → | gleiches Land auch | Flags |\n|---|---|---|---|---|---|---|\n")
        for r in df[df['flags'] != ""].itertuples() if len(df) else []:
            f.write(f"| {r.loader.split('/')[-1]} | {r.rohname} | {r.zeilen} | {r.kandidaten} | "
                    f"{r.ergebnis_iso3} | {r.andere_namen_gleiches_land} | {r.flags} |\n")
        f.write("\n## Verworfen (kein Land gefunden)\n\n")
        for r in df[df.ergebnis_iso3 == ""].itertuples() if len(df) else []:
            f.write(f"- {r.loader.split('/')[-1]}: {r.rohname} ({r.zeilen} Zeilen, Weg {r.weg}, Kandidaten {r.kandidaten or '–'})\n")

    print(f"{len(records)} Namen geprüft, {sum(1 for r in records if r['flags'])} Verdachtsfälle, "
          f"{len(fehler)} Loader mit Fehler. Bericht: {OUT}/audit_bericht.md")
    if fehler:
        sys.exit(1)


if __name__ == "__main__":
    main()
