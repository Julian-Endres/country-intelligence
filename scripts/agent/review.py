"""
Julians Prüfung eines Laufs (Schritt 3 von 4: Lauf → Auto-Prüfung → Prüfung → Übertragung).

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/review.py <lauf>

Ablauf:
  1. Die Auto-Prüfung läuft noch einmal frisch (die DB könnte sich geändert haben).
  2. ❌ fehlerhafte Vorschläge werden automatisch verworfen.
  3. Du siehst alle ⚠️-Vorschläge (darunter alle mit Sicherheit MITTEL/UNSICHER)
     und 3 zufällige ✅ als Stichprobe. Die übrigen ✅ werden übernommen.
     Lehnst du eine Stichprobe ab, zeigt das Skript alle übrigen ✅ an.
  4. Tasten:  j = übernehmen   n = verwerfen   k = bekannte Auffälligkeit
              (verwerfen und in known_issues festhalten)   a = abbrechen, nichts speichern
  5. Am Ende siehst du die Zusammenfassung und bestätigst das Speichern.
     Ergebnis: review.json im Lauf-Ordner, Status „freigegeben“.
     Die Datenbank ändert sich hier noch nicht, das macht erst apply.py.
"""

import random
import sys
import textwrap

from lib import checks, decisions, runs
from lib.decisions import J, K, N

SAMPLE_SIZE = 3
WIDTH = 92
ALLOWED_START = {"neu", "geprüft", "freigegeben"}


def wrap(label: str, text: str) -> str:
    pad = " " * (len(label) + 2)
    return textwrap.fill(text, WIDTH, initial_indent=f"{label}: ", subsequent_indent=pad)


def show(b: dict, nr: int, total: int, why: str) -> None:
    s = b["set"]
    print("\n" + "─" * WIDTH)
    print(f"[{nr}/{total}]  {checks.ICON[b['status']]}  {b['code']}   ({why})")
    print("─" * WIDTH)
    for col in checks.ALLOWED_COLUMNS:
        if col in s:
            print(wrap(col.capitalize(), s[col]))
    w = b.get("werte")
    if w and w.get("n"):
        print(f"Werte in der DB: {w['min']:g} bis {w['max']:g}, {w['distinct']} verschiedene, {w['n']} Zeilen")
    be = b.get("beleg") or {}
    if be.get("zitat"):
        print(wrap("Beleg", f"{be['datei']}, S. {be['seite']}: „{be['zitat']}“"))
    elif be.get("quelle"):
        print(f"Beleg: {be['quelle']}")
    if b.get("sicherheit"):
        print(f"Sicherheit (laut Agent): {b['sicherheit']}")
    hints = [n for n in b["notizen"] if not n.startswith(("Zitat gefunden", "Einheit passt", "Einheit wird nicht"))]
    for n in hints:
        print(wrap("  Auto-Prüfung", n))


def ask(prompt: str, allowed: str) -> str:
    while True:
        try:
            a = input(prompt).strip().lower()
        except EOFError:
            a = "a"
        if a and a[0] in allowed:
            return a[0]
        print(f"  Bitte eine dieser Tasten: {' / '.join(allowed)}")


def main(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    st = runs.read_status(run_dir) or {}
    if st.get("status") not in ALLOWED_START:
        sys.exit(f"Lauf hat Status „{st.get('status')}“. Prüfen geht nur bei: {', '.join(sorted(ALLOWED_START))}.")
    if st.get("status") == "freigegeben":
        print("Hinweis: Lauf war schon freigegeben. Eine neue Prüfung ersetzt die alte.")

    print(f"Lauf: {run_dir.name}\nAuto-Prüfung läuft frisch …")
    results = checks.run_check(run_dir)
    if not results:
        sys.exit("Keine .sql-Datei im Lauf-Ordner, nichts zu prüfen.")

    decided, queue = [], []
    rng = random.SystemRandom()
    for r in results:
        sql_path = run_dir / r["datei"]
        for g in r["global"]:
            print(f"⚠️  {r['datei']}: {g}  (apply.py führt die Datei nicht aus, sondern nur geprüfte Vorschläge)")
        oks = [b for b in r["bloecke"] if b["status"] == checks.OK]
        sample = {id(b) for b in rng.sample(oks, min(SAMPLE_SIZE, len(oks)))}
        for b in r["bloecke"]:
            entry = {"datei": r["datei"], "datei_hash": decisions.file_hash(sql_path),
                     "code": b["code"], "sha": decisions.fingerprint(b["sql"]),
                     "auto": b["status"], "set": b["set"], "notiz": ""}
            if b["status"] == checks.FAIL:
                decided.append({**entry, "entscheidung": N, "grund": "automatisch (❌ Auto-Prüfung)",
                                "notiz": " | ".join(b["notizen"])})
            elif b["status"] == checks.WARN:
                queue.append((b, entry, "⚠️ ansehen"))
            elif id(b) in sample:
                queue.append((b, entry, "Stichprobe"))
            else:
                decided.append({**entry, "entscheidung": J, "grund": "automatisch (✅, keine Stichprobe)",
                                "_block": b})

    n_fail = sum(1 for d in decided if d["entscheidung"] == N)
    n_ok = sum(1 for d in decided if d["entscheidung"] == J)
    print(f"\n{len(queue)} zum Ansehen · {n_ok} ✅ ohne Stichprobe · {n_fail} ❌ automatisch verworfen")
    print("Tasten: j = übernehmen · n = verwerfen · k = bekannte Auffälligkeit · a = abbrechen")

    i, expanded = 0, False
    while i < len(queue):
        b, entry, why = queue[i]
        show(b, i + 1, len(queue), why)
        a = ask("Entscheidung [j/n/k/a]: ", "jnka")
        if a == "a":
            sys.exit("Abgebrochen. Nichts gespeichert.")
        if a == "j":
            decided.append({**entry, "entscheidung": J, "grund": f"angesehen ({why})"})
        else:
            note = ""
            while not note:
                try:
                    note = input("  Kurz der Grund (Pflicht): ").strip()
                except EOFError:
                    sys.exit("Abgebrochen. Nichts gespeichert.")
            decided.append({**entry, "entscheidung": N if a == "n" else K,
                            "grund": f"angesehen ({why})", "notiz": note})
            if why == "Stichprobe" and not expanded:
                expanded = True
                rest = [d for d in decided if d.get("_block") is not None]
                for d in rest:
                    decided.remove(d)
                    blk = d.pop("_block")
                    queue.append((blk, {k: v for k, v in d.items() if k not in ("entscheidung", "grund")},
                                  "nach abgelehnter Stichprobe"))
                if rest:
                    print(f"\n  Stichprobe abgelehnt. Du siehst jetzt auch die übrigen {len(rest)} ✅-Vorschläge.")
        i += 1

    for d in decided:
        d.pop("_block", None)
    count = {x: sum(1 for d in decided if d["entscheidung"] == x) for x in (J, N, K)}
    print("\n" + "═" * WIDTH)
    print(f"Ergebnis: {count[J]} übernehmen · {count[N]} verwerfen · {count[K]} bekannte Auffälligkeit")
    for d in decided:
        if d["entscheidung"] != J:
            print(f"  {d['entscheidung']:<11} {d['code']}: {d['notiz'][:70]}")
    if ask("Speichern? [j/n]: ", "jn") != "j":
        sys.exit("Nichts gespeichert.")

    decisions.save(run_dir, {"lauf": run_dir.name, "pruefer": "julian", "entscheidungen": decided})
    if count[J] or count[K]:
        runs.set_status(run_dir, "freigegeben",
                        f"Prüfung: {count[J]} übernehmen, {count[N]} verwerfen, {count[K]} bekannt")
        print(f"Gespeichert, Status „freigegeben“. Nächster Schritt:\n  python3 scripts/agent/apply.py {run_dir.name}")
    else:
        runs.set_status(run_dir, "verworfen", "Prüfung: alles verworfen")
        print("Gespeichert. Nichts übernommen, Status „verworfen“.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 scripts/agent/review.py <lauf>")
    main(sys.argv[1])
