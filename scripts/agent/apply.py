"""
Übertragung eines freigegebenen Laufs in die Datenbank (Schritt 4 von 4).
Das einzige Skript, das schreibt. Startet nur Julian, nie ein Agent.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/apply.py <lauf>

Sicherungen:
  - nur Status „freigegeben“ und nur Vorschläge, die in review.json auf „übernehmen“ stehen
  - Fingerabdruck: Wurde die SQL-Datei nach der Prüfung geändert, bricht das Skript ab
  - Die SQL-Datei des Agenten wird NIE ausgeführt. apply.py baut jedes UPDATE selbst
    (mit Parametern), nur für erlaubte Spalten
  - Ersetzen nur, was du gesehen hast: Steht in der DB nicht mehr genau der alte Wert aus der
    Prüfung, bricht das Skript ab
  - vorher: Backup der ganzen Tabelle indicator_metadata nach backups/agent/ (die letzten 5 bleiben)
    und rueckgaengig.sql im Lauf-Ordner (alte Werte der betroffenen Zeilen)
  - eine Transaktion: Jedes UPDATE muss genau 1 Zeile ändern, sonst wird alles zurückgerollt
  - Kontrolle vor und nach dem COMMIT: Steht in der DB genau der freigegebene Text?
  - setzt metadata_reviewed_at; „k“ wird übernommen wie „j“ und landet zusätzlich in known_issues
    (vorher Existenzprüfung)
"""

import sys
from datetime import datetime
from pathlib import Path

from psycopg2 import sql as psql

from lib import checks, decisions, runs
from lib.decisions import J, K
from lib.writer import connect_write

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = REPO_ROOT / "backups" / "agent"
KEEP_BACKUPS = 5
UNDO_COLS = checks.ALLOWED_COLUMNS + ("metadata_reviewed_at",)


def same(a, b) -> bool:
    """Vergleich mit Toleranz für Zahlen; leer, '' und [] gelten als gleich."""
    if a in (None, "", []) and b in (None, "", []):
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) < 1e-9
    return a == b


class Abbruch(Exception):
    pass


def load_plan(run_dir: Path) -> tuple[list[dict], list[dict]]:
    """Prüft review.json gegen die aktuellen Dateien. Gibt (updates, known_issues) zurück."""
    review = decisions.load(run_dir)
    if not review:
        raise Abbruch("Keine review.json. Erst prüfen: python3 scripts/agent/review.py <lauf>")
    files: dict[str, dict] = {}
    updates, issues = [], []
    for d in review["entscheidungen"]:
        if d["entscheidung"] not in (J, K):
            continue
        f = d["datei"]
        if f not in files:
            path = run_dir / f
            if not path.exists():
                raise Abbruch(f"{f} fehlt im Lauf-Ordner")
            if decisions.file_hash(path) != d["datei_hash"]:
                raise Abbruch(f"{f} wurde nach der Prüfung geändert. Bitte neu prüfen (review.py).")
            files[f] = {p["sha"]: p for p in decisions.parse_proposals(path)}
        p = files[f].get(d["sha"])
        if not p or p["code"] != d["code"]:
            raise Abbruch(f"Vorschlag {d['code']} nicht mehr in {f} gefunden (Fingerabdruck)")
        if d["entscheidung"] == K:
            # k = Text übernehmen UND Datenproblem in known_issues festhalten (seit 10.11. abends)
            issues.append(d)
        extra = set(p["columns"]) - set(checks.ALLOWED_COLUMNS)
        if extra or set(p["columns"]) - set(p["set"]):
            raise Abbruch(f"{d['code']}: unerlaubte Spalten {sorted(extra) or p['columns']}")
        if p["errors"]:
            raise Abbruch(f"{d['code']}: nicht lesbare Werte: {'; '.join(p['errors'])}")
        if p["set"] != d["set"]:
            raise Abbruch(f"{d['code']}: Vorschlag weicht von der geprüften Fassung ab")
        if not (p["set"].get("description") or "").strip():
            raise Abbruch(f"{d['code']}: keine Beschreibung im Vorschlag")
        if "alt" not in d:
            raise Abbruch(f"{d['code']}: review.json ohne alte Werte (alte Fassung), bitte neu prüfen")
        updates.append({"code": d["code"], "set": p["set"], "alt": d["alt"]})
    codes = [u["code"] for u in updates]
    if len(codes) != len(set(codes)):
        raise Abbruch("Ein Code kommt mehrfach vor: " + ", ".join(sorted({c for c in codes if codes.count(c) > 1})))
    return updates, issues


def backup_table(cur, stamp: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"indicator_metadata_{stamp}.csv"
    with path.open("w", encoding="utf-8") as fh:
        cur.copy_expert("COPY indicator_metadata TO STDOUT WITH (FORMAT csv, HEADER)", fh)
    old = sorted(BACKUP_DIR.glob("indicator_metadata_*.csv"))
    for p in old[:-KEEP_BACKUPS]:
        p.unlink()
    return path


def undo_text(cur, rows: list[tuple]) -> str:
    lines = ["-- Rückgängig machen der Übertragung (alte Werte vor apply.py)",
             f"-- Erstellt {datetime.now():%Y-%m-%d %H:%M}. Nur ausführen, wenn du das wirklich willst.",
             "BEGIN;"]
    assign = ", ".join(f"{c} = %s" for c in UNDO_COLS)
    for row in rows:
        lines.append(cur.mogrify(f"UPDATE indicator_metadata SET {assign} WHERE indicator_code = %s;",
                                 list(row[1:]) + [row[0]]).decode("utf-8"))
    lines.append("-- COMMIT;")
    return "\n".join(lines) + "\n"


def verify(cur, updates: list[dict]) -> list[str]:
    cols = ", ".join(checks.ALLOWED_COLUMNS)
    cur.execute(f"SELECT indicator_code, {cols}, metadata_reviewed_at "
                "FROM indicator_metadata WHERE indicator_code = ANY(%s)", ([u["code"] for u in updates],))
    have = {r[0]: dict(zip(UNDO_COLS, r[1:])) for r in cur.fetchall()}
    errors = []
    for u in updates:
        r = have.get(u["code"])
        if not r:
            errors.append(f"{u['code']}: Zeile fehlt")
            continue
        for col, val in u["set"].items():
            if not same(r[col], val):
                errors.append(f"{u['code']}: {col} weicht ab")
        if r["metadata_reviewed_at"] is None:
            errors.append(f"{u['code']}: metadata_reviewed_at nicht gesetzt")
    return errors


def main(arg: str) -> None:
    run_dir = runs.resolve_run(arg)
    st = runs.read_status(run_dir) or {}
    if st.get("status") != "freigegeben":
        sys.exit(f"Lauf hat Status „{st.get('status')}“. Übertragen geht nur bei „freigegeben“.")
    try:
        updates, issues = load_plan(run_dir)
    except Abbruch as e:
        sys.exit(f"❌ {e}")
    if not updates and not issues:
        sys.exit("Nichts zu übertragen.")

    print(f"Lauf: {run_dir.name}")
    print(f"  {len(updates)} Indikatoren eintragen (indicator_metadata), davon "
          f"{sum(1 for u in updates if any(u['alt'].get(c) not in (None, '', []) for c in u['set']))} mit Ersetzungen")
    print(f"  {len(issues)} bekannte Auffälligkeiten festhalten (known_issues)")
    try:
        ok = input("Übertragen? Zum Bestätigen „ja“ tippen: ").strip().lower() == "ja"
    except EOFError:
        ok = False
    if not ok:
        sys.exit("Nicht übertragen.")

    stamp = f"{datetime.now():%Y-%m-%d_%H%M%S}"
    conn = connect_write()
    try:
        with conn.cursor() as cur:
            backup = backup_table(cur, stamp)
            print(f"  Backup: {backup.relative_to(REPO_ROOT)}")
            codes = [u["code"] for u in updates]
            cur.execute(f"SELECT indicator_code, {', '.join(UNDO_COLS)} "
                        "FROM indicator_metadata WHERE indicator_code = ANY(%s) FOR UPDATE", (codes,))
            old_rows = cur.fetchall()
            if len(old_rows) != len(codes):
                missing = set(codes) - {r[0] for r in old_rows}
                raise Abbruch(f"Codes nicht in indicator_metadata: {', '.join(sorted(missing))}")
            current = {r[0]: dict(zip(UNDO_COLS, r[1:])) for r in old_rows}
            changed = [f"{u['code']}.{c}" for u in updates for c in u["set"]
                       if not same(current[u["code"]][c], u["alt"].get(c))]
            if changed:
                raise Abbruch("Seit der Prüfung in der DB geändert (nicht überschreiben): " + ", ".join(changed))
            undo_sql = undo_text(cur, old_rows)

            for u in updates:
                cols = list(u["set"])
                q = psql.SQL("UPDATE indicator_metadata SET {}, metadata_reviewed_at = now() "
                             "WHERE indicator_code = %s").format(
                    psql.SQL(", ").join(psql.SQL("{} = %s").format(psql.Identifier(c)) for c in cols))
                cur.execute(q, [u["set"][c] for c in cols] + [u["code"]])
                if cur.rowcount != 1:
                    raise Abbruch(f"{u['code']}: UPDATE hat {cur.rowcount} Zeilen geändert statt 1")

            n_issue = 0
            for d in issues:
                title = d["notiz"][:200]
                cur.execute("SELECT 1 FROM known_issues WHERE indicator_code = %s AND title = %s",
                            (d["code"], title))
                if cur.fetchone():
                    print(f"  known_issues: {d['code']} schon vorhanden, übersprungen")
                    continue
                desc = (f"{d['notiz']}\n\nFestgehalten bei der Prüfung von Lauf {run_dir.name}. "
                        f"Verworfener Vorschlag: " + "; ".join(f"{k} = {v}" for k, v in d["set"].items() if k in ("name", "description")))
                cur.execute("INSERT INTO known_issues (scope, indicator_code, title, description, decision) "
                            "VALUES ('indicator', %s, %s, %s, 'accepted')", (d["code"], title, desc))
                n_issue += 1

            errors = verify(cur, updates)
            if errors:
                raise Abbruch("Kontrolle vor dem COMMIT fehlgeschlagen: " + "; ".join(errors))
        conn.commit()
    except Abbruch as e:
        conn.rollback()
        conn.close()
        sys.exit(f"❌ {e}\nAlles zurückgerollt, die Datenbank ist unverändert.")
    except Exception as e:
        conn.rollback()
        conn.close()
        sys.exit(f"❌ Fehler: {e}\nAlles zurückgerollt, die Datenbank ist unverändert.")
    conn.close()
    undo = run_dir / "rueckgaengig.sql"
    undo.write_text(undo_sql, encoding="utf-8")

    # Kontrolle nach dem COMMIT mit neuer Verbindung
    conn = connect_write()
    try:
        with conn.cursor() as cur:
            errors = verify(cur, updates)
    finally:
        conn.rollback()
        conn.close()

    lines = ["# Übertragung", "", f"Lauf: `{run_dir.name}`  ", f"Übertragen: {datetime.now():%Y-%m-%d %H:%M}", "",
             f"- {len(updates)} Indikatoren eingetragen, metadata_reviewed_at gesetzt",
             f"- {n_issue} Einträge in known_issues",
             f"- Backup: `{backup.relative_to(REPO_ROOT)}`",
             f"- Rückgängig: `{undo.name}`",
             f"- Kontrolle nach COMMIT: {'OK' if not errors else 'FEHLER: ' + '; '.join(errors)}", "",
             "## Eingetragen", ""] + [f"- {u['code']}: {u['set'].get('name', '')}" for u in updates]
    (run_dir / "uebertragung.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    runs.set_status(run_dir, "übertragen", f"{len(updates)} eingetragen, {n_issue} known_issues")

    print(f"✅ {len(updates)} eingetragen, {n_issue} known_issues.")
    print("✅ Kontrolle nach COMMIT: alles wie freigegeben." if not errors
          else "❌ Kontrolle nach COMMIT: " + "; ".join(errors))
    print(f"Protokoll: {run_dir / 'uebertragung.md'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Aufruf: python3 scripts/agent/apply.py <lauf>")
    main(sys.argv[1])
