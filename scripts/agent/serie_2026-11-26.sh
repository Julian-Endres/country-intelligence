#!/usr/bin/env bash
# Sekretär-Serie 26./27.11.2026 (CI-169): neue Leitfäden mit Kasten + Kasten für alle älteren Leitfäden.
#   Teil 1: neue Leitfäden PWT, GHI, SIPRI, EI, EMBER, EIA (Energie je Urheber, OWID Energy = Bezugsweg).
#   Teil 2: Kasten-Pilot (neuer Modus --kasten-aus) an WB, VDEM, ILO. Nur wenn alle drei sauber sind (❌ 0,
#           richtiges Präfix), läuft Teil 3. Sonst Stopp mit Meldung – erst lesen, dann ausrollen.
#   Teil 3: Kasten für die übrigen 14 alten Leitfäden.
#   Teil 4: nur wenn CI-177 live gelaufen ist (FH:STATUS hat Werte): neue Leitfäden FH, FSI; Kasten KOF, GITOC,
#           WHR; Kasten neu für TI und HENLEY (deren Bei-uns-Zahlen ändern sich mit CI-177).
# Keine Metadaten in dieser Serie (69 Vorschläge vom 25.11. warten noch auf Review).
# Wiederanlauf am Nutzungslimit: Lauf verwerfen, 40 min warten, höchstens 3 Versuche je Schritt.
# Wiederholbar: Fertige Leitfäden und saubere Kästen werden nicht neu geschrieben.
# NICHT parallel zu einer anderen Serie starten.
# Start (Shell, Repo-Wurzel, venv aktiv):  caffeinate -i bash scripts/agent/serie_2026-11-26.sh
cd "$(dirname "$0")/../.." || exit 1
LOG="logs/sekretaer_serie_2026-11-26.log"
OUT="scripts/agent/output"
WARTE_MIN=40
declare -a ERG=()

ok_leitfaden() {  # neuester regulär fertiger, nicht verworfener Lauf mit leitfaden.md zum Thema (oder leer)
  for d in $(ls -d "$OUT"/*_sekretaer_"$1" 2>/dev/null | sort -r); do
    [ -f "$d/leitfaden.md" ] && grep -q "Status: success" "$d/protokoll.md" 2>/dev/null \
      && ! grep -q '"status": "verworfen"' "$d/status.json" 2>/dev/null && { echo "$d"; return; }
  done
}

kasten_ok() {  # $1 Lauf, $2 Präfix: regulär fertig, Wer-Zeile mit richtigem Präfix, Auto-Prüfung kasten.md ❌ 0
  [ -n "$1" ] && [ -f "$1/kasten.md" ] && grep -q "Status: success" "$1/protokoll.md" 2>/dev/null \
    && grep -qE "^Wer: \`$2\`" "$1/kasten.md" \
    && awk '/^## kasten.md/{f=1;next} f && /❌/{print; exit}' "$1/pruefung.md" 2>/dev/null | grep -q "❌ 0 "
}

limit_abbruch() {  # $1 Lauf-Ordner: true, wenn am Nutzungslimit abgebrochen
  [ -n "$1" ] && grep -qiE "hit your .*limit|usage limit|rate limit" "$1/protokoll.md" "$1/status.json" 2>/dev/null
}

verwerfen_und_warten() {  # $1 Lauf-Ordner
  python3 scripts/agent/status.py "$(basename "$1")" --verwerfen "Abbruch am Nutzungslimit, Serie startet neu" 2>&1 | tee -a "$LOG"
  echo "=== $(date +%H:%M) Limit: warte $WARTE_MIN min" | tee -a "$LOG"
  sleep $((WARTE_MIN * 60))
}

leitfaden() {  # $1 Thema (ohne _leitfaden), $2 Präfix, $3 Budget, $4 Auftrag
  local t="$1_leitfaden" p="$2" budget="$3" auftrag="$4" d v last
  d=$(ok_leitfaden "$t")
  if [ -n "$d" ]; then ERG+=("$t: schon fertig ($(basename "$d")), nicht neu geschrieben"); return; fi
  for v in 1 2 3; do
    echo "=== $(date +%H:%M) Leitfaden $t (Versuch $v)" | tee -a "$LOG"
    python3 scripts/agent/secretary.py "$auftrag $G" --thema "$t" --budget "$budget" --max-turns 120 2>&1 | tee -a "$LOG"
    d=$(ok_leitfaden "$t"); [ -n "$d" ] && break
    last=$(ls -d "$OUT"/*_sekretaer_"$t" 2>/dev/null | sort | tail -1)
    if limit_abbruch "$last" && [ "$v" -lt 3 ]; then verwerfen_und_warten "$last"; else break; fi
  done
  if [ -z "$d" ]; then ERG+=("$t: Leitfaden NICHT fertig"); return; fi
  if kasten_ok "$d" "$p"; then ERG+=("$t: Leitfaden + Kasten ok ($(basename "$d"))")
  else ERG+=("$t: Leitfaden ok, Kasten NICHT sauber – pruefung.md ansehen ($(basename "$d"))"); fi
}

kasten() {  # $1 Präfix, $2 Thema des alten Leitfadens (z. B. wb_leitfaden), $3 Zusatz zum Auftrag (optional)
  local p="$1" quelle t d v last
  t="$(echo "$2" | sed 's/_leitfaden$//')_kasten"
  for d in $(ls -d "$OUT"/*_sekretaer_"$t" 2>/dev/null | sort -r); do
    if kasten_ok "$d" "$p" && ! grep -q '"status": "verworfen"' "$d/status.json"; then
      ERG+=("$t: schon sauber ($(basename "$d")), nicht neu geschrieben"); return 0; fi
  done
  quelle=$(ok_leitfaden "$2")
  if [ -z "$quelle" ]; then ERG+=("$t: KEIN fertiger Leitfaden-Lauf für $2 gefunden"); return 1; fi
  for v in 1 2 3; do
    echo "=== $(date +%H:%M) Kasten $t aus $(basename "$quelle") (Versuch $v)" | tee -a "$LOG"
    python3 scripts/agent/secretary.py "$p. ${3:-}" --thema "$t" --kasten-aus "$(basename "$quelle")" --praefix "$p" \
      --budget 0.5 --max-turns 40 2>&1 | tee -a "$LOG"
    last=$(ls -d "$OUT"/*_sekretaer_"$t" 2>/dev/null | sort | tail -1)
    if limit_abbruch "$last" && [ "$v" -lt 3 ]; then verwerfen_und_warten "$last"; else break; fi
  done
  if kasten_ok "$last" "$p"; then ERG+=("$t: Kasten ok ($(basename "$last"))"); return 0; fi
  ERG+=("$t: Kasten NICHT sauber – pruefung.md ansehen ($(basename "$last"))"); return 1
}

G="Schreibe den Quellen-Leitfaden (leitfaden.md und leitfaden_belege.md), kasten.md und befunde.md mit Länder-Stichprobe DB gegen Rohdatei für DEU, USA, JPN, BRA, NGA (wo vorhanden; je Code mindestens zwei Land-Jahre, Abweichungen mit Größe nennen). Keine metadata.sql. Lies zuerst den Loader (read_text mit Pfad ab Repo-Wurzel, scripts/pipeline/...), damit du weißt, was genau geladen und gerechnet wurde, und prüf per sql_query, welche Codes, Jahre (time_period) und wie viele Länder in der DB stehen. Prüf auch die Rohdaten selbst: Stand/Version, Zeilen und Spalten, ob der Loader-Pfad zur Datei passt, auffällige Werte. Excel-Dateien mit table_to_text lesen. Kann eine Datei nicht gelesen werden oder fehlt sie, ist das ein Befund in befunde.md, kein Grund zu raten. Methodik nur mit Beleg (Datei und Zeile oder abgerufene URL), nicht aus dem Gedächtnis; was nicht belegt ist, als offen markieren. Belege außerhalb des Referenzordners mit Pfad ab Repo-Wurzel angeben. Abschnitt 7: ein Steckbrief je DB-Code mit dem Wortlaut der Quelle, soweit belegt; bei Codes, die erst unser Loader berechnet, die Rechnung aus dem Loader beschreiben (mit Zeile)."
E="Alle drei Energie-Urheber (EI, EMBER, EIA) kommen über einen Loader aus der OWID-Datei owid-energy-data.csv (scripts/pipeline/environment/load_owid_energy.py, Z. 24–61). Den Bezugsweg beschreibt schon der Leitfaden scripts/agent/output/2026-11-23_2106_sekretaer_owid_energy_leitfaden/leitfaden.md – lesen, nicht wiederholen, nur kurz verweisen. Dieser Leitfaden handelt vom Urheber selbst: wer, wie erhoben, welche Ausgabe OWID übernimmt, wie sich die Original-Reihe von der OWID-Spalte unterscheidet (Einheit, Umrechnung, Lücken), Nutzungsbedingungen des Urhebers und von OWID. Kurz halten: weniger Steckbriefe, nur die Codes dieses Präfixes. Im Kasten: Wer = Urheber, Bezugsweg OWID dahinter."

# --- Teil 1: neue Leitfäden ---
leitfaden pwt PWT 1.0 "PWT (Penn World Table 11.0, GGDC Groningen, 21 Codes PWT:*). Loader: scripts/pipeline/economy/load_pwt.py (FILE Z. 45 zeigt auf data/raw/Manuell_27-05/…; lokal liegt die Datei unter data/raw/economy/pwt110_Penn World Table.xlsx – festhalten, ob der Pfad stimmt). Lokal auch data/raw/reference/pwt110_whats_new.txt. Doku per WebFetch von rug.nl/ggdc/productivity/pwt (User Guide, Variablen-Definitionen; Blatt 'Legend' in der xlsx). Pflichtfragen: (1) rgdpe gegen rgdpo und cgdpe/cgdpo: wann welche Reihe (Vergleich über Länder oder über Zeit). (2) Preisbasis (2021 USD, chained PPPs) laut Quelle gegen die Namen im Loader. (3) Einheiten pop/emp (Millionen), hc (Index), Anteile. (4) Datenqualität-Grade (i_xr, i_outlier o. Ä.) und ob der Loader sie berücksichtigt. (5) Neu in 11.0 gegenüber 10.x. (6) Nutzungsbedingungen (CC BY 4.0?) und Zitierpflicht."
leitfaden ghi GHI 0.8 "GHI (Global Hunger Index 2025, Concern Worldwide/Welthungerhilfe/IFHV, 1 Code GHI:*). Loader: scripts/pipeline/health/load_ghi.py (Datei data/raw/health/2025_global Hunger index.xlsx, Blatt 'GHI Scores 2025'). Ältere Ausgaben lokal: data/raw/health/2022_…csv, 2023 …csv, 2024_…xlsx, archive_global hunger index.zip. Doku per WebFetch von globalhungerindex.org (Methodology, FAQ). Pflichtfragen: (1) Die vier Komponenten (Unterernährung, Wachstumsverzögerung, Auszehrung, Kindersterblichkeit) und ihre Gewichte. (2) Skala 0–100 und Schweregrade; Richtung (höher = schlechter). (3) Vergleichbarkeit: Werte sind nur innerhalb einer Ausgabe vergleichbar – laden wir Jahre aus einer Ausgabe (Stützjahre 2000, 2008, 2016, 2025)? Mit Zeile im Loader. (4) Länder ohne Score (Datenlage) und Länder mit hohem Einkommen, die nicht bewertet werden. (5) Formelzellen ohne gespeicherten Wert (table_to_text markiert sie) – betreffen sie geladene Werte? (6) Nutzungsbedingungen."
leitfaden sipri SIPRI 0.8 "SIPRI (SIPRI Military Expenditure Database, 1 Code SIPRI:milex_gdp). Kein eigener Loader: geladen über OWID in scripts/pipeline/governance/load_fsi_gitoc_owid.py (Z. 82–84, Datei data/raw/governance/sipri_military_expenditure.csv). Doku per WebFetch von sipri.org (Military Expenditure Database, Sources and methods, Definition of military expenditure) und der OWID-Grapher-Seite zur Reihe. Pflichtfragen: (1) SIPRI-Definition von Militärausgaben (was zählt, was nicht: z. B. paramilitärische Kräfte, Pensionen). (2) Anteil am BIP: welches BIP (Quelle der BIP-Werte), laufende Preise. (3) Kennzeichnung von Schätzungen und unsicheren Werten bei SIPRI – übernimmt OWID sie, übernimmt der Loader sie? (4) Welche SIPRI-Ausgabe steckt in der OWID-Datei (Stand). (5) Nutzungsbedingungen SIPRI und OWID."
leitfaden ei EI 1.0 "EI (Energy Institute, Statistical Review of World Energy, Präfix EI). $E"
leitfaden ember EMBER 1.0 "EMBER (Ember, Yearly Electricity Data, Präfix EMBER). $E"
leitfaden eia EIA 1.0 "EIA (U.S. Energy Information Administration, International Energy Statistics, Präfix EIA). $E"

# --- Teil 2: Kasten-Pilot ---
PILOT_OK=1
kasten WB wb_leitfaden "Hinweis: 253 Codes, viele Kategorien – im Was die Breite benennen, nicht einzelne Reihen." || PILOT_OK=0
kasten VDEM vdem_leitfaden || PILOT_OK=0
kasten ILO ilo_leitfaden || PILOT_OK=0

# --- Teil 3: übrige alte Leitfäden (nur nach sauberem Pilot) ---
if [ "$PILOT_OK" -eq 1 ]; then
  kasten ACLED acled_leitfaden
  kasten ATOP atop_leitfaden
  kasten EDELMAN edelman_leitfaden
  kasten FAO_FOOD fao_food_leitfaden "Der Leitfaden deckt auch FAO_FOOD_GRP; Bei-uns-Zahlen nur für FAO_FOOD, FAO_FOOD_GRP im Was erwähnen."
  kasten HOFSTEDE hofstede_leitfaden
  kasten OWID_CO2 owid_co2_leitfaden
  kasten PEW_REL pew_rel_leitfaden
  kasten UNDP undp_leitfaden
  kasten UNHCR unhcr_leitfaden
  kasten UNVOTE unvote_leitfaden
  kasten WEF_GGGI wef_leitfaden
  kasten WID wid_leitfaden
  kasten WVS wvs_leitfaden
  kasten POLITY5 polity5
else
  ERG+=("Teil 3 ÜBERSPRUNGEN: Kasten-Pilot nicht sauber – erst die Pilot-Läufe lesen.")
fi

# --- Teil 4: nur nach CI-177 (Live-Lauf der neuen Loader FH, HENLEY, TI, WHR, GITOC, FSI, KOF) ---
# -X: ~/.psqlrc nicht lesen (sonst steht z. B. "Pager-Verwendung ist aus." vor der Zahl, Befund 26.11.)
FH_STATUS=$(psql -X -q -d country_intelligence -tAc "SELECT count(*) FROM indicators WHERE indicator_code = 'FH:STATUS'" 2>&1)
echo "=== $(date +%H:%M) Prüfung CI-177: FH:STATUS-Werte = $FH_STATUS" | tee -a "$LOG"
if [[ "$FH_STATUS" =~ ^[0-9]+$ ]] && [ "$FH_STATUS" -gt 0 ]; then
  leitfaden fh FH 1.0 "FH (Freedom House, Freedom in the World, 3 Codes FH:PR, FH:CL, FH:STATUS). Loader: scripts/pipeline/governance/load_freedom_house.py (neu seit CI-177, Datei data/raw/governance/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx). Doku per WebFetch von freedomhouse.org (Methodology, Scoring). Pflichtfragen: (1) Skalen PR und CL 1–7, 1 = am freiesten (Richtung!), Status F/PF/NF und wie er aus PR+CL entsteht. (2) Ausgabejahr gegen Berichtszeitraum; Ausgaben 1982–1989 mit Zeitraum statt Jahr – wie bucht der Loader sie (Endjahr, mit Zeile). (3) Länder gegen Gebiete (Territories) – lädt der Loader Gebiete? (4) Methodikwechsel (Punktesystem 0–100 seit 2006) und ob die Teilwerte bei uns fehlen. (5) Nutzungsbedingungen."
  leitfaden fsi FSI 0.8 "FSI (Fragile States Index, Fund for Peace, 13 Codes FSI:*). Loader: scripts/pipeline/governance/load_fsi.py (neu seit CI-177, Datei data/raw/governance/fragile_states_index.xlsx, Blatt 'FSI 2006-2022'). Doku per WebFetch von fragilestatesindex.org (Methodology, Indicators). Pflichtfragen: (1) Die 12 Indikatoren in vier Gruppen, Skala 0–10 je Indikator, Gesamt 0–120, Richtung (höher = fragiler). (2) Methode (CAST-Rahmen: Inhaltsanalyse, quantitative Daten, Expertenprüfung). (3) Die Datei reicht 2006–2022, wir laden nur 2022 – warum (mit Zeile)? (4) Vergleichbarkeit über die Jahre laut Quelle. (5) Nutzungsbedingungen."
  kasten KOF kof_leitfaden
  kasten GITOC gitoc_leitfaden
  kasten WHR whr_leitfaden
  kasten TI ti_leitfaden "Kasten neu wegen CI-177 (Bei-uns-Zahlen geändert)."
  kasten HENLEY henley_leitfaden "Kasten neu wegen CI-177 (Bei-uns-Zahlen geändert)."
else
  ERG+=("Teil 4 ÜBERSPRUNGEN: CI-177 noch nicht live gelaufen (FH:STATUS = $FH_STATUS). Nach dem Lauf diese Serie erneut starten – Fertiges wird übersprungen.")
fi

echo; echo "===== Zusammenfassung =====" | tee -a "$LOG"
for z in "${ERG[@]}"; do echo "$z" | tee -a "$LOG"; done
echo "Danach: Pilot-Kästen WB/VDEM/ILO gegen den Leitfaden lesen (Claude), dann Kästen und neue Leitfäden nach Notion (CI-169)." | tee -a "$LOG"
