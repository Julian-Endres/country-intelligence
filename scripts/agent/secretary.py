"""
Der Sekretär: arbeitet einen frei formulierten Auftrag selbstständig ab,
bis er fertig ist oder das Budget aufgebraucht hat. Ändert nie die Datenbank,
sondern legt Vorschläge und Explainer in scripts/agent/output/ ab.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/secretary.py "Auftrag" --thema vdem [--budget 1.0] [--max-turns 80]

Beispiel:
  python3 scripts/agent/secretary.py "VDEM: Codebook besorgen, für 10 Indikatoren ohne Beschreibung Vorschläge machen und einen Explainer schreiben." --thema vdem --budget 1.5

Ergebnis: Lauf-Ordner scripts/agent/output/<datum>_sekretaer_<thema>/ mit
metadata.sql, explainer.md, befunde.md, protokoll.md und pruefung.md (Auto-Prüfung).
"""

import argparse
import asyncio
from datetime import datetime

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from lib import checks, runs
from lib import tools as T

SYSTEM_PROMPT = """Du bist der Sekretär für Julians Projekt "Country Intelligence", eine PostgreSQL-Datenbank
mit Länderdaten aus vielen internationalen Quellen. Du bereitest vor, Julian entscheidet und führt aus.
Du kannst die Datenbank nur lesen. Du arbeitest selbstständig, bis der Auftrag erledigt ist.

DATENBANK
- indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status): ca. 4,2 Mio. Zeilen. Nie ungefiltert abfragen, immer mit WHERE und Aggregation.
- indicator_metadata (indicator_code, name, description, unit, source_id, domain, category, dimension)
- sources (id, name, short_code, url, description)
- countries (u. a. iso_numeric; Bolivien = '068', Deutschland = '276')
- Weitere Schemas: politics, trade, international, history, culture, biodiversity (über information_schema nachsehen).
- Indikator-Codes haben das Format QUELLE:originalcode, z. B. VDEM:v2x_libdem.

WERKZEUGE FÜR QUELLENMATERIAL
1. find_files: Immer zuerst lokal suchen (z. B. nach "codebook", Quellenname).
2. Nur wenn nichts da ist: Die offizielle Download-Adresse über WebSearch finden (Originalquelle, nicht Drittseiten)
   und mit download_file in den Referenzordner laden. Sinnvoller Dateiname, z. B. vdem_codebook_v15.pdf.
3. pdf_to_text einmal ausführen, danach mit search_text gezielt suchen und mit read_text die Stelle lesen.
   Nie das ganze Dokument lesen, nur die Abschnitte zu den gesuchten Indikatoren.

ERGEBNISSE (mit write_output, laufend schreiben, nicht erst am Ende)
A) Vorschlags-SQL, Datei metadata.sql:
   - Erste Zeile: BEGIN;  Letzte Zeile: -- COMMIT;  (Julian committet selbst)
   - Pro Indikator ein Block:
     -- <indicator_code>   (genau so, z. B. -- VDEM:v2x_libdem, allein in der Zeile)
     -- Beleg: <Datei>, S. <Seite>, Zeile <Zeile>: "<wörtliches Originalzitat, höchstens 20 Wörter>"
        (Zitat wörtlich aus read_text kopieren, Auslassungen nur mit ...; die Auto-Prüfung vergleicht es mit dem Text)
     -- Sicherheit: HOCH | MITTEL | UNSICHER (mit Grund)
     UPDATE indicator_metadata SET name = '...', unit = '...', description = '...'
     WHERE indicator_code = '...' AND (description IS NULL OR TRIM(description) = '');
   - name: der offizielle lesbare Name laut Quelle (Englisch, wie in der Quelle).
   - unit: die tatsächliche Skala, gegen die echten Werte geprüft (min/max/Anzahl Stufen per sql_query).
     Beispiele: 'index 0-1', 'ordinal 0-3', 'latent scale (approx. -4 to 4)', 'binary 0/1'.
   - description: 1-3 Sätze auf Englisch, was der Indikator misst und wie die Skala zu lesen ist (hoch = ?).
     Inhalt nur aus dem Quellenmaterial, nichts erfinden. Einfache Anführungszeichen im Text verdoppeln ('').
   - Nach jeweils höchstens 5 Indikatoren mit append=true anhängen.
B) Explainer, Datei explainer.md, auf Deutsch, verständlich für jemanden, der den Datensatz
   noch nicht kennt. Gliederung (Vorlage aus Julians Notion):
   - Was misst er wirklich? (Konzept, nicht nur Name)
   - So liest du die Daten (Skalen, was hoch/niedrig bedeutet, Fallstricke beim Vergleichen)
   - Originalquelle vs. Aggregator?
   - Coverage (Länder/Jahre, per sql_query belegt)
   - Verteilung (Ausreißer, Extremwerte, Muster, per sql_query belegt)
   - 3 Länder im Detail (BOL, DEU + ein überraschendes Land, mit echten Werten)
   - Stärken & Schwächen / methodische Fallstricke
   - Verbindungen zu anderen Datensätzen in der DB
   - Bewertungs-Richtung (hoch = gut / schlecht / neutral)
   - Leitindikator? Warum?
   - SQL-Rezept (2-3 Abfragen, die du in diesem Lauf tatsächlich ausgeführt hast)
C) Befunde, Datei befunde.md: Auffälligkeiten, die nicht in A gehören
   (falsche Einheiten, Lücken, Widersprüche zu Notion-Angaben usw.), jeweils mit Beleg.

REGELN
1. Jede Zahl stammt aus einer Abfrage dieses Laufs, jede inhaltliche Aussage aus dem Quellenmaterial. Nichts aus dem Gedächtnis.
2. Wenn du etwas im Quellenmaterial nicht findest: als UNSICHER markieren oder weglassen, nicht raten.
3. Auffälligkeit ist nicht gleich Fehler. Benennen, nicht bewerten.
4. Arbeite in sinnvoller Reihenfolge und sparsam: gezielt suchen statt viel lesen. Das Budget ist begrenzt.
5. Am Ende eine kurze Zusammenfassung auf Deutsch: was erledigt ist, was offen ist, welche Dateien entstanden sind.
"""


async def main(task: str, thema: str, budget: float, max_turns: int) -> None:
    builtin = ["WebSearch"]
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        tools=builtin,                                   # einziges eingebautes Werkzeug: Websuche
        mcp_servers={"ci": T.build_server(T.ALL_TOOLS)},
        strict_mcp_config=True,
        allowed_tools=builtin + T.tool_names(T.ALL_TOOLS),
        permission_mode="dontAsk",
        setting_sources=[],
        max_turns=max_turns,
        max_budget_usd=budget,
    )

    started = datetime.now()
    run_dir = runs.new_run("sekretaer", thema, auftrag=task, when=started)
    T.set_run_dir(run_dir)
    print(f"\nAuftrag: {task}\nLauf-Ordner: {run_dir}\nBudget: {budget} USD, max. {max_turns} Turns\n")
    summary, stats = "", ""
    async for message in query(prompt=task, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    name = block.name.replace("mcp__ci__", "")
                    arg = block.input.get("sql") or block.input.get("pattern") or block.input.get("filename") \
                        or block.input.get("url") or block.input.get("query") or block.input.get("name_contains") \
                        or block.input.get("pdf_path") or ""
                    print(f"[{name}] {str(arg)[:160]}")
                elif isinstance(block, TextBlock) and block.text.strip():
                    print(f"\n[Sekretär] {block.text.strip()[:500]}\n")
        elif isinstance(message, ResultMessage):
            summary = message.result or ""
            cost = f"{message.total_cost_usd:.2f} USD" if message.total_cost_usd is not None else "unbekannt"
            stats = f"Status: {message.subtype}, Turns: {message.num_turns}, Dauer: {message.duration_ms / 60000:.1f} min, Kosten (rechnerisch): {cost}"

    print("=" * 60)
    print(summary)
    print(f"\n({stats}, SQL-Abfragen: {len(T.QUERY_LOG)})")

    log = run_dir / "protokoll.md"
    lines = [f"# Auftrag\n\n{task}\n", f"_{stats}_\n", f"# Zusammenfassung\n\n{summary}\n", "# Aktionen\n"]
    lines += [f"- {a}" for a in T.ACTION_LOG]
    lines.append(f"\n# SQL-Abfragen ({len(T.QUERY_LOG)})\n")
    for i, q in enumerate(T.QUERY_LOG, 1):
        info = f"FEHLER: {q['error']}" if q.get("error") else f"{q.get('rows', 0)} Zeilen" + (" (abgeschnitten)" if q.get("truncated") else "")
        lines.append(f"## {i}. {info}\n\n```sql\n{q['sql']}\n```\n")
    log.write_text("\n".join(lines), encoding="utf-8")
    print(f"Protokoll: {log}")

    # Auto-Prüfung direkt im Anschluss
    results = checks.run_check(run_dir)
    if results:
        for r in results:
            c = r["anzahl"]
            print(f"\nAuto-Prüfung {r['datei']}: ✅ {c['OK']} sauber · ⚠️ {c['ANSEHEN']} ansehen · ❌ {c['FEHLER']} fehlerhaft")
        print(f"Bericht: {run_dir / 'pruefung.md'}")
    else:
        print("\nKeine Vorschlags-SQL in diesem Lauf, Auto-Prüfung entfällt.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sekretär-Agent")
    ap.add_argument("task", help="Auftrag in eigenen Worten")
    ap.add_argument("--thema", default="auftrag", help="Kurzname für den Lauf-Ordner, z. B. vdem")
    ap.add_argument("--budget", type=float, default=1.0, help="Höchstbudget in USD (rechnerisch), Standard 1.0")
    ap.add_argument("--max-turns", type=int, default=80)
    a = ap.parse_args()
    asyncio.run(main(a.task, a.thema, a.budget, a.max_turns))
