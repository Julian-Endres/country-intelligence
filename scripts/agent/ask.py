"""
Stufe 1: Frag deine Datenbank.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/ask.py "Wie viele Indikatoren pro Domain gibt es?"

Was passiert:
  - Claude bekommt GENAU ein Werkzeug: sql_query (read-only).
  - Alle eingebauten Claude-Code-Werkzeuge (Bash, Dateien lesen/schreiben,
    Web) sind abgeschaltet.
  - Jede Abfrage wird live angezeigt und am Ende mit der Antwort im
    Lauf-Ordner scripts/agent/output/<datum>_ask_<thema>/protokoll.md gespeichert (Beleg).
"""

import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from lib import runs
from lib.tools import QUERY_LOG, SQL_TOOL_NAME, build_server

SYSTEM_PROMPT = """Du bist der Datenassistent für Julians Projekt "Country Intelligence":
eine PostgreSQL-Datenbank mit Länderdaten aus vielen internationalen Quellen.

Werkzeug: sql_query (nur lesend, höchstens 50 Zeilen pro Abfrage).

Wichtige Tabellen:
- indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status): Zeitreihen-Werte, ca. 4,2 Mio. Zeilen. Immer mit WHERE und Aggregation abfragen, nie ungefiltert.
- indicator_metadata (indicator_code, name, description, unit, source_id, domain, category, dimension)
- sources (id, name, short_code, url, description)
- countries (u. a. iso_numeric)
- weitere Tabellen in den Schemas politics, trade, international, history, culture, biodiversity. Bei Bedarf über information_schema.tables / information_schema.columns nachsehen.
Hierarchie: Domain → Category → Dimension → Indicator.

Regeln:
1. Jede Zahl in deiner Antwort stammt aus einer Abfrage, die du in diesem Lauf ausgeführt hast. Nichts schätzen, nichts aus dem Gedächtnis.
2. Wenn du die Struktur nicht kennst, schau sie zuerst nach (information_schema), statt Spaltennamen zu raten.
3. Große Tabellen nie ohne Filter oder Aggregation abfragen.
4. Wenn etwas auffällig wirkt, benenne es als Auffälligkeit, nicht als Fehler.
5. Antworte auf Deutsch, knapp. Schreibe KEINE SQL-Abfragen in die Antwort: Die tatsächlich ausgeführten Abfragen werden automatisch protokolliert. Eine abgeschriebene oder vereinfachte Abfrage sähe wie ein Beleg aus, wäre aber keiner.
"""


async def main(question: str) -> None:
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        tools=[],                       # alle eingebauten Werkzeuge aus
        mcp_servers={"ci": build_server()},
        strict_mcp_config=True,         # keine fremden MCP-Server laden
        allowed_tools=[SQL_TOOL_NAME],  # nur unser Werkzeug läuft ohne Rückfrage
        permission_mode="dontAsk",      # alles andere wird abgelehnt
        setting_sources=[],             # keine lokalen Einstellungen laden
        max_turns=15,                   # Notbremse gegen Endlosschleifen
    )

    answer = ""
    stats = ""
    print(f"\nFrage: {question}\n")
    async for message in query(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    sql = block.input.get("sql", block.input)
                    print(f"[Abfrage] {sql}\n")
                elif isinstance(block, TextBlock) and block.text.strip():
                    print(f"[Claude] {block.text.strip()}\n")
        elif isinstance(message, ResultMessage):
            answer = message.result or ""
            stats = f"Turns: {message.num_turns}, Dauer: {message.duration_ms / 1000:.1f} s, Status: {message.subtype}"

    print("=" * 60)
    print(answer)
    print(f"\n({stats}, Abfragen: {len(QUERY_LOG)})")

    run_dir = runs.new_run("ask", " ".join(question.split()[:5]), auftrag=question, status="erledigt")
    out = run_dir / "protokoll.md"
    lines = [f"# Frage\n\n{question}\n", f"# Antwort\n\n{answer}\n", f"# Abfragen ({len(QUERY_LOG)})\n"]
    for i, q in enumerate(QUERY_LOG, 1):
        info = q.get("error") and f"FEHLER: {q['error']}" or f"{q.get('rows', 0)} Zeilen" + (" (abgeschnitten)" if q.get("truncated") else "")
        lines.append(f"## {i}. {info}\n\n```sql\n{q['sql']}\n```\n")
    lines.append(f"\n_{stats}_\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Beleg gespeichert: {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('Aufruf: python3 scripts/agent/ask.py "Deine Frage"')
    asyncio.run(main(" ".join(sys.argv[1:])))
