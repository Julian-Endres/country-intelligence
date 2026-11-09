"""
Zerlegt eine Vorschlags-SQL-Datei in Blöcke (Kommentarzeilen + Statement).

Beachtet einfache Anführungszeichen ('' als Escape), damit ein Semikolon
oder '--' innerhalb einer Beschreibung kein Statement-Ende ist.
"""

import re
from dataclasses import dataclass, field


@dataclass
class Statement:
    sql: str
    line: int                                       # Startzeile in der Datei
    comments: list[str] = field(default_factory=list)  # Kommentare direkt davor


def split_statements(text: str) -> tuple[list[Statement], list[str]]:
    """Gibt Statements (mit vorangehenden Kommentaren) und Kommentare am Dateiende zurück."""
    statements: list[Statement] = []
    pending: list[str] = []
    buf: list[str] = []
    start_line = None
    i, line, n = 0, 1, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            buf.append(c)
            if c == "'":
                if i + 1 < n and text[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_str = False
        elif c == "-" and text.startswith("--", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            comment = text[i + 2:j].strip()
            if not "".join(buf).strip():
                pending.append(comment)
            i = j
            continue
        elif c == "'":
            in_str = True
            buf.append(c)
        elif c == ";":
            sql = "".join(buf).strip()
            if sql:
                statements.append(Statement(sql=sql, line=start_line or line, comments=pending))
            pending, buf, start_line = [], [], None
        else:
            if not c.isspace() and start_line is None:
                start_line = line
            buf.append(c)
        if c == "\n":
            line += 1
        i += 1
    rest = "".join(buf).strip()
    if rest:
        statements.append(Statement(sql=rest, line=start_line or line, comments=pending))
        pending = []
    return statements, pending


STRING_ASSIGN = re.compile(r"(\w+)\s*=\s*'((?:[^']|'')*)'", re.DOTALL)


def find_keyword_outside_strings(sql: str, keyword: str) -> int:
    """Position des letzten Vorkommens von keyword außerhalb von Strings, sonst -1."""
    pos, in_str, i = -1, False, 0
    up = sql.upper()
    k = keyword.upper()
    while i < len(sql):
        if sql[i] == "'":
            if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        elif not in_str and up.startswith(k, i):
            before = sql[i - 1] if i > 0 else " "
            after = sql[i + len(k)] if i + len(k) < len(sql) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                pos = i
        i += 1
    return pos


def parse_update(sql: str) -> dict | None:
    """Zerlegt 'UPDATE indicator_metadata SET ... WHERE ...'. None, wenn das Muster nicht passt."""
    m = re.match(r"\s*UPDATE\s+indicator_metadata\s+SET\s", sql, re.IGNORECASE)
    if not m:
        return None
    w = find_keyword_outside_strings(sql, "WHERE")
    if w == -1:
        return None
    set_part, where_part = sql[m.end():w], sql[w + len("WHERE"):]
    values = {k.lower(): v.replace("''", "'") for k, v in STRING_ASSIGN.findall(set_part)}
    # alle zugewiesenen Spalten, auch ohne Text-Wert (z. B. source_id = 2)
    without_strings = re.sub(r"'(?:[^']|'')*'", "''", set_part)
    columns = [c.lower() for c in re.findall(r"(\w+)\s*=", without_strings)]
    return {"set": values, "columns": columns, "where": where_part.strip()}
