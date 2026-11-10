# Sources – candidates

**As of:** 2026-11-10 · Sources not yet loaded, by topic · Counterpart: `SOURCES_AVAILABLE.md`

## Summary

This file lists **only sources that are not in the database**, grouped by the ten domains, plus **Latin America & Bolivia** as a regional block and a **cross-cutting** section with aggregators, portals and API notes. It is the **work list of the source-scout agent** (backlog #25): the agent picks candidates here, checks access and licence, and proposes additions; once a source is loaded, its row moves to `SOURCES_AVAILABLE.md`.

Contents: 01 · 02 · 03 · 04 · 05 · 06 · 07 · 08 · 09 · Regional · Cross-cutting · Appendix

## 01 · Population & Demographics

### Family & relationships

| Quelle | Auth | URL |
|---|---|---|
| **OECD Family Database** | Keine SDMX | oecd.org/en/data/datasets/oecd-family-database |
| **Generations and Gender Survey (GGS-II)** | Free Reg | ggp-i.org |
| **DHS STATcompiler** | Keine | `api.dhsprogram.com` |

### Migration & diaspora

| Quelle | Auth | URL |
|---|---|---|
| **UN DESA International Migrant Stock 2024** | Keine | Excel-Bulk |
| **KNOMAD Bilateral Remittances** | Keine | WB-gehostet (KNOMAD 2024 stillgelegt) |
| **IOM DTM API** | Keine | `dtmapi.iom.int/api/` |

## 02 · Health & Survival

### Health

| Quelle | Indikatoren | Auth | Notiz |
|---|---|---|---|
| **WHO GISAH** | Alkohol ~200 | Keine | In GHO enthalten |
| **IHME GBD Results** | 204 Länder | Free Reg | **Kein API**, nur CSV-Download |
| **UNAIDS AIDSinfo** | 170 Länder | Keine | Excel-Bulk |
| **JMP WASH** | 200+ Länder | Keine | washdata.org |

### Drugs & addiction

| Quelle | Inhalt | Format |
|---|---|---|
| **UNODC dataUNODC** | Beschlagnahmungen, Prävalenz, Homizide | CSV-Bulk |
| **UNODC Coca Bolivia** | Jährliche Monitoring-Reports | PDF/Excel |
| **EUDA** (EU) | EU+NO+TR; Wastewater, Drug Checking | datacatalogue |

**UNODC Bolivia 2024 Warnung:** Methodenbruch → +51% Monitoring-Fläche → Zeitreihe 2023→2024 nicht direkt vergleichbar.

### Trauma & mental health

| Quelle | Inhalt | Zugang |
|---|---|---|
| **IHME GBD** | PTSD, Depression, Suizid, 204 Länder | Free Reg, CSV |
| **WHO Mental Health Atlas** | System-Level, alle 3 Jahre | PDF |
| **Truth Commissions DB** | ~50 Kommissionen | USIP/ICTJ Web |

**Proxy für nationalen Trauma-Index:** IHME GBD PTSD-Prävalenz + UCDP Battle-Deaths/Capita + EM-DAT Total Affected + Truth-Commission-Existenz (Binär).

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **WHO/UNICEF JMP** | WASH household surveys, hygiene | CSV, washdata.org |

## 03 · Education, Science & Innovation

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **OECD PISA** | Student performance | CSV/SAS, oecd.org |

## 04 · Economy, Wealth & Labor

### World Bank – further databases

```python
pip install wbgapi  # Die unverzichtbare Bibliothek
```

Wichtige Sub-Datenbanken (alle via wbgapi abrufbar):

| ID | Name | Inhalt |
|---|---|---|
| 14 | Gender Statistics | Gender-Indikatoren |
| 12 | EdStats | Bildung |
| 16 | HNP | Gesundheit & Bevölkerung |
| 32 | Findex | Financial Inclusion |
| 63 | HCI | Human Capital Index |
| 46 | SDG | Sustainable Development Goals |
| 75 | ESG | Environmental, Social, Governance |

Spezialisierte APIs:
- **PIP** (Poverty): `https://api.worldbank.org/pip/v1/pip`
- **CCKP** (Klima): AWS S3 `s3://wbg-cckp/`
- **WBL** (Women, Business & Law): `wbl.worldbank.org`

### IMF, OECD, Eurostat, BIS

```python
pip install sdmx1  # Für alle SDMX-Quellen
pip install eurostat  # Eurostat-Wrapper
```

| Quelle | Base-URL | Besonderheit |
|---|---|---|
| **IMF** (neu 2025) | `api.imf.org/external/sdmx/3.0/` | IFS aufgelöst in Topic-Datasets |
| **OECD Data Explorer** | `sdmx.oecd.org/public/rest/` | URL nie erraten — aus Developer-Button kopieren |
| **Eurostat** | via `eurostat` Python | JSON-Stat + SDMX 2.1 |
| **BIS** | `stats.bis.org/api/v1/` | Keine Auth |

### Specialised economic sources

| Quelle | Zeitraum | Format |
|---|---|---|
| **Atlas of Economic Complexity** | aktuell | Bulk-CSV (Harvard) |

**OEC Warnung:** Free API seit 2021 abgeschafft.

### Tourism

| Quelle | Auth | Notiz |
|---|---|---|
| **UNWTO Tourism Database** | paid (Vollzugriff) | Free Dashboard für Schlüsselindikatoren |

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **UNWTO Tourism** | Tourist arrivals, receipts | CSV export, e-unwto.org |

## 05 · Infrastructure & Technology

### Public transport & rail

#### Die optimale Drei-Quellen-Strategie

**1. OSM via Overpass API** — aktuellste Rohgeometrie (ODbL):
```overpassql
[out:json][timeout:300];
area["ISO3166-1"="BO"][admin_level=2]->.a;
(way["railway"~"^(rail|narrow_gauge|light_rail|subway|tram|monorail)$"]
    ["service"!~"^(siding|yard|crossover|spur)$"]
    ["railway"!="abandoned"](area.a););
out geom;
```

**2. Wikidata SPARQL** — strukturierte Metadaten:
```sparql
SELECT ?station ?stationLabel ?coord ?operatorLabel ?inception WHERE {
  ?station wdt:P31/wdt:P279* wd:Q55488 ;
           wdt:P17 wd:Q750 ;  # Q750 = Bolivien
           wdt:P625 ?coord .
  OPTIONAL { ?station wdt:P137 ?operator . }
  OPTIONAL { ?station wdt:P1619 ?inception . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,en". }
}
```

**3. OpenRailwayMap API:**
- `api.openrailwaymap.org/api/facility?q=<name>`
- Bei intensiver Nutzung: selbst hosten via osm2pgsql + ORM-API

#### GTFS-Ökosystem

| Quelle | Auth | Python | URL |
|---|---|---|---|
| **Mobility Database** | JWT | `mobility-db-api` | mobilitydatabase.org |
| **Transitland v2** | API-Key | requests | `transit.land/api/v2/rest/` |

```python
# Bolivien-Beispiel: Stops nahe La Paz
GET https://transit.land/api/v2/rest/stops?lat=-16.5&lon=-68.15&radius=5000

# GTFS einlesen
pip install partridge  # Ingestion + busy-week-Filtering
pip install gtfs-kit   # Indikatoren + GeoJSON
```

#### Schienen-Quellen

| Quelle | Wert | Format |
|---|---|---|
| **Wikipedia/Wikidata Metro-Systeme** | Bestes globales Metro-DB | SPARQL |
| **UITP World Metro Figures 2023** | 195 Städte, 626 Linien, 16.400 km | PDF |
| **UIC RAILISA** | Operator-Statistik | Web/CSV (paid für Nicht-Mitglieder) |
| **WB Rail Database** | Country-level km, p-km, t-km | Excel + WB API |
| **Eurostat rail_* Tabellen** | EU-Tiefe | SDMX |

#### Bolivien Schienennetz — Faktenbasis 2026

| Operator | Netz | Länge | Status |
|---|---|---|---|
| **FCA** (Ferroviaria Andina) | Altiplano: La Paz–Oruro–Uyuni–Villazón + Abzweige | ~2.275 km | Aktiv (Expreso del Sur, Wara Wara) |
| **FCO** (Ferroviaria Oriental) | Santa Cruz–Quijarro, Santa Cruz–Yacuíba | ~1.244 km | Aktiv (Sojaverladung, Ferrobus) |
| **Tren Bioceánico** | Geplant Ilo (PE) – Santos (BR), 1.521 km in BO | 3.865 km gesamt | **NUR PROJEKT, keine Bauarbeiten** |
| **Mi Teleférico** | 11 Linien, La Paz/El Alto | ~33 km | Weltgrößte urbane Seilbahn, GTFS verfügbar |

**Wichtig:** FCA und FCO sind physisch NICHT verbunden. Arica–La Paz-Linie seit 2005 außer Betrieb.

#### Routing-APIs

| Tool | Limit | Notiz |
|---|---|---|
| **Navitia.io** | ~30/min free | SNCF/Hove-betrieben |
| **OpenTripPlanner** | self-host | GTFS + OSM PBF reinladen |
| **Transitland Routing** | 1.000/month beta | USA-fokussiert |

### Architecture & urban form

| Quelle | Inhalt | Format |
|---|---|---|
| **GHSL (JRC Copernicus)** | Built-up Surface, 1975–2030, 100m | GeoTIFF, auch GEE |
| **Google Open Buildings** | 1,8 Mrd. Gebäude-Polygone Global South | CC-BY/ODbL |
| **WorldPop** | Bevölkerungsverteilung | GeoTIFF |
| **OSM Overpass** | `building=*`, `historic=*`, `heritage=*` | JSON |

### Public transport – Europe

Die bestehende Drei-Quellen-Strategie (OSM Overpass + Wikidata + OpenRailwayMap) bleibt die globale Basis. Für Europa/Nordamerika gibt es zusätzlich hochwertige nationale/regionale Quellen:

| Kategorie | Quelle | Abdeckung | Format | Lizenz |
|---|---|---|---|---|
| Schienennetz | **NARN — North American Rail Network** (BTS NTAD) | USA/Kanada, Stand 2016 (Update 2026 geplant) | Shapefile/GeoJSON | Public Domain (US) |
| Bahnhofsdaten | **DB StaDa-API** | Deutschland | JSON-API | ODbL (DB OpenData) |
| Echtzeitdaten | **DB SIRI/TRIAS-API** | Deutschland, live | API | ODbL |
| Fahrplan/Netz | **SNCF OpenData / transport.data.gouv.fr** | Frankreich (TER/Intercités/TGV, 151 Tage im Voraus) | GTFS, NeTEx, GTFS-RT/SIRI | ODbL-ähnlich |
| Fahrplan/Netz | **opentransportdata.swiss** | Schweiz, gesamtes ÖV-Netz | GTFS (ZIP) | ODbL |
| Fahrgastzahlen | **UIC Railway Statistics** | Global, Bahn-Betreiber | PDF/Excel | Copyright (UIC), teils Mitgliedschaft nötig |
| Fahrgastzahlen | **Eurostat (ENV-TRANSPORT / rail_\*-Tabellen)** | EU, Personenkilometer nach Schiene | SDMX/CSV | CC-BY (EU) |

Für Bolivien bleibt die im Hauptdokument (Abschnitt 4) bereits erfasste Faktenbasis (FCA/FCO, Mi Teleférico, Tren Bioceánico) die relevante Quelle — die Europa-Spezifika oben sind primär für spätere Ländervergleiche mit europäischen Referenzländern (z.B. Deutschland als zweiter Anker-Country neben Bolivien) interessant.

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **OpenStreetMap Overpass** | Infrastructure, POIs, transit | REST API, overpass-turbo.eu |

## 06 · Environment, Climate & Resources

### Geography, weather, climate, astronomy

| Quelle | Priorität | Python/Format | URL |
|---|---|---|---|
| **GeoNames** | MUSS | `geopy.geocoders.GeoNames` | geonames.org |
| **Natural Earth** | MUSS | `geopandas.read_file()` direkt von S3 | naturalearthdata.com |
| **geoBoundaries** | MUSS | GeoPackage, CC-BY | geoboundaries.org |
| **WB Climate Change Knowledge Portal** | MUSS | REST + AWS S3 `s3://wbg-cckp/` | climateknowledgeportal.worldbank.org |
| **Köppen-Geiger Beck 2023 V3** | MUSS | GeoTIFF | gloh2o.org/koppen |
| **WorldClim 2.1 + CHELSA V2.1** | MUSS | GeoTIFF, R `geodata` | worldclim.org / chelsa-climate.org |
| **NASA Black Marble VNP46** | MUSS | `blackmarblepy` (World Bank DIME) | earthdata.nasa.gov |
| **Falchi Light Pollution Atlas** | MUSS | GeoTIFF, DOI 10.5880/GFZ.1.4.2016.001 | gfz-potsdam.de |
| **ERA5/Copernicus CDS** | MUSS | `cdsapi` Python | cds.climate.copernicus.eu |
| **Meteostat** | nice | `meteostat` Python | meteostat.net |
| **NOAA IBTrACS** | nische | NetCDF | ncei.noaa.gov |

**Bolivien-Hinweis:** Altiplano + Salar de Uyuni = Bortle-Klasse 1–2 (dunkelster Himmel weltweit). Falchi-Werte mit `rasterio` am Koordinatenpunkt extrahieren.

### Disasters & resilience

| Quelle | Auth | Besonderheit |
|---|---|---|
| **EM-DAT** | Free Reg ODER HDX Mirror (ohne Account!) | 27.000+ Events seit 1900 |
| **GDACS** | Keine | Real-time, `gdacs-api` Python |
| **ReliefWeb API** | appname-Reg (seit Nov 2025) | Humanitäre Reports |
| **INFORM Risk Index** | Keine | JRC, 191 Länder jährlich |
| **USGS Earthquake** | Keine | FDSN Standard, `obspy.clients.fdsn` |
| **DesInventar** | Keine | LATAM-fokussiert, subnational, historisch bis 1970er |

**HDX-Tipp:** EM-DAT Country Profiles auf `data.humdata.org/dataset/emdat-country-profiles` ohne EM-DAT-Account!

### Biodiversity, flora, fauna

| Quelle | Stärke | Auth | Python |
|---|---|---|---|
| **IUCN Red List v4** ⚠ | Bedrohungsstatus | Token (v3 EOL!) | `rredlist` R |
| **Catalogue of Life** | 2,1M Species | Keine | `api.checklistbank.org` |
| **eBird** | Vogelbeobachtungen | Free Key | requests |
| **iNaturalist** | Citizen Science | Keine | `pyinaturalist` |
| **CITES Trade Database** | Artenschutz-Handel | Free Token | `rcites` R / `citesdb` |
| **Global Forest Watch** | Tree Cover Loss 30m | API-Key | `data-api.globalforestwatch.org` |
| **MapBiomas Bolivia** | Annual Land Cover BO | Keine | mapbiomas.org/bolivia |
| **Protected Planet WDPA v4** ⚠ | 260k Schutzgebiete | Reg (v3 EOL Mai 2026!) | `pywdpa` |
| **WAHIS (WOAH)** | Tierseuchen | kein REST | Web-CSV-Export |
| **FAOSTAT Livestock** | Viehbestand | SDMX | `faostat` Python |

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **Köppen-Geiger V3** | Climate classification | GeoTIFF, gloh2o.org |
| **Copernicus CDS (ERA5)** | Full reanalysis climate data | API, cds.climate.copernicus.eu |

## 07 · Politics, Governance & Law

### Crime & violence

| Quelle | Auth | Python | Notiz |
|---|---|---|---|
| **World Prison Brief** | Keine | R `prisonbrief` | 226 Länder |

**Numbeo Warnung:** Methodisch ungültig für akademische Nutzung (dokumentierte Manipulation 2017, 2022). Nur als Lebenshaltungskosten-Proxy verwenden, NICHT als Crime/Quality-of-Life-Index.

### Political data

| Quelle | Zeitraum | Indikatoren | Format |
|---|---|---|---|
| **BTI (Bertelsmann)** | 2003+ | 137 Länder | Datenbank |
| **ParlGov** | aktuell | EU/OECD only | SQL |
| **COW Formal Alliances** | 1816–2012 | Allianzen | CSV |

### Politics, elites & history

Already loaded sources on this topic (WID, MARPOR, COLDAT, CCP, Polity5) are listed in `SOURCES_AVAILABLE.md`.

| Quelle | Owner | Inhalt | Zugang | Coverage |
|---|---|---|---|---|
| **WIID (World Income Inequality DB)** | UNU-WIDER | Gini, Dezil-Anteile, P90/P10-Ratio | Excel/Stata | 201 Länder, 26.000+ Datenpunkte |
| **V-Party (V-Dem)** | V-Dem Institute | 3.467 Parteien, 178 Länder; Populismus, Institutionalisierung, Personalisierung | CSV/Stata (DOI 10.23696/vpartydsv2) | 1970–2019 |
| **Clio-Infra** | IISH (van Zanden et al.) | 50+ historische Serien: BIP/Kopf, Reallöhne, Lebenserwartung, Bildung — bis 500 Jahre zurück | XLSX pro Indikator | Global, dünn vor 1850 |
| **LobbyFacts + EU Transparency Register** | EU/Corporate Europe Observatory | Lobbyausgaben, Interessenvertretung auf EU-Ebene | JSON-API + XML/CSV, tägliches Update | EU-fokussiert |
| **Archigos** | Goemans et al. | Regierungschefs/Staatsoberhäupter 1875–2015: Amtsantritt/-ende, Geschlecht, Todesursache | Stata/CSV | 3.000+ Fälle, letzte Version 2015 |
| **Seshat Global History Databank** | Seshat-Projekt | Gesellschaftliche Komplexität, politische/ökonomische Institutionen von der Antike bis heute | CSV (Zenodo, CC BY-NC) | Unregelmäßige Abdeckung, hoher Aufwand |
| **Paths to Power (PtP)** | Harvard Dataverse | Biographien von 44.789 Kabinettsmitgliedern, 141 Länder | CSV (DOI 10.7910/DVN/TP42YG) | 1966–2021 |

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **GTI Global Terrorism Index** | Terrorism impact, 163 countries | IEP Excel |
| **Voter Turnout (IDEA)** | Election participation 1945+ | CSV, idea.int |

## 08 · Culture, Society & Beliefs

### Art, literature, music, rituals, fashion

#### Museum-APIs

| API | Auth | Stärke | URL |
|---|---|---|---|
| **Met Museum** | Keine | 470k Objekte, CC0 | `collectionapi.metmuseum.org/public/collection/v1/` |
| **Rijksmuseum** | Free Key | 700k+ NL-Objekte + SPARQL/Linked-Art | rijksmuseum.nl/api |
| **Smithsonian Open Access** | data.gov Key | 2,8M+ CC0 inkl. Folkways, AWS S3 | `s3://smithsonian-open-access` |
| **V&A** | Keine | 1M+ Records, **stark für Mode/Textil/Schmuck** | api.vam.ac.uk |
| **Cleveland Museum** | Keine | 64k Records, CC0 | openaccess-api.clevelandart.org |
| **Harvard Art Museums** | Free Key (2.500/day) | 224k Records | github.com/harvardartmuseums/api-docs |
| **MoMA GitHub** | Public Git | 140k Werke + Wikidata-IDs | github.com/MuseumofModernArt/collection |

**Lateinamerika-Hinweis:** Keine einheitliche Museum-API existiert. Workaround: Wikidata SPARQL + Europeana + Smithsonian NMAI/NMAfA + Met (prä-kolumbianisch).

#### Literatur

| Quelle | Auth | Notiz |
|---|---|---|
| **Gutendex** | Keine | ~76k Bücher mit `languages=`-Filter |
| **Open Library** | Keine | monatliche Bulk-Dumps |
| **Wikidata SPARQL** | Keine | Autoren by `wdt:P27` (Staatsbürgerschaft) |
| **HathiTrust** | Keine | OAI-PMH-Feed |
| **Index Translationum (UNESCO)** | Keine | 1979–2008 eingefroren |

**Goodreads API ist seit Dez 2020 tot — nicht verwenden.**

#### Musik & Tanz — Der Kern

```python
pip install musicbrainzngs  # Rate-Limit: 1 req/sec mit User-Agent
```

**MusicBrainz PostgreSQL-Dump:** Direkter Import möglich — kein API-Limit, komplettes globales Musik-Backend. Bolivien via Area-Entity mit ISO-Code BO.

| Quelle | Auth | Stärke |
|---|---|---|
| **MusicBrainz** | Keine (Dump) | Country-of-Origin für Artists/Releases |
| **Discogs** | OAuth (Bulk CC0) | Release `country`-Feld zuverlässig |
| **Global Jukebox / Cantometrics** | GitHub CC-BY | 5.776 Songs × 37 stilistische Features |
| **Smithsonian Folkways** | SI Open Access | 100+ Ethnografie-Alben |

**AcousticBrainz seit Feb 2022 abgeschaltet — nur Archiv-Dump.**

#### Rituale & Traditionen: D-PLACE ⭐

**D-PLACE** ist der unbekannteste Goldschatz für quantitative Kulturdaten:
- **GitHub:** `github.com/D-PLACE/dplace-data`, CC-BY 4.0
- **Inhalt:** 1.400+ Gesellschaften × 2.000+ Variablen
- **Datasets:** Ethnographic Atlas, SCCS, Binford, Pulotu (Pazifik-Religion), Cantometrics
- **Variablen:** Heiratsregeln, Residenzmuster, Abstammung, Religionstyp, Subsistenz, politische Komplexität, Körpermodifikation, Musik...

```python
# Nutzung
import pandas as pd
df = pd.read_csv("dplace-data/datasets/EA/data.csv")
# Join über Glottocodes zu Glottolog für Sprachfamilien
# Match via lat/lon zu modernen Ländern
```

**Gotcha:** Beschreibt vorindustrielle Gesellschaften — aggregieren nötig.

#### eHRAF World Cultures (Yale HRAF)

Ergänzt D-PLACE um **qualitative ethnografische Volltexte** statt nur kodierter Variablen:
- **URL:** `ehrafworldcultures.yale.edu` — Web-Export, institutionelle Lizenz nötig
- **Inhalt:** Ethnografische Texte zu ~360 Kulturen, durchsuchbar über den **OCM-Index** (Outline of Cultural Materials)
- **Schlüssel-OCM-Codes:** 545 (Rituals), 788 (Religious Practices), 580 (Marriage), 590 (Familial Relations)
- **Parallel:** `ehrafarchaeology.yale.edu` für archäologische Kulturen
- **Stärke:** Tiefe qualitative Beschreibungen — gut für narrative Synthese-Layer, nicht für KPIs
- **Gotcha:** Lizenzpflichtig (Universitätszugang); kein freier Bulk-Download

#### UNESCO Heritage Stack

| Liste | Inhalte | API |
|---|---|---|
| **Creative Cities Network** | ~350 Städte, 7 Kategorien | Web-Export |

#### Mode & Schmuck — Schwächste Datenlage

Beste Proxies:
- **UN Comtrade** Kapitel 50–63 (Textil) + 71 (Schmuck) als Industrie-Proxy
- **V&A Museum API** für historische Objekte
- **Slow Food Ark of Taste** (scrapen) für traditionelle Produkte

### Values & cultural dimensions

| Quelle | Länder | Zeitraum | Zugang |
|---|---|---|---|
| **GLOBE Project** | 62 | statisch | Buch-Appendix-Transkription |
| **Inglehart-Welzel Cultural Map** | ~90 | WVS-basiert | Aus WVS ableiten |

### Religion

| Quelle | Länder | Auth | URL |
|---|---|---|---|
| **ARDA** | 190+ | Keine | thearda.com |
| **Pew GRI + SHI** | 198 | Free Reg | pewresearch.org/dataset |
| **Religion and State Project (Fox)** | 183 | ARDA | 1990–2014 |
| **Database of Religious History (DRH)** | historisch | Keine | religiondatabase.org |

### Language & linguistics

| Quelle | Umfang | Format | URL |
|---|---|---|---|
| **WALS** | 2.700 Sprachen × 192 Features | CLDF GitHub | wals.info |
| **PHOIBLE** | Phonologische Inventare | CLDF | phoible.org |
| **CLDR (Unicode)** | Locale-Daten | JSON `cldr-json` | cldr.unicode.org |
| **Ethnologue** | 7.000+ Sprachen | paid | — |
| **ELP** | Bedrohte Sprachen | Browse | endangeredlanguages.com |

```python
pip install pyglottolog  # Glottolog Python-Client
```

### Indigenous peoples

| Quelle | Stärke | URL |
|---|---|---|
| **Native Land Digital** | 1.500+ Territorien Americas/AU | `api-docs.native-land.ca` |
| **IWGIA** | 75 Länder-Jahresberichte | iwgia.org |
| **D-PLACE** | Quantitative Kulturvariablen | github.com/D-PLACE |

**Disclaimer Pflicht bei Native Land:** "Nicht legal-bindend, keine offiziellen Grenzen."

### Gender, sexuality, LGBTQ+

| Quelle | Länder | Auth | Besonderheit |
|---|---|---|---|
| **Equaldex** ⭐ | 200+ | Free Key | Bestes LGBTQ-Rights-API, 13–15 Issues, historische Timelines |
| **OECD SIGI 2023** | 179 | Keine SDMX | SDG 5.1.1 Custodian |
| **WB Women, Business & Law** | 190 | WB API | `SG.LAW.INDX`, 1971–2024 |
| **WomanStats Project** | 176 | Free Reg | 350+ Variablen, Quanti+Quali |
| **ILGA World** | 193 | PDF | Annual *Laws on Us* |
| **UCLA Williams Institute GAI** | 174 | Free | 1981–2020 |

### Food & food culture

| Quelle | Inhalt | Format |
|---|---|---|
| **FAO/WHO GIFT** | 188 Surveys, 72 Länder | Web |
| **Open Food Facts** | 4M+ Produkte (bias: FR/DE) | Parquet bulk, 15 req/min |
| **USDA FoodData Central** | Nährstoff-Referenz | Free API-Key |
| **Slow Food Ark of Taste** | 5.000+ Produkte aus 150 Ländern | Scrapen |

### Communication & media

Diese Domain ist im Projekt aktuell am dünnsten (nach v2-Restructure teilweise in Infrastructure/Politics aufgegangen, aber die Medienlandschaft selbst fehlt fast komplett). Folgende Quellen wurden recherchiert, aber noch nicht integriert:

| Quelle | Inhalt | Format/Zugang | Aufwand |
|---|---|---|---|
| **GDELT** | Medienereignisse, Themen, Sentiment, 15-Min-Intervalle | CSV/API, kostenlos, sehr große Datenmenge | Hoch |
| **Reuters Digital News Report** | Vertrauen/Nutzung von Nachrichtenmedien, 40+ Länder | PDF, jährlich | Mittel |
| **ITU DataHub** | ICT-Zugang (Internet, Mobilfunk, Breitband, Cybersecurity) | API/CSV, kostenlos, jährlich | Mittel |
| **Google Trends** (`pytrends`) | Relatives Suchinteresse nach Land/Zeit | inoffizielle Python-Lib, kostenlos | Mittel |
| **RSF Media Ownership Monitor (MOM)** | Medienkonzentration, Eigentümerstrukturen, 30+ Länder | Web/PDF, qualitativ | Hoch (Scraping) |
| **CMPF Media Pluralism Monitor** | EU + Kandidatenländer, Medienpluralismus-Indikatoren | Excel, jährlich | Mittel |
| **CPJ (Committee to Protect Journalists)** | Inhaftierte/getötete/vermisste Journalisten, weltweit | Datenbank, kostenlos | Niedrig |
| **Freedom House — Freedom on the Net** | Internetfreiheit, 72 Länder (89% aller Internetnutzer) | Excel, jährlich | Niedrig |
| **DataReportal** | Digital-/Social-Media-Nutzung pro Land | Web/Reports, kostenlos | Mittel |
| **WAN-IFRA World Press Trends** | Zeitungsauflagen, Reichweite (Survey-basiert, 66 Länder) | Kostenpflichtig für Nicht-Mitglieder | — |
| **StatCounter** | Browser/OS/Plattform-Marktanteile | Free Web-Interface | Niedrig |
| **data.ai / Similarweb Free Tier** | App-/Web-Traffic-Schätzungen | Freemium, seit Sensor-Tower-Übernahme 2024 in Transition — Verfügbarkeit vor Nutzung prüfen | — |
| **Oxford Internet Institute (OxIS)** | Computational-Propaganda-/Desinformationsforschung | PDF-Reports, qualitativ | — |

**Empfehlung für Ersteinstieg:** Reuters DNR + ITU DataHub + Freedom on the Net + CPJ decken die größte Lücke mit vertretbarem Aufwand ab. GDELT und RSF MOM sind mächtig, aber deutlich aufwändiger (Scraping bzw. Rohdatenmenge) — nur bei konkretem Bedarf.

### Social fabric & values

| Quelle | Owner | Inhalt | Zugang | Coverage |
|---|---|---|---|---|
| **ESS (European Social Survey)** | ESS ERIC | Soziales Vertrauen, Normen, Politikbeteiligung, Lebenszufriedenheit | CSV/SPSS, freie Registrierung | Europa, zweijährlich |
| **GESIS Eurobarometer Data Service** | GESIS / EU-Kommission | Meinungsforschung EU seit 1970, u.a. Kultur, Mediennutzung, Religion | SPSS/Stata/SAS + Codebücher, freie Registrierung | EU-Mitglieds-/Kandidatenländer, ~2×/Jahr |
| **ARDA — Association of Religion Data Archives** | Indiana University | 1.400+ Dateien zu Religionszugehörigkeit, -freiheit, Umfragen | SPSS/Stata/CSV pro Datei | 232 Nationen (international) |
| **Pew Global Restrictions on Religion (GRI/SHI)** | Pew Research Center | Staatliche Restriktionen vs. gesellschaftliche Feindseligkeit gegenüber Religion | Excel | 198 Länder |
| **Gallup World Poll** | Gallup | Größte konsistente globale Werte-/Wohlbefinden-Befragung | Kostenpflichtig (Mikrodaten), Headlines teils frei | ~160 Länder |

**Caveat, wichtig für spätere Interpretation:** Regionale Barometer (Latinobarómetro, LAPOP, Eurobarometer, ESS) sind untereinander **nicht direkt vergleichbar** — unterschiedliche Wellen, Fragebögen, Erhebungsjahre. Für Cross-Region-Vergleiche vorsichtig sein.

### Language, identity, sport

| Quelle | Owner | Inhalt | Zugang | Coverage |
|---|---|---|---|---|
| **WALS (World Atlas of Language Structures)** | MPI EVA Leipzig | ~200 strukturelle Sprachmerkmale für ~2.600 Sprachen | CLDF/CSV | Weltweit |
| **TasteAtlas** | TasteAtlas | Nationalgerichte, Esskultur (textuell) | Inoffizielle JSON | Weltweit |
| **Joshua Project** | US-Missionsforschung | 16.405 Volksgruppen, 238 Länder — Bevölkerung, Religion, Sprache, Christen-/Evangelikalen-Anteil | v1/v2-API (Key erforderlich), Excel-Bulk | 238 Länder |
| **FIFA World Rankings** (Community-Archive) | FIFA (Daten), Community (Zugang) | Monatliches Männer-Ranking seit 1992, ~210 Nationalteams | GitHub-Scraper / Kaggle-CSV (kein offizielles FIFA-API) | ~210 Nationalteams |
| **OpenAlex** | OurResearch | Wissenschaftliche Publikationen, Autoren, Institutionen nach Land — Proxy für Forschungsoutput | REST-API, kostenlos | Weltweit |
| **OpenCorporates** | OpenCorporates | Unternehmensregister-Daten, Eigentümerstrukturen | API (Teil kostenpflichtig) | Weltweit, uneinheitliche Tiefe |

**Hinweis zur Datenqualität:** TasteAtlas, Equaldex und Wikidata sind nutzergeneriert — für ein Portfolio-Projekt nutzbar, aber immer als "Crowdsourced" kennzeichnen, nicht als offizielle Statistik.

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **Open Library API** | Books, authors by country | REST JSON, openlibrary.org |
| **Project Gutenberg / Gutendex** | Public-domain literature by topic | REST JSON, gutendex.com |
| **Met Museum Open Access** | Art, jewelry, fashion objects | GitHub CSV + REST, metmuseum.github.io |
| **eHRAF World Cultures** | Ethnographic OCM index, rituals | Web export, Yale (license) |
| **Olympics historical** | Medals 1896–2020 | Kaggle (auth) |

## 09 · History & Collective Memory

### Archives & hard-to-access sources

Diese Quellen sind bewusst nicht in den regulären Rollout eingeplant — hoher Beschaffungsaufwand, aber potenziell einzigartige Tiefe für ein späteres Data-Storytelling-Stück:

| Quelle | Inhalt | Zugangsbeschaffung |
|---|---|---|
| **National Archives / FOIA** | Diplomaten-/Geheimdienstberichte (z.B. CIA Reading Room) | FOIA-Anfrage oder Archivbesuch |
| **Chronicling America (Library of Congress)** | Historische US-Zeitungen, OCR-Volltext, 1789–1963 | Öffentliche API / Bulk-Download, kostenlos |
| **ProQuest Historical Newspapers** | Weltweite historische Zeitungsarchive, 19./20. Jh. | Uni-Bibliothek/Fachdatenbank-Abo |
| **Global Terrorism Database (GTD)** | Terrorismusereignisse weltweit, 1970–2019 | Download via ICPSR/UMD, kostenlos |
| **Medieninstitute (Edelman, Reuters Institute)** | Langfristige Vertrauens-/Meinungsforschungs-Barometer über das Web hinaus | Direkter Kontakt / Forschungskooperation |

**Realistische Einschätzung:** Diese Kategorie lohnt sich nur, wenn ein konkretes Story-Stück (z.B. für die geplante Bolivien-Publikation im August) einen archivarischen Beleg braucht — nicht für die reguläre Indikator-Pipeline.

## Regional: Latin America & Bolivia

### Regionale Aggregatoren (MUSS)

| Quelle | Indikatoren | Auth | URL |
|---|---|---|---|
| **CEPALSTAT (UN ECLAC)** | 1.000+, 33 LAC-Länder | Keine | `api-cepalstat.cepal.org/cepalstat/api/v1/` |
| **IDB N4D** | 2.000+, alle LAC | Keine | `api-data.iadb.org/datasitedata` |
| **SEDLAC (CEDLAS + WB)** | Haushalts-Surveys | Keine | cedlas.econo.unlp.edu.ar |
| **LAPOP AmericasBarometer** | 34 Länder, 2004–2023 | Click-Lizenz | vanderbilt.edu/lapop |
| **Latinobarómetro** | 18 Länder, 1995+ | Free nach 1 Jahr | latinobarometro.org |

### Nationale APIs — Tier-Liste

**S-Tier (Production-Grade):**
```python
# Argentinien
GET https://apis.datos.gob.ar/series/api/series/?ids={ID}

# Brasilien IBGE
pip install sidrapy  # SIDRA API
pip install ipeadatapy  # IPEA OData v4
GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/dados?formato=json
```

**A-Tier:**
```python
# Mexico
pip install INEGIpy  # INEGI Indikatoren + DENUE
pip install BANXICOpy  # Banco de México

# Chile
pip install bcch-sdk  # Banco Central Chile

# Kolumbien/Peru: Socrata SODA + CKAN
```

### Bolivien-Spezifisch

| Quelle | Zugang | Inhalt |
|---|---|---|
| **INE Bolivia + ANDA** | REDATAM/CSV-Bulk | Census 2024 (413 MB CSV) |
| **datos.gob.bo** (AGETIC) | CKAN `/api/3/action/` | Dünn bestückt |
| **SENAMHI Bolivia** | Nur PDF/Excel | Wetterdaten |
| **UNODC Coca Monitoring** | PDF Fact Sheets | **Methodenbruch 2024**: +51% Monitoring-Fläche |
| **Mi Teleférico GTFS** | Mobility Database | 11 Linien, ~33 km, weltgrößtes urbanes Seilbahnnetz |

**Warnung:** GeoBolivia wurde 2024–25 ohne Vorwarnung geschlossen.

**Administrative Einheiten Bolivien:**
- Standard: Departamento → Provincia → Municipio
- Einzigartig: **TIOC** (Territorio Indígena Originario Campesino) — unbedingt ins Schema aufnehmen

### City-Daten LATAM

| Stadt | Portal | API-Typ |
|---|---|---|
| **Buenos Aires** | data.buenosaires.gob.ar | CKAN + Transit/Bici APIs |
| **CDMX** | datos.cdmx.gob.mx | `APIdatosCDMX` Python |
| **São Paulo** | dados.prefeitura.sp.gov.br | CKAN |
| **Bogotá** | datosabiertos.bogota.gov.co | Socrata |

### Spezialisierte LATAM-Quellen

| Thema | Quelle |
|---|---|
| Indigene Sprachen | AILLA (Austin), Glottolog, ELP |
| Amazon/Land | **RAISG** (9 Länder Shapefiles), **MapBiomas Bolivia** |
| Migration | IOM DTM API, R4V (Venezuela) |
| Homizid LATAM | **Igarapé Homicide Monitor** (city-level) |
| Drogen/Coca | UNODC Crop Monitoring Bolivia |
| Gewalt | CEPAL Femizid-Observatorium, IPEA Atlas da Violência (BR) |

### Prioritised in the roadmap (June 2026)

| Source | Content / rationale | Access |
|---|---|---|
| **AmericasBarometer (LAPOP)** | 34 countries, 2004–2023 | Click-license, vanderbilt.edu/lapop |

### Additions from the roadmap (June 2026)

| Source | Coverage | Access |
|--------|----------|--------|
| **IDB Numbers for Development** | 2.000+ indicators, all LAC | api-data.iadb.org |
| **RAISG / MapBiomas Bolivia** | Amazon territories, land use | Shapefiles |

Note: GeoBolivia was shut down in 2024/25 without warning. Model TIOC (Territorio Indígena Originario Campesino) in any subnational schema.

## Cross-cutting: aggregators, portals, API notes

### Meta-aggregators

Diese drei decken ~70% aller Standard-Indikatoren ab:

| Aggregator | Python | Stärke |
|---|---|---|
| **DBnomics** | `pip install dbnomics` | ~80 Provider, SDMX-normalisiert, ~1 Mrd. Zeitreihen |
| **DataCommons (Google)** | `pip install datacommons-client` | WB/UN/OECD/WHO in einem Knowledge Graph |
| **HDX** | `pip install hdx-python-api` | Humanitäre + Länderdaten, CKAN-API |

### Hidden gems

Quellen die 99% der Data Analysts nie finden:

1. **D-PLACE** — 2.000+ ethnografische Variablen × 1.400 Gesellschaften, CC-BY auf GitHub
2. **MusicBrainz PostgreSQL-Dumps** — komplettes globales Musik-Backend, direkt importierbar
3. **DataCommons V2** — Googles bestes Geheimnis, MCP-Server verfügbar
4. **HDX HAPI** — neue Generation humanitärer Daten, standardisierte Indikatoren

### API changes

| Quelle | Deadline | Aktion |
|---|---|---|
| **WDPA v3** | Mai 2026 | v4-Migration, neues Token |
| **IUCN v3** | EOL März 2025 | v4-Token beantragen |
| **ReliefWeb** | Nov 2025 | appname-Registrierung |
| **Europeana** | Mai 2025 | API-Key-pflichtig |

### UN family

| Quelle | Auth | Python | URL |
|---|---|---|---|
| **WHO GHED** | Keine | Excel-Bulk | apps.who.int/nha/database |
| **UN SDG API** | Keine | requests | `unstats.un.org/sdgapi/` |
| **UNESCO UIS** | Reg | BDDS Bulk / `uisapi` R | uis.unesco.org/bdds |

### Discovery & meta portals

#### Wichtige Meta-Aggregatoren

| Tool | URL | Stärke |
|---|---|---|
| **DataCommons** | datacommons.org | Google Knowledge Graph |
| **Gapminder** | gapminder.org | `open-numbers/ddf--gapminder` GitHub |
| **Wikidata** | wikidata.org/sparql | Universal-Joker |
| **SDMX Global Registry** | registry.sdmx.org | Zentrale DSDs |

#### Discovery-Tools

- `re3data.org` — ~3.000 Research-Data-Repositories
- `dateno.io/registry` — nationale CKAN-Portale
- `github.com/awesomedata/awesome-public-datasets`
- `public-apis/public-apis` auf GitHub
- `dataportals.org` — ~100 LAC-Portale gelistet

#### Code-Mapping Utilities

```python
pip install hdx-python-country  # ISO3/M49/WB-Code-Mapping — UNVERZICHTBAR
pip install pycountry            # Alternative
```

**Das einzige wichtigste praktische Problem:** Country-Code-Harmonisierung (M49/ISO3/WB-Code) — immer `hdx-python-country` als zentralen Helper nutzen.

### Blocked

| Source | Problem | Workaround |
|---|---|---|
| **COW Intrastate v5.1** | ZIP is HTML redirect | Manual download |
| **IMF DOTS** | 403 API protection | No workaround found |
| **Box Office data** | No free country-level bulk | Deferred |

## Appendix

### Python packages

```bash
# Tier 1 — sofort installieren
pip install wbgapi dbnomics hdx-python-api datacommons-client
pip install hdx-python-country pycountry  # Code-Mapping

# Geo & Klima
pip install geopandas openmeteo-requests cdsapi meteostat
pip install rasterio blackmarblepy  # Raster-Verarbeitung

# SDMX
pip install sdmx1 eurostat

# Transport
pip install partridge gtfs-kit mobility-db-api

# Spezialquellen
pip install pygbif musicbrainzngs pyinaturalist
pip install faostat ipeadatapy INEGIpy sidrapy

# Utilities
pip install pyreadstat pdfplumber  # SPSS-Daten + PDF-Extraktion
```

*Dieses Dokument ist eine lebende Referenz. Regelmäßig aktualisieren wenn neue Quellen integriert werden.*

## Provenance and rules

- Built on 2026-11-10 from `docs/SOURCES_ENCYCLOPEDIA.md` (as of 2026-06-03) and the phase 4, Latin America and blocked sections of `docs/SOURCES_ROADMAP.md`. Both files are replaced; earlier versions are in the Git history.
- **Removed:** entries for sources that are already loaded (see `SOURCES_AVAILABLE.md`), duplicates within the old file, and the outdated six-month rollout plan from June.
- Access, licence and deadline details come from research in May/June 2026 and **must be re-checked before loading**.
- Source-scout agent (#25): reads this file as its input, writes proposals to its run folder; Julian decides, then the row moves to `SOURCES_AVAILABLE.md`.
- Check: `python3 scripts/check_sources.py`.
