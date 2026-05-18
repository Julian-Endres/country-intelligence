# Project Context – Country Intelligence Layer

This document captures the full context of the project for AI assistants and future reference. Update regularly.

Last updated: 2026-05-18

---

## Vision

A multi-dimensional database that aggregates country-level data from international sources into a unified system. Long-term goal: an interactive, map-centric platform that gives a comprehensive view of any country in the world – economy, geography, culture, infrastructure, environment, history.

Project narrative: Started in Cochabamba, Bolivia, during a sabbatical in 2026. Combines technical skill-building with genuine intellectual curiosity about countries and cultures.

The goal is not to show numbers. The goal is to answer questions:
- "Where is child mortality high?"
- "Which regions of Bolivia are the poorest?"
- "Where does Bolivia export its raw materials?"
- "How have these things developed over the last years?"

## Portfolio Positioning

The project demonstrates:
- Ability to find and connect data from many different sources (not just pre-cleaned datasets)
- End-to-end data pipeline thinking (API → Python → Database → Visualization)
- Clean, scalable database architecture
- International perspective and substantive content

Target audience: Recruiters in NGO/Impact/International Organizations sector.

---

## Conceptual Framework: Societal Intelligence Framework (SIF)

The project is structured around 10 core domains from the SIF framework:

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

Each indicator in `indicator_metadata` is mapped to a `domain` and `dimension` from this framework. This is the project's own classification layer, separate from the original source categories (e.g. World Bank topics).

---

## Architecture Decisions

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Primary Key Strategy
- `countries`: ISO 3166-1 numeric (iso_numeric) – internationally standardized, never changes
- All other tables: SERIAL – no external standard exists

### Schema: 5 core tables
1. `countries` – stable country data (immutable facts only), 249 countries
2. `sources` – data sources catalog
3. `indicator_metadata` – describes what each indicator means (WB: prefix convention)
4. `indicators` – actual values with source_id, time_period (text), obs_status (SDMX-inspired)
5. `indicator_catalog` – all available indicators from all sources with coverage data (1.486 WB indicators)

### Indicator Code Convention
Format: `SOURCE:ORIGINAL_CODE` (e.g. `WB:NY.GDP.PCAP.CD`)
Never invent own codes – always keep original source codes.

### Two-Layer Categorization
- `category` field = original source category (e.g. World Bank topic) → never overwrite
- `domain` + `dimension` fields = SIF classification → project's own layer

### Design Principles
- Stable, immutable facts in `countries`
- Anything multi-valued or time-dependent gets its own table
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `time_period` as TEXT (not INT) to support quarterly/monthly data later
- `source_id` in UNIQUE key of indicators – allows parallel storage of same indicator from multiple sources

### What was deliberately NOT built
- No `regions` table – overengineering for 7 regions
- No `update_log` table – `last_updated` field sufficient

---

## Technical Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (running in WSL)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas, python-dotenv, streamlit, plotly
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code
- **Hardware:** ThinkPad T490

## Connection Details (Local Development)

Stored in `.env` file (not committed). See `.env.example` for required variables.

---

## Current Status (2026-05-18)

### Data loaded: ~500.000+ Datenpunkte

| Domain | Indikatoren | Zeitraum | Coverage |
|---|---|---|---|
| Population & Demographics | 91 | 2000–2024 | 215 Länder |
| Health, Body & Behavior | 12 | 2000–2024 | 183–215 Länder |
| Economy & Infrastructure | 3 | 2000–2024 | 212–215 Länder |
| Communication & Media | 1 | 2024 | 29 Länder |

### Coverage Notes
- 215 Länder haben mindestens einen Datenpunkt
- 34 Länder bei 0% – Territorien, Mikrostaaten, keine eigene Statistikbehörde
- Taiwan: strukturell fehlend (WB führt Taiwan nicht als vollständiges Mitglied)
- Median Coverage: 94% bei "echten" Ländern

### ✅ Completed
- WSL2 + PostgreSQL setup
- 249 countries loaded from RestCountries API
- Region mapping completed
- World Bank Indicator Catalog: 1.486 indicators with categories and coverage data
- 34 core indicators loaded historically (2000–2024) – 164.808 Datenpunkte
- 55 demographic indicators loaded (2000–2024) – ~300.000 Datenpunkte
- SIF Domain/Dimension mapping on all loaded indicators
- Data quality checks established
- Search tool, Coverage tools, Streamlit Indicator Explorer
- Full project documentation

### ⏳ Next: Further data loading by domain
Priority order:
1. Economy & Infrastructure (WB: Poverty, Trade, Infrastructure)
2. Health deeper (WHO GHO ~2.300 indicators)
3. UN Comtrade (trade flows – "where does Bolivia export its raw materials?")
4. Geography & Environment (Open-Meteo, Natural Earth)

### 📋 Later phases
- V-Dem political data (500+ democracy indicators)
- World Values Survey (cultural values)
- CEPALSTAT (Latin America specific)
- Visualization layer (Plotly, Folium → Kepler.gl)
- Interactive dashboard

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── load_countries.py           # RestCountries import, einmalig
│   │   ├── load_demographics.py        # WB Demographics 2000-2024
│   │   └── world_bank_historical.py    # Original 34 Indikatoren, historische Referenz
│   ├── catalog/
│   │   ├── wb_catalog.py               # Load WB indicator catalog
│   │   ├── search.py                   # Terminal keyword search
│   │   ├── check_coverage.py           # Coverage check per indicator
│   │   ├── batch_coverage.py           # Bulk coverage update
│   │   └── app.py                      # Streamlit indicator explorer
│   └── analysis/                       # (leer, Visualisierungen kommen später)
├── sql/
│   ├── 01_setup/                       # Table creation scripts
│   ├── 02_seed/                        # Initial data + SIF mapping
│   └── 03_queries/
│       ├── data_quality_checks.sql     # Regelmäßige DB-Checks
│       ├── exploration_queries.sql
│       └── indicator_search.sql
├── docs/
│   ├── SOURCES_ROADMAP.md
│   └── SOURCES_ENCYCLOPEDIA.md
├── .env.example
├── README.md
└── PROJECT_CONTEXT.md
```

---

## Lessons Learned & Gotchas

- **WSL2 + PostgreSQL:** Enable `listen_addresses = '*'` in postgresql.conf + add line to pg_hba.conf
- **PostgreSQL auto-start:** Manual `sudo service postgresql start` needed after Windows restart
- **Foreign Key on indicators:** Always insert into `indicator_metadata` BEFORE running a load script, or FK violation crashes the script
- **RestCountries API:** Limited to 10 fields per request
- **World Bank API:** Returns aggregates mixed with real countries – filter via countries table join
- **Indicator codes:** Always use `SOURCE:ORIGINAL_CODE` format – never invent codes
- **WB categories:** Keep original WB categories intact – use `domain`/`dimension` as own classification layer
- **Taiwan:** Structurally missing from WB data – political, not a data error
- **Literacy (SE.ADT.LITR.ZS):** Only 29 countries – missing exactly where most relevant (developing countries). Deprioritize.
- **Gini (SI.POV.GINI):** Only 4 datapoints with year 2025 – likely projections, not measurements

---

## Key Data Sources

| Source | Code | Status | Notes |
|--------|------|--------|-------|
| World Bank WDI | WB | ✅ Active | 1.486 in catalog, 91 loaded |
| RestCountries | REST | ✅ Active | Base country data |
| WHO GHO | WHO | ⏳ Planned | ~2.300 indicators |
| UN Comtrade | COMTRADE | ⏳ Planned | Trade flows |
| UNDP HDR | UNDP | ⏳ Planned | HDI, GII, MPI |
| V-Dem | VDEM | ⏳ Planned | 500+ democracy indicators |
| World Values Survey | WVS | ⏳ Planned | Cultural values |
| CEPALSTAT | CEPAL | ⏳ Planned | Latin America specific |