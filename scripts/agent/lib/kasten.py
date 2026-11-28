"""
Kasten einer Datensatz-Seite (Format vom 23.11.2026): kasten.md im Lauf-Ordner.

Eine Zeile je Feld, "Feld: Text". Pflicht: Was, Wer, Umfang, Art der Werte, Nutzung. Optional: Vorsicht.
Hier liegen Feldliste, Parser und Prüfung an einer Stelle; benutzt von
  - helpers/leitfaden_notion.py (Umwandlung nach Notion)
  - lib/checks.py (Auto-Prüfung von Leitfaden-Läufen)
"""

import re
from pathlib import Path

FELDER = ("Was", "Wer", "Umfang", "Art der Werte", "Nutzung", "Vorsicht")
PFLICHT = FELDER[:5]
ZEILE_MAX = 450          # Zeichen je Feld; der Kasten ist eine Kurzfassung

PRAEFIX = re.compile(r"`([A-Z][A-Z0-9_]*)`")
BEI_UNS = re.compile(r"Bei uns:\s*(\d+)\s+Codes?.*?([\d.]+)\s+L\u00e4nder.*?([\d.]+)\s+Werte", re.IGNORECASE)
STAND = re.compile(r"\(Stand \d{1,2}\.\d{1,2}\.\d{4}\)")


def parse(text: str) -> tuple[list[tuple[int, str, str]], list[str]]:
    """Liefert [(zeile, feld, text)] und Fehler (unbekannte Felder, leere Zeilen mit Inhalt ohne Feld)."""
    eintraege, fehler = [], []
    for nr, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        feld, sep, rest = line.partition(":")
        feld = feld.strip()
        if not sep or feld not in FELDER or not rest.strip():
            fehler.append(f"Zeile {nr}: unbekanntes oder leeres Feld {line[:50]!r} (erlaubt: {', '.join(FELDER)})")
            continue
        eintraege.append((nr, feld, rest.strip()))
    vorhanden = [f for _, f, _ in eintraege]
    for f in PFLICHT:
        if f not in vorhanden:
            fehler.append(f"Pflichtfeld fehlt: {f}")
    for f in set(vorhanden):
        if vorhanden.count(f) > 1:
            fehler.append(f"Feld doppelt: {f}")
    return eintraege, fehler


def _int(s: str) -> int:
    return int(s.replace(".", ""))


def _db_umfang(praefix: str) -> tuple[int, int, int] | None:
    from . import tools                      # erst hier: der Konverter braucht keine DB
    conn = tools.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(DISTINCT indicator_code), COUNT(DISTINCT iso_numeric), COUNT(*) "
                        "FROM indicators WHERE split_part(indicator_code, ':', 1) = %s", (praefix,))
            return cur.fetchone()
    finally:
        conn.rollback()
        conn.close()


def check(run_dir: Path, mit_db: bool = True) -> dict | None:
    """Pr\u00fcft kasten.md eines Leitfaden-Laufs. None, wenn der Lauf keinen Leitfaden hat.
    Ergebnis im Format von checks.check_sql_file (datei, anzahl, global, bloecke)."""
    if not (run_dir / "leitfaden.md").exists():
        return None
    res = {"datei": "kasten.md", "global": [], "bloecke": []}
    f = run_dir / "kasten.md"
    if not f.exists():
        res["global"].append("kasten.md fehlt (Pflicht bei Leitfaden-L\u00e4ufen)")
        res["anzahl"] = {"OK": 0, "ANSEHEN": 0, "FEHLER": 1}
        return res
    eintraege, fehler = parse(f.read_text(encoding="utf-8"))
    res["global"] += fehler
    belege_text = ""
    if (run_dir / "leitfaden_belege.md").exists():
        belege_text = (run_dir / "leitfaden_belege.md").read_text(encoding="utf-8")
    m = re.search(r"^## Kasten\s*$(.*?)(?=^## |\Z)", belege_text, re.M | re.S)
    belege_kasten = m.group(1) if m else ""
    if not m:
        res["global"].append("leitfaden_belege.md hat keinen Abschnitt \u201e## Kasten\u201c")

    for nr, feld, text in eintraege:
        notizen, status = [], "OK"

        def warn(n):
            nonlocal status
            notizen.append(n)
            status = "ANSEHEN" if status == "OK" else status

        if len(text) > ZEILE_MAX:
            warn(f"{len(text)} Zeichen, Kasten soll kurz sein (h\u00f6chstens {ZEILE_MAX})")
        if m and not re.search(rf"^\s*-?\s*\**{re.escape(feld)}\**\s*:", belege_kasten, re.M):
            warn("kein Beleg im Abschnitt \u201e## Kasten\u201c von leitfaden_belege.md")
        if feld == "Wer" and not PRAEFIX.search(text):
            warn("Pr\u00e4fix fehlt (in Backticks, z. B. `RSF`)")
        if feld == "Umfang":
            bu = BEI_UNS.search(text)
            if not bu:
                warn("\u201eBei uns: <n> Codes, <n> L\u00e4nder, \u2026, <n> Werte\u201c nicht gefunden")
            if not STAND.search(text):
                warn("Stand-Datum \u201e(Stand TT.MM.JJJJ)\u201c fehlt")
            wer = next((t for _, fl, t in eintraege if fl == "Wer"), "")
            p = PRAEFIX.search(wer)
            if bu and p and mit_db:
                try:
                    db = _db_umfang(p.group(1))
                except Exception as e:          # laut melden, nicht schlucken
                    warn(f"DB-Abgleich nicht m\u00f6glich: {e}")
                    db = None
                if db is not None:
                    soll = tuple(_int(x) for x in bu.groups())
                    if soll != tuple(db):
                        warn(f"Bei uns laut Kasten {soll[0]} Codes / {soll[1]} L\u00e4nder / {soll[2]} Werte, "
                             f"DB {db[0]} / {db[1]} / {db[2]} (Pr\u00e4fix {p.group(1)}, nur Codes mit Werten)")
        res["bloecke"].append({"status": status, "code": f"Kasten: {feld}", "zeile": nr,
                               "notizen": notizen, "set": {}})
    n_fehl = len(res["global"])
    res["anzahl"] = {"OK": sum(b["status"] == "OK" for b in res["bloecke"]),
                     "ANSEHEN": sum(b["status"] == "ANSEHEN" for b in res["bloecke"]),
                     "FEHLER": n_fehl}
    return res
