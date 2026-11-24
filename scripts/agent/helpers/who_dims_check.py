"""CI-174: Welche WHO-Codes aus load_who.py liefern je Land und Jahr mehrere Zeilen
(Geschlecht = Dim1, Altersgruppe = Dim2, ...)?

Nur lesen: fragt die WHO-GHO-API ab, schreibt nichts in die DB.
Aufruf (Shell, im Repo):  python3 scripts/agent/helpers/who_dims_check.py [CODE ...]
Ergebnis: Tabelle am Bildschirm + logs/2026-11-24_who_dims.csv
Fehler werden laut gemeldet (Exit 1), kein Code wird still übersprungen.
"""
import ast
import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[3]
LOADERS = [REPO / "scripts/pipeline/health/load_who.py", REPO / "scripts/pipeline/health/load_who_quickwins.py"]
OUT = REPO / "logs/2026-11-24_who_dims.csv"   # bei Aufruf mit Codes: _nachlauf.csv
BASE = "https://ghoapi.azureedge.net/api"


def codes_aus_loader():
    """Liest die Listen who_indicators aus den WHO-Loadern, ohne sie auszuführen (sie verbinden sich sonst mit der DB)."""
    codes = []
    for loader in LOADERS:
        baum = ast.parse(loader.read_text(encoding="utf-8"))
        liste = None
        for knoten in baum.body:
            if isinstance(knoten, ast.Assign) and any(getattr(t, "id", "") == "who_indicators" for t in knoten.targets):
                liste = [eintrag[0][4:] for eintrag in ast.literal_eval(knoten.value)]
        if liste is None:
            raise SystemExit(f"FEHLER: who_indicators nicht in {loader} gefunden")
        codes.extend(liste)
    return codes


def alle_zeilen(code):
    zeilen, skip = [], 0
    while True:
        url = f"{BASE}/{code}?$select=SpatialDim,SpatialDimType,TimeDim,Dim1,Dim2,Dim3,NumericValue&$top=1000&$skip={skip}"
        for versuch in range(1, 4):               # bis zu 3 Versuche, dann laut scheitern
            try:
                r = requests.get(url, timeout=180)
                r.raise_for_status()              # HTTP-Fehler -> Ausnahme, nicht still abbrechen
                teil = r.json().get("value", [])
                break
            except Exception as e:
                if versuch == 3:
                    raise
                print(f"    {code} skip={skip}: Versuch {versuch} fehlgeschlagen ({type(e).__name__}), warte 10 s")
                time.sleep(10)
        zeilen.extend(teil)
        if len(teil) < 1000:
            return zeilen
        skip += 1000
        time.sleep(0.1)


def main():
    codes = codes_aus_loader()
    if len(sys.argv) > 1:                         # optional nur einzelne Codes: ... NCD_PAA NCD_BMI_PLUS1C
        unbekannt = [c for c in sys.argv[1:] if c not in codes]
        if unbekannt:
            raise SystemExit(f"FEHLER: nicht in den Loadern: {unbekannt}")
        codes = sys.argv[1:]
    print(f"{len(codes)} Codes aus {len(LOADERS)} WHO-Loadern\n")
    ergebnisse, fehler = [], []
    for code in codes:
        try:
            zeilen = [z for z in alle_zeilen(code) if z.get("SpatialDimType") == "COUNTRY"]
        except Exception as e:                    # laut melden, am Ende Exit 1
            fehler.append((code, repr(e)))
            print(f"  FEHLER {code}: {e}")
            continue
        je_land_jahr = Counter((z["SpatialDim"], z["TimeDim"]) for z in zeilen)
        dims = defaultdict(Counter)
        for z in zeilen:
            for d in ("Dim1", "Dim2", "Dim3"):
                dims[d][z.get(d)] += 1
        mehrfach = sum(1 for n in je_land_jahr.values() if n > 1)
        e = {
            "code": f"WHO:{code}",
            "zeilen_api": len(zeilen),
            "land_jahr": len(je_land_jahr),
            "land_jahr_mehrfach": mehrfach,
            "max_zeilen_je_land_jahr": max(je_land_jahr.values(), default=0),
            "dim1": " | ".join(f"{k}:{v}" for k, v in dims["Dim1"].most_common()),
            "dim2": " | ".join(f"{k}:{v}" for k, v in dims["Dim2"].most_common()),
            "dim3": " | ".join(f"{k}:{v}" for k, v in dims["Dim3"].most_common()),
        }
        ergebnisse.append(e)
        flag = "LEER" if not zeilen else ("BETROFFEN" if mehrfach else "ok")
        print(f"  {flag:9} {e['code']:42} Zeilen {e['zeilen_api']:>6}  Land-Jahr {e['land_jahr']:>5}  mehrfach {mehrfach:>5}  max {e['max_zeilen_je_land_jahr']}")
        time.sleep(0.3)

    out = OUT.with_name(OUT.stem + "_nachlauf.csv") if len(sys.argv) > 1 else OUT
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ergebnisse[0].keys()) if ergebnisse else ["code"])
        w.writeheader()
        w.writerows(ergebnisse)

    betroffen = [e for e in ergebnisse if e["land_jahr_mehrfach"]]
    print(f"\nGeprüft {len(ergebnisse)} von {len(codes)} Codes, betroffen {len(betroffen)}, Fehler {len(fehler)}")
    print(f"Datei: {out.relative_to(REPO)}")
    if fehler:
        print("\nFEHLER (nicht geprüft):")
        for c, m in fehler:
            print(f"  {c}: {m}")
        sys.exit(1)


if __name__ == "__main__":
    main()
