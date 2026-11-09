"""
Auto-Prüfung eines Lauf-Ordners (ohne KI).

Prüft jede Vorschlags-SQL-Datei (*.sql) im Lauf-Ordner:
  1. Struktur   nur UPDATE indicator_metadata, mit Schutzbedingung, Code im Kommentar = Code im WHERE
  2. Beleg      steht das Zitat wirklich an der genannten Stelle im Referenztext?
  3. Datenbank  gibt es den Code, ist die Beschreibung noch leer, passen die Längen in die Spalten?
  4. Werte      passt die vorgeschlagene Einheit zu den echten min/max-Werten?

Ergebnis pro Vorschlag: OK / ANSEHEN / FEHLER, geschrieben nach pruefung.md und pruefung.json.
"""

import bisect
import json
import re
from datetime import datetime
from pathlib import Path

from . import runs, sqlfile, tools

OK, WARN, FAIL = "OK", "ANSEHEN", "FEHLER"
ICON = {OK: "✅", WARN: "⚠️", FAIL: "❌"}
RANK = {OK: 0, WARN: 1, FAIL: 2}

CODE_LINE = re.compile(r"^([A-Za-z0-9_]+:\S+)\s*$")
BELEG_LINE = re.compile(
    r"^Beleg:\s*(?P<file>[^,]+?),\s*S\.\s*(?P<page>\d+),\s*Zeile\s*(?P<lines>[\d\s/,\-–]+?):\s*"
    r"[\"“„](?P<quote>.+)[\"”“]\s*$")
SICHER_LINE = re.compile(r"^Sicherheit:\s*(HOCH|MITTEL|UNSICHER)\b(.*)$", re.IGNORECASE)
QUELLE_LINE = re.compile(r"^Quelle:\s*(https?://\S+)")
GUARD = "(descriptionisnullortrim(description)='')"


def _norm(s: str) -> str:
    """Nur Buchstaben und Ziffern, klein. Macht den Vergleich robust gegen Satzzeichen und Umbrüche."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


class RefText:
    """Referenztext mit schneller Suche nach normalisierten Zitat-Fragmenten."""

    def __init__(self, path: Path):
        self.lines = path.read_text(encoding="utf-8").splitlines()
        self.norm = [_norm(l) for l in self.lines]
        self.offsets, pos = [], 0
        for n in self.norm:
            self.offsets.append(pos)
            pos += len(n)
        self.full = "".join(self.norm)

    def window(self, lo: int, hi: int) -> str:
        lo, hi = max(1, lo), min(len(self.lines), hi)
        return "".join(self.norm[lo - 1:hi])

    def find_line(self, frag: str) -> int | None:
        idx = self.full.find(frag)
        if idx == -1:
            return None
        return bisect.bisect_right(self.offsets, idx)  # 1-basierte Zeilennummer


def _merge(a: str, b: str) -> str:
    return a if RANK[a] >= RANK[b] else b


def check_beleg(comments: list[str], ref_cache: dict) -> tuple[str, list[str], dict]:
    beleg = next((m for c in comments if (m := BELEG_LINE.match(c))), None)
    if not beleg:
        quelle = next((m for c in comments if (m := QUELLE_LINE.match(c))), None)
        if quelle:
            return OK, [f"API-Quelle {quelle.group(1)} (kein Textbeleg nötig)"], {"quelle": quelle.group(1)}
        return FAIL, ["Kein Beleg-Kommentar gefunden"], {}
    fname = Path(beleg.group("file").strip()).name
    nums = [int(x) for x in re.findall(r"\d+", beleg.group("lines"))]
    quote = beleg.group("quote")
    info = {"datei": fname, "seite": int(beleg.group("page")), "zeilen": nums, "zitat": quote}
    ref_path = tools.REF_DIR / fname
    if not ref_path.exists():
        return FAIL, [f"Referenzdatei {fname} nicht gefunden"], info
    ref = ref_cache.setdefault(fname, RefText(ref_path))
    frags = [_norm(f) for f in re.split(r"\.\.\.|…", quote)]
    frags = [f for f in frags if len(f) >= 8]
    if not frags:
        return WARN, ["Zitat zu kurz für eine automatische Prüfung"], info
    lo, hi = min(nums) - 3, max(nums) + 3
    win = ref.window(lo, hi)
    status, notes = OK, []
    for f in frags:
        if f in win:
            continue
        where = ref.find_line(f)
        if where:
            status = _merge(status, WARN)
            notes.append(f"Zitat-Teil steht in Zeile {where}, nicht bei Zeile {'/'.join(map(str, nums))}")
        else:
            status = _merge(status, FAIL)
            notes.append(f"Zitat-Teil nicht im Referenztext gefunden: „{f[:60]}…“")
    if status == OK:
        notes.append(f"Zitat gefunden ({fname}, Zeile {'/'.join(map(str, nums))})")
    return status, notes, info


UNIT_PATTERNS = [
    ("binary", re.compile(r"binary", re.I)),
    ("ordinal", re.compile(r"ordinal\s*\(?\s*(-?\d+)\s*[-–]\s*(-?\d+)", re.I)),
    ("approx", re.compile(r"approx\.?\s*(-?\d+(?:\.\d+)?)\s*(?:to|[-–])\s*(-?\d+(?:\.\d+)?)", re.I)),
    ("index", re.compile(r"(?:index|scale|interval)\s*\(?\s*(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)", re.I)),
]


def check_unit(unit: str | None, stats: dict | None) -> tuple[str, list[str]]:
    if unit is None:
        return OK, ["Einheit wird nicht geändert"]
    if not stats or stats["n"] == 0:
        return WARN, ["Keine Werte in der DB, Einheit nicht prüfbar"]
    mn, mx, nd, ints = stats["min"], stats["max"], stats["distinct"], stats["ints"]
    real = f"echte Werte {mn:g} bis {mx:g}, {nd} verschiedene"
    for kind, rx in UNIT_PATTERNS:
        m = rx.search(unit)
        if not m:
            continue
        if kind == "binary":
            ok = mn >= 0 and mx <= 1 and nd <= 2 and ints
        elif kind == "ordinal":
            lo, hi = int(m.group(1)), int(m.group(2))
            ok = ints and mn >= lo and mx <= hi and nd <= hi - lo + 1
        elif kind == "approx":
            lo, hi = float(m.group(1)), float(m.group(2))
            tol = 0.2 * (hi - lo)
            ok = abs(mn - lo) <= tol and abs(mx - hi) <= tol
        else:
            lo, hi = float(m.group(1)), float(m.group(2))
            eps = 1e-9 + 0.001 * (hi - lo)
            ok = mn >= lo - eps and mx <= hi + eps
        return (OK, [f"Einheit passt ({real})"]) if ok else (FAIL, [f"Einheit „{unit}“ passt nicht: {real}"])
    return WARN, [f"Einheit „{unit}“ nicht automatisch prüfbar ({real})"]


def _db_facts(codes: list[str]) -> tuple[dict, dict, dict]:
    conn = tools.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT column_name, character_maximum_length FROM information_schema.columns "
                        "WHERE table_name = 'indicator_metadata'")
            maxlen = {c: l for c, l in cur.fetchall()}
            cur.execute("SELECT indicator_code, description FROM indicator_metadata WHERE indicator_code = ANY(%s)", (codes,))
            meta = {c: d for c, d in cur.fetchall()}
            cur.execute("SELECT indicator_code, COUNT(*), MIN(value), MAX(value), COUNT(DISTINCT value), "
                        "BOOL_AND(value = ROUND(value::numeric)) FROM indicators "
                        "WHERE indicator_code = ANY(%s) GROUP BY indicator_code", (codes,))
            stats = {c: {"n": n, "min": mn, "max": mx, "distinct": nd, "ints": bool(i)}
                     for c, n, mn, mx, nd, i in cur.fetchall()}
    finally:
        conn.rollback()
        conn.close()
    return maxlen, meta, stats


def check_sql_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    statements, _ = sqlfile.split_statements(text)
    global_issues, blocks, codes = [], [], []

    for st in statements:
        head = st.sql.split(None, 1)[0].upper()
        if head == "BEGIN":
            continue
        if head in ("COMMIT", "END"):
            global_issues.append(f"Zeile {st.line}: aktives COMMIT in der Datei (darf nur auskommentiert sein)")
            continue
        code = next((m.group(1) for c in st.comments if (m := CODE_LINE.match(c))), None)
        b = {"zeile": st.line, "code": code, "status": OK, "notizen": [], "sql": st.sql,
             "set": {}, "sicherheit": None, "beleg": {}}
        upd = sqlfile.parse_update(st.sql)
        if not upd:
            b["status"] = FAIL
            b["notizen"].append("Kein erlaubtes Statement (nur UPDATE indicator_metadata SET … WHERE … ist zulässig)")
            blocks.append(b)
            continue
        b["set"] = upd["set"]
        where_code = re.search(r"indicator_code\s*=\s*'([^']+)'", upd["where"])
        where_code = where_code.group(1) if where_code else None
        if not code:
            b["code"] = code = where_code
            b["status"] = _merge(b["status"], WARN)
            b["notizen"].append("Code-Kommentar fehlt")
        if where_code != code:
            b["status"] = FAIL
            b["notizen"].append(f"Code im Kommentar ({code}) ≠ Code im WHERE ({where_code})")
        if GUARD not in re.sub(r"\s+", "", upd["where"]).lower():
            b["status"] = FAIL
            b["notizen"].append("Schutzbedingung fehlt: AND (description IS NULL OR TRIM(description) = '')")
        unknown = set(upd["columns"]) - {"name", "unit", "description"}
        if set(upd["columns"]) - set(upd["set"]):
            b["status"] = FAIL
            b["notizen"].append("Jede Spalte muss einen Text-Wert in einfachen Anführungszeichen bekommen")
        if unknown:
            b["status"] = FAIL
            b["notizen"].append(f"Unerlaubte Spalten im SET: {', '.join(sorted(unknown))}")
        sich = next((m for c in st.comments if (m := SICHER_LINE.match(c))), None)
        if sich:
            b["sicherheit"] = sich.group(1).upper()
            if b["sicherheit"] != "HOCH":
                b["status"] = _merge(b["status"], WARN)
                b["notizen"].append(f"Sicherheit {b['sicherheit']}{sich.group(2)}")
        b["_comments"] = st.comments
        blocks.append(b)
        if code:
            codes.append(code)

    maxlen, meta, stats = _db_facts(codes) if codes else ({}, {}, {})
    ref_cache: dict = {}
    for b in blocks:
        comments = b.pop("_comments", [])
        if b["status"] == FAIL and not b["set"]:
            continue
        code = b["code"]
        if code not in meta:
            b["status"] = FAIL
            b["notizen"].append("Code existiert nicht in indicator_metadata")
        else:
            if meta[code] and meta[code].strip():
                b["status"] = _merge(b["status"], WARN)
                b["notizen"].append("Beschreibung ist schon befüllt, UPDATE würde 0 Zeilen ändern")
        for col, val in b["set"].items():
            lim = maxlen.get(col)
            if lim and len(val) > lim:
                b["status"] = FAIL
                b["notizen"].append(f"{col} zu lang: {len(val)} Zeichen, erlaubt {lim}")
            if not val.strip():
                b["status"] = FAIL
                b["notizen"].append(f"{col} ist leer")
        s, notes, info = check_beleg(comments, ref_cache)
        b["status"] = _merge(b["status"], s)
        b["notizen"] += notes
        b["beleg"] = info
        s, notes = check_unit(b["set"].get("unit"), stats.get(code))
        b["status"] = _merge(b["status"], s)
        b["notizen"] += notes
        b["werte"] = stats.get(code)

    counts = {k: sum(1 for b in blocks if b["status"] == k) for k in (OK, WARN, FAIL)}
    return {"datei": path.name, "global": global_issues, "bloecke": blocks, "anzahl": counts}


def write_report(run_dir: Path, results: list[dict]) -> Path:
    lines = [f"# Auto-Prüfung", "", f"Lauf: `{run_dir.name}`  ", f"Geprüft: {datetime.now():%Y-%m-%d %H:%M}", ""]
    for r in results:
        c = r["anzahl"]
        lines += [f"## {r['datei']}", "",
                  f"✅ {c[OK]} sauber · ⚠️ {c[WARN]} ansehen · ❌ {c[FAIL]} fehlerhaft", ""]
        for g in r["global"]:
            lines.append(f"- ❌ **Datei:** {g}")
        if r["global"]:
            lines.append("")
        for b in sorted(r["bloecke"], key=lambda x: -RANK[x["status"]]):
            lines.append(f"### {ICON[b['status']]} {b['code'] or '(ohne Code)'}  (Zeile {b['zeile']})")
            for n in b["notizen"]:
                lines.append(f"- {n}")
            if b["set"].get("name"):
                lines.append(f"- Vorschlag Name: {b['set']['name']}")
            if b["set"].get("unit"):
                lines.append(f"- Vorschlag Einheit: {b['set']['unit']}")
            lines.append("")
    out = run_dir / "pruefung.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "pruefung.json").write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return out


def run_check(run_dir: Path) -> list[dict]:
    sql_files = sorted(run_dir.glob("*.sql"))
    results = [check_sql_file(p) for p in sql_files]
    if results:
        write_report(run_dir, results)
        total = {k: sum(r["anzahl"][k] for r in results) for k in (OK, WARN, FAIL)}
        has_global = any(r["global"] for r in results)
        runs.set_status(run_dir, "geprüft",
                        f"Auto-Prüfung: {total[OK]} OK, {total[WARN]} ansehen, {total[FAIL]} Fehler"
                        + (", Datei-Fehler" if has_global else ""))
    return results
