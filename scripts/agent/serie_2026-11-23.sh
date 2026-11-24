#!/usr/bin/env bash
# Sekretär-Serie 23.11.2026: je Leitfaden-Thema erst Leitfaden (mit Rohdaten-Stichprobe), danach Metadaten je Präfix.
# OWID Energy: ein Leitfaden für EI, EMBER, EIA (ein Loader, eine Datei; batch.py findet ihn über LEITFADEN_ALIAS).
# Nur lesend gegenüber der DB, schreibt nur in scripts/agent/output/<lauf>/. Review und apply.py macht Julian danach.
# Start (Shell, Repo-Wurzel, venv aktiv):  caffeinate -i bash scripts/agent/serie_2026-11-23.sh [thema]
# Mit [thema] (z. B. owid_energy) läuft nur dieses Thema.
cd "$(dirname "$0")/../.." || exit 1
LOG="logs/sekretaer_serie_2026-11-23.log"
declare -a ERG=()
NUR="${1:-}"

thema() {  # $1 Thema (ohne _leitfaden), $2 Budget, $3 Auftrag, $4… Präfixe für die Metadaten
  [ -n "$NUR" ] && [ "$NUR" != "$1" ] && return
  local t="$1_leitfaden" budget="$2" auftrag="$3"; shift 3
  echo "=== $(date +%H:%M) Leitfaden $t" | tee -a "$LOG"
  python3 scripts/agent/secretary.py "$auftrag" --thema "$t" --budget "$budget" --max-turns 120 2>&1 | tee -a "$LOG"
  local d; d=$(ls -d scripts/agent/output/*_sekretaer_"$t" 2>/dev/null | sort | tail -1)
  if [ -z "$d" ] || [ ! -f "$d/leitfaden.md" ] || ! grep -q "Status: success" "$d/protokoll.md"; then
    ERG+=("$t: Leitfaden NICHT regulär fertig (${d:-kein Ordner}) – Metadaten $* übersprungen"); return
  fi
  ERG+=("$t: Leitfaden ok ($(basename "$d"))")
  for src in "$@"; do
    echo "=== $(date +%H:%M) Metadaten $src" | tee -a "$LOG"
    python3 scripts/agent/batch.py "$src" --paket 40 --anzahl 1 2>&1 | tee -a "$LOG"
    ERG+=("  $src: batch Exit ${PIPESTATUS[0]}")
  done
}

G="Schreibe den Quellen-Leitfaden (leitfaden.md und leitfaden_belege.md) und befunde.md mit Länder-Stichprobe DB gegen Rohdatei für DEU, USA, JPN, BRA, NGA (wo vorhanden; je Code mindestens zwei Land-Jahre, Abweichungen mit Größe nennen). Keine metadata.sql. Lies zuerst den Loader (read_text mit Pfad ab Repo-Wurzel, scripts/pipeline/...), damit du weißt, was genau geladen und gerechnet wurde, und prüf per sql_query, welche Codes, Jahre (time_period) und wie viele Länder in der DB stehen. Prüf auch die Rohdaten selbst: Stand/Version, Zeilen und Spalten, ob der Loader-Pfad zur Datei passt, auffällige Werte. Methodik nur mit Beleg (Datei und Zeile oder abgerufene URL), nicht aus dem Gedächtnis; was nicht belegt ist, als offen markieren. Belege außerhalb des Referenzordners mit Pfad ab Repo-Wurzel angeben. Abschnitt 7: ein Steckbrief je DB-Code mit dem Wortlaut der Quelle, soweit belegt; bei Codes, die erst unser Loader berechnet, die Rechnung aus dem Loader beschreiben (mit Zeile)."

thema ucdp 1.3 "UCDP (Uppsala Conflict Data Program, Georeferenced Event Dataset GED Version 26.1, 3 Codes UCDP:ged_deaths_total, UCDP:ged_deaths_civilians, UCDP:ged_events). Loader: scripts/pipeline/governance/load_ucdp_ged_aggregate.py (aggregiert Ereignisse zu Land-Jahr); dazu ansehen, aber nicht beschreiben: load_ucdp.py, load_ucdp_onesided.py, load_ucdp_ged_context.py (relationale Tabellen politics.conflict*). Rohdaten: data/raw/governance/UCDP/GEDEvent_v26_1.csv (261 MB: nur Kopf mit read_text und gezielt mit search_text lesen, nie ganz), dazu UcdpPrioConflict_v26_1.csv, BattleDeaths_v26_1_conf.csv, NonState_v26_1.csv. Für die Länder-Stichprobe: Kontrolltabelle data/raw/reference/ucdp_ged261_kontrolle_land_jahr.csv (von Claude am 23.11. unabhängig vom Loader aus der GED-Datei summiert, Kopfzeilen erklären die Rechnung; DEU, USA, BRA, NGA, dazu SYR, UKR, COL, MEX, IND; JPN hat keine Ereignisse). Vergleiche DB gegen diese Tabelle und erkläre jede Abweichung aus dem Loader (Filter, Länderzuordnung). Auffällig und zu klären: Syrien nur 18 Jahre in GED. Codebook GED 26.1 per download_file von ucdp.uu.se/downloads (PDF, dann pdf_to_text). Pflichtfragen: (1) Was ist ein Ereignis in GED (organisierte Gewalt, Schwelle mindestens ein Todesopfer, drei Gewaltarten type_of_violence 1/2/3). (2) Welche Todesopfer-Spalte nutzt der Loader (best, low, high) und wie werden deaths_civilians gebildet. (3) Zuordnung zum Land: Ort des Ereignisses (country_id) oder Konfliktpartei, Gleditsch-Ward-Codes und deren Abbildung im Loader. (4) Abdeckung: welche Jahre und Regionen (GED-Abdeckung ist nicht weltweit gleich lang). (5) Länder-Jahre ohne Ereignis: 0 oder fehlend in der DB? (6) Zitierweise und Nutzungsbedingungen. $G" UCDP

thema nobel 1.0 "NOBEL (Nobel Prize API v2.1, Codes NOBEL:phy, che, med, lit, pea, eco und ggf. total). Loader: scripts/pipeline/culture/load_nobel.py (API https://api.nobelprize.org/2.1/laureates). Hole für die Stichprobe mit download_file die API-Antwort (Parameter wie im Loader; mindestens die Preisträger eines Jahres und eines Landes). Doku per WebFetch von nobelprize.org/about/developer-zone-2 (API-Dokumentation, Felder birth/affiliation/nationality). Pflichtfragen: (1) Welchem Land ordnet der Loader einen Preisträger zu (Geburtsland, Geburtsland heute, Staatsangehörigkeit, Institution) und mit welchem Jahr (Preisjahr). (2) Wie werden geteilte Preise und Organisationen (Friedenspreis) gezählt. (3) Steht NOBEL:total in der DB, und ist es die Summe der übrigen Codes? (4) Wirtschaftspreis: seit 1969, kein Nobelpreis im engen Sinn – festhalten. (5) Geburtsländer, die es heute nicht mehr gibt: wie abgebildet. (6) Nutzungsbedingungen der API (CC0?). $G" NOBEL

thema owid_energy 1.5 "OWID Energy (Our World in Data, energy-data; 12 Codes mit Präfixen nach Urheber, die unser Loader von Hand vergeben hat: EI:fossil_share_energy, EI:coal_share_energy, EI:gas_share_energy, EI:coal_production, EI:gas_production, EI:oil_production, EMBER:renewables_share_energy, EMBER:solar_share_elec, EMBER:wind_share_elec, EMBER:hydro_share_elec, EMBER:nuclear_share_elec, EIA:energy_per_capita). Loader: scripts/pipeline/environment/load_owid_energy.py (lädt die Datei direkt von GitHub). Lokale Abzüge vom 23.11.2026 im Referenzordner: owid-energy-codebook.csv (Spalten column, description, unit, source) und owid-energy-data.csv (aktueller Stand, nicht zwingend der geladene). Pflichtfragen: (1) Je Code Beschreibung, Einheit und Primärquelle laut Codebook (wörtlich, mit Zeile). (2) Stimmt das Präfix im Code mit der Primärquelle laut Codebook überein? Für jeden Code einzeln, Abweichungen deutlich in befunde.md (Claude hat vorab gesehen: renewables_share_energy nennt laut Codebook das Energy Institute, nicht Ember – bestätigen oder widerlegen). (3) Primärenergie: Substitutionsmethode oder direkte Methode (wichtig für die Anteile). (4) Strom-Anteile: Anteil an der Erzeugung, nicht am Verbrauch; Ember und Energy Institute kombiniert – wie. (5) energy_per_capita: welche Bevölkerungszahl und welche Quelle je Zeitraum. (6) Stand der geladenen Fassung (Jahre in der DB gegen den lokalen Abzug) und Nutzungsbedingungen (OWID CC BY, Bedingungen von EI, Ember, EIA). $G" EI EMBER EIA

echo; echo "===== Zusammenfassung =====" | tee -a "$LOG"
printf '%s\n' "${ERG[@]}" | tee -a "$LOG"
echo "Danach: python3 scripts/agent/status.py, dann review.py und apply.py je Metadaten-Lauf" | tee -a "$LOG"
