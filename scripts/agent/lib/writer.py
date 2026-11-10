"""
Schreib-Verbindung, ausschließlich für apply.py.

Die Agenten importieren dieses Modul nie: Sie arbeiten nur mit tools.py
(ci_agent_readonly). apply.py startet Julian selbst, nach seiner Prüfung.
Anmeldung mit DB_USER / DB_PASSWORD aus .env (Julians eigener Zugang).
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect_write():
    user = os.getenv("DB_USER")
    if not user:
        raise SystemExit("DB_USER fehlt in .env")
    if user == os.getenv("DB_AGENT_USER", "ci_agent_readonly"):
        raise SystemExit("apply.py braucht Julians Zugang (DB_USER), nicht den Agenten-Zugang")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=user,
        password=os.getenv("DB_PASSWORD"),
        options="-c statement_timeout=60000",
    )
    conn.autocommit = False
    return conn
