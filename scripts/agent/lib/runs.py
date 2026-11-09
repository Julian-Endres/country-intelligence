"""
Lauf-Ordner und Status.

Jeder Lauf bekommt einen eigenen Ordner in scripts/agent/output/:
  JJJJ-MM-TT_HHMM_<agent>_<thema>/
    status.json     Status und Verlauf
    protokoll.md    Auftrag, Zusammenfassung, Aktionen, Abfragen
    ...             Ergebnisse (metadata.sql, explainer.md, befunde.md, pruefung.md)

Status-Ablauf:
  neu -> geprüft -> freigegeben -> übertragen
  (ask-Läufe: direkt erledigt; jederzeit möglich: verworfen)
"""

import json
import re
from datetime import datetime
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = AGENT_DIR / "output"

STATUSES = ["neu", "geprüft", "freigegeben", "übertragen", "erledigt", "verworfen"]


def slug(text: str) -> str:
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:40] or "lauf"


def new_run(agent: str, thema: str, auftrag: str = "", when: datetime | None = None, status: str = "neu") -> Path:
    when = when or datetime.now()
    base = f"{when:%Y-%m-%d_%H%M}_{slug(agent)}_{slug(thema)}"
    run_dir, i = OUTPUT_ROOT / base, 2
    while run_dir.exists():
        run_dir, i = OUTPUT_ROOT / f"{base}_{i}", i + 1
    run_dir.mkdir(parents=True)
    write_status(run_dir, {
        "agent": agent,
        "thema": thema,
        "auftrag": auftrag,
        "erstellt": when.isoformat(timespec="seconds"),
        "status": status,
        "verlauf": [{"zeit": when.isoformat(timespec="seconds"), "status": status, "notiz": "angelegt"}],
    })
    return run_dir


def read_status(run_dir: Path) -> dict | None:
    p = run_dir / "status.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def write_status(run_dir: Path, data: dict) -> None:
    (run_dir / "status.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_status(run_dir: Path, status: str, notiz: str = "") -> None:
    if status not in STATUSES:
        raise ValueError(f"Unbekannter Status: {status}")
    data = read_status(run_dir) or {"verlauf": []}
    data["status"] = status
    data.setdefault("verlauf", []).append(
        {"zeit": datetime.now().isoformat(timespec="seconds"), "status": status, "notiz": notiz})
    write_status(run_dir, data)


def resolve_run(arg: str) -> Path:
    """Akzeptiert vollen Pfad, Ordnernamen oder eindeutigen Anfang des Ordnernamens."""
    p = Path(arg).expanduser()
    if p.is_dir():
        return p.resolve()
    if (OUTPUT_ROOT / arg).is_dir():
        return OUTPUT_ROOT / arg
    matches = sorted(d for d in OUTPUT_ROOT.iterdir() if d.is_dir() and d.name.startswith(arg)) if OUTPUT_ROOT.exists() else []
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit(f"Kein Lauf-Ordner gefunden für: {arg}")
    raise SystemExit("Mehrdeutig, bitte genauer:\n  " + "\n  ".join(m.name for m in matches))
