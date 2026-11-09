"""
Gemeinsame Werkzeuge für alle Agenten (Sekretär, Quellen-Pfleger, Unterstützer).

Grundsatz: Kein Werkzeug kann die Datenbank ändern. Schreiben ist nur in zwei
Ordnern möglich:
  - den Lauf-Ordner des aktuellen Laufs (scripts/agent/output/<lauf>/)
  - data/raw/reference/     Referenzmaterial (Codebooks usw.), von Git ignoriert
"""

import os
import re
import shutil
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
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "country-intelligence-agent"}) as r:
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
            tmp.rename(target)
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


def _ref_file(name: str) -> Path | None:
    p = REF_DIR / Path(name).name
    return p if p.exists() else None


@tool(
    "search_text",
    "Durchsucht eine Textdatei im Referenzordner nach einem Begriff oder regulären Ausdruck "
    "(ohne Groß-/Kleinschreibung). Gibt bis zu 25 Treffer mit Zeilennummer, Seite und etwas Kontext zurück.",
    {"filename": str, "pattern": str},
)
async def search_text(args: dict[str, Any]) -> dict[str, Any]:
    p = _ref_file(args["filename"])
    if not p:
        return _text("FEHLER: Datei nicht im Referenzordner. Erst pdf_to_text ausführen.")
    try:
        rx = re.compile(args["pattern"], re.IGNORECASE)
    except re.error as e:
        return _text(f"FEHLER im Suchmuster: {e}")
    lines = p.read_text(encoding="utf-8").splitlines()
    page, hits = 0, []
    for i, line in enumerate(lines, start=1):
        m = re.match(r"=== Seite (\d+) ===", line)
        if m:
            page = int(m.group(1))
            continue
        if rx.search(line):
            ctx = " ⏎ ".join(l.strip() for l in lines[i - 1:i + 2] if l.strip())
            hits.append(f"Zeile {i} (S. {page}): {ctx[:300]}")
            if len(hits) >= MAX_SEARCH_HITS:
                hits.append("(weitere Treffer abgeschnitten, Suchmuster präzisieren)")
                break
    _log(f"search_text {p.name} '{args['pattern']}': {len(hits)} Treffer")
    return _text("\n".join(hits) if hits else "Keine Treffer.")


@tool(
    "read_text",
    "Liest einen Ausschnitt (höchstens 150 Zeilen) aus einer Textdatei im Referenzordner, ab start_line.",
    {"filename": str, "start_line": int, "num_lines": int},
)
async def read_text(args: dict[str, Any]) -> dict[str, Any]:
    p = _ref_file(args["filename"])
    if not p:
        return _text("FEHLER: Datei nicht im Referenzordner.")
    start = max(1, int(args["start_line"]))
    n = min(MAX_READ_LINES, max(1, int(args["num_lines"])))
    lines = p.read_text(encoding="utf-8").splitlines()
    chunk = lines[start - 1:start - 1 + n]
    _log(f"read_text {p.name} Zeilen {start}-{start + len(chunk) - 1}")
    return _text("\n".join(f"{start + k}: {l}" for k, l in enumerate(chunk)) or "Ende der Datei.")


# ---------------------------------------------------------------- Ergebnisse schreiben

RESERVED_NAMES = {"protokoll.md", "pruefung.md", "status.json"}


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


# ---------------------------------------------------------------- Server

ALL_TOOLS = [sql_query, find_files, download_file, pdf_to_text, search_text, read_text, write_output]


def build_server(tools=None):
    return create_sdk_mcp_server(name="ci", version="0.2.0", tools=tools or [sql_query])


def tool_names(tools) -> list[str]:
    return [f"mcp__ci__{t.name}" for t in tools]


SQL_TOOL_NAME = "mcp__ci__sql_query"
