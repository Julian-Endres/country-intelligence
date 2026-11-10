"""
Überblick über alle Läufe und was als Nächstes zu tun ist.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/status.py          offene Läufe (noch nicht übertragen/erledigt/verworfen)
  python3 scripts/agent/status.py --alle   alle Läufe
  python3 scripts/agent/status.py <lauf>   Verlauf eines Laufs
"""

import json
import sys

from lib import decisions, runs

DONE = {"übertragen", "erledigt", "verworfen"}
NEXT = {
    "neu": "check.py",
    "geprüft": "review.py",
    "freigegeben": "apply.py",
}


def counts(run_dir) -> str:
    p = run_dir / "pruefung.json"
    parts = []
    if p.exists():
        res = json.loads(p.read_text(encoding="utf-8"))
        c = {k: sum(r["anzahl"][k] for r in res) for k in ("OK", "ANSEHEN", "FEHLER")}
        parts.append(f"✅{c['OK']} ⚠️{c['ANSEHEN']} ❌{c['FEHLER']}")
    rv = decisions.load(run_dir)
    if rv:
        e = [d["entscheidung"] for d in rv["entscheidungen"]]
        parts.append(f"j{e.count(decisions.J)} n{e.count(decisions.N)} k{e.count(decisions.K)}")
    return "  ".join(parts)


def overview(show_all: bool) -> None:
    if not runs.OUTPUT_ROOT.exists():
        sys.exit("Noch keine Läufe.")
    rows = []
    for d in sorted(runs.OUTPUT_ROOT.iterdir()):
        if not d.is_dir():
            continue
        st = runs.read_status(d) or {}
        s = st.get("status", "?")
        if show_all or s not in DONE:
            rows.append((d.name, s, counts(d), NEXT.get(s, "")))
    if not rows:
        print("Keine offenen Läufe. (--alle zeigt alle)")
        return
    w = max(len(r[0]) for r in rows)
    print(f"{'Lauf':<{w}}  {'Status':<12} {'Zahlen':<26} Nächster Schritt")
    for name, s, c, nxt in rows:
        print(f"{name:<{w}}  {s:<12} {c:<26} {('python3 scripts/agent/' + nxt + ' ' + name[:15]) if nxt else ''}")


def detail(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    st = runs.read_status(run_dir) or {}
    print(f"Lauf:    {run_dir.name}\nAgent:   {st.get('agent')}   Thema: {st.get('thema')}")
    print(f"Status:  {st.get('status')}   {counts(run_dir)}")
    if st.get("auftrag"):
        print(f"Auftrag: {st['auftrag'][:200]}")
    print("Verlauf:")
    for v in st.get("verlauf", []):
        print(f"  {v['zeit']}  {v['status']:<12} {v.get('notiz', '')}")
    print("Dateien: " + ", ".join(sorted(p.name for p in run_dir.iterdir())))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        overview(False)
    elif args == ["--alle"]:
        overview(True)
    elif len(args) == 1:
        detail(args[0])
    else:
        sys.exit(__doc__)
