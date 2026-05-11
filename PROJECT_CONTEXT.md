# Project Context – Country Intelligence Layer

This document captures the full context of the project for AI assistants and future reference. Update regularly.

Last updated: 2026-05-11

---

## Vision

A multi-dimensional database that aggregates country-level data from international sources into a unified system. Long-term goal: an interactive dashboard with maps and visualizations that gives a comprehensive view of any country in the world – economy, geography, culture, infrastructure, environment.

Project narrative: Started in Cochabamba, Bolivia, during a sabbatical in 2026. Combines technical skill-building with genuine intellectual curiosity about countries and cultures.

## Portfolio Positioning

The project demonstrates:
- Ability to find and connect data from many different sources (not just pre-cleaned datasets)
- End-to-end data pipeline thinking (API → Python → Database → Visualization)
- Clean, scalable database architecture
- International perspective and substantive content
- Personal data search engine for international development data

Target audience: Recruiters in NGO/Impact/International Organizations sector.

---

## Architecture Decisions

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Primary Key Strategy
- `countries`: ISO 3166-1 numeric (iso_numeric) – internationally standardized, never changes
- All other tables: SERIAL – no external standard exists

### Schema: 4 core tables + indicator catalog
1. `countries` – stable country data (immutable facts only), 249 countries
2. `sources` – data sources catalog
3. `indicator_metadata` – describes what each indicator means (WB: prefix convention)
4. `indicators` – actual values with source_id, time_period (text), obs_status (SDMX-inspired)
5. `indicator_catalog` – all available indicators from all sources with coverage data

### Indicator Code Convention
Format: `SOURCE:ORIGINAL_CODE` (e.g. `WB:NY.GDP.PCAP.CD`)
Never invent own codes – always keep original source codes.

### Design Principles
- Stable, immutable facts in `countries`
- Anything multi-valued or time-dependent gets its own table
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `time_period` as TEXT (not INT) to support quarterly/monthly data later
- `source_id` in UNIQUE key of indicators – allows parallel storage of same indicator from multiple sources

### What was deliberately NOT built
- No `regions` table – overengineering for 7 regions
- No `update_log` table – `last_updated` field sufficient
- No historical data yet – structure supports it, only loading current year first

---

## Technical Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (running in WSL)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas, python-dotenv, streamlit
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code
- **Hardware:** ThinkPad T490

## Connection Details (Local Development)

Stored in `.env` file (not committed). See `.env.example` for required variables.

---

## Current Status

### ✅ Completed
- WSL2 + Ubuntu setup (including BIOS virtualization fix)
- PostgreSQL 18 installed and configured (TCP connections enabled)
- DBeaver connected via WSL2 bridge
- Project structure with venv
- 4 core tables + indicator_catalog created
- Environment variables with .env (no passwords in code)
- 249 countries loaded from RestCountries API
- Region mapping completed (Africa: 59, Americas: 56, Europe: 52, Asia: 50, Oceania: 27, Antarctic: 5)
- 5 World Bank indicators loaded for all 249 countries (654 data points)
  - WB:NY.GDP.PCAP.CD – GDP per capita
  - WB:SP.DYN.LE00.IN – Life expectancy
  - WB:SP.POP.TOTL – Total population
  - WB:SE.ADT.LITR.ZS – Literacy rate
  - WB:SI.POV.GINI – Gini coefficient
- World Bank Indicator Catalog: 1.486 indicators with categories and coverage data
- Coverage analysis: latest_year + coverage_recent fields populated
- Search tool (search.py) – keyword search across indicator catalog
- Coverage check tool (check_coverage.py) – coverage analysis per indicator
- Batch coverage script (batch_coverage.py) – bulk coverage update
- Streamlit web app (app.py) – interactive indicator explorer with filters
- Coverage view (v_country_coverage) in DBeaver
- SQL scripts organized in numbered folders
- Full documentation: README, PROJECT_CONTEXT, SOURCES_ROADMAP, SOURCES_ENCYCLOPEDIA
- Project pushed to GitHub

### 🔄 In Progress
- Batch coverage script ran – latest_year and coverage_recent being populated

### ⏳ Next Steps
1. First visualization – world map with GDP per capita (Plotly + Folium)
2. WHO GHO integration (next major data source)
3. Latinobarómetro (Latin America cultural data)
4. OWID CSVs integration
5. Autostart PostgreSQL in WSL (TODO)

### 📋 Backlog / Future
- WHO health data
- UNDP HDI data
- V-Dem political data (500+ democracy indicators)
- World Values Survey (cultural values)
- CEPALSTAT (Latin America specific)
- Country geometry (PostGIS)
- Public transport / rail network (OSM, OpenRailwayMap, Mobility Database)
- Cultural data (Hofstede, D-PLACE)
- Web scraping layer (Numbeo, Hofstede)
- Interactive dashboard (Plotly + Dash + Folium)

---

## Project Structure

country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── load_countries.py
│   │   └── world_bank.py
│   ├── catalog/
│   │   ├── wb_catalog.py       # Load WB indicator catalog
│   │   ├── search.py           # Terminal search tool
│   │   ├── check_coverage.py   # Coverage check per indicator
│   │   ├── batch_coverage.py   # Bulk coverage update
│   │   └── app.py              # Streamlit web app
│   └── analysis/
├── sql/
│   ├── 01_setup/
│   ├── 02_seed/
│   └── 03_queries/
│       ├── exploration_queries.sql
│       └── indicator_search.sql
├── docs/
│   ├── SOURCES_ROADMAP.md
│   └── SOURCES_ENCYCLOPEDIA.md
├── .env.example
├── venv/
├── README.md
└── PROJECT_CONTEXT.md

---

## Lessons Learned & Gotchas

- **WSL2 + PostgreSQL:** Enable `listen_addresses = '*'` in postgresql.conf + add line to pg_hba.conf
- **PostgreSQL auto-start:** Manual `sudo service postgresql start` needed after Windows restart
- **DBeaver UPDATE statements:** Need explicit COMMIT in some cases
- **RestCountries API:** Limited to 10 fields per request – use ?fields= parameter
- **Region data:** Derived from subregion via UPDATE statements (not in API with 10-field limit)
- **World Bank API:** Returns aggregates (regions, income groups) mixed with real countries – filter via countries table join
- **Indicator codes:** Always use `SOURCE:ORIGINAL_CODE` format (WB:NY.GDP.PCAP.CD) – never invent codes
- **source_id in UNIQUE key:** Critical for multi-source aggregation (IMF + WB both have GDP data)
- **time_period as TEXT:** Enables quarterly (2024-Q1) and monthly (2024-03) data later
- **obs_status:** SDMX-inspired field – A=actual, E=estimated, P=provisional, F=forecast

---

## Key Data Sources

| Source | Code | Status | Indicators | URL |
|--------|------|--------|------------|-----|
| World Bank WDI | WB | ✅ Active | 1.486 in catalog, 5 loaded | data.worldbank.org |
| RestCountries | REST | ✅ Active | Base country data | restcountries.com |
| WHO GHO | WHO | ⏳ Planned | ~2.300 | who.int/data |
| UNDP HDR | UNDP | ⏳ Planned | HDI, GII, MPI | hdr.undp.org |
| V-Dem | VDEM | ⏳ Planned | 500+ democracy | v-dem.net |
| Latinobarómetro | LATBAR | ⏳ Planned | Cultural values | latinobarometro.org |
| World Values Survey | WVS | ⏳ Planned | Values since 1981 | worldvaluessurvey.org |
| CEPALSTAT | CEPAL | ⏳ Planned | 1.000+ LAC | api-cepalstat.cepal.org |