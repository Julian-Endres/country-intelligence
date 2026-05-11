# Data Sources Roadmap – Country Intelligence Layer

Last updated: 2026-05

---

## Status Übersicht

| Quelle | Kategorie | Status | Priorität |
|--------|-----------|--------|-----------|
| World Bank WDI | Wirtschaft, Gesundheit, Bildung | ✅ Integriert | Hoch |
| RestCountries | Basisdaten | ✅ Integriert | Hoch |
| WHO GHO | Gesundheit, Sucht | ⏳ Geplant | Hoch |
| Latinobarómetro | Kultur, Werte, Lateinamerika | ⏳ Geplant | Hoch |
| OWID | Aufbereitete Daten, viele Themen | ⏳ Geplant | Hoch |
| V-Dem | Demokratie, Politik | ⏳ Geplant | Mittel |
| World Values Survey | Kultur, Werte, Traditionen | ⏳ Geplant | Mittel |
| CEPALSTAT | Lateinamerika spezifisch | ⏳ Geplant | Mittel |
| UNDP HDR | HDI, Bildung, Ungleichheit | ⏳ Geplant | Mittel |
| UNESCO | Weltkulturerbe, Bildung | ⏳ Geplant | Mittel |
| UNODC | Drogen, Kriminalität | ⏳ Geplant | Mittel |
| GBIF | Flora, Fauna, Biodiversität | ⏳ Geplant | Niedrig |
| The Met / Rijksmuseum | Kunst, Kultur | ⏳ Geplant | Niedrig |
| OpenStreetMap / OpenRailwayMap | Verkehr, Infrastruktur | ⏳ Geplant | Niedrig |
| Numbeo | Lebensqualität, Preise | ⏳ Geplant | Niedrig |
| Hofstede Insights | Kulturdimensionen | ⏳ Geplant | Niedrig |
| IDB | Lateinamerika Entwicklung | ⏳ Geplant | Niedrig |
| FAOSTAT | Landwirtschaft, Ernährung | ⏳ Geplant | Niedrig |

---

## Phase 1 – Cochabamba (aktuell)

**Ziel:** Fundament mit den wichtigsten globalen Quellen

1. ✅ World Bank – 1.486 Indikatoren im Catalog, 5 Kernindikatoren geladen
2. ⏳ WHO GHO – Gesundheit, Sucht, reproduktive Gesundheit
3. ⏳ Latinobarómetro – Kulturwerte Lateinamerika (manueller Export)
4. ⏳ OWID – aufbereitete CSVs für Armut, Energie, Umwelt

---

## Phase 2 – Reisephase

**Ziel:** Politische und kulturelle Tiefe

1. V-Dem – 500+ Demokratie-Indikatoren, CSV Download
2. World Values Survey – Werte, Traditionen, Vertrauen seit 1981
3. UNDP HDR – HDI, Gender Inequality Index
4. CEPALSTAT – Lateinamerika spezifisch, R-Paket verfügbar

---

## Phase 3 – Deutschland

**Ziel:** Spezialthemen und Visualisierung

1. UNESCO – Weltkulturerbe CSV
2. UNODC – Drogen und Kriminalität
3. GBIF – Flora und Fauna (pygbif)
4. OpenRailwayMap – Schienennetz
5. Numbeo – Lebensqualität (Scraping)
6. Hofstede – Kulturdimensionen (Scraping)

---

## Themen-Abdeckung

| Thema (aus ursprünglicher Liste) | Beste Quelle | Status |
|----------------------------------|-------------|--------|
| Essen | FAO, OWID | ⏳ |
| Geschichte | COW, V-Dem | ⏳ |
| Traditionen | World Values Survey, Latinobarómetro | ⏳ |
| Sprache | RestCountries (Basis), Open Library | ⏳ |
| Herkunft | COW Colonial Dataset | ⏳ |
| Politische Situation | V-Dem | ⏳ |
| Regionale Unterschiede | CEPALSTAT, nationale Portale | ⏳ |
| Traumas | GBD (IHME), WHO | ⏳ |
| Zwischenmenschlichkeit | World Values Survey | ⏳ |
| Rituale | World Values Survey, eHRAF | ⏳ |
| Regionale Verbindungen | COW Alliances | ⏳ |
| Politische Geschichte | V-Dem (seit 1789), COW | ⏳ |
| Abhängigkeiten | COW Colonial/Dependency | ⏳ |
| Familienstruktur | World Values Survey | ⏳ |
| Kunst | The Met API, Rijksmuseum API | ⏳ |
| Flora und Fauna | GBIF | ⏳ |
| Tiere | GBIF | ⏳ |
| Wetter | Data Commons (NOAA/NASA) | ⏳ |
| Geographische Position | RestCountries ✅ | ✅ |
| Süchte | WHO GHO, UNODC | ⏳ |
| Mode | Europeana, The Met | ⏳ |
| Alkohol und Drogen | WHO GHO, UNODC | ⏳ |
| Straßenverkehr | Data Commons, OSM | ⏳ |
| Körperliche Nähe | World Values Survey | ⏳ |
| Sex | WHO GHO | ⏳ |
| Männlichkeit | World Values Survey, WVS | ⏳ |
| Ökonomische Situation | World Bank ✅ | ✅ |
| Religion | World Values Survey, ARDA | ⏳ |
| Schmuck | The Met API | ⏳ |
| Literatur | Project Gutenberg, Open Library | ⏳ |
| Hygiene | JMP (WHO/UNICEF) | ⏳ |
| Tourismus | UNESCO World Heritage | ⏳ |

---

## Technische Notizen

### Python Wrapper die wir nutzen werden
- `wbgapi` – World Bank (besser als direkte API)
- `pygbif` – GBIF Flora/Fauna
- `pandas` – OWID CSVs direkt laden

### Lateinamerika Spezialquellen
- **Latinobarómetro** – kein direkter API-Zugriff, manueller Export als Excel
- **CEPALSTAT** – R-Paket `CepalStatR`, Python über direkte JSON API
- **IDB** – R-Paket `Numbers for Development`
- **Nationale Portale** – Argentinien, Brasilien, Kolumbien, Chile alle CKAN-basiert
- **ColombiAPI** – Spezialpaket für Kolumbien (Flughäfen, Gerichte, Radiostationen)

### Wichtige Standards
- SDMX – UNdata, OECD, CEPALSTAT nutzen diesen Standard
- CKAN – Standard für nationale Open-Data-Portale Lateinamerika
- CC0 – The Met, viele Museen – frei nutzbar ohne Einschränkungen