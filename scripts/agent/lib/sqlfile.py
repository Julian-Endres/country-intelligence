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


def find_keyword_outside_strings(sql: str, keyword: str) -> int:
    """Position des letzten Vorkommens von keyword außerhalb von Strings, sonst -1."""
    # Kein sql.upper() auf den ganzen Text: "ß".upper() ist "SS" und verschiebt alle Positionen.
    pos, in_str, i = -1, False, 0
    k = keyword.upper()
    while i < len(sql):
        if sql[i] == "'":
            if in_str and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_str = not in_str
        elif not in_str and sql[i:i + len(k)].upper() == k:
            before = sql[i - 1] if i > 0 else " "
            after = sql[i + len(k)] if i + len(k) < len(sql) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                pos = i
        i += 1
    return pos


def _split_top(text: str, sep: str = ",") -> list[str]:
    """Trennt an sep, aber nicht in Strings oder eckigen Klammern."""
    parts, buf, depth, in_str, i = [], [], 0, False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            buf.append(c)
            if c == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_str = False
        elif c == "'":
            in_str = True
            buf.append(c)
        elif c == "[":
            depth += 1
            buf.append(c)
        elif c == "]":
            depth -= 1
            buf.append(c)
        elif c == sep and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


class ValueError_(Exception):
    pass


def parse_value(raw: str):
    """'Text' -> str, Zahl -> float, NULL -> None, ARRAY['a','b'] -> list[str]. Sonst ValueError_."""
    raw = raw.strip()
    if re.fullmatch(r"'(?:[^']|'')*'", raw, re.DOTALL):
        return raw[1:-1].replace("''", "'")
    if raw.upper() == "NULL":
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        return float(raw)
    m = re.fullmatch(r"ARRAY\s*\[(.*)\]", raw, re.IGNORECASE | re.DOTALL)
    if m:
        items = _split_top(m.group(1))
        out = []
        for it in items:
            v = parse_value(it)
            if not isinstance(v, str):
                raise ValueError_(f"Listenelement ist kein Text: {it[:40]}")
            out.append(v)
        if not out:
            raise ValueError_("Leere Liste, bitte NULL verwenden")
        return out
    raise ValueError_(f"Unbekannter Wert: {raw[:60]}")


def parse_update(sql: str) -> dict | None:
    """Zerlegt 'UPDATE indicator_metadata SET ... WHERE ...'. None, wenn das Muster nicht passt.

    Rückgabe: set (Spalte -> Wert: str, float, None oder list[str]), columns (Reihenfolge),
    errors (nicht lesbare Zuweisungen), where.
    """
    m = re.match(r"\s*UPDATE\s+indicator_metadata\s+SET\s", sql, re.IGNORECASE)
    if not m:
        return None
    w = find_keyword_outside_strings(sql, "WHERE")
    if w == -1:
        return None
    set_part, where_part = sql[m.end():w], sql[w + len("WHERE"):]
    values, columns, errors = {}, [], []
    for assign in _split_top(set_part):
        am = re.match(r"(\w+)\s*=\s*(.*)$", assign, re.DOTALL)
        if not am:
            errors.append(f"Keine Zuweisung: {assign[:60]}")
            continue
        col = am.group(1).lower()
        if col in columns:
            errors.append(f"Spalte doppelt: {col}")
        columns.append(col)
        try:
            values[col] = parse_value(am.group(2))
        except ValueError_ as e:
            errors.append(f"{col}: {e}")
    return {"set": values, "columns": columns, "errors": errors, "where": where_part.strip()}
