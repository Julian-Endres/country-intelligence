"""
WB-Beschreibungen aus der Weltbank-API holen -> SQL-Datei zur Prüfung.

Baustein 1 des Hygiene-Agenten (ohne KI, deterministisch).

Was das Skript tut:
  1. Liest über den Read-only-Zugang (ci_agent_readonly) alle WB-Indikatoren
     ohne description.
  2. Holt pro Indikator die offizielle Beschreibung (sourceNote) aus der
     Weltbank-API.
  3. Schreibt eine SQL-Datei mit UPDATE-Statements. Ausgeführt wird NICHTS.
     Die Datei prüft und führt Julian selbst aus.

Voraussetzung in .env (Repo-Wurzel):
  DB_AGENT_USER=ci_agent_readonly
  DB_AGENT_PASSWORD=...

Aufruf aus der Repo-Wurzel:
  python3 scripts/agent/wb_descriptions.py
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.worldbank.org/v2/indicator/{code}?format=json"
PREFIX = "WB:"
OUTPUT_DIR = Path(__file__).parent / "output"


def get_readonly_connection():
    user = os.getenv("DB_AGENT_USER")
    password = os.getenv("DB_AGENT_PASSWORD")
    if not user or not password:
        sys.exit("DB_AGENT_USER / DB_AGENT_PASSWORD fehlen in .env")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=user,
        password=password,
    )


def fetch_missing_indicators(conn):
    query = """
        SELECT m.indicator_code, m.name
        FROM indicator_metadata m
        JOIN sources s ON s.id = m.source_id
        WHERE s.short_code = 'WB'
          AND (m.description IS NULL OR TRIM(m.description) = '')
        ORDER BY m.indicator_code;
    """
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def fetch_wb_description(api_code):
    """Gibt (sourceNote, api_name, fehlergrund) zurück."""
    url = API_URL.format(code=api_code)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return None, None, f"API-Fehler: {e}"

    # Erwartete Form (geprüft am 05.11.2026): [ {page-Infos}, [ {indikator} ] ]
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return None, None, f"Unerwartete Antwort: {str(data)[:200]}"

    item = data[1][0]
    note = (item.get("sourceNote") or "").strip()
    api_name = (item.get("name") or "").strip()
    if not note:
        return None, api_name, "sourceNote leer"
    return note, api_name, None


def sql_literal(text):
    return "'" + text.replace("'", "''") + "'"


def comment_safe(text):
    return " ".join(text.split())


def main():
    conn = get_readonly_connection()
    rows = fetch_missing_indicators(conn)
    conn.close()
    print(f"{len(rows)} WB-Indikatoren ohne description gefunden.")

    found, missing = [], []
    for db_code, db_name in rows:
        api_code = db_code[len(PREFIX):] if db_code.startswith(PREFIX) else db_code
        note, api_name, error = fetch_wb_description(api_code)
        if error:
            missing.append((db_code, db_name, error))
            print(f"  ✗ {db_code}: {error}")
        else:
            found.append((db_code, db_name, api_name, note, API_URL.format(code=api_code)))
            print(f"  ✓ {db_code}")
        time.sleep(0.3)  # API schonen

    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_file = OUTPUT_DIR / f"wb_descriptions_{stamp}.sql"

    lines = [
        f"-- WB-Beschreibungen aus der Weltbank-API (sourceNote)",
        f"-- Erzeugt: {datetime.now():%Y-%m-%d %H:%M} von scripts/agent/wb_descriptions.py",
        f"-- Gefunden: {len(found)} | Ohne Beschreibung: {len(missing)} | Gesamt: {len(rows)}",
        f"-- Jedes UPDATE greift nur, wenn description noch leer ist (überschreibt nichts).",
        f"-- Ablauf: Datei ausführen -> Ausgaben prüfen (je 'UPDATE 1') -> dann selbst COMMIT; oder ROLLBACK;",
        "",
        "BEGIN;",
        "",
    ]

    for db_code, db_name, api_name, note, url in found:
        lines.append(f"-- {db_code} | DB-Name: {comment_safe(db_name)}")
        if api_name and api_name != db_name:
            lines.append(f"-- ACHTUNG Name weicht ab. API-Name: {comment_safe(api_name)}")
        lines.append(f"-- Quelle: {url}")
        lines.append(
            f"UPDATE indicator_metadata SET description = {sql_literal(note)}\n"
            f"WHERE indicator_code = {sql_literal(db_code)}\n"
            f"  AND (description IS NULL OR TRIM(description) = '');"
        )
        lines.append("")

    lines.append("-- COMMIT;   <- erst nach Prüfung selbst ausführen")
    lines.append("")

    if missing:
        lines.append("-- ===== MANUELL KLÄREN (keine Beschreibung aus der API) =====")
        for db_code, db_name, error in missing:
            lines.append(f"-- {db_code} | {comment_safe(db_name)} | {comment_safe(error)}")

    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nGefunden: {len(found)}, manuell klären: {len(missing)}")
    print(f"SQL-Datei: {out_file}")


if __name__ == "__main__":
    main()
