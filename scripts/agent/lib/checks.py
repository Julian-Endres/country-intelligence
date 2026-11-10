"""
Auto-Prüfung eines Lauf-Ordners (ohne KI), Stand Metadaten v3.

Prüft jede Vorschlags-SQL-Datei (*.sql) im Lauf-Ordner, Block für Block:
  1. Struktur   nur UPDATE indicator_metadata, WHERE nur der Code, nur erlaubte Spalten, lesbare Werte
  2. Felder     Wertelisten, Beschreibung = ein Satz, Einheit nur bei Messgrößen, value_labels bei Stufen,
                key_info 1–5 Punkte, keywords 3–8
  3. Belege     Hauptbeleg (Definition) und je ein Beleg pro key_info-Punkt (außer "Note: ...");
                steht das Zitat wirklich an der genannten Stelle im Referenztext?
  4. Datenbank  Code vorhanden, Längen, was würde ersetzt, schon von Julian freigegeben?
  5. Werte      echte Werte gegen scale_min/scale_max, binary, value_labels (Datenauffälligkeiten)

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
    r"^Beleg(?:\s+(?P<label>k\d))?:\s*(?P<file>[^,]+?),\s*(?:S\.\s*(?P<page>\d+),\s*)?"
    r"Zeile\s*(?P<lines>[\d\s/,\-–]+?):\s*[\"“„](?P<quote>.+)[\"”“]\s*$")
QUELLE_LINE = re.compile(r"^Quelle(?:\s+(?P<label>k\d))?:\s*(?P<url>https?://\S+)")
SICHER_LINE = re.compile(r"^Sicherheit:\s*(HOCH|MITTEL|UNSICHER)\b(.*)$", re.IGNORECASE)
PAGE_MARK = re.compile(r"^=== Seite (\d+) ===\s*$")
GUARD = "(descriptionisnullortrim(description)='')"

# ---------------------------------------------------------------- Feldregeln (Metadaten v3)

TEXT_COLS = ("name", "description", "unit", "producer_definition", "value_labels", "reference",
             "scale_type", "direction", "data_origin", "temporal_type")
NUM_COLS = ("scale_min", "scale_max")
LIST_COLS = ("key_info", "keywords")
# Spalten, die ein Vorschlag setzen darf (apply.py überträgt nur diese)
ALLOWED_COLUMNS = TEXT_COLS + NUM_COLS + LIST_COLS
REQUIRED = ("name", "description")

ENUMS = {
    "scale_type": ("index", "ordinal", "binary", "categorical", "percent", "count", "currency",
                   "rate", "ratio", "measure", "other"),
    "direction": ("higher_is_better", "higher_is_worse", "neutral", "not_applicable"),
    "data_origin": ("expert_survey", "official_statistics", "population_survey", "model_estimate",
                    "event_count", "administrative_record", "other"),
    "temporal_type": ("annual", "survey_wave", "snapshot", "irregular", "other"),
}
NO_UNIT = ("index", "ordinal", "binary", "categorical")
LABELLED = ("ordinal", "binary", "categorical")
DESC_MAX = 200
KEY_INFO_MAX_CHARS = 300
RANGE_IN_TEXT = re.compile(r"\d\s*(?:-|–|to)\s*\d")
PAGE_IN_REF = re.compile(r"\b(?:S\.|p\.|page|Seite)\s*\d", re.IGNORECASE)
LABEL_ITEM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*=\s*(.+?)\s*$")


def _norm(s: str) -> str:
    """Nur Buchstaben und Ziffern, klein. Macht den Vergleich robust gegen Satzzeichen und Umbrüche."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _merge(a: str, b: str) -> str:
    return a if RANK[a] >= RANK[b] else b


class Block:
    """Sammelt Status und Notizen eines Vorschlags."""

    def __init__(self, line: int, code: str | None, sql: str):
        self.d = {"zeile": line, "code": code, "status": OK, "notizen": [], "sql": sql,
                  "set": {}, "alt": {}, "sicherheit": None, "beleg": {}, "belege_ki": [], "werte": None}

    def add(self, status: str, note: str) -> None:
        self.d["status"] = _merge(self.d["status"], status)
        self.d["notizen"].append(note)


# ---------------------------------------------------------------- Referenztexte und Belege

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
        # Seite je Zeile aus den Markern "=== Seite N ===" (pdf_to_text)
        self.page, cur = [], None
        for l in self.lines:
            m = PAGE_MARK.match(l)
            if m:
                cur = int(m.group(1))
            self.page.append(cur)

    def page_of(self, line: int) -> int | None:
        return self.page[line - 1] if 1 <= line <= len(self.page) else None

    def window(self, lo: int, hi: int) -> str:
        lo, hi = max(1, lo), min(len(self.lines), hi)
        return "".join(self.norm[lo - 1:hi])

    def find_line(self, frag: str) -> int | None:
        idx = self.full.find(frag)
        if idx == -1:
            return None
        return bisect.bisect_right(self.offsets, idx)  # 1-basierte Zeilennummer


def _frags(text: str) -> list[str]:
    return [f for f in (_norm(x) for x in re.split(r"\.\.\.|…", text)) if len(f) >= 8]


def verify_beleg(m: re.Match, ref_cache: dict, what: str) -> tuple[str, list[str], dict]:
    """Prüft einen Beleg-Kommentar gegen den Referenztext."""
    fname = Path(m.group("file").strip()).name
    nums = [int(x) for x in re.findall(r"\d+", m.group("lines"))]
    quote = m.group("quote")
    page = int(m.group("page")) if m.group("page") else None
    info = {"datei": fname, "seite": page, "zeilen": nums, "zitat": quote}
    ref_path = tools.REF_DIR / fname
    if not ref_path.exists():
        return FAIL, [f"{what}: Referenzdatei {fname} nicht gefunden"], info
    ref = ref_cache.setdefault(fname, RefText(ref_path))
    frags = _frags(quote)
    if not frags:
        return WARN, [f"{what}: Zitat zu kurz für eine automatische Prüfung"], info
    win = ref.window(min(nums) - 3, max(nums) + 3)
    status, notes = OK, []
    for f in frags:
        if f in win:
            continue
        where = ref.find_line(f)
        if where:
            status = _merge(status, WARN)
            notes.append(f"{what}: Zitat steht in Zeile {where}, nicht bei Zeile {'/'.join(map(str, nums))}")
        else:
            status = _merge(status, FAIL)
            notes.append(f"{what}: Zitat nicht im Referenztext gefunden: „{f[:60]}…“")
    real_page = ref.page_of(min(nums))
    if page is not None and real_page is not None and real_page != page:
        status = _merge(status, WARN)
        notes.append(f"{what}: Seitenangabe S. {page} stimmt nicht, Zeile {min(nums)} steht auf S. {real_page}")
    if status == OK:
        notes.append(f"{what}: Zitat gefunden ({fname}, Zeile {'/'.join(map(str, nums))})")
    return status, notes, info


def collect_belege(comments: list[str]) -> tuple[dict, dict]:
    """Hauptbeleg (ohne Label) und key_info-Belege (k1..k5). Werte: ('datei', match) oder ('url', url)."""
    main, ki = None, {}
    for c in comments:
        m = BELEG_LINE.match(c)
        q = QUELLE_LINE.match(c) if not m else None
        if not (m or q):
            continue
        label = (m or q).group("label")
        entry = ("datei", m) if m else ("url", q.group("url"))
        if label:
            ki[int(label[1:])] = entry
        elif main is None:
            main = entry
    return main, ki


def check_belege(b: Block, comments: list[str], ref_cache: dict) -> None:
    s = b.d["set"]
    main, ki = collect_belege(comments)
    # Hauptbeleg: belegt Definition und Beschreibung
    if main is None:
        b.add(FAIL, "Kein Hauptbeleg (-- Beleg: … oder -- Quelle: https://…)")
    elif main[0] == "url":
        b.d["beleg"] = {"quelle": main[1]}
        b.add(WARN if s.get("producer_definition") else OK,
              f"Hauptbeleg nur als URL ({main[1]}), Wortlaut nicht automatisch prüfbar")
    else:
        st, notes, info = verify_beleg(main[1], ref_cache, "Hauptbeleg")
        b.d["beleg"] = info
        for n in notes:
            b.add(st, n)
        pd = s.get("producer_definition")
        if pd and info.get("datei") in ref_cache:
            ref = ref_cache[info["datei"]]
            missing = [f for f in _frags(pd) if f not in ref.full]
            if missing:
                b.add(FAIL, "producer_definition ist nicht wörtlich im Referenztext")
            else:
                b.add(OK, "producer_definition wörtlich gefunden")
    # key_info-Belege
    items = s.get("key_info") or []
    need = [i for i, t in enumerate(items, 1) if not t.startswith("Note:")]
    for i in need:
        e = ki.get(i)
        if e is None:
            b.add(FAIL, f"key_info {i}: kein Beleg (-- Beleg k{i}: …) und nicht als „Note:“ markiert")
        elif e[0] == "url":
            b.d["belege_ki"].append({"punkt": i, "quelle": e[1]})
            b.add(WARN, f"key_info {i}: Beleg nur als URL, nicht automatisch prüfbar")
        else:
            st, notes, info = verify_beleg(e[1], ref_cache, f"key_info {i}")
            b.d["belege_ki"].append({"punkt": i, **info})
            for n in notes:
                b.add(st, n)
    extra = sorted(set(ki) - set(need))
    if extra:
        b.add(WARN, f"Belege ohne passenden key_info-Punkt: {', '.join('k' + str(x) for x in extra)}")


# ---------------------------------------------------------------- Feldregeln

def check_fields(b: Block) -> None:
    s, cols = b.d["set"], b.d["columns"]
    for col in REQUIRED:
        if not (isinstance(s.get(col), str) and s[col].strip()):
            b.add(FAIL, f"{col} fehlt oder ist leer")
    for col, v in s.items():
        if v is None:
            continue
        if col in TEXT_COLS and not isinstance(v, str):
            b.add(FAIL, f"{col}: muss Text sein")
        if col in NUM_COLS and not isinstance(v, float):
            b.add(FAIL, f"{col}: muss eine Zahl sein")
        if col in LIST_COLS and not isinstance(v, list):
            b.add(FAIL, f"{col}: muss eine Liste sein (ARRAY['…', '…'])")
        if isinstance(v, str) and not v.strip():
            b.add(FAIL, f"{col}: leerer Text, bitte NULL verwenden")
    for col, allowed in ENUMS.items():
        v = s.get(col)
        if isinstance(v, str) and v not in allowed:
            b.add(FAIL, f"{col} = „{v}“ ist nicht erlaubt ({', '.join(allowed)})")

    desc = s.get("description")
    if isinstance(desc, str) and desc.strip():
        sentences = [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", desc.strip()) if x]
        if len(desc) > DESC_MAX:
            b.add(FAIL, f"description zu lang: {len(desc)} Zeichen, erlaubt {DESC_MAX}")
        if len(sentences) != 1:
            b.add(FAIL, f"description muss genau ein Satz sein (gefunden: {len(sentences)})")
        if not desc.rstrip().endswith("."):
            b.add(WARN, "description endet nicht mit Punkt")
        if RANGE_IN_TEXT.search(desc):
            b.add(WARN, "description enthält offenbar einen Zahlenbereich (gehört in scale_min/scale_max)")

    st = s.get("scale_type")
    unit = s.get("unit")
    if "unit" in cols or st:
        if st in NO_UNIT and unit:
            b.add(FAIL, f"unit muss bei scale_type {st} leer sein (NULL)")
        if st and st not in NO_UNIT and st != "other" and not unit:
            b.add(WARN, f"unit fehlt, bei scale_type {st} erwartet")
    if isinstance(unit, str) and RANGE_IN_TEXT.search(unit):
        b.add(FAIL, f"unit enthält einen Wertebereich („{unit}“), der gehört in scale_min/scale_max")

    labels = s.get("value_labels")
    if st in LABELLED and not labels:
        b.add(WARN, f"value_labels fehlen, bei scale_type {st} erwartet")
    if labels and st and st not in LABELLED:
        b.add(FAIL, f"value_labels nur bei {', '.join(LABELLED)}, nicht bei {st}")
    if isinstance(labels, str):
        parsed = [LABEL_ITEM.match(x) for x in labels.split(";") if x.strip()]
        if not all(parsed):
            b.add(FAIL, "value_labels nicht im Format „0 = …; 1 = …“")
        else:
            b.d["labels"] = [float(m.group(1)) for m in parsed]

    mn, mx = s.get("scale_min"), s.get("scale_max")
    if isinstance(mn, float) and isinstance(mx, float) and mn >= mx:
        b.add(FAIL, "scale_min muss kleiner als scale_max sein")
    if st == "binary" and (mn, mx) not in ((0.0, 1.0), (None, None)):
        b.add(WARN, "binary: erwartet scale_min 0 und scale_max 1")
    if st == "percent" and isinstance(mx, float) and mx != 100.0:
        b.add(WARN, f"percent mit scale_max {mx:g}, erwartet 100")

    ki = s.get("key_info")
    if isinstance(ki, list):
        if not 1 <= len(ki) <= 5:
            b.add(FAIL, f"key_info braucht 1 bis 5 Punkte (gefunden: {len(ki)})")
        for i, t in enumerate(ki, 1):
            if len(t) > KEY_INFO_MAX_CHARS:
                b.add(WARN, f"key_info {i} ist lang ({len(t)} Zeichen)")
    kw = s.get("keywords")
    if isinstance(kw, list) and not 3 <= len(kw) <= 8:
        b.add(WARN, f"keywords: 3 bis 8 erwartet (gefunden: {len(kw)})")
    ref = s.get("reference")
    if isinstance(ref, str) and PAGE_IN_REF.search(ref):
        b.add(WARN, "reference nennt eine Seite, bitte Abschnitt bzw. Variableneintrag angeben")


# ---------------------------------------------------------------- Datenbank und echte Werte

def _db_facts(codes: list[str]) -> tuple[dict, dict, dict]:
    conn = tools.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT column_name, character_maximum_length FROM information_schema.columns "
                        "WHERE table_name = 'indicator_metadata'")
            maxlen = {c: l for c, l in cur.fetchall()}
            cols = ", ".join(ALLOWED_COLUMNS)
            cur.execute(f"SELECT indicator_code, {cols}, metadata_reviewed_at FROM indicator_metadata "
                        "WHERE indicator_code = ANY(%s)", (codes,))
            meta = {}
            for row in cur.fetchall():
                vals = dict(zip(ALLOWED_COLUMNS, row[1:-1]))
                vals = {k: (float(v) if k in NUM_COLS and v is not None else v) for k, v in vals.items()}
                meta[row[0]] = {"werte": vals, "freigegeben": row[-1].isoformat() if row[-1] else None}
            cur.execute("SELECT indicator_code, COUNT(*), MIN(value), MAX(value), COUNT(DISTINCT value), "
                        "BOOL_AND(value = ROUND(value::numeric)) FROM indicators "
                        "WHERE indicator_code = ANY(%s) GROUP BY indicator_code", (codes,))
            stats = {c: {"n": n, "min": mn, "max": mx, "distinct": nd, "ints": bool(i)}
                     for c, n, mn, mx, nd, i in cur.fetchall()}
            cur.execute("SELECT indicator_code, array_agg(DISTINCT value ORDER BY value) FROM indicators "
                        "WHERE indicator_code = ANY(%s) GROUP BY indicator_code "
                        "HAVING COUNT(DISTINCT value) <= 20", (codes,))
            levels = {c: [float(x) for x in v] for c, v in cur.fetchall()}
    finally:
        conn.rollback()
        conn.close()
    for c, lv in levels.items():
        stats[c]["stufen"] = lv
    return maxlen, meta, stats


def check_values(b: Block, stats: dict | None) -> None:
    s = b.d["set"]
    if not stats or not stats["n"]:
        b.add(WARN, "Keine Werte in der DB, Skala nicht prüfbar")
        return
    real = f"echte Werte {stats['min']:g} bis {stats['max']:g}, {stats['distinct']} verschiedene"
    mn, mx = s.get("scale_min"), s.get("scale_max")
    out = (isinstance(mn, float) and stats["min"] < mn - 1e-9) or (isinstance(mx, float) and stats["max"] > mx + 1e-9)
    if out:
        b.add(WARN, f"Datenauffälligkeit: {real}, außerhalb von scale_min/scale_max "
                    f"({'' if mn is None else f'{mn:g}'} bis {'' if mx is None else f'{mx:g}'})")
    elif mn is not None or mx is not None:
        b.add(OK, f"Skala passt ({real})")
    st = s.get("scale_type")
    lv = stats.get("stufen")
    if st == "binary" and lv is not None and not set(lv) <= {0.0, 1.0}:
        b.add(WARN, f"Datenauffälligkeit: binary, aber Werte {', '.join(f'{x:g}' for x in lv)}")
    if st in ("ordinal", "binary", "categorical") and not stats["ints"]:
        b.add(WARN, f"Datenauffälligkeit: scale_type {st}, aber nicht nur ganze Zahlen")
    if b.d.get("labels") and lv is not None:
        unlabelled = [x for x in lv if x not in b.d["labels"]]
        if unlabelled:
            b.add(WARN, f"Datenauffälligkeit: Werte ohne value_label: {', '.join(f'{x:g}' for x in unlabelled)}")


def check_db(b: Block, maxlen: dict, meta: dict) -> None:
    code = b.d["code"]
    if code not in meta:
        b.add(FAIL, "Code existiert nicht in indicator_metadata")
        return
    old = meta[code]["werte"]
    b.d["alt"] = {c: old.get(c) for c in b.d["set"]}
    missing = [c for c in ALLOWED_COLUMNS if c not in b.d["set"]]
    if missing:
        b.add(WARN, f"Felder fehlen im Vorschlag (bitte alle nennen, notfalls NULL): {', '.join(missing)}")
    st = b.d["set"].get("scale_type", old.get("scale_type"))
    if "unit" not in b.d["set"] and old.get("unit"):
        if st in NO_UNIT:
            b.add(FAIL, f"Alte Einheit „{old['unit']}“ bliebe stehen, bei scale_type {st} muss unit = NULL gesetzt werden")
        elif RANGE_IN_TEXT.search(old["unit"]):
            b.add(FAIL, f"Alte Einheit „{old['unit']}“ mit Wertebereich bliebe stehen, bitte unit neu setzen")
    changed = [c for c, v in b.d["set"].items() if old.get(c) not in (None, "", []) and old.get(c) != v]
    if changed:
        b.d["ersetzt"] = changed
        b.d["notizen"].append(f"Ersetzt vorhandene Werte: {', '.join(changed)}")
    if meta[code]["freigegeben"]:
        b.d["freigegeben"] = meta[code]["freigegeben"]
        if changed:
            b.add(WARN, f"Schon von Julian freigegeben ({meta[code]['freigegeben'][:10]}), wird ersetzt")
    for col, val in b.d["set"].items():
        lim = maxlen.get(col)
        if lim and isinstance(val, str) and len(val) > lim:
            b.add(FAIL, f"{col} zu lang: {len(val)} Zeichen, erlaubt {lim}")


# ---------------------------------------------------------------- Datei prüfen

def check_sql_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    statements, _ = sqlfile.split_statements(text)
    global_issues, blocks, codes, pending = [], [], [], []

    for st in statements:
        head = st.sql.split(None, 1)[0].upper()
        if head == "BEGIN":
            continue
        if head in ("COMMIT", "END"):
            global_issues.append(f"Zeile {st.line}: aktives COMMIT in der Datei (darf nur auskommentiert sein)")
            continue
        code = next((m.group(1) for c in st.comments if (m := CODE_LINE.match(c))), None)
        b = Block(st.line, code, st.sql)
        upd = sqlfile.parse_update(st.sql)
        if not upd:
            b.add(FAIL, "Kein erlaubtes Statement (nur UPDATE indicator_metadata SET … WHERE … ist zulässig)")
            blocks.append(b)
            continue
        b.d["set"], b.d["columns"] = upd["set"], upd["columns"]
        for e in upd["errors"]:
            b.add(FAIL, f"Nicht lesbar: {e}")
        where_code = re.search(r"indicator_code\s*=\s*'([^']+)'", upd["where"])
        where_code = where_code.group(1) if where_code else None
        if not code:
            b.d["code"] = code = where_code
            b.add(WARN, "Code-Kommentar fehlt")
        if where_code != code:
            b.add(FAIL, f"Code im Kommentar ({code}) ≠ Code im WHERE ({where_code})")
        where_norm = re.sub(r"\s+", "", upd["where"]).lower()
        if where_code and where_norm not in (f"indicator_code='{where_code.lower()}'",
                                             f"indicator_code='{where_code.lower()}'and{GUARD}"):
            b.add(FAIL, "WHERE darf nur den Code enthalten: WHERE indicator_code = '…'")
        unknown = [c for c in upd["columns"] if c not in ALLOWED_COLUMNS]
        if unknown:
            b.add(FAIL, f"Unerlaubte Spalten im SET: {', '.join(unknown)}")
        sich = next((m for c in st.comments if (m := SICHER_LINE.match(c))), None)
        if sich:
            b.d["sicherheit"] = sich.group(1).upper()
            if b.d["sicherheit"] != "HOCH":
                b.add(WARN, f"Sicherheit {b.d['sicherheit']}{sich.group(2)}")
        else:
            b.add(WARN, "Sicherheit fehlt")
        check_fields(b)
        blocks.append(b)
        pending.append((b, st.comments))
        if code:
            codes.append(code)

    seen = [b.d["code"] for b in blocks if b.d["code"]]
    for c in {c for c in seen if seen.count(c) > 1}:
        global_issues.append(f"Code mehrfach in der Datei: {c}")

    maxlen, meta, stats = _db_facts(codes) if codes else ({}, {}, {})
    ref_cache: dict = {}
    for b, comments in pending:
        check_db(b, maxlen, meta)
        check_belege(b, comments, ref_cache)
        check_values(b, stats.get(b.d["code"]))
        b.d["werte"] = stats.get(b.d["code"])

    out = [b.d for b in blocks]
    counts = {k: sum(1 for b in out if b["status"] == k) for k in (OK, WARN, FAIL)}
    return {"datei": path.name, "global": global_issues, "bloecke": out, "anzahl": counts}


# ---------------------------------------------------------------- Bericht

QUIET = ("Zitat gefunden", "Skala passt", "producer_definition wörtlich")


def is_quiet(note: str) -> bool:
    """Erfolgsmeldungen, die im Bericht und in der Prüfung nicht als Hinweis erscheinen."""
    return any(q in note for q in QUIET)


def write_report(run_dir: Path, results: list[dict]) -> Path:
    lines = ["# Auto-Prüfung", "", f"Lauf: `{run_dir.name}`  ", f"Geprüft: {datetime.now():%Y-%m-%d %H:%M}", ""]
    for r in results:
        c = r["anzahl"]
        lines += [f"## {r['datei']}", "", f"✅ {c[OK]} sauber · ⚠️ {c[WARN]} ansehen · ❌ {c[FAIL]} fehlerhaft", ""]
        for g in r["global"]:
            lines.append(f"- ❌ **Datei:** {g}")
        if r["global"]:
            lines.append("")
        auff = [(b["code"], n) for b in r["bloecke"] for n in b["notizen"] if n.startswith("Datenauffälligkeit")]
        if auff:
            lines += ["### Datenauffälligkeiten (für befunde.md / Backlog)", ""]
            lines += [f"- {code}: {n.split(': ', 1)[1]}" for code, n in auff] + [""]
        for b in sorted(r["bloecke"], key=lambda x: -RANK[x["status"]]):
            lines.append(f"### {ICON[b['status']]} {b['code'] or '(ohne Code)'}  (Zeile {b['zeile']})")
            lines += [f"- {n}" for n in b["notizen"] if not is_quiet(n)]
            if b["set"].get("description"):
                lines.append(f"- Vorschlag: {b['set']['description']}")
            lines.append("")
    out = run_dir / "pruefung.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "pruefung.json").write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str),
                                          encoding="utf-8")
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
