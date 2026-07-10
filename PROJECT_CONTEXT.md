# Project Context — Country Intelligence Layer

**Last updated:** 2026-07-10

---

## Vision

A multi-dimensional database aggregating country-level data from 50+ international sources into a unified PostgreSQL system. Long-term goal: an interactive, map-centric platform that gives a comprehensive, intuitive view of any country — economy, geography, culture, institutions, environment, history, and lived experience.

The project is not a dashboard that shows numbers. It is a system that answers questions.

> "Where is child mortality high?" · "Which regions are the poorest?" · "Where does a country export its raw materials?" · "How has press freedom changed over the last decade?"

Structured around the **Societal Intelligence Framework (SIF v2)** — 10 core domains covering the full complexity of societies. Bolivia (where the project started, during a sabbatical) serves as a recurring analytical anchor throughout, benchmarked against its South American neighbors.

**Portfolio positioning:** End-to-end data pipeline thinking, scalable database architecture, international analytical perspective, and data storytelling. Target sector: NGO / Impact / International Organizations.

---

## Conceptual Framework: SIF v2 — 10 Core Domains

**v2 restructure (June 2026):** split out *Education, Science & Innovation* and *Infrastructure & Technology* as their own domains (previously folded into Economy), dissolved *Communication & Media* (press freedom → Politics, digital access → Infrastructure), merged *Culture & Identity* + *Social Fabric & Daily Life* into *Culture, Society & Beliefs*.

| # | Domain | Indicators | Documentation Status |
|---|--------|-----------|----------------------|
| 01 | Population & Demographics | ~84 | ✅ Fully documented (4/4 categories) |
| 02 | Health & Survival | ~121 | ⏳ Data loaded, documentation pending |
| 03 | Education, Science & Innovation | ~10 | ⏳ Phase 4 (thin, needs UNESCO UIS / OECD PISA / WIPO) |
| 04 | Economy, Wealth & Labor | ~145 | ✅ 5/7 categories documented + composite scores |
| 05 | Infrastructure & Technology | ~17 | ⏳ Phase 4 (thin, needs ITU / IRENA / ITF) |
| 06 | Environment, Climate & Resources | ~77 | ⏳ Data loaded, documentation pending |
| 07 | Politics, Governance & Law | ~124 | ✅ Fully documented (4/4 categories, incl. UCDP/ACLED conflict data) |
| 08 | Culture, Society & Beliefs | ~99 | ⏳ Data loaded, documentation pending |
| 09 | History & Collective Memory | ~10 | ⏳ Stub — strong niche sources (Maddison, COLDAT, COW), thin coverage |
| 10 | International Relations & Global Integration | ~38 | ⏳ Concept ready — unique sources (UNGA voting, ATOP, KOF), documentation not started |
| | **Total** | **~725** | **3/10 domains fully documented** |

Indicator counts approximate and drift slightly as metadata is refined; see `sql/02_seed/` for the authoritative mapping.

### Data Hierarchy (4 levels)

```
Domain        → Large conceptual category (e.g. Politics, Governance & Law)
  Category    → SIF sub-grouping (e.g. Security & Conflict)
    Dimension → Thematic cluster (e.g. Armed Conflict)
      Indicator → Quantifiable signal (e.g. UCDP:battle_deaths)
```

The `category` field in `indicator_metadata` represents the SIF hierarchy level — not the original source category. See `docs/SIF_DOMAIN_STRUCTURE.md` for the full category/dimension breakdown per domain.

### Documentation Methodology

Each fully documented domain follows a consistent pattern (established during the Politics domain build-out): source overview → Bolivia time-series trend (with SQL) → South America comparison ranking (with SQL) → critical assessment of what the data actually shows, including corrections to naive expectations → connections to other domains/categories. Full write-ups live in the project's Notion Encyclopedia (private, not linked from this repo).

---

## Architecture

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Core Tables (`public` schema)

| Table | Description |
|-------|-------------|
| `countries` | 249 countries, ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 50+ registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, domain, category, dimension |
| `indicators` | ~7M+ data values (country × indicator × year). Long format, SDMX-inspired |
| `indicator_catalog` | all available indicators with coverage metadata |

### Relational Schemas

| Schema | Tables | Content |
|--------|--------|---------|
| `trade` | `trade_products`, `trade_partners` | Comtrade HS-4 flows (5.6M+) + bilateral trade (997k+) |
| `politics` | `political_parties`, `marpor_elections`, `constitutional_events`, `coups`, `conflicts_state`, `conflicts_state_actors`, `conflicts_nonstate`, `conflicts_onesided`, `conflict_context` | Political history + UCDP armed conflict data + ACLED political violence |
| `international` | `diplomatic_relations` (DASID), `diplomatic_representation` (DDR), `colonial_history` (COLDAT) | IR relational data |
| `history` | `ethnic_groups` | EPR ethnic group power relations 1946–2023 |
| `culture` | `national_dishes`, `country_facts` | Curated cultural reference data |

### Indicator Code Convention

```
SOURCE:ORIGINAL_CODE
Examples: WB:NY.GDP.PCAP.CD · VDEM:v2x_polyarchy · UNDP:hdi · UNVOTE:agree_usa · UCDP:battle_deaths
```

**Never invent codes** — always preserve original source codes.

### Design Principles

- `time_period` as TEXT: supports `"2023"`, `"2023-01"`, `"static"`
- `source_id` in UNIQUE key — allows parallel storage from multiple sources
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `ON CONFLICT DO NOTHING` / `DO UPDATE` everywhere — all scripts idempotent and re-runnable
- No hardcoded credentials — all via `.env` (audited July 2026, confirmed clean across all loaders)
- Every new table/indicator gets an `indicator_metadata` (or `relational_table_metadata`) entry immediately, not retroactively

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/          # Domain-organized loaders (base, wb, economy, health,
│   │                      # demographics, environment, governance, culture,
│   │                      # history, international, social)
│   ├── catalog/           # Indicator catalog + search tools
│   ├── analysis/          # Export + exploration queries
│   ├── archive/           # wb_legacy/ — pre-restructure WB bulk loaders, superseded
│   │                      # by domain-organized loaders but kept for reproducibility
│   └── experimental/      # WIP scripts, not production: species_gbif_wip.py,
│                          # vdem_partysystem_wip.py
├── sql/
│   ├── 01_setup/          # Table creation
│   ├── 02_seed/           # Initial data + SIF mapping
│   ├── 03_queries/        # Exploration + data quality
│   └── 04_categories/     # Category assignment scripts (one per domain)
├── api/routes/            # FastAPI routes
├── docs/                  # PROJECT_CONTEXT, SOURCES_ROADMAP,
│                          # SOURCES_ENCYCLOPEDIA, SIF_DOMAIN_STRUCTURE
├── data/raw/               # Raw data files — not in git (~6.6 GB, backup pending)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Tech Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (TCP on localhost:5432)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas, python-dotenv, fastapi, pygbif, openpyxl, pycountry, country_converter
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code

### Setup Notes

- WSL2 + PostgreSQL: `listen_addresses = '*'` in `postgresql.conf` + `pg_hba.conf` modification
- PostgreSQL needs manual start: `sudo service postgresql start`
- Python venv: `venv/` in project root
- **Reproducibility note:** a full from-scratch DB rebuild currently needs both the domain-organized loaders (`scripts/pipeline/`) and, for some early World Bank indicators, the archived legacy loaders in `scripts/archive/wb_legacy/` — this should be consolidated so the domain loaders are self-sufficient.

---

## API Layer (FastAPI)

### Route Structure

```
GET /api/country/{iso}                          → Country Overview + Top KPIs
GET /api/country/{iso}/demography               → Domain Overview (Category Cards)
GET /api/country/{iso}/demography/{category}    → Category Detail + time series
GET /api/country/{iso}/demography/pyramid       → Age pyramid (34 age groups)
GET /api/country/{iso}/timeseries/{indicator}   → Generic time series
GET /api/country/{iso}/governance               → Governance (flat, not blueprint yet)
GET /api/country/{iso}/economy                  → Economy (flat, not blueprint yet)
```

### Three-Level Navigation

```
Level 1 — Country Overview:   Map + Top KPIs
Level 2 — Domain Overview:    Category Cards with key indicator + signal
Level 3 — Category Detail:    All indicators + summary + time series
```

**Status:** Demography domain fully built on the blueprint pattern. Health, Economy, Governance routes still flat — bringing them to blueprint level is a prerequisite for the visualization layer.

---

## Open Items

### Immediate — visualization layer (current focus, Sprint 2)

1. Streamlit dashboard — 3-domain navigation (Demography, Economy, Politics) reusing the existing blueprint pattern
2. Bolivia country profile as centerpiece
3. Choropleth world map for 5–10 headline indicators
4. Bring Health/Economy/Governance API routes to blueprint level

### Data pipeline hygiene

5. Consolidate `scripts/archive/wb_legacy/` into the domain loaders so a from-scratch rebuild doesn't need both (see Setup Notes above)
6. Resolve two WIP scripts in `scripts/experimental/`: GBIF species-per-country loader, V-Party/WhoGov party-system loader (feeds the still-open "Party System & Election Results" item in Politics)
7. Auto-descriptions for ~300 indicators without `description` (VDEM, GITOC, UNVOTE, COW, ATOP, FAO_FOOD, GBIF, WVS — via Claude API, not blocking)
8. ACLED granular event context (Notes column), analogous to the existing UCDP `conflict_context` table
9. RSF Press Freedom — currently loaded via OWID (ends 2021); load directly from rsf.org for 2022–2025

### Backup (unresolved risk)

10. `data/raw/` is ~6.6 GB, exists only locally, no backup strategy yet. `pg_dump` of the database + upload of `data/raw/` to cloud storage, then a weekly routine.

### Medium term — new sources (frozen until v1.0, see below)

See `SOURCES_ROADMAP.md` for the full prioritized list. Not pulled until they unblock a specific score/chapter.

---

## Definition of Done (v1.0)

The project counts as complete for portfolio purposes when:

- [x] Public repo with polished README
- [ ] Working dashboard with 3 domains + world map
- [x] 1 domain (Economy) documented in depth with composite scores — plus Population and Politics also complete
- [ ] 1 published data story (Bolivia — "Anatomy of an Artificial Stability": fixed exchange rate, shrinking reserves, informality, gas dependency)
- [ ] Reproducible setup (backup + setup docs consolidated)

Everything beyond this (remaining domains at Encyclopedia depth, subnational data, full API coverage) is v1.1+ — not a blocker for the initial portfolio release.
