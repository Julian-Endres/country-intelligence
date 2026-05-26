# Data Sources Roadmap – Country Intelligence Layer

**Last updated:** 2026-05-26

---

## Status Overview

| Source | Code | Domain | Status | Data Points |
|--------|------|--------|--------|-------------|
| World Bank WDI | WB | Multi | ✅ Integrated | ~750k |
| RestCountries | REST | Base | ✅ Integrated | 249 countries |
| V-Dem Institute | VDEM | Governance | ✅ Integrated | 1.03M |
| Freedom House | FH | Governance | ✅ Integrated | 15.9k |
| Transparency International CPI | CPI | Governance | ✅ Integrated | 2.3k |
| RSF Press Freedom Index | RSF | Media | ✅ Integrated | 1.6k |
| WHO GHO | WHO | Health | ✅ Integrated | 128k |
| UN Comtrade P1 (Products) | — | Economy | ✅ Integrated | 2.93M |
| UN Comtrade P2 (Partners) | — | Economy | 🔄 Loading | — |
| OWID CO2 & Energy | OWID_CO2 | Environment | ✅ Integrated | 218k |
| UNDP HDR + MPI | UNDP | Development | ✅ Integrated | ~38k |
| FAO Land Use | FAO_LAND | Environment | ✅ Integrated | ~200k |
| FAO Food Balance Sheets | FAO_FOOD | Health | ✅ Integrated | 7.2k |
| ND-GAIN Climate Index | NDGAIN | Environment | ✅ Integrated | ~43k |
| GBIF Biodiversity | GBIF | Environment | ✅ Integrated | 1.9k |
| GBIF IUCN Red List | GBIF | Environment | ✅ Integrated | 991 |
| Open-Meteo ERA5 | OPENMETEO | Environment | ✅ Integrated | ~17k |
| Maddison Project 2023 | MADDISON | History | ✅ Integrated | 38.5k |
| Correlates of War | COW | History | ✅ Integrated | 585 |
| World Values Survey | WVS | Culture | ✅ Integrated | 5.6k |
| Hofstede 6 Dimensions | HOFSTEDE | Culture | ✅ Integrated | 293 |
| World Happiness Report | WHR | Social | ✅ Integrated | 7.9k |
| UNESCO World Heritage | UNESCO_WHC | Culture | ✅ Integrated | 461 |
| Nobel Prize API | NOBEL | Culture | ✅ Integrated | ~600 |
| IMDb Titles | IMDB | Media | ✅ Integrated | 30.8k |
| Olympics Paris 2024 | OLYMPICS | Culture | ✅ Integrated | small |
| Global Forest Watch | GFW | Environment | ⏳ Planned | — |
| Olympics historical | OLYMPICS | Culture | ⏳ Planned | — |
| Penn World Table | PWT | Economy | ⏳ Planned | — |
| Gapminder | GAPMINDER | Multi | ⏳ Planned | — |
| Equaldex LGBTQ Rights | EQUALDEX | Culture | ⏳ Planned | — |
| UCDP Conflict Data | UCDP | History | ⏳ Token required | — |
| CEPALSTAT | CEPAL | Economy | ⏳ Planned | — |
| Human Freedom Index | HFI | Governance | ⏳ Planned | — |
| Global Hunger Index | GHI | Health | ⏳ Planned | — |
| UNHCR Refugee Data | UNHCR | Demographics | ⏳ Planned | — |
| CCKP Climate Data | CCKP | Environment | ⚠️ API issue | — |

---

## Phase 1 – Cochabamba ✅ Complete

**Goal:** Foundation with the most important global sources

- ✅ World Bank – 34 indicators historically 2000–2024
- ✅ WHO GHO – 22 health indicators
- ✅ V-Dem – 1M+ democracy data points
- ✅ Freedom House, CPI
- ✅ Comtrade – 2.93M trade rows (products)
- ✅ UNDP, Hofstede, WVS, WHR
- ✅ OWID CO2, FAO Land + Food
- ✅ ND-GAIN, GBIF, Open-Meteo
- ✅ Maddison, COW, UNESCO, Nobel, IMDb, RSF
- ✅ FastAPI layer (Demography blueprint)

---

## Phase 2 – Next Steps

**Goal:** Fill gaps, extend API

1. Comtrade P1 load 2000–2009
2. Comtrade P2 finish loading
3. WHO: 2 indicators reload
4. Global Forest Watch – Tree Cover Loss 2001–2023
5. Olympics historical 1896–2020
6. Penn World Table – TFP, Human Capital
7. Gapminder historical series
8. API routes: Health, Economy, Environment to Demography level

---

## Phase 3 – Germany

**Goal:** Visualization + Portfolio

1. Equaldex LGBTQ Rights
2. UCDP Conflict Data
3. CEPALSTAT Latin America
4. Human Freedom Index
5. UNHCR Refugee Data
6. First visualizations (Folium / Kepler.gl)
7. Power BI showcases
8. Frontend dashboard

---

## SIF Domain Coverage

| Domain | Sources | Coverage |
|--------|---------|----------|
| Population & Demographics | WB, WHO, UNDP | ✅ Good |
| Geography & Environment | FAO Land, GBIF, ND-GAIN, OWID CO2, Open-Meteo | ✅ Good |
| Economy & Infrastructure | WB, Comtrade, Maddison, CPI | ✅ Good |
| Politics & Governance | V-Dem, Freedom House, RSF | ✅ Good |
| Culture & Identity | Hofstede, WVS, WHR, Nobel, UNESCO, IMDb | ✅ Good |
| Social Fabric & Daily Life | WVS, WHR | 🟡 Thin |
| Communication & Media | Nobel, IMDb, RSF | 🟡 Thin |
| Health, Body & Behavior | WB, WHO, FAO Food | ✅ Good |
| History & Collective Memory | Maddison, COW, V-Dem | 🟡 Started |
| International Relations | Comtrade | ✅ Good |

---

## Topic Coverage (original vision)

| Topic | Best Source | Status |
|-------|------------|--------|
| Food & Nutrition | FAO Food Balance Sheets | ✅ |
| History & Conflicts | Maddison, COW, V-Dem | ✅ |
| Cultural Values | WVS, Hofstede | ✅ |
| Language | RestCountries (basic) | ✅ basic |
| Political situation | V-Dem, Freedom House | ✅ |
| Flora & Fauna | GBIF | ✅ |
| Climate & Weather | Open-Meteo, ND-GAIN | ✅ |
| Geographic position | RestCountries | ✅ |
| Economy | World Bank, Comtrade | ✅ |
| Religion | WVS (partial) | 🟡 |
| Press & Media freedom | RSF | ✅ |
| Happiness & Wellbeing | WHR | ✅ |
| Trade flows | Comtrade | ✅ |
| Deforestation | Global Forest Watch | ⏳ |
| LGBTQ rights | Equaldex | ⏳ |
| Refugees & Migration | UNHCR | ⏳ |
| Arts & Culture (museums) | The Met API, Rijksmuseum | ⏳ |
| Literature | Project Gutenberg | ⏳ |
| Infrastructure | OpenRailwayMap, OSM | ⏳ |

---

## Blocked / Problematic Sources

| Source | Problem | Workaround |
|--------|---------|------------|
| IUCN Red List API | Cloudflare block | GBIF `iucnRedListCategory` filter |
| CCKP ERA5 Timeseries | API returns empty data | Open-Meteo instead |
| COW Intrastate v5.1 | ZIP is HTML redirect | Manual download required |
| Maddison xlsx | Redirect to HTML | Manual browser download |
| OWID CSV direct | 403 without User-Agent | Set User-Agent header |
| Box Office revenue | No free bulk download | TMDB API (rate limited) |
| Equaldex via OWID | OWID URLs return 404 | Direct Equaldex API |
| Latinobarómetro | No direct API | Manual Excel export |
