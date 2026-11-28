"""
Gemeinsame Werkzeuge für alle Agenten (Sekretär, Quellen-Pfleger, Unterstützer).

Grundsatz: Kein Werkzeug kann die Datenbank ändern. Schreiben ist nur in zwei
Ordnern möglich:
  - den Lauf-Ordner des aktuellen Laufs (scripts/agent/output/<lauf>/)
  - data/raw/reference/     Referenzmaterial (Codebooks usw.), von Git ignoriert
"""

import itertools
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
import requests
from dotenv import load_dotenv
from claude_agent_sdk import create_sdk_mcp_server, tool

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[3]
REF_DIR = REPO_ROOT / "data" / "raw" / "reference"

# Lauf-Ordner des aktuellen Laufs; wird vom Startskript gesetzt (set_run_dir)
RUN_DIR: Path | None = None


def set_run_dir(run_dir: Path) -> None:
    global RUN_DIR
    RUN_DIR = run_dir

# Ordner, in denen nach vorhandenen Dateien gesucht werden darf (nur lesen)
SEARCH_ROOTS = [
    REF_DIR,
    REPO_ROOT / "data" / "raw",
    Path.home() / "Dokumente" / "Country-Intelligence",
    Path.home() / "Documents" / "Country-Intelligence",
    Path.home() / "Downloads",
    REPO_ROOT / "scripts" / "agent" / "output",   # Leitfäden früherer Läufe (nur lesen; 15.11.2026)
    REPO_ROOT / "scripts" / "pipeline",   # Loader lesen (nur lesen; 19.11.2026, Entscheidung Julian)
]

MAX_ROWS = 50
MAX_CELL_CHARS = 200
TIMEOUT_MS = 30_000
MAX_DOWNLOAD_MB = 150
DOWNLOAD_TYPES = {".pdf", ".csv", ".xlsx", ".xls", ".zip", ".txt", ".json"}
MAX_READ_LINES = 150
MAX_SEARCH_HITS = 25

# Protokolle für die Belegführung
QUERY_LOG: list[dict[str, Any]] = []
ACTION_LOG: list[str] = []


def _log(action: str) -> None:
    ACTION_LOG.append(f"{datetime.now():%H:%M:%S} {action}")


def _text(s: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": s}]}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- Datenbank

def connect():
    """Read-only-Verbindung (auch für die Prüfskripte)."""
    return _connect()


def _connect():
    user = os.getenv("DB_AGENT_USER")
    password = os.getenv("DB_AGENT_PASSWORD")
    if not user or not password:
        raise RuntimeError("DB_AGENT_USER / DB_AGENT_PASSWORD fehlen in .env")
    if user != "ci_agent_readonly":
        raise RuntimeError(f"Agent darf nur als ci_agent_readonly laufen, nicht als {user}")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=user,
        password=password,
        options=f"-c statement_timeout={TIMEOUT_MS} -c default_transaction_read_only=on",
    )


def run_query(sql: str) -> str:
    entry: dict[str, Any] = {"sql": sql}
    try:
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description is None:
                    result = "Abfrage ohne Ergebniszeilen."
                    entry["rows"] = 0
                else:
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchmany(MAX_ROWS + 1)
                    truncated = len(rows) > MAX_ROWS
                    rows = rows[:MAX_ROWS]
                    lines = [" | ".join(cols)]
                    for row in rows:
                        cells = []
                        for v in row:
                            s = "NULL" if v is None else str(v)
                            if len(s) > MAX_CELL_CHARS:
                                s = s[:MAX_CELL_CHARS] + "…"
                            cells.append(s)
                        lines.append(" | ".join(cells))
                    if truncated:
                        lines.append(f"(abgeschnitten nach {MAX_ROWS} Zeilen, für mehr mit LIMIT/OFFSET oder Aggregation arbeiten)")
                    result = "\n".join(lines)
                    entry["rows"] = len(rows)
                    entry["truncated"] = truncated
        finally:
            conn.rollback()
            conn.close()
    except Exception as e:
        result = f"FEHLER: {e}"
        entry["error"] = str(e)
    QUERY_LOG.append(entry)
    return result


@tool(
    "sql_query",
    "Führt eine lesende SQL-Abfrage (SELECT) auf der PostgreSQL-Datenbank "
    "country_intelligence aus. Zugang ist read-only. Liefert höchstens 50 Zeilen.",
    {"sql": str},
)
async def sql_query(args: dict[str, Any]) -> dict[str, Any]:
    return _text(run_query(args["sql"]))


# ---------------------------------------------------------------- Dateien finden und holen

@tool(
    "find_files",
    "Sucht vorhandene Dateien, deren Name den Suchbegriff enthält (ohne Groß-/Kleinschreibung), "
    "im Referenzordner, in data/raw, im Ablageordner Dokumente/Country-Intelligence und in Downloads. "
    "Immer zuerst hier suchen, bevor etwas heruntergeladen wird.",
    {"name_contains": str},
)
async def find_files(args: dict[str, Any]) -> dict[str, Any]:
    needle = args["name_contains"].lower()
    hits = []
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and needle in p.name.lower():
                hits.append(f"{p}  ({p.stat().st_size / 1e6:.1f} MB)")
            if len(hits) >= 30:
                break
    _log(f"find_files '{needle}': {len(hits)} Treffer")
    return _text("\n".join(hits) if hits else "Keine Datei gefunden.")


@tool(
    "download_file",
    "Lädt eine Datei (pdf, csv, xlsx, xls, zip, txt, json) per https in den Referenzordner "
    "data/raw/reference/. Überschreibt nichts. Nur verwenden, wenn find_files nichts gefunden hat.",
    {"url": str, "filename": str},
)
async def download_file(args: dict[str, Any]) -> dict[str, Any]:
    url, filename = args["url"], Path(args["filename"]).name
    if not url.startswith("https://"):
        return _text("FEHLER: Nur https-Adressen erlaubt.")
    if Path(filename).suffix.lower() not in DOWNLOAD_TYPES:
        return _text(f"FEHLER: Dateityp nicht erlaubt. Erlaubt: {sorted(DOWNLOAD_TYPES)}")
    REF_DIR.mkdir(parents=True, exist_ok=True)
    target = REF_DIR / filename
    if target.exists():
        return _text(f"Datei existiert bereits: {target}")
    try:
        # Browser-Kennung: manche Server (z. B. ILO/Cloudflare) liefern sonst HTTP 200 mit 0 Bytes (14.11.)
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": ua}) as r:
            r.raise_for_status()
            size = 0
            tmp = target.with_suffix(target.suffix + ".part")
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD_MB * 1e6:
                        f.close()
                        tmp.unlink()
                        return _text(f"FEHLER: Datei größer als {MAX_DOWNLOAD_MB} MB, abgebrochen.")
                    f.write(chunk)
            if size == 0:
                tmp.unlink()
                return _text(f"FEHLER: Leere Antwort (HTTP {r.status_code}, 0 Bytes). Nichts gespeichert.")
            tmp.rename(target)
        if target.suffix.lower() == ".json":
            # API-Antworten oft in einer Zeile: lesbar formatieren, damit Belege sinnvolle Zeilennummern haben
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                target.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            except ValueError as e:
                _log(f"download_file: JSON nicht formatierbar ({e}), Datei unformatiert gespeichert: {target}")
    except Exception as e:
        _log(f"download_file FEHLER {url}: {e}")
        return _text(f"FEHLER beim Download: {e}")
    _log(f"download_file {url} -> {target} ({size / 1e6:.1f} MB)")
    return _text(f"Gespeichert: {target} ({size / 1e6:.1f} MB)")


# ---------------------------------------------------------------- Text aus Dokumenten

@tool(
    "pdf_to_text",
    "Wandelt ein PDF in eine durchsuchbare Textdatei im Referenzordner um (einmalig, danach aus dem Cache). "
    "Seitenwechsel sind als '=== Seite N ===' markiert. Pfad muss aus find_files oder download_file stammen.",
    {"pdf_path": str},
)
async def pdf_to_text(args: dict[str, Any]) -> dict[str, Any]:
    pdf = Path(args["pdf_path"]).expanduser()
    if not any(_inside(pdf, r) for r in SEARCH_ROOTS) or not pdf.exists():
        return _text("FEHLER: PDF nicht gefunden oder außerhalb der erlaubten Ordner.")
    REF_DIR.mkdir(parents=True, exist_ok=True)
    txt = REF_DIR / (pdf.stem + ".txt")
    if txt.exists():
        n = sum(1 for _ in open(txt, encoding="utf-8"))
        return _text(f"Bereits vorhanden: {txt} ({n} Zeilen)")
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    with open(txt, "w", encoding="utf-8") as out:
        for i, page in enumerate(doc, start=1):
            out.write(f"\n=== Seite {i} ===\n")
            out.write(page.get_textpage().get_text_range())
    pages = len(doc)
    n = sum(1 for _ in open(txt, encoding="utf-8"))
    _log(f"pdf_to_text {pdf.name}: {pages} Seiten -> {txt.name}")
    return _text(f"Erstellt: {txt} ({pages} Seiten, {n} Zeilen)")


# Tabellen (xlsx/xls) als Text, gleiches Prinzip wie pdf_to_text (#154, 26.11.2026).
# Jede Zeile trägt Blatt und Excel-Zeilennummer ("Notes!17: ..."), Zellen tabgetrennt, leere Zeilen entfallen.
# Belege zitieren die Zeilennummer der Textdatei (wie bei PDFs); die Excel-Fundstelle steht im Zitat selbst.
TABLE_TYPES = {".xlsx", ".xlsm", ".xls"}
MAX_TABLE_ROWS_PER_SHEET = 300_000
MAX_TABLE_CELL_CHARS = 1_000
WIDE_SHEET_COLS = 200
SHEET_MARK = "=== Blatt {name} ==="


def table_text_path(table: Path) -> Path:
    """Name des Text-Auszugs: <stem>_<endung>.txt (kein Zusammenstoß mit pdf_to_text bei gleichem Namen)."""
    return REF_DIR / f"{table.stem}_{table.suffix.lower().lstrip('.')}.txt"


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        v = int(v)
    if isinstance(v, datetime):
        v = v.date().isoformat() if (v.hour, v.minute, v.second) == (0, 0, 0) else v.isoformat()
    t = re.sub(r"\s+", " ", str(v)).strip()
    return t[:MAX_TABLE_CELL_CHARS] + " …[gekürzt]" if len(t) > MAX_TABLE_CELL_CHARS else t


def _table_sheets(path: Path):
    """Liefert (Blattname, Iterator über (Excel-Zeile, Werte)). Formeln: gespeicherter Wert (data_only)."""
    if path.suffix.lower() == ".xls":
        import xlrd
        book = xlrd.open_workbook(str(path))
        for sh in book.sheets():
            def rows(sh=sh):
                for r in range(sh.nrows):
                    vals = []
                    for c in range(sh.ncols):
                        cell = sh.cell(r, c)
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            vals.append(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode))
                        elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                            vals.append(None)
                        else:
                            vals.append(cell.value)
                    yield r + 1, vals
            yield sh.name, rows()
    else:
        import openpyxl
        # Zweimal öffnen: gespeicherte Werte (data_only) und Formeln. Fehlt zu einer Formel der gespeicherte Wert
        # (Datei nie in Excel gespeichert), wird die Formel sichtbar markiert statt still leer ausgegeben.
        book = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        forms = openpyxl.load_workbook(str(path), read_only=True)
        try:
            for ws, wf in zip(book.worksheets, forms.worksheets):
                def rows(ws=ws, wf=wf):
                    for r, (vals, fvals) in enumerate(zip(ws.iter_rows(values_only=True),
                                                          wf.iter_rows(values_only=True)), start=1):
                        vals = list(vals)
                        for i, (v, f) in enumerate(zip(vals, fvals)):
                            if v is None and isinstance(f, str) and f.startswith("="):
                                vals[i] = f"[Formel ohne gespeicherten Wert: {f}]"
                        yield r, vals
                yield ws.title, rows()
        finally:
            book.close()
            forms.close()


def table_to_text_file(path: Path) -> tuple[Path, list[str]]:
    """Schreibt den Text-Auszug und gibt (Pfad, Meldungen) zurück. Fehler werden nicht geschluckt."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    txt = table_text_path(path)
    tmp = txt.with_suffix(".txt.part")
    notes: list[str] = []
    with open(tmp, "w", encoding="utf-8") as out:
        for name, rows in _table_sheets(path):
            out.write(SHEET_MARK.format(name=name) + "\n")
            n_rows, capped, max_cols, n_formula = 0, None, 0, 0
            for r, vals in rows:
                cells = [_cell(v) for v in vals]
                while cells and cells[-1] == "":
                    cells.pop()
                if not cells:
                    continue
                max_cols = max(max_cols, len(cells))
                n_formula += sum(c.startswith("[Formel ohne gespeicherten Wert") for c in cells)
                if n_rows >= MAX_TABLE_ROWS_PER_SHEET:
                    capped = r
                    break
                out.write(f"{name}!{r}: " + "\t".join(cells) + "\n")
                n_rows += 1
            if capped:
                msg = (f"Blatt {name}: nach {MAX_TABLE_ROWS_PER_SHEET} Zeilen gekappt (ab Excel-Zeile {capped} fehlt alles)")
                out.write(f"=== GEKAPPT: {msg} ===\n")
                notes.append(msg)
            elif n_rows == 0:
                notes.append(f"Blatt {name}: leer")
            else:
                notes.append(f"Blatt {name}: {n_rows} Zeilen, bis {max_cols} Spalten")
            if n_formula:
                notes.append(f"Blatt {name}: {n_formula} Formelzellen ohne gespeicherten Wert (als Formel markiert)")
            if max_cols > WIDE_SHEET_COLS:
                notes.append(f"Blatt {name}: breit ({max_cols} Spalten) – Zeilen sehr lang, "
                             f"gezielt mit search_text suchen, read_text nur mit num_lines=1")
    tmp.rename(txt)
    return txt, notes


@tool(
    "table_to_text",
    "Wandelt eine Excel-Datei (xlsx, xls) in eine durchsuchbare Textdatei im Referenzordner um (einmalig, danach aus dem "
    "Cache). Jedes Blatt beginnt mit '=== Blatt <Name> ==='; jede Zeile beginnt mit Blatt und Excel-Zeile, z. B. "
    "'Notes!17: ...', Zellen sind tabgetrennt, leere Zeilen fehlen. Formeln erscheinen mit dem in der Datei gespeicherten "
    "Wert. Danach mit search_text/read_text lesen. Pfad muss aus find_files oder download_file stammen.",
    {"path": str},
)
async def table_to_text(args: dict[str, Any]) -> dict[str, Any]:
    src = Path(args["path"]).expanduser()
    if not src.is_absolute():
        src = (REPO_ROOT / src).resolve()
    if not any(_inside(src, r) for r in SEARCH_ROOTS) or not src.is_file():
        return _text("FEHLER: Datei nicht gefunden oder außerhalb der erlaubten Ordner.")
    if src.suffix.lower() not in TABLE_TYPES:
        return _text(f"FEHLER: Nur {sorted(TABLE_TYPES)}. PDFs mit pdf_to_text, csv/txt direkt mit read_text.")
    txt = table_text_path(src)
    if txt.exists():
        n = sum(1 for _ in open(txt, encoding="utf-8"))
        return _text(f"Bereits vorhanden: {txt} ({n} Zeilen)")
    try:
        txt, notes = table_to_text_file(src)
    except Exception as e:
        _log(f"table_to_text FEHLER {src.name}: {type(e).__name__}: {e}")
        return _text(f"FEHLER beim Lesen von {src.name}: {type(e).__name__}: {e}. Als Befund festhalten, nicht raten.")
    n = sum(1 for _ in open(txt, encoding="utf-8"))
    _log(f"table_to_text {src.name} -> {txt.name} ({n} Zeilen; " + "; ".join(notes) + ")")
    return _text(f"Erstellt: {txt} ({n} Zeilen)\n" + "\n".join(notes))


def _ref_file(name: str) -> Path | None:
    """Datei im Referenzordner (nur Name) oder voller Pfad aus find_files innerhalb der Suchordner."""
    given = Path(name).expanduser()
    if given.is_absolute():
        if given.is_file() and any(_inside(given, root) for root in SEARCH_ROOTS):
            return given
        return None
    if len(given.parts) > 1:                      # Pfad relativ zur Repo-Wurzel, z. B. scripts/agent/output/<lauf>/leitfaden.md
        p = (REPO_ROOT / given).resolve()
        if p.is_file() and any(_inside(p, root) for root in SEARCH_ROOTS):
            return p
    p = REF_DIR / given.name
    return p if p.exists() else None


def _not_text(p: Path) -> str | None:
    """Binärdateien nicht als Text lesen (sonst Binärmüll ohne Meldung, Fall POLITY5/#154)."""
    suf = p.suffix.lower()
    if suf in TABLE_TYPES:
        return f"FEHLER: {p.name} ist eine Excel-Datei. Erst table_to_text ausführen, dann die erzeugte .txt lesen."
    if suf == ".pdf":
        return f"FEHLER: {p.name} ist ein PDF. Erst pdf_to_text ausführen, dann die erzeugte .txt lesen."
    if suf in {".gz", ".zip", ".parquet", ".dta", ".sav", ".rds"}:
        return f"FEHLER: {p.name} ({suf}) ist kein Text und mit den Werkzeugen nicht lesbar. Als Befund festhalten."
    return None


@tool(
    "search_text",
    "Durchsucht eine Textdatei (Name im Referenzordner oder voller Pfad aus find_files) nach einem Begriff oder regulären Ausdruck "
    "(ohne Groß-/Kleinschreibung). Gibt bis zu 25 Treffer mit Zeilennummer, Seite und etwas Kontext zurück.",
    {"filename": str, "pattern": str},
)
async def search_text(args: dict[str, Any]) -> dict[str, Any]:
    p = _ref_file(args["filename"])
    if not p:
        return _text("FEHLER: Datei nicht im Referenzordner. Erst pdf_to_text (PDF) bzw. table_to_text (xlsx/xls) ausführen.")
    if (err := _not_text(p)):
        return _text(err)
    try:
        rx = re.compile(args["pattern"], re.IGNORECASE)
    except re.error as e:
        return _text(f"FEHLER im Suchmuster: {e}")
    page, hits = 0, []
    with open(p, encoding="utf-8", errors="replace") as fh:
        for i, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n")
            m = re.match(r"=== Seite (\d+) ===", line)
            if m:
                page = int(m.group(1))
                continue
            if rx.search(line):
                hits.append(f"Zeile {i} (S. {page}): {line.strip()[:300]}")
                if len(hits) >= MAX_SEARCH_HITS:
                    hits.append("(weitere Treffer abgeschnitten, Suchmuster präzisieren)")
                    break
    _log(f"search_text {p.name} '{args['pattern']}': {len(hits)} Treffer")
    return _text("\n".join(hits) if hits else "Keine Treffer.")


@tool(
    "read_text",
    "Liest einen Ausschnitt (höchstens 150 Zeilen) aus einer Textdatei (Name im Referenzordner oder "
    "voller Pfad aus find_files), ab start_line. Auch für große CSV-Dateien geeignet.",
    {"filename": str, "start_line": int, "num_lines": int},
)
async def read_text(args: dict[str, Any]) -> dict[str, Any]:
    p = _ref_file(args["filename"])
    if not p:
        return _text("FEHLER: Datei nicht im Referenzordner.")
    if (err := _not_text(p)):
        return _text(err)
    start = max(1, int(args["start_line"]))
    n = min(MAX_READ_LINES, max(1, int(args["num_lines"])))
    with open(p, encoding="utf-8", errors="replace") as fh:
        chunk = [l.rstrip("\n") for l in itertools.islice(fh, start - 1, start - 1 + n)]
    _log(f"read_text {p.name} Zeilen {start}-{start + len(chunk) - 1}")
    return _text("\n".join(f"{start + k}: {l}" for k, l in enumerate(chunk)) or "Ende der Datei.")


# ---------------------------------------------------------------- Ergebnisse schreiben

RESERVED_NAMES = {"protokoll.md", "pruefung.md", "pruefung.json", "status.json", "review.json",
                  "uebertragung.md", "rueckgaengig.sql"}
# Kasten-Modus (26.11.2026): übernommene Dateien des alten Leitfaden-Laufs. Anhängen ja, ersetzen nein.
PROTECTED_NAMES: set[str] = set()


@tool(
    "write_output",
    "Schreibt ein Ergebnis (.md oder .sql) in den Lauf-Ordner. Mit append=true wird angehängt, "
    "sonst neu angelegt (bestehende Dateien werden nie überschrieben). Ergebnisse laufend schreiben, "
    "nicht erst am Ende: Bei Budget-Stopp bleibt nur erhalten, was geschrieben ist.",
    {"filename": str, "content": str, "append": bool},
)
async def write_output(args: dict[str, Any]) -> dict[str, Any]:
    if RUN_DIR is None:
        return _text("FEHLER: Kein Lauf-Ordner gesetzt.")
    name = Path(args["filename"]).name
    if Path(name).suffix.lower() not in {".md", ".sql"}:
        return _text("FEHLER: Nur .md oder .sql erlaubt.")
    if name.lower() in RESERVED_NAMES:
        return _text(f"FEHLER: {name} ist reserviert und wird automatisch erstellt.")
    target = RUN_DIR / name
    if args.get("append"):
        with open(target, "a", encoding="utf-8") as f:
            f.write(args["content"])
        _log(f"write_output angehängt: {name}")
        return _text(f"Angehängt an {target}")
    if target.exists():
        return _text(f"FEHLER: {name} existiert bereits. append=true verwenden oder neuen Namen wählen.")
    target.write_text(args["content"], encoding="utf-8")
    _log(f"write_output neu: {name}")
    return _text(f"Geschrieben: {target}")


@tool(
    "replace_output",
    "Ersetzt eine eigene Ergebnisdatei (.md oder .sql) im Lauf-Ordner komplett durch neuen Inhalt. "
    "Für Korrekturen nach self_check: lieber die Datei ersetzen als eine zweite Fassung anlegen.",
    {"filename": str, "content": str},
)
async def replace_output(args: dict[str, Any]) -> dict[str, Any]:
    if RUN_DIR is None:
        return _text("FEHLER: Kein Lauf-Ordner gesetzt.")
    name = Path(args["filename"]).name
    if Path(name).suffix.lower() not in {".md", ".sql"}:
        return _text("FEHLER: Nur .md oder .sql erlaubt.")
    if name.lower() in RESERVED_NAMES:
        return _text(f"FEHLER: {name} ist reserviert und wird automatisch erstellt.")
    if name.lower() in PROTECTED_NAMES:
        return _text(f"FEHLER: {name} ist aus dem alten Leitfaden-Lauf übernommen und wird nicht ersetzt. "
                     "Ergänzungen mit write_output(append=true) anhängen.")
    target = RUN_DIR / name
    if not target.exists():
        return _text(f"FEHLER: {name} gibt es noch nicht. Mit write_output anlegen.")
    target.write_text(args["content"], encoding="utf-8")
    _log(f"replace_output ersetzt: {name}")
    return _text(f"Ersetzt: {target}")


# ---------------------------------------------------------------- Server

ALL_TOOLS = [sql_query, find_files, download_file, pdf_to_text, table_to_text, search_text, read_text, write_output,
             replace_output]


def build_server(tools=None):
    return create_sdk_mcp_server(name="ci", version="0.2.0", tools=tools or [sql_query])


def tool_names(tools) -> list[str]:
    return [f"mcp__ci__{t.name}" for t in tools]


SQL_TOOL_NAME = "mcp__ci__sql_query"
