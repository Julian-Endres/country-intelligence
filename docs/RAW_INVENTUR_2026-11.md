# Rohdaten-Inventur November 2026

**Stand:** 14.11.2026 · Backlog #134 · nur lesend erhoben, nichts verschoben oder gelöscht.

## Kurzfassung

- `data/raw` enthält **469 Dateien, 6,6 GB** (Summe der Dateigrößen; `du` zeigt 6,7 GB). 394 stammen aus `backups/data_raw_20260711.tar.gz`, 75 lagen schon vorher dort (`comtrade/` 2, `reference/` 73).
- **120 Dateien (5,1 GB) werden von einem Loader gelesen** und ihre Daten sind in der DB. **37 Dateien (1,4 GB) liest kein Loader.** 75 Dateien sind Belege für den Sekretär. 231 Dateien sind ND-GAIN, das nicht in der DB ist.
- **31 von 45 Rohdaten-Pfaden in den Loadern zeigen ins Leere.** Die Dateien liegen im Archiv nach Themen sortiert, die Loader erwarten sie in `Manuell_27-05/` oder direkt in `data/raw/`. Zwei Loader (`load_vdem.py`, `load_freedom_house.py`) haben feste Linux-Pfade.
- **69 Gruppen inhaltsgleicher Dateien**, 83 Dateien sind überzählig. Fast alle liegen in ND-GAIN.
- Drei Quellen sind in der DB, haben aber keine Rohdatei: **FAO_LAND** (Zip fehlt), **politics.coups** (keine Datei, kein Loader), **OLYMPICS** (leer, Loader lädt per URL).

## Herkunft der Zahlen

| Zahl | Beleg |
|---|---|
| Dateien, Größen, Zuordnung | Skript über `data/raw`, 14.11., 469 Dateien, 0 ohne Zuordnung |
| Prüfsummen, Dubletten | `scripts/agent/output/2026-11-14_raw_inventur/raw_sha256.txt` (469 Zeilen, 0 Fehler) |
| Zip-Inhalte | `…/raw_zip_inhalt.txt` (9 Archive) |
| Codes, Werte, Tabellenzeilen | `…/db_quelleninventar.txt`, `…/db_zuordnung.txt` (Abfragen vom 10.11., am 14.11. neu ausgeführt) |
| Loader-Pfade | `grep` über `scripts/pipeline` und `scripts/experimental`, je Pfad mit `test -e` geprüft |

## Fundstücke zu offenen Punkten

| Backlog | Befund |
|---|---|
| #102 Hofstede | CSV vorhanden, zweimal identisch: `culture/6-dimensions.csv` und `reference/hofstede_6dimensions_2015-08-16.csv`. 111 Datenzeilen, Spalte `ctr` mit eigenen Kürzeln, Bosnien mit `#NULL!`. |
| #93 ND-GAIN | Rohdaten vorhanden: `environment/ndgain/` (18 CSV) und `environment/ndgain_alt/` (213 CSV). 15 Zeitreihen 1995–2023 mit je 192 Ländern, also höchstens 83.520 Werte. Alle 18 Dateien aus `ndgain/` liegen identisch in `ndgain_alt/`. Die rund 43.000 Werte vom Mai entsprechen etwa 8 Dateien (**Schätzung**). |
| #9 Olympics | Keine Rohdatei. `load_olympics.py` lädt vier CSV direkt von OWID. |
| #128 UNDP | Importdatei ist `demographics/hdr-data_2.csv` (1.441 Datenzeilen). Bolivien-MPI darin: 0,023 / 5,8 / 39,6, Jahr 2023 (Survey EDSA/BLSS 2023). Die DB stimmt mit der Datei überein. NaN und CAR nicht geprüft. |
| #78 Juni-Dateien | Nicht gefunden, weder als Datei im Repo noch in den 9 Zip-Archiven. |
| #69 SIPRI, UNODC | Beide haben einen Ladeweg: `governance/load_fsi_gitoc_owid.py` liest `sipri_military_expenditure.csv` (8.540 Zeilen, OWID-Export) und `owid_homicide_*`, `owid_prison_*`. Der Loader schreibt aber Codes mit Präfix `OWID_SOCIAL:`, die es in der DB nicht mehr gibt. |
| #69 Coups | `history/CSPCoupsAnnualv2021_…xls` ist der Coup-Datensatz des Center for Systemic Peace (10.464 Land-Jahre), nicht Cline Center. Für `politics.coups` (957 Zeilen) gibt es weder Rohdatei noch Loader. |
| #69 Reuters | 14 PDF 2012–2025 in `social/Reuters/`, Loader fehlt weiter. |
| #129 GITOC | `governance/global_oc_index.xlsx` (298.951 Bytes), Blätter `2021_dataset`, `2023_dataset`, `2025_dataset` laut Loader. `gitoc_crime_index.xlsx` hat 0 Bytes. |

## Quellen in der DB ohne Rohdatei

| Quelle | Lage |
|---|---|
| FAO_LAND (13 Codes, 134.130 Werte) | Loader erwartet `Inputs_LandUse_E_All_Data_(Normalized).zip` als Argument, die Datei fehlt. |
| CLINE / `politics.coups` (957 Zeilen) | Keine Rohdatei, kein Loader. |
| OLYMPICS (0 Codes) | Leer. Loader lädt per URL. |
| COW | Nur `cow_interstate_wars.csv`; die Intrastate-Datei fehlt (2 Codes ohne Werte, #63). |
| TI | `load_cpi.py` lädt über `owid.catalog`; `economy/CPI2025_Results.xlsx` liest niemand. |
| Über API oder URL geladen, kein lokaler Abzug | WB, WHO, ILO, UNHCR, GBIF, NOBEL, OPENMETEO, UNESCO_ICH, UNESCO_WHC, OWID_CO2, EI, EIA, Ember, RSF, EPR, HENLEY, GLOTTOLOG, SAMAYO, WEF_GGGI, REST, COMTRADE |

## Auffälligkeiten

- **9 Dateien `reference/wb_*.json` sind 140 Bytes groß.** Sechs davon sind identisch und enthalten die API-Fehlermeldung „Invalid value“ statt Daten.
- `reference/pwt110.xlsx` und `economy/pwt110_Penn World Table.xlsx` sind gleich groß (5.839.841 Bytes), haben aber verschiedene Prüfsummen.
- Die KOF-Datei `…22_07_53.xlsx` liegt identisch in `Manuell_27-05/ATOP/` und `Manuell_27-05/KOF/`.
- `dyadic_formatv3.csv` (1,2 GB) liegt neben ihrem Zip (52 MB).
- Drei OWID-Reihen (Migration, Urbanisierung, Jugendarbeitslosigkeit) stehen im Loader, in der DB gibt es dazu keinen Code unter Quelle 53. Verbleib offen.
- `history/load_coups.py` ist eine Kopie von `load_ddr.py` (bekannt, #69).

## Zielstruktur (Entscheidung Julian, 14.11.2026)

- **Ablage flach nach Quelle:** `data/raw/<kürzel>/<version oder datum>/`. Belege für den Sekretär getrennt in `data/reference/<kürzel>/`. Ungenutztes vorerst in `data/raw/_ungenutzt/`.
- **Zuordnungsdatei** im gemeinsamen Modul (#110): Kürzel → Ordner, Themen, Version, Loader. Loader fragen den Pfad über das Kürzel ab, kein fester Pfad im Skript.
- **Themen-Ansicht** `data/nach_thema/<01–10>/<kürzel>`: nur Verknüpfungen auf die Quellen-Ordner, per Skript erzeugt. Eine Quelle darf in mehreren Themen stehen.
- **`data/raw/INDEX.md`**, aus der Zuordnungsdatei erzeugt: Kürzel, Name, Themen, Inhalt, Version, Loader.
- Ein Suchbefehl (`scripts/raw.py`) erst bei Bedarf.
- Umzug in einem Schritt mit Liste alt → neu und Prüfsummen-Kontrolle vorher und nachher, danach neues Backup. Umsetzung im Backlog: #135 (Umzug und Pfade), #136 (ungenutzte Rohdaten), #137 (fehlerhafte WB-Belege), #138 (Backup), #139 (FAO_LAND).

## Inventur je Datei

Spalte „Pfad“: ok = der im Loader genannte Pfad existiert; „–“ = kein fester Pfad im Loader.

| Datei | Größe | Quelle | Loader | Pfad | In der DB | Backlog | Status |
|---|---|---|---|---|---|---|---|
| `Manuell_27-05/2026_02_06_ga_voting.csv` | 347,4 MB | UNVOTE | international/load_un_voting*.py (5 Skripte) | ok | UNVOTE: 16 Codes, 151.205 Werte | #71 | genutzt |
| `Manuell_27-05/ATOP 5.1 (.csv)/atop5_1sy.csv` | 1,2 MB | ATOP | international/load_atop.py | ok | ATOP: 6 Codes, 66.474 Werte |  | genutzt |
| `Manuell_27-05/ATOP/atop_5_1_codebook.pdf` | 462 KB | ATOP Codebook | keiner | – | – |  | Beleg |
| `Manuell_27-05/ATOP/kof_data_export_2026-05-28_22_07_53.xlsx` | 1,9 MB | KOF (im falschen Ordner) | keiner | – | – |  | Dublette von KOF/…22_07_53.xlsx |
| `Manuell_27-05/IGO Membership/IGO-Codebook_v3_short-copy.pdf` | 125 KB | IGO Codebook | keiner | – | – |  | Beleg |
| `Manuell_27-05/IGO Membership/dyadic_formatv3.csv` | 1,2 GB | IGO | international/load_igo.py | ok | IGO: 3 Codes, 40.077 Werte |  | genutzt |
| `Manuell_27-05/IGO Membership/dyadic_formatv3.zip` | 51,8 MB | IGO (Archiv der CSV daneben) | keiner | – | – |  | Archiv neben entpackter Datei |
| `Manuell_27-05/KOF/kof_data_export_2026-05-28_22_06_58.xlsx` | 10,9 MB | KOF | international/load_kof.py | ok | KOF: 9 Codes, 86.290 Werte |  | genutzt |
| `Manuell_27-05/KOF/kof_data_export_2026-05-28_22_07_53.xlsx` | 1,9 MB | KOF (zweiter Export, Inhalt ungeprüft) | keiner | – | nein |  | ungenutzt |
| `bench/qog_std_cs_jan26_Quality of Government (QoG).csv` | 1,6 MB | QoG Standard Jan 2026 | keiner (load_gender_gap.py lädt Jan 2025 per URL) | – | nein |  | ungenutzt |
| `comtrade/reference/Reporters.json` | 63 KB | COMTRADE Referenzlisten | economy/load_comtrade_v2.py | ok | trade.trade_products 8.163.977, trade.trade_partners 1.279.868 Zeilen | #88, #110 | genutzt |
| `comtrade/reference/partnerAreas.json` | 75 KB | COMTRADE Referenzlisten | economy/load_comtrade_v2.py | ok | trade.trade_products 8.163.977, trade.trade_partners 1.279.868 Zeilen | #88, #110 | genutzt |
| `culture/6-dimensions.csv` | 4 KB | HOFSTEDE | culture/load_hofstede.py (Datei als Argument) | – | HOFSTEDE: 6 Codes, 293 Werte (falsch zugeordnet) | #102 | genutzt; identisch mit reference/hofstede_…csv |
| `culture/Religious-Composition-2010-2020-dataset_Pew Research.zip` | 287 KB | PEW_REL | culture/load_pew_religion.py | Pfad im Loader falsch | PEW_REL: 8 Codes, 3.184 Werte | #1 | genutzt |
| `culture/WHR26_Data_Figure_2.1.xlsx` | 130 KB | WHR | culture/load_whr.py (Datei als Argument) | – | WHR: 7 Codes, 8.095 Werte |  | genutzt |
| `culture/WVS_Time_Series_1981-2022_csv_v5_0.csv` | 1,3 GB | WVS | demographics/load_wvs.py (Datei als Argument) | – | WVS: 21 Codes, 5.625 Werte | #71 | genutzt |
| `culture/boxoffice/Mojo_budget_data.csv` | 700 KB | Box Office Mojo | keiner | – | nein |  | ungenutzt |
| `culture/boxoffice/Mojo_budget_update.csv` | 1,5 MB | Box Office Mojo | keiner | – | nein |  | ungenutzt |
| `culture/imdb_akas.tsv.gz` | 474,3 MB | IMDB | culture/load_imdb.py | Pfad im Loader falsch | IMDB: 3 Codes, 30.820 Werte |  | genutzt |
| `culture/imdb_basics.tsv.gz` | 211,8 MB | IMDB | culture/load_imdb.py | Pfad im Loader falsch | IMDB: 3 Codes, 30.820 Werte |  | genutzt |
| `demographics/hdr-data(2).xlsx` | 88 KB | UNDP (xlsx-Export, Inhalt ungeprüft) | keiner | – | nein |  | ungenutzt |
| `demographics/hdr-data_2.csv` | 230 KB | UNDP | demographics/load_undp.py (Datei als Argument) | – | UNDP: 19 Codes, 37.456 Werte | #128 | genutzt |
| `demographics/owid_migration_stock_total.csv` | 59 KB | OWID (Migration, Urbanisierung, Jugendarbeitslosigkeit) | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | nicht belegt (kein Code unter Quelle 53 außer UNODC/WHO/WB) | #2 | Verbleib in der DB offen |
| `demographics/owid_urban_population_share.csv` | 621 KB | OWID (Migration, Urbanisierung, Jugendarbeitslosigkeit) | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | nicht belegt (kein Code unter Quelle 53 außer UNODC/WHO/WB) | #2 | Verbleib in der DB offen |
| `economy/CPI2025_Results.xlsx` | 2,9 MB | TI (CPI 2025) | keiner (load_cpi.py lädt über owid.catalog) | – | TI: 1 Code, 2.286 Werte bis 2024; diese Datei nicht geladen |  | ungenutzt |
| `economy/mpd2023_web.xlsx` | 4,7 MB | MADDISON | economy/load_maddison.py (Datei als Argument) | – | MADDISON: 2 Codes, 38.549 Werte |  | genutzt |
| `economy/owid_poverty_headcount.csv` | 2,1 MB | WB:poverty_3_day über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | 1 Code, 2.274 Werte unter Quelle 53 | #2 | genutzt |
| `economy/owid_youth_unemployment.csv` | 181 KB | OWID (Migration, Urbanisierung, Jugendarbeitslosigkeit) | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | nicht belegt (kein Code unter Quelle 53 außer UNODC/WHO/WB) | #2 | Verbleib in der DB offen |
| `economy/pwt110_Penn World Table.xlsx` | 5,6 MB | PWT 11.0 | economy/load_pwt.py | Pfad im Loader falsch | PWT: 21 Codes, 211.399 Werte | #1 | genutzt |
| `economy/wid_all_data.zip` | 814,4 MB | WID | economy/load_wid.py | Pfad im Loader falsch | WID: 38 Codes, 274.558 Werte | #1 | genutzt |
| `economy/worldbank_poverty_headcount.csv` | 17 KB | World Bank (Einzelabzug Armut) | keiner | – | nein |  | ungenutzt |
| `en.openfoodfacts.org.products.csv.gz` | 1,2 GB | Open Food Facts | keiner | – | nein |  | ungenutzt |
| `governance/ACLED/number_of_demonstration_events_by_country-year_as-of-03Jul2026.xlsx` | 48 KB | ACLED | governance/load_acled.py | ok | ACLED: 5 Codes, 13.917 Werte | #66 | genutzt |
| `governance/ACLED/number_of_events_targeting_civilians_by_country-year_as-of-03Jul2026.xlsx` | 45 KB | ACLED | governance/load_acled.py | ok | ACLED: 5 Codes, 13.917 Werte | #66 | genutzt |
| `governance/ACLED/number_of_political_violence_events_by_country-year_as-of-03Jul2026.xlsx` | 46 KB | ACLED | governance/load_acled.py | ok | ACLED: 5 Codes, 13.917 Werte | #66 | genutzt |
| `governance/ACLED/number_of_reported_civilian_fatalities_by_country-year_as-of-03Jul2026.xlsx` | 45 KB | ACLED | governance/load_acled.py | ok | ACLED: 5 Codes, 13.917 Werte | #66 | genutzt |
| `governance/ACLED/number_of_reported_fatalities_by_country-year_as-of-03Jul2026.xlsx` | 48 KB | ACLED | governance/load_acled.py | ok | ACLED: 5 Codes, 13.917 Werte | #66 | genutzt |
| `governance/Country_and_Territory_Ratings_and_Statuses_FIW_1973-2024.xlsx` | 209 KB | FH | governance/load_freedom_house.py | Pfad im Loader falsch (fester Linux-Pfad) | FH: 3 Codes, 15.930 Werte | #63 | genutzt |
| `governance/MPDataset_MPDS2025a.csv` | 3,3 MB | MARPOR | governance/load_marpor.py | Pfad im Loader falsch | politics.marpor_elections 5.285 Zeilen | #81 | genutzt |
| `governance/UCDP/BattleDeaths_v26_1_conf.csv` | 307 KB | UCDP | governance/load_ucdp*.py (4 Skripte) | ok | UCDP: 3 Codes, 6.396 Werte; 5 politics.conflict*-Tabellen | #66 | genutzt |
| `governance/UCDP/GEDEvent_v26_1.csv` | 261,3 MB | UCDP | governance/load_ucdp*.py (4 Skripte) | ok | UCDP: 3 Codes, 6.396 Werte; 5 politics.conflict*-Tabellen | #66 | genutzt |
| `governance/UCDP/NonState_v26_1.csv` | 429 KB | UCDP | governance/load_ucdp*.py (4 Skripte) | ok | UCDP: 3 Codes, 6.396 Werte; 5 politics.conflict*-Tabellen | #66 | genutzt |
| `governance/UCDP/OneSided_v26_1.xlsx` | 130 KB | UCDP | governance/load_ucdp*.py (4 Skripte) | ok | UCDP: 3 Codes, 6.396 Werte; 5 politics.conflict*-Tabellen | #66 | genutzt |
| `governance/UCDP/UcdpPrioConflict_v26_1.csv` | 507 KB | UCDP | governance/load_ucdp*.py (4 Skripte) | ok | UCDP: 3 Codes, 6.396 Werte; 5 politics.conflict*-Tabellen | #66 | genutzt |
| `governance/V-Dem-CY-Full+Others-v16.csv` | 387,5 MB | VDEM v16 | governance/load_vdem.py | Pfad im Loader falsch (fester Linux-Pfad) | VDEM: 59 Codes, 1.126.533 Werte | #6 | genutzt |
| `governance/fragile_states_index.xlsx` | 60 KB | FSI | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | FSI: 13 Codes, 2.249 Werte |  | genutzt |
| `governance/gitoc_crime_index.xlsx` | 0 B | GITOC (0 Bytes) | keiner | – | – |  | defekt, leere Datei |
| `governance/global_oc_index.xlsx` | 292 KB | GITOC | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | GITOC: 17 Codes, 8.110 Werte | #129 | genutzt |
| `governance/owid_homicide_count.csv` | 151 KB | UNODC über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | UNODC: 4 Codes, 10.806 Werte (unter Quelle 53) | #2, #69 | genutzt |
| `governance/owid_homicide_rate.csv` | 176 KB | UNODC über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | UNODC: 4 Codes, 10.806 Werte (unter Quelle 53) | #2, #69 | genutzt |
| `governance/owid_prison_occupancy_capacity.csv` | 5 KB | UNODC über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | UNODC: 4 Codes, 10.806 Werte (unter Quelle 53) | #2, #69 | genutzt |
| `governance/owid_prison_population_rate.csv` | 50 KB | UNODC über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | UNODC: 4 Codes, 10.806 Werte (unter Quelle 53) | #2, #69 | genutzt |
| `governance/parties_MPDataset_MPDS2025a.csv` | 150 KB | MARPOR | governance/load_marpor.py | Pfad im Loader falsch | politics.political_parties 1.412 Zeilen | #81 | genutzt |
| `governance/parties_long_MPDataset_MPDS2025a_Manifesto.csv` | 437 KB | MARPOR (Langformat) | keiner | – | nein |  | ungenutzt |
| `governance/sipri_military_expenditure.csv` | 296 KB | SIPRI über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | SIPRI: 1 Code, 8.523 Werte (ohne source_id) | #1, #69 | genutzt |
| `governance/unodc_homicide.xlsx` | 43 KB | UNODC (Originaldatei) | keiner | – | nein | #2 | ungenutzt |
| `health/2022_global hunger index.csv` | 5 KB | GHI | health/load_ghi.py | ok | GHI: 1 Code, 6.535 Werte | #1 | genutzt |
| `health/2023 global hunger index.csv` | 5 KB | GHI | health/load_ghi.py | ok | GHI: 1 Code, 6.535 Werte | #1 | genutzt |
| `health/2024_global hunger index.xlsx` | 57 KB | GHI | health/load_ghi.py | ok | GHI: 1 Code, 6.535 Werte | #1 | genutzt |
| `health/2025_global Hunger index.xlsx` | 57 KB | GHI | health/load_ghi.py | ok | GHI: 1 Code, 6.535 Werte | #1 | genutzt |
| `health/archive_global hunger index.zip` | 27 KB | GHI | health/load_ghi.py | ok | GHI: 1 Code, 6.535 Werte | #1 | genutzt |
| `health/fao_food.zip` | 52,3 MB | FAO_FOOD, FAO_FOOD_GRP | health/load_fao_food.py, load_fao_food_groups.py (Datei als Argument) | – | 3 Codes, 7.233 Werte; 26 Codes, 61.683 Werte |  | genutzt |
| `health/owid_alcohol_binge_drinking.csv` | 105 KB | WHO über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | WHO: 4 Codes, 13.072 Werte (unter Quelle 53) | #2 | genutzt |
| `health/owid_alcohol_consumption_per_capita.csv` | 102 KB | WHO über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | WHO: 4 Codes, 13.072 Werte (unter Quelle 53) | #2 | genutzt |
| `health/owid_drug_deaths_who.csv` | 109 KB | WHO über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | WHO: 4 Codes, 13.072 Werte (unter Quelle 53) | #2 | genutzt |
| `health/owid_tobacco_prevalence.csv` | 25 KB | WHO über OWID | governance/load_fsi_gitoc_owid.py | Pfad im Loader falsch | WHO: 4 Codes, 13.072 Werte (unter Quelle 53) | #2 | genutzt |
| `history/COLDAT_colonies.csv` | 26 KB | COLDAT (Kolonien) | keiner | – | nein |  | ungenutzt |
| `history/COLDAT_dyads.csv` | 57 KB | COLDAT | history/load_coldat.py | Pfad im Loader falsch | international.colonial_history 161 Zeilen | #81 | genutzt |
| `history/CSPCoupsAnnualv2021_Forcibly Displaced Populations, 1964-2008_U.S. Committee for Refugees and Immigrants (USCRI).xls` | 1,4 MB | CSP Coups 2021 (Dateiname irreführend) | keiner | – | nein; politics.coups nennt Cline Center | #69 | ungenutzt |
| `history/ccpcce_v6_Comparative Constitutions Project.zip` | 810 KB | CCP v6 | history/load_ccp.py | ok | politics.constitutional_events 4.335 Zeilen | #81 | genutzt |
| `history/cow_interstate_wars.csv` | 31 KB | COW | history/load_cow.py (Datei als Argument) | – | COW: 4 Codes, 585 Werte | #63 | genutzt |
| `history/p5v2018_Polity5_Annual Time-Series, 1946-2018.xls` | 4,3 MB | POLITY5 | governance/load_polity5.py | ok | POLITY5: 6 Codes, 101.643 Werte | #1, #89 | genutzt |
| `international/DASID.zip` | 11,3 MB | DASID | international/load_dasid.py | Pfad im Loader falsch | international.diplomatic_relations 1.165.894 Zeilen | #81 | genutzt |
| `international/dataverse_files_Diplometric.zip` | 96,9 MB | DDR | international/load_ddr.py (Kopie: history/load_coups.py) | Pfad im Loader falsch | international.diplomatic_representation 432.645 Zeilen | #69, #81 | genutzt |
| `reference/hofstede_6dimensions_2015-08-16.csv` | 4 KB | HOFSTEDE | keiner (Sekretär-Beleg) | – | – | #102 | Beleg; identisch mit culture/6-dimensions.csv |
| `social/archive_CAF World Giving Index.zip` | 28 KB | CAF_WGI | social/load_caf_wgi.py | Pfad im Loader falsch | CAF_WGI: 4 Codes, 6.964 Werte | #1 | genutzt |
| `social/world_giving_2023_complete.csv` | 5 KB | CAF_WGI | social/load_caf_wgi.py | Pfad im Loader falsch | CAF_WGI: 4 Codes, 6.964 Werte | #1 | genutzt |
| `social/world_giving_2024_complete.csv` | 5 KB | CAF_WGI | social/load_caf_wgi.py | Pfad im Loader falsch | CAF_WGI: 4 Codes, 6.964 Werte | #1 | genutzt |

**Gruppen (gleichartige Dateien zusammengefasst):**

| Ordner | Dateien | Größe | Quelle | Loader | Pfad | In der DB | Backlog | Status |
|---|---|---|---|---|---|---|---|---|
| `Manuell_27-05/ATOP 5.1 (.csv)/` (ATOP-Paket, 11 weitere CSV) | 11 | 39,9 MB | ATOP (übrige Dateien des Pakets) | keiner | – | nein |  | ungenutzt |
| `environment/ndgain/` (ND-GAIN, 18 CSV) | 18 | 1,4 MB | NDGAIN | environment/load_ndgain.py (3 von 18 Dateien als Argument) | – | nein (Quelle fehlt in sources) | #93 | Rohdaten für Neuladen; alle 18 identisch in ndgain_alt/ |
| `environment/ndgain_alt/` (ND-GAIN alt, 213 CSV) | 213 | 12,9 MB | NDGAIN (Originalstruktur des Downloads) | keiner | – | nein | #93 | enthält ndgain/ vollständig, dazu Einzelindikatoren |
| `reference/` (PWT-Belege) | 9 | 11,5 MB | PWT (Handbücher, Legend-Datei) | keiner (Sekretär-Beleg) | – | – |  | Beleg |
| `reference/` (UNDP-Belege) | 5 | 11,3 MB | UNDP HDR 2025 (Bericht, Technical Notes, Zeitreihe) | keiner (Sekretär-Beleg) | – | – | #128 | Beleg |
| `reference/` (V-Dem-Belege) | 8 | 13,7 MB | V-Dem v16 (Codebook, Methodik) | keiner (Sekretär-Beleg) | – | – |  | Beleg |
| `reference/` (WB-Belege) | 50 | 1,8 MB | World Bank API-Abzüge | keiner (Sekretär-Beleg) | – | – |  | Beleg |
| `social/Edelman/` (Edelman, 63 CSV) | 63 | 96 KB | EDELMAN | social/load_edelman.py | ok | EDELMAN: 36 Codes, 12.340 Werte |  | genutzt |
| `social/Reuters/` (Reuters, 14 PDF) | 14 | 171,9 MB | Reuters Digital News Report 2012–2025 | fehlt im Repo (load_reuters_dnr.py) | – | nein | #69 | ungenutzt |
