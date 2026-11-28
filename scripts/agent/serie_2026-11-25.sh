#!/usr/bin/env bash
# Sekretär-Serie 25./26.11.2026 (Metadaten R4.1, erster Einsatz Kasten = Pilot CI-169): je Thema Leitfaden (mit Rohdaten-Prüfung), danach Metadaten je Präfix.
# Wiederanlauf: Bricht ein Lauf am Nutzungslimit ab, wird er verworfen, das Skript wartet 40 min und versucht es
# erneut (höchstens 3 Versuche je Schritt). Andere Fehler: kein neuer Versuch, laut in der Zusammenfassung.
# Wiederholbar: Gibt es schon einen regulär fertigen Leitfaden zum Thema, wird er nicht neu geschrieben;
# batch.py plant nur Codes ein, die noch offen sind (sonst 0 und Ende).
# NICHT parallel zu einer anderen Serie starten.
# Start (Shell, Repo-Wurzel, venv aktiv):  caffeinate -i bash scripts/agent/serie_2026-11-25.sh
cd "$(dirname "$0")/../.." || exit 1
LOG="logs/sekretaer_serie_2026-11-25.log"
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

# Bewusst NICHT in dieser Serie (25.11.): WHO (neuer Loader CI-174 nicht gelaufen, Definitionen nur als HTML #107),
# FSI (neuer Loader CI-177 nicht gelaufen), UNODC (Präfix/Quelle #2), WB (1 Code, Einzelfall).

G="Schreibe den Quellen-Leitfaden (leitfaden.md und leitfaden_belege.md), kasten.md und befunde.md mit Länder-Stichprobe DB gegen Rohdatei für DEU, USA, JPN, BRA, NGA (wo vorhanden; je Code mindestens zwei Land-Jahre, Abweichungen mit Größe nennen). Keine metadata.sql. Lies zuerst den Loader (read_text mit Pfad ab Repo-Wurzel, scripts/pipeline/...), damit du weißt, was genau geladen und gerechnet wurde, und prüf per sql_query, welche Codes, Jahre (time_period) und wie viele Länder in der DB stehen. Prüf auch die Rohdaten selbst: Stand/Version, Zeilen und Spalten, ob der Loader-Pfad zur Datei passt, auffällige Werte. Kann eine Datei nicht gelesen werden (z. B. xlsx, gz) oder fehlt sie, ist das ein Befund in befunde.md, kein Grund zu raten. Methodik nur mit Beleg (Datei und Zeile oder abgerufene URL), nicht aus dem Gedächtnis; was nicht belegt ist, als offen markieren. Belege außerhalb des Referenzordners mit Pfad ab Repo-Wurzel angeben. Abschnitt 7: ein Steckbrief je DB-Code mit dem Wortlaut der Quelle, soweit belegt; bei Codes, die erst unser Loader berechnet, die Rechnung aus dem Loader beschreiben (mit Zeile)."

# --- Teil 1: Pilot Kasten (kleine Quellen, Rohdaten lokal oder per URL) ---
thema cow 1.0 "COW (Correlates of War, Kriegsdaten, 4 Codes COW:interstate_wars, intrastate_wars, total_wars, battle_deaths). Loader: scripts/pipeline/history/load_cow.py (Dateipfade per Argument --interstate/--intrastate). Lokal gefunden: data/raw/history/cow_interstate_wars.csv; eine Intra-State-Datei wurde lokal nicht gefunden – prüfen und festhalten. Doku per WebFetch von correlatesofwar.org (Inter-State War Data v4.0, Intra-State War Data v5.1, Codebooks). Pflichtfragen: (1) Was zählt als Krieg (Schwelle 1.000 Gefechtstote, Zeitraum). (2) Zählt der Loader Kriege je Land-Jahr als laufende oder neu begonnene Kriege; wie entsteht total_wars (Summe? Doppelzählung?). (3) battle_deaths: je Land-Jahr oder je Krieg auf ein Jahr gebucht, Umgang mit fehlenden Werten (-8/-9). (4) Welche Länderzuordnung nutzt der Loader (eigenes Dict COW_TO_ISO3 im Loader oder countries.cow_code)? Stimmen Stichproben-Zuordnungen (z. B. 135, 145)? (5) Nutzungsbedingungen." COW

thema igo 1.0 "IGO (COW Intergovernmental Organizations v3.0, 3 Codes IGO:n_memberships, n_full, n_observer). Loader: scripts/pipeline/international/load_igo.py (liest data/raw/Manuell_27-05/IGO Membership/dyadic_formatv3.csv chunkweise). Codebook lokal: data/raw/Manuell_27-05/IGO Membership/IGO-Codebook_v3_short-copy.pdf. Pflichtfragen: (1) Wie zählt der Loader Mitgliedschaften aus dem dyadischen Format (Dyaden sind Länderpaare – wird ein Land-Jahr mehrfach gezählt?) – Rechnung mit Zeile, Stichprobe gegen eine eigene Zählung. (2) Kodierung Vollmitglied/assoziiert/Beobachter/keins und fehlend (-9, -1) laut Codebook; zählt n_memberships assoziierte mit? (3) Zeitraum (1816–2014?) und Länderzuordnung (COW-Codes). (4) Nutzungsbedingungen." IGO

thema epr 1.0 "EPR (Ethnic Power Relations, ETH Zürich, 3 Codes EPR:n_groups, excluded_share, discriminated_share). Loader: scripts/pipeline/history/load_epr.py (lädt https://icr.ethz.ch/data/epr/core/EPR-2023.csv). Hole die Datei für die Stichprobe mit download_file (gleiche URL), Codebook per WebFetch von icr.ethz.ch (EPR Core 2023). Pflichtfragen: (1) Bedeutung der Machtstatus-Kategorien (monopoly, dominant, senior/junior partner, powerless, discriminated, self-exclusion, irrelevant) und welche der Loader als excluded und discriminated zählt (mit Zeile). (2) Anteile: Bevölkerungsanteil der Gruppen (size) – Summe über 100 % möglich (known_issues nennt NGA 121 %)? (3) Gruppen-Zeiträume (from/to) auf Land-Jahre umgelegt – wie. (4) Länderzuordnung (gwid; CI-172 hatte NGA und SRB in Quarantäne) – Stichprobe NGA/SRB ausdrücklich. (5) Nutzungsbedingungen." EPR

# --- Teil 2: übrige Quellen ohne Leitfaden ---
thema fao_land 1.5 "FAO_LAND (FAOSTAT Land Use, 13 Codes FAO_LAND:country_area, land_area, agricultural_land, cropland, arable_land, permanent_crops, pastures, forest_land, primary_forest, nat_regen_forest, planted_forest, other_land, inland_waters). Loader: scripts/pipeline/environment/load_fao_landuse.py (ZIP Inputs_LandUse_E_All_Data_(Normalized).zip per Argument; lokal nicht gefunden – festhalten). Doku per WebFetch von fao.org/faostat (Domain RL, Definitions and standards). Wenn möglich die aktuelle Datei per download_file für die Stichprobe. Pflichtfragen: (1) Definitionen je Element wörtlich (Land Use Definitions), Einheit 1000 ha. (2) Hierarchie: welche Flächen sind Teilmengen (cropland = arable + permanent crops? agricultural = cropland + pastures?) – Stichprobe, ob die Summen in der DB aufgehen. (3) Flags (A, E, I, …) und ob der Loader geschätzte Werte übernimmt. (4) Länderzuordnung (M49/Area Code), historische Einheiten (UdSSR, Sudan alt) und China-Aggregate. (5) Stand der geladenen Fassung, Nutzungsbedingungen (CC BY 4.0?). Bekannt: AG.LND.FRST.ZS (WB) weicht von der API ab (#106), Vergleich FAO_LAND:forest_land gegen die Weltbank-Reihe ist erwünscht." FAO_LAND

thema gbif 1.5 "GBIF (Global Biodiversity Information Facility, 12 Codes GBIF:*). Loader: scripts/pipeline/environment/load_gbif.py, load_gbif_historical.py, load_gbif_iucn.py (API-Abfragen, Taxon-Keys im Loader). Doku per WebFetch von gbif.org und techdocs.gbif.org (Occurrence API, Facetten, iucnRedListCategory). Pflichtfragen: (1) Zählen die Codes Fundmeldungen (occurrence records) oder Arten? Der Loader nennt sie 'Species Occurrences' – irreführend? (2) Bezug Land: Fundort (country) oder veröffentlichendes Land (publishingCountry)? (3) Jahre: Beobachtungsjahr oder kumuliert; was steht in time_period, wann abgerufen (Werte ändern sich laufend). (4) IUCN-Codes: Kategorie aus welcher Taxonomie-Version. (5) Starke Erfassungsverzerrung (Meldeaktivität statt Artenvielfalt) belegen. (6) Nutzungsbedingungen (Daten je Datensatz CC0/BY/BY-NC)." GBIF

thema openmeteo 1.0 "OPENMETEO (Open-Meteo Historical Weather API, 3 Codes OPENMETEO:temp_mean, precip_sum, sunshine). Loader: scripts/pipeline/environment/load_openmeteo.py (archive-api.open-meteo.com, 2000–2023). Doku per WebFetch von open-meteo.com (Historical Weather API, Datengrundlage ERA5). Pflichtfragen: (1) Für welchen Punkt je Land wird abgefragt (Hauptstadt? Mittelpunkt? Koordinaten-Quelle und Länderzuordnung im Loader, mit Zeile) – ist ein Punkt für große Länder repräsentativ? (2) Aggregation je Jahr (Mittel der Tageswerte, Summe), Einheiten. (3) sunshine: Sonnenscheindauer in Sekunden oder Stunden? (4) Reanalyse-Modell (ERA5/ERA5-Land), Auflösung. (5) Nutzungsbedingungen (CC BY 4.0)." OPENMETEO

thema samayo 0.8 "SAMAYO (samayo/country-json auf GitHub, 5 Codes SAMAYO:*, time_period 'static'). Loader: scripts/pipeline/culture/load_samayo.py (lädt JSON-Dateien von raw.githubusercontent.com/samayo/country-json/master/src/). Hole die Dateien für die Stichprobe mit download_file. Pflichtfragen: (1) Wer pflegt die Daten, woher stammen sie laut README, Stand (letzter Commit), offizielle Quelle? (2) Je Code: Herkunft und Bedeutung (z. B. independence_year bei Ländern ohne Unabhängigkeit, avg_male_height Bezugsjahr). (3) Länderzuordnung über Namen (CI-172 hatte GBR in Quarantäne) – Stichprobe ausdrücklich GBR und Namen mit Sonderzeichen. (4) Nutzungsbedingungen (Lizenz des Repos)." SAMAYO

thema imdb 1.0 "IMDB (IMDb Non-Commercial Datasets, 3 Codes IMDB:movies, tvseries, total). Loader: scripts/pipeline/culture/load_imdb.py (title.basics und title.akas; Loader-Pfad data/raw/imdb_*.tsv.gz, lokal liegen die Dateien unter data/raw/culture/ – festhalten). Doku per WebFetch von developer.imdb.com/non-commercial-datasets. Pflichtfragen: (1) Wie ordnet der Loader einen Titel einem Land zu (akas.region = Veröffentlichungsregion, nicht Produktionsland?) – trägt der Name 'Movies Produced' dann? (2) Zählt ein Titel in mehreren Ländern? (3) Jahr = startYear? (4) Nutzungsbedingungen (nur nicht-kommerziell). Die gz-Dateien kann das Werkzeug evtl. nicht lesen – dann festhalten und die Stichprobe offen lassen." IMDB

thema maddison 0.8 "MADDISON (Maddison Project Database 2023, 2 Codes MADDISON:gdppc, pop). Loader: scripts/pipeline/economy/load_maddison.py (Datei per Argument; lokal data/raw/economy/mpd2023_web.xlsx – xlsx ist mit read_text nicht lesbar, #154; dann Stichprobe offen lassen). Doku per WebFetch von rug.nl/ggdc/historicaldevelopment/maddison (Release 2023, Documentation). Pflichtfragen: (1) gdppc: Preisbasis laut Quelle (2011 USD PPP?) gegen den Namen im Loader. (2) pop: Einheit (Tausend? Millionen?) laut Quelle gegen die Einheit im Loader 'millions'. (3) Zeitraum und Lücken (frühe Jahrhunderte nur Stützjahre). (4) Nutzungsbedingungen (CC BY 4.0) und Zitierpflicht." MADDISON

# --- Teil 3: nur Metadaten (Leitfaden vorhanden) ---
thema wvs 1.0 "" WVS

echo; echo "===== Zusammenfassung =====" | tee -a "$LOG"
for z in "${ERG[@]}"; do echo "$z" | tee -a "$LOG"; done
echo "Morgen: python3 scripts/agent/status.py, dann je Lauf review.py und apply.py; Kästen gegen den Leitfaden lesen (Pilot CI-169)." | tee -a "$LOG"
