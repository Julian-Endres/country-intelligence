"""
Werkzeug self_check: Der Sekretär prüft seine eigene Vorschlagsdatei mit der Auto-Prüfung,
bevor er fertig meldet. Eigenes Modul, weil checks.py selbst tools.py importiert.
"""

from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from . import checks, tools


@tool(
    "self_check",
    "Prüft eine eigene Vorschlagsdatei (.sql im Lauf-Ordner) mit derselben Auto-Prüfung, die Julian sieht. "
    "Gibt alle Fehler und Hinweise je Indikator zurück. Vor dem Abschluss immer ausführen und Fehler beheben.",
    {"filename": str},
)
async def self_check(args: dict[str, Any]) -> dict[str, Any]:
    if tools.RUN_DIR is None:
        return tools._text("FEHLER: Kein Lauf-Ordner gesetzt.")
    path = tools.RUN_DIR / Path(args["filename"]).name
    if path.suffix.lower() != ".sql" or not path.exists():
        return tools._text("FEHLER: .sql-Datei im Lauf-Ordner angeben.")
    try:
        r = checks.check_sql_file(path)
    except Exception as e:  # z. B. DB nicht erreichbar
        return tools._text(f"FEHLER bei der Prüfung: {e}")
    c = r["anzahl"]
    lines = [f"{path.name}: {c[checks.OK]} OK, {c[checks.WARN]} ansehen, {c[checks.FAIL]} Fehler"]
    lines += [f"DATEI: {g}" for g in r["global"]]
    for b in r["bloecke"]:
        notes = [n for n in b["notizen"] if not checks.is_quiet(n) and not n.startswith("Ersetzt vorhandene")]
        if b["status"] != checks.OK or notes:
            lines.append(f"{b['status']} {b['code']}: " + " | ".join(notes))
    tools._log(f"self_check {path.name}: {c[checks.OK]}/{c[checks.WARN]}/{c[checks.FAIL]}")
    return tools._text("\n".join(lines))
