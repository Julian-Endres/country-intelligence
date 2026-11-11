"""
Mehrere Sekretär-Pakete nacheinander, zum Laufenlassen nebenbei.

Wählt Indikatoren einer Quelle, die noch nicht freigegeben sind (metadata_reviewed_at leer) und in
keinem offenen Lauf stecken, teilt sie in Pakete mit fester Code-Liste und startet je Paket einen
Sekretär-Lauf mit Auto-Prüfung. Die Datenbank ändert sich dabei nicht: Prüfen und Übertragen
machst du danach wie immer je Lauf mit review.py und apply.py (status.py zeigt die offenen Läufe).

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/batch.py WB --paket 40 --anzahl 3
  python3 scripts/agent/batch.py WB --domain "Health & Survival" --paket 40 --anzahl 2
  python3 scripts/agent/batch.py WB --vorschau          # nur anzeigen, was dran wäre

Mac wach halten, während es läuft:
  caffeinate -i python3 scripts/agent/batch.py WB --paket 40 --anzahl 3

Stoppt nach dem ersten Lauf, der nicht sauber endet (Budget, Turns, Fehler, Nutzungslimit).
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime

from lib import decisions, runs, tools
import secretary

OPEN = {"neu", "geprüft", "freigegeben"}
# Bewusst ausgenommen (Entscheidung offen, siehe Backlog)
SKIP = {"WB:SI.POV.DDAY"}

HINTS = {
    "WB": "Definitionen zuerst in der lokalen Datei wb_wdi_all_indicator_defs.json suchen (search_text nach "
          "dem Code, dann read_text); nur wenn ein Code dort fehlt, einzeln über "
          "https://api.worldbank.org/v2/indicator/<CODE>?format=json mit download_file holen.",
}


WB_ALL_DEFS = "wb_wdi_all_indicator_defs.json"


def prepare_wb_defs(codes: list[str], thema: str) -> tuple[str | None, list[str]]:
    """Zieht die Definitionen der Paket-Codes aus der großen WDI-Datei in eine kleine Textdatei
    (ohne KI). Spart dem Agenten das Durchblättern von 1,5 MB JSON. Gibt (Dateiname, fehlende Codes)."""
    src = tools.REF_DIR / WB_ALL_DEFS
    if not src.exists():
        return None, codes
    data = json.loads(src.read_text(encoding="utf-8"))
    entries = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
    by_id = {e.get("id"): e for e in entries if isinstance(e, dict)}
    clean = lambda v: " ".join(str(v or "").split())          # Zeilenumbrüche raus, damit Zitate passen
    lines, missing = [f"Auszug aus {WB_ALL_DEFS} (Weltbank-API, alle WDI-Indikatoren) für {thema}", ""], []
    for code in codes:
        e = by_id.get(code.split(":", 1)[1])
        if not e:
            missing.append(code)
            continue
        src_name = e.get("source", {}).get("value", "") if isinstance(e.get("source"), dict) else ""
        topics = ", ".join(t.get("value", "") for t in e.get("topics") or [] if isinstance(t, dict))
        lines += [f"=== {code} ===", f"name: {clean(e.get('name'))}", f"unit: {clean(e.get('unit'))}",
                  f"source: {clean(src_name)}", f"topics: {clean(topics)}",
                  f"sourceNote: {clean(e.get('sourceNote'))}",
                  f"sourceOrganization: {clean(e.get('sourceOrganization'))}", ""]
    name = f"wb_defs_{thema}.txt"
    (tools.REF_DIR / name).write_text("\n".join(lines), encoding="utf-8")
    return name, missing


def codes_in_open_runs() -> set[str]:
    taken = set()
    if not runs.OUTPUT_ROOT.exists():
        return taken
    for d in runs.OUTPUT_ROOT.iterdir():
        st = runs.read_status(d) if d.is_dir() else None
        if not st or st.get("status") not in OPEN:
            continue
        for sql in d.glob("*.sql"):
            taken |= {p["code"] for p in decisions.parse_proposals(sql) if p["code"]}
    return taken


def candidates(source: str, domain: str | None) -> list[tuple[str, str]]:
    sql = ("SELECT indicator_code, COALESCE(domain, '') FROM indicator_metadata "
           "WHERE indicator_code LIKE %s AND metadata_reviewed_at IS NULL")
    params = [f"{source}:%"]
    if domain:
        sql += " AND domain = %s"
        params.append(domain)
    sql += " ORDER BY domain NULLS LAST, indicator_code"
    conn = tools.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.rollback()
        conn.close()


def task_for(source: str, codes: list[str], nr: int, defs_file: str | None = None,
             missing: list[str] | None = None) -> str:
    if defs_file:
        hint = (f"Die Definitionen dieses Pakets stehen gesammelt in {defs_file} (Referenzordner, ein Block pro "
                f"Code). Lies diese Datei mit read_text vollständig und belege mit ihr (Datei und Zeile). "
                f"Die große Datei {WB_ALL_DEFS} nicht durchsuchen.")
        if missing:
            hint += (f" Nicht darin enthalten sind: {', '.join(missing)}; dafür einzeln "
                     f"https://api.worldbank.org/v2/indicator/<CODE>?format=json mit download_file holen.")
    else:
        hint = HINTS.get(source, "")
    return (f"{source} Metadaten v3, Paket {nr}: Beschreibe genau diese {len(codes)} Indikatoren "
            f"(keine anderen): {', '.join(codes)}. {hint} "
            "Schreibe metadata.sql (alle 14 Felder, self_check vor dem Abschluss) und befunde.md mit "
            "Länder-Stichprobe für 2 der Indikatoren. Kein Leitfaden.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mehrere Sekretär-Pakete nacheinander")
    ap.add_argument("quelle", help="Präfix der Indikator-Codes, z. B. WB")
    ap.add_argument("--domain", help="nur diese Domain")
    ap.add_argument("--paket", type=int, default=40, help="Indikatoren pro Lauf (Standard 40)")
    ap.add_argument("--anzahl", type=int, default=1, help="Wie viele Pakete nacheinander (Standard 1)")
    ap.add_argument("--budget", type=float, default=4.0, help="Höchstbudget je Lauf in USD")
    ap.add_argument("--max-turns", type=int, default=150)
    ap.add_argument("--vorschau", action="store_true", help="nur anzeigen, nichts starten")
    ap.add_argument("--model", default=None, help="optional, z. B. sonnet (sonst Standard der CLI)")
    a = ap.parse_args()

    src = a.quelle.upper()
    taken = codes_in_open_runs()
    rows = [(c, d) for c, d in candidates(src, a.domain) if c not in taken and c not in SKIP]
    packets = [rows[i:i + a.paket] for i in range(0, len(rows), a.paket)][:a.anzahl]

    print(f"{src}: {len(rows)} Indikatoren offen (ohne {len(taken)} in offenen Läufen, ohne {sorted(SKIP)})")
    for i, p in enumerate(packets, 1):
        doms = sorted({d or '(ohne)' for _, d in p})
        print(f"  Paket {i}: {len(p)} Indikatoren, {p[0][0]} … {p[-1][0]}  [{', '.join(doms)}]")
    if a.vorschau or not packets:
        return

    start = datetime.now()
    done = []
    for i, p in enumerate(packets, 1):
        codes = [c for c, _ in p]
        thema = f"{src.lower()}_batch_{start:%H%M}_{i}"
        print(f"\n{'#' * 60}\nPaket {i}/{len(packets)} startet ({len(codes)} Indikatoren)\n{'#' * 60}")
        defs_file, missing = prepare_wb_defs(codes, thema) if src == "WB" else (None, [])
        if defs_file and len(missing) > len(codes) / 2:
            print(f"Achtung: {len(missing)} von {len(codes)} Codes nicht in {WB_ALL_DEFS} gefunden, "
                  "Vorbereitung wird nicht genutzt (bisheriger Weg).")
            defs_file, missing = None, []
        if defs_file:
            print(f"Definitionen vorbereitet: {defs_file} ({len(codes) - len(missing)} von {len(codes)})")
        res = asyncio.run(secretary.main(task_for(src, codes, i, defs_file, missing), thema, a.budget,
                                         a.max_turns, a.model))
        done.append(res)
        if res.get("subtype") != "success":
            print(f"\nPaket {i} endete mit „{res.get('subtype')}“. Ich höre hier auf, damit nichts doppelt läuft.")
            break

    print(f"\n{'=' * 60}\nFertig nach {(datetime.now() - start).seconds // 60} min.")
    for r in done:
        p = r.get("pruefung") or [{}]
        c = p[0] if p else {}
        cost = f"{r['kosten']:.2f} USD" if r.get("kosten") is not None else "?"
        print(f"  {r['run_dir'].name}: {r.get('subtype')}, {cost}, "
              f"✅ {c.get('OK', 0)}  ⚠️  {c.get('ANSEHEN', 0)}  ❌ {c.get('FEHLER', 0)}")
    print("Weiter mit:  python3 scripts/agent/status.py   (dann review.py und apply.py je Lauf)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main()
