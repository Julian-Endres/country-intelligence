"""
Einmalig: sortiert die alten, losen Dateien in scripts/agent/output/ in Lauf-Ordner ein.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/helpers/migrate_output.py              zeigt nur den Plan
  python3 scripts/agent/helpers/migrate_output.py --ausfuehren  verschiebt wirklich

Erkannte Muster:
  ask_JJJJMMTT_HHMMSS.md                 -> <datum>_ask_frage/protokoll.md               (erledigt)
  secretary_log_JJJJMMTT_HHMMSS.md       -> <datum>_sekretaer_<thema>/protokoll.md        (neu)
  <thema>_metadata|explainer|befunde_JJJJMMTT.* -> in den Sekretär-Lauf desselben Tages
  wb_descriptions_JJJJMMTT_HHMM.sql      -> <datum>_wb_beschreibungen/metadata.sql        (übertragen)
Alles andere bleibt liegen und wird gemeldet.
"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import runs  # noqa: E402

ROOT = runs.OUTPUT_ROOT


def plan() -> tuple[list[tuple], list[Path]]:
    files = sorted(p for p in ROOT.iterdir() if p.is_file()) if ROOT.exists() else []
    jobs, used = [], set()
    sec_by_day: dict[str, list] = {}

    for p in files:
        if m := re.fullmatch(r"ask_(\d{8})_(\d{6})\.md", p.name):
            when = datetime.strptime(m[1] + m[2], "%Y%m%d%H%M%S")
            jobs.append(("ask", "frage", when, "erledigt", "Frage an die Datenbank", [(p, "protokoll.md")]))
            used.add(p)
        elif m := re.fullmatch(r"wb_descriptions_(\d{8})_(\d{4})\.sql", p.name):
            when = datetime.strptime(m[1] + m[2], "%Y%m%d%H%M")
            jobs.append(("wb", "beschreibungen", when, "übertragen",
                         "WB-Beschreibungen aus der API; am 05.11.2026 per psql ausgeführt (56 x UPDATE 1, COMMIT)",
                         [(p, "metadata.sql")]))
            used.add(p)
        elif m := re.fullmatch(r"secretary_log_(\d{8})_(\d{6})\.md", p.name):
            when = datetime.strptime(m[1] + m[2], "%Y%m%d%H%M%S")
            sec_by_day.setdefault(m[1], []).append((when, p))

    for day, logs in sec_by_day.items():
        extras = [p for p in files if (m := re.fullmatch(rf"(\w+?)_(metadata|explainer|befunde)_{day}\.(sql|md)", p.name))]
        if len(logs) == 1:
            when, log = logs[0]
            thema = next((re.match(r"(\w+?)_(metadata|explainer|befunde)_", p.name)[1] for p in extras), "auftrag")
            moves = [(log, "protokoll.md")]
            for p in extras:
                kind = re.match(r"\w+?_(metadata|explainer|befunde)_", p.name)[1]
                moves.append((p, f"{kind}{p.suffix}"))
                used.add(p)
            jobs.append(("sekretaer", thema, when, "neu", "aus alten Dateien einsortiert", moves))
            used.add(log)
        else:
            for when, log in logs:
                jobs.append(("sekretaer", "auftrag", when, "neu", "aus alten Dateien einsortiert", [(log, "protokoll.md")]))
                used.add(log)

    rest = [p for p in files if p not in used]
    return sorted(jobs, key=lambda j: j[2]), rest


def main(execute: bool) -> None:
    jobs, rest = plan()
    if not jobs:
        print("Nichts einzusortieren.")
    for agent, thema, when, status, note, moves in jobs:
        name = f"{when:%Y-%m-%d_%H%M}_{runs.slug(agent)}_{runs.slug(thema)}"
        print(f"\n{name}/   (Status: {status})")
        for src, dst in moves:
            print(f"    {src.name}  ->  {dst}")
        if execute:
            run_dir = runs.new_run(agent, thema, auftrag=note, when=when, status=status)
            for src, dst in moves:
                shutil.move(str(src), str(run_dir / dst))
    if rest:
        print("\nBleibt liegen (unbekanntes Muster, bitte selbst entscheiden):")
        for p in rest:
            print(f"    {p.name}")
    if not execute and jobs:
        print("\nDas war nur der Plan. Zum Ausführen:  python3 scripts/agent/helpers/migrate_output.py --ausfuehren")


if __name__ == "__main__":
    main("--ausfuehren" in sys.argv)
