"""
ci172_entscheidung.py — CI-172 Quarantäne, Schritt 2 (nur lesend, schreibt nur CSV)
=====================================================================================
Prüft jede Kandidatenzeile aus sql/03_queries/ci172_quarantaene_liste.sql gegen die Rohdatei
und entscheidet: umhaengen (Wert gehört nachweislich einem anderen Land der Quelle),
loeschen (Einheit ohne Land oder Mischung) oder behalten. Nachgebaut wird jeweils die
Reihenfolge, in der der alte Loader mit DO NOTHING die erste Zeile gewinnen ließ.

Eingabe:  logs/migrations/ci172/kandidaten_indicators.csv, kandidaten_epr_gruppen.csv
          Rohdateien: TI CPI 2025 (reference), FIW 1973–2024 (governance), passport-index-tidy (reference),
          WHR26_Data_Figure_2.1.xlsx (culture)
Ausgabe:  logs/migrations/ci172/entscheidung_indicators.csv, entscheidung_epr_gruppen.csv
Aufruf (Shell, Repo-Wurzel, venv aktiv):  python scripts/analysis/ci172_entscheidung.py
Stand 24.11.2026: 503 Zeilen (153 umhaengen, 280 loeschen, 70 behalten), 0 unklar.
"""
import csv, json, math, collections
import pandas as pd

K = "logs/migrations/ci172/"
ind = pd.read_csv(K + "kandidaten_indicators.csv", dtype={"iso_numeric": str, "time_period": str})
grp = pd.read_csv(K + "kandidaten_epr_gruppen.csv", dtype={"iso_numeric": str})
ISO = {"NGA": "566", "NER": "562", "SRB": "688", "COD": "180", "COG": "178", "CYP": "196", "GBR": "826"}
out = []   # dicts je indicators-Zeile

def entscheide(r, aktion, ziel="", beleg=""):
    out.append(dict(id=r.id, short_code=r.short_code, iso3=r.iso3, iso_numeric=r.iso_numeric,
                    indicator_code=r.indicator_code, time_period=r.time_period, value_db=r.value,
                    aktion=aktion, ziel_iso_numeric=ziel, beleg=beleg))

def gleich(a, b, tol=1e-6):
    return a is not None and b is not None and not (isinstance(b, float) and math.isnan(b)) and abs(float(a) - float(b)) <= tol

# ---------- TI: OWID-Reihenfolge Niger vor Nigeria; Rohwerte aus der TI-Datei ----------
rows = list(csv.reader(open("data/raw/reference/ti_cpi2025_timeseries_2012_2025.csv", encoding="utf-8", errors="ignore")))
hdr = rows[3]; ti = {r[0]: r for r in rows[4:] if r and r[0] in ("Niger", "Nigeria")}
def ti_wert(land, jahr):
    treffer = [i for i, h in enumerate(hdr) if h.strip().lower() == f"cpi score {jahr}"]
    if not treffer: return None
    v = ti[land][treffer[0]].strip()
    return float(v) if v not in ("", "-") else None
for r in ind[ind.short_code == "TI"].itertuples():
    niger, nigeria = ti_wert("Niger", r.time_period), ti_wert("Nigeria", r.time_period)
    if r.iso3 == "NGA" and niger is not None:
        entscheide(r, "umhaengen" if gleich(r.value, niger) else "UNKLAR", ISO["NER"] if gleich(r.value, niger) else "",
                   f"TI-Datei Niger {r.time_period} = {niger}, Nigeria = {nigeria}")
    else:
        entscheide(r, "behalten" if gleich(r.value, nigeria) else "UNKLAR", "", f"TI-Datei Nigeria {r.time_period} = {nigeria}")

# ---------- FH: Loader-Logik nachgebaut (erste Spaltengruppe je Jahr gewinnt; Zeilen alphabetisch) ----------
fh = pd.read_excel("data/raw/governance/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx",
                   sheet_name="Country Ratings, Statuses ", header=[0, 1])
fh.columns = ["_".join([str(a).strip(), str(b).strip()]) for a, b in fh.columns]
fh = fh[fh.iloc[:, 0].notna()]; fh = fh.rename(columns={fh.columns[0]: "country_name"})
cols = fh.columns.tolist(); gruppen = []
for i in range(1, len(cols), 3):
    ys = cols[i].split("_")[-1]
    try:
        y = int(ys.split("-")[-1]) if "-" in ys else int(ys)
        if 1970 <= y <= 2030: gruppen.append((y, cols[i], cols[i + 1] if i + 1 < len(cols) else None))
    except ValueError: pass
def fh_werte(land):
    row = fh[fh.country_name.astype(str).str.strip() == land].iloc[0]; w = {}
    for y, pc, cc in gruppen:
        for code, c in (("FH:PR", pc), ("FH:CL", cc)):
            if c is None: continue
            v = row[c]
            if pd.notna(v) and str(v) not in ("-", "..", "nan") and (code, str(y)) not in w:
                try: w[(code, str(y))] = float(v)
                except ValueError: pass
    return w
FHW = {l: fh_werte(l) for l in ("Niger", "Nigeria", "Kosovo", "Serbia")}
for r in ind[ind.short_code == "FH"].itertuples():
    k = (r.indicator_code, r.time_period)
    if r.iso3 == "NGA":
        erst, zweit, ziel = "Niger", "Nigeria", ISO["NER"]
        ak_erst = "umhaengen"
    else:  # SRB
        erst, zweit, ziel = "Kosovo", "Serbia", ""
        ak_erst = "loeschen"
    if k in FHW[erst]:
        ok = gleich(r.value, FHW[erst][k])
        entscheide(r, ak_erst if ok else "UNKLAR", ziel if ok else "", f"FIW {erst} {k[1]} {k[0]} = {FHW[erst][k]}, {zweit} = {FHW[zweit].get(k)}")
    else:
        ok = gleich(r.value, FHW[zweit].get(k))
        entscheide(r, "behalten" if ok else "UNKLAR", "", f"FIW {erst} ohne Wert {k[1]}, {zweit} = {FHW[zweit].get(k)}")

# ---------- HENLEY: Kosovo vor Serbia (groupby sortiert) ----------
pp = pd.read_csv("data/raw/reference/passport-index-tidy.csv")
def klass(q):
    q = str(q).lower().strip()
    return {"visa required": "visa_required", "e-visa": "evisa", "visa on arrival": "visa_on_arrival", "-1": None}.get(q, "visa_free")
def henley(land):
    c = pp[pp.Passport == land].Requirement.map(klass).dropna().value_counts()
    return {"HENLEY:visa_required": c.get("visa_required", 0), "HENLEY:evisa": c.get("evisa", 0),
            "HENLEY:visa_on_arrival": c.get("visa_on_arrival", 0),
            "HENLEY:visa_free_total": c.get("visa_free", 0) + c.get("evisa", 0) + c.get("visa_on_arrival", 0)}
HK, HS = henley("Kosovo"), henley("Serbia")
for r in ind[ind.short_code == "HENLEY"].itertuples():
    ok = gleich(r.value, HK[r.indicator_code])
    entscheide(r, "loeschen" if ok else "UNKLAR", "", f"Passport-Index Kosovo = {HK[r.indicator_code]}, Serbia = {HS[r.indicator_code]}")

# ---------- WHR: Dateireihenfolge, je Spalte gewinnt die erste Zeile mit Wert ----------
VAR = {"Life evaluation (3-year average)": "WHR:life_evaluation", "Explained by: Log GDP per capita": "WHR:gdp_component",
       "Explained by: Social support": "WHR:social_support", "Explained by: Healthy life expectancy": "WHR:health",
       "Explained by: Freedom to make life choices": "WHR:freedom", "Explained by: Generosity": "WHR:generosity",
       "Explained by: Perceptions of corruption": "WHR:corruption"}
wx = pd.read_excel("data/raw/culture/WHR26_Data_Figure_2.1.xlsx", engine="openpyxl")
def whr_erster(namen):
    sieger = {}   # (code, jahr) -> (name, wert, anderer_wert)
    for _, row in wx.iterrows():
        n = row["Country name"]
        if n not in namen or pd.isna(row["Year"]): continue
        for col, code in VAR.items():
            v = row[col]
            if pd.isna(v): continue
            k = (code, str(int(row["Year"])))
            if k not in sieger: sieger[k] = (n, float(v))
    return sieger
def whr_wert(name, k):
    s = wx[(wx["Country name"] == name) & (wx["Year"] == int(k[1]))]
    col = [c for c, cd in VAR.items() if cd == k[0]][0]
    return None if s.empty or pd.isna(s.iloc[0][col]) else float(s.iloc[0][col])
S_COD, S_CYP = whr_erster({"Congo", "DR Congo"}), whr_erster({"Cyprus", "North Cyprus"})
for r in ind[ind.short_code == "WHR"].itertuples():
    k = (r.indicator_code, r.time_period)
    if r.iso3 == "COD":
        n, v = S_COD.get(k, (None, None)); ok = gleich(r.value, v)
        ak = ("umhaengen" if n == "Congo" else "behalten") if ok else "UNKLAR"
        entscheide(r, ak, ISO["COG"] if ak == "umhaengen" else "", f"WHR erster Treffer {n} = {v}; Congo = {whr_wert('Congo', k)}, DR Congo = {whr_wert('DR Congo', k)}")
    else:  # CYP
        n, v = S_CYP.get(k, (None, None)); ok = gleich(r.value, v)
        ak = ("loeschen" if n == "North Cyprus" else "behalten") if ok else "UNKLAR"
        entscheide(r, ak, "", f"WHR erster Treffer {n} = {v}; Cyprus = {whr_wert('Cyprus', k)}, North Cyprus = {whr_wert('North Cyprus', k)}")

# ---------- EPR-Indikatoren: Mischung, wo Niger- bzw. Kosovo-Gruppen im Jahr aktiv sind ----------
def jahre(name):
    j = set()
    for g in grp[grp.country_name == name].itertuples(): j |= set(range(int(g.year_from), int(g.year_to) + 1))
    return j
J_NIGER, J_KOSOVO = jahre("Niger"), jahre("Kosovo")
for r in ind[ind.short_code == "EPR"].itertuples():
    y = int(r.time_period)
    gemischt = (r.iso3 == "NGA" and y in J_NIGER) or (r.iso3 == "SRB" and y in J_KOSOVO)
    entscheide(r, "loeschen" if gemischt else "behalten", "",
               "Gruppen von " + ("Niger" if r.iso3 == "NGA" else "Kosovo") + (" im Jahr aktiv (Mischung)" if gemischt else " im Jahr nicht aktiv"))

# ---------- SAMAYO-Indikatoren GBR: Wert gilt für alle Teile und für GBR ----------
for r in ind[ind.short_code == "SAMAYO"].itertuples():
    entscheide(r, "behalten", "", "Wert gilt für England, Schottland, Wales, Nordirland und GBR gleich (0 bzw. 1)")

res = pd.DataFrame(out)
res.to_csv(K + "entscheidung_indicators.csv", index=False)
print(res.groupby(["short_code", "iso3", "aktion"]).size().to_string())
n_unklar = int((res.aktion == "UNKLAR").sum())
print("UNKLAR:", n_unklar)
if n_unklar:
    raise SystemExit(f"{n_unklar} Zeilen unklar – Liste nicht verwenden, erst klären.")

# ---------- EPR-Gruppen ----------
g = grp.copy()
g["aktion"] = g.country_name.map({"Niger": "umhaengen", "Kosovo": "loeschen"}).fillna("behalten")
g["ziel_iso_numeric"] = g.country_name.map({"Niger": ISO["NER"]}).fillna("")
g[["id", "country_name", "iso_numeric", "group_name", "year_from", "year_to", "is_successor", "aktion", "ziel_iso_numeric"]].to_csv(K + "entscheidung_epr_gruppen.csv", index=False)
print(g.groupby(["country_name", "aktion"]).size().to_string())
