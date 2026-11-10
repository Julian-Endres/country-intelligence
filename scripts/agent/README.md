# Sekretär-Agent (v1)

Der Sekretär beschreibt Indikatoren und Quellen der Datenbank: Metadaten nach Format v3,
Quellen-Leitfäden und Befunde zu Datenproblemen. **Er ändert die Datenbank nie selbst.**
Er liest nur (Rolle `ci_agent_readonly`) und legt Vorschläge ab. Julian prüft und überträgt.

Läuft über das Pro-Abo (Claude Agent SDK), keine API-Credits nötig.

## Ablauf in vier Schritten

| Schritt | Wer | Befehl | Ergebnis / Status |
|---|---|---|---|
| 1. Lauf | Agent | `secretary.py "Auftrag" --thema x` | Vorschläge im Lauf-Ordner, Selbstprüfung mit `self_check` |
| 2. Auto-Prüfung | Skript, ohne KI | läuft automatisch (von Hand: `check.py <lauf>`) | `pruefung.md`, Status **geprüft** |
| 3. Prüfung | Julian | `review.py <lauf>` | `review.json`, Status **freigegeben** |
| 4. Übertragung | Julian | `apply.py <lauf>` | DB geändert, Status **übertragen** |

Alle Befehle aus der Repo-Wurzel, venv aktiv (`source venv/bin/activate`).
`<lauf>` = Ordnername in `scripts/agent/output/` oder sein eindeutiger Anfang (z. B. `2026-11-10_1440`).

```bash
# Überblick: offene Läufe und der jeweils nächste Befehl
python3 scripts/agent/status.py            # --alle für alle, <lauf> für den Verlauf

# 1. Lauf (Beispiel)
python3 scripts/agent/secretary.py "VDEM: Beschreibe 5 Indikatoren nach Metadaten v3 (metadata.sql und befunde.md mit Länder-Stichprobe). Nimm v2x_libdem, v2x_polyarchy, v2x_regime, v2x_corr und v2x_rule." --thema vdem_v3 --budget 2.0

# 3. Prüfen: ⚠️ und 3 zufällige ✅ ansehen, j / n / k, am Ende speichern
python3 scripts/agent/review.py <lauf>

# 4. Übertragen: "ja" tippen
python3 scripts/agent/apply.py <lauf>

# Mehrere Pakete nacheinander, nebenbei (Mac bleibt wach dank caffeinate)
python3 scripts/agent/batch.py WB --vorschau                       # was wäre dran?
caffeinate -i python3 scripts/agent/batch.py WB --paket 40 --anzahl 3

# Läufe ohne SQL (Leitfaden) abschließen bzw. Läufe ablegen
python3 scripts/agent/status.py <lauf> --erledigt "in Notion übernommen"
python3 scripts/agent/status.py <lauf> --verwerfen "Grund"
```

Tasten in `review.py`: **j** übernehmen · **n** verwerfen (Grund Pflicht) · **k** verwerfen und als
bekannte Auffälligkeit in `known_issues` festhalten · **a** abbrechen (nichts gespeichert).
Lehnst du eine Stichprobe ab, zeigt das Skript alle übrigen ✅-Vorschläge.

## Was ein Lauf erzeugt

`scripts/agent/output/JJJJ-MM-TT_HHMM_sekretaer_<thema>/` (von Git ignoriert):

- `metadata.sql`: Vorschläge, ein UPDATE pro Indikator mit allen 14 Feldern, Belegen und Sicherheit
- `befunde.md`: Datenprobleme, Pflicht-Länder-Stichprobe (DB gegen Originaldatei)
- `leitfaden.md` + `leitfaden_belege.md`: Quellen-Leitfaden (nur wenn beauftragt)
- `protokoll.md`: Auftrag, Zusammenfassung, Werkzeug-Aktionen, alle SQL-Abfragen
- `pruefung.md` / `.json`: Auto-Prüfung · `review.json`: deine Entscheidungen
- `uebertragung.md`, `rueckgaengig.sql`: nach apply.py

Status: `neu → geprüft → freigegeben → übertragen`, dazu `erledigt` (ohne SQL) und `verworfen`.

## Sicherungen

- Agent: nur Lesezugriff auf die DB, Schreiben nur im eigenen Lauf-Ordner und in `data/raw/reference/`.
- `apply.py` führt die SQL-Datei des Agenten **nie** aus. Es baut jedes UPDATE selbst, nur für erlaubte
  Spalten, und nur für Vorschläge, die in `review.json` freigegeben sind.
- Fingerabdruck: Wird die Datei nach der Prüfung geändert, bricht `apply.py` ab.
- Sperre: Steht in der DB nicht mehr genau der alte Wert aus der Prüfung, bricht `apply.py` ab.
- Eine Transaktion, jedes UPDATE genau 1 Zeile, Kontrolle vor und nach dem COMMIT.
- Backup der ganzen Tabelle `indicator_metadata` nach `backups/agent/` (die letzten 5 bleiben)
  und `rueckgaengig.sql` im Lauf-Ordner (alte Werte; `-- COMMIT;` erst bewusst einkommentieren).
- `apply.py` setzt `metadata_reviewed_at`. Schon freigegebene Indikatoren zeigt `review.py` immer an.

## Metadaten v3 (Regeln, Kurzfassung)

Die Regeln stehen als Spaltenkommentare in der DB und werden von der Auto-Prüfung kontrolliert:

- `description`: genau ein Satz in einfachen Wörtern, höchstens 200 Zeichen, hoher Wert = „mehr davon“
- `key_info`: 1 bis 5 Kernpunkte, jeder belegt; eigene Hinweise beginnen mit „Note:“
- `producer_definition`: wörtlich aus der Quelle, sonst leer
- `unit`: nur echte Maßeinheit ohne Wertebereich, bei Indizes/Stufen leer
- `scale_type`, `direction`, `data_origin`, `temporal_type`: feste Wertelisten
- `scale_min`/`scale_max`: nur wenn von der Quelle genannt oder mathematisch fest
- `value_labels`: nur bei ordinal/binary/categorical, Format `0 = …; 1 = …`
- `reference`: Abschnitt, nicht Seite · `keywords`: 3–8, Deutsch und Englisch

Schema eingefroren bis 5 Quellen vollständig beschrieben sind. Neue Ideen in den Backlog.

## Leitfaden nach Notion

```bash
python3 scripts/agent/helpers/leitfaden_notion.py <lauf>   # erzeugt leitfaden_notion.md mit ausklappbaren Abschnitten
```
Die Übertragung auf die Notion-Seite der Quelle erledigt Claude im Chat. Danach den Lauf mit `--erledigt` abschließen.

## Dateien

| Datei | Zweck |
|---|---|
| `secretary.py` | Agent starten (Prompt mit allen Regeln) |
| `ask.py` | Einzelne Fragen an die DB stellen (nur lesen) |
| `check.py`, `review.py`, `apply.py`, `status.py` | Schritte 2 bis 4 und Überblick |
| `batch.py` | Mehrere Pakete einer Quelle nacheinander (feste Code-Listen, nichts doppelt) |
| `lib/tools.py` | Werkzeuge des Agenten (SQL nur lesend, Dateien, Download, PDF-Text) |
| `lib/selfcheck.py` | Werkzeug `self_check` (Auto-Prüfung für den Agenten) |
| `lib/checks.py` | Auto-Prüfung (Regeln v3, Belege, Datenauffälligkeiten) |
| `lib/sqlfile.py` | Liest Vorschlagsdateien (Texte, Zahlen, Listen, NULL) |
| `lib/decisions.py`, `lib/runs.py` | Entscheidungen (`review.json`) und Lauf-Ordner/Status |
| `lib/writer.py` | Schreibverbindung, nur für `apply.py` |
| `helpers/` | Einmal- und Hilfsskripte (Weltbank-API, Leitfaden → Notion) |

## Wenn etwas hakt

- `ModuleNotFoundError` → venv nicht aktiv: `source venv/bin/activate`
- SQL in der Shell getippt (`syntax error near unexpected token`) → `psql -d country_intelligence -c "…"`
- `apply.py` bricht ab → nichts ist passiert (Rollback). Meldung lesen, meist hilft `review.py` neu.
- Agent-Lauf zu teuer oder hängt → `--budget` und `--max-turns` begrenzen beides.
- Richtwert (WB, 10.11.): 25 Indikatoren ≈ 9 min, 2,14 USD, ca. 20 % eines 5-Stunden-Fensters im Pro-Abo.
