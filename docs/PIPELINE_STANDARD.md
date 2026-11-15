# Pipeline-Standard (Entwurf)

**Stand:** 15.11.2026 (spätabends) · **Status:** Entwurf, wächst an echten Fällen · Offene Arbeit: Notion-Backlog #110

Dieses Dokument ist der eine Ort für den Loader-Standard. Hier steht, was jeder Loader in
`scripts/pipeline/` können muss und warum. Jede Pflicht hat einen Beleg: einen Fall, in dem
ihr Fehlen Schaden angerichtet hat, oder eine Entscheidung von Julian. Der Backlog-Eintrag
#110 führt nur die offene Arbeit.

## 1. Vorgehen

1. **Fälle sammeln:** Loader, die ohnehin angefasst werden, nach dem aktuellen Entwurf neu
   schreiben. Jeder Fall bekommt einen Abschnitt in Teil 5 (was er gelehrt hat).
2. **Abbruchkriterium:** Nach **3 Fällen verschiedenen Typs** wird das gemeinsame Modul
   `scripts/pipeline/lib` gebaut, nicht erst nach allen Backlog-Punkten.

   | Typ | Fall | Stand |
   |---|---|---|
   | API | ILO (`load_ilostat.py`) | erledigt 14.11. |
   | Datei (Excel/CSV) | GHI (`load_ghi.py`) | erledigt 15.11. |
   | Datei (Excel/CSV), zweiter Fall | POLITY5 (`load_polity5.py`) | erledigt 15.11. |
   | Datei (CSV), dritter Fall | Hofstede (`load_hofstede.py`) | Code 15.11., Lauf bei Julian offen |
   | Große relationale Daten | Kandidat: Comtrade (#88) | offen |

3. **Danach:** übrige Loader beim Anfassen auf das Modul umstellen, nicht in einer Massenaktion.
   Abhängig davon: Ländercodes (CL-105), Rohdaten-Umzug (#135).

## 2. Pflichten je Loader (Entwurf)

Belegt durch einen Fall (Teil 5) oder eine Entscheidung (Teil 6). „ILO“ = hat sich im
ILO-Loader bewährt.

**Abruf und Rohdaten**
- P1 **Rohdaten speichern** nach `data/raw/<quelle>/<datum>/`, bevor irgendetwas geprüft wird. Die DB lässt sich so jederzeit gegen eine Lieferung prüfen. (ILO)
- P2 **0 Bytes / 0 Zeilen sind ein Fehler**, kein leeres Ergebnis. HTTP 200 allein beweist nichts. (ILO, Comtrade)
- P3 HTTP-Abruf mit User-Agent, Zeitlimit und bis zu 3 Versuchen bei Verbindungsfehlern. (ILO)
- P4 Kein fester Pfad im Loader; Pfad über eine Zuordnungsdatei im Modul (Kürzel → Ordner, Version, Loader). (Inventur #134)

**Prüfen vor dem Schreiben**
- P5 **Zwei Stufen:** `--trocken` lädt, speichert, prüft und vergleicht mit der DB, schreibt nichts. Geschrieben wird nur aus gespeicherten, geprüften Rohdaten (`--rohdaten DATUM`). (ILO)
- P6 **Vergleich mit der DB je Indikator:** neu / Wert geändert / nur Status geändert / gleich / nur in DB. (ILO)
- P7 Pflichtspalten **je Datensatz**, nicht pauschal; Spalten, nach denen gefiltert wird, müssen da sein. (ILO)
- P8 **Genau eine Zeile je Land, Indikator, Jahr** nach dem Filter, sonst Abbruch. (ILO; NULL-Dubletten #1)
- P9 Nicht zugeordnete Länder **namentlich** ausgeben, Aggregate zählen, nichts still verwerfen. (ILO, V-Dem, CL-105)
  **Keine unscharfe Suche** (`pycountry.search_fuzzy` o. Ä.): nur exakter, normalisierter Name (Akzente, `&`, Apostroph) oder eine ausdrückliche Liste Name → ISO3. Fehlt ein Land, Abbruch mit Namensliste. (CAF „Columbia“ → Kanada, GHI)
  **Codes der Quelle nur über eine vollständige, ausdrückliche Liste** (Quell-Code → ISO3 oder → verwerfen mit Grund), keine Kette aus Paket + Ersatztabelle. Ein Code, der in keiner Liste steht → Abbruch. **Die Quelle bestimmt die Einheit:** Führt sie einen Staat nach Teilung/Vereinigung unter neuem Code, ist das eine eigene Einheit und wird nicht auf das heutige Land gelegt (bis CL-105 historische Einheiten kennt: verwerfen, dokumentieren). (POLITY5, 5.3)
- P10 Nicht numerische Werte und nicht jährliche Zeitangaben → Fehler mit Beispiel, kein `except: pass`. (ILO; Freedom House, Comtrade)

**Schreiben**
- P11 **Alles oder nichts:** ist ein Indikator fehlerhaft, wird nichts geschrieben. Eine Transaktion. (ILO)
- P12 `ON CONFLICT … DO UPDATE`, nie `DO NOTHING`. (WB #106, ILO)
- P13 **Beim Schreiben „geändert“ und „unverändert“ getrennt zählen**, wie im Trockenlauf. `RETURNING (xmax = 0)` allein trennt nur neu/vorhanden; „aktualisiert“ umfasst sonst alle vorhandenen Zeilen (ILO, siehe 5.1). **Lösung (GHI, 5.2):** `DO UPDATE … WHERE indicators.value IS DISTINCT FROM EXCLUDED.value OR indicators.obs_status IS DISTINCT FROM EXCLUDED.obs_status` plus `RETURNING (xmax = 0)`: unveränderte Zeilen werden nicht berührt und nicht zurückgegeben.
- P14 **Werte, die die Quelle nicht mehr liefert, löscht der Loader nicht.** Er meldet sie; gelöscht wird per Migration mit Liste (Teil 3). (ILO)
- P15 `source_id` aus `sources` holen; **fehlt die Quelle oder fehlen Metadaten → Abbruch**, nichts anlegen. Name, Einheit, Hierarchie nur in `indicator_metadata`, der Loader überschreibt sie nicht. (ILO, #1, WB-Infrastruktur/#98)
- P16 `sources.loaded_at` und `loaded_version` setzen. (ILO; Befund: bei den meisten Quellen leer)
- P17 `indicator_coverage` nach dem Laden auffrischen.
- P18 `obs_status` wie geliefert (leer → `A`); Flags und Prognosen regelt #86.
- P19 `time_period`: `static` nur für Eigenschaften ohne Zeitbezug, sonst das Jahr der Ausgabe (Entscheidung Julian 14.11., Spaltenkommentar).

## 3. Muster für Daten-Migrationen (Löschen, Bereinigen)

Bewährt in `sql/05_migrations/2026-11-14_ilo_bereinigung.sql`:

1. Vorher **Backup** der betroffenen Zeilen als CSV nach `backups/` (eigene, nur lesende Datei).
2. Aufruf mit `psql -v ON_ERROR_STOP=1`, alles in `BEGIN … COMMIT`.
3. **Kontrollzahlen vorher** in einem `DO`-Block: weicht eine Zahl ab → `RAISE EXCEPTION`, nichts ist geändert.
4. Löschlisten als CSV per `\copy` in eine `TEMP TABLE … ON COMMIT DROP`; löschen **nur bei unverändertem Wert** (`i.value = z.value_db`).
5. **Kontrollzahlen nachher** im zweiten `DO`-Block, sonst Abbruch.
6. `REFRESH MATERIALIZED VIEW indicator_coverage` im selben Skript.
7. Danach den Trockenlauf des Loaders wiederholen: überall nur „gleich“.

## 4. Vorgehen bei kaputter Quelle

- Erst den **Antwort-Kopf** ansehen (`curl -sS -D kopf.txt`), nie `curl -s` ohne Statuscode und Größe.
- Bei geänderter Schnittstelle zuerst die **offizielle Client-Bibliothek** der Quelle lesen (ILO: R-Paket Rilostat). Dort steht der gültige Aufruf.
- Gegenprobe mit einem zweiten Weg (ILO: SDMX), bevor man eine Ursache festschreibt.

## 5. Fälle

### 5.1 ILO, 14.11.2026 (Typ API) · Commit `ca638f6`

**Ausgangslage:** 9 Indikatoren, 22.280 Werte unter `source_id` 59, dazu 56.398 Dubletten ohne
`source_id` aus einer Juni-Fassung (#1). Bei Analysen immer wieder ein Hindernis.

**Befunde**
- Die ILO-Schnittstelle (rplumber, hinter Cloudflare) liefert Skripten ohne Browser-User-Agent
  **HTTP 200 mit 0 Bytes**. Der alte Loader schrieb dann „0 raw rows“ ins Log und lief weiter –
  er lud seit unbekannter Zeit still nichts. → P2, P3
- Alter Loader: `DO NOTHING` (Reload änderte nichts), keine Rohdaten, legte Quelle und
  Metadaten selbst an, verwarf nicht zugeordnete Länder still. → P1, P9, P12, P15
- ILO-Dateien haben je Datensatz verschiedene Spalten (`classif1`, `sex`, `obs_status` fehlen
  teils). Die erste, pauschale Spaltenprüfung schlug bei 3 von 9 an. → P7
- Verdacht „mehrere Erhebungen je Land-Jahr“ widerlegt: Die ILO liefert je Land-Jahr eine Zeile.
  Die Prüfung P8 bleibt trotzdem Pflicht.
- Abgleich mit der DB: seit Juni **351 Werte geändert** (darunter 4 Werte genau 4-mal zu hoch,
  z. B. Ghana 2024 50,5 Mio. statt 12,6 Mio. Erwerbstätige), **259 neu**, **291 zurückgezogen**.
  → P6, P14
- Zählfalle: „21.989 aktualisiert“ statt der erwarteten Zahl geänderter Werte, weil `DO UPDATE`
  jede vorhandene Zeile berührt. → P13
- Nicht zugeordnet: `KOS` (Kosovo; V-Dem nutzt `XKX`), `ANT`, `CHA` → CL-105.

**Ergebnis:** `load_ilostat.py` neu, DB = ILO-Stand 14.11. (22.248 Werte, 0 ohne `source_id`),
Backup `backups/2026-11-14_ilo_indicators_vorher.csv`, Belege in
`scripts/agent/output/2026-11-14_ilo/`. Noch nicht umgesetzt: P13 (Zählung beim Schreiben).

### 5.2 GHI, 15.11.2026 (Typ Datei) · Backlog #1

**Ausgangslage:** 6.535 Werte ohne `source_id`, 1.618 Land-Jahre, bis zu 6 Zeilen je Land-Jahr.

**Befunde**
- 7 Loader-Läufe am 28.05. innerhalb von 13 Minuten. Ohne `source_id` greift UNIQUE nicht, `DO NOTHING`
  fügte bei jedem Lauf alles neu ein. Dasselbe Muster in 6 weiteren Loadern (#1). → P12, P15
- Der Loader mischte 5 Berichtsausgaben in einem dict; das OWID-Archiv (Bericht 2021) kam zuletzt und
  überschrieb die neueren Berichte (z. B. DR Kongo 2000: DB 50,6, Bericht 2025 46,1). 103 von 493 Werten
  wichen vom Bericht 2025 ab. GHI ist laut Herausgeber nur **innerhalb eines Berichts** vergleichbar.
  → neue Regel: Methodik der Quelle zu Ausgaben/Revisionen prüfen, Ausgaben nicht mischen.
- „<5“ wurde still zu 2,5. Jetzt 2,5 mit `obs_status` E und known_issue. → P18
- Ländernamen per `pycountry.search_fuzzy`; derselbe Ansatz machte bei CAF aus „Columbia“ Kanada. → P9
- Datei-Format kann sich je Ausgabe ändern (Spaltenjahre 2007/2008, 2015/2016). → Kopfzeile prüfen (P7).

**Ergebnis:** `load_ghi.py` neu (Trockenlauf als Standard, `--schreiben`, Kopfzeilen-Prüfung, 17 ausdrückliche
Zuordnungen, Abbruch bei fehlendem Land, P13-Zählung, `loaded_version` mit sha256 der Datei, Coverage-Refresh).
DB: 493 Werte (Bericht 2025: 2000/2008/2016/2025), Migration `sql/05_migrations/2026-11-15_ci1_migration2_ghi.sql`,
Backup `backups/2026-11-15_ci1_null_vorher.csv`. Offen für das Modul: Dateipfad noch als Konstante (P4, #135).

### 5.3 POLITY5, 15.11.2026 (Typ Datei) · Backlog #1, #89

**Ausgangslage:** 101.643 Werte ohne `source_id`, 569 Land/Code/Jahr-Paare doppelt, 3.216 Sondercodes
(-66/-77/-88) als Werte in democ, autoc, xconst, polcomp.

**Befunde**
- Länderzuordnung über das Paket `countrycode` plus Ersatztabelle `COW_FALLBACK`. Wo das Paket nichts fand,
  griff die Tabelle mit **geratenen ISO-Codes**: Baden → Barbados (BAD→BRB), Modena → Moldau, Sardinien →
  Saudi-Arabien, Parma → Panama, Zentralamerika (UPC) → Uganda. Dasselbe Muster wie Hofstede (#102). → P9
- DDR und BRD beide → DEU, Nord- und Südjemen → YEM usw. Polity selbst führt bei Teilung/Vereinigung
  **neue Einheiten mit eigenem Code** (Handbuch v2018, Anhang A); die Quelle hat in Grenzjahren
  (DEU 1945 und 1990, Äthiopien 1993) zwei Einheiten. Zusammenlegen erzeugt Dubletten. → P8, P9
- Sondercodes nur bei polity2 ausgeschlossen. Polity ersetzt sie in polity2 selbst; in den übrigen Codes
  sind sie keine Skalenwerte. → nicht laden, je Code zählen, known_issue.
- Der Sekretär kann `.xls` nicht lesen: Leitfaden ohne Länder-Stichprobe; die Prüffragen wurden direkt an
  der Datei beantwortet (Backlog-Eintrag 15.11.).
- Kontrolle: Alle 92.439 neuen Werte waren gleich dem Altbestand (kein Wert verschoben, nur aufgeräumt).

**Ergebnis:** `load_polity5.py` neu (feste Liste: 166 scodes → ISO3, 28 verworfen mit Grund; Abbruch bei
unbekanntem scode und bei Überlappung; Trockenlauf mit Verworfen-Liste und CSV des Altbestands ohne
Entsprechung; P13-Zählung; `loaded_version` mit sha256). Migration
`sql/05_migrations/2026-11-15_ci1_migration3_polity5.sql` (101.643 gelöscht, 3 known_issues), danach
`indicators.source_id` NOT NULL (`2026-11-15_indicators_source_id_not_null.sql`). Getestet an einer Test-DB
mit den echten Altzeilen: zweiter Schreiblauf „92.439 unverändert“, Migrationen brechen vor dem Loader und
beim zweiten Lauf ab.

### 5.4 Hofstede, 15.11.2026 (Typ Datei) · Backlog #102

**Ausgangslage:** 293 Werte (6 Codes, 60 Länder, `time_period` 'static'). Der Sekretär hatte am 10.11. beim
Format-Pilot gemeldet, dass die Werte an falschen Ländern hängen.

**Befunde**
- Die Datei hat **eigene Kürzel** (Spalte `ctr`), keine ISO-Codes. Der alte Loader fand keine ISO-Spalte
  und nahm still die **ersten 2 Buchstaben des Ländernamens** als ISO2 (Denmark → DE, Bangladesh → BA = Bosnien,
  Arab countries → AR = Argentinien). Mit `DO NOTHING` gewann die erste Zeile je Präfix. → P9, P12
- Abgleich Altbestand gegen die Datei: **144 zufällig richtig, 71 am falschen Land, 78 bei Ländern ohne Wert in
  der Quelle** (z. B. Bolivien, Afghanistan, Guam). 12 Länder hatten Werte, obwohl die Quelle für sie gar keine hat;
  53 Länder der Quelle fehlten ganz (u. a. USA, Japan, China). Nach dem Neuladen: 461 Werte, 101 Länder.
- **Kürzel, die wie ISO3 aussehen, aber ein anderes Land meinen:** BEN (Belgien flämisch, nicht Benin), CAF
  (Kanada französisch, nicht Zentralafrika), MNG (Montenegro, nicht Mongolei), SLV (Slowenien, nicht El Salvador),
  MAC (Nordmazedonien, nicht Macau). Eine Zuordnung „Kürzel = ISO3, wenn vorhanden“ wäre still falsch gewesen.
  → neue Regel: **die feste Liste prüft zusätzlich den Namen**; abweichender Name → Abbruch.
- Datei enthält 3 Regionen und 7 Teilgruppen eines Landes (Belgium French, South Africa white …). → verwerfen
  mit Grund, known_issue.
- Zwei Fassungen auf der Website (ohne Begrenzung und „0-100“). Geladen ist die Hauptfassung wie bisher. → known_issue.
- Kein Erhebungsjahr: `time_period` '2015' = Ausgabe (P19).

**Ergebnis:** `load_hofstede.py` neu (feste Liste 101 Kürzel → ISO3 mit Namensprüfung, 10 verworfen mit Grund,
Kopfzeile exakt, Werte ganzzahlig 0–120, P13-Zählung, `loaded_version` mit sha256, Trockenlauf mit Urteil je
Altwert als CSV). Migration `sql/05_migrations/2026-11-15_hofstede_neu.sql` (293 Altzeilen nach Liste und Wert
gelöscht, 3 known_issues, Nachher-Stichproben DEU/DNK/USA). Getestet an einer Test-DB aus dem Backup 14.11.:
Migration bricht vor dem Loader und beim zweiten Lauf ab, zweiter Trockenlauf „461 gleich“, Abbruch bei
falschem Namen, unbekanntem Kürzel und Wert außerhalb des Bereichs.

## 6. Befunde aus der Bestandsaufnahme (aus #110 übernommen, Stand 14.11.)

- 10.11.: 16 Dateien in `scripts/pipeline` mit eigener Verbindungsfunktion, kein gemeinsames
  Modul. WB-Loader mit `DO NOTHING` (Ursache #106), Hofstede #102, Comtrade #88. Comtrade hat
  keinen Eintrag in `sources` und keinen in `relational_table_metadata` (SELECT 10.11. leer).
- 14.11.: `load_wb_infrastructure.py` setzt bei `ON CONFLICT` domain/category/dimension mit
  SIF-v1-Namen ('Economy & Infrastructure') → jeder Reload schreibt alte Domain-Namen zurück
  (Muster wie #98). → P15; zentrale Taxonomie #103.
- Inventur 14.11. (#134, `docs/RAW_INVENTUR_2026-11.md`): 31 von 45 in Loadern genannten
  Rohdaten-Pfaden existieren nicht, 2 Loader mit festem Linux-Pfad, 10 Loader erwarten die
  Datei als Argument. → P4. Zielstruktur (flach nach Quelle, Zuordnungsdatei, Themen-Ansicht,
  `INDEX.md`) von Julian entschieden, Umsetzung #135.
- `sources.loaded_version`/`loaded_at`: nur bei wenigen der 59 Quellen befüllt (u. a. CCP v6,
  MARPOR 2025a, DDR). → P16
- Regel `time_period` (Julian 14.11., aus #87): umstellen beim Anfassen: HOFSTEDE (6, Ausgabe
  2015, mit #102: umgesetzt in `load_hofstede.py`, Fall 5.4), HENLEY (4), WEF GGGI (5, aus QoG Jan 2025), GLOTTOLOG (3, v5.3),
  SAMAYO avg_male_height. Später denkbar: Eigenschaften ohne Zeitbezug in eigene Länder-Tabelle
  (Julian: vorerst nicht). → P19
- Ursprünglicher Modul-Entwurf (#110): `scripts/pipeline/lib` mit db, http (Retries +
  Rohdaten-Cache), registry (source_id holen, abbrechen statt anlegen, loaded_at setzen),
  Logging nach `logs/`. Lauf-Protokoll vorerst nur Log-Dateien, Tabelle `pipeline_runs` erst
  nach 2–3 Loadern. Bezug: #1, #14, #69, #70, #71, #81, #100, #24.
