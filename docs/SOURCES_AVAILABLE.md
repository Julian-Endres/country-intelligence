# Sources – available

**As of:** 2026-11-10 · Figures from `sql/03_queries/2026-11-10_quelleninventar.sql` · Counterpart: `SOURCES_CANDIDATES.md`

## Summary

The database holds **59 sources in `sources`**, 49 of them with values (4,195,302 values in `indicators`), plus **18 relational tables** with 8,508,875 rows; **7 sources exist only as relational tables** (no codes in `indicators`). The status column points to the Notion backlog, where the explanation lives.

Status: ✅ usable · ⚠️ usable with a known issue · ❌ not usable

## 01 · Population & Demographics

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `UNHCR` | UNHCR – UN Refugee Agency | 6 | 15,161 | 209 | 2000–2024 | – | ⚠️ values without source_id (#1) | `demographics/load_unhcr.py` |

## 02 · Health & Survival

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `WHO` | World Health Organization | 28 | 105,262 | 229 | 1932–2024 | 06 | ⚠️ 2 codes without data (#63), zero values in adolescent birth rate (#92) | `health/load_who.py`, `load_who_quickwins.py` |
| `FAO_FOOD_GRP` | FAOSTAT Food Balance Sheets – Food Groups | 26 | 61,683 | 178 | 2010–2023 | – | ✅ | `health/load_fao_food_groups.py` |
| `UNDP` | UN Development Programme | 19 | 37,456 | 195 | 1990–2024 | 03, 04, 08 | ⚠️ NaN values in MPI (#85) | `demographics/load_undp.py` |
| `FAO_FOOD` | FAOSTAT Food Balance Sheets | 3 | 7,233 | 178 | 2010–2023 | – | ✅ | `health/load_fao_food.py` |
| `GHI` | Global Hunger Index – Concern Worldwide / Welthungerhilfe | 1 | 6,535 | 131 | 2000–2025 | – | ⚠️ values without source_id, duplicate rows (#1) | `health/load_ghi.py` |

## 03 · Education, Science & Innovation

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `NOBEL` | Nobel Prize API | 6 | 1,415 | 82 | 1901–2025 | 08 | ✅ | `culture/load_nobel.py` |

## 04 · Economy, Wealth & Labor

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `WB` | World Bank | 253 | 1,118,104 | 216 | 1963–2025 | 01, 02, 05, 06, 07 | ⚠️ outdated vintage (#106), poverty lines mislabelled (#91) | `several (#14)` |
| `WID` | WID.world — World Inequality Database | 38 | 274,558 | 215 | 1800–2024 | 06 | ⚠️ values without source_id (#1) | `economy/load_wid.py` |
| `PWT` | Penn World Table 11.0 – GGDC Groningen | 21 | 211,399 | 185 | 1950–2023 | 01 | ⚠️ values without source_id (#1) | `economy/load_pwt.py` |
| `ILO` | ILOSTAT – International Labour Organization | 9 | 78,678 | 229 | 2000–2027 | – | ⚠️ duplicate rows without source_id (#1), projections up to 2027 (#86) | `economy/load_ilostat.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `COMTRADE` | UN Comtrade (goods by HS4, trading partners) | `trade.trade_products`, `trade.trade_partners` | 6,872,764 | 2000–2025 | ⚠️ incomplete, USA/FRA/IND/NOR/CHE missing (#88), table metadata not linked (#81) | `economy/load_comtrade_v2.py` |

## 05 · Infrastructure & Technology

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `EIA` | U.S. Energy Information Administration – International Energy Statistics | 1 | 10,267 | 216 | 1965–2024 | – | ✅ | `environment/load_owid_energy.py` |

## 06 · Environment, Climate & Resources

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `OWID_CO2` | Our World in Data – CO2 & GHG Emissions | 10 | 218,554 | 215 | 1750–2024 | – | ✅ | `economy/load_owid_co2.py` |
| `FAO_LAND` | FAOSTAT Land Use | 13 | 134,130 | 236 | 1961–2025 | – | ✅ | `environment/load_fao_landuse.py` |
| `EI` | Energy Institute – Statistical Review of World Energy | 6 | 53,326 | 215 | 1900–2024 | 04 | ✅ | `environment/load_owid_energy.py` |
| `GBIF` | Global Biodiversity Information Facility | 12 | 42,302 | 249 | 2000–2024 | – | ⚠️ 2024 value is the all-time total (#90) | `environment/load_gbif*.py` |
| `Ember` | Ember – Yearly Electricity Data | 5 | 30,175 | 213 | 1965–2025 | – | ✅ | `environment/load_owid_energy.py` |
| `OPENMETEO` | Open-Meteo ERA5 | 3 | 2,652 | 48 | 2000–2023 | – | ✅ only 48 countries | `environment/load_openmeteo.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `GBIF` | GBIF – species occurrences | `biodiversity.species_occurrences` | 2,490 | – | ⚠️ experimental (#15), no table metadata (#81) | `experimental/species_gbif_wip.py` |

Lost:

| Code | Source | Status | Loader |
|---|---|---|---|
| `NDGAIN` | ND-GAIN Country Index | ❌ data lost, loader still exists (#93) | `environment/load_ndgain.py` |

## 07 · Politics, Governance & Law

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `VDEM` | V-Dem Institute | 59 | 1,126,533 | 175 | 1900–2025 | – | ⚠️ open findings (#6) | `governance/load_vdem.py` |
| `POLITY5` | Polity5 – Center for Systemic Peace | 6 | 101,643 | 168 | 1776–2020 | – | ⚠️ values without source_id (#1), special codes stored as values (#89) | `governance/load_polity5.py` |
| `FH` | Freedom House | 3 | 15,930 | 193 | 1972–2024 | – | ⚠️ FH:STATUS has no data (#63) | `governance/load_freedom_house.py` |
| `ACLED` | Armed Conflict Location & Event Data Project | 5 | 13,917 | 243 | 1997–2026 | – | ✅ API authentication changed (#66) | `governance/load_acled.py` |
| `UNODC` | UN Office on Drugs and Crime | 4 | 10,806 | 228 | 1990–2026 | – | ⚠️ partly loaded via OWID (#2), no loader in repo (#69) | – |
| `SIPRI` | SIPRI Military Expenditure Database | 1 | 8,523 | 166 | 1949–2025 | – | ⚠️ values without source_id (#1), no loader in repo (#69) | – |
| `GITOC` | GI-TOC Global Organized Crime Index | 17 | 8,110 | 185 | 2021–2025 | – | ✅ | `governance/load_fsi_gitoc_owid.py` |
| `UCDP` | Uppsala Conflict Data Program | 3 | 6,396 | 126 | 1989–2025 | – | ✅ token required (#66) | `governance/load_ucdp*.py` |
| `TI` | Transparency International | 1 | 2,286 | 180 | 2012–2024 | – | ✅ | `economy/load_cpi.py` |
| `FSI` | Fragile States Index (Fund for Peace) | 13 | 2,249 | 173 | 2022–2022 | – | ✅ 2022 only | `governance/load_fsi_gitoc_owid.py` |
| `RSF` | Reporters Without Borders – Press Freedom Index | 1 | 1,591 | 177 | 2013–2021 | – | ⚠️ ends 2021 (#10) | `governance/load_rsf.py` |
| `WEF_GGGI` | WEF Global Gender Gap Index | 5 | 795 | 159 | static | 02, 03, 04 | ⚠️ static, actually a time series (#87) | `governance/load_gender_gap.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `UCDP` | UCDP – conflict tables | `politics.conflicts_state`, `politics.conflicts_state_actors`, `politics.conflicts_nonstate`, `politics.conflicts_onesided`, `politics.conflict_context` | 11,688 | 1946–2025 | ✅ | `governance/load_ucdp*.py` |
| `MARPOR` | Manifesto Project (MARPOR) | `politics.marpor_elections`, `politics.political_parties` | 6,697 | – | ⚠️ table metadata not linked to `sources` (#81) | `governance/load_marpor.py` |
| `CCP` | Comparative Constitutions Project v6 | `politics.constitutional_events` | 4,335 | 1789–today | ⚠️ table metadata not linked to `sources` (#81) | `history/load_ccp.py` |
| `CLINE` | Cline Center Coup d'État Project | `politics.coups` | 957 | 1945–2026 | ⚠️ table metadata not linked (#81); `load_coups.py` contains the DDR loader, own loader missing (#69) | – |

## 08 · Culture, Society & Beliefs

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `IMDB` | IMDb Non-Commercial Datasets | 3 | 30,820 | 229 | 1900–2025 | – | ✅ | `culture/load_imdb.py` |
| `EDELMAN` | Edelman Trust Barometer | 36 | 12,340 | 28 | 2012–2025 | – | ✅ only 28 countries | `social/load_edelman.py` |
| `WHR` | World Happiness Report | 7 | 8,095 | 163 | 2011–2025 | – | ✅ | `culture/load_whr.py` |
| `CAF_WGI` | CAF World Giving Index | 4 | 6,964 | 161 | 2010–2024 | – | ⚠️ values without source_id (#1) | `social/load_caf_wgi.py` |
| `WVS` | World Values Survey | 21 | 5,625 | 107 | 1981–2023 | – | ✅ | `demographics/load_wvs.py` |
| `PEW_REL` | Pew Research Center – Global Religious Composition | 8 | 3,184 | 199 | 2010–2020 | – | ⚠️ values without source_id (#1) | `culture/load_pew_religion.py` |
| `UNESCO_ICH` | UNESCO Intangible Cultural Heritage | 3 | 1,717 | 157 | 2008–2025 | – | ✅ | `culture/load_unesco_ich.py` |
| `SAMAYO` | samayo/country-json | 5 | 956 | 236 | static | 02, 06, 09 | ✅ static (#87), unofficial source | `culture/load_samayo.py`, `load_national_dishes.py` |
| `GLOTTOLOG` | Glottolog 5.3 | 3 | 732 | 244 | static | – | ✅ static (#87) | `culture/load_glottolog.py` |
| `UNESCO_WHC` | UNESCO World Heritage Centre | 4 | 461 | 170 | 2024–2024 | – | ✅ | `culture/load_unesco_whc.py` |
| `HOFSTEDE` | Hofstede Cultural Dimensions | 6 | 293 | 60 | static | – | ❌ values assigned to wrong countries (#102) | `culture/load_hofstede.py` |
| `OLYMPICS` | Olympic Games – OWID | 0 | 0 | 0 | – | – | ❌ data lost (#9) | `culture/load_olympics.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `SAMAYO` | samayo/country-json – extra tables | `culture.country_facts`, `culture.national_dishes` | 475 | static | ⚠️ no table metadata (#81) | `culture/load_samayo.py`, `load_national_dishes.py` |

## 09 · History & Collective Memory

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `MADDISON` | Maddison Project Database 2023 | 2 | 38,549 | 166 | 1000–2022 (+ static) | – | ✅ | `economy/load_maddison.py` |
| `EPR` | Ethnic Power Relations Dataset | 3 | 32,478 | 171 | 1946–2023 | – | ✅ some shares above 100 % (#64) | `history/load_epr.py` |
| `COW` | Correlates of War Project | 4 | 585 | 82 | 1823–2003 | – | ⚠️ 2 codes without data (#63) | `history/load_cow.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `EPR` | EPR – ethnic groups | `history.ethnic_groups` | 10,769 | 1946–2023 | ⚠️ no table metadata (#81) | `history/load_epr.py` |
| `COLDAT` | COLDAT Colonial Dates (Uni Bremen) | `international.colonial_history` | 161 | – | ⚠️ no table metadata (#81) | `history/load_coldat.py` |

## 10 · International Relations & Global Integration

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `UNVOTE` | UN General Assembly Voting Data | 16 | 151,205 | 193 | 1946–2025 | – | ✅ | `international/load_un_voting*.py` |
| `KOF` | KOF Swiss Economic Institute – Globalisation Index | 9 | 86,290 | 197 | 1970–2023 | – | ✅ | `international/load_kof.py` |
| `ATOP` | Alliance Treaty Obligations and Provisions (ATOP) | 6 | 66,474 | 187 | 1815–2018 | – | ✅ ends 2018 | `international/load_atop.py` |
| `IGO` | COW IGO Membership Data v3.0 | 3 | 40,077 | 193 | 1816–2014 | – | ✅ ends 2014 | `international/load_igo.py` |
| `HENLEY` | Henley Passport Index | 4 | 788 | 197 | static | – | ✅ static (#87) | `international/load_henley.py` |

Relational tables:

| Code | Source | Tables | Rows | Period | Status | Loader |
|---|---|---|---|---|---|---|
| `DASID` | DASID Dyadic Annual State Interactions (Pardee Center) | `international.diplomatic_relations` | 1,165,894 | – | ⚠️ no table metadata (#81) | `international/load_dasid.py` |
| `DDR` | Diplometrics Diplomatic Representation 1960–2024 | `international.diplomatic_representation` | 432,645 | 1960–2024 | ⚠️ no table metadata (#81) | `international/load_ddr.py` |

## Cross-cutting and base data

| Code | Source | Codes | Values | Countries | Period | Also in | Status | Loader |
|---|---|---|---|---|---|---|---|---|
| `REST` | RestCountries | 0 | 0 | 0 | – | – | base: country master data in `countries` | `base/load_countries.py` |
| `OWID_SOCIAL` | OWID – Social & Health Indicators | 0 | 0 | 0 | – | – | ⚠️ aggregator, values stored under other sources' codes (#2) | `governance/load_fsi_gitoc_owid.py` |

## Maintenance

API changes affecting loaded sources, check before the next reload (#66): ACLED (new authentication), UCDP (token), WHO GHO (schema migration).

## Provenance and rules

- **Values** counts all rows in `indicators` whose code is assigned to this source in `indicator_metadata`, including values without a source_id (#1). **Countries** = distinct `iso_numeric`. **Period** = first and last year; "static" = values without a year (#87).
- **Main domain** = the domain holding most of the source's codes; "Also in" lists the others. For mixed sources (`SAMAYO`, `EI`) the content decides.
- Every source appears **exactly once** in one of the two files. When a candidate source is loaded, its row moves here.
- Check: `python3 scripts/check_sources.py` (add `--db` to compare against the database). Regenerate: `python3 scripts/gen_sources_available.py`.
