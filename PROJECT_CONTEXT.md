# Project Context – Country Intelligence Layer

This document captures the full technical context for AI assistants and future reference. Update regularly.

**Last updated:** 2026-05-26

---

## Vision

A multi-dimensional database aggregating country-level data from 25+ international sources. Long-term goal: an interactive, map-centric platform that gives a comprehensive view of any country – economy, geography, culture, infrastructure, environment, history.

The project is structured around the **Societal Intelligence Framework (SIF)** – 10 core domains covering the full complexity of societies. Not a dashboard that shows numbers. A system that answers questions.

**Portfolio positioning:** Demonstrates end-to-end data pipeline thinking, scalable DB architecture, and international analytical perspective. Target: NGO/Impact/International Organizations sector.

---

## Conceptual Framework: SIF – 10 Core Domains

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

---

## Architecture

### Database: PostgreSQL 18 (WSL2 Ubuntu)

### Core Tables

| Table | Description |
|-------|-------------|
| `countries` | 249 countries, ISO codes, coordinates, region. PK: `iso_numeric` (ISO 3166-1) |
| `sources` | 35+ registered data sources |
| `indicator_metadata` | indicator_code, name, unit, source_id, category |
| `indicators` | 5.5M+ data values. Long format, SDMX-inspired |
| `trade_products` | Comtrade HS-4 product trade flows. 2.9M+ rows |
| `trade_partners` | Bilateral trade flows by partner country |

### Indicator Code Convention
Format: `SOURCE:ORIGINAL_CODE` (e.g. `WB:NY.GDP.PCAP.CD`, `VDEM:v2x_polyarchy`)
**Never invent codes** – always preserve original source codes.

### Design Principles
- `time_period` as TEXT: supports `"2023"`, `"2023-01"`, `"static"`, `"trend"`
- `source_id` in UNIQUE key – allows parallel storage from multiple sources
- `obs_status`: A=actual, E=estimated, P=provisional, F=forecast
- `ON CONFLICT DO NOTHING` everywhere – all scripts idempotent/re-runnable
- No hardcoded credentials – all via `.env`

### What was deliberately NOT built
- No `regions` table – overengineering for 7 regions
- No `update_log` table – `last_updated` field sufficient

---

## Tech Stack

- **OS:** Windows 11 + WSL2 Ubuntu
- **Database:** PostgreSQL 18 (TCP on localhost:5432)
- **Language:** Python 3.14
- **Key libraries:** psycopg2-binary, requests, pandas, python-dotenv, fastapi, pygbif, openpyxl
- **GUI:** DBeaver Community Edition
- **IDE:** VS Code

### Setup Notes
- WSL2 + PostgreSQL: `listen_addresses = '*'` in postgresql.conf + pg_hba.conf modification
- PostgreSQL needs manual start: `sudo service postgresql start`
- Python venv: `~/projects/country-intelligence/venv`

---

## API Layer (FastAPI)

### Route Structure

```
GET /api/country/{iso_code}                           → Country Overview + Top KPIs
GET /api/country/{iso_code}/demography                → Domain Overview (4 Category Cards)
GET /api/country/{iso_code}/demography/population     → Population Detail + time series
GET /api/country/{iso_code}/demography/fertility      → Fertility Detail + time series
GET /api/country/{iso_code}/demography/migration      → Migration Detail + time series
GET /api/country/{iso_code}/demography/urbanization   → Urbanization Detail + time series
GET /api/country/{iso_code}/demography/pyramid        → Age pyramid (34 age groups)
GET /api/country/{iso_code}/timeseries/{indicator}    → Generic time series
GET /api/country/{iso_code}/governance                → Governance with summary
GET /api/country/{iso_code}/economy                   → Economy with summary
```

### Three-Level Navigation
```
Level 1 – Country Overview:   Map + Top KPIs
Level 2 – Domain Overview:    Category Cards with key indicator + signal
Level 3 – Category Detail:    All indicators + summary + time series
```

### get_indicator_summary() Fields
`value · z_score · trend_long · trend_short · trend_label · global_rank · regional_rank · latest_year · global_avg · n_countries`

### Indicator Types System
```python
"neutral":  increasing / stable / decreasing    # Population, Urbanization
"flow":     net_inflow / balanced / net_outflow  # Net migration
"positive": improving / stable / declining       # GDP, Life expectancy
"negative": improving / stable / declining       # Child mortality (inverted)
```

### Demography Categories Config
```python
DEMOGRAPHY_CATEGORIES = {
    "population":   {key_indicator: "WB:SP.POP.TOTL",       11 indicators},
    "fertility":    {key_indicator: "WB:SP.DYN.TFRT.IN",     4 indicators},
    "migration":    {key_indicator: "WB:SM.POP.NETM",         5 indicators},
    "urbanization": {key_indicator: "WB:SP.URB.TOTL.IN.ZS",  6 indicators},
}
```

---

## Strategic Decisions

**[DECISION] Trade Data Architecture:**
Trade data in separate tables (`trade_products`, `trade_partners`), not in `indicators`.
Reason: Multidimensional (product × partner × flow) – doesn't fit the indicators schema.

**[DECISION] API Blueprint Approach:**
Demography built as blueprint first, then generalize. Recognize real patterns before going generic.

**[DECISION] Subnational Data:**
Long-term goal: overlay factors on map at subnational level.
Technical requirement: PostGIS + regions table.
Priority: Phase 3–4, not now.

**[DECISION] Raw data not in Git:**
`data/raw/` in `.gitignore` – too large, manually reproducible from source URLs.

---

## Current Data Status (2026-05-26)

| Source | Code | Data Points | Countries | Period | Status |
|--------|------|-------------|-----------|--------|--------|
| World Bank WDI | WB | ~750k | 215 | 2000–2024 | ✅ |
| V-Dem | VDEM | 1.03M | 175 | 1900–2025 | ✅ |
| Freedom House | FH | 15.9k | 193 | 1972–2024 | ✅ |
| CPI | CPI | 2.3k | ~180 | 2012–2024 | ✅ |
| WHO GHO | WHO | 128k | 199–227 | 1932–2024 | ✅ |
| Comtrade P1 | — | 2.93M | 249 | 2010–2024 | ✅ |
| Comtrade P2 | — | loading | — | 2010–2024 | 🔄 |
| OWID CO2 | OWID_CO2 | 218k | ~200 | 1750–2024 | ✅ |
| UNDP HDR + MPI | UNDP | ~38k | 195 | 1990–2023 | ✅ |
| FAO Land Use | FAO_LAND | ~200k | 236 | 1961–2025 | ✅ |
| FAO Food | FAO_FOOD | 7.2k | 178 | 1961–2022 | ✅ |
| ND-GAIN | NDGAIN | ~43k | 192 | 1995–2023 | ✅ |
| GBIF | GBIF | 1.9k | ~200 | 2024 | ✅ |
| GBIF IUCN | GBIF | 991 | ~150 | 2024 | ✅ |
| Open-Meteo | OPENMETEO | ~17k | 249 | 2000–2023 | ✅ |
| Maddison | MADDISON | 38.5k | 166 | 1–2022 | ✅ |
| COW Wars | COW | 585 | 82 | 1816–2003 | ✅ |
| WVS | WVS | 5.6k | 107 | 1981–2022 | ✅ |
| Hofstede | HOFSTEDE | 293 | 60 | static | ✅ |
| WHR | WHR | 7.9k | 158 | 2011–2025 | ✅ |
| UNESCO WHC | UNESCO_WHC | 461 | 170 | 2024 | ✅ |
| Nobel Prize | NOBEL | ~600 | ~60 | 1901–2024 | ✅ |
| IMDb | IMDB | 30.8k | ~150 | 1900–2025 | ✅ |
| RSF | RSF | 1.6k | 180 | 2013–2025 | ✅ |
| Olympics | OLYMPICS | small | ~90 | 2024 | ✅ |
| **TOTAL** | | **~5.5M+** | | | |

---

## Project Structure

```
country-intelligence/
├── scripts/
│   ├── pipeline/
│   │   ├── base/          # load_countries.py, world_bank_historical.py
│   │   ├── wb/            # World Bank domain scripts
│   │   ├── economy/       # load_comtrade.py, load_maddison.py, load_owid_co2.py, load_cpi.py
│   │   ├── health/        # load_who.py, load_fao_food.py
│   │   ├── demographics/  # load_undp.py, load_wvs.py
│   │   ├── environment/   # load_fao_landuse.py, load_ndgain.py, load_gbif.py, load_gbif_iucn.py, load_openmeteo.py
│   │   ├── governance/    # load_freedom_house.py, load_vdem.py, load_rsf.py
│   │   ├── culture/       # load_hofstede.py, load_whr.py, load_nobel.py, load_olympics.py, load_unesco_whc.py, load_imdb.py
│   │   └── history/       # load_cow.py
│   ├── catalog/           # Indicator catalog + search tools
│   └── analysis/
├── sql/
│   ├── 01_setup/          # Table creation
│   ├── 02_seed/           # Initial data + SIF mapping
│   └── 03_queries/        # Exploration + data quality
├── api/
│   └── routes/
│       └── countries.py   # All API routes
├── docs/
│   ├── SOURCES_ROADMAP.md
│   └── SOURCES_ENCYCLOPEDIA.md
├── data/raw/              # NOT in git – too large
├── .comtrade_state.json   # Comtrade resume state
├── .env                   # NOT in git
├── .env.example
└── README.md
```

---

## Open Items

### Immediate
1. Comtrade P2 finish loading (2000–2024)
2. Comtrade P1 load 2000–2009
3. WHO: `NCD_BMI_MINUS2C` + `TB_c_newinc` reload
4. `load_vdem.py` – remove `domain`/`dimension` columns (schema mismatch)

### Short Term
5. Health API route
6. Countries List route: `GET /api/countries`
7. Compare route: `GET /api/compare?countries=BOL,PER,ARG`
8. Economy + Governance routes to Demography level

### Medium Term
9. CCKP Climate API – URL structure not yet resolved
10. Global Forest Watch – Tree Cover Loss 2001–2023
11. Olympics historical (1896–2020)
12. Penn World Table – TFP, Human Capital

### Long Term
13. First visualizations (Folium / Kepler.gl / Plotly)
14. Power BI showcases
15. Frontend dashboard

---

## Lessons Learned

- `partnerCode=ALL` is not a valid Comtrade API v1 parameter
- FastAPI route order matters: `/demography/pyramid` must come before `/demography/{category}`
- `ON CONFLICT DO UPDATE` fails when the same row appears twice in one batch → deduplicate first with dict
- Comtrade sometimes returns duplicate rows
- IUCN API v3 blocked by Cloudflare → use GBIF `occ.search(iucnRedListCategory=...)` instead
- OWID blocks programmatic CSV downloads without User-Agent header
- Zone.Identifier files appear when copying Windows → WSL → add to `.gitignore`
- `data/raw/` belongs in `.gitignore`
- UNESCO DataHub API field: `iso_codes` not `iso_code`
- FAO Food Balance Sheets: indicators in `Element` field, not `Item`
- WVS is individual-level data → must aggregate to country level (mean per country + year)
- Maddison xlsx download redirects to HTML → manual browser download required
- UNDP time_period float issue: use `str(int(float(row['year'])))` not direct cast
- Rejected Comtrade API calls (400) may still count against daily limit
