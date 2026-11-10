"""Generates docs/SOURCES_AVAILABLE.md from the inventory output (psql) plus a fixed mapping (domain, status, loader).

Usage: python3 scripts/gen_sources_available.py scripts/agent/output/<date>_quelleninventar.txt docs/SOURCES_AVAILABLE.md
First:  psql -d country_intelligence -f sql/03_queries/2026-11-10_quelleninventar.sql > scripts/agent/output/<date>_quelleninventar.txt
New source in the DB -> add an entry to A (or R), otherwise the script stops."""
import re, sys

INV = sys.argv[1]
OUT = sys.argv[2]

txt = open(INV, encoding="utf-8").read()

def section(name):
    m = re.search(r"=== " + re.escape(name) + r".*?===\n(.*?)(?=\n=== |\Z)", txt, re.S)
    return m.group(1)

# I1: sources
src = {}
for line in section("I1").splitlines():
    p = [x.strip() for x in line.split("|")]
    if len(p) >= 9 and p[0].isdigit():
        src[p[1]] = dict(id=int(p[0]), name=p[2], codes=int(p[3]), werte=int(p[4]),
                         laender=int(p[5]), von=p[6], bis=p[7], sonder=p[8] == "t")
# I5: row counts of relational tables
rel = {}
for m in re.finditer(r"^\s*([a-z_]+\.[a-z_]+)\s*\|\s*(\d+)\s*$", section("I5"), re.M):
    rel[m.group(1)] = int(m.group(2))

DOM = [
    ("01", "Population & Demographics"), ("02", "Health & Survival"),
    ("03", "Education, Science & Innovation"), ("04", "Economy, Wealth & Labor"),
    ("05", "Infrastructure & Technology"), ("06", "Environment, Climate & Resources"),
    ("07", "Politics, Governance & Law"), ("08", "Culture, Society & Beliefs"),
    ("09", "History & Collective Memory"), ("10", "International Relations & Global Integration"),
    ("00", "Cross-cutting and base data"),
]

# code -> (main domain, also in, status, loader)
A = {
 "UNHCR": ("01", "", "⚠️ values without source_id (#1)", "demographics/load_unhcr.py"),
 "WHO": ("02", "06", "⚠️ 2 codes without data (#63), zero values in adolescent birth rate (#92)", "health/load_who.py, load_who_quickwins.py"),
 "FAO_FOOD_GRP": ("02", "", "✅", "health/load_fao_food_groups.py"),
 "FAO_FOOD": ("02", "", "✅", "health/load_fao_food.py"),
 "GHI": ("02", "", "⚠️ values without source_id, duplicate rows (#1)", "health/load_ghi.py"),
 "UNDP": ("02", "03, 04, 08", "⚠️ NaN values in MPI (#85)", "demographics/load_undp.py"),
 "NOBEL": ("03", "08", "✅", "culture/load_nobel.py"),
 "WB": ("04", "01, 02, 05, 06, 07", "⚠️ outdated vintage (#106), poverty lines mislabelled (#91)", "several (#14)"),
 "WID": ("04", "06", "⚠️ values without source_id (#1)", "economy/load_wid.py"),
 "PWT": ("04", "01", "⚠️ values without source_id (#1)", "economy/load_pwt.py"),
 "ILO": ("04", "", "⚠️ duplicate rows without source_id (#1), projections up to 2027 (#86)", "economy/load_ilostat.py"),
 "EIA": ("05", "", "✅", "environment/load_owid_energy.py"),
 "FAO_LAND": ("06", "", "✅", "environment/load_fao_landuse.py"),
 "OWID_CO2": ("06", "", "✅", "economy/load_owid_co2.py"),
 "EI": ("06", "04", "✅", "environment/load_owid_energy.py"),
 "Ember": ("06", "", "✅", "environment/load_owid_energy.py"),
 "GBIF": ("06", "", "⚠️ 2024 value is the all-time total (#90)", "environment/load_gbif*.py"),
 "OPENMETEO": ("06", "", "✅ only 48 countries", "environment/load_openmeteo.py"),
 "VDEM": ("07", "", "⚠️ open findings (#6)", "governance/load_vdem.py"),
 "POLITY5": ("07", "", "⚠️ values without source_id (#1), special codes stored as values (#89)", "governance/load_polity5.py"),
 "FH": ("07", "", "⚠️ FH:STATUS has no data (#63)", "governance/load_freedom_house.py"),
 "GITOC": ("07", "", "✅", "governance/load_fsi_gitoc_owid.py"),
 "FSI": ("07", "", "✅ 2022 only", "governance/load_fsi_gitoc_owid.py"),
 "ACLED": ("07", "", "✅ API authentication changed (#66)", "governance/load_acled.py"),
 "UNODC": ("07", "", "⚠️ partly loaded via OWID (#2), no loader in repo (#69)", "–"),
 "SIPRI": ("07", "", "⚠️ values without source_id (#1), no loader in repo (#69)", "–"),
 "UCDP": ("07", "", "✅ token required (#66)", "governance/load_ucdp*.py"),
 "TI": ("07", "", "✅", "economy/load_cpi.py"),
 "RSF": ("07", "", "⚠️ ends 2021 (#10)", "governance/load_rsf.py"),
 "WEF_GGGI": ("07", "02, 03, 04", "⚠️ static, actually a time series (#87)", "governance/load_gender_gap.py"),
 "EDELMAN": ("08", "", "✅ only 28 countries", "social/load_edelman.py"),
 "WVS": ("08", "", "✅", "demographics/load_wvs.py"),
 "PEW_REL": ("08", "", "⚠️ values without source_id (#1)", "culture/load_pew_religion.py"),
 "WHR": ("08", "", "✅", "culture/load_whr.py"),
 "HOFSTEDE": ("08", "", "❌ values assigned to wrong countries (#102)", "culture/load_hofstede.py"),
 "CAF_WGI": ("08", "", "⚠️ values without source_id (#1)", "social/load_caf_wgi.py"),
 "UNESCO_WHC": ("08", "", "✅", "culture/load_unesco_whc.py"),
 "IMDB": ("08", "", "✅", "culture/load_imdb.py"),
 "GLOTTOLOG": ("08", "", "✅ static (#87)", "culture/load_glottolog.py"),
 "UNESCO_ICH": ("08", "", "✅", "culture/load_unesco_ich.py"),
 "SAMAYO": ("08", "02, 06, 09", "✅ static (#87), unofficial source", "culture/load_samayo.py, load_national_dishes.py"),
 "OLYMPICS": ("08", "", "❌ data lost (#9)", "culture/load_olympics.py"),
 "MADDISON": ("09", "", "✅", "economy/load_maddison.py"),
 "EPR": ("09", "", "✅ some shares above 100 % (#64)", "history/load_epr.py"),
 "COW": ("09", "", "⚠️ 2 codes without data (#63)", "history/load_cow.py"),
 "UNVOTE": ("10", "", "✅", "international/load_un_voting*.py"),
 "KOF": ("10", "", "✅", "international/load_kof.py"),
 "ATOP": ("10", "", "✅ ends 2018", "international/load_atop.py"),
 "IGO": ("10", "", "✅ ends 2014", "international/load_igo.py"),
 "HENLEY": ("10", "", "✅ static (#87)", "international/load_henley.py"),
 "REST": ("00", "", "base: country master data in `countries`", "base/load_countries.py"),
 "OWID_SOCIAL": ("00", "", "⚠️ aggregator, values stored under other sources' codes (#2)", "governance/load_fsi_gitoc_owid.py"),
}

# Sources that exist only as relational tables (in sources since 2026-11-10, no codes in indicators), and extra relational tables
R = [
 # (main domain, code, name, tables, period, status, loader)
 ("04", "COMTRADE", "UN Comtrade (goods by HS4, trading partners)", ["trade.trade_products", "trade.trade_partners"], "2000–2025",
  "⚠️ incomplete, USA/FRA/IND/NOR/CHE missing (#88), table metadata not linked (#81)", "economy/load_comtrade_v2.py"),
 ("07", "UCDP", "UCDP – conflict tables", ["politics.conflicts_state", "politics.conflicts_state_actors", "politics.conflicts_nonstate", "politics.conflicts_onesided", "politics.conflict_context"], "1946–2025",
  "✅", "governance/load_ucdp*.py"),
 ("07", "MARPOR", "Manifesto Project (MARPOR)", ["politics.marpor_elections", "politics.political_parties"], "–",
  "⚠️ table metadata not linked to `sources` (#81)", "governance/load_marpor.py"),
 ("07", "CCP", "Comparative Constitutions Project v6", ["politics.constitutional_events"], "1789–today",
  "⚠️ table metadata not linked to `sources` (#81)", "history/load_ccp.py"),
 ("07", "CLINE", "Cline Center Coup d'État Project", ["politics.coups"], "1945–2026",
  "⚠️ table metadata not linked (#81); `load_coups.py` contains the DDR loader, own loader missing (#69)", "–"),
 ("08", "SAMAYO", "samayo/country-json – extra tables", ["culture.country_facts", "culture.national_dishes"], "static",
  "⚠️ no table metadata (#81)", "culture/load_samayo.py, load_national_dishes.py"),
 ("06", "GBIF", "GBIF – species occurrences", ["biodiversity.species_occurrences"], "–",
  "⚠️ experimental (#15), no table metadata (#81)", "experimental/species_gbif_wip.py"),
 ("09", "EPR", "EPR – ethnic groups", ["history.ethnic_groups"], "1946–2023",
  "⚠️ no table metadata (#81)", "history/load_epr.py"),
 ("09", "COLDAT", "COLDAT Colonial Dates (Uni Bremen)", ["international.colonial_history"], "–",
  "⚠️ no table metadata (#81)", "history/load_coldat.py"),
 ("10", "DASID", "DASID Dyadic Annual State Interactions (Pardee Center)", ["international.diplomatic_relations"], "–",
  "⚠️ no table metadata (#81)", "international/load_dasid.py"),
 ("10", "DDR", "Diplometrics Diplomatic Representation 1960–2024", ["international.diplomatic_representation"], "1960–2024",
  "⚠️ no table metadata (#81)", "international/load_ddr.py"),
]
LOST = [("06", "NDGAIN", "ND-GAIN Country Index", "❌ data lost, loader still exists (#93)", "environment/load_ndgain.py")]

rel_codes = {r[1] for r in R}
missing = set(src) - set(A) - rel_codes   # sources that exist only as relational tables are listed under R
extra = set(A) - set(src)
if missing or extra:
    sys.exit(f"Mapping incomplete: missing {missing}, extra {extra}")

def fmt_loader(s):
    if s.startswith("–") or s.startswith("mehrere"):
        return s
    return ", ".join("`" + x.strip() + "`" for x in s.split(","))

def de(n):
    return f"{n:,}"

def zeitraum(s):
    if s["codes"] == 0:
        return "–"
    if s["sonder"] and not s["von"]:
        return "static"
    return f"{s['von']}–{s['bis']}" + (" (+ static)" if s["sonder"] else "")

werte_ges = sum(s["werte"] for s in src.values())
zeilen_ges = sum(rel.values())
mit_daten = sum(1 for s in src.values() if s["werte"] > 0)
n_rel_only = len(rel_codes - set(A))

L = []
L.append("# Sources – available")
L.append("")
L.append("**As of:** 2026-11-10 · Figures from `sql/03_queries/2026-11-10_quelleninventar.sql` · Counterpart: `SOURCES_CANDIDATES.md`")
L.append("")
L.append("## Summary")
L.append("")
L.append(f"The database holds **{len(src)} sources in `sources`**, {mit_daten} of them with values "
         f"({de(werte_ges)} values in `indicators`), plus **{len(rel)} relational tables** with {de(zeilen_ges)} rows; "
         f"**{n_rel_only} sources exist only as relational tables** (no codes in `indicators`). "
         "The status column points to the Notion backlog, where the explanation lives.")
L.append("")
L.append("Status: ✅ usable · ⚠️ usable with a known issue · ❌ not usable")
L.append("")

for code, dname in DOM:
    rows = sorted([k for k, v in A.items() if v[0] == code], key=lambda k: -src[k]["werte"])
    rrows = [r for r in R if r[0] == code]
    lost = [x for x in LOST if x[0] == code]
    if not (rows or rrows or lost):
        continue
    title = dname if code == "00" else f"{code} · {dname}"
    L.append(f"## {title}")
    L.append("")
    if rows:
        L.append("| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for k in rows:
            s, a = src[k], A[k]
            L.append(f"| `{k}` | {s['name']} | {s['codes']} | {de(s['werte'])} | {s['laender']} | {zeitraum(s)} | {a[1] or '–'} | {a[2]} | {fmt_loader(a[3])} |")
        L.append("")
    if rrows:
        L.append("Relational tables:")
        L.append("")
        L.append("| Code | Source | Tables | Rows | Period | Status | Loader |")
        L.append("|---|---|---|---|---|---|---|")
        for _, k, name, tabs, zr, z, ld in rrows:
            zeilen = sum(rel[t] for t in tabs)
            L.append(f"| `{k}` | {name} | {', '.join('`'+t+'`' for t in tabs)} | {de(zeilen)} | {zr} | {z} | {fmt_loader(ld)} |")
        L.append("")
    if lost:
        L.append("Lost:")
        L.append("")
        L.append("| Code | Source | Status | Loader |")
        L.append("|---|---|---|---|")
        for _, k, name, z, ld in lost:
            L.append(f"| `{k}` | {name} | {z} | {fmt_loader(ld)} |")
        L.append("")

L.append("## Maintenance")
L.append("")
L.append("API changes affecting loaded sources, check before the next reload (#66): ACLED (new authentication), UCDP (token), WHO GHO (schema migration).")
L.append("")
L.append("## Provenance and rules")
L.append("")
L.append("- **Values** counts all rows in `indicators` whose code is assigned to this source in `indicator_metadata`, including values without a source_id (#1). **Countries** = distinct `iso_numeric`. **Period** = first and last year; \"static\" = values without a year (#87).")
L.append("- **Main domain** = the domain holding most of the source's codes; \"Also in\" lists the others. For mixed sources (`SAMAYO`, `EI`) the content decides.")
L.append("- Every source appears **exactly once** in one of the two files. When a candidate source is loaded, its row moves here.")
L.append("- Check: `python3 scripts/check_sources.py` (add `--db` to compare against the database). Regenerate: `python3 scripts/gen_sources_available.py`.")
L.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print(f"written: {OUT} | sources {len(src)} | relationale Tabellen {len(rel)} | Werte {werte_ges} | Zeilen {zeilen_ges}")
