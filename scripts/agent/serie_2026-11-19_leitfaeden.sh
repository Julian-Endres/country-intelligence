#!/usr/bin/env bash
# Sekretär-Serie 19.11.2026: Quellen-Leitfäden für 5 neue Quellen (Stufe 1).
# Nur lesend gegenüber der DB, schreibt nur in scripts/agent/output/<lauf>/.
# Start (Shell, Repo-Wurzel):  caffeinate -i bash scripts/agent/serie_2026-11-19_leitfaeden.sh
# Danach: python3 scripts/agent/status.py
cd "$(dirname "$0")/../.." || exit 1
LOG="logs/sekretaer_serie_2026-11-19.log"
declare -a ERG=()

lauf() {  # $1 thema, $2 budget, $3 auftrag
  echo "=== $(date +%H:%M) Start $1" | tee -a "$LOG"
  python3 scripts/agent/secretary.py "$3" --thema "$1" --budget "$2" --max-turns 120 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  ERG+=("$1: Exit $rc")
  echo "=== $(date +%H:%M) Ende $1 (Exit $rc)" | tee -a "$LOG"
}

GEMEINSAM="Schreibe den Quellen-Leitfaden (leitfaden.md und leitfaden_belege.md) und befunde.md mit Länder-Stichprobe DB gegen Rohdatei für DEU, USA, JPN, BRA, NGA (wo vorhanden). Keine metadata.sql. Lies zuerst den Loader, damit du weißt, was genau geladen wurde, und prüf per sql_query, welche Codes und Jahre (time_period) in der DB stehen. Methodik nur mit Beleg (Datei und Zeile oder abgerufene URL), nicht aus dem Gedächtnis; was nicht belegt ist, als offen markieren. Abschnitt 7: ein Steckbrief je DB-Code mit dem Wortlaut der Quelle, soweit belegt."

lauf edelman_leitfaden 1.5 "EDELMAN (Edelman Trust Barometer, Edelman Trust Institute, 36 Codes trust_<institution>:<gruppe>). Loader: scripts/pipeline/social/load_edelman.py. Rohdaten: data/raw/social/Edelman/ (63 CSV-Dateien data-edelman-trust-institute(N).csv; öffne einige, um den Aufbau zu verstehen). Methodik per WebFetch von edelman.com (Trust Barometer, Methodology). Pflichtfragen: (1) Erhebung: Online-Panel, Stichprobengröße, Länder, Feldzeit je Ausgabe. (2) Wie wird Vertrauen gemessen (Skala, ab welchem Wert zählt jemand als vertrauend, ist der DB-Wert ein Prozentanteil). (3) Wie sind die Gruppen definiert (Alter, Einkommen niedrig/mittel/hoch je Land?). (4) Welches Jahr trägt eine Ausgabe (Ausgabejahr oder Feldjahr) und was steht in time_period. (5) Nutzungsbedingungen. $GEMEINSAM"

lauf wvs_leitfaden 2.0 "WVS (World Values Survey / EVS Integrated Time Series 1981-2022, v5.0, 21 Codes). Loader: scripts/pipeline/demographics/load_wvs.py (wichtig: er bildet je Land und Erhebungsjahr S020 den ungewichteten Mittelwert der Rohcodes, ohne Gewicht S017). Rohdatei: data/raw/culture/WVS_Time_Series_1981-2022_csv_v5_0.csv (sehr groß, nur Kopfzeile und gezielte Zeilen lesen). Codebuch und Fragewortlaut per WebFetch/download_file von worldvaluessurvey.org (Documentation, Time Series Variables). Pflichtfragen: (1) Wortlaut und Antwortskala je Code, inklusive Richtung (ist 1 = sehr viel oder gar nicht). (2) Was ist ein Mittelwert dieses Codes inhaltlich (bei zweistufigen oder kategorialen Fragen ist ein Mittelwert schwer zu lesen; benenne das je Code). (3) tradrat5, tradagg, survsagg: wie gebildet, welche Skala. (4) Gewichtung: was empfiehlt die WVS, was bedeutet das Fehlen von S017 für die DB-Werte. Rechne für 2 Länder-Jahre den gewichteten und ungewichteten Mittelwert eines Codes nach, wenn das mit vertretbarem Aufwand geht. (5) Wellen und Jahre, Nutzungsbedingungen und Zitierweise. $GEMEINSAM"

lauf fao_food_leitfaden 1.5 "FAO_FOOD (FAOSTAT Food Balance Sheets, 29 Codes wie kcal_per_capita, protein_per_capita, meat, wine). Loader: scripts/pipeline/health/load_fao_food.py und load_fao_food_groups.py (welcher Code aus welchem Item und Element). Rohdaten: data/raw/health/fao_food.zip (FoodBalanceSheets_E_*.csv, die Datendatei ist sehr groß; nutze Elements, ItemCodes und Flags und nur gezielte Zeilen). Methodik per WebFetch von fao.org/faostat (Food Balance Sheets, Methodology/Handbook). Pflichtfragen: (1) Was misst eine Food Balance Sheet (Angebot, nicht Verzehr). (2) Einheit je Code (kg/Kopf/Jahr, kcal/Kopf/Tag, g/Kopf/Tag) laut Element. (3) Methodenbruch alte und neue FBS (ab 2010) und was der Loader davon lädt. (4) Welche Items stecken in den Gruppen-Codes (cereals, vegetables, meat …), belegt am Loader und an ItemCodes. (5) Flags (geschätzt, imputiert) und Nutzungsbedingungen (Lizenz). $GEMEINSAM"

lauf kof_leitfaden 1.2 "KOF (KOF Globalisation Index, ETH Zürich, 9 Codes gi, ecgi, trgi, figi, sogi, pogi, cugi, ingi, ipgi). Loader: scripts/pipeline/international/load_kof.py. Rohdaten: data/raw/Manuell_27-05/KOF/kof_data_export_*.xlsx (zwei Exporte; kläre, welcher geladen wird und ob sie sich unterscheiden). Methodik per WebFetch von kof.ethz.ch (Globalisation Index, Methodik) und Gygli, Haelg, Potrafke, Sturm (2019), Review of International Organizations. Pflichtfragen: (1) Bedeutung jedes Codes (gesamt, wirtschaftlich, Handel, Finanzen, sozial, interpersonell, Information, kulturell, politisch) und ob de facto, de jure oder kombiniert geladen ist. (2) Skala 1-100 und Normierung. (3) Ausgabe/Version und Jahre. (4) Nutzungsbedingungen. $GEMEINSAM"

lauf owid_co2_leitfaden 1.2 "OWID_CO2 (Our World in Data CO2 and Greenhouse Gas Emissions, 10 Codes co2, co2_per_capita, co2_per_gdp, share_global_co2, methane, nitrous_oxide, primary_energy, coal_co2, oil_co2, gas_co2). Loader: scripts/pipeline/economy/load_owid_co2.py (Quelle der Datei, welche Spalten). Codebuch per download_file: https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-codebook.csv (Spalten column, description, unit, source). Pflichtfragen: (1) Beschreibung, Einheit und Primärquelle je Code laut Codebuch (Global Carbon Project, Jones et al., Energy Institute). (2) Territorial oder konsumbasiert. (3) Einschluss von Landnutzung (LUC) bei co2. (4) Stand der geladenen Fassung und Nutzungsbedingungen (CC BY). $GEMEINSAM"

echo; echo "===== Zusammenfassung =====" | tee -a "$LOG"
printf '%s\n' "${ERG[@]}" | tee -a "$LOG"
echo "Weiter mit: python3 scripts/agent/status.py" | tee -a "$LOG"
