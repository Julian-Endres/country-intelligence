# Country Intelligence Layer

A multi-dimensional database aggregating country-level data from **50 international sources** into a unified PostgreSQL system. Built to answer questions about countries — not just show numbers.

> "Where is child mortality high?" · "Where does a country export its raw materials?" · "How has press freedom changed over the last decade?"

Started in Cochabamba, Bolivia, during a sabbatical in 2026. Combines technical pipeline engineering with genuine curiosity about how societies work.

---

## Conceptual Framework

The project is structured around the **Societal Intelligence Framework (SIF)** — 10 core domains that aim to cover the full complexity of a society, from measurable structure to lived experience.

| # | Domain | # | Domain |
|---|--------|---|--------|
| 1 | Population & Demographics | 6 | Social Fabric & Daily Life |
| 2 | Geography & Environment | 7 | Communication & Media |
| 3 | Economy & Infrastructure | 8 | Health, Body & Behavior |
| 4 | Politics & Governance | 9 | History & Collective Memory |
| 5 | Culture & Identity | 10 | International Relations & Global Integration |

Every indicator is mapped through a **4-level hierarchy**: `Domain → Category → Dimension → Indicator`.

---

## Architecture

### Core Tables (`public` schema)

| Table | Description |
|-------|-------------|
| `countries` | 249 countries with ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 50 registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, domain, category, dimension |
| `indicators` | ~9M+ data values (country × indicator × year). Long format, SDMX-inspired |
| `indicator_catalog` | all available indicators with coverage metadata |

### Relational Schemas

| Schema | Content |
|--------|---------|
| `trade` | Comtrade HS-4 product flows (5.6M+) + bilateral trade partners (997k+) |
| `politics` | Manifesto Project elections, constitutional events, coups |
| `international` | Diplomatic relations, representation, colonial history |
| `history` | EPR ethnic group power relations 1946–2023 |
| `culture` | Curated national dishes + country facts |

### Indicator Code Convention

```
SOURCE:ORIGINAL_CODE
Examples: WB:NY.GDP.PCAP.CD · VDEM:v2x_polyarchy · UNDP:hdi
```

Original source codes are always preserved — never invented.

---

## Data Sources

50 integrated sources spanning all 10 domains, from global aggregators to specialized datasets:

**Multi-domain & economy:** World Bank (WDI + WGI), UN Comtrade, WID.world, Penn World Table, Maddison Project, ILO, UNDP, OWID

**Governance & politics:** V-Dem, Freedom House, Polity5, Transparency International, SIPRI, Fragile States Index, GI-TOC, UNODC, MARPOR Manifesto Project

**Health & environment:** WHO GHO, FAO (Food + Land), GBIF, Global Hunger Index, Open-Meteo ERA5, Ember, Energy Institute, EIA

**Culture & society:** World Values Survey, Hofstede, World Happiness Report, Pew Research, UNESCO (WHC + ICH), Nobel Prize, IMDb, Glottolog, CAF World Giving Index, Edelman Trust Barometer

**International relations:** KOF Globalisation Index, ATOP Alliances, UN General Assembly Voting, COW IGO Membership, Henley Passport Index

**History & demographics:** Correlates of War, EPR Ethnic Power Relations, UNHCR Refugee Data, WEF Global Gender Gap

**Total: ~9 million data points**

See [`docs/SOURCES_ROADMAP.md`](docs/SOURCES_ROADMAP.md) for the full list, integration status, and planned sources, and [`docs/SOURCES_ENCYCLOPEDIA.md`](docs/SOURCES_ENCYCLOPEDIA.md) as a living reference of available data sources worldwide.

---

## Tech Stack

- **PostgreSQL 18** — Database (WSL2 Ubuntu)
- **Python 3.14** — Data pipeline
- **FastAPI** — REST API layer
- **psycopg2 · pandas · requests · pygbif** — Data handling
- **DBeaver** — Database GUI
- **VS Code + WSL2** — Development environment

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/          # Domain-organized loaders (base, wb, economy, health,
│   │                      # demographics, environment, governance, culture,
│   │                      # history, international, social)
│   ├── catalog/           # Indicator catalog + search tools
│   └── analysis/          # Export + analysis queries
├── sql/
│   ├── 01_setup/          # Table creation
│   ├── 02_seed/           # Initial data + SIF mapping
│   ├── 03_queries/        # Exploration + data quality
│   └── 04_categories/     # Category assignment scripts
├── api/routes/            # FastAPI routes
├── docs/                  # PROJECT_CONTEXT, SOURCES_ROADMAP,
│                          # SOURCES_ENCYCLOPEDIA, SIF_DOMAIN_STRUCTURE
├── data/raw/              # Raw data files — not in git
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

- ✅ Database architecture (core tables + 5 relational schemas)
- ✅ 249 countries loaded
- ✅ 50 data sources integrated (~9M+ data points)
- ✅ 4-level SIF hierarchy assigned across all 10 domains
- ✅ FastAPI layer (Demography domain complete, blueprint pattern)
- 🔄 Comtrade 2020–2025 batches completing
- ⏳ Health, Economy, Governance API routes to blueprint level
- ⏳ Visualization layer — the next major milestone

---

## Roadmap

The next phase focuses on **storytelling and visualization** — turning the data foundation into maps and narratives that answer real questions. See [`docs/SOURCES_ROADMAP.md`](docs/SOURCES_ROADMAP.md) for details.
