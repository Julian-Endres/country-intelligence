# Country Intelligence Layer

A multi-dimensional database that aggregates country-level data from international sources into a unified system. Designed for exploration, analysis, and visualization.

Started in Cochabamba, Bolivia, during a sabbatical in 2026.

## Project Goal

Build a professional data pipeline that:
- Connects to multiple international data sources (World Bank, WHO, UNDP, V-Dem, etc.)
- Stores country information in a clean, scalable PostgreSQL database
- Enables visualization of economic, cultural, geographic, and political dimensions per country
- Serves as a portfolio piece demonstrating data engineering and analytical skills

## Architecture

The database consists of four core tables:

- **countries** – Stable country information (name, ISO codes, region, geography). Primary key: `iso_numeric` (ISO 3166-1 standard)
- **sources** – All data sources used in the project
- **indicator_metadata** – Description of each indicator (name, unit, category, source)
- **indicators** – Actual data values (one row per country, indicator, year)

## Tech Stack

- **PostgreSQL 18** – Database
- **Python 3.14** – Data pipeline scripts
- **psycopg2** – Python ↔ PostgreSQL connection
- **requests** – API calls
- **DBeaver** – Database GUI
- **WSL2 (Ubuntu)** – Development environment on Windows

## Project Structure
country-intelligence/
├── scripts/              # Python scripts for data loading
│   ├── load_countries.py
│   └── world_bank.py
├── sql/                  # SQL scripts
│   ├── 01_setup/         # Table creation
│   ├── 02_seed/          # Initial data
│   └── 03_queries/       # Exploration queries
├── venv/                 # Python virtual environment (not in git)
└── README.md
## Setup Instructions

1. Install PostgreSQL and create database `country_intelligence`
2. Run all scripts in `sql/01_setup/` in order
3. Run `sql/02_seed/01_insert_sources.sql`
4. Run `sql/02_seed/02_insert_indicator_metadata.sql`
5. Run `python3 scripts/load_countries.py` to load all countries
6. Run `sql/02_seed/03_update_regions.sql` to enrich region data

## Status

- ✅ Database architecture
- ✅ 249 countries loaded with base data
- ✅ Sources and indicator metadata defined
- 🔄 World Bank indicators (in progress)
- ⏳ Visualization layer (planned)
- ⏳ Web scraping integration (planned)

## Author

Julian Endres