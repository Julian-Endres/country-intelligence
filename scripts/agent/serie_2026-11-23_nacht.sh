#!/usr/bin/env bash
# Sekretär-Nachtserie 23./24.11.2026: je Thema Leitfaden (mit Rohdaten-Prüfung), danach Metadaten je Präfix.
# Wiederanlauf: Bricht ein Lauf am Nutzungslimit ab, wird er verworfen, das Skript wartet 40 min und versucht es
# erneut (höchstens 3 Versuche je Schritt). Andere Fehler: kein neuer Versuch, laut in der Zusammenfassung.
# Wiederholbar: Gibt es schon einen regulär fertigen Leitfaden zum Thema, wird er nicht neu geschrieben;
# batch.py plant nur Codes ein, die noch offen sind (sonst 0 und Ende).
# NICHT parallel zu einer anderen Serie starten.
# Start (Shell, Repo-Wurzel, venv aktiv):  caffeinate -i bash scripts/agent/serie_2026-11-23_nacht.sh
cd "$(dirname "$0")/../.." || exit 1
LOG="logs/sekretaer_serie_2026-11-23_nacht.log"
OUT="scripts/agent/output"
WARTE_MIN=40
declare -a ERG=()

ok_leitfaden() {  # neuester regulär fertiger, nicht verworfener Leitfaden-Lauf zum Thema (oder leer)
  for d in $(ls -d "$OUT"/*_sekretaer_"$1" 2>/dev/null | sort -r); do
    [ -f "$d/leitfaden.md" ] && grep -q "Status: success" "$d/protokoll.md" 2>/dev/null \
      && ! grep -q '"status": "verworfen"' "$d/status.json" 2>/dev/null && { echo "$d"; return; }
  done
}

limit_abbruch() {  # $1 Lauf-Ordner: true, wenn am Nutzungslimit abgebrochen
  [ -n "$1" ] && grep -qiE "hit your .*limit|usage limit|rate limit" "$1/protokoll.md" "$1/status.json" 2>/dev/null
}

verwerfen_und_warten() {  # $1 Lauf-Ordner
  python3 scripts/agent/status.py "$(basename "$1")" --verwerfen "Abbruch am Nutzungslimit, Nachtserie startet neu" 2>&1 | tee -a "$LOG"
  echo "=== $(date +%H:%M) Limit: warte $WARTE_MIN min" | tee -a "$LOG"
  sleep $((WARTE_MIN * 60))
}

thema() {  # $1 Thema (ohne _leitfaden), $2 Budget, $3 Auftrag, $4… Präfixe für die Metadaten
  local t="$1_leitfaden" budget="$2" auftrag="$3" d v; shift 3
  d=$(ok_leitfaden "$t")
  if [ -n "$d" ]; then
    ERG+=("$t: schon fertig ($(basename "$d")), nicht neu geschrieben")
  else
    for v in 1 2 3; do
      echo "=== $(date +%H:%M) Leitfaden $t (Versuch $v)" | tee -a "$LOG"
      python3 scripts/agent/secretary.py "$auftrag $G" --thema "$t" --budget "$budget" --max-turns 120 2>&1 | tee -a "$LOG"
      d=$(ok_leitfaden "$t"); [ -n "$d" ] && break
      local last; last=$(ls -d "$OUT"/*_sekretaer_"$t" 2>/dev/null | sort | tail -1)
      if limit_abbruch "$last" && [ "$v" -lt 3 ]; then verwerfen_und_warten "$last"; else break; fi
    done
    if [ -z "$d" ]; then ERG+=("$t: Leitfaden NICHT fertig – Metadaten $* übersprungen"); return; fi
    ERG+=("$t: Leitfaden ok ($(basename "$d"))")
  fi
  local src rc low last
  for src in "$@"; do
    low=$(echo "$src" | tr 'A-Z' 'a-z')
    for v in 1 2 3; do
      echo "=== $(date +%H:%M) Metadaten $src (Versuch $v)" | tee -a "$LOG"
      python3 scripts/agent/batch.py "$src" --paket 40 --anzahl 1 2>&1 | tee -a "$LOG"; rc=${PIPESTATUS[0]}
      [ "$rc" -eq 0 ] && break
      last=$(ls -d "$OUT"/*_sekretaer_"$low"_batch_* 2>/dev/null | sort | tail -1)
      if limit_abbruch "$last" && [ "$v" -lt 3 ]; then verwerfen_und_warten "$last"; else break; fi
    done
    ERG+=("  $src: batch Exit $rc")
  done
}

G="Schreibe den Quellen-Leitfaden (leitfaden.md und leitfaden_belege.md) und befunde.md mit Länder-Stichprobe DB gegen Rohdatei für DEU, USA, JPN, BRA, NGA (wo vorhanden; je Code mindestens zwei Land-Jahre, Abweichungen mit Größe nennen). Keine metadata.sql. Lies zuerst den Loader (read_text mit Pfad ab Repo-Wurzel, scripts/pipeline/...), damit du weißt, was genau geladen und gerechnet wurde, und prüf per sql_query, welche Codes, Jahre (time_period) und wie viele Länder in der DB stehen. Prüf auch die Rohdaten selbst: Stand/Version, Zeilen und Spalten, ob der Loader-Pfad zur Datei passt, auffällige Werte. Methodik nur mit Beleg (Datei und Zeile oder abgerufene URL), nicht aus dem Gedächtnis; was nicht belegt ist, als offen markieren. Belege außerhalb des Referenzordners mit Pfad ab Repo-Wurzel angeben. Abschnitt 7: ein Steckbrief je DB-Code mit dem Wortlaut der Quelle, soweit belegt; bei Codes, die erst unser Loader berechnet, die Rechnung aus dem Loader beschreiben (mit Zeile)."

thema owid_energy 1.5 "OWID Energy (Our World in Data, energy-data; 12 Codes mit Präfixen nach Urheber, die unser Loader von Hand vergeben hat: EI:fossil_share_energy, EI:coal_share_energy, EI:gas_share_energy, EI:coal_production, EI:gas_production, EI:oil_production, EMBER:renewables_share_energy, EMBER:solar_share_elec, EMBER:wind_share_elec, EMBER:hydro_share_elec, EMBER:nuclear_share_elec, EIA:energy_per_capita). Loader: scripts/pipeline/environment/load_owid_energy.py (lädt die Datei direkt von GitHub). Lokale Abzüge vom 23.11.2026 im Referenzordner: owid-energy-codebook.csv (Spalten column, description, unit, source) und owid-energy-data.csv (aktueller Stand, nicht zwingend der geladene). Pflichtfragen: (1) Je Code Beschreibung, Einheit und Primärquelle laut Codebook (wörtlich, mit Zeile). (2) Stimmt das Präfix im Code mit der Primärquelle laut Codebook überein? Für jeden Code einzeln, Abweichungen deutlich in befunde.md (Claude hat vorab gesehen: renewables_share_energy nennt laut Codebook das Energy Institute, nicht Ember – bestätigen oder widerlegen). (3) Primärenergie: Substitutionsmethode oder direkte Methode (wichtig für die Anteile). (4) Strom-Anteile: Anteil an der Erzeugung, nicht am Verbrauch; Ember und Energy Institute kombiniert – wie. (5) energy_per_capita: welche Bevölkerungszahl und welche Quelle je Zeitraum. (6) Stand der geladenen Fassung (Jahre in der DB gegen den lokalen Abzug) und Nutzungsbedingungen (OWID CC BY, Bedingungen von EI, Ember, EIA)." EI EMBER EIA

thema ti 1.0 "TI (Transparency International, Corruption Perceptions Index, 1 Code TI:CPI). Loader: scripts/pipeline/economy/load_cpi.py – er lädt NICHT von TI, sondern über den OWID-Katalog (owid.catalog search(\"corruption\"), erster Treffer): klären, welcher Datensatz und welche Spalte das war, welche Jahre in der DB stehen und ob der erste Suchtreffer überhaupt der CPI ist. Originaldaten von TI lokal: data/raw/economy/CPI2025_Results.xlsx, lesbar als Referenzdateien ti_cpi2025_timeseries_2012_2025.csv und ti_cpi2025_global_scores.csv (von Claude am 23.11. unverändert aus der Excel exportiert, Kopfzeilen ab Zeile 4). Methodik per WebFetch von transparency.org (CPI 2025 Technical Methodology Note, Sources description). Pflichtfragen: (1) Was misst der CPI (wahrgenommene Korruption im öffentlichen Sektor, Expertenurteile, nicht Erfahrung), Skala 0–100, hoher Wert = weniger Korruption. (2) Mindestzahl Quellen je Land, Standardfehler. (3) Vergleichbarkeit über Jahre: erst ab 2012 vergleichbar (Methodenwechsel), was steht für ältere Jahre in der DB? (4) Stimmen die DB-Werte mit den TI-Originalwerten überein (Stichprobe)? (5) Nutzungsbedingungen (CC BY-ND?)." TI

thema rsf 1.0 "RSF (Reporters sans frontières, World Press Freedom Index, 1 Code RSF:press_freedom). Loader: scripts/pipeline/governance/load_rsf.py (lädt über OWID Grapher press-freedom-index-rsf.csv, URL im Loader Zeile 8). Hole die Datei für die Stichprobe mit download_file (gleiche URL) und dazu die Metadaten der Grapher-Seite (https://ourworldindata.org/grapher/press-freedom-index-rsf.metadata.json). Methodik per WebFetch von rsf.org/en/index (Methodology). Pflichtfragen: (1) Skala und Richtung: Ist es der Score (0–100, hoch = mehr Pressefreiheit, seit 2022) oder der alte Score (niedrig = besser)? Was steht in der DB für Jahre vor 2022 – Bruch in der Zeitreihe? (2) Fünf Teilindikatoren und Fragebogen + Übergriffe. (3) Was OWID an den Werten ändert. (4) Nutzungsbedingungen RSF und OWID." RSF

thema caf_wgi 1.2 "CAF_WGI (Charities Aid Foundation, World Giving Index, 4 Codes CAF_WGI:total_score, helping_stranger, donating_money, volunteering_time). Loader: scripts/pipeline/social/load_caf_wgi.py. Der Loader erwartet die Dateien unter data/raw/Manuell_27-05/ (Zeile 41–43), sie liegen heute unter data/raw/social/ (archive_CAF World Giving Index.zip, world_giving_2023_complete.csv, world_giving_2024_complete.csv) – festhalten, CSV-Dateien dort lesen. Methodik per WebFetch von cafonline.org (World Giving Index Report, Methodology; Datengrundlage Gallup World Poll). Pflichtfragen: (1) Wortlaut der drei Gallup-Fragen und Bezugszeitraum (letzter Monat). (2) total_score: einfacher Mittelwert der drei Anteile? (3) Jahre: Berichtsjahr gegen Erhebungsjahr, mehrjährige Mittel (z. B. 10-Jahres-Ausgabe), was steht in time_period. (4) 2024-Ausgabe: Methodenwechsel (World Giving Report?) – vergleichbar? (5) Nutzungsbedingungen." CAF_WGI

thema henley 1.2 "HENLEY (4 Codes HENLEY:visa_free_total, visa_required, evisa, visa_on_arrival, time_period 'static'). Loader: scripts/pipeline/international/load_henley.py lädt NICHT vom Henley Passport Index, sondern den Community-Datensatz ilyankou/passport-index-dataset (GitHub, passport-index-tidy.csv). Lokale Abzüge vom 23.11. im Referenzordner: passport-index-tidy.csv und passport-index-dataset_README.md (README: Stand 12.01.2025, archiviert, Herkunft der Daten). Pflichtfragen: (1) Wer ist der Urheber der Daten laut README (Passport Index von Arton Capital? Henley? eigene Sammlung?) – stimmt das Präfix HENLEY und der Name der Quelle in der DB? Deutlich in befunde.md. (2) Wie der Loader die Kategorien zählt (Werte 7–360 Tage, visa free, visa on arrival, e-visa, eta, visa required, covid ban, -1) und was visa_free_total einschließt (Loader-Zeilen). (3) Stand der Daten (welcher Monat) und was 'static' bedeutet. (4) Nutzungsbedingungen (Lizenz laut README)." HENLEY

thema glottolog 1.0 "GLOTTOLOG (Glottolog 5.3, 3 Codes GLOTTOLOG:n_languages, n_families, ldi). Loader: scripts/pipeline/culture/load_glottolog.py (lädt languages.csv aus glottolog-cldf v5.3). Lokaler Abzug im Referenzordner: glottolog_5_3_languages.csv (gleiche URL wie im Loader, 23.11.). Doku per WebFetch von glottolog.org (About, Glossary) und der CLDF-Beschreibung. Pflichtfragen: (1) Wie ordnet der Loader eine Sprache einem Land zu (Feld Countries? Macroarea?) – eine Sprache in mehreren Ländern zählt mehrfach? (2) Was zählt als Sprache (Level language, keine Dialekte/Familien), Umgang mit ausgestorbenen Sprachen und Bookkeeping. (3) n_families: Familien oder auch Isolate? (4) ldi: welcher Index genau (Greenberg-Index braucht Sprecherzahlen, die Glottolog nicht hat) – Rechnung aus dem Loader mit Zeile, und ob der Name ldi dann irreführend ist. (5) Nutzungsbedingungen (CC BY 4.0)." GLOTTOLOG

thema unesco_whc 1.0 "UNESCO_WHC (UNESCO-Welterbeliste, 4 Codes UNESCO_WHC:total, cultural, natural, mixed). Loader: scripts/pipeline/culture/load_unesco_whc.py (API data.unesco.org whc001). Hole für die Stichprobe mit download_file die API-Antwort (Parameter wie im Loader). Doku per WebFetch von whc.unesco.org (List, Criteria). Pflichtfragen: (1) Zählt der Loader Stätten je Land kumuliert bis zum Jahr oder Neueinschreibungen je Jahr? Was steht in time_period? (2) Grenzüberschreitende Stätten: zählen sie bei jedem beteiligten Land? (3) Gestrichene Stätten und Rote Liste (in Gefahr). (4) Nutzungsbedingungen." UNESCO_WHC

thema unesco_ich 1.0 "UNESCO_ICH (Immaterielles Kulturerbe, 4 Codes UNESCO_ICH:total, rl, usl, rsp). Loader: scripts/pipeline/culture/load_unesco_ich.py (API data.unesco.org ich001). Hole für die Stichprobe mit download_file die API-Antwort (Parameter wie im Loader). Doku per WebFetch von ich.unesco.org (Lists). Pflichtfragen: (1) Bedeutung der drei Listen (Representative List, Urgent Safeguarding List, Register of Good Safeguarding Practices). (2) Kumuliert oder je Jahr, was steht in time_period. (3) Multinationale Einträge: zählen sie bei jedem Land? (4) Nutzungsbedingungen." UNESCO_ICH

echo; echo "===== Zusammenfassung =====" | tee -a "$LOG"
printf '%s\n' "${ERG[@]}" | tee -a "$LOG"
echo "Morgen: python3 scripts/agent/status.py, dann review.py und apply.py je Metadaten-Lauf" | tee -a "$LOG"
