# Entscheidungen – Country Intelligence

**Stand:** 28.11.2026 · **ENTWURF**, alle Blöcke 15.05.–28.11. Aus Mai–Okt. stehen nur Entscheidungen, die heute noch gelten oder auf die spätere verweisen.

Hier steht, **was Julian entschieden hat**, mit Datum und Backlog-Bezug. Nicht hier: offene Arbeit (Notion-Backlog), Arbeitsregeln (`CLAUDE.md`, `docs/ARBEITSREGELN.md`), Loader-Pflichten (`docs/PIPELINE_STANDARD.md`), Zahlen zum Stand (DB). Je Thema in zeitlicher Reihenfolge. Eine abgelöste Entscheidung bleibt stehen und bekommt **„ersetzt durch …“**, damit alte Chat-Dokus lesbar bleiben. *Kursiv* = Vorschlag oder von Claude umgesetzt, nicht ausdrücklich entschieden.

Kürzel: `CI-123` und `#123` meinen denselben Backlog-Eintrag. Belege: Chat-Dokus in `kontext/chats/` (lokal).

## Meilenstein und Ausrichtung
- **10.07. Das Projekt ist eine Plattform, aus der Kurzprojekte wachsen**, kein abgeschlossenes Einzelprojekt. *Präzisiert am 10.11.*
- **10.07. International Relations als Encyclopedia-Domain bewusst zurückgestellt;** Economy, Population und Politics sind dokumentiert.
- **10.11. Neuausrichtung:** Die **Datenbank ist das Fundament** („etwas fürs Leben“), aktueller Fokus Aufräumen. Die **Plattform** (Frontend, API als Unterbau, später Suchmaschine) ist das Hauptziel, läuft aber als **Dauerspur ohne Frist**. **Kurzprojekte** (5–10 h) liefern Ergebnisse, Portfolio und Lernen. *Ersetzt „Sprint 2 hat Vorrang“ (10.07.) und die Definition of Done aus der Analyse vom 12.06.* Details: `kontext/dokumente/STRUKTUR_Plattform_Nebenprojekte_Skills.md`.
- **10.11. Karriere- und Weiterbildungsthemen** stehen nicht im Backlog, sondern in Julians Aufgaben-App.
- **15.11. Meilenstein „DB v1.0“** mit 6 Prüfpunkten (Ladefehler, Zuordnung, Struktur, Metadaten, dokumentierte Grenzen, Sicherung). **Ready heißt: jeder bekannte Fehler behoben oder als known_issue dokumentiert**, belegt durch `sql/03_queries/2026-11-15_readiness_check.sql`. Notion: Seite „🏁 Meilenstein DB v1.0“, Backlog-Eigenschaft „Meilenstein“.
- **15.11. Regel gegen das Nachwachsen:** Neue Befunde kommen nur in v1.0, wenn sie **Datenfehler in bereits geladenen Werten** sind.
- **23.11. Deadline DB v1.0 ist der 01.12.2026.**
- **24.11. Taxonomie (Domain → Category → Dimension) ist nicht Teil von v1.0.** Plattform-Thema, Prio B, wird weiterentwickelt, nicht neu gedacht. R3.3 ist seitdem nur Info. **Die DB ist maßgeblich, Notion folgt.**
- **25.11. Nach v1.0: Daten kennenlernen über Zusammenhänge** zwischen Konzepten, kombiniert mit der Vorbereitung auf DataCamp SQL Associate. Pilot **Demokratie × Wohlstand, Bolivien als Faden** (CI-184, CI-185). Kleine Themen (10–15 h, Schätzung) als Puffer, Quellenvergleich als Gegenprobe.
  - *Vorschlag in CI-184:* In dieser Phase schreibt **Julian das SQL, Claude prüft**.

## Arbeitsweise und Doku
- **05.11. Repo-Ordner nur für Code und Repo-Doku**; private Dateien liegen außerhalb (Repo ist öffentlich).
- **09.11. Der Notion-Backlog ist die einzige Liste offener Arbeit.** Chat-Dokus haben keine eigene Offen-Liste. Trennung: Backlog = Arbeit, `known_issues` = akzeptierte Daten-Fakten, Kommunikationsprotokoll = Regeln.
- **10.11. Chat-Dokus bleiben, aber kurz:** Entscheidungen, Korrekturen, Muster. Begründung: Die Chat-Suche liefert nur Ausschnitte, führt korrigierte Fehlaussagen mit und ist für Agenten und Claude Code nicht lesbar.
- **10.11. Arbeitsgrundsätze** (10 Punkte + Arbeitsrahmen) sind die Projekt-Anweisung. **Kurzfassung oben, Herkunft und Hilfsblöcke ans Ende. Fett subtil im Satz**, keine fetten Etiketten. Codewort **„mas corto“** = zu lang.
- **10.11. Backlog-Bereiche:** Daten, Agenten, Infrastruktur, Encyclopedia, Doku & Organisation, Plattform, Datenprojekte.
- **10.11. DB-Audit:** Teil 1–4, weitere Teile erst bei Bedarf.
- **11.11. Reden ist Standard:** Claude antwortet aus dem Bekannten, gearbeitet wird erst auf klare Ansage („mach“, „los“, „umsetzen“); vor größeren Aufgaben Umfang nennen und auf Okay warten.
- **11.11. Volumen sparen:** neue Session je Arbeitsblock, Änderungen bündeln, Dokumente nicht komplett neu schreiben, ungenutzte Verbindungen trennen. Anlass: Dauer-Chat 10./11.11. kostete rund 20 € Zusatzbudget.
- **14.11. Reihenfolge strikt einhalten, eins nach dem anderen.**
- **14.11. Lange Rechenschritte laufen als Befehl auf dem Mac** (#40), nicht über die Verbindung.
- **14.11. `README.md` und `PROJECT_CONTEXT.md` auf Englisch.** PROJECT_CONTEXT ohne Offen-Liste, mit Verweis auf den Backlog.
- **15.11. Ausgaben von Prüfläufen und Migrationen nach `logs/`** (`logs/readiness/`, `logs/migrations/`), nicht nach `scripts/agent/output/`. *Nicht durchgehend umgesetzt (Stand 28.11.), Aufräumen siehe Backlog.*
- **28.11. SQL-Rezepte direkt im Chat, mit Erklärung je Baustein.** Julian will SQL verstehen, nicht nur Ergebnisse. Kleine Rezepte werden nicht in Dateien abgelegt; Dateien nur für Prüfungen, Migrationen und wiederholte Abfragen.
- **28.11. Projektordner soll für Julian selbst lesbar sein:** eine klare Ablage für Ausgaben (Claude-Arbeitsdateien, Agenten-Läufe, Logs, Backups). Umsetzung im Backlog.

## Datenmodell und Struktur
- **15.05. Code-Konvention `QUELLE:ORIGINALCODE`** (z. B. `WB:NY.GDP.PCAP.CD`). **Nie eigene Codes erfinden**, immer den Originalcode behalten. *Der Präfix-Teil folgt seit 24.11. dem `short_code` des Datensatzes (siehe Metadaten).*
- **15.05. Kern-Tabellen:** `countries` (PK `iso_numeric`, ISO 3166-1) nur für stabile Fakten, Mehrfach- oder zeitabhängige Werte in eigene Tabellen. `indicators` im Long Format, SDMX-nah: `time_period` als TEXT, `obs_status` A/E/P/F, UNIQUE über (`iso_numeric`, `indicator_code`, `source_id`, `time_period`). Keine `regions`- und keine `update_log`-Tabelle.
- **25.05. Comtrade in zwei getrennten Strukturen:** Produkte (HS-4, alle Partner) und Partner. Kombinierte Aussagen nur als gekennzeichnete Annahme („based on aggregate distribution“).
- **25.05. API nach Blueprint:** erst Demography vollständig, dann verallgemeinern. **Subnationale Daten** (PostGIS) erst später, bis dahin Länderebene.
- **27.05. SIF (Societal Intelligence Framework) und „Country Intelligence Layer“ sind dasselbe;** SIF ist der ursprüngliche Name. Fachliche Grundlage: `kontext/dokumente/Final_Societal_Intelligence_Framework_V2.pdf`.
- **07.06. SIF v2 mit 10 Domains:** Education & Innovation und Infrastructure & Technology neu, Communication & Media aufgelöst (Pressefreiheit → Politics, Digitales → Infrastructure), Culture und Social Fabric zusammengelegt zu Culture, Society & Beliefs, History bleibt, Human Development aufgeteilt. Stand: `docs/SIF_DOMAIN_STRUCTURE.md`.
- **Juli. Tabelle oder Zeitreihe je Quelle bewusst entscheiden:** Ereignisdaten mit Akteuren und Kontext (UCDP, Coups, Verfassungsereignisse) → relationale Tabelle; einfache Land-Jahr-Zahlen (ACLED, GITOC, UNODC) → `indicators`. Relationale Tabellen bekommen `relational_table_metadata`; `v_all_metadata` fasst beides zusammen.
- **10.07. Im öffentlichen Repo steht nur die Struktur.** Analysen, SQL-Rezepte und Bolivien-Zahlen bleiben in der privaten Notion-Encyclopedia. Persönliche Daten nie ins Repo (27.05.).

## Metadaten und Benennung
- **09.11. Metadaten v2** (Migration): neue Felder in `indicator_metadata`, `sources`, `relational_table_metadata`; Tabelle `known_issues`; Sicht `indicator_coverage`.
- **09.11. Wissensebenen:** Katalog (Notion) → Quellen-Leitfaden → Indikator (DB). **Die Wahrheit liegt in der DB, Notion ist die Leseansicht.**
- **10.11. Metadaten v3:** Texte auf Englisch. Beschreibungen dürfen ersetzt werden (Sperre auf den gesehenen alten Wert). `description` = genau ein Satz, höchstens 200 Zeichen, hoher Wert = „mehr davon“. `unit` nur bei echten Maßeinheiten. Keine `processing`-Spalte, bewusste Verarbeitung → `known_issues`. Vorbild Our World in Data. Neu `key_info`, `producer_definition`, `value_labels`. Regeln stehen als Spaltenkommentare. **Schema eingefroren, bis 5 Quellen vollständig beschrieben sind.**
- **12.11. `description` sachlich mit gängigen Fachwörtern** (*prevalence*), ohne statistischen Jargon und ohne wertende Wörter (*clearly, too, poor*). Schwellen und Referenzstandard gehören in `key_info`.
- **14.11. `name` = offizieller Name der Quelle.** Die Rückverfolgbarkeit läuft über `indicator_code`, der nie verändert wird (Regel 15.05.). *Teilweise ersetzt am 24.11.: Präfixe wurden umbenannt (#84), der Teil nach dem Doppelpunkt bleibt Originalcode.*
- **14.11. `data_origin` Regel B** (#124, niedrige Priorität): Prüffrage „Beruht der Wert auf einer eigenen Beobachtung genau dieses Land-Jahres?“ Ja → Art der Beobachtung, nein → `model_estimate`. Nur wenn eindeutig, sonst leer. Begründung: Kein Skript liest die Spalte heute.
- **14.11. Sicherheitsstufe** eines Vorschlags = schwächstes Feld, `data_origin` zählt nicht mit (#125).
- **14.11. `static` nur für Eigenschaften ohne Zeitbezug.** Ein Stand einer Ausgabe bekommt das Jahr der Ausgabe (P19).
- **14.11. `indicator_catalog` ist nur noch ein Suchverzeichnis** für nicht geladene Indikatoren (CI-143). Ob er gelöscht wird, ist offen.
- **15.11. `indicators.source_id` ist `NOT NULL`.**
- **15.11. Readiness R4.2 folgt Metadaten v3:** Codes ohne `unit` zählen nur, wenn `scale_type` nicht `index`, `ordinal`, `binary` oder `categorical` ist.
- **15.11. Hofstede:** Code `HOFSTEDE:lto` bleibt.
- **19.11. `direction` bei Mengen:** Absolute Mengen sind `neutral`, Intensitäten (per_capita, per_gdp) behalten ihre Wertung. Werten nur, wo allgemein anerkannt.
- **23.11. `name` bleibt der offizielle Name**, auch wenn er sperrig ist (WHR „Explained by: …“). Ein kurzer Anzeigename ist eine Schemafrage für CI-157.
- **24.11. Präfix = Urheber, Bezugsweg ist Pflichtangabe** (in `loader_script` und `reference`). Laden über OWID ist für sekundäre Quellen in Ordnung. Quellenübersicht mit Originalquelle nach v1.0 (CI-157). *Ersetzt 19.11. „Präfix = Bezugsquelle“.*
- **24.11. `short_code` = Datensatz, Präfix = `short_code`** (#84): Ember → `EMBER`, `WEF:` → `WEF_GGGI:`, `FAO_FOOD:` → `FAO_FOOD_GRP:` (26 Codes), `CULTURE:` → `SAMAYO:`. Außerdem `EMBER:renewables_share_energy` → `EI`.
- **24.11. Namen:** `NOBEL:total` „(excl. Economics)“, `HENLEY:visa_free_total` „Destinations without a required visa (incl. e-visa and visa on arrival)“.
- **24.11. deprecated:** `WB:poverty_3_day` (Doppelung zu `SI.POV.DDAY`); COW intrastate/total bis nach v1.0.
- **24.11. ILO-Flags** als known_issue dokumentieren, die 366 Prognosewerte auf `F`; saubere Abbildung nach v1.0 (#32).
- **25.11. `FH:STATUS` ist `ordinal`.**

## Länderzuordnung (CI-105, CI-172, CI-177)
- **10.11. Ländercodes-Meilenstein (#105) zurückgestellt:** erst der Sekretär durch alle Quellen, dann ein Standard auf Basis der Befunde. 14.11. bestätigt („der Reihe nach“). *Überholt durch 15.11. und 24.11.: Die Länderzuordnung kommt zuerst ins Modul.*
- **14.11. V-Dem:** DEU 1945–48/BRD und „nur Punktschätzer“ sind `accepted`. Die verworfenen Einheiten (DDR, Kosovo, Gaza, Somaliland, Südjemen, Sansibar) werden über #105 gelöst.
- **15.11. Länderzuordnung allumfassend, mit klaren Regeln für historische Staaten.** Vom Modul kommt **zuerst nur die Länderzuordnung**.
- **15.11. Historische Staaten für v1.0 verwerfen**, dokumentieren und später als eigene Einheiten nachladen (**Weg A**, #105). Die beiden `to_fix`-Einträge (V-Dem, POLITY5) stehen auf `accepted` mit Verweis auf #105.
- **15.11. „Die Quelle bestimmt die Einheit“:** Ein Code, der einen heutigen Staat bezeichnet, kommt mit seiner ganzen Reihe (POLITY5: Deutschland mit Preußen und Reich). Polity-Verwerfen-Liste freigegeben, auch Äthiopien bis 1993, Pakistan 1947–1971, Sudan bis 2011.
- **24.11. Länderlisten als CSV je Quelle im Repo**, mit Spalten `von`/`bis` (1B). Eine DB-Tabelle kommt erst mit Weg A.
- **24.11. Weg für v1.0** (2B): Quarantäne, Sperre der 17 Loader, Modul-Pilot an FH und HENLEY, danach TI (aus der TI-Datei) und WHR neu. **P9 wird erst nach dem Pilot festgeschrieben.**
- **24.11. EPR wird nach v1.0 neu aufgebaut** (3B), alle drei EPR-Codes bis dahin in Quarantäne. **Kosovo wird bis Weg A verworfen** (4A).
- **25.11. „umsetzen“:** Modul `scripts/pipeline/lib/laender.py`, Listen und neue Loader für FH, HENLEY, TI, WHR, GITOC, FSI, KOF liegen im Repo. **Julian führt aus**, Reihenfolge laut `Claude outputs/AUSFUEHREN_2026-11-25.md`. FH 1982–1989 mit dem Endjahr, 1981 bleibt leer.
- **25.11. Die Löschmigration CI-163 bleibt `ENTWURF_`,** bis Julian die Listen geprüft hat. „umsetzen“ ist keine Freigabe zum Löschen.

## Loader, Pipeline-Standard und Nachladen
- **14.11. ILO:** DB auf den ILO-Stand bringen, zurückgezogene Werte löschen (sie bleiben im Backup).
- **14.11. Pipeline-Standard** in `docs/PIPELINE_STANDARD.md` als dem einen Ort für Loader-Pflichten. Abbruchkriterium: Nach 3 Fällen verschiedenen Typs (API, Datei, große relationale Daten) wird `scripts/pipeline/lib` gebaut. #110 enthält nur die offene Arbeit.
- **15.11. Der Pipeline-Standard ist Werkzeug, kein Ziel:** Nur Loader, die wegen eines Datenfehlers neu laden müssen, werden nach dem Standard neu geschrieben.
- **15.11. GHI nur Bericht 2025**, weil Werte laut Herausgeber nur innerhalb eines Berichts vergleichbar sind. „<5“ wird als 2,5 mit `obs_status` E gespeichert, dazu ein known_issue. **Ausgaben einer Quelle nicht mischen.**
- **15.11. CAF:** 4 Zeilen von Kanada auf Kolumbien 2011 umhängen, nicht löschen.
- **15.11. COMTRADE zurückgestellt:** Die relationale Tabelle braucht ein Konzept.
- **24.11. `FH:STATUS` laden** (mit CI-172/177). **`WB:SE.ADT.LITR.ZS` (#119)** nicht einzeln nachladen, sondern mit dem neuen WB-Loader (#106).

## Rohdaten und Backup
- **26.05. `data/raw/` gehört nicht ins Repo** (`.gitignore`). Loader und Rohdaten damals nach Domain-Ordnern sortiert; *für die Rohdaten ersetzt durch die Zielstruktur vom 14.11.*
- **11.07. Erstes vollständiges Backup** (DB-Dump und `data/raw` als tar.gz) nach Google Drive `CountryIntelligence/backups/`.
- **25.10. Umzug auf den Mac:** macOS, Homebrew, PostgreSQL 18.6, Python 3.14, Shell bleibt `/bin/bash` (Julian). Backups zunächst manuell. *Backup ersetzt am 14.11.*
- **14.11. Backup über Drive für Desktop,** wöchentlich Sonntag 20:00 per launchd (`scripts/backup_drive.sh`, `scripts/launchd/de.julian.ci-backup.plist`), das Skript löscht nichts, Rohdaten getrennt (#138). *Ersetzt 25.10. „Backups manuell“.*
- **14.11. Zielstruktur Rohdaten** (#135, noch nicht umgesetzt): Ablage flach nach Quelle `data/raw/<kürzel>/<version oder datum>/`, Belege in `data/reference/<kürzel>/`, Ungenutztes in `data/raw/_ungenutzt/`. Finden getrennt davon: Themen-Ansicht `data/nach_thema/` nur aus Verknüpfungen, `data/raw/INDEX.md` aus der Zuordnungsdatei. Begründung: Quellen wie die Weltbank gehören zu sechs Domains.
- **14.11. Verbrauchsprotokoll** (`usage_log.py`, Entwurf in `kontext/dokumente/ENTWURF_usage_log.md`): eine Datei `logs/usage.jsonl`, nicht in die DB. **Umsetzung verschoben.**

## Sekretär-Agent
- **05.11. Agenten-Architektur:** drei Rollen in einem Gerüst (`scripts/agent/`): **Sekretär** (Hygiene), **Quellen-Pfleger** (neue Versionen), **Unterstützer** (neue Quellen, lädt nie selbst). Reihenfolge in dieser Folge. Agenten bereiten vor, Julian führt aus. **Nicht alles braucht KI:** Zählen und API-Abfragen sind Skripte, KI nur für Urteil und Text.
- **05.11. Sekretär-Regeln:** jeder Befund mit Beleg, Stichprobe 10–15 vor Bulk, Abgleich gegen `known_issues`. Belege nur aus dem automatischen Protokoll.
- **05.11. DB-Rolle `ci_agent_readonly`** (SELECT auf 7 Schemas, `default_transaction_read_only = on`). Agent SDK und `claude -p` laufen über das Pro-Abo.
- **09.11. Prüfablauf:** Lauf (KI) → Auto-Prüfung (ohne KI) → Julians Prüfung (⚠️/UNSICHER + 3 zufällige ✅) → Übertragen per `apply.py` (Backup, Transaktion, Kontrolle). **Quellen-Leitfaden** (12 Abschnitte, Belege getrennt) statt Explainer.
- **10.11. Taste k** = Text übernehmen **und** Datenproblem nach `known_issues`. Nur **n** bei einer Stichprobe weitet auf alle übrigen ✅ aus. Faustregel: **j** Text und Daten stimmen · **k** Text stimmt, Daten auffällig · **n** Vorschlag selbst falsch. Ein leeres Feld ist kein Grund für n.
- **14.11. Sonnet ist Standardmodell des Sekretärs** (#126; 94 Sonnet-Vorschläge, 0 verworfen).
- **15.11. Lauf-Ordner `scripts/agent/output` sind für den Sekretär lesbar** (statt Leitfäden zu kopieren).
- **15.11. Leitfaden vor dem Loader, Metadatenlauf erst nach der Bereinigung**, sonst prüft der Sekretär gegen kaputte Daten.
- **15.11. Leitfäden WB, WID, UNDP, GITOC, ILO freigegeben.**
- **19.11. Leseordner `scripts/pipeline`**, damit der Sekretär die Loader sieht.
- **19.11. Leitfaden und Metadaten in einer Serie,** Review am nächsten Tag. Metadaten laufen nur nach einem Leitfaden mit `success` und `leitfaden.md`.
- **24.11. Der Agent schreibt den Kasten selbst** (`kasten.md`, jede Zeile mit Beleg, Zahlen „bei uns“ per Abfrage). Pilot vor Commit; 25.11. an COW, IGO, EPR gelaufen, *Claudes Empfehlung: abnehmen*.
- **25.11. Excel-Reader `table_to_text`** (#154) als Entwurf, **Fix in `checks.py` für PDF-/xlsx-Belege** freigegeben.
- *27.11. (von Claude umgesetzt, nicht committet, Abnahme in CI-187):* **Kasten-Regel verschärft:** Alte Befunde gelten als veraltet, Zustand bei uns im selben Lauf per Abfrage. Serien rufen `psql -X`. Budget EI/EMBER/EIA 1,0 USD.

## Notion
- **29./30.05. Encyclopedia in Notion** (Domain-, Category-, Dimension-Seiten, Bolivien als Anker mit SAM-Vergleich). *Seitenformat für Quellen ersetzt am 23.11.*
- **23.11. Datensatz-Seiten im neuen Format:** Der Leitfaden ist die Hauptseite. Oben ein **Kasten** (Was · Wer · Umfang · Art der Werte · Nutzung · Vorsicht), darunter Abschnitte 1–12, am Ende „Herkunft und Belege“. Entfallen: Coverage von Hand, Stärken/Schwächen, SQL-Rezept, Leitindikator, Statuszeile oben. „Umfang“ = Quelle laut Leitfaden + „Bei uns“ aus `docs/SOURCES_AVAILABLE.md` mit Stand-Datum. „Vorsicht“ nur bei echtem Fallstrick.
- **24.11. Alte Hauptseiten in den Papierkorb,** sobald die neue Seite steht (jeweils nach Bestätigung). Ältere Leitfäden vorher herausziehen.
- **24.11. UNESCO bekommt zwei Seiten** (WHC, ICH). **FAO ist zurückgestellt.** **Energie ist offen**; *Vorschlag: Leitfäden je Urheber (EI, EMBER, EIA), OWID Energy als Bezugsweg.*
- **28.11. Der Encyclopedia-Blueprint (Juni) ist durch dieses Format abgelöst** und liegt nur noch im Archiv.

## Quellenverzeichnis
- **10.11. `docs/SOURCES_AVAILABLE.md`** (aus dem DB-Inventar erzeugt, `scripts/gen_sources_available.py`) und **`docs/SOURCES_CANDIDATES.md`** (nicht geladene Quellen) ersetzen `SOURCES_ENCYCLOPEDIA.md` und `SOURCES_ROADMAP.md`. Prüfskript `scripts/check_sources.py`.

## Umzug auf Claude Code
- **05.11. Claude Code im Berechtigungsmodus Manual** (ob dauerhaft gesetzt, prüft #101).
- **27.11. Tarif Pro, kein Max; Standardmodell Sonnet** (`.claude/settings.json`).
- **28.11. Verbrauchsziel: Arbeit innerhalb des Pro-Kontingents, ohne Zusatznutzung.** Claude macht zu Beginn und am Ende jeder Session einen Verbrauchs-Check (Modell, Wochenstand aus `/usage` von Julian, Empfehlung für die nächste Session).
- **27.11. Private Inhalte nicht ins öffentliche Repo:** `Claude outputs/`, `CLAUDE.local.md` und `kontext/` stehen in `.gitignore`.
- **28.11. Proxmox-Server (Ubuntu, Claude Code) wird erst nach Abschluss des Umzugs ins Projekt integriert.** Bis dahin bleiben Mac und Mac-DB der Arbeitsort; vor dem Abschluss liefert Julian den Kontext zum Server.
- **28.11. Archiv `kontext/`** (lokal) mit dem Projektwissen aus claude.ai, nur zum Nachschlagen per `grep`. Maßgeblich sind `CLAUDE.md`, `docs/` und der Backlog.

---
Herkunft: Notion-Backlog CI-40 (Nachträge 11.11. und 14.11., in keiner Chat-Doku); Chat-Dokus 05.–25.11. in `kontext/chats/` (vollständig gelesen); Chat-Dokus 15.05.–25.10. und `kontext/dokumente/PROJEKT_STATUS_Phase1_Abschluss_2026-07-10.md` (Abschnitte zu Entscheidungen, Design, Lehren und Technik gelesen); claude.ai-Chats ohne Doku: „Agent-Lauf Fehler Leitfaden“ (26./27.11.), „Agenten-Auftrag Datenkontrolle“ (27.11.), „Umzug auf Claude Code“ (27.11.), „Proxmox-Server mit Ubuntu“ (27.11.); Abgleich mit `scripts/agent/secretary.py` (Kasten, Urheber).
