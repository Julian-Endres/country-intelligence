# Country Intelligence Layer — Datenquellen-Enzyklopädie

> Lebende Referenz für alle verfügbaren Datenquellen weltweit.
> Nicht als To-Do-Liste, sondern als Nachschlagewerk.
> Was bereits integriert ist, steht in `SOURCES_ROADMAP.md` (aktuell 50 Quellen, ~9M Datenpunkte).
> Letzte Aktualisierung: 2026-06-03

---

## Schnellübersicht: Die wichtigsten Erkenntnisse

### Drei Tier-1 Meta-Aggregatoren
Diese drei decken ~70% aller Standard-Indikatoren ab:

| Aggregator | Python | Stärke |
|---|---|---|
| **DBnomics** | `pip install dbnomics` | ~80 Provider, SDMX-normalisiert, ~1 Mrd. Zeitreihen |
| **DataCommons (Google)** | `pip install datacommons-client` | WB/UN/OECD/WHO in einem Knowledge Graph |
| **HDX** | `pip install hdx-python-api` | Humanitäre + Länderdaten, CKAN-API |

### Die vier unbekannten Schätze
Quellen die 99% der Data Analysts nie finden:

1. **D-PLACE** — 2.000+ ethnografische Variablen × 1.400 Gesellschaften, CC-BY auf GitHub
2. **MusicBrainz PostgreSQL-Dumps** — komplettes globales Musik-Backend, direkt importierbar
3. **DataCommons V2** — Googles bestes Geheimnis, MCP-Server verfügbar
4. **HDX HAPI** — neue Generation humanitärer Daten, standardisierte Indikatoren

### Wichtige API-Migrations-Deadlines
| Quelle | Deadline | Aktion |
|---|---|---|
| **WDPA v3** | Mai 2026 | v4-Migration, neues Token |
| **IUCN v3** | EOL März 2025 | v4-Token beantragen |
| **ACLED OAuth** | Sept 2025 abgelaufen | neues Auth-System |
| **WHO GHO OData** | Ende 2025 | Schema-Migration prüfen |
| **UCDP** | Feb 2026 | Token-Auth nötig |
| **ReliefWeb** | Nov 2025 | appname-Registrierung |
| **Europeana** | Mai 2025 | API-Key-pflichtig |

---

## 1. Geografie, Wetter, Klima, Astronomie

| Quelle | Priorität | Python/Format | URL |
|---|---|---|---|
| **GeoNames** | MUSS | `geopy.geocoders.GeoNames` | geonames.org |
| **Natural Earth** | MUSS | `geopandas.read_file()` direkt von S3 | naturalearthdata.com |
| **geoBoundaries** | MUSS | GeoPackage, CC-BY | geoboundaries.org |
| **Open-Meteo** | MUSS | `openmeteo-requests`, ERA5 zurück bis 1940 | open-meteo.com |
| **WB Climate Change Knowledge Portal** | MUSS | REST + AWS S3 `s3://wbg-cckp/` | climateknowledgeportal.worldbank.org |
| **Köppen-Geiger Beck 2023 V3** | MUSS | GeoTIFF | gloh2o.org/koppen |
| **WorldClim 2.1 + CHELSA V2.1** | MUSS | GeoTIFF, R `geodata` | worldclim.org / chelsa-climate.org |
| **NASA Black Marble VNP46** | MUSS | `blackmarblepy` (World Bank DIME) | earthdata.nasa.gov |
| **Falchi Light Pollution Atlas** | MUSS | GeoTIFF, DOI 10.5880/GFZ.1.4.2016.001 | gfz-potsdam.de |
| **ERA5/Copernicus CDS** | MUSS | `cdsapi` Python | cds.climate.copernicus.eu |
| **Meteostat** | nice | `meteostat` Python | meteostat.net |
| **NOAA IBTrACS** | nische | NetCDF | ncei.noaa.gov |

**Bolivien-Hinweis:** Altiplano + Salar de Uyuni = Bortle-Klasse 1–2 (dunkelster Himmel weltweit). Falchi-Werte mit `rasterio` am Koordinatenpunkt extrahieren.

---

## 2. Globale Makro-Statistik

### World Bank Ökosystem
```python
pip install wbgapi  # Die unverzichtbare Bibliothek
```

Wichtige Sub-Datenbanken (alle via wbgapi abrufbar):

| ID | Name | Inhalt |
|---|---|---|
| 2 | WDI | World Development Indicators (Standard) |
| 3 | WGI | Worldwide Governance Indicators, 1996+ |
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

### UN-Familie

| Quelle | Auth | Python | URL |
|---|---|---|---|
| **WHO GHO OData** | Keine | requests direkt | `ghoapi.azureedge.net/api/` |
| **WHO GHED** | Keine | Excel-Bulk | apps.who.int/nha/database |
| **UNHCR Refugee Statistics** | Keine | `refugees` R-Paket | `api.unhcr.org/population/v1/` |
| **UN SDG API** | Keine | requests | `unstats.un.org/sdgapi/` |
| **UNESCO UIS** | Reg | BDDS Bulk / `uisapi` R | uis.unesco.org/bdds |
| **UNDP HDR** | Keine | CSV-Bulk | hdr.undp.org/data-center |

**WHO GHO Warnung:** Ende 2025 API-Schema-Migration → Migration einplanen.

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

### Spezialisierte Wirtschaftsquellen

| Quelle | Zeitraum | Format |
|---|---|---|
| **Penn World Table 11.0** | 1950–2023, 185 Länder | Stata/CSV, R `pwt10` |
| **Maddison Project 2023** | Jahr 1–2022, 169 Länder | Excel/Stata |
| **WID.world** (World Inequality) | 1980+ | R `wid` / `widr` |
| **Atlas of Economic Complexity** | aktuell | Bulk-CSV (Harvard) |
| **UN Comtrade Plus** | 1962+ | API 500 calls/day free, `comtradeapicall` |

**OEC Warnung:** Free API seit 2021 abgeschafft.

---

## 3. Lateinamerika & Bolivien

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

---

## 4. Öffentlicher Verkehr & Schiene 🚂

### Die optimale Drei-Quellen-Strategie

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

### GTFS-Ökosystem

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

### Schienen-Quellen

| Quelle | Wert | Format |
|---|---|---|
| **Wikipedia/Wikidata Metro-Systeme** | Bestes globales Metro-DB | SPARQL |
| **UITP World Metro Figures 2023** | 195 Städte, 626 Linien, 16.400 km | PDF |
| **UIC RAILISA** | Operator-Statistik | Web/CSV (paid für Nicht-Mitglieder) |
| **WB Rail Database** | Country-level km, p-km, t-km | Excel + WB API |
| **Eurostat rail_* Tabellen** | EU-Tiefe | SDMX |

### Bolivien Schienennetz — Faktenbasis 2026

| Operator | Netz | Länge | Status |
|---|---|---|---|
| **FCA** (Ferroviaria Andina) | Altiplano: La Paz–Oruro–Uyuni–Villazón + Abzweige | ~2.275 km | Aktiv (Expreso del Sur, Wara Wara) |
| **FCO** (Ferroviaria Oriental) | Santa Cruz–Quijarro, Santa Cruz–Yacuíba | ~1.244 km | Aktiv (Sojaverladung, Ferrobus) |
| **Tren Bioceánico** | Geplant Ilo (PE) – Santos (BR), 1.521 km in BO | 3.865 km gesamt | **NUR PROJEKT, keine Bauarbeiten** |
| **Mi Teleférico** | 11 Linien, La Paz/El Alto | ~33 km | Weltgrößte urbane Seilbahn, GTFS verfügbar |

**Wichtig:** FCA und FCO sind physisch NICHT verbunden. Arica–La Paz-Linie seit 2005 außer Betrieb.

### Routing-APIs

| Tool | Limit | Notiz |
|---|---|---|
| **Navitia.io** | ~30/min free | SNCF/Hove-betrieben |
| **OpenTripPlanner** | self-host | GTFS + OSM PBF reinladen |
| **Transitland Routing** | 1.000/month beta | USA-fokussiert |

---

## 5. Kunst, Literatur, Musik, Tanz, Rituale, Mode, Schmuck

### Museum-APIs

| API | Auth | Stärke | URL |
|---|---|---|---|
| **Met Museum** | Keine | 470k Objekte, CC0 | `collectionapi.metmuseum.org/public/collection/v1/` |
| **Rijksmuseum** | Free Key | 700k+ NL-Objekte + SPARQL/Linked-Art | rijksmuseum.nl/api |
| **Smithsonian Open Access** | data.gov Key | 2,8M+ CC0 inkl. Folkways, AWS S3 | `s3://smithsonian-open-access` |
| **V&A** | Keine | 1M+ Records, **stark für Mode/Textil/Schmuck** | api.vam.ac.uk |
| **Cleveland Museum** | Keine | 64k Records, CC0 | openaccess-api.clevelandart.org |
| **Harvard Art Museums** | Free Key (2.500/day) | 224k Records | github.com/harvardartmuseums/api-docs |
| **Europeana** | Free Key | **50M+ Items aus 3.500 Institutionen** | pro.europeana.eu/page/apis |
| **MoMA GitHub** | Public Git | 140k Werke + Wikidata-IDs | github.com/MuseumofModernArt/collection |

**Lateinamerika-Hinweis:** Keine einheitliche Museum-API existiert. Workaround: Wikidata SPARQL + Europeana + Smithsonian NMAI/NMAfA + Met (prä-kolumbianisch).

### Literatur

| Quelle | Auth | Notiz |
|---|---|---|
| **Gutendex** | Keine | ~76k Bücher mit `languages=`-Filter |
| **Open Library** | Keine | monatliche Bulk-Dumps |
| **Nobel Prize API** | Keine | `api.nobelprize.org/2.1/` |
| **Wikidata SPARQL** | Keine | Autoren by `wdt:P27` (Staatsbürgerschaft) |
| **HathiTrust** | Keine | OAI-PMH-Feed |
| **Index Translationum (UNESCO)** | Keine | 1979–2008 eingefroren |

**Goodreads API ist seit Dez 2020 tot — nicht verwenden.**

### Musik & Tanz — Der Kern

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

### Rituale & Traditionen: D-PLACE ⭐

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

### eHRAF World Cultures (Yale HRAF)

Ergänzt D-PLACE um **qualitative ethnografische Volltexte** statt nur kodierter Variablen:
- **URL:** `ehrafworldcultures.yale.edu` — Web-Export, institutionelle Lizenz nötig
- **Inhalt:** Ethnografische Texte zu ~360 Kulturen, durchsuchbar über den **OCM-Index** (Outline of Cultural Materials)
- **Schlüssel-OCM-Codes:** 545 (Rituals), 788 (Religious Practices), 580 (Marriage), 590 (Familial Relations)
- **Parallel:** `ehrafarchaeology.yale.edu` für archäologische Kulturen
- **Stärke:** Tiefe qualitative Beschreibungen — gut für narrative Synthese-Layer, nicht für KPIs
- **Gotcha:** Lizenzpflichtig (Universitätszugang); kein freier Bulk-Download

### UNESCO Heritage Stack

| Liste | Inhalte | API |
|---|---|---|
| **World Heritage List** | 1.248 Properties (2025) | `data.unesco.org/explore/dataset/whc001/` |
| **Intangible Cultural Heritage** | 680+ Practices, 140 Länder | `data.unesco.org/explore/dataset/ich001/` |
| **Creative Cities Network** | ~350 Städte, 7 Kategorien | Web-Export |

### Mode & Schmuck — Schwächste Datenlage

Beste Proxies:
- **UN Comtrade** Kapitel 50–63 (Textil) + 71 (Schmuck) als Industrie-Proxy
- **V&A Museum API** für historische Objekte
- **Slow Food Ark of Taste** (scrapen) für traditionelle Produkte

---

## 6. Werte, Kultur-Dimensionen, Religion, Sprache, Indigene Völker

### Werte & Kulturdimensionen

| Quelle | Länder | Zeitraum | Zugang |
|---|---|---|---|
| **Hofstede 6D** | 76 | statisch | **Komplett offen**: `geerthofstede.com/research-and-vsm/dimension-data-matrix/` — kein Scraping nötig! |
| **World Values Survey Wave 7** | 64 | 2017–2022 | Free Reg, CSV/SPSS (`pyreadstat`) |
| **V-Dem v16** | 202 | 1789–2024 | R `vdemdata::vdem()` / CSV |
| **GLOBE Project** | 62 | statisch | Buch-Appendix-Transkription |
| **Inglehart-Welzel Cultural Map** | ~90 | WVS-basiert | Aus WVS ableiten |
| **Edelman Trust Barometer** | 28 | 2001+ | PDF (pdfplumber extrahieren) |

### Religion

| Quelle | Länder | Auth | URL |
|---|---|---|---|
| **ARDA** | 190+ | Keine | thearda.com |
| **Pew GRI + SHI** | 198 | Free Reg | pewresearch.org/dataset |
| **Pew Global Religious Landscape 2020** | 198 | Keine | Excel |
| **Religion and State Project (Fox)** | 183 | ARDA | 1990–2014 |
| **Database of Religious History (DRH)** | historisch | Keine | religiondatabase.org |

### Sprache & Linguistik

| Quelle | Umfang | Format | URL |
|---|---|---|---|
| **Glottolog v5.3** | 25.000+ Languoids | API + CLDF | glottolog.org |
| **WALS** | 2.700 Sprachen × 192 Features | CLDF GitHub | wals.info |
| **PHOIBLE** | Phonologische Inventare | CLDF | phoible.org |
| **CLDR (Unicode)** | Locale-Daten | JSON `cldr-json` | cldr.unicode.org |
| **Ethnologue** | 7.000+ Sprachen | paid | — |
| **ELP** | Bedrohte Sprachen | Browse | endangeredlanguages.com |

```python
pip install pyglottolog  # Glottolog Python-Client
```

### Indigene Völker

| Quelle | Stärke | URL |
|---|---|---|
| **Native Land Digital** | 1.500+ Territorien Americas/AU | `api-docs.native-land.ca` |
| **IWGIA** | 75 Länder-Jahresberichte | iwgia.org |
| **D-PLACE** | Quantitative Kulturvariablen | github.com/D-PLACE |
| **RAISG** | Amazon-Territorien 9 Länder | raisg.org |

**Disclaimer Pflicht bei Native Land:** "Nicht legal-bindend, keine offiziellen Grenzen."

### Familie & Beziehungen

| Quelle | Auth | URL |
|---|---|---|
| **OECD Family Database** | Keine SDMX | oecd.org/en/data/datasets/oecd-family-database |
| **Generations and Gender Survey (GGS-II)** | Free Reg | ggp-i.org |
| **DHS STATcompiler** | Keine | `api.dhsprogram.com` |

### Gender, Sexualität, LGBTQ+

| Quelle | Länder | Auth | Besonderheit |
|---|---|---|---|
| **Equaldex** ⭐ | 200+ | Free Key | Bestes LGBTQ-Rights-API, 13–15 Issues, historische Timelines |
| **OECD SIGI 2023** | 179 | Keine SDMX | SDG 5.1.1 Custodian |
| **WB Women, Business & Law** | 190 | WB API | `SG.LAW.INDX`, 1971–2024 |
| **WomanStats Project** | 176 | Free Reg | 350+ Variablen, Quanti+Quali |
| **ILGA World** | 193 | PDF | Annual *Laws on Us* |
| **UCLA Williams Institute GAI** | 174 | Free | 1981–2020 |

### Migration & Diaspora

| Quelle | Auth | URL |
|---|---|---|
| **UN DESA International Migrant Stock 2024** | Keine | Excel-Bulk |
| **KNOMAD Bilateral Remittances** | Keine | WB-gehostet (KNOMAD 2024 stillgelegt) |
| **UNHCR Refugee Statistics API** | Keine | `api.unhcr.org/population/v1/` |
| **IOM DTM API** | Keine | `dtmapi.iom.int/api/` |

---

## 7. Gesundheit, Drogen, Hygiene, Crime, Trauma, Desaster

### Gesundheit (MUSS)

| Quelle | Indikatoren | Auth | Notiz |
|---|---|---|---|
| **WHO GHO OData** | ~2.300 | Keine | `ghoapi.azureedge.net/api/` — Schema-Migration 2025! |
| **WHO GISAH** | Alkohol ~200 | Keine | In GHO enthalten |
| **IHME GBD Results** | 204 Länder | Free Reg | **Kein API**, nur CSV-Download |
| **DHS STATcompiler** | 90+ LMIC | Keine | `api.dhsprogram.com` |
| **UNAIDS AIDSinfo** | 170 Länder | Keine | Excel-Bulk |
| **JMP WASH** | 200+ Länder | Keine | washdata.org |

### Drogen & Sucht

| Quelle | Inhalt | Format |
|---|---|---|
| **UNODC dataUNODC** | Beschlagnahmungen, Prävalenz, Homizide | CSV-Bulk |
| **UNODC Coca Bolivia** | Jährliche Monitoring-Reports | PDF/Excel |
| **WHO GISAH** | Alkohol-Konsum, Policies | GHO OData |
| **EUDA** (EU) | EU+NO+TR; Wastewater, Drug Checking | datacatalogue |

**UNODC Bolivia 2024 Warnung:** Methodenbruch → +51% Monitoring-Fläche → Zeitreihe 2023→2024 nicht direkt vergleichbar.

### Crime & Violence

| Quelle | Auth | Python | Notiz |
|---|---|---|---|
| **UNODC CTS** | Keine | CSV-Bulk | Homizide, Gefangene |
| **World Prison Brief** | Keine | R `prisonbrief` | 226 Länder |
| **GI-TOC Global Crime Index** | Keine | CSV | 193 Länder, 2021/2023/2025 |
| **Igarapé Homicide Monitor** | Keine | Web | city-Ebene LATAM |
| **UCDP** | Token (seit Feb 2026) | `ucdp` R / API | 1946/1989–2024 |
| **ACLED** | OAuth (neu) | `acledR` | Bolivien seit 2018 |

**Numbeo Warnung:** Methodisch ungültig für akademische Nutzung (dokumentierte Manipulation 2017, 2022). Nur als Lebenshaltungskosten-Proxy verwenden, NICHT als Crime/Quality-of-Life-Index.

### Trauma & Mental Health

| Quelle | Inhalt | Zugang |
|---|---|---|
| **IHME GBD** | PTSD, Depression, Suizid, 204 Länder | Free Reg, CSV |
| **WHO Mental Health Atlas** | System-Level, alle 3 Jahre | PDF |
| **UCDP GED** | Konflikt-Events georeferenziert | Token-Auth |
| **Truth Commissions DB** | ~50 Kommissionen | USIP/ICTJ Web |

**Proxy für nationalen Trauma-Index:** IHME GBD PTSD-Prävalenz + UCDP Battle-Deaths/Capita + EM-DAT Total Affected + Truth-Commission-Existenz (Binär).

### Desaster & Resilienz

| Quelle | Auth | Besonderheit |
|---|---|---|
| **EM-DAT** | Free Reg ODER HDX Mirror (ohne Account!) | 27.000+ Events seit 1900 |
| **GDACS** | Keine | Real-time, `gdacs-api` Python |
| **ReliefWeb API** | appname-Reg (seit Nov 2025) | Humanitäre Reports |
| **INFORM Risk Index** | Keine | JRC, 191 Länder jährlich |
| **ND-GAIN Country Index** | Keine | 192 Länder, 1995–2023, CC-BY |
| **USGS Earthquake** | Keine | FDSN Standard, `obspy.clients.fdsn` |
| **DesInventar** | Keine | LATAM-fokussiert, subnational, historisch bis 1970er |

**HDX-Tipp:** EM-DAT Country Profiles auf `data.humdata.org/dataset/emdat-country-profiles` ohne EM-DAT-Account!

---

## 8. Biodiversität, Flora, Fauna, Tiere

| Quelle | Stärke | Auth | Python |
|---|---|---|---|
| **GBIF** | 2,5 Mrd. Occurrence-Records | Keine | `pygbif` |
| **IUCN Red List v4** ⚠ | Bedrohungsstatus | Token (v3 EOL!) | `rredlist` R |
| **Catalogue of Life** | 2,1M Species | Keine | `api.checklistbank.org` |
| **eBird** | Vogelbeobachtungen | Free Key | requests |
| **iNaturalist** | Citizen Science | Keine | `pyinaturalist` |
| **CITES Trade Database** | Artenschutz-Handel | Free Token | `rcites` R / `citesdb` |
| **Global Forest Watch** | Tree Cover Loss 30m | API-Key | `data-api.globalforestwatch.org` |
| **MapBiomas Bolivia** | Annual Land Cover BO | Keine | mapbiomas.org/bolivia |
| **Protected Planet WDPA v4** ⚠ | 260k Schutzgebiete | Reg (v3 EOL Mai 2026!) | `pywdpa` |
| **WAHIS (WOAH)** | Tierseuchen | kein REST | Web-CSV-Export |
| **eBird** | Vogelbeob. weltweit | Free Key | requests |
| **FAOSTAT Livestock** | Viehbestand | SDMX | `faostat` Python |

---

## 9. Essen, Tourismus, Architektur & Urban

### Essen / Cuisine

| Quelle | Inhalt | Format |
|---|---|---|
| **FAOSTAT Food Balance Sheets** | Kalorische Versorgung, 1961+ | `faostat` Python |
| **FAO/WHO GIFT** | 188 Surveys, 72 Länder | Web |
| **Open Food Facts** | 4M+ Produkte (bias: FR/DE) | Parquet bulk, 15 req/min |
| **USDA FoodData Central** | Nährstoff-Referenz | Free API-Key |
| **UNESCO ICH** | Traditionelle Küchen (Washoku, Mediterran...) | REST API |
| **Slow Food Ark of Taste** | 5.000+ Produkte aus 150 Ländern | Scrapen |

### Tourismus

| Quelle | Auth | Notiz |
|---|---|---|
| **UNWTO Tourism Database** | paid (Vollzugriff) | Free Dashboard für Schlüsselindikatoren |
| **WB WDI** `ST.INT.ARVL` | Keine | Ankünfte, free |
| **UNESCO World Heritage** | Keine | 1.248 Properties, Koordinaten |
| **GeoNames** | Username | POIs nach feature_code |

### Architektur & Stadtform

| Quelle | Inhalt | Format |
|---|---|---|
| **GHSL (JRC Copernicus)** | Built-up Surface, 1975–2030, 100m | GeoTIFF, auch GEE |
| **Google Open Buildings** | 1,8 Mrd. Gebäude-Polygone Global South | CC-BY/ODbL |
| **WorldPop** | Bevölkerungsverteilung | GeoTIFF |
| **OSM Overpass** | `building=*`, `historic=*`, `heritage=*` | JSON |

---

## 10. Politische Daten

| Quelle | Zeitraum | Indikatoren | Format |
|---|---|---|---|
| **V-Dem v16** | 1789–2024 | 531 + 251 Indizes | R `vdemdata` / CSV |
| **Freedom House FIW** | 1972+ | PR + CL | Excel |
| **BTI (Bertelsmann)** | 2003+ | 137 Länder | Datenbank |
| **WGI (World Bank)** | 1996+ | 6 Governance | WB API Source 3 |
| **CPI (Transparency Int.)** | 1995+ | 180 Länder | Excel |
| **Polity5** | 1800–2018 | ersetzt durch V-Dem | — |
| **ParlGov** | aktuell | EU/OECD only | SQL |
| **ACLED** | 1997+ | Konfliktereignisse | OAuth-API |
| **UCDP** | 1946+ | State-based Conflict | Token-API |
| **COW Formal Alliances** | 1816–2012 | Allianzen | CSV |

---

## 11. Discovery & Meta-Portale

### Wichtige Meta-Aggregatoren

| Tool | URL | Stärke |
|---|---|---|
| **DBnomics** | db.nomics.world | ~80 Provider, SDMX-normalisiert |
| **DataCommons** | datacommons.org | Google Knowledge Graph |
| **HDX** | data.humdata.org | Humanitäre Daten |
| **OWID** | ourworldindata.org | Kuratiert, `owid-catalog` Python |
| **Gapminder** | gapminder.org | `open-numbers/ddf--gapminder` GitHub |
| **Wikidata** | wikidata.org/sparql | Universal-Joker |
| **SDMX Global Registry** | registry.sdmx.org | Zentrale DSDs |

### Discovery-Tools

- `re3data.org` — ~3.000 Research-Data-Repositories
- `dateno.io/registry` — nationale CKAN-Portale
- `github.com/awesomedata/awesome-public-datasets`
- `public-apis/public-apis` auf GitHub
- `dataportals.org` — ~100 LAC-Portale gelistet

### Code-Mapping Utilities

```python
pip install hdx-python-country  # ISO3/M49/WB-Code-Mapping — UNVERZICHTBAR
pip install pycountry            # Alternative
```

**Das einzige wichtigste praktische Problem:** Country-Code-Harmonisierung (M49/ISO3/WB-Code) — immer `hdx-python-country` als zentralen Helper nutzen.

---

## 12. Empfohlener 6-Monats-Rollout

### Phase 1 — Fundament (Wochen 1–4)
DBnomics + DataCommons + HDX + wbgapi → ~70% Standard-Indikatoren.
Country-Code-Harmonisierung mit `hdx-python-country`.

### Phase 2 — Tiefe & LATAM (Wochen 5–10)
sdmx1 für OECD/IMF/Eurostat/BIS.
CEPALSTAT + IDB N4D + INE Bolivia Census 2024 + Argentina Series API + IBGE SIDRA.
UNHCR + IOM DTM. UNODC Coca Bolivia.

### Phase 3 — ÖPNV-Schwerpunkt (Wochen 11–14)
OSM Overpass + OpenRailwayMap + Wikidata-Stationsabfragen für alle Länder.
Mobility Database + Transitland für GTFS.
`partridge` + `gtfs-kit` als Indikator-Pipeline.

### Phase 4 — Soft Culture (Wochen 15–20)
Hofstede 6D + WVS Wave 7 + V-Dem v16 + **D-PLACE**.
ARDA + Pew GRI/SHI + Religion-and-State.
Glottolog + WALS + CLDR.
Equaldex + OECD SIGI + WBL.

### Phase 5 — Kunst/Heritage/Tourismus (Wochen 21–24)
**MusicBrainz PostgreSQL-Dump** direkt importieren.
Met + Smithsonian + Cleveland + V&A + Europeana.
UNESCO WHL/ICH via DataHub-API.
GHSL + Google Open Buildings.

---

## Anhang: Wichtige Python-Pakete

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

---

*Dieses Dokument ist eine lebende Referenz. Regelmäßig aktualisieren wenn neue Quellen integriert werden.*
