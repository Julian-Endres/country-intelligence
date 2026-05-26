# Country Intelligence Layer

A multi-dimensional database aggregating country-level data from 25+ international sources into a unified PostgreSQL system. Built to answer questions about countries – not just show numbers.

> "Where is child mortality high?" · "Where does Bolivia export its raw materials?" · "How has press freedom changed over the last decade?"

Started in Cochabamba, Bolivia, during a sabbatical in 2026.

---

## Conceptual Framework

The project is structured around the **Societal Intelligence Framework (SIF)** – 10 core domains that cover the full complexity of societies:

| # | Domain |
|---|--------|
| 1 | Population & Demographics |
| 2 | Geography & Environment |
| 3 | Economy & Infrastructure |
| 4 | Politics & Governance |
| 5 | Culture & Identity |
| 6 | Social Fabric & Daily Life |
| 7 | Communication & Media |
| 8 | Health, Body & Behavior |
| 9 | History & Collective Memory |
| 10 | International Relations & Global Integration |

Each indicator in the database is mapped to a domain from this framework.

---

## Architecture

### Core Tables

| Table | Description |
|-------|-------------|
| `countries` | 249 countries with ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 35+ registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, category, SIF domain |
| `indicators` | 5.5M+ data values (country × indicator × year). Long format, SDMX-inspired |
| `trade_products` | 2.9M+ Comtrade HS-4 product trade flows |
| `trade_partners` | Bilateral trade flows by partner country |

### Indicator Code Convention

```
SOURCE:ORIGINAL_CODE
Examples: WB:NY.GDP.PCAP.CD · VDEM:v2x_polyarchy · UNDP:hdi · WHO:MDG_0000000001
```

Never invent codes – always preserve original source codes.

---

## Data Sources (25+)

| Source | Code | Domain | Data Points | Period |
|--------|------|--------|-------------|--------|
| World Bank WDI | WB | Multi | ~750k | 2000–2024 |
| V-Dem Institute | VDEM | Governance | 1.03M | 1900–2025 |
| Freedom House | FH | Governance | 15.9k | 1972–2024 |
| Transparency International CPI | CPI | Governance | 2.3k | 2012–2024 |
| RSF Press Freedom Index | RSF | Media | 1.6k | 2013–2025 |
| WHO GHO | WHO | Health | 128k | 1932–2024 |
| UN Comtrade | — | Economy | 2.93M+ | 2010–2024 |
| OWID CO2 & Energy | OWID_CO2 | Environment | 218k | 1750–2024 |
| UNDP HDR + MPI | UNDP | Development | ~38k | 1990–2023 |
| FAO Land Use | FAO_LAND | Environment | ~200k | 1961–2025 |
| FAO Food Balance Sheets | FAO_FOOD | Health | 7.2k | 1961–2022 |
| ND-GAIN Country Index | NDGAIN | Environment | ~43k | 1995–2023 |
| GBIF Biodiversity | GBIF | Environment | 1.9k | 2024 |
| GBIF IUCN Red List | GBIF | Environment | 991 | 2024 |
| Open-Meteo ERA5 | OPENMETEO | Environment | ~17k | 2000–2023 |
| Maddison Project 2023 | MADDISON | History | 38.5k | 1–2022 |
| Correlates of War | COW | History | 585 | 1816–2003 |
| World Values Survey | WVS | Culture | 5.6k | 1981–2022 |
| Hofstede 6 Dimensions | HOFSTEDE | Culture | 293 | static |
| World Happiness Report | WHR | Social | 7.9k | 2011–2025 |
| UNESCO World Heritage | UNESCO_WHC | Culture | 461 | 2024 |
| Nobel Prize API | NOBEL | Culture | ~600 | 1901–2024 |
| IMDb Titles | IMDB | Media | 30.8k | 1900–2025 |
| Olympics Paris 2024 | OLYMPICS | Culture | — | 2024 |

**Total: ~5.5 million data points**

---

## Tech Stack

- **PostgreSQL 18** – Database (WSL2 Ubuntu)
- **Python 3.14** – Data pipeline
- **FastAPI** – REST API layer
- **psycopg2 · pandas · requests** – Data handling
- **DBeaver** – Database GUI
- **VS Code + WSL2** – Development environment

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── base/          # load_countries.py, world_bank_historical.py
│   │   ├── wb/            # World Bank domain scripts
│   │   ├── economy/       # Comtrade, Maddison, OWID CO2, CPI
│   │   ├── health/        # WHO, FAO Food
│   │   ├── demographics/  # UNDP, WVS
│   │   ├── environment/   # FAO Land, ND-GAIN, GBIF, Open-Meteo
│   │   ├── governance/    # Freedom House, V-Dem, RSF
│   │   ├── culture/       # Hofstede, WHR, Nobel, Olympics, UNESCO, IMDb
│   │   └── history/       # COW Wars
│   ├── catalog/           # Indicator catalog + search tools
│   └── analysis/
├── sql/
│   ├── 01_setup/          # Table creation
│   ├── 02_seed/           # Initial data + SIF mapping
│   └── 03_queries/        # Exploration + data quality
├── api/                   # FastAPI routes
├── docs/
│   ├── SOURCES_ROADMAP.md
│   └── SOURCES_ENCYCLOPEDIA.md
├── data/raw/              # Raw data files – not in git
├── .env.example
└── README.md
```

---

## Setup

```bash
# 1. Clone & install
git clone https://github.com/Julian-Endres/country-intelligence
cd country-intelligence
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Database
createdb country_intelligence
psql -d country_intelligence -f sql/01_setup/...

# 3. Configure
cp .env.example .env  # fill in DB credentials + API keys

# 4. Load base data
python3 scripts/pipeline/base/load_countries.py
```

---

## Status

- ✅ Database architecture (6 tables)
- ✅ 249 countries loaded
- ✅ 25+ data sources integrated (~5.5M data points)
- ✅ FastAPI layer (Demography domain complete)
- ✅ Pipeline scripts organized by domain
- 🔄 Comtrade P2 bilateral trade (in progress)
- ⏳ Health, Economy, Environment API routes
- ⏳ Visualization layer

---

## Author

Julian Endres
