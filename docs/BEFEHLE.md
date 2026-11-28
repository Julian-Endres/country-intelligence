# Befehle – Country Intelligence

**Stand:** 28.11.2026 · **ENTWURF.** Jeder Befehl ist gegen den Code geprüft (Skriptkopf, `argparse` bzw. `sys.argv`, Kopf der SQL-Datei). Wo etwas nur aus einer Chat-Doku stammt, steht es dabei.

**Platzhalter:** `<lauf>`, `<datei>` usw. vor dem Ausführen durch den echten Namen ersetzen. Bleiben sie stehen, liest die Shell `<` als Umleitung und bricht ab; es passiert nichts. Wo ein Befehl schreibt, stehen stattdessen Variablen mit Prüfung.

**Wo läuft was:** *Shell* = Terminal auf dem Mac, im Repo-Stamm `~/Projekte/country-intelligence`, mit aktivem venv (Prompt zeigt `(venv)`). *psql* = innerhalb von `psql` nach dem Verbinden. Python-Skripte immer mit `python3 scripts/…` starten.

> **Vorsicht, zwei Arten von Loadern.** Die neuen Loader (Tabelle in Abschnitt 4) machen ohne Option nur einen **Trockenlauf** und schreiben erst mit `--schreiben`. **Die übrigen 50 Loader haben keine Optionen und schreiben sofort** (alle enthalten `commit()`). 17 Loader sind wegen CI-172 gesperrt und brechen mit Meldung ab.

## 0. Grundlagen (Shell)
- `cd ~/Projekte/country-intelligence` – in den Repo-Stamm wechseln.
- `source venv/bin/activate` – Python-Umgebung des Projekts einschalten; `deactivate` schaltet sie aus. Ohne venv: `ModuleNotFoundError`.
- `caffeinate -i python3 -u <skript> | tee -a logs/<name>.log` – lange Läufe: Mac schläft nicht ein (`caffeinate -i`), Ausgabe sofort sichtbar (`-u`) und zugleich im Log (`tee -a`). **Nicht für `review.py`/`apply.py`** (interaktiv).

## 1. Datenbank
- `psql -d country_intelligence` – Shell: interaktiv mit der DB verbinden; `\q` beendet.
- `psql -d country_intelligence -X -c "SELECT count(*) FROM indicators;"` – Shell: eine Abfrage ohne interaktive Sitzung. `-X` lässt `~/.psqlrc` weg (wichtig in Skripten und Dateiausgaben).
- `psql -d country_intelligence -X -f <datei>.sql > logs/<bereich>/<name>.txt 2>&1` – Shell: SQL-Datei ausführen, Ausgabe **und Fehler** (`2>&1`) in eine Datei.
- `scripts/db_lesen.sh "SELECT …"` oder `scripts/db_lesen.sh -f <datei>.sql` – Shell: nur lesender Zugang als `ci_agent_readonly` (für Claude Code, CI-23). Lehnt Backslash-Befehle ab. Stand 28.11.: Ablehnungen mit Attrappe statt `psql` geprüft; Abfrage gegen die DB von Julian ausgeführt (`current_user` = `ci_agent_readonly`).
- In psql: `\dt politics.*` (Tabellen eines Schemas), `\d indicators` (Spalten einer Tabelle), `\x` (breite Zeilen untereinander), `\pset pager off` (Pager aus; steht schon in `~/.psqlrc`).
- `REFRESH MATERIALIZED VIEW indicator_coverage;` – psql: Abdeckungs-Übersicht nach jedem Laden neu berechnen.
- **Readiness-Check v5** (nur lesend, Sitzung read only) – Shell:

      psql -d country_intelligence -X -f sql/03_queries/2026-11-15_readiness_check.sql > logs/readiness/stand_$(date +%Y%m%d_%H%M).txt 2>&1

## 2. Backup (vor jeder Migration und jedem schreibenden Loader)
- Voll-Backup – Shell. Die erste Zeile setzt das Thema, `test ! -e` verhindert, dass ein vorhandenes Backup überschrieben wird:

      THEMA=ci177; F="backups/db_backup_$(date +%Y%m%d)_vor_${THEMA}.dump"; test ! -e "$F" && pg_dump -Fc -U postgres country_intelligence > "$F" && ls -l "$F"

- `bash scripts/backup_drive.sh` – Shell: Wochen-Backup von Hand anstoßen (Dump in den Drive-Ordner; löscht nichts).
- Zeitplan: launchd, **sonntags 20:00** (`scripts/launchd/de.julian.ci-backup.plist`). `launchctl start de.julian.ci-backup` testet ihn sofort (so laufen Hintergrundprozesse mit ihren echten Rechten); `launchctl load` / `unload ~/Library/LaunchAgents/de.julian.ci-backup.plist` schaltet ihn ein oder aus. Log: `logs/backup.log`.
- Wiederherstellen: nur nach Absprache, Ablauf in Notion „Backup & Restore“ (25.10. mit `pg_restore -j 4 --no-owner`, laut Chat-Doku).

## 3. Migrationen (`sql/05_migrations/`)
Muster seit 24.11.: Die Datei setzt `ON_ERROR_STOP`, öffnet `BEGIN` selbst und macht ohne Variable **ROLLBACK**. Neue Dateien heißen `ENTWURF_…`, bis Julian sie geprüft hat.
- **Datei festlegen** – Shell, einmal je Migration (Beispiel: die CI-171-Migration; Namen anpassen). Die Logdatei bekommt den Migrationsnamen und die Laufzeit, damit nichts überschrieben wird:

      M=sql/05_migrations/2026-11-24_ci171_kleinpunkte.sql; L="logs/migrations/$(basename "$M" .sql)_lauf_$(date +%Y%m%d_%H%M)"; test -f "$M" && echo "$M → $L"

- **Probelauf** (zeigt alle Kontrollzahlen, speichert nichts) – Shell: `psql -d country_intelligence -X -f "$M" > "${L}_probe.txt" 2>&1`
- **Ausführen** (COMMIT) – Shell, erst nach Backup und gelesenem Probelauf: `psql -d country_intelligence -X -v ausfuehren=1 -f "$M" > "$L.txt" 2>&1`
- Danach: Log lesen, die mitgelieferte Kontrollabfrage laufen lassen, `REFRESH MATERIALIZED VIEW indicator_coverage;`, Readiness-Check.
- *Ältere Migrationen bis 15.11.* stehen mit `-v ON_ERROR_STOP=1 --single-transaction` im Kopf; für die gilt ihr eigener Kopf.

## 4. Loader (`scripts/pipeline/`)
**Neue Loader mit Trockenlauf** (ohne Option: lesen, mit der DB vergleichen, nichts schreiben):

| Loader (`scripts/pipeline/…`) | Schreiben | weitere Optionen |
|---|---|---|
| `governance/load_freedom_house.py` | `--schreiben` | `--datei`, `--ohne-1982-1989` (Altverhalten) |
| `international/load_henley.py`, `international/load_kof.py` | `--schreiben` | `--datei` |
| `governance/load_fsi.py`, `governance/load_gitoc.py`, `governance/load_polity5.py` | `--schreiben` | `--datei` |
| `economy/load_cpi.py` (TI), `culture/load_whr.py`, `culture/load_hofstede.py`, `health/load_ghi.py` | `--schreiben` | `--datei` |
| `health/load_who.py` (CI-174, noch nicht gegen die API getestet) | `--schreiben` | `--codes`, `--rohdaten` |

**Mit eigenem Ablauf:**
- `python3 scripts/pipeline/economy/load_ilostat.py --trocken` – lädt Rohdaten nach `data/raw/ilo/<datum>/` und vergleicht mit der DB. `… --trocken --rohdaten <datum>` vergleicht erneut mit schon geladenen Rohdaten, `… --rohdaten <datum>` schreibt aus genau diesen Rohdaten.
- `python3 scripts/pipeline/economy/load_comtrade_v2.py --laender USA,DEU,BOL --jahre 2008-2012 --trocken` – Testlauf (Beispiel vom 11.11.); weitere Optionen `--pipeline`, `--state`. Tageslimit der API, Fortsetzung über `.comtrade_state_v2.json`.
- `history/load_cow.py` (`--interstate`, `--intrastate`), `environment/load_ndgain.py` (`--gain`, `--vulnerability`, `--readiness`): Optionen wählen Dateien, **kein Trockenlauf**.

**Tests** (Länder-Modul und WHO) – Shell: `python3 -m pytest scripts/pipeline/lib/test_laender.py scripts/pipeline/health/test_load_who.py -q`

## 5. Sekretär-Agent (`scripts/agent/`, liest die DB nur als `ci_agent_readonly`)
Ablauf: **Lauf → Auto-Prüfung → `review.py` (Julian) → `apply.py` (Julian)**. Der Lauf-Name ist der Ordnername unter `scripts/agent/output/`; ein eindeutiger Anfang reicht (z. B. `2026-11-25_2116`).
- `python3 scripts/agent/status.py` – offene Läufe mit dem nächsten Befehl je Lauf. `--alle` alle Läufe; `status.py <lauf>` Verlauf eines Laufs.
- `python3 scripts/agent/status.py <lauf> --erledigt "Notiz"` – Lauf ohne Übertragung abschließen (z. B. Leitfaden nach Notion übertragen).
- `python3 scripts/agent/status.py <lauf> --verwerfen "Grund"` – Lauf verwerfen.
- `python3 scripts/agent/secretary.py "Auftrag" --thema <thema> --budget 1.0` – freier Auftrag (Standard: `--model sonnet`, `--max-turns 80`). Leitfaden: `--thema <quelle>_leitfaden`. Kasten-Modus: `--kasten-aus <leitfaden-lauf> [--praefix <PRÄFIX>]`.
- `python3 scripts/agent/batch.py WB --vorschau` – zeigt, welche Indikatoren dran wären; `batch.py WB --paket 40 --anzahl 3` startet Pakete (`--domain`, `--budget` 4.0, `--model sonnet`). Stoppt beim ersten nicht sauberen Lauf.
- `python3 scripts/agent/check.py <lauf>` – Auto-Prüfung von Hand wiederholen.
- `python3 scripts/agent/review.py <lauf>` – **Julian**: Prüfung, Tasten **j** (übernehmen) · **k** (übernehmen + Datenproblem nach `known_issues`) · **n** (verwerfen) · **a** (abbrechen). Nicht durch `tee`.
- `python3 scripts/agent/apply.py <lauf>` – **Julian**: einziges schreibendes Skript (Backup, Transaktion, Kontrolle vor und nach COMMIT). Nicht durch `tee`.
- `python3 scripts/agent/beschreibung.py <lauf>` – nur `description` eines Laufs neu formulieren; `… --uebernehmen` übernimmt sie.
- `python3 scripts/agent/ask.py "Frage"` – Frage an die DB, Antwort nur aus echten Abfragen.
- `python3 scripts/agent/helpers/leitfaden_notion.py <lauf>` – Leitfaden in Notion-Format umwandeln.
- **Serien** (mehrere Läufe nacheinander, nie zwei parallel): `caffeinate -i bash scripts/agent/serie_<datum>.sh`. Jede Serie beschreibt im Kopf, was sie tut; Log in `logs/sekretaer_serie_<datum>.log`.
- Helfer, nur lesend: `python3 scripts/agent/helpers/wb_abgleich.py` (WB-Werte gegen API; `--von 2015 --bis 2024 --limit --neu`), `python3 scripts/agent/helpers/who_dims_check.py [CODE …]` (WHO-Dimensionen je Code).

## 6. Quellenverzeichnis
- `python3 scripts/check_sources.py` – prüft `docs/SOURCES_AVAILABLE.md` und `SOURCES_CANDIDATES.md` (Aufbau, Eindeutigkeit); `--db` gleicht zusätzlich mit der DB ab (nur lesend).
- Neu erzeugen: erst das Inventar (`psql … -f sql/03_queries/2026-11-10_quelleninventar.sql > <inventar>.txt 2>&1`), dann `python3 scripts/gen_sources_available.py <inventar>.txt docs/SOURCES_AVAILABLE.md`. *Ablageort des Inventars ist Teil von CI-188 (bisher `scripts/agent/output/`).*

## 7. Git (öffentliches Repo)
- `git status` – was geändert oder neu ist. **Vor jedem Commit.**
- `git --no-pager diff <datei>` – Änderungen ansehen, ohne Pager (in `less` würde eingefügter Text Befehle starten; Beenden dort mit `q`).
- `git --no-pager log --oneline -10` – letzte Commits.
- `git add <datei1> <datei2>` und `git commit -m "…"` – **Dateien einzeln adden, nie `git add .`**; `git push` danach. Commit und Push macht Julian.

## 8. Claude Code
- `/model` zeigt das aktive Modell, `/model sonnet` bzw. `/model opus` wechselt (wird als Standard gespeichert). `/status` zeigt Sitzung und Modell, `/usage` den Verbrauch gegen die Limits (nur lokaler Verlauf dieses Rechners). `/clear` leert den Kontext zwischen unabhängigen Aufgaben.

---
Herkunft: Skriptköpfe und Optionen per `grep` am 28.11.2026 (`scripts/agent/*.py`, `scripts/agent/helpers/*.py`, `scripts/pipeline/**/load_*.py`, `scripts/check_sources.py`, `scripts/gen_sources_available.py`, `scripts/backup_drive.sh`, `scripts/launchd/de.julian.ci-backup.plist`), Köpfe von `sql/03_queries/2026-11-15_readiness_check.sql` und `sql/05_migrations/2026-11-24_ci171_kleinpunkte.sql`, Prüfung „Loader ohne Optionen enthalten `commit()`“ (50 von 50) und Sperrvermerke CI-172 per `grep`; Restore-Weg und Comtrade-Beispiel aus den Chat-Dokus 25.10. und 11.11.; Claude-Code-Befehle aus CLAUDE.md (Doku code.claude.com, abgerufen 27.11.).
