# Project Context – Country Intelligence Layer

This document captures the full context of the project for AI assistants and future reference. Update regularly.

Last updated: 2026-05-07

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

Target audience: Recruiters in NGO/Impact/International Organizations sector.

---

## Architecture Decisions

### Database: PostgreSQL
- Industry standard, scales well, fits future plans (PostGIS for geo data later)
- Running locally on WSL2 Ubuntu

### Primary Key Strategy: ISO numeric for countries
- Uses ISO 3166-1 numeric standard as primary key for `countries` table
- Internationally standardized, never changes, compatible with World Bank, UN, WHO data
- For other tables (sources, indicators), SERIAL is used since no external standard exists

### Schema: 4 core tables
1. `countries` – stable country data (immutable facts only)
2. `sources` – data sources catalog
3. `indicator_metadata` – describes what each indicator means
4. `indicators` – actual values (one row per country/indicator/year)

### Design Principle
- Stable, immutable facts in `countries`
- Anything multi-valued or time-dependent gets its own table
- Future subdomain tables planned: transport, languages, religions, etc.

### What was deliberately NOT built
- No `regions` table – overengineering for 7 regions
- No `update_log` table – overkill for solo project, `last_updated` field sufficient
- No historical data yet – structure supports it, but only loading current year first

---

## Technical Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (running in WSL)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code
- **Hardware:** ThinkPad T490

## Connection Details (Local Development)

Stored in `.env` file (not committed). See `.env.example` for required variables.

## Current Status
✅ World Bank GDP per capita loaded for 5 countries (test)
✅ Environment variables setup with .env
✅ Project pushed to GitHub
### ✅ Completed
- WSL2 + Ubuntu setup
- PostgreSQL installed and configured (TCP connections enabled)
- Project structure with venv
- 4 core tables created
- 5 sources seeded
- 5 indicator metadata entries seeded
- 249 countries loaded from RestCountries API
- Region mapping completed (Africa: 59, Americas: 56, Europe: 52, Asia: 50, Oceania: 27, Antarctic: 5)
- SQL scripts organized in numbered folders
- README and PROJECT_CONTEXT documentation

### 🔄 In Progress
- Understanding the architecture deeply before adding more

### ⏳ Next Steps
1. Load World Bank data into `indicators` table (GDP, life expectancy, population, literacy, Gini)
2. Push project to GitHub
3. First visualization (world map with one indicator)
4. Add more indicators progressively

### 📋 Backlog / Future
- WHO health data
- UNDP HDI data
- V-Dem political data
- Country geometry (PostGIS)
- Public transport / rail network data (OpenStreetMap, OpenRailwayMap)
- Cultural data (Hofstede, World Values Survey)
- Web scraping layer (Numbeo, Wikipedia)
- Interactive dashboard (Plotly + Dash + Folium)

---

## Project Structure
country-intelligence/
├── scripts/
│   ├── load_countries.py
│   └── world_bank.py
├── sql/
│   ├── 01_setup/
│   │   ├── 01_drop_tables.sql
│   │   ├── 02_create_sources.sql
│   │   ├── 03_create_countries.sql
│   │   ├── 04_create_indicator_metadata.sql
│   │   └── 05_create_indicators.sql
│   ├── 02_seed/
│   │   ├── 01_insert_sources.sql
│   │   ├── 02_insert_indicator_metadata.sql
│   │   └── 03_update_regions.sql
│   └── 03_queries/
│       └── exploration_queries.sql
├── venv/
├── README.md
└── PROJECT_CONTEXT.md
---

## Lessons Learned & Gotchas

- **WSL2 + PostgreSQL:** Need to enable `listen_addresses = '*'` in postgresql.conf and add line to pg_hba.conf for Windows ↔ WSL connection
- **PostgreSQL doesn't auto-start in WSL:** Manual `sudo service postgresql start` needed after Windows restart (TODO: automate)
- **DBeaver UPDATE statements:** Need explicit COMMIT in some cases
- **RestCountries API:** Limited to 10 fields per request – need to use ?fields= parameter explicitly
- **Region data:** Not provided directly by RestCountries with limited fields, derived from subregion via UPDATE statements

---

## Key Data Sources Documented

| Source | Code | Status | URL |
|--------|------|--------|-----|
| World Bank | WB | Planned | data.worldbank.org |
| WHO | WHO | Planned | who.int/data |
| UNDP | UNDP | Planned | hdr.undp.org |
| RestCountries | REST | ✅ Used | restcountries.com |
| V-Dem | VDEM | Planned | v-dem.net |