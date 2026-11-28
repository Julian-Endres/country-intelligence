"""
Der Sekretär: arbeitet einen frei formulierten Auftrag selbstständig ab,
bis er fertig ist oder das Budget aufgebraucht hat. Ändert nie die Datenbank,
sondern legt Vorschläge und Explainer in scripts/agent/output/ ab.

Aufruf aus der Repo-Wurzel (venv aktiv):
  python3 scripts/agent/secretary.py "Auftrag" --thema vdem [--budget 1.0] [--max-turns 80]
  Kasten-Modus (26.11.2026): nur kasten.md zu einem vorhandenen Leitfaden schreiben
  python3 scripts/agent/secretary.py "WB" --thema wb_kasten --kasten-aus 2026-11-10_1457_sekretaer_wb_leitfaden --budget 0.4

Beispiel:
  python3 scripts/agent/secretary.py "VDEM: 10 Indikatoren nach Metadaten v3 beschreiben." --thema vdem --budget 1.5

Ergebnis: Lauf-Ordner scripts/agent/output/<datum>_sekretaer_<thema>/ mit
metadata.sql, befunde.md, ggf. leitfaden.md + kasten.md, protokoll.md und pruefung.md (Auto-Prüfung).
"""

import argparse
import asyncio
import re
import shutil
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
from lib.selfcheck import self_check
from lib import tools as T

SYSTEM_PROMPT = """Du bist der Sekretär für Julians Projekt "Country Intelligence", eine PostgreSQL-Datenbank
mit Länderdaten aus vielen internationalen Quellen. Du bereitest vor, Julian entscheidet und führt aus.
Du kannst die Datenbank nur lesen. Du arbeitest selbstständig, bis der Auftrag erledigt ist.

DATENBANK
- indicators (iso_numeric, indicator_code, source_id, value, time_period, obs_status): ca. 4,2 Mio. Zeilen. Nie ungefiltert abfragen, immer mit WHERE und Aggregation.
- indicator_metadata (indicator_code, name, description, unit, source_id, domain, category, dimension,
  scale_type, scale_min, scale_max, direction, data_origin, temporal_type, key_info, producer_definition,
  value_labels, reference, keywords, metadata_reviewed_at, ...). Spaltenkommentare enthalten die Regeln.
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
   Excel-Dateien (xlsx, xls) genauso mit table_to_text umwandeln: Die Textdatei heißt <name>_xlsx.txt bzw.
   <name>_xls.txt, jede Zeile beginnt mit Blatt und Excel-Zeile (z. B. "Notes!17: ..."). Erst nach Blättern wie
   Notes, Codebook, Legend, Definitions suchen; Datenblätter für die Länder-Stichprobe. Im Beleg die .txt nennen.
4. APIs (z. B. Weltbank): Antwort mit download_file als .json in den Referenzordner speichern
   (z. B. https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.CD?format=json -> wb_NY.GDP.PCAP.CD.json)
   und mit search_text/read_text wörtlich lesen. WebFetch kürzt und umschreibt Texte, deshalb nie als Beleg
   für wörtliche Zitate verwenden; WebFetch nur für Überblicksseiten.

ERGEBNISSE (mit write_output, laufend schreiben, nicht erst am Ende)
A) Vorschlags-SQL, Datei metadata.sql (Metadaten v3). Bestehende Werte dürfen ersetzt werden;
   vorher per sql_query lesen, was drinsteht. Julian sieht alt und neu nebeneinander.
   - Erste Zeile: BEGIN;  Letzte Zeile: -- COMMIT;
   - Pro Indikator ein Block, IMMER alle 14 Felder (unbekannt oder nicht belegbar: NULL, nicht raten):
     -- <indicator_code>          (allein in der Zeile, z. B. -- VDEM:v2x_libdem)
     -- Beleg: <Datei>, S. <Seite>, Zeile <Zeile>: "<wörtliches Zitat, höchstens 20 Wörter>"
        (Hauptbeleg für Definition und Beschreibung; bei Dateien ohne Seiten "S. …," weglassen)
     -- Beleg k1: <Datei>, S. <Seite>, Zeile <Zeile>: "<Zitat>"   (je ein Beleg pro key_info-Punkt, k1 bis k5)
     -- Sicherheit: HOCH | MITTEL | UNSICHER (mit Grund)
        Gesamtstufe = die des schwächsten bewerteten Feldes (nicht "HOCH (…; x MITTEL)" schreiben).
        data_origin zählt dabei NICHT mit: ein leeres oder unsicheres data_origin ist kein Grund für MITTEL.
     UPDATE indicator_metadata SET
       name = '...', description = '...', unit = NULL, scale_type = '...', scale_min = 0, scale_max = 1,
       direction = '...', data_origin = '...', temporal_type = '...',
       key_info = ARRAY['...', 'Note: ...'], producer_definition = '...', value_labels = NULL,
       reference = '...', keywords = ARRAY['...', '...']
     WHERE indicator_code = '...';
     Zitate wörtlich aus read_text kopieren, Auslassungen nur mit ...; die Auto-Prüfung vergleicht sie mit dem Text.
     Einfache Anführungszeichen im Text verdoppeln (''). Zahlen ohne Anführungszeichen, leer = NULL.
   Feldregeln (Englisch, außer keywords):
   - name: offizieller Name laut Quelle, nicht übersetzt.
   - description: GENAU EIN Satz, höchstens 200 Zeichen: sachlich, was gemessen wird.
     Gängige Fachwörter sind erwünscht (prevalence, mortality rate, share, per capita), statistischer
     Jargon nicht. Schwellen, Referenzstandards und Methode gehören in key_info, nicht hierher.
     Keine wertende Alltagssprache ("clearly too heavy", "much too short", "poor toilets").
     Beispiele: "Prevalence of overweight among girls under five." · "How widespread corruption is in the public sector."
     So formuliert, dass ein hoher Wert "mehr davon" bedeutet. Keine Skalenzahlen, kein Quellenname.
   - key_info: 1-5 Kernpunkte: wie entsteht der Wert, wie liest man ihn, Grenzen, Vergleichbarkeit,
     Unsicherheit, Bezugszeitraum. Jeder Punkt aus der Quelle belegt (Beleg kN). Eigene Folgerungen nur als
     Punkt, der mit "Note: " beginnt (ohne Beleg). Gibt die Quelle wenig her: weniger Punkte, nichts auffüllen.
   - producer_definition: wörtliche Definition des Herausgebers (z. B. V-Dem "Question", Weltbank sourceNote),
     muss wörtlich im Referenztext des Hauptbelegs stehen. Sonst NULL.
   - unit: echte Maßeinheit ohne Wertebereich ("current US dollars", "years", "deaths per 1,000 live births").
     Bei scale_type index, ordinal, binary, categorical: NULL.
   - scale_type: index | ordinal | binary | categorical | percent | count | currency | rate | ratio |
     measure (Messgröße wie Jahre, Tonnen, km²) | other
   - scale_min / scale_max: nur wenn die Quelle sie nennt oder sie mathematisch feststehen (Prozent 0/100),
     sonst NULL. Gegen die echten Werte prüfen (min/max per sql_query); Abweichungen in befunde.md.
   - direction: higher_is_better | higher_is_worse | neutral | not_applicable. Nur werten, wo das allgemein
     anerkannt ist (Lebenserwartung, Kindersterblichkeit, Korruption); sonst neutral.
   - data_origin: expert_survey | official_statistics | population_survey | model_estimate | event_count |
     administrative_record | other. Prüffrage: Beruht der Wert auf einer eigenen Beobachtung genau dieses
     Landes in genau diesem Jahr? Ja: die Art dieser Beobachtung, auch wenn sie danach zu einem Index
     verrechnet wird (V-Dem-Indizes, WGI: expert_survey). Nein, weil interpoliert, fortgeschrieben oder
     modelliert: model_estimate. Nur setzen, wenn eindeutig; sonst NULL (das ist kein Mangel).
   - temporal_type: annual | survey_wave | snapshot | irregular | other
   - value_labels: nur bei ordinal, binary, categorical, Format '0 = ...; 1 = ...'. Sonst NULL.
   - reference: Fundstelle als Abschnitt bzw. Variableneintrag, nicht als Seite ("V-Dem Codebook v16, section 2.1.2").
   - keywords: 3-8 Suchbegriffe, Deutsch und Englisch gemischt.
   - Fällt auf, dass ein Indikator laut Quelle überholt oder ersetzt ist: in befunde.md, nicht im SQL.
   - Nach jeweils höchstens 5 Indikatoren mit append=true anhängen.
   - VOR DEM ABSCHLUSS: self_check auf metadata.sql ausführen. FEHLER beheben und die Datei mit
     replace_output ersetzen (nie eine zweite SQL-Datei anlegen), dann erneut self_check. ANSEHEN-Hinweise
     beheben, wo möglich; was bleibt, in der Zusammenfassung kurz begründen.
B) Quellen-Leitfaden, Datei leitfaden.md (nur wenn der Auftrag danach fragt).
   Zweck: Julian will die Quelle als Ganzes verstehen und sich nach und nach bis zu den Rohdaten vorarbeiten.
   Er sammelt damit Wissen über viele internationale Datenquellen. Schreibe für einen klugen Leser,
   der die Quelle noch nicht kennt: Deutsch, klar, Fachbegriffe beim ersten Auftreten kurz erklären.
   Gründlich, aber lesbar. KEINE Zeilen- oder Seitenangaben im Text, KEINE Angaben über Julians Datenbank
   (Coverage, Lücken, Fehler gehören in befunde.md). Format: Titel als "# Leitfaden: <Quelle>", jeder
   Abschnitt als "## <Nr>. <Überschrift>" (daraus werden in Notion ausklappbare Abschnitte), Steckbriefe als
   "###". Gliederung, genau diese Überschriften:
   1. Auf einen Blick (3-4 Sätze: was, wer, wofür)
   2. Wer steckt dahinter (Institution, seit wann, Finanzierung, wer nutzt die Daten)
   3. Wofür die Quelle nützlich ist und wofür nicht (typische Fragen, Grenzen)
   4. So entstehen die Daten (Methodik in einfachen Worten, Schritt für Schritt)
   5. So ist der Datensatz aufgebaut (Ebenen, Variablentypen, Namenslogik der Variablen, Versionen und Updates)
   6. So liest du die Werte (Skalen, Richtung, Unsicherheit, Fallstricke beim Vergleichen)
   7. Die wichtigsten Variablen (5-10 Steckbriefe). Jeder Steckbrief als "### <Name> (<Code>)" mit genau
      diesen vier Zeilen: **Was sie misst**, **Wie man sie liest**, **Wann nehmen** (für welche Frage sie die
      richtige Wahl ist und wann eine andere Variable besser passt), **Nicht verwechseln mit**.
      Inhalt IMMER aus dem Codebook-Eintrag der Variable lesen (search_text, read_text), nie Platzhalter
      wie "siehe Eintrag" oder "Eintrag lesen". Findest du den Eintrag nicht: Variable weglassen.
   8. So nutzt du das Codebook (Aufbau, wo was steht, wie man eine Variable nachschlägt)
   9. Kritik und Grenzen (was die Quelle selbst einräumt; Außenkritik nur mit Namensnennung "laut ...";
      wenn du nichts Belastbares findest, schreib das, statt etwas zu erfinden)
   10. Verwandte Quellen (welche ähnlichen Datensätze es gibt und wie sie sich unterscheiden). Nur Quellen,
       die diese Quelle selbst nennt oder deren offizielle Selbstbeschreibung du gelesen hast (WebFetch der
       About-/Methodik-Seite), keine Einordnung aus dem Gedächtnis. Per sql_query in sources nachsehen,
       welche davon Julian schon hat, und das kurz erwähnen.
   11. Nächster Schritt: Rohdaten (wie die offizielle Datei aussieht, wie man sich einen kleinen Ausschnitt anschaut)
   12. Weiterlesen (offizielle Links)
   Dazu Datei leitfaden_belege.md: pro Abschnitt die Fundstellen (Dokument + Seite/Zeile oder URL), damit jede
   Aussage prüfbar bleibt.
   Dazu Datei kasten.md: die Kurzfassung, die in Notion oben auf der Datensatz-Seite steht. Genau eine Zeile
   je Feld, Form "Feld: Text", ohne Überschrift. Pflicht: Was, Wer, Umfang, Art der Werte, Nutzung; optional
   Vorsicht. Jede Zeile höchstens 2-3 kurze Sätze.
     Was: was die Werte messen, in einem Satz (bei Codes, die erst unser Loader berechnet, das so sagen).
     Wer: `<PRÄFIX>` · Urheber (nicht der Bezugsweg; kommt der Datensatz über OWID, QoG o. Ä., das dahinter
          nennen) · [Kurzname](https://offizielle-URL)
     Umfang: Quelle: <Länder, Zeitraum, Ausgabe laut Quelle> · Bei uns: <n> Codes, <n> Länder, <von–bis>,
          <n> Werte *(Stand TT.MM.JJJJ)*. Die Bei-uns-Zahlen per sql_query in diesem Lauf: COUNT(DISTINCT
          indicator_code), COUNT(DISTINCT iso_numeric), MIN/MAX(time_period), COUNT(*) aus indicators für
          split_part(indicator_code, ':', 1) = Präfix. Tausender mit Punkt. Stand = heutiges Datum.
     Art der Werte: Art der Erhebung (amtliche Statistik, Befragung, Experteneinschätzung, Modell, Zählung)
          und was erst unser Loader rechnet.
     Nutzung: Lizenz laut Quelle; nicht gefunden: "Lizenz nicht belegt".
     Vorsicht: höchstens drei echte Fallstricke (Skalenrichtung, Zeitreihenbrüche, bekannte Datenfehler bei
          uns aus befunde.md oder known_issues). Ohne echten Fallstrick die Zeile weglassen.
   Der Kasten fasst nur zusammen: jede Aussage muss im Leitfaden, in befunde.md oder in einer Abfrage dieses
   Laufs stehen. Nichts aus dem Gedächtnis (Sitz, Gründer, Lizenz, Abrufzeiträume). In leitfaden_belege.md
   einen Abschnitt "## Kasten" anlegen, je Feld eine Zeile "- <Feld>: <Fundstelle>" (Abschnitt des
   Leitfadens, Datei + Zeile, URL oder Nummer der Abfrage im Protokoll). Für Abschnitte 2, 3 und 9 offizielle Seiten der Quelle mit WebFetch lesen
   (About, Methodik, FAQ), Dokumente ggf. mit download_file holen.
C) Befunde, Datei befunde.md: Auffälligkeiten, die nicht in A gehören, vor allem Datenprobleme.
   PFLICHT bei jeder Quelle: Länder-Stichprobe. Ländercodes sind die häufigste Fehlerquelle im Projekt
   (Hofstede: Werte hingen am falschen Land). Vergleiche für 5 Länder (Bolivien '068', Deutschland '276',
   USA '840' und zwei weitere aus verschiedenen Regionen) die Werte eines Indikators in der DB mit der
   Originaldatei bzw. API der Quelle (mit download_file/read_text). Ergebnis als kleine Tabelle
   (Land, DB-Wert, Originalwert, passt?). Achte auch auf: Länder in der Quelle, die in der DB fehlen
   (z. B. Kosovo, das in countries keinen Eintrag hat), Werte bei Kleinstterritorien, die die Quelle gar
   nicht abdeckt, und historische Staaten (Westdeutschland, Jugoslawien, UdSSR, Nord-/Südjemen).
   Rohdateien zuerst lokal suchen (find_files, data/raw); ist keine Originalfassung erreichbar,
   das ausdrücklich schreiben statt zu schätzen.
   Weitere Befunde: echte Werte außerhalb der Skala, Lücken, Widersprüche. Jeweils mit Beleg. Bekannte Fälle stehen in der Tabelle known_issues (per sql_query lesen)
   und werden nicht erneut gemeldet.

REGELN
1. Jede Zahl stammt aus einer Abfrage dieses Laufs, jede inhaltliche Aussage aus dem Quellenmaterial. Nichts aus dem Gedächtnis.
2. Wenn du etwas im Quellenmaterial nicht findest: als UNSICHER markieren oder weglassen, nicht raten.
3. Auffälligkeit ist nicht gleich Fehler. Benennen, nicht bewerten.
4. Arbeite in sinnvoller Reihenfolge und sparsam: gezielt suchen statt viel lesen. Das Budget ist begrenzt.
5. Am Ende eine kurze Zusammenfassung auf Deutsch: was erledigt ist, was offen ist, welche Dateien entstanden sind.
"""


AGENT_TOOLS = T.ALL_TOOLS + [self_check]

KASTEN_AUFTRAG = """KASTEN-MODUS. Der Quellen-Leitfaden ist fertig: leitfaden.md und leitfaden_belege.md liegen schon in
deinem Lauf-Ordner (übernommen aus dem Lauf {quelle}; dessen Befunde als befunde_leitfaden.md, falls vorhanden).
Pfade zum Lesen ab Repo-Wurzel: {rel}/leitfaden.md, {rel}/leitfaden_belege.md, {rel}/befunde_leitfaden.md.
Schreibe KEINEN neuen Leitfaden, keine metadata.sql, und ändere leitfaden.md nicht.
Aufgabe: kasten.md für das Präfix {praefix} nach Abschnitt B (Felder, Form, Länge) und den Abschnitt "## Kasten"
mit write_output(filename="leitfaden_belege.md", append=true) anhängen (vorher eine Leerzeile).
- Bei-uns-Zahlen per sql_query in diesem Lauf (Abfrage wie in Abschnitt B), Stand = heutiges Datum.
- Was, Wer, Art der Werte, Nutzung aus dem Leitfaden (Abschnitte 1, 2, 4, 5, 12) und leitfaden_belege.md. Steht dort
  keine Lizenz, höchstens ein WebFetch der offiziellen Lizenz- oder Nutzungsseite, deren Link der Leitfaden nennt;
  sonst "Lizenz nicht belegt".
- Vorsicht: aus befunde_leitfaden.md und known_issues (sql_query, source oder Präfix {praefix}). befunde_leitfaden.md
  ist ALT (Datum des alten Laufs); seither wurden Daten korrigiert, Flags gesetzt und Loader erneuert. Jede Aussage
  über den Zustand bei uns (obs_status, fehlende Länder/Jahre, Anzahlen, Ausreißer) prüfst du mit einer Abfrage in
  diesem Lauf, z. B. obs_status je Code: SELECT indicator_code, obs_status, count(*) ... GROUP BY 1, 2. Kommt etwas
  anderes heraus als im alten Befund, gilt die Abfrage: dann den heutigen Stand schreiben oder den Punkt weglassen.
  Im Beleg die Nummer dieser Abfrage nennen.
- Neue Auffälligkeiten aus deinen Abfragen in befunde.md (kurz), sonst keine befunde.md.
Sparsam arbeiten: der Leitfaden ist die Quelle, kein neues Quellenstudium.
Zusatz zum Auftrag: """


def kasten_vorbereiten(run_dir, kasten_aus: str) -> str:
    """Kasten-Modus: Leitfaden-Dateien aus dem alten Lauf übernehmen (alter Kasten-Abschnitt entfällt).
    Gibt den Namen des Quell-Laufs zurück; fehlt etwas, Abbruch mit Meldung (nichts still schlucken)."""
    src = runs.OUTPUT_ROOT / kasten_aus.rstrip("/").split("/")[-1]
    for n in ("leitfaden.md", "leitfaden_belege.md"):
        if not (src / n).exists():
            raise SystemExit(f"Kasten-Modus: {src / n} fehlt – Abbruch.")
    shutil.copy2(src / "leitfaden.md", run_dir / "leitfaden.md")
    belege = (src / "leitfaden_belege.md").read_text(encoding="utf-8")
    belege = re.sub(r"^## Kasten\s*$.*?(?=^## |\Z)", "", belege, flags=re.M | re.S).rstrip() + "\n"
    (run_dir / "leitfaden_belege.md").write_text(belege, encoding="utf-8")
    if (src / "befunde.md").exists():
        shutil.copy2(src / "befunde.md", run_dir / "befunde_leitfaden.md")
    T.PROTECTED_NAMES.clear()
    T.PROTECTED_NAMES.update({"leitfaden.md", "leitfaden_belege.md", "befunde_leitfaden.md"})
    runs.set_status(run_dir, "neu", f"Kasten-Modus: Leitfaden übernommen aus {src.name}")
    return src.name


async def main(task: str, thema: str, budget: float, max_turns: int, model: str | None = None,
               kasten_aus: str | None = None, praefix: str | None = None) -> dict:
    builtin = ["WebSearch", "WebFetch"]
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        tools=builtin,                                   # eingebaut nur: Websuche und Webseiten lesen
        mcp_servers={"ci": T.build_server(AGENT_TOOLS)},
        strict_mcp_config=True,
        allowed_tools=builtin + T.tool_names(AGENT_TOOLS),
        permission_mode="dontAsk",
        setting_sources=[],
        max_turns=max_turns,
        max_budget_usd=budget,
        **({"model": model} if model else {}),       # z. B. "sonnet"; ohne Angabe: Standard der CLI
    )

    started = datetime.now()
    T.QUERY_LOG.clear()          # bei mehreren Läufen nacheinander (batch.py) nicht vermischen
    T.ACTION_LOG.clear()
    run_dir = runs.new_run("sekretaer", thema, auftrag=task, when=started)
    T.set_run_dir(run_dir)
    T.PROTECTED_NAMES.clear()
    if kasten_aus:
        quelle = kasten_vorbereiten(run_dir, kasten_aus)
        rel = run_dir.relative_to(runs.OUTPUT_ROOT.parent.parent.parent)
        task = KASTEN_AUFTRAG.format(quelle=quelle, rel=rel, praefix=praefix or task.split()[0]) + task
    print(f"\nAuftrag: {task}\nLauf-Ordner: {run_dir}\nBudget: {budget} USD, max. {max_turns} Turns\n")
    summary, stats, result = "", "", {"subtype": "abgebrochen", "kosten": None}
    models: set[str] = set()     # welches Modell tatsächlich geantwortet hat (für Vergleiche)
    fehler = ""
    try:
        async for message in query(prompt=task, options=options):
            if isinstance(message, AssistantMessage):
                if getattr(message, "model", None):
                    models.add(message.model)
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
                modell = ", ".join(sorted(models)) or "unbekannt"
                result = {"subtype": message.subtype, "kosten": message.total_cost_usd, "turns": message.num_turns,
                          "modell": modell}
                stats = f"Status: {message.subtype}, Modell: {modell}, Turns: {message.num_turns}, Dauer: {message.duration_ms / 60000:.1f} min, Kosten (rechnerisch): {cost}"

    except Exception as e:      # z. B. Nutzungslimit (claude_agent_sdk), Netz – laut melden, Lauf markieren (#141)
        fehler = f"{type(e).__name__}: {e}"
        result = {"subtype": "abgebrochen", "kosten": None, "fehler": fehler}
        stats = f"Status: abgebrochen, Fehler: {fehler}"
        print(f"\n!!! LAUF ABGEBROCHEN: {fehler}\n")

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
    results, kres = checks.run_check_all(run_dir)
    if results or kres:
        for r in results + ([kres] if kres else []):
            c = r["anzahl"]
            print(f"\nAuto-Prüfung {r['datei']}: ✅ {c['OK']} sauber · ⚠️ {c['ANSEHEN']} ansehen · ❌ {c['FEHLER']} fehlerhaft")
        print(f"Bericht: {run_dir / 'pruefung.md'}")
    else:
        print("\nKeine Vorschlags-SQL und kein Leitfaden in diesem Lauf, Auto-Prüfung entfällt.")
    if result.get("subtype") != "success":
        # Status bleibt, wie er ist (Rettung per review/apply bleibt möglich), aber mit deutlicher Notiz (#141)
        runs.set_status(run_dir, (runs.read_status(run_dir) or {}).get("status", "neu"), f"ABGEBROCHEN ({result.get('subtype')}): {fehler or 'kein regulärer Abschluss'}. "
                                         "Unvollständig: self_check/befunde.md können fehlen.")
        print(f"\n!!! Lauf als ABGEBROCHEN markiert: {run_dir.name}")
    result["run_dir"] = run_dir
    result["pruefung"] = [r["anzahl"] for r in results] if results else []
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sekretär-Agent")
    ap.add_argument("task", help="Auftrag in eigenen Worten")
    ap.add_argument("--thema", default="auftrag", help="Kurzname für den Lauf-Ordner, z. B. vdem")
    ap.add_argument("--budget", type=float, default=1.0, help="Höchstbudget in USD (rechnerisch), Standard 1.0")
    ap.add_argument("--max-turns", type=int, default=80)
    ap.add_argument("--model", default="sonnet", help="Modell, Standard sonnet (Entscheidung 14.11., #126); z. B. opus")
    ap.add_argument("--kasten-aus", default=None, help="Kasten-Modus: Lauf-Ordner (Name) mit fertigem Leitfaden")
    ap.add_argument("--praefix", default=None, help="Kasten-Modus: Präfix, Standard erstes Wort des Auftrags")
    a = ap.parse_args()
    asyncio.run(main(a.task, a.thema, a.budget, a.max_turns, a.model, a.kasten_aus, a.praefix))