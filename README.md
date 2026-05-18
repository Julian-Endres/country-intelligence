# Country Intelligence Layer

A multi-dimensional database that aggregates country-level data from international sources into a unified system. Designed for exploration, analysis, and visualization.

Started in Cochabamba, Bolivia, during a sabbatical in 2026.

## Project Goal

Build a professional data pipeline that answers questions like:
- "Where is child mortality high?"
- "Which regions of Bolivia are the poorest?"
- "Where does Bolivia export its raw materials?"
- "How have these things developed over the last years?"

Not a dashboard that shows numbers. A system that answers questions.

## Conceptual Framework

The project is structured around the **Societal Intelligence Framework (SIF)** – 10 core domains that cover the full complexity of societies:

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

Each indicator in the database is mapped to a domain and dimension from this framework.

## Architecture

Five core tables:

- **countries** – Stable country information (name, ISO codes, region, geography). 249 countries. Primary key: `iso_numeric` (ISO 3166-1 standard)
- **sources** – All data sources used in the project
- **indicator_metadata** – Description of each indicator (name, unit, category, SIF domain/dimension)
- **indicators** – Actual data values (one row per country, indicator, year). Long format, SDMX-inspired
- **indicator_catalog** – All available indicators from all sources with coverage data (1.486 WB indicators)

## Tech Stack

- **PostgreSQL 18** – Database (WSL2 Ubuntu)
- **Python 3.14** – Data pipeline scripts
- **psycopg2** – Python ↔ PostgreSQL
- **requests / pandas** – API calls and data handling
- **Streamlit** – Indicator Explorer web app
- **Plotly** – Visualizations
- **DBeaver** – Database GUI

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/        # Data loading scripts
│   ├── catalog/         # Indicator catalog tools + Streamlit app
│   └── analysis/        # Visualization scripts
├── sql/
│   ├── 01_setup/        # Table creation
│   ├── 02_seed/         # Initial data + SIF mapping
│   └── 03_queries/      # Exploration + data quality checks
├── docs/
│   ├── SOURCES_ROADMAP.md
│   └── SOURCES_ENCYCLOPEDIA.md
└── PROJECT_CONTEXT.md
```

## Current Data

| Domain | Indicators | Period | Coverage |
|--------|-----------|--------|----------|
| Population & Demographics | 91 | 2000–2024 | 215 countries |
| Health, Body & Behavior | 12 | 2000–2024 | 183–215 countries |
| Economy & Infrastructure | 3 | 2000–2024 | 212–215 countries |

**~500.000+ data points** across 215 countries, 2000–2024.

## Setup

1. Install PostgreSQL and create database `country_intelligence`
2. Run scripts in `sql/01_setup/` in order
3. Run `sql/02_seed/` scripts in order
4. Copy `.env.example` to `.env` and fill in credentials
5. Run `python3 scripts/pipeline/load_countries.py`
6. Run `python3 scripts/pipeline/load_demographics.py`

## Status

- ✅ Database architecture
- ✅ 249 countries loaded
- ✅ 1.486 WB indicators in catalog
- ✅ 91 demographic indicators loaded (2000–2024)
- ✅ SIF domain/dimension mapping
- ✅ Streamlit indicator explorer
- ⏳ Economy & Infrastructure (next)
- ⏳ WHO health data
- ⏳ UN Comtrade (trade flows)
- ⏳ Visualization layer

## Author

Julian Endres
