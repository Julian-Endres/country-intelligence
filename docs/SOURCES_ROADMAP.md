# Data Sources Roadmap — Country Intelligence Layer

**Last updated:** 2026-06-03

---

## Status Overview — Integrated Sources (50)

| Source | Code | Domain | Status | Data Points |
|--------|------|--------|--------|-------------|
| World Bank WDI + WGI | WB | Multi | ✅ Integrated | ~1.09M |
| RestCountries | REST | Base | ✅ Integrated | 249 countries |
| V-Dem Institute | VDEM | Governance | ✅ Integrated | 1.03M |
| Freedom House | FH | Governance | ✅ Integrated | 15.9k |
| Transparency International CPI | TI | Governance | ✅ Integrated | 2.3k |
| RSF Press Freedom Index | RSF | Media | ✅ Integrated | 1.6k |
| WHO GHO | WHO | Health | ✅ Integrated | ~105k |
| UN Comtrade P1 (Products) | — | Economy/IR | ✅ Integrated | 5.63M+ |
| UN Comtrade P2 (Partners) | — | IR | ✅ Integrated | 997k+ |
| OWID CO2 | OWID_CO2 | Environment | ✅ Integrated | 218k |
| Ember Electricity | Ember | Environment | ✅ Integrated | 30.2k |
| Energy Institute | EI | Environment/Economy | ✅ Integrated | 53.3k |
| EIA Energy | EIA | Economy | ✅ Integrated | 10.3k |
| UNDP HDR + MPI | UNDP | Economy/Demographics | ✅ Integrated | ~38k |
| FAO Land Use | FAO_LAND | Environment | ✅ Integrated | 134k |
| FAO Food Balance Sheets | FAO_FOOD | Health | ✅ Integrated | 7.2k |
| FAO Food Groups | FAO_FOOD_GRP | Health | ✅ Integrated | 61.7k |
| GBIF Biodiversity + IUCN | GBIF | Environment | ✅ Integrated | 42.3k |
| Open-Meteo ERA5 | OPENMETEO | Environment | ✅ Integrated | 2.7k |
| Maddison Project 2023 | MADDISON | History | ✅ Integrated | 38.5k |
| Correlates of War | COW | History | ✅ Integrated | 585 |
| EPR Ethnic Power Relations | EPR | History | ✅ Integrated | 32.5k + relational |
| World Values Survey | WVS | Culture | ✅ Integrated | 5.6k |
| Hofstede 6 Dimensions | HOFSTEDE | Culture | ✅ Integrated | 293 |
| World Happiness Report | WHR | Social Fabric | ✅ Integrated | 8.1k |
| Pew Research (Religion) | PEW_REL | Culture | ✅ Integrated | 3.2k |
| CAF World Giving Index | CAF_WGI | Social Fabric | ✅ Integrated | 7.0k |
| Edelman Trust Barometer | EDELMAN | Social Fabric | ✅ Integrated | 12.3k |
| WID.world (Inequality) | WID | Economy | ✅ Integrated | ~275k |
| Penn World Table 11.0 | PWT | Economy | ✅ Integrated | ~211k |
| SIPRI Military Expenditure | SIPRI | Governance | ✅ Integrated | 8.5k |
| Polity5 | POLITY5 | Governance | ✅ Integrated | 102k |
| Global Hunger Index | GHI | Health | ✅ Integrated | 6.5k |
| Fragile States Index | FSI | Governance | ✅ Integrated | 2.2k |
| UNESCO WHC + ICH | UNESCO | Culture | ✅ Integrated | 2.2k |
| Nobel Prize | NOBEL | Culture | ✅ Integrated | 1.4k |
| IMDb | IMDB | Culture/Media | ✅ Integrated | 30.8k |
| GI-TOC Crime Index | GITOC | Governance | ✅ Integrated | 8.1k |
| UNODC Homicide | UNODC | Governance | ✅ Integrated | 10.8k |
| ILO | ILO | Economy | ✅ Integrated | 78.7k |
| KOF Globalisation Index | KOF | Int. Relations | ✅ Integrated | 86.3k |
| ATOP Military Alliances | ATOP | Int. Relations | ✅ Integrated | 21.1k |
| UN General Assembly Voting | UNVOTE | Int. Relations | ✅ Integrated | 151k |
| COW IGO Membership | IGO | Int. Relations | ✅ Integrated | 12.4k |
| Henley Passport Index | HENLEY | Int. Relations | ✅ Integrated | 788 |
| Glottolog 5.3 | GLOTTOLOG | Culture | ✅ Integrated | 732 |
| WEF Global Gender Gap | WEF_GGGI | Multi | ✅ Integrated | ~795 |
| MARPOR Manifesto Project | MARPOR | Governance | ✅ Integrated | relational |
| UNHCR Refugee Data | UNHCR | Demographics | ✅ Integrated | 15.2k |
| samayo/country-json | SAMAYO | Culture/Base | ✅ Integrated | ~1k |

**Total: ~9M+ data points across 50 sources**

### Relational datasets (not in `indicators`)

| Dataset | Schema.Table | Rows | Period |
|---------|--------------|------|--------|
| MARPOR Elections | politics.marpor_elections | 5.3k+ | — |
| Constitutional Events (CCP) | politics.constitutional_events | 4.1k | — |
| Coups (CSP) | politics.coups | 919 | 1946–2021 |
| Diplomatic Relations (DASID) | international.diplomatic_relations | 1.2M | 1985–2019 |
| Diplomatic Representation (DDR) | international.diplomatic_representation | 433k | 1960–2024 |
| Colonial History (COLDAT) | international.colonial_history | 160 | — |
| Ethnic Groups (EPR) | history.ethnic_groups | 32.5k | 1946–2023 |
| Trade Products (Comtrade) | trade.trade_products | 5.63M+ | 2000–2025 |
| Trade Partners (Comtrade) | trade.trade_partners | 997k+ | 2000–2025 |

---

## Phase History

### Phase 1 — Cochabamba ✅ Complete

Foundation with the most important global sources. Core architecture, 249 countries, ~5.5M data points across the primary multi-domain aggregators (WB, V-Dem, WHO, Comtrade).

### Phase 2 — Category Sprint ✅ Complete

4-level hierarchy (domain → category → dimension) assigned to all indicators. New sources: WID, PWT, ILO, EPR, OWID Energy, Polity5, SIPRI, GHI, Edelman, CAF, MARPOR. Comtrade extended to 2000–2024. New relational schemas (politics, international, history). ~7M+ data points.

### Phase 3 — International Relations & Culture Sprint ✅ Complete

International Relations domain filled: KOF, ATOP, UN Voting, IGO, Henley. Culture extended: Glottolog, Pew Religion. Comtrade migrated to `trade` schema. Encyclopedia concept + Notion workspace built. ~9M+ data points, 50 sources.

---

## Phase 4 — Next Sources & API (upcoming work phase)

### Priority 1 — Fill domain gaps

| Source | Domain | Why | Access |
|--------|--------|-----|--------|
| **IHME GBD** | Health | Mental health, PTSD, DALY, depression/anxiety | Export tool, ghdx.healthdata.org |
| **Reuters Digital News Report** | Comm. & Media | Media trust, news consumption — biggest gap | PDF scrape, annual |
| **ITU DataHub** | Comm. & Media | ICT access, internet, mobile, cybersecurity | API/CSV, datahub.itu.int |
| **Latinobarómetro** | Social Fabric | LAC political attitudes, institutional trust | XLS/CSV, free after 1yr |
| **AmericasBarometer (LAPOP)** | Social Fabric | 34 countries, 2004–2023 | Click-license, vanderbilt.edu/lapop |

### Priority 2 — Cultural & qualitative depth

| Source | Domain | Content | Access |
|--------|--------|---------|--------|
| **Open Library API** | Culture | Books, authors by country | REST JSON, openlibrary.org |
| **Project Gutenberg / Gutendex** | Culture | Public-domain literature by topic | REST JSON, gutendex.com |
| **Met Museum Open Access** | Culture | Art, jewelry, fashion objects | GitHub CSV + REST, metmuseum.github.io |
| **Europeana** | Culture | European art, fashion, heritage | REST API (key), pro.europeana.eu |
| **eHRAF World Cultures** | Culture/History | Ethnographic OCM index, rituals | Web export, Yale (license) |
| **ARDA** | Culture | Religion family trees, detailed | Web/CSV, thearda.com |
| **TasteAtlas** | Culture | National dishes, food culture (textual) | Unofficial JSON |
| **MusicBrainz** | Culture | Global music metadata, PostgreSQL dumps | Bulk dump / REST |

### Priority 3 — Environment & geography

| Source | Domain | Content | Access |
|--------|--------|---------|--------|
| **Global Forest Watch** | Environment | Tree cover loss, carbon | API key, globalforestwatch.org |
| **WHO/UNICEF JMP** | Health/Social | WASH household surveys, hygiene | CSV, washdata.org |
| **Köppen-Geiger V3** | Environment | Climate classification | GeoTIFF, gloh2o.org |
| **OpenStreetMap Overpass** | Geography | Infrastructure, POIs, transit | REST API, overpass-turbo.eu |
| **Copernicus CDS (ERA5)** | Environment | Full reanalysis climate data | API, cds.climate.copernicus.eu |

### Priority 4 — Economy & society

| Source | Domain | Content | Access |
|--------|--------|---------|--------|
| **UNWTO Tourism** | Economy/IR | Tourist arrivals, receipts | CSV export, e-unwto.org |
| **FAOSTAT Livestock** | Environment | Livestock primary, animals | Bulk CSV, fao.org |
| **OECD PISA** | Social/Education | Student performance | CSV/SAS, oecd.org |
| **UCDP Conflict Data** | History | Organized violence, deaths | API (token), ucdp.uu.se |
| **GTI Global Terrorism Index** | Governance | Terrorism impact, 163 countries | IEP Excel |
| **Voter Turnout (IDEA)** | Governance | Election participation 1945+ | CSV, idea.int |
| **Equaldex** | Culture/Governance | LGBTQ rights index | API |
| **Olympics historical** | Culture | Medals 1896–2020 | Kaggle (auth) |

### Priority 5 — API routes

- Health, Economy, Environment, Governance routes → Demography blueprint level
- Countries List route: `GET /api/countries`
- Compare route: `GET /api/compare?countries=BOL,PER,ARG`
- Z-score + ranking logic as reusable SQL functions

---

## Latin America & Bolivia (regional deep-dive sources)

For subnational and regional work (Phase 5+):

| Source | Coverage | Access |
|--------|----------|--------|
| **CEPALSTAT (UN ECLAC)** | 1.000+ indicators, 33 LAC countries | api-cepalstat.cepal.org |
| **IDB Numbers for Development** | 2.000+ indicators, all LAC | api-data.iadb.org |
| **SEDLAC (CEDLAS + WB)** | Household surveys | cedlas.econo.unlp.edu.ar |
| **INE Bolivia + ANDA** | Census 2024 (413 MB CSV) | REDATAM/CSV bulk |
| **RAISG / MapBiomas Bolivia** | Amazon territories, land use | Shapefiles |
| **Mi Teleférico GTFS** | La Paz cable car network | Mobility Database |

**Note:** GeoBolivia was shut down in 2024–25 without warning. TIOC (Territorio Indígena Originario Campesino) should be modeled in any subnational schema.

---

## Blocked / Problematic Sources

| Source | Problem | Workaround |
|--------|---------|------------|
| IUCN Red List API v3 | Cloudflare block | GBIF `iucnRedListCategory` filter |
| CCKP ERA5 Timeseries | API returns empty data | Open-Meteo instead |
| COW Intrastate v5.1 | ZIP is HTML redirect | Manual download |
| Maddison xlsx | Redirect to HTML | Manual browser download |
| OWID CSV direct | 403 without User-Agent | Set User-Agent header |
| IMF DOTS | 403 API protection | No workaround found |
| ILO SDMX/Bulk | Cloudflare block | Loaded via OWID |
| Box Office data | No free country-level bulk | Deferred |

---

## API Migration Deadlines (watch list)

| Source | Deadline | Action |
|--------|----------|--------|
| WHO GHO OData | End 2025 | Schema migration check |
| UCDP | Feb 2026 | Token auth required |
| WDPA v3 | May 2026 | v4 migration, new token |
| Europeana | May 2025 | API key now required |
