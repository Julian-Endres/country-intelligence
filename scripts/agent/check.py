"""
Auto-Prüfung eines Laufs (ohne KI). Läuft nach jedem Sekretär-Lauf automatisch,
lässt sich aber auch von Hand starten.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/check.py <lauf>

<lauf> = Ordnername in scripts/agent/output/ oder dessen eindeutiger Anfang,
z. B.  python3 scripts/agent/check.py 2026-11-09_1817
"""

import sys

from lib import checks, runs


def main(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    results = checks.run_check(run_dir)
    if not results:
        print(f"Keine .sql-Datei in {run_dir.name}, nichts zu prüfen.")
        return
    for r in results:
        c = r["anzahl"]
        print(f"\n{r['datei']}: ✅ {c['OK']} sauber · ⚠️ {c['ANSEHEN']} ansehen · ❌ {c['FEHLER']} fehlerhaft")
        for g in r["global"]:
            print(f"  ❌ Datei: {g}")
        for b in r["bloecke"]:
            if b["status"] != "OK":
                print(f"  {checks.ICON[b['status']]} {b['code']}: " + " | ".join(
                    n for n in b["notizen"] if not checks.is_quiet(n)))
    print(f"\nBericht: {run_dir / 'pruefung.md'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 scripts/agent/check.py <lauf>")
    main(sys.argv[1])
