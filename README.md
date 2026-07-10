# Country Intelligence Layer

A multi-dimensional database aggregating country-level data from **50+ international sources** into a unified PostgreSQL system. Built to answer questions about countries — not just show numbers.

> "Where is child mortality high?" · "Where does a country export its raw materials?" · "How has press freedom changed over the last decade?"

Started in Cochabamba, Bolivia, during a sabbatical in 2026. Combines technical pipeline engineering with genuine curiosity about how societies work. Bolivia serves as a recurring analytical anchor throughout the project, benchmarked against its South American neighbors.

Each documented domain follows a consistent methodology: source overview, Bolivia time-series trend, South America comparison, and a critical assessment of what the data actually shows (including where it corrects naive expectations).

---

## Conceptual Framework

The project is structured around the **Societal Intelligence Framework (SIF v2)** — 10 core domains that aim to cover the full complexity of a society, from measurable structure to lived experience. Every indicator is mapped through a **4-level hierarchy**: `Domain → Category → Dimension → Indicator`.

| # | Domain | Data | Encyclopedia Doc |
|---|--------|------|------------------|
| 01 | Population & Demographics | 100% | ✅ 100% |
| 02 | Health & Survival | 100% | ⏳ 0% |
| 03 | Education, Science & Innovation | 100% (thin — 10 indicators) | ⏳ 0% |
| 04 | Economy, Wealth & Labor | 100% | ✅ 100% (5/7 categories + composite scores) |
| 05 | Infrastructure & Technology | 100% (thin — 17 indicators) | ⏳ 0% |
| 06 | Environment, Climate & Resources | 100% | ⏳ 0% |
| 07 | Politics, Governance & Law | 100% | ✅ 100% (4/4 categories) |
| 08 | Culture, Society & Beliefs | 100% | ⏳ 0% |
| 09 | History & Collective Memory | 100% (thin coverage) | ⏳ 0% |
| 10 | International Relations & Global Integration | 100% | ⏳ 0% (concept ready — UNGA voting, ATOP, KOF) |

*"Data" = raw indicators loaded into PostgreSQL. "Encyclopedia Doc" = full methodology write-up (source overview, Bolivia trend, South America comparison, critical assessment) in the project's Notion encyclopedia. A domain can be 100% loaded and still 0% documented.*

**v2 restructure (June 2026):** split out *Education, Science & Innovation* and *Infrastructure & Technology* as their own domains, dissolved *Communication & Media* (press freedom → Politics, digital access → Infrastructure), merged *Culture & Identity* + *Social Fabric* into *Culture, Society & Beliefs*.

---

## Data Sources

50+ integrated sources spanning all 10 domains, from global aggregators to specialized niche datasets. The combination of standard aggregators (World Bank, WHO, UNDP) **and** specialist sources most portfolios don't touch (ATOP military alliances, UN General Assembly voting records, COLDAT colonial history, MARPOR party manifestos) is a deliberate differentiator.

**Multi-domain & economy:** World Bank (WDI + WGI), UN Comtrade, WID.world, Penn World Table, Maddison Project Database, ILO, UNDP, OWID

**Governance & politics:** V-Dem, Freedom House, Polity5, Transparency International, SIPRI, Fragile States Index, GI-TOC, UNODC, UCDP, ACLED, MARPOR Manifesto Project, Comparative Constitutions Project, Cline Center (coups)

**Health & environment:** WHO GHO, FAO (Food + Land), GBIF, Global Hunger Index, Open-Meteo ERA5, Ember, Energy Institute, EIA

**Culture & society:** World Values Survey, Hofstede, World Happiness Report, Pew Research, UNESCO (WHC + ICH), Nobel Prize, IMDb, Glottolog, CAF World Giving Index, Edelman Trust Barometer

**International relations:** KOF Globalisation Index, ATOP Alliances, UN General Assembly Voting, COW IGO Membership, Henley Passport Index, DASID/DDR diplomatic relations, COLDAT colonial history

**History & demographics:** Correlates of War, EPR Ethnic Power Relations, UNHCR Refugee Data, WEF Global Gender Gap

**Scale:** ~720 indicators across the 10 domains (~4.2M data points) plus 17 relational tables (~8.5M rows: bilateral trade — Comtrade 5.6M+ product-level + 1.2M+ partner-level — plus armed conflict, diplomatic relations, elections, and more). **~12.7M data points total.** Counted separately by type because they're structurally different (long-format indicators vs. relational event/relationship data) — see `docs/SOURCES_ROADMAP.md` for the full source list and integration status.

---

## Architecture

### Core Tables (`public` schema)

| Table | Description |
|-------|-------------|
| `countries` | 249 countries with ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 50+ registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, domain, category, dimension |
| `indicators` | ~4.2M data values (country × indicator × year). Long format, SDMX-inspired |
| `indicator_catalog` | all available indicators with coverage metadata |

### Relational Schemas

| Schema | Content |
|--------|---------|
| `trade` | Comtrade HS-4 product flows (5.6M+) + bilateral trade partners (1.2M+) |
| `politics` | Manifesto Project elections, constitutional events, coups, armed conflicts (UCDP), political violence (ACLED) |
| `international` | Diplomatic relations (DASID), diplomatic representation (DDR), colonial history (COLDAT) |
| `history` | EPR ethnic group power relations 1946–2023 |
| `culture` | Curated national dishes + country facts |

### Indicator Code Convention

```
SOURCE:ORIGINAL_CODE
Examples: WB:NY.GDP.PCAP.CD · VDEM:v2x_polyarchy · UNDP:hdi · UNVOTE:agree_usa
```

Original source codes are always preserved — never invented.

---

## Tech Stack

- **PostgreSQL 18** — Database (WSL2 Ubuntu)
- **Python 3.14** — Data pipeline
- **FastAPI** — REST API layer
- **Streamlit** — Indicator explorer (early stage)
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
│   └── 04_categories/     # Category assignment scripts (one per domain)
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
psql -d country_intelligence -f sql/01_setup/01_drop_tables.sql
psql -d country_intelligence -f sql/01_setup/02_create_sources.sql
psql -d country_intelligence -f sql/01_setup/03_create_countries.sql
psql -d country_intelligence -f sql/01_setup/04_create_indicator_metadata.sql
psql -d country_intelligence -f sql/01_setup/05_create_indicators.sql

# 3. Configure
cp .env.example .env  # fill in DB credentials + API keys

# 4. Load base data
python3 scripts/pipeline/base/load_countries.py
```

---

## Status

- ✅ Database architecture (core tables + 5 relational schemas)
- ✅ 249 countries loaded
- ✅ 50+ data sources integrated, ~720 indicators across all 10 domains, ~12.7M data points total
- ✅ 4-level SIF hierarchy (v2) assigned across all 10 domains
- ✅ Three domains fully documented with methodology: **Population & Demographics**, **Economy, Wealth & Labor** (5/7 categories + composite scores), **Politics, Governance & Law** (all 4 categories, incl. armed conflict, organized crime, coups)
- ✅ FastAPI layer (Demography domain complete, blueprint pattern)
- ⏳ Health, Economy, Governance API routes to blueprint level
- ⏳ **Visualization layer — the next major milestone** (Streamlit dashboard, Bolivia country profile, choropleth world map)

---

## Roadmap

The current phase focuses on **storytelling and visualization** — turning the data foundation into an interactive dashboard and narratives that answer real questions, anchored on Bolivia as a case study ("Anatomy of an Artificial Stability" — fixed exchange rate, shrinking reserves, informality, gas dependency). See `docs/SOURCES_ROADMAP.md` and `docs/PROJECT_CONTEXT.md` for details.