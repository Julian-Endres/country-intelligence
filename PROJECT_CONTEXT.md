# Project Context – Country Intelligence Layer

**Last updated:** 2026-05-28

---

## Vision

A multi-dimensional database aggregating country-level data from 25+ international sources. Long-term goal: an interactive, map-centric platform that gives a comprehensive view of any country – economy, geography, culture, infrastructure, environment, history.

Structured around the **Societal Intelligence Framework (SIF)** – 10 core domains covering the full complexity of societies.

**Portfolio positioning:** End-to-end data pipeline thinking, scalable DB architecture, international analytical perspective. Target: NGO/Impact/International Organizations sector.

---

## Conceptual Framework: SIF – 10 Core Domains

1. Population & Demographics
2. Geography & Environment
3. Economy & Infrastructure
4. Politics & Governance
5. Culture & Identity
6. Social Fabric & Daily Life
7. Communication & Media
8. Health, Body & Behavior
9. History & Collective Memory
10. International Relations & Global Integration

---

## 4-Level Hierarchy (domain → category → dimension → indicator)

`category` field in `indicator_metadata` is the SIF hierarchy level (not source category).

| Domain | Categories | Status |
|--------|-----------|--------|
| Population & Demographics | Population, Fertility, Migration, Urbanization | ✅ |
| Health, Body & Behavior | Survival & Mortality, Disease & Burden, Nutrition & Food, Health System, Risk Behavior, Environment & WASH | ✅ |
| Politics & Governance | Democracy & Elections, Rule of Law & Rights, State Capacity & Institutions, Security & Conflict, Political Economy | ✅ |
| Culture & Identity | Identity & Values, Religion & Belief, Cultural Production, Heritage & Memory | ✅ |
| Economy & Infrastructure | Output & Growth, Wealth & Inequality, Labour & Employment, Economic Structure, Public Finance & Energy, Human Development | ✅ |
| History & Collective Memory | Ethnicity & Peoples, Conflict & War, Economic History, State & Sovereignty | ✅ |
| Communication & Media | Digital Access, Press & Media Freedom | ✅ |
| Geography & Environment | Climate & Emissions, Land & Ecosystems, Biodiversity, Water & Weather, Environmental Inequality | ✅ |
| Social Fabric & Daily Life | Trust & Institutions, Civic Life, Wellbeing, Basic Services | ✅ |
| International Relations | ⏳ New sources needed (UN Voting, IGO, Alliance Data) | ⏳ |

---

## Architecture

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Core Tables

| Table | Description |
|-------|-------------|
| `countries` | 249 countries, ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 40+ registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, domain, category, dimension |
| `indicators` | 7M+ data values. Long format, SDMX-inspired |

### Relational Schemas

| Schema | Tables | Content |
|--------|--------|---------|
| `trade` | `trade_products`, `trade_partners` | Comtrade HS-4 flows + bilateral trade |
| `politics` | `political_parties`, `marpor_elections`, `constitutional_events`, `coups` | Political history |
| `international` | `diplomatic_relations`, `diplomatic_representation`, `colonial_history` | IR relational data |
| `history` | `ethnic_groups` | EPR ethnic group data 1946-2023 |

### Indicator Code Convention
Format: `SOURCE:ORIGINAL_CODE` (e.g. `WB:NY.GDP.PCAP.CD`, `VDEM:v2x_polyarchy`)
**Never invent codes** – always preserve original source codes.

### Design Principles
- `time_period` as TEXT: supports `"2023"`, `"2023-01"`, `"static"`
- `source_id` in UNIQUE key – allows parallel storage from multiple sources
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `ON CONFLICT DO NOTHING` everywhere – all scripts idempotent/re-runnable
- No hardcoded credentials – all via `.env`

---

## Tech Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (TCP on localhost:5432)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas, python-dotenv, fastapi, pygbif, openpyxl, pycountry
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code

### Setup Notes
- WSL2 + PostgreSQL: `listen_addresses = '*'` in postgresql.conf + pg_hba.conf modification
- PostgreSQL needs manual start: `sudo service postgresql start`
- Python venv: `~/projects/country-intelligence/venv`

---

## API Layer (FastAPI)

### Route Structure

```
GET /api/country/{iso_code}                           → Country Overview + Top KPIs
GET /api/country/{iso_code}/demography                → Domain Overview (4 Category Cards)
GET /api/country/{iso_code}/demography/population     → Population Detail + time series
GET /api/country/{iso_code}/demography/fertility      → Fertility Detail + time series
GET /api/country/{iso_code}/demography/migration      → Migration Detail + time series
GET /api/country/{iso_code}/demography/urbanization   → Urbanization Detail + time series
GET /api/country/{iso_code}/demography/pyramid        → Age pyramid (34 age groups)
GET /api/country/{iso_code}/timeseries/{indicator}    → Generic time series
GET /api/country/{iso_code}/governance                → Governance (flat, not blueprint yet)
GET /api/country/{iso_code}/economy                   → Economy (flat, not blueprint yet)
```

### Three-Level Navigation
```
Level 1 – Country Overview:   Map + Top KPIs
Level 2 – Domain Overview:    Category Cards with key indicator + signal
Level 3 – Category Detail:    All indicators + summary + time series
```

### get_indicator_summary() Fields
`value · z_score · trend_long · trend_short · trend_label · global_rank · regional_rank · latest_year · global_avg · n_countries`

### Indicator Types System
```python
"neutral":  increasing / stable / decreasing    # Population, Urbanization
"flow":     net_inflow / balanced / net_outflow  # Net migration
"positive": improving / stable / declining       # GDP, Life expectancy
"negative": improving / stable / declining       # Child mortality (inverted)
```

---

## Current Data Status (2026-05-28)

| Source | Code | Data Points | Countries | Period | Status |
|--------|------|-------------|-----------|--------|--------|
| World Bank WDI + WGI | WB | ~850k | 215 | 1996–2024 | ✅ |
| V-Dem | VDEM | 1.03M | 175 | 1900–2025 | ✅ |
| Freedom House | FH | 15.9k | 193 | 1972–2024 | ✅ |
| Transparency International CPI | TI | 2.3k | ~180 | 2012–2024 | ✅ |
| WHO GHO | WHO | 128k+ | 199–227 | 1932–2024 | ✅ |
| ILO | ILO | 22.3k | 188 | 2000–2027 | ✅ |
| UN Comtrade P1 (Products) | — | 5.72M | 184 | 2000–2024 | ✅ |
| UN Comtrade P2 (Partners) | — | 899k | 187 | 2000–2024 | ✅ |
| OWID CO2 | OWID_CO2 | 218k | ~200 | 1750–2024 | ✅ |
| OWID Energy (Ember + EI + EIA) | EMBER/EI/EIA | 93.8k | ~180 | 1965–2024 | ✅ |
| UNDP HDR + MPI | UNDP | ~38k | 195 | 1990–2023 | ✅ |
| FAO Land Use | FAO_LAND | ~200k | 236 | 1961–2025 | ✅ |
| FAO Food Balance Sheets | FAO_FOOD | 7.2k | 178 | 1961–2022 | ✅ |
| ND-GAIN Climate Index | NDGAIN | ~43k | 192 | 1995–2023 | ✅ |
| GBIF Biodiversity + IUCN | GBIF | ~25k | ~250 | 2000–2024 | ✅ |
| Open-Meteo ERA5 | OPENMETEO | ~17k | 48 | 2000–2023 | ✅ |
| Maddison Project 2023 | MADDISON | 38.5k | 166 | 1–2022 | ✅ |
| Correlates of War | COW | 585 | 82 | 1816–2003 | ✅ |
| EPR Ethnic Power Relations | EPR | 32.5k | 171 | 1946–2023 | ✅ |
| World Values Survey | WVS | 5.6k | 107 | 1981–2023 | ✅ |
| Hofstede 6 Dimensions | HOFSTEDE | 293 | 60 | static | ✅ |
| World Happiness Report | WHR | 7.9k | 158 | 2011–2025 | ✅ |
| Pew Research (Religion) | PEW_REL | ~3k | 199 | 2010–2020 | ✅ |
| CAF World Giving Index | CAF_WGI | ~7k | 161 | 2010–2024 | ✅ |
| Edelman Trust Barometer | EDELMAN | 12.3k | 28 | 2012–2025 | ✅ |
| WID.world (Inequality) | WID | ~275k | 215 | 1800–2024 | ✅ |
| Penn World Table 11.0 | PWT | ~211k | 185 | 1950–2023 | ✅ |
| SIPRI Military | SIPRI | ~8.5k | ~170 | 1949–2023 | ✅ |
| Polity5 | POLITY5 | ~102k | ~167 | 1800–2018 | ✅ |
| Global Health Index | GHI | ~1.2k | ~130 | 2000–2023 | ✅ |
| Fragile States Index | FSI | ~1.5k | 178 | 2006–2024 | ✅ |
| RSF Press Freedom | RSF | 1.6k | 180 | 2013–2021 | ✅ |
| UNESCO WHC + ICH | UNESCO | ~1.8k | ~170 | 2008–2025 | ✅ |
| Nobel Prize | NOBEL | ~1.4k | ~60 | 1901–2025 | ✅ |
| IMDb | IMDB | 30.8k | ~150 | 1900–2025 | ✅ |
| GI-TOC Crime Index | GITOC | ~17k | ~193 | 2021–2023 | ✅ |
| UNODC Homicide | UNODC | ~4k | ~190 | 2000–2022 | ✅ |
| **TOTAL** | | **~7M+** | | | |

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── base/
│   │   ├── wb/
│   │   ├── economy/       # load_comtrade.py, load_maddison.py, load_owid_co2.py, load_cpi.py
│   │   │                  # load_wb_governance.py, load_wb_infrastructure.py, load_ilostat.py
│   │   ├── health/        # load_who.py, load_fao_food.py, load_who_quickwins.py
│   │   ├── demographics/  # load_undp.py, load_wvs.py
│   │   ├── environment/   # load_fao_landuse.py, load_ndgain.py, load_gbif.py
│   │   │                  # load_gbif_iucn.py, load_openmeteo.py, load_owid_energy.py
│   │   ├── governance/    # load_freedom_house.py, load_vdem.py, load_rsf.py, load_wb_governance.py
│   │   ├── culture/       # load_hofstede.py, load_whr.py, load_nobel.py, load_olympics.py
│   │   │                  # load_unesco_whc.py, load_imdb.py
│   │   ├── history/       # load_cow.py, load_epr.py
│   │   └── social/        # load_edelman.py
│   ├── catalog/           # wb_catalog.py, indicator_search.sql
│   └── analysis/
├── sql/
│   ├── 01_setup/
│   ├── 02_seed/
│   └── 03_queries/
│   └── 04_categories/     # Category assignment scripts (one per domain)
├── api/
│   └── routes/
│       └── countries.py
├── docs/
│   ├── PROJECT_CONTEXT.md
│   ├── SOURCES_ROADMAP.md
│   ├── SOURCES_ENCYCLOPEDIA.md
│   └── SIF_DOMAIN_STRUCTURE.md   # NEW: full 4-level hierarchy doc
├── data/raw/              # NOT in git
├── .comtrade_state.json
├── .env                   # NOT in git
├── .env.example
└── README.md
```

---

## Open Items

### Immediate
1. Git commit – category sprint + new sources
2. WHO: `NCD_BMI_MINUS2C` + `TB_c_newinc` reload
3. `load_vdem.py` – remove `domain`/`dimension` columns (schema mismatch)
4. Save all category SQL scripts to `sql/04_categories/`

### Short Term — API
5. Health API route (blueprint pattern)
6. Countries List route: `GET /api/countries`
7. Compare route: `GET /api/compare?countries=BOL,PER,ARG`
8. Economy + Governance routes to Demography level

### Medium Term — New Sources
9. GTI Global Terrorism Index
10. Voter Turnout (IDEA)
11. UN Voting Data (Voeten)
12. IGO Membership (COW)
13. Alliance Data (ATOP)
14. Reuters Digital News Report (PDF scrape)
15. Global Forest Watch
16. Olympics historical (1896–2020)
17. Equaldex LGBTQ Rights
18. UNHCR Refugee Data
19. UCDP Conflict Data (token required)
20. Auto-descriptions for ~300 indicators without description (Claude API)

### Long Term
21. First visualizations (Folium / Kepler.gl / Plotly)
22. Power BI showcases
23. Frontend dashboard
24. Subnational data (Phase 3–4, PostGIS)

---

## Lessons Learned

- `partnerCode=ALL` is not a valid Comtrade API v1 parameter
- FastAPI route order matters: `/demography/pyramid` before `/demography/{category}`
- `ON CONFLICT DO UPDATE` fails when same row appears twice in batch → deduplicate first
- Comtrade sometimes returns duplicate rows
- IUCN API v3 blocked by Cloudflare → use GBIF `occ.search(iucnRedListCategory=...)` instead
- OWID blocks programmatic CSV downloads without User-Agent header
- Zone.Identifier files appear when copying Windows → WSL → add to `.gitignore`
- `data/raw/` belongs in `.gitignore`
- UNESCO DataHub API field: `iso_codes` not `iso_code`
- FAO Food Balance Sheets: indicators in `Element` field, not `Item`
- WVS is individual-level data → must aggregate to country level
- Maddison xlsx download redirects to HTML → manual browser download required
- UNDP time_period float issue: `str(int(float(row['year'])))` not direct cast
- Rejected Comtrade API calls (400) may still count against daily limit
- WB WGI: correct source is `source=75`, not `source=3`
- ILO INSERT must include `source_id` in tuple – otherwise UNIQUE constraint never fires
- `%` in psycopg2 SQL strings must be a parameter, not hardcoded in query string
- GW/COW codes ≠ ISO numeric – need manual mapping for EPR, COW datasets
- EPR defunct states (Yugoslavia, USSR) → replicate rows for successors with `is_successor=TRUE`
- Edelman loader: DELETE all before re-inserting (no idempotent fix possible due to missing dedup key)
