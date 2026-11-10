"""
Vorschläge und Julians Entscheidungen (review.json) eines Lauf-Ordners.

Jeder Vorschlag wird über einen Fingerabdruck (sha256 des SQL-Texts) erkannt.
Ändert sich ein Vorschlag nach der Prüfung, passt der Fingerabdruck nicht mehr
und apply.py bricht ab. So wird nur übertragen, was Julian gesehen hat.
"""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from . import sqlfile

REVIEW_FILE = "review.json"

CODE_LINE = re.compile(r"^([A-Za-z0-9_]+:\S+)\s*$")   # wie in checks.py

J, N, K = "übernehmen", "verwerfen", "bekannt"     # Tasten j / n / k


def fingerprint(sql: str) -> str:
    return hashlib.sha256(" ".join(sql.split()).encode("utf-8")).hexdigest()[:16]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def parse_proposals(path: Path) -> list[dict]:
    """Alle UPDATE-Vorschläge einer SQL-Datei: code, set (Spalte → Text), Fingerabdruck."""
    statements, _ = sqlfile.split_statements(path.read_text(encoding="utf-8"))
    out = []
    for st in statements:
        upd = sqlfile.parse_update(st.sql)
        if not upd:
            continue
        code = next((m.group(1) for c in st.comments if (m := CODE_LINE.match(c))), None)
        out.append({"code": code, "set": upd["set"], "columns": upd["columns"], "errors": upd["errors"],
                    "where": upd["where"], "sha": fingerprint(st.sql), "zeile": st.line})
    return out


def load(run_dir: Path) -> dict | None:
    p = run_dir / REVIEW_FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(run_dir: Path, data: dict) -> None:
    data["gespeichert"] = datetime.now().isoformat(timespec="seconds")
    (run_dir / REVIEW_FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
