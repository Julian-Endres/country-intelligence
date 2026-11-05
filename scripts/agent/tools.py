"""
Gemeinsame Werkzeuge für alle Agenten (Sekretär, Quellen-Pfleger, Unterstützer).

Stufe 1: ein Werkzeug, sql_query. Läuft ausschließlich über den
Read-only-Zugang ci_agent_readonly (DB_AGENT_USER / DB_AGENT_PASSWORD in .env).
"""

import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from claude_agent_sdk import create_sdk_mcp_server, tool

load_dotenv()

MAX_ROWS = 50          # mehr Zeilen bekommt das Modell nie zu sehen
MAX_CELL_CHARS = 200   # lange Texte werden gekürzt
TIMEOUT_MS = 30_000    # Abfragen über 30 Sekunden werden abgebrochen

# Protokoll aller ausgeführten Abfragen dieses Laufs (für die Belegführung)
QUERY_LOG: list[dict[str, Any]] = []


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
    """Führt eine Abfrage aus und gibt das Ergebnis als Text-Tabelle zurück."""
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
            conn.rollback()  # nichts wird je gespeichert
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
    text = run_query(args["sql"])
    return {"content": [{"type": "text", "text": text}]}


def build_server():
    return create_sdk_mcp_server(name="ci", version="0.1.0", tools=[sql_query])


# Name, unter dem das Modell das Werkzeug sieht: mcp__<server>__<tool>
SQL_TOOL_NAME = "mcp__ci__sql_query"
