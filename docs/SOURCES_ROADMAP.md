# Data Sources Roadmap – Country Intelligence Layer

**Last updated:** 2026-05-28

---

## Status Overview

| Source | Code | Domain | Status | Data Points |
|--------|------|--------|--------|-------------|
| World Bank WDI | WB | Multi | ✅ Integrated | ~850k |
| RestCountries | REST | Base | ✅ Integrated | 249 countries |
| V-Dem Institute | VDEM | Governance | ✅ Integrated | 1.03M |
| Freedom House | FH | Governance | ✅ Integrated | 15.9k |
| Transparency International CPI | TI | Governance | ✅ Integrated | 2.3k |
| RSF Press Freedom Index | RSF | Governance/Media | ✅ Integrated | 1.6k |
| WHO GHO | WHO | Health | ✅ Integrated | 128k+ |
| UN Comtrade P1 (Products) | — | Economy | ✅ Integrated | 5.72M |
| UN Comtrade P2 (Partners) | — | Economy | ✅ Integrated | 899k |
| OWID CO2 & Energy | OWID_CO2 | Environment | ✅ Integrated | 218k |
| OWID Energy (Ember + EI + EIA) | EMBER/EI/EIA | Environment/Economy | ✅ Integrated | 93.8k |
| UNDP HDR + MPI | UNDP | Economy/Demographics | ✅ Integrated | ~38k |
| FAO Land Use | FAO_LAND | Environment | ✅ Integrated | ~200k |
| FAO Food Balance Sheets | FAO_FOOD | Health | ✅ Integrated | 7.2k |
| ND-GAIN Climate Index | NDGAIN | Environment | ✅ Integrated | ~43k |
| GBIF Biodiversity | GBIF | Environment | ✅ Integrated | ~25k |
| Open-Meteo ERA5 | OPENMETEO | Environment | ✅ Integrated | ~17k |
| Maddison Project 2023 | MADDISON | History | ✅ Integrated | 38.5k |
| Correlates of War | COW | History | ✅ Integrated | 585 |
| EPR Ethnic Power Relations | EPR | History | ✅ Integrated | 32.5k + relational |
| World Values Survey | WVS | Culture | ✅ Integrated | 5.6k |
| Hofstede 6 Dimensions | HOFSTEDE | Culture | ✅ Integrated | 293 |
| World Happiness Report | WHR | Social Fabric | ✅ Integrated | 7.9k |
| Pew Research (Religion) | PEW_REL | Culture | ✅ Integrated | ~3k |
| CAF World Giving Index | CAF_WGI | Social Fabric | ✅ Integrated | ~7k |
| Edelman Trust Barometer | EDELMAN | Social Fabric | ✅ Integrated | 12.3k |
| WID.world (Inequality) | WID | Economy | ✅ Integrated | ~275k |
| Penn World Table 11.0 | PWT | Economy | ✅ Integrated | ~211k |
| SIPRI Military Expenditure | SIPRI | Governance | ✅ Integrated | ~8.5k |
| Polity5 | POLITY5 | Governance | ✅ Integrated | ~102k |
| Global Health Index | GHI | Health | ✅ Integrated | ~1.2k |
| Fragile States Index | FSI | Governance | ✅ Integrated | ~1.5k |
| UNESCO WHC + ICH | UNESCO | Culture | ✅ Integrated | ~1.8k |
| Nobel Prize | NOBEL | Culture | ✅ Integrated | ~1.4k |
| IMDb | IMDB | Culture | ✅ Integrated | 30.8k |
| GI-TOC Crime Index | GITOC | Governance | ✅ Integrated | ~17k |
| UNODC Homicide | UNODC | Governance | ✅ Integrated | ~4k |
| WB WGI | WB | Governance | ✅ Integrated | 28.5k |
| ILO | ILO | Economy | ✅ Integrated | 22.3k |
| GTI Global Terrorism Index | GTI | Governance/History | ⏳ Planned | — |
| Voter Turnout (IDEA) | IDEA | Governance | ⏳ Planned | — |
| UCDP Conflict Data | UCDP | History | ⏳ Token required | — |
| UN Voting Data | UNVOTING | Int. Relations | ⏳ Planned | — |
| IGO Membership (COW) | IGO | Int. Relations | ⏳ Planned | — |
| Alliance Data (ATOP) | ATOP | Int. Relations | ⏳ Planned | — |
| Reuters Digital News Report | REUTERS | Media | ⏳ PDF scrape needed | — |
| Global Forest Watch | GFW | Environment | ⏳ Planned | — |
| Olympics historical | OLYMPICS | Culture | ⏳ Planned | — |
| Equaldex LGBTQ Rights | EQUALDEX | Culture/Governance | ⏳ Planned | — |
| UNHCR Refugee Data | UNHCR | Demographics | ⏳ Planned | — |
| CCKP Climate Data | CCKP | Environment | ⚠️ API issue | — |
| IMF DOTS Trade | IMF | Economy | ❌ Blocked (403) | — |

---

## Phase 1 – Cochabamba ✅ Complete

**Goal:** Foundation with the most important global sources (~5.5M data points)

---

## Phase 2 – Category Sprint ✅ Complete (2026-05-28)

**Goal:** Assign 4-level hierarchy (domain → category → dimension) to all indicators

- ✅ 9/10 domains fully categorized
- ✅ New sources added: WB WGI, WB Infrastructure, ILO (fixed), EPR, OWID Energy, Edelman (fixed)
- ✅ Comtrade extended to 2000-2024 (was 2010-2024)
- ✅ history.ethnic_groups table created
- ✅ ~7M+ total data points
- ⏳ International Relations – needs new sources first

---

## Phase 3 – New Sources & API

**Goal:** Fill IR domain + key gaps + extend API routes

### Priority 1 — Quick wins (1-2 days each)
1. GTI Global Terrorism Index – IEP Excel, ~163 countries, 2008–present
2. Voter Turnout – IDEA International, CSV, ~190 countries, 1945–present
3. WB additional Infrastructure – already identified, 1 API call

### Priority 2 — International Relations domain
4. UN Voting Data – Voeten dataset, Harvard Dataverse
5. IGO Membership – COW IGO Dataset
6. Alliance Data – ATOP

### Priority 3 — Environment gap
7. Global Forest Watch – Tree Cover Loss API
8. OWID fossil_fuel + renewables_share – fix loader

### Priority 4 — Culture & Social
9. Olympics historical (1896–2020) – Kaggle auth
10. Equaldex LGBTQ Rights
11. Reuters Digital News Report – PDF scrape

### Priority 5 — API routes
12. Health, Economy, Environment routes to Demography level
13. Countries List route
14. Compare route

---

## Phase 4 – Germany (Visualization & Portfolio)

1. UNHCR Refugee Data
2. UCDP Conflict Data
3. First visualizations (Folium / Kepler.gl)
4. Power BI showcases
5. Frontend dashboard
6. Subnational data (PostGIS)

---

## SIF Domain Coverage (2026-05-28)

| Domain | Sources | Categories | Coverage |
|--------|---------|-----------|----------|
| Population & Demographics | WB, WHO, UNDP | 4 | ✅ Good |
| Geography & Environment | FAO Land, GBIF, ND-GAIN, OWID CO2, OWID Energy, Open-Meteo, WID | 5 | ✅ Strong |
| Economy & Infrastructure | WB, Comtrade, Maddison, WID, PWT, ILO, EI, EIA, EMBER | 6 | ✅ Strong |
| Politics & Governance | V-Dem, FH, RSF, Polity5, SIPRI, FSI, GITOC, UNODC, WGI, TI | 5 | ✅ Strong |
| Culture & Identity | Hofstede, WVS, WHR, Nobel, UNESCO, IMDb, Pew | 4 | ✅ Good |
| Social Fabric & Daily Life | WVS, WHR, CAF, Edelman, WHO WASH | 4 | 🟡 Thin (28 countries Edelman) |
| Communication & Media | RSF, WB Internet, WB Mobile | 2 | 🟡 Thin (Reuters missing) |
| Health, Body & Behavior | WB, WHO, FAO Food, GHI | 6 | ✅ Good |
| History & Collective Memory | Maddison, COW, EPR + relational tables | 4 | 🟡 Growing |
| International Relations | Comtrade (relational) | ⏳ | ❌ No indicators yet |

---

## Blocked / Problematic Sources

| Source | Problem | Workaround |
|--------|---------|------------|
| IUCN Red List API | Cloudflare block | GBIF `iucnRedListCategory` filter |
| CCKP ERA5 Timeseries | API returns empty data | Open-Meteo instead |
| COW Intrastate v5.1 | ZIP is HTML redirect | Manual download |
| Maddison xlsx | Redirect to HTML | Manual browser download |
| OWID CSV direct | 403 without User-Agent | Set User-Agent header |
| IMF DOTS | 403 API protection | No workaround found |
| WB WGI | source=3 invalid → use source=75 | Fixed |
| ILO | source_id missing from INSERT → UNIQUE never fires | Fixed |
