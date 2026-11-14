"""
Beschreibungs-Lauf: formuliert NUR das Feld description eines Sekretär-Laufs neu,
nach der aktuellen Regel (sachlich, gängige Fachwörter, keine Alltagssprache).
Alle anderen Felder bleiben unverändert. Gedacht für Läufe, die vor der Regeländerung
vom 12.11.2026 entstanden sind (#129, #123).

Zwei Schritte, aus der Repo-Wurzel (venv aktiv):

  1. Vorschlag (ändert nichts an metadata.sql):
       python3 scripts/agent/beschreibung.py <lauf> [--model sonnet] [--budget 0.5]
     -> beschreibungen.json + beschreibungen.md (alt/neu nebeneinander) im Lauf-Ordner

  2. Übernehmen (nach dem Lesen von beschreibungen.md):
       python3 scripts/agent/beschreibung.py <lauf> --uebernehmen
     -> Backup metadata.sql.vor_beschreibung, nur die description-Werte ersetzt,
        Nachkontrolle, danach Auto-Prüfung neu.

Nur für Läufe ohne review.json (Status neu oder geprüft): apply.py prüft einen
Fingerabdruck der Datei, eine Änderung nach dem Review würde das Übertragen blockieren.
"""

import argparse
import asyncio
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from lib import runs, sqlfile

CODE_LINE = re.compile(r"^([A-Za-z0-9_]+:\S+)\s*$")
DESC_MAX = 200
ALLOWED_STATUS = {"neu", "geprüft"}
# Wörter, die auf wertende Alltagssprache hindeuten (nur Hinweis, kein Abbruch)
SOFT_WORDS = re.compile(r"\b(clearly|too|much|(?<!multidimensionally )poor|very|really|typical|basically|someone|baby)\b", re.I)

SYSTEM_PROMPT = """Du formulierst für eine Indikator-Datenbank das Feld description neu. Nur dieses Feld.

REGEL für description (Englisch):
- GENAU EIN Satz, höchstens 200 Zeichen (besser unter 150), endet mit Punkt.
- Sachlich: was gemessen wird. Gängige Fachwörter sind erwünscht (prevalence, mortality rate, share,
  per capita, incidence, ratio, index), statistischer Jargon nicht.
- Bevorzugt als Nominalphrase: "Share of …", "Prevalence of …", "Number of … per 1,000 …",
  "Value of …". Bei Indizes und Expertenurteilen: "Extent to which …" oder "How widespread …".
- Schwellen, Referenzstandards und Methode gehören NICHT hierher (sie stehen in key_info).
- Keine wertende Alltagssprache ("clearly too heavy", "much too short", "poor toilets",
  "a typical working person"). Keine Umschreibung von Fachbegriffen in Alltagswörter
  ("physical goods a country buys" statt "merchandise imports" ist falsch).
- So formuliert, dass ein hoher Wert "mehr davon" bedeutet.
- Keine Skalenzahlen, keine Wertebereiche, kein Quellenname, keine Maßeinheit, außer sie gehört zur
  Bedeutung (z. B. "per 1,000 live births").
- Nur Inhalte, die in name, producer_definition oder key_info stehen. Nichts hinzuerfinden.

Beispiele (gut):
- "Prevalence of overweight among girls under five."
- "How widespread corruption is in the public sector."

AUSGABE: ausschließlich ein JSON-Objekt, Schlüssel = indicator_code, Wert = neue description.
Jeder übergebene Code genau einmal. Kein Text davor oder danach."""


# ---------------------------------------------------------------- Datei lesen

def read_blocks(sql_path: Path) -> list[dict]:
    """Je Indikator: code und die Felder, die das Modell als Grundlage bekommt."""
    statements, _ = sqlfile.split_statements(sql_path.read_text(encoding="utf-8"))
    out = []
    for st in statements:
        upd = sqlfile.parse_update(st.sql)
        if not upd:
            continue
        code = next((m.group(1) for c in st.comments if (m := CODE_LINE.match(c))), None)
        if not code:
            raise SystemExit(f"Zeile {st.line}: UPDATE ohne Code-Kommentarzeile, Abbruch.")
        s = upd["set"]
        out.append({"code": code, "name": s.get("name"), "description": s.get("description"),
                    "unit": s.get("unit"), "scale_type": s.get("scale_type"), "direction": s.get("direction"),
                    "producer_definition": s.get("producer_definition"), "key_info": s.get("key_info")})
    if not out:
        raise SystemExit(f"Keine UPDATE-Blöcke in {sql_path}, Abbruch.")
    codes = [b["code"] for b in out]
    dup = {c for c in codes if codes.count(c) > 1}
    if dup:
        raise SystemExit(f"Codes doppelt in der Datei: {', '.join(sorted(dup))}. Abbruch.")
    return out


def validate(desc: str) -> list[str]:
    """Gleiche Grundregeln wie die Auto-Prüfung, plus Hinweis auf Alltagswörter."""
    notes = []
    if len(desc) > DESC_MAX:
        notes.append(f"FEHLER: {len(desc)} Zeichen (max. {DESC_MAX})")
    if len([x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", desc.strip()) if x]) != 1:
        notes.append("FEHLER: nicht genau ein Satz")
    if not desc.rstrip().endswith("."):
        notes.append("Hinweis: endet nicht mit Punkt")
    if (m := SOFT_WORDS.search(desc)):
        notes.append(f"Hinweis: Alltagswort „{m.group(0)}“")
    return notes


# ---------------------------------------------------------------- Schritt 1: Vorschlag

def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b == -1:
        raise SystemExit("Antwort des Modells enthält kein JSON-Objekt. Antwort:\n" + text[:1000])
    return json.loads(t[a:b + 1])


async def ask_model(blocks: list[dict], model: str, budget: float) -> tuple[dict, dict]:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

    prompt = ("Formuliere description für diese Indikatoren neu. Das Feld description zeigt die bisherige "
              "Fassung (alte Regel, oft zu umgangssprachlich).\n\n" + json.dumps(blocks, ensure_ascii=False, indent=1))
    options = ClaudeAgentOptions(system_prompt=SYSTEM_PROMPT, tools=[], allowed_tools=[], max_turns=1,
                                 permission_mode="dontAsk", setting_sources=[], max_budget_usd=budget, model=model)
    text, info, models = "", {}, set()
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage) and getattr(message, "model", None):
            models.add(message.model)
        elif isinstance(message, ResultMessage):
            text = message.result or ""
            info = {"subtype": message.subtype, "kosten_usd": message.total_cost_usd,
                    "dauer_s": round(message.duration_ms / 1000, 1), "modell": ", ".join(sorted(models)) or model}
    if info.get("subtype") != "success":
        raise SystemExit(f"Modell-Aufruf nicht erfolgreich: {info}. Antwort:\n{text[:1000]}")
    return parse_json(text), info


def propose(run_dir: Path, model: str, budget: float) -> None:
    blocks = read_blocks(run_dir / "metadata.sql")
    print(f"{run_dir.name}: {len(blocks)} Indikatoren, frage {model} …")
    new, info = asyncio.run(ask_model(blocks, model, budget))

    codes = [b["code"] for b in blocks]
    missing = [c for c in codes if not isinstance(new.get(c), str) or not new[c].strip()]
    extra = [c for c in new if c not in codes]
    if missing or extra:
        raise SystemExit(f"Antwort unvollständig. Fehlend: {missing or '-'} · Unbekannt: {extra or '-'}. Nichts gespeichert.")

    rows, n_fail, n_hint = [], 0, 0
    for b in blocks:
        d = new[b["code"]].strip()
        notes = validate(d)
        n_fail += any(n.startswith("FEHLER") for n in notes)
        n_hint += any(n.startswith("Hinweis") for n in notes)
        rows.append({"code": b["code"], "alt": b["description"], "neu": d, "hinweise": notes})

    stamp = datetime.now().isoformat(timespec="seconds")
    (run_dir / "beschreibungen.json").write_text(json.dumps(
        {"erstellt": stamp, **info, "eintraege": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    kosten = f"{info['kosten_usd']:.2f} USD" if info.get("kosten_usd") is not None else "unbekannt"
    md = [f"# Beschreibungs-Lauf {run_dir.name}\n",
          f"_{stamp} · Modell: {info['modell']} · Dauer: {info['dauer_s']} s · Kosten (rechnerisch): {kosten}_\n",
          f"{len(rows)} Indikatoren · {n_fail} mit FEHLER · {n_hint} mit Hinweis. "
          f"metadata.sql ist **noch unverändert**. Übernehmen mit `--uebernehmen`.\n"]
    for r in rows:
        md.append(f"## {r['code']}\n\n- alt: {r['alt']}\n- **neu: {r['neu']}**")
        md += [f"- {n}" for n in r["hinweise"]]
        md.append("")
    (run_dir / "beschreibungen.md").write_text("\n".join(md), encoding="utf-8")

    st = runs.read_status(run_dir) or {}
    runs.set_status(run_dir, st.get("status", "geprüft"),
                    f"Beschreibungs-Vorschlag: {len(rows)} neu, {n_fail} Fehler, Modell {info['modell']}, {kosten}")
    print(f"Fertig: {len(rows)} Vorschläge, {n_fail} mit FEHLER, {n_hint} mit Hinweis, Kosten {kosten}.")
    print(f"Lesen: {run_dir / 'beschreibungen.md'}")


# ---------------------------------------------------------------- Schritt 2: übernehmen

def replace_descriptions(text: str, new: dict[str, tuple[str, str]]) -> tuple[str, list[str]]:
    """Ersetzt je Code genau den description-Wert im Block nach der Zeile '-- <code>'.
    new: code -> (alt, neu). Prüft, dass dort wirklich der alte Wert steht. Gibt neuen Text und Fehler zurück."""
    errors = []
    for code, (old, neu) in new.items():
        m = re.search(r"^--\s*" + re.escape(code) + r"\s*$", text, re.M)
        if not m:
            errors.append(f"{code}: Code-Zeile nicht gefunden")
            continue
        end = text.find("WHERE indicator_code", m.end())
        d = re.compile(r"\bdescription\s*=\s*'").search(text, m.end(), end if end != -1 else len(text))
        if not d:
            errors.append(f"{code}: description im Block nicht gefunden")
            continue
        old_esc = old.replace("'", "''")
        if not text.startswith(old_esc + "'", d.end()) or text.startswith("'", d.end() + len(old_esc) + 1):
            errors.append(f"{code}: alter Wert steht nicht wie erwartet in der Datei")
            continue
        text = text[:d.end()] + neu.replace("'", "''") + text[d.end() + len(old_esc):]
    return text, errors


def apply_new(run_dir: Path) -> None:
    sql_path, js_path = run_dir / "metadata.sql", run_dir / "beschreibungen.json"
    if not js_path.exists():
        raise SystemExit("beschreibungen.json fehlt. Zuerst ohne --uebernehmen laufen lassen.")
    data = json.loads(js_path.read_text(encoding="utf-8"))
    rows = data["eintraege"]
    bad = [r["code"] for r in rows if any(n.startswith("FEHLER") for n in r["hinweise"])]
    if bad:
        raise SystemExit(f"Vorschläge mit FEHLER: {', '.join(bad)}. Erst neu erzeugen, nichts geändert.")
    backup = run_dir / "metadata.sql.vor_beschreibung"
    if backup.exists():
        raise SystemExit(f"{backup.name} existiert schon (bereits übernommen?). Nichts geändert.")

    # Kontrolle vorher: aktuelle Datei passt zum Vorschlag
    current = {b["code"]: b["description"] for b in read_blocks(sql_path)}
    stale = [r["code"] for r in rows if current.get(r["code"]) != r["alt"]]
    if stale or set(current) != {r["code"] for r in rows}:
        raise SystemExit(f"metadata.sql hat sich seit dem Vorschlag geändert ({stale or 'andere Codes'}). Nichts geändert.")

    text, errors = replace_descriptions(sql_path.read_text(encoding="utf-8"),
                                        {r["code"]: (r["alt"], r["neu"]) for r in rows})
    if errors:
        raise SystemExit("Abbruch, nichts geändert:\n  " + "\n  ".join(errors))

    shutil.copy2(sql_path, backup)
    sql_path.write_text(text, encoding="utf-8")

    # Kontrolle nachher: jede description = neu, alle anderen Felder unverändert
    def fields(p: Path) -> dict:
        out = {}
        for st in sqlfile.split_statements(p.read_text(encoding="utf-8"))[0]:
            u = sqlfile.parse_update(st.sql)
            if u:
                code = next((m.group(1) for c in st.comments if (m := CODE_LINE.match(c))), None)
                out[code] = u["set"]
        return out
    before, after = fields(backup), fields(sql_path)
    problems = []
    for r in rows:
        a, b = after.get(r["code"], {}), before.get(r["code"], {})
        if a.get("description") != r["neu"]:
            problems.append(f"{r['code']}: description nicht wie vorgeschlagen")
        if {k: v for k, v in a.items() if k != "description"} != {k: v for k, v in b.items() if k != "description"}:
            problems.append(f"{r['code']}: anderes Feld verändert")
    if problems:
        shutil.copy2(backup, sql_path)
        backup.unlink()
        raise SystemExit("Nachkontrolle fehlgeschlagen, Datei zurückgesetzt:\n  " + "\n  ".join(problems))
    print(f"Ersetzt: {len(rows)} descriptions, alle anderen Felder unverändert. Backup: {backup.name}")

    from lib import checks          # braucht die DB-Verbindung
    for r in checks.run_check(run_dir):
        c = r["anzahl"]
        print(f"Auto-Prüfung {r['datei']}: ✅ {c['OK']} · ⚠️ {c['ANSEHEN']} · ❌ {c['FEHLER']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="description eines Sekretär-Laufs neu formulieren")
    ap.add_argument("lauf")
    ap.add_argument("--uebernehmen", action="store_true", help="Vorschlag in metadata.sql übernehmen")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--budget", type=float, default=0.5, help="Höchstbudget in USD (rechnerisch)")
    a = ap.parse_args()
    run_dir = runs.resolve_run(a.lauf)
    status = (runs.read_status(run_dir) or {}).get("status")
    if status not in ALLOWED_STATUS or (run_dir / "review.json").exists():
        sys.exit(f"Lauf hat Status „{status}“ bzw. schon eine review.json. Nur vor dem Review möglich.")
    if not (run_dir / "metadata.sql").exists():
        sys.exit("Keine metadata.sql in diesem Lauf.")
    apply_new(run_dir) if a.uebernehmen else propose(run_dir, a.model, a.budget)
