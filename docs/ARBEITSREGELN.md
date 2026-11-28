# Arbeitsregeln – Country Intelligence

**Stand:** 28.11.2026 · **ENTWURF**, von Julian noch nicht freigegeben.

Die Kurzfassung der Regeln steht in `CLAUDE.md` und wird bei jedem Start geladen. Hier steht das **Warum**: jede Regel mit ihrem **Anker-Fall** (Datum, Backlog-Nummer). Nachschlagen, wenn eine Regel unklar ist oder ein ähnlicher Fall auftritt. Alte Nummern aus dem Kommunikationsprotokoll (R1–R12, Fall 1–11) stehen in Klammern, damit Verweise in alten Chat-Dokus auffindbar bleiben. Quelle: `kontext/dokumente/KOMMUNIKATIONSPROTOKOLL_Claude_Julian.md` und die Chat-Dokus in `kontext/chats/`.

## 1. Zusammenarbeit und Rollen
- **Julian entscheidet, Claude schlägt vor, Schritt für Schritt** (1.1, R6). Keine großen, unaufgeforderten Blöcke oder Massenänderungen ohne Zwischenabstimmung. *Hat sich seit Mai über alle Sessions bewährt.*
- **Eine klare Empfehlung, begründete Kritik ist erwünscht** (1.10). *Anker: Die Entscheidung, International Relations zurückzustellen (10.07.), wurde geprüft und bestätigt statt reflexhaft mitgetragen.*
- **Julian fragen, wenn er es schneller kann** (R10, Fall 9). Reine DB-Abfragen, Dateilisten und Ausgaben als fertigen Befehl geben, mit einem Satz zum Warum. *Anker 15.11.: DB-Stand dreimal aus dem Dump gelesen (sechs Minuten) statt einer `psql`-Abfrage.*
- **Erklärungen zum Code erst im Code nachlesen.** *Anker 10.11.: Die Taste k in `review.py` aus dem Gedächtnis erklärt; laut `apply.py` tat sie das Gegenteil.*
- **Funde beim Erkunden ins Backlog, nicht sofort reparieren** („Handarbeit-Drift“). *Anker 05.11. und 25.11.: Aus Prüfen und Kennenlernen wird sonst wieder Säubern.*
- **Anthropic-Produktfragen gegen die aktuelle offizielle Hilfe prüfen.** *Anker 05.11.: „Agent-SDK-Guthaben auch für Pro“ war veraltet.*
- **Rollen in Claude Code:** Bisher galt „Claude führt nie aus“ (1.3, Mai–Juli), seit 05.11. „Julian gibt frei“. Was Claude Code selbst ausführen darf, regelt `CLAUDE.md` (Abschnitt Rollen und Rechte).

## 2. Belegte Zahlen und Ehrlichkeit
- **Tool-Ehrlichkeit** (R1, Fall 1): Kommt ein Tool-Aufruf leer zurück oder scheitert er, steht das ausdrücklich da. Nie mit Gedächtnis auffüllen und als „gelesen“ ausgeben. *Anker 10.07.: leere GitHub-Abfrage, Tabelle stammte aus alten Dokus.*
- **Jede Zahl hat eine Herkunft** (R7). Schätzungen heißen Schätzung. *Anker: „~7 Mio.“ lief wochenlang als Fakt, die Zählung ergab 12,7 Mio. (10.07.).*
- **Doku-Zahlen veralten am selben Tag.** Vor jeder Zahl aus einer Doku den aktuellen Stand abfragen. *Anker 12.11.: „52 Quellen“ aus der Doku vom Morgen, abends waren es 59. 14.11.: Juli-Werte in der README um Millionen falsch.*
- **Eigene Aussagen gegen die Datei zählen,** nicht gegen einen Prüfbericht. *Anker 11.11.: „Paket 1 kann so übernommen werden“, tatsächlich stand bei 16 von 27 NULL.*
- **Eine Ausgabedatei ist erst gelesen, wenn sie gelesen ist.** *Anker 11.11.: Die Comtrade-Zählung brach vorher und nachher ab; der Fehler stand in der Datei, ausgewertet erst am nächsten Tag.*
- **Was ein Skript nicht messen kann, gibt es nicht aus.** *Anker 14.11.: „Bestand Drive: 0 Dumps“ war eine verweigerte Abfrage, kein leerer Ordner.*
- **Aussagen aus dem Agenten-Text sind keine geprüften Fakten**, auch im Prüfbericht. *Anker 12.11.: „known_issues Nr. 3“ stammte nur aus dem Agenten-Text.*

## 3. Prüfen statt vermuten
- **Erst prüfen, dann „kein Zugriff“ sagen** (R2, Fall 2 und 3). Alle verfügbaren Wege durchgehen (Dateien, Tools, Integrationen). *Anker 10.07.: „kein GitHub-Zugriff“ behauptet, die Integration war verbunden.*
- **Erste Frage bei Auffälligkeiten: Ist das schon bekannt?** (R4, Fall 5 und 11) Backlog, `known_issues`, Chat-Dokus. *Anker: Gini mit 4 Ländern als „kaputt“ eingestuft, war geprüft und echt dünn (Juli); NaN bei UNDP als neu gemeldet, war #85 (15.11.); Gini erneut als „neu“ gemeldet (14.11.).*
- **Prioritäten aus Primärquellen ableiten, nicht aus Intuition.** *Anker 21.10.: Lernziele erst nach Auszählung von 21 echten Ausschreibungen festgelegt; mehrere Annahmen kippten.*
- **Plausible Erklärungen gegen einen Kontrollfall prüfen.** *Anker 10.11.: „Bolivien meldet verzögert an Comtrade“ klang schlüssig; erst Japan als bekannt vollständiger Melder zeigte den Ladefehler (#88).*
- **Kritisch nachfragen statt übernehmen** (1.4): fehlende Daten → Quellenlücke oder eigener Filter? Extreme Werte → Kontext recherchieren. Attraktive Narrative → gegen den SAM-Vergleich prüfen. *Anker Juni/Juli: UNODC-Gefängnisdaten „fehlten“ wegen eines Jahresfilters; Brasiliens ACLED-Tote waren überwiegend Polizeigewalt; „Bolivien als Kokain-Sonderfall“ hielt dem Vergleich nicht stand.*
- **Der Kontrollfall trennt Ladefehler von Quellenunterschied.** *Anker 11.11.: USA und DEU stimmen gegen die Weltbank, also liegt die Bolivien-Abweichung an den Quellen.*
- **Vor dem Einstufen die Originaldatei fragen.** *Anker 14.11.: Die Hälfte der V-Dem-Befunde war mit zwei Zeilen Python an der CSV geklärt. 15.11.: CAF „Columbia“ und GHI Kongo wären ohne Blick in die Rohdatei falsch gelöst worden.*
- **„Kein Loader im Repo“ erst nach einer Suche nach dem Rohdatei-Namen.** *Anker 14.11.: SIPRI hatte einen Loader unter anderem Namen.*
- **Eine installierte App ist noch kein Sync-Client; „nicht in /Applications“ heißt nicht „nicht installiert“.** Erst den Ort prüfen. *Anker 14.11.: Drive lief nur als Chrome-Web-App. 25.10.: VS Code lag dreimal im Download-Ordner.*

## 4. Erst lesen, dann schreiben
- **SELECT vor jedem schreibenden Statement** (R3, Fall 6). *Anker Juli: fast ein doppelter `INSERT INTO sources` für ACLED (id 140 existierte).*
- **Vor destruktiven Schritten auflisten, was betroffen ist, und bestätigen lassen** (R6). *Anker 07.06.: `allow_deleting_content` löschte alle Encyclopedia-Unterseiten, Rettung nur über den Papierkorb.*
- **Eine allgemeine Freigabe deckt kein Löschen.** *Anker 25.11.: Nach „umsetzen“ wollte Claude die CI-163-Löschmigration als „freigegeben“ markieren; abgelehnt.*
- **Eine beiläufige Zustimmung gilt nur für das, worauf sie sich bezieht.** *Anker 14.11.: „2-3 ist auch fein“ als Freigabe der ganzen Backlog-Liste gelesen.*
- **Backup vor BEGIN, ein vorhandenes Backup nie überschreiben.** *Anker 24.11.: Ein zweiter Testlauf hätte das Original-Backup der Quarantäne überschrieben → Sperre im Skript. 26.11.: Backup von `secretary.py` überschrieben, nur durch Rückwärtsanwenden gerettet.*
- **„Neu gleich alt“ ist der stärkste Beleg vor einem Löschen.** *Anker 15.11.: POLITY5 neu geladen, alle 92.439 Werte im Altbestand vorhanden; erst dann 101.643 Altzeilen gelöscht.*
- **Urteil je Altwert** (richtig / falsch / ohne Grundlage) zeigt das Ausmaß. *Anker 15.11.: Hofstede 144 zufällig richtig, 71 am falschen Land, 78 ohne Grundlage.*

## 5. Ursache statt Symptom
- **Muster beim ersten Auftreten benennen und dauerhaft lösen** (R5, Fall 4). *Anker Juni/Juli: Windows-Zeilenenden mehrfach einzeln gefixt, erst spät dauerhaft gelöst.*
- **NULL in UNIQUE + `DO NOTHING` = Verdopplung bei jedem Lauf.** Strukturelle Lösung: Spalte `NOT NULL`. *Anker 09.–15.11.: 684.365 Werte ohne `source_id`, GHI am 28.05. siebenmal geladen; Abschluss mit `source_id NOT NULL`.*
- **Eine Regel ohne Durchsetzung schützt nicht.** Sperre im Code und feste Prüfung gehören zur Regel. *Anker 24.11. (CI-172): P9 stand seit 15.11. im Standard, galt aber nur beim Anfassen eines Loaders; 12 Quellen betroffen.*
- **Strukturelle Sperre am Ende jeder Bereinigung**, damit das Muster nicht zurückkommt. *Anker 15.11.: `NOT NULL`; 24.11.: 17 Loader gesperrt.*
- **Bei einem Fund die Geschwister-Loader mitprüfen.** *Anker 24.11.: WHO und WHO-Quickwins, WB historical und WB infrastructure hatten jeweils denselben Fehler.*
- **Gleicher Fehlertyp in mehreren Loadern → Standard statt Einzelreparatur.** *Anker 10.11.: WB `DO NOTHING`, Hofstede-Codes, Comtrade-Codes → `docs/PIPELINE_STANDARD.md`.*
- **Eine DB-Korrektur ist erst fertig, wenn auch die Fehlerquelle im Loader korrigiert ist.** *Anker 23.11.: WEF pes/pos in der DB und in `load_gender_gap.py`.*
- **Umbenennungen brechen Code still.** Bei Namens- oder Schemaänderungen den Code nach den alten Werten durchsuchen. *Anker 10.11.: Nach SIF v2 lieferten API-Routen leer, ohne Fehler (#98).*
- **Pfade an eine Stelle.** *Anker 14.11.: Rohdaten nach Themen umsortiert, 31 von 45 Loader-Pfaden existierten nicht mehr (#135).*
- **Daten können still verschwinden.** Feste Prüfung der Quellenanzahl und Werte je Quelle gegen den letzten Stand. *Anker 10.11.: ND-GAIN und Olympics ohne Spur weg (#18).*

## 6. Pilot vor Standard
- **Neue Strukturen erst an wenigen echten Fällen** (R9, Fall 8). *Anker 09./10.11.: Metadaten v2 auf dem Papier entworfen → zweite Migration; v3 erst als Pilot an 10 Indikatoren aus 3 Quellen.*
- **Vorbilder suchen statt erfinden.** *Anker 10.11.: Beschreibungsformat von Our World in Data.*
- **Erst die Praxis recherchieren, dann die Regel festlegen.** *Anker 15.11.: Recherche zu historischen Staaten (ISO 3166-3, UNCTAD, QoG, COW) verbesserte die eigene erste Empfehlung.*
- **Neue Prüf- und Kontroll-SQL an einem kleinen Fall testen.** *Anker 11.11.: Eine Kontrolle, die selbst abbricht, sieht in der Kette aus wie Erfolg.*
- **Test-DB aus dem echten Dump, Erfolgs- und Abbruchfall.** *Anker 15.11.: Hofstede-Test traf die Zahlen des echten Laufs genau.*
- **Kontrollfall für jede neue Prüfung:** Testkopie mit absichtlich falscher Zahl. *Anker 24.11.: Kasten-Prüfung meldete 9.999 statt 1.591 korrekt.*
- **Prüfregeln und Schreibregeln nutzen dieselbe Definition.** *Anker 15.11.: R4.2 zählte jeden Code ohne Einheit als Fehler, obwohl Metadaten v3 bei Indizes keine verlangt.*

## 7. Nichts still schlucken
- **Ein leeres Ergebnis ist ein Befund.** *Anker 14.11.: WB-Abgleich, DB 0 gegen API 721 (#144).*
- **Leere Antwort mit HTTP 200 ist ein eigenes Fehlerbild.** Statuscode, Größe und Kopf ansehen. *Anker 14.11.: Die ILO-API (Cloudflare) lieferte Skripten ohne Browser-Kennung 0 Bytes; der Loader lud seit unbekannter Zeit nichts.*
- **Gespeicherte API-Antworten prüfen.** Eine Datei, die existiert, ist kein Beleg. *Anker 14.11.: Sechs WB-„Belege“ waren Fehlermeldungen (#137).*
- **Wiederholen nur bei vorübergehenden Fehlern** (5xx, Timeout), nie bei 4xx oder „archiviert“. *Anker 14.11.: jeder Fehler 4 × 90 s wiederholt, 485 min Laufzeit.*
- **Gefilterte Zeilen ins Log.** *Anker 11.11.: „World“ still gefiltert, richtig, aber unsichtbar.*
- **Kein stilles `continue`, kein `except: pass`, kein `2>/dev/null`.** *Anker 15.11.: GITOC verlor beide Koreas seit Mai durch `continue`; 14.11.: `2>/dev/null` verschluckte, warum launchd nichts fand; 25.11.: FH 1982–1989 still übersprungen.*
- **Ein Abbruch durch das Limit sieht aus wie ein fertiger Lauf.** *Anker 14.11.: GITOC-Lauf blieb auf „neu“ (#141).*

## 8. Datenarbeit
- **Neue Quelle: erst verstehen, dann laden** (1.5). Rohdaten-Struktur, Feldbedeutung, Methodik zu Ausgaben und Revisionen, Zielschema (Tabelle oder Zeitreihe) gemeinsam, dann Loader. *Anker 15.11.: GHI mischte 5 Berichtsausgaben.*
- **Metadaten sofort** (1.6), nie nachträglich.
- **Länderspezifisch bleibt länderspezifisch** (R11, Fall 10). *Anker 15.11.: WID-`method` stammte aus den DE-Metadaten, 24 `key_info`-Punkte machten daraus allgemeine Aussagen.*
- **Länderzuordnung: Heuristik hat viele Formen** (`search_fuzzy`, Paket `countrycode`, Teilstring, erste zwei Buchstaben). Nur exakt oder über eine ausdrückliche Liste, sonst Abbruch. *Anker: Hofstede Denmark → DE (10.11.), CAF Columbia → Kanada (15.11.), TI Niger → Nigeria (23.11.), WHR Mali ⊂ Somaliland (25.11.).*
- **Kürzel, die wie Standardcodes aussehen, sind die gefährlichste Form eigener Codes.** Feste Liste plus Namensprüfung. *Anker 15.11.: Hofstede BEN, CAF, MNG, SLV, MAC meinen andere Länder.*
- **Varianten je Ausgabe gehören in ausdrückliche Listen,** nicht in Normalisierung. *Anker 25.11.: GITOC Kommas, FH Berichtszeiträume, KOF alte Codes.*
- **Spuren statt Rohdaten:** Verwechslungspaare und „fehlt nur hier“ finden Fehlzuordnungen in allen Quellen mit zwei Abfragen. **Nicht-Länder** (Kosovo, Somaliland, Nordzypern) sehen sie nicht; die landen unsichtbar beim Nachbarn, das zeigt nur der Trockenlauf neu gegen alt. *Anker 24./25.11.*
- **Erste Zeile gewinnt bei `DO NOTHING`;** fehlender Dimensionsfilter vermischt still. *Anker 15.11.: WHO mischte Geschlecht und Altersgruppen (CI-174).*
- **Ein doppelter Ladelauf ohne Aufräumen ergänzt, statt zu korrigieren.** *Anker 25.11.: coups und Verfassungsereignisse doppelt (CI-163).*
- **Upsert-Zähler sind kein Zuwachs** (P13). *Anker 13./14.11.: „8,07 Mio. geschriebene Zeilen“ im Comtrade-Log, echter Zuwachs laut Zählung `trade_products` +2,47 Mio.*
- **Spaltennamen nie raten.** *Anker 14.11.: `sources.source_id` statt `id`, die ganze lesende Transaktion brach ab.*
- **`concat_ws` statt `||`**, wenn ein Teil NULL sein kann. *Anker 23.11.: `reference || …` hätte bei NULL den Text gelöscht.*
- **Zusammenhänge:** Skalenrichtung klären, Wohlstand als verdeckter Dritter, Land-Jahre nicht unabhängig. *Anker 25.11.: FH 1 = am besten, unbesehen ergibt das ein falsches Vorzeichen.*

## 9. Sekretär-Agent
- **Belege nur aus dem automatischen Protokoll,** nie vom Agenten formuliert. *Anker 05.11.: `ask.py` gab eine „wichtigste Abfrage“ an, die er nie ausgeführt hatte.*
- **Ein Hinweis gilt erst als befolgt, wenn das Protokoll es zeigt; vorher prüfen, ob das Werkzeug den Pfad erreicht.** *Anker 15.11.: Drei Läufe lang „Leitfaden zuerst lesen“, kein Lauf konnte ihn lesen (0 Treffer stand im Protokoll). 19.11.: derselbe Fehler mit `scripts/pipeline`.*
- **Leseregel und Prüfregel aus derselben Funktion.** *Anker 19.11.: Leseordner erweitert, Auto-Prüfung nicht → EDELMAN und FAO_FOOD fälschlich ❌.*
- **Eine Regeländerung betrifft Prompt, README und DB-Spaltenkommentare gemeinsam.** *Anker 14.11.: Der Agent liest die Kommentare als Regeln.*
- **Regeln für Textfelder brauchen ein Positiv-Beispiel.** *Anker 12.11.: „einfache Wörter“ ergab „clearly too heavy for their height“.*
- **Status im Lauf-Ordner ≠ Stand in der DB.** Gegenprobe per SELECT. *Anker 10.11.: „freigegeben“ als „übertragen“ gelesen.*
- **Lauf-Dateien nur vor dem Review ändern** (`apply.py` prüft einen Fingerabdruck). *Anker 12.11.*
- **Alte Läufe gegen den heutigen DB-Stand lesen.** *Anker 24.11.: Läufe vom 23.11. hätten den Bezugsweg aus CI-171 überschrieben; erst `review.py` zeigte es.*
- **Alte Befunde gelten als veraltet.** *Anker 26.11.: ILO-Kasten übernahm einen am 24.11. erledigten Befund.*
- **Grüne Auto-Prüfung ist kein Inhaltstest;** die Kasten-„Vorsicht“ an Loader und Rohdatei gegenprüfen. *Anker 25.11.: Die Vorsicht-Zeile fand den IGO-Ladefehler (CI-186).*
- **Ein Fehler wird gemeldet, nie umgangen.** *Anker 25./27.11.: MADDISON-SQL ohne Umlaute neu geschrieben, um einen Prüfabsturz zu umgehen.*
- **Neue Prüfung, neuer Absturzweg:** Jeder Dateityp, den der Agent als Beleg nennen darf, muss in der Prüfung abgefangen sein. *Anker 25.11.: PDF-Beleg brachte die Auto-Prüfung zum Absturz.*
- **Ein ⚠️-Zähler misst auch die Beschriftung; die Quelle bestimmt die ⚠️ stärker als das Modell.** Vor „viele ⚠️ = schlechter“ die Ursachen auszählen. *Anker 11.11.: „HOCH (…; data_origin MITTEL)“ ergab ✅; UNDP gut dokumentiert, PWT nicht lesbar.*
- **„MITTEL“ in Serie hat meist eine Ursache in Quellenlage oder Auftrag.** Einmal klären. *Anker 23.11.: FAO_FOOD 29 × MITTEL.*
- **„Ersetzt vorhandene Werte“ ist ein Hinweis, kein Fehler** (alte Loader-Werte können falsch sein). *Anker 25.11.*
- **Eine 403 beim Agenten heißt nicht, dass die Seite fehlt;** Claude kommt oft heran. **Methodik ohne Volltext markieren** (R12). *Anker 23.11. UNHCR; 15.11. ILOSTAT.*
- **Große Rohdaten (> ~50 MB) kann der Agent nicht summieren:** unabhängige Kontrolltabelle in den Referenzordner. *Anker 23.11.: UCDP.*
- **Vor einem Pilot prüfen, ob Definitionen in einem lesbaren Format vorliegen.** *Anker 14.11.: WHO-GHO liefert nur Code und Namen.*
- **Eingrenzen statt neu laufen lassen; ein Feld ohne Nutzer nicht pflegen.** *Anker 14.11.: `beschreibung.py` für Cent statt Neulauf; `data_origin` liest heute niemand.*
- **Kenngrößen eines Laufs von Anfang an ins Protokoll; Modellvergleich nur auf demselben Quellentyp.** *Anker 11.11.: Modell zwei Tage lang nicht protokolliert.*
- **Einzelpakete sind teuer,** feste Kosten dominieren. *Anker 14.11.: 0,30 USD für 1 Indikator.*

## 10. Notion
- **Nach dem Schreiben neu abrufen** (R8, Fall 7). *Anker 10.11.: „1. Titel“ wurde zur Liste, Codes zu falschen Links.*
- **Dateinamen, Codes und Pfade in Backticks, auch in Properties; nie Dateinamen in Titeln; `$` maskieren.** *Anker 23.–24.11.: vierter Fall falscher Links; `$…$` als Formel gesetzt; `load_coups.py` im Titel von CI-180.*
- **Den richtigen Eintrag adressieren, nicht die Datenbank.** *Anker 14.11.: Schreibvorgang an die Backlog-Datenbank statt an #135.*
- **Eine Suche ohne Treffer ist kein Beleg,** erst `fetch` zeigt den Stand. *Anker 12.11.: GINI-Satz stand trotz Suche weiter auf der Seite.*
- **Leitfaden vor dem Löschen herausziehen; bestehende Seiten umbauen statt neu erzeugen,** wenn dort Nachträge nur in Notion stehen. *Anker 24.11.*
- **Kontextbudget:** Ein voller Seitenabruf kostet 8–15 Tsd. Token, höchstens etwa 8 Seiten je Session. *Anker 24.11.*

## 11. Terminal und Technik
- **Neue Befehle in einem Halbsatz erklären:** was sie tun, wo sie laufen. *Anker 05.11.: Julian landete regelmäßig in der falschen Ebene (Shell, psql, Python).*
- **Pager aus:** `git --no-pager …`, `\pset pager off` in `~/.psqlrc`; **in Skripten `psql -X`** (die `.psqlrc` schreibt Text vor Ergebnisse). *Anker 15.11.: in `less` gelandet, eingefügter Text startet dort Befehle; 26.11.: „Pager-Verwendung ist aus.“ vor der Zahl brach eine Prüfung.*
- **`2>&1` bei psql-Ausgaben in Dateien.** *Anker 10.11.: Abbrüche sahen aus wie leere Abschnitte.*
- **`python3 -u`, wenn die Ausgabe durch `tee` geht; interaktive Skripte nie durch `tee`.** *Anker 14.11.: stundenlang keine Ausgabe; 24.11.: `apply.py | tee … || break` hätte die Ja-Abfrage gepuffert.*
- **venv:** Prompt ohne `(venv)` plus `ModuleNotFoundError` → `source venv/bin/activate`. Skripte mit `python3 scripts/…` starten. *Anker 09.11. und 14.11.*
- **Befehle mit `&&` verketten, vor Folgebefehlen den Zwischenstand abfragen.** *Anker 25.10.: zusammengeklebte Zeilen, ein `mkdir` nicht ausgeführt.*
- **Keine ausführbaren Platzhalter.** *Anker 14.11.: `"<eingefügter Pfad>"` wurde wörtlich angelegt.*
- **Zeilenenden erhalten** (`file` prüfen, danach Diff-Bilanz). *Anker 14.11.: README von CRLF auf LF (332 Zeilen Diff); 24.11.: `load_cpi.py`.*
- **Hintergrundprozesse haben auf macOS andere Rechte:** jeden Zeitplan über `launchctl start` testen. `pgrep` findet auch den eigenen Befehl. *Anker 14.11.*
- **macOS-bash 3.2:** leeres Array unter `set -u` bricht ab. *Anker 14.11.*
- **Server langsam ≠ kaputt;** bei geänderter Schnittstelle zuerst die offizielle Client-Bibliothek lesen. *Anker 10.11.: `Reporters.json` 19 s; 14.11.: ILO-Aufruf stand im R-Paket Rilostat.*
- **Fortsetzbare Läufe:** Daten (Cache) und Prüfstand trennen, den DB-Stand jedes Mal neu lesen. Lange Läufe mit `caffeinate -i`. *Anker 14.11.: WB-Abgleich meldete #3 aus dem Cache als offen.*
- **Grenzwerte an den echten Dateien messen.** *Anker 26.11.: Kappung 50.000 Zeilen hätte bei MADDISON die USA abgeschnitten; KOF hat CSV-Zeilen mit 180.604 Zeichen.*

## 12. Schreiben
- **Kurzfassung oben,** sonst nur Datum und Status; Herkunft, Belege, Methode ans Ende. *Julians Wunsch 10.11.*
- **Fett subtil mitten im Satz** auf den tragenden Wörtern, keine fetten Etiketten. Codewort **„mas corto“** = zu lang. *10.11.*
- **Terminologie: Domain → Category → Dimension.** Ein Fehler wird sofort projektweit korrigiert. *Anker Juli: „Sub-Category“ an 27 Stellen.*
- **Bei Frustration Klarheit statt Aufmunterung** (1.10).

## 13. Verbrauch
- **Rechnerische USD ≠ Abo-Verbrauch;** Planungswerte als Schätzung. *Anker 10./11.11.*
- **Langer Chat = teure Folgeantworten,** neues Thema = neue Session. *Anker 10./11.11.: Dauer-Chat mit 252 Anfragen kostete rund 20 € Zusatzbudget; 60 % Grundanweisungen, 14 % Mac-Dateien und Befehle, 9 % Projektwissen, 7 % Notion (96 Aufrufe), 7 % Gespräch (CI-40).*
- **Reden ist Standard, Arbeit auf Ansage;** Änderungen bündeln, Dokumente gezielt ändern, ungenutzte Verbindungen trennen (11.11.).
- Details und Messweise: `CLAUDE.md`, Abschnitt Verbrauch und Modellwahl.

---
**Nicht übernommen** (galt nur für frühere Arbeitswege): WSL2-Eigenheiten (`^M`, `dos2unix`, manueller Postgres-Start), Projektwissen-Suche für CSVs (R2-Zusatz), Übertragen per `device_commit_files` mit Prüfsumme, DB-Stand aus dem Dump lesen. In Claude Code arbeitet Claude direkt im Repo.

Herkunft: `kontext/dokumente/KOMMUNIKATIONSPROTOKOLL_Claude_Julian.md` (Stand 10.07., Nachträge 10.11. und 15.11.), Abschnitte „Muster“ und „Korrekturen“ aller Chat-Dokus 15.05.–26.11. in `kontext/chats/`, claude.ai-Chats 26./27.11. ohne Doku.
