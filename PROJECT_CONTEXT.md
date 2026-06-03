# Project Context — Country Intelligence Layer

**Last updated:** 2026-06-03

---

## Vision

A multi-dimensional database aggregating country-level data from 50 international sources into a unified PostgreSQL system. Long-term goal: an interactive, map-centric platform that gives a comprehensive, intuitive view of any country — economy, geography, culture, institutions, environment, history, and lived experience.

The project is not a dashboard that shows numbers. It is a system that answers questions.

> "Where is child mortality high?" · "Which regions are the poorest?" · "Where does a country export its raw materials?" · "How has press freedom changed over the last decade?"

Structured around the **Societal Intelligence Framework (SIF)** — 10 core domains covering the full complexity of societies.

**Portfolio positioning:** End-to-end data pipeline thinking, scalable database architecture, international analytical perspective, and data storytelling. Target sector: NGO / Impact / International Organizations.

---

## Conceptual Framework: SIF — 10 Core Domains

| # | Domain | Status |
|---|--------|--------|
| 1 | Population & Demographics | ✅ Strong |
| 2 | Geography & Environment | ✅ Strong |
| 3 | Economy & Infrastructure | ✅ Strong |
| 4 | Politics & Governance | ✅ Strong |
| 5 | Culture & Identity | ✅ Good |
| 6 | Social Fabric & Daily Life | 🟡 Thin |
| 7 | Communication & Media | 🟡 Thin |
| 8 | Health, Body & Behavior | ✅ Good |
| 9 | History & Collective Memory | 🟡 Growing |
| 10 | International Relations & Global Integration | ✅ Good (new) |

### Four Analytical Pillars

1. **Structural Foundation** — measurable physical and institutional reality (demographics, economics, infrastructure, governance, environment)
2. **Perception Layer** — collective subjective experience (trust, fear, satisfaction)
3. **Cultural & Identity Layer** — values, norms, identity systems
4. **Narrative Layer** — AI-assisted interpretive synthesis

### Data Hierarchy (4 levels)

```
Domain        → Large conceptual category (e.g. Culture & Identity)
  Category    → SIF sub-grouping (e.g. Identity & Values)
    Dimension → Thematic cluster (e.g. Cultural Dimensions)
      Indicator → Quantifiable signal (e.g. HOFSTEDE:idv)
```

The `category` field in `indicator_metadata` represents the SIF hierarchy level — not the original source category.

---

## Architecture

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Core Tables (public schema)

| Table | Description |
|-------|-------------|
| `countries` | 249 countries, ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 50 registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, domain, category, dimension |
| `indicators` | ~9M+ data values. Long format, SDMX-inspired |
| `indicator_catalog` | all available indicators with coverage metadata |

### Relational Schemas

| Schema | Tables | Content |
|--------|--------|---------|
| `trade` | `trade_products`, `trade_partners` | Comtrade HS-4 flows + bilateral trade |
| `politics` | `political_parties`, `marpor_elections`, `constitutional_events`, `coups` | Political history |
| `international` | `diplomatic_relations`, `diplomatic_representation`, `colonial_history` | IR relational data |
| `history` | `ethnic_groups` | EPR ethnic group data 1946–2023 |
| `culture` | `national_dishes`, `country_facts` | Curated cultural reference data |

### Indicator Code Convention

```
SOURCE:ORIGINAL_CODE
Examples: WB:NY.GDP.PCAP.CD · VDEM:v2x_polyarchy · UNDP:hdi · WHO:UHC_INDEX_REPORTED
```

**Never invent codes** — always preserve original source codes.

### Design Principles

- `time_period` as TEXT: supports `"2023"`, `"2023-01"`, `"static"`
- `source_id` in UNIQUE key — allows parallel storage from multiple sources
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `ON CONFLICT DO NOTHING` / `DO UPDATE` everywhere — all scripts idempotent and re-runnable
- No hardcoded credentials — all via `.env`

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
- Python venv: `venv/` in project root

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

### get_indicator_summary() Fields

`value · z_score · trend_long · trend_short · trend_label · global_rank · regional_rank · latest_year · global_avg · n_countries`

### Indicator Types System

```python
"neutral":  increasing / stable / decreasing      # Population, Urbanization
"flow":     net_inflow / balanced / net_outflow   # Net migration
"positive": improving / stable / declining        # GDP, Life expectancy
"negative": improving / stable / declining        # Child mortality (inverted)
```

**Decision:** Blueprint pattern (category → dimension → indicator) built on Demography first, then rolled out to all domains. Health is next.

---

## Current Data Status

| Source | Code | Data Points | Countries | Period | Status |
|--------|------|-------------|-----------|--------|--------|
| World Bank WDI + WGI | WB | ~1.09M | 215 | 1963–2025 | ✅ |
| V-Dem | VDEM | 1.03M | 175 | 1900–2025 | ✅ |
| Freedom House | FH | 15.9k | 193 | 1972–2024 | ✅ |
| Transparency International CPI | TI | 2.3k | 180 | 2012–2024 | ✅ |
| WHO GHO | WHO | ~105k | 215–227 | 1932–2024 | ✅ |
| ILO | ILO | 78.7k | 229 | 2000–2027 | ✅ |
| UN Comtrade P1 (Products) | — | 5.63M+ | 192 | 2000–2025 | ✅ |
| UN Comtrade P2 (Partners) | — | 997k+ | 195 | 2000–2025 | ✅ |
| OWID CO2 | OWID_CO2 | 218k | ~215 | 1750–2024 | ✅ |
| Ember Electricity | Ember | 30.2k | 213 | 1965–2025 | ✅ |
| Energy Institute | EI | 53.3k | 215 | 1900–2024 | ✅ |
| EIA Energy | EIA | 10.3k | 216 | 1965–2024 | ✅ |
| UNDP HDR + MPI | UNDP | ~38k | 195 | 1990–2024 | ✅ |
| FAO Land Use | FAO_LAND | 134k | 236 | 1961–2025 | ✅ |
| FAO Food Balance | FAO_FOOD | 7.2k | 178 | 2010–2023 | ✅ |
| FAO Food Groups | FAO_FOOD_GRP | 61.7k | 178 | 2010–2023 | ✅ |
| GBIF Biodiversity + IUCN | GBIF | 42.3k | 249 | 2000–2024 | ✅ |
| Open-Meteo ERA5 | OPENMETEO | 2.7k | 48 | 2000–2023 | ✅ |
| Maddison Project 2023 | MADDISON | 38.5k | 166 | 1–2022 | ✅ |
| Correlates of War | COW | 585 | 82 | 1823–2003 | ✅ |
| EPR Ethnic Power Relations | EPR | 32.5k | 171 | 1946–2023 | ✅ |
| World Values Survey | WVS | 5.6k | 107 | 1981–2023 | ✅ |
| Hofstede 6 Dimensions | HOFSTEDE | 293 | 60 | static | ✅ |
| World Happiness Report | WHR | 8.1k | 163 | 2011–2025 | ✅ |
| Pew Research (Religion) | PEW_REL | 3.2k | 199 | 2010–2020 | ✅ |
| CAF World Giving Index | CAF_WGI | 7.0k | 161 | 2010–2024 | ✅ |
| Edelman Trust Barometer | EDELMAN | 12.3k | 28 | 2012–2025 | ✅ |
| WID.world (Inequality) | WID | ~275k | 215 | 1800–2024 | ✅ |
| Penn World Table 11.0 | PWT | ~211k | 185 | 1950–2023 | ✅ |
| SIPRI Military | SIPRI | 8.5k | 166 | 1949–2025 | ✅ |
| Polity5 | POLITY5 | 102k | 168 | 1776–2020 | ✅ |
| Global Hunger Index | GHI | 6.5k | 131 | 2000–2025 | ✅ |
| Fragile States Index | FSI | 2.2k | 173 | 2022 | ✅ |
| RSF Press Freedom | RSF | 1.6k | 177 | 2013–2021 | ✅ |
| UNESCO WHC + ICH | UNESCO | 2.2k | 170 | 2008–2025 | ✅ |
| Nobel Prize | NOBEL | 1.4k | 82 | 1901–2025 | ✅ |
| IMDb | IMDB | 30.8k | 229 | 1900–2025 | ✅ |
| GI-TOC Crime Index | GITOC | 8.1k | 185 | 2021–2025 | ✅ |
| UNODC Homicide | UNODC | 10.8k | 228 | 1990–2026 | ✅ |
| KOF Globalisation Index | KOF | 86.3k | 197 | 1970–2023 | ✅ |
| ATOP Military Alliances | ATOP | 21.1k | 64 | 1815–2018 | ✅ |
| UN General Assembly Voting | UNVOTE | 151k | 193 | 1946–2025 | ✅ |
| COW IGO Membership | IGO | 12.4k | 63 | 1838–2014 | ✅ |
| Henley Passport Index | HENLEY | 788 | 197 | static | ✅ |
| Glottolog 5.3 | GLOTTOLOG | 732 | 244 | static | ✅ |
| WEF Global Gender Gap | WEF_GGGI | ~795 | 159 | 2006–2024 | ✅ |
| MARPOR Manifesto Project | MARPOR | relational | — | — | ✅ |
| UNHCR Refugee Data | UNHCR | 15.2k | 209 | 2000–2024 | ✅ |
| samayo/country-json | SAMAYO | ~1k | 235 | static | ✅ |
| **TOTAL** | | **~9M+** | | | |

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── base/          # load_countries.py, world_bank_historical.py
│   │   ├── wb/            # World Bank domain scripts
│   │   ├── economy/       # load_comtrade.py, load_maddison.py, load_owid_co2.py
│   │   │                  # load_wid.py, load_pwt.py, load_ilostat.py, load_cpi.py
│   │   ├── health/        # load_who.py, load_fao_food.py, load_who_quickwins.py, load_ghi.py
│   │   ├── demographics/  # load_undp.py, load_wvs.py, load_unhcr.py
│   │   ├── environment/   # load_fao_landuse.py, load_gbif.py, load_gbif_iucn.py
│   │   │                  # load_openmeteo.py, load_owid_energy.py, load_ndgain.py
│   │   ├── governance/    # load_freedom_house.py, load_vdem.py, load_rsf.py
│   │   │                  # load_polity5.py, load_sipri.py, load_fsi_gitoc.py, load_marpor.py
│   │   ├── culture/       # load_hofstede.py, load_whr.py, load_nobel.py, load_olympics.py
│   │   │                  # load_unesco_whc.py, load_imdb.py, load_glottolog.py, load_pew.py
│   │   ├── history/       # load_cow.py, load_epr.py
│   │   ├── international/ # load_kof.py, load_atop.py, load_un_voting_*.py, load_igo.py
│   │   │                  # load_henley.py, load_colonial.py, load_diplomatic.py
│   │   └── social/        # load_edelman.py, load_caf_wgi.py
│   ├── catalog/           # indicator catalog + search tools
│   └── analysis/          # export_encyclopedia_data.sql
├── sql/
│   ├── 01_setup/          # Table creation
│   ├── 02_seed/           # Initial data + SIF mapping
│   ├── 03_queries/        # Exploration + data quality
│   └── 04_categories/     # Category assignment scripts (one per domain)
├── api/
│   └── routes/
│       └── countries.py
├── docs/
│   ├── PROJECT_CONTEXT.md
│   ├── SOURCES_ROADMAP.md
│   ├── SOURCES_ENCYCLOPEDIA.md
│   └── SIF_DOMAIN_STRUCTURE.md
├── data/raw/              # NOT in git
├── .comtrade_state.json
├── .env                   # NOT in git
├── .env.example
└── README.md
```

---

## Open Items

### Immediate

1. Comtrade P1+P2 2020–2025 — remaining batches (resumes via `.comtrade_state.json`)
2. `load_vdem.py` — remove `domain`/`dimension` columns (schema mismatch)
3. Save all category SQL scripts to `sql/04_categories/`
4. Auto-descriptions for ~300 indicators without description (Claude API)

### Short Term — API

5. Health API route (blueprint pattern) — next priority
6. Countries List route: `GET /api/countries`
7. Compare route: `GET /api/compare?countries=BOL,PER,ARG`
8. Economy + Governance routes to Demography level
9. Z-score + ranking logic as reusable SQL functions

### Medium Term — New Sources

See `SOURCES_ROADMAP.md` for the full prioritized list. Highlights:
- IHME GBD (mental health, PTSD, DALY)
- Reuters Digital News Report (Communication & Media gap)
- Regional barometers (Latinobarómetro, AmericasBarometer) for Social Fabric
- Cultural/qualitative sources (Open Library, Met Museum, eHRAF, Gutendex)

### Long Term

10. **First visualizations** (Folium / Kepler.gl / Plotly) — the critical gap
11. Power BI showcases
12. Frontend dashboard
13. Subnational data (Phase 3–4, PostGIS)

---

## Lessons Learned

- `partnerCode=ALL` is not a valid Comtrade API v1 parameter — load partner codes from reference API, then batch
- Rejected Comtrade API calls (400) may still count against the daily limit (500/day free tier)
- FastAPI route order matters: `/demography/pyramid` before `/demography/{category}`
- `ON CONFLICT DO UPDATE` fails when the same row appears twice in a batch → deduplicate first
- IUCN API v3 blocked by Cloudflare → use GBIF `occ.search(iucnRedListCategory=...)` instead
- OWID blocks programmatic CSV downloads without a User-Agent header
- Zone.Identifier files appear when copying Windows → WSL → add to `.gitignore`
- `data/raw/` belongs in `.gitignore` (too large, binary files)
- UNESCO DataHub API field: `iso_codes` not `iso_code`; `countries` is a list `['BO']`
- FAO Food Balance Sheets: indicators in `Element` field, not `Item`
- WVS is individual-level data → must aggregate to country level
- Maddison xlsx download redirects to HTML → manual browser download required
- UNDP time_period float issue: `str(int(float(row['year'])))` not direct cast
- WB WGI: correct source is `source=75`, not `source=3`
- ILO INSERT must include `source_id` in tuple — otherwise UNIQUE constraint never fires
- `%` in psycopg2 SQL strings must be a parameter, not hardcoded in query string
- `np.float64` as psycopg2 value → `schema "np" does not exist` → always cast to `float()`
- GW/COW codes ≠ ISO numeric → need manual mapping for EPR, COW, ATOP, IGO datasets
- EPR defunct states (Yugoslavia, USSR) → replicate rows for successors
- Edelman loader: DELETE all before re-inserting (no idempotent fix due to missing dedup key)
- WSL2 crashes on large in-memory pandas operations → chunk-based processing
- UN Voting: split into 4 stages, load only needed columns to avoid RAM crashes
- `git show HEAD~1:path/to/file` rescues overwritten scripts
- PostgreSQL `ROUND(double precision, int)` fails → cast to `::numeric` first
