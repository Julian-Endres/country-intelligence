# SIF Domain Structure — Full 4-Level Hierarchy (v2)

**Last updated:** 2026-07-10
**Levels:** Domain → Category → Dimension → Indicator (examples)

**Legend:**
- ✅ **Confirmed** — category structure fully documented (Notion Encyclopedia) and reflected in `indicator_metadata`
- 🔧 **Partial** — some categories confirmed, others still planning-stage
- 📋 **Planned** — category structure is a proposal from project planning docs, not yet implemented in the DB or documented in depth

---

## 01. Population & Demographics ✅

**~84 indicators, all 4/4 categories fully documented.** Sources: World Bank WDI, UNHCR, Penn World Table (historical population).

### Category: Population & Growth

**Dimension: Population & Growth**
- WB:SP.POP.TOTL — Total population
- WB:SP.POP.GROW — Population growth (annual %)
- WB:SP.POP.TOTL.FE.ZS — Female (% of total)
- WB:SP.POP.TOTL.MA.ZS — Male (% of total)
- WB:SP.POP.BRTH.MF — Sex ratio at birth
- PWT:pop — Population (millions), historical back to 1950

**Dimension: Altersverteilung & Abhängigkeit (Age Distribution & Dependency)**
- WB:SP.POP.0014.TO.ZS — Population ages 0–14 (%)
- WB:SP.POP.1564.TO.ZS — Population ages 15–64 (%)
- WB:SP.POP.65UP.TO.ZS — Population ages 65+ (%)
- WB:SP.POP.DPND — Age dependency ratio
- WB:SP.POP.DPND.YG — Young dependency ratio
- WB:SP.POP.DPND.OL — Old dependency ratio
- WB:SP.DYN.TFRT.IN — Total fertility rate
- WB:SP.DYN.CBRT.IN — Birth rate (per 1,000)
- WB:SP.DYN.CDRT.IN — Death rate (per 1,000)
- WB:SP.ADO.TFRT — Adolescent fertility rate

### Category: Age Structure

**Dimension: Age Structure**
- `WB:SP.POP.{band}.MA.5Y` / `WB:SP.POP.{band}.FE.5Y` — 34 indicators, five-year age bands from 0–4 to 80+, male and female. Raw material for population pyramid visualization; 215 countries, 2000–2024.

### Category: Migration & Displacement

**Dimension: Migration & Displacement**
- WB:SM.POP.NETM — Net migration
- WB:SM.POP.TOTL.ZS — Migrant stock (% of population)
- WB:SM.POP.TOTL — Migrant stock (absolute)
- UNHCR:refugees_origin — Refugees originating from country
- UNHCR:refugees_asylum — Refugees hosted
- UNHCR:asylum_seekers — Asylum seekers
- UNHCR:idps — Internally displaced persons
- UNHCR:stateless — Stateless persons

### Category: Urbanization

**Dimension: Urbanization**
- WB:SP.URB.TOTL.IN.ZS — Urbanization rate (%)
- WB:SP.URB.GROW — Urban population growth
- WB:SP.URB.TOTL — Urban population (absolute)
- WB:SP.RUR.TOTL.ZS — Rural population (%)
- WB:SP.RUR.TOTL.ZG — Rural population growth
- WB:SP.RUR.TOTL — Rural population (absolute)
- WB:EN.POP.DNST — Population density
- WB:EN.POP.SLUM.UR.ZS — Slum population (% of urban)

---

## 02. Health & Survival 📋

**~121 indicators.** Sources: WHO GHO, World Bank, FAO Food, Global Hunger Index. Data loaded; full Encyclopedia documentation not yet started — categories below are the working assignment already applied in `indicator_metadata`, not yet validated with Bolivia/South-America analysis.

### Survival & Mortality
- **Mortality & Life Expectancy** — WB:SP.DYN.LE00.IN, WHO:MDG_0000000001 (infant), WHO:MDG_0000000007 (under-5), WB:SH.DYN.MORT
- **Child Health** — WB:SH.STA.STNT.ME.ZS, GHI:stunting, GHI:wasting, WHO:CHILDMORT5TO14

### Disease & Burden
- **Disease & Epidemics** — WHO:WHS3_62 (measles), WB:SH.TBS.INCD (TB), WB:SH.DYN.AIDS.ZS (HIV), WB:SH.MLR.INCD.P3 (malaria)
- **Mental Health** — thin; IHME GBD planned (Phase 4) for PTSD/depression/DALYs

### Nutrition & Food
- **Nutrition & Food Security** — WHO:NCD_BMI_30A/25A/18A (adult), WHO:NCD_BMI_PLUS1C/MINUS2C (children), GHI:score, FAO_FOOD:energy_kcal + Food Groups (45 indicators)

### Health System
- **Healthcare System** — WHO:UHC_INDEX_REPORTED, WB:SH.MED.PHYS.ZS, WB:SH.XPD.CHEX.GD.ZS
- **Immunization** — WB:SH.IMM.MEAS, WB:SH.IMM.IDPT

### Risk Behavior
- **Substance Use** — WHO:NCD_PAA (physical inactivity), WB:SH.ALC.PCAP.LI
- **Reproductive Health** — WHO:MDG_0000000003, WB:SH.STA.MMRT

### Environment & WASH
- **WASH** — WHO:WSH_WATER_BASIC, WHO:WSH_SANITATION_BASIC, WB:SH.H2O.BASW.ZS

---

## 03. Education, Science & Innovation 📋

**~10 indicators — thin, Phase 4.** Only World Bank literacy/enrollment data currently loaded.

### Educational Attainment
- **Literacy & Schooling** — WB:SE.ADT.LITR.ZS
- **Needs Phase 4 sources:** UNESCO UIS (enrollment, attainment), OECD PISA (learning outcomes), WIPO (patents, as innovation proxy)

---

## 04. Economy, Wealth & Labor ✅

**~145 indicators, 5/7 categories fully documented with composite scores.** Sources: World Bank (WDI+WGI), UN Comtrade, WID.world, Penn World Table, Maddison, ILO.

### Category: Output & Growth ✅

**Dimension: Wirtschaftsgröße & Dynamik (Economic Size & Dynamics)**
- WB:NY.GDP.MKTP.CD — GDP, current US$
- WB:NY.GDP.PCAP.CD — GDP per capita, nominal
- WB:NY.GDP.PCAP.PP.KD — ⭐ GDP per capita, PPP, real (headline indicator)
- WB:NY.GDP.PCAP.KD.ZG — Real GDP per capita growth (annual %)
- PWT:rgdpe — Real GDP, expenditure-side, chained PPPs
- MADDISON:gdppc — Historical GDP per capita (year 1846–2022)
- PWT:ctfp — Total factor productivity (USA=1)

**Dimension: Stabilität & Preisniveau (Stability & Price Level)**
- WB:FP.CPI.TOTL.ZG — Inflation, consumer prices (annual %)
- WB:NY.GDP.DEFL.KD.ZG — Inflation, GDP deflator (annual %)
- WB:FP.CPI.TOTL — Consumer price index (2010=100)
- WB:PA.NUS.FCRF — Official exchange rate (LCU per US$)
- PWT:pl_gdpo — Price level of GDP (USA=1.0)
- ILO:EAR_EHRA_SEX_NB — Average hourly earnings (local currency)
- WB:FI.RES.TOTL.CD — Total reserves (US$)
- WB:FI.RES.TOTL.MO — ⭐ Reserves in months of imports
- WB:FI.RES.TOTL.DT.ZS — Reserves (% of external debt)

**Dimension: Kapital & Produktivität (Capital & Productivity)**
- PWT:cn — Capital stock (mil. 2021 US$, PPP)
- PWT:delta — Average depreciation rate of capital stock
- PWT:irr — Real internal rate of return
- WB:BX.KLT.DINV.CD.WD — FDI net inflows
- PWT:hc — Human capital index
- WB:NY.ADJ.AEDU.GN.ZS — Education expenditure (% GNI)
- PWT:labsh — Labour share of GDP
- PWT:emp — Employed persons (millions)
- PWT:ctfp — TFP (shared with Wirtschaftsgröße & Dynamik, not re-documented)

**Dimension: Wirtschaftsstruktur (Economic Structure)**
- PWT:csh_c — Household consumption share of GDP
- PWT:csh_g — Government consumption share of GDP
- PWT:csh_i — Investment share of GDP
- PWT:csh_x — Exports share of GDP
- PWT:csh_m — Imports share of GDP
- WB:NV.AGR.TOTL.ZS — Agriculture, value added (% GDP)
- WB:NV.IND.TOTL.ZS — Industry, value added (% GDP)
- WB:NV.SRV.TOTL.ZS — Services, value added (% GDP)
- WB:NV.IND.MANF.ZS — Manufacturing, value added (% GDP)
- WB:NY.GNP.PCAP.CD — GNI per capita
- ILO:SDG_0831_SEX_ECO_RT — Informal employment rate (cross-referenced as validity signal, see Labour & Employment)
- WB:SL.EMP.SELF.ZS — Self-employed (% of employment) — informality proxy
- WB:SL.AGR.EMPL.ZS — Agricultural employment share
- WB:GC.TAX.TOTL.GD.ZS — Tax revenue (% GDP) — cross-referenced with Public Finance

**Composite scores (percentile rank, 2022 reference year):** Output Score (GDP per capita PPP 50% + TFP 30% + 10-year CAGR 20%), Stability Score (inflation distance-from-2% 50% + reserve months 50%), Structure Score (investment share 40% + human capital 35% + manufacturing share 25%, ECI planned as Phase-4 replacement for manufacturing).

### Category: Equality & Distribution ✅

**Dimension: Wealth Distribution**
- WID:shwealj992:p99p100 — Top 1% wealth share
- WID:shwealj992:p90p100 — Top 10% wealth share
- WID:shwealj992:p0p50 — ⭐ Bottom 50% wealth share
- WID:ghwealj992:p0p100 — Gini coefficient, wealth
- WID:thwealj992:p90p100 — Wealth threshold, top 10%
- WID:thwealj992:p99p100 — Wealth threshold, top 1%

**Dimension: Income Distribution**
- WID:sptincj992:p99p100 / p90p100 / p0p50 — Pre-tax income shares
- WID:sdiincj992:p99p100 / p90p100 / p0p50 — Post-tax (disposable) income shares
- WID:gptincj992:p0p100 — Gini, pre-tax income
- WID:gdiincj992:p0p100 — Gini, post-tax income
- WID:tdiincj992:p99p100 — Income threshold, top 1%
- WB:SI.POV.GINI — Gini index (World Bank, broader coverage)

**Dimension: Poverty**
- WB:SI.POV.DDAY — ⭐ Extreme poverty headcount ($2.15/day)
- WB:SI.POV.NAHC — National poverty headcount
- WB:SI.POV.GAPS — Poverty gap
- UNDP:mpi — Multidimensional Poverty Index

**Composite scores:** Inequality Score (bottom-50-wealth 40% + wealth-Gini 40% + pre-tax-Gini 20%, higher = worse), Redistribution Score (Gini pre-post delta 60% + post-tax Gini 40%, higher = worse).

### Category: Labour & Employment ✅

**Dimension: Beteiligung (Participation)**
- WB:SL.TLF.CACT.ZS — Labour force participation rate
- ILO:SDG_0852_SEX_AGE_RT — Unemployment rate
- WB:SL.UEM.1524.ZS — Youth unemployment
- WB:SL.UEM.TOTL.MA.ZS / FE.ZS — Unemployment by gender
- WB:SL.UEM.1524.MA.ZS / FE.ZS — Youth unemployment by gender
- ILO:EAP_DWAP_SEX_AGE_RT — Labour force participation rate (ILO)
- WEF:gggi_pes — Gender Gap: Economic Participation subindex (static)

**Dimension: Struktur (Structure)**
- WB:SL.AGR.EMPL.ZS / WB:SL.IND.EMPL.ZS / WB:SL.SRV.EMPL.ZS — Employment by sector
- WB:SL.EMP.SELF.ZS — ⭐ Self-employed (% of employment)
- WB:SL.EMP.WORK.ZS — Wage and salaried workers
- ILO:SDG_0831_SEX_ECO_RT — Informal employment rate
- ILO:ILR_TUMT_NOC_RT — Trade union density (context only, ends 2019)

**Dimension: Arbeitsbedingungen (Working Conditions)** ⚠️ thin, Phase 4 needed
- ILO:EAR_EHRA_SEX_NB — Average hourly earnings
- WB:FP.CPI.TOTL — CPI (for real-wage deflation)
- PWT:avh — Average annual hours worked (context, 130 countries)
- UNDP:gii — Gender Inequality Index
- WEF:gggi_pes — Gender Gap Economic (static)
- **Phase 4 TODO:** minimum wage, social security coverage, direct gender pay gap, ILO Working Conditions Survey, WB Social Protection & Labor (SPL)

### Category: Trade & External Sector ✅

**Dimension: Handelsvolumen (Trade Volume)**
- WB:TG.VAL.TOTL.GD.ZS — ⭐ Merchandise trade (% GDP)
- WB:TX.VAL.MRCH.CD.WT / WB:TM.VAL.MRCH.CD.WT — Merchandise exports/imports (current US$)
- WB:TX.QTY.MRCH.XD.WD / WB:TM.QTY.MRCH.XD.WD — Export/import volume index (2015=100)
- WB:BN.CAB.XOKA.GD.ZS — Current account balance (% GDP)

**Dimension: Handelsstruktur (Trade Structure)**
- WB:TX.MNF.TECH.ZS.UN — ⭐ Medium/high-tech exports (% of manufactured exports)
- Relational: `trade.trade_products` (Comtrade HS-4 product flows, 5.6M+ rows), `trade.trade_partners` (bilateral partners, 997k+ rows)

**Dimension: Tourismus & Remittances (Tourism & Remittances)**
- WB:BX.TRF.PWKR.CD.DT — ⭐ Remittances received (US$)
- WB:BX.TRF.PWKR.DT.GD.ZS — Remittances received (% GDP)
- WB:BM.TRF.PWKR.CD.DT — Remittances paid
- WB:ST.INT.ARVL — Tourist arrivals (ends 2020, COVID)
- WB:ST.INT.RCPT.CD — Tourism receipts (ends 2020)
- WB:BX.GSR.TRVL.ZS / WB:BM.GSR.TRVL.ZS — Travel services export/import share

*No composite score for this category — the Comtrade relational layer doesn't fit the percentile-rank schema, and some indicators have borderline coverage.*

### Category: Public Finance ✅

**Dimension: Public Finance**
- WB:GC.TAX.TOTL.GD.ZS — ⭐ Tax revenue (% GDP)
- WB:GC.XPN.TOTL.GD.ZS — Government expenditure (% GDP)
- WB:GC.DOD.TOTL.GD.ZS — Central government debt (% GDP)
- WB:DT.ODA.ALLD.CD — ⭐ Net ODA received (US$)
- WB:DT.ODA.ODAT.GN.ZS — Net ODA received (% GNI, recipients only)
- WB:DT.ODA.ODAT.PC.ZS — Net ODA per capita
- Known gap: the fiscal core indicators (tax, expenditure, debt) stop around 2007 for several countries including Bolivia; IMF Government Finance Statistics/WEO identified as Phase-4 replacement, not yet loaded

### Category: Energy & Resources 🔧
- Data loaded (resource rents: `WB:NY.GDP.TOTL.RT.ZS`); category assignment vs. Trade/Environment domains still open

### Category: Money & Banking 📋
- Explicitly deferred to Phase 4 — needs IMF IFS or World Bank Financial Development data

---

## 05. Infrastructure & Technology 📋

**~17 indicators — thin, Phase 4.**

### Digital Access
- **Internet & ICT** — WB:IT.NET.USER.ZS, WB:IT.CEL.SETS.P2, WB:IT.NET.BBND.P2, WB:IT.NET.SECR.P6
- **Needs Phase 4 sources:** ITU (telecom infrastructure), IRENA (energy infrastructure), ITF (transport)

---

## 06. Environment, Climate & Resources 📋

**~77 indicators.** Sources: OWID CO2 + Energy (Ember/EI/EIA), FAO Land Use, GBIF, Open-Meteo, WID (environmental inequality). Data-rich but not yet documented with Bolivia/SAM analysis — category structure below is the current planning proposal.

### Climate & Emissions
- **Emissions & Climate** — OWID_CO2:co2, OWID_CO2:co2_per_capita, WB:EN.GHG.ALL.MT.CE.AR5
- **Energy Mix** — EMBER:renewables_share_elec, EMBER:solar_share_elec, EI:fossil_share_energy, EIA:energy_per_capita
- **Air Quality** — WHO:SDGPM25, WB:EN.ATM.PM25.MC.M3

### Land & Ecosystems
- **Land Use** — FAO_LAND:forest_land, FAO_LAND:agricultural_land, WB:AG.LND.FRST.ZS
- **Protected Areas** — WB:ER.LND.PTLD.ZS, WB:ER.PTD.TOTL.ZS

### Biodiversity
- **Species Occurrences** — GBIF:total, GBIF:mammals, GBIF:birds, GBIF:plants
- **Threatened Species** — GBIF:iucn_cr, GBIF:iucn_en, GBIF:iucn_vu

### Water & Weather
- **Climate & Weather** — OPENMETEO:temp_mean, OPENMETEO:precip_sum (ERA5, back to 1940)
- **Water Resources** — WB:ER.H2O.FWST.ZS, WB:ER.H2O.INTR.PC

### Environmental Inequality
- **GHG by Income Group** — WID:lpfghgi999 (p0p50, p90p100, p99p100)

---

## 07. Politics, Governance & Law ✅

**~124 indicators, all 4/4 categories fully documented.** Sources: V-Dem, Freedom House, Polity5, Transparency International, SIPRI, Fragile States Index, GI-TOC, UNODC, UCDP, ACLED, MARPOR, Comparative Constitutions Project, Cline Center (coups).

### Category: Democracy & Elections ✅

**Dimension: Regime & Staatsform (Regime & Statehood)**
- VDEM:v2x_regime — ⭐ Regime type (0=Closed Autocracy, 1=Electoral Autocracy, 2=Electoral Democracy, 3=Liberal Democracy)
- VDEM:v2x_regime_amb — Regime ambiguity (0–6, higher = clearer classification)
- FH:PR / FH:CL — Freedom House Political Rights / Civil Liberties (1–7)
- Relational: `politics.coups` (Cline Center Coup d'État Project — successful/attempted/plotted/alleged coups, auto-coups, forced resignations/exits, 1946–2021)

**Dimension: Regierungssystem-Struktur (Government System Structure)**
- VDEM:v2x_ex_hereditary — Hereditary executive
- VDEM:v2x_ex_military — Military-controlled executive
- VDEM:v2x_ex_party — Party-based executive
- VDEM:v2x_ex_direlect — Direct election of executive
- VDEM:v2x_ex_confidence — Confidence-vote requirement (parliamentary vs. presidential)
- VDEM:v2x_divparctrl — Divided control (executive vs. legislature, z-standardized)
- VDEM:v2x_feduni — Federalism vs. unitarism

**Dimension: Demokratiequalität (Democracy Quality) — VDEM Democracy Wheel**
- VDEM:v2x_polyarchy — ⭐ Electoral democracy
- VDEM:v2x_libdem — Liberal democracy
- VDEM:v2x_partipdem — Participatory democracy
- VDEM:v2x_delibdem — Deliberative democracy
- VDEM:v2x_egaldem — Egalitarian democracy
- `_stock` variants (e.g. VDEM:v2x_polyarchy_stock, VDEM:v2x_libdem_stock) — cumulative institutional experience
- POLITY5:polity2 — Combined democracy score (-10 to +10, ends 2018)

**Dimension: Wahlintegrität (Electoral Integrity)**
- VDEM:v2x_electoral_integrity — ⭐ Overall electoral process quality
- VDEM:v2x_elecreg — Election regularity
- VDEM:v2x_elecoff — Election of chief executive
- VDEM:v2x_suffr — Suffrage (universal voting rights)
- VDEM:v2x_EDcomp_thick — Electoral democracy component (broad composite)
- WB:SG.GEN.PARL.ZS — Women in parliament (%)

**Dimension: Parteiensystem & Wahlergebnisse (Party System & Election Results)** 🚧 open
- VDEM:v2xps_party — Party institutionalization
- VDEM:v2cacamps — Polarization (opposing political camps)
- VDEM:v2psbars — Party ban restrictions
- VDEM:v2psparban — Party ban threshold
- Relational: `politics.marpor_elections`, `politics.political_parties` (MARPOR — thin, only 65/67 country coverage, Bolivia only 2 election years)
- Deliberately not loaded: V-Party (data ends 2019, would miss the entire post-Morales era)
- Under evaluation: WhoGov (leader/party data to 2023), Wikidata P6/P102 (most current but crowdsourced, no built-in left-right score) — see `scripts/experimental/vdem_partysystem_wip.py`

### Category: Rule of Law & Rights ✅

**Dimension: Rule of Law**
- VDEM:v2x_rule — ⭐ Rule of law index
- VDEM:v2x_liberal — Liberal component (rule of law + civil liberties + checks & balances)
- VDEM:v2x_jucon — Judicial constraints on the executive
- VDEM:v2x_horacc — Horizontal accountability (z-standardized)
- VDEM:v2x_veracc — Vertical accountability (z-standardized)
- VDEM:v2x_diagacc — Diagonal accountability (z-standardized)
- VDEM:v2x_accountability — Aggregate accountability index (z-standardized)

**Dimension: Corruption**
- TI:CPI — ⭐ Corruption Perceptions Index (high = clean)
- VDEM:v2x_corr — ⭐ Political corruption (high = corrupt)
- VDEM:v2x_execorr — Executive corruption
- VDEM:v2x_pubcorr — Public sector corruption
- VDEM:v2x_neopat — Neopatrimonialism

**Dimension: Civil Liberties**
- VDEM:v2x_civlib — ⭐ Civil liberties index (aggregate)
- VDEM:v2x_clphy — Physical violence (state violence, torture, disappearance)
- VDEM:v2x_clpol — Political civil liberties (protest, party, opposition)
- VDEM:v2x_clpriv — Private civil liberties (religion, movement, autonomy)

**Dimension: Press & Media Freedom**
- VDEM:v2x_freexp — ⭐ Freedom of expression
- VDEM:v2x_freexp_altinf — Alternative information sources
- RSF:press_freedom — Press Freedom Index (currently loaded only to 2021 via OWID; direct rsf.org load planned)

**Dimension: Gender & Political Equality**
- VDEM:v2x_gender — ⭐ Women's political empowerment (aggregate)
- UNDP:gii — ⭐ Gender Inequality Index (reproductive health + education + labour market)
- VDEM:v2x_gencl — Women's civil liberties
- VDEM:v2x_gencs — Women's civil society participation
- VDEM:v2x_genpp — Women's political participation
- VDEM:v2x_egal — Egalitarian democracy component
- WEF:gggi_ggi — Global Gender Gap Index (outcome-based, static)
- Cross-referenced: WEF gender-indicators also appear in Health, Education, Economy domains

**Dimension: Political Participation**
- VDEM:v2x_partip — ⭐ Participatory democracy
- VDEM:v2x_cspart — Civil society participation
- VDEM:v2x_frassoc_thick — Freedom of association
- VDEM:v2x_api — Academic and cultural freedom
- VDEM:v2x_mpi — Mobilization for power (high = repression/intimidation present)
- Known gap: voter turnout not loaded — IDEA identified as potential source

**Dimension: Constitutional Stability**
- Relational: `politics.constitutional_events` (Comparative Constitutions Project — event types: `new`, `amendment`, `suspension`, `reinstated`)

### Category: Security & Conflict ✅

**Dimension: Armed Conflict**
- Relational: `politics.conflicts_state` (state-based conflicts), `politics.conflicts_nonstate` (non-state armed group violence), `politics.conflicts_onesided` (violence against civilians), `politics.conflict_context` (contextual headline per country-year, derived from UCDP GED raw data)
- UCDP:ged_deaths_total / UCDP:ged_deaths_civilians / UCDP:ged_events — aggregated time series (secondary to the relational tables)

**Dimension: Organized Crime** — GI-TOC Global Organized Crime Index (3 waves: 2021, 2023, 2025; scale 1–10)
- GITOC:criminality — ⭐ Aggregate criminality score
- GITOC:resilience — ⭐ Aggregate resilience score
- GITOC:cocaine / heroin / cannabis / synthetic_drugs — Drug market scores
- GITOC:arms_trafficking / human_trafficking / human_smuggling / financial_crimes — Other criminal market scores
- GITOC:criminal_markets — Markets pillar aggregate
- GITOC:mafia / state_actors — Criminal actor type scores
- GITOC:criminal_actors — Actors pillar aggregate
- GITOC:governance / law_enforcement / aml — Resilience sub-components (political leadership, law enforcement, anti-money-laundering)

**Dimension: Homicide & Crime**
- UNODC:homicide_rate — ⭐ Homicides per 100,000 population
- UNODC:homicide_count — Absolute homicide count (context only, not for cross-country comparison)
- UNODC:prison_occupancy — ⭐ Prison occupancy (% of official capacity)
- UNODC:prison_rate — Prison population per 100,000

**Dimension: Political Violence** — ACLED (Armed Conflict Location & Event Data), regional coverage staggered (Africa 1997 → Americas 2018 → Western Europe 2020)
- ACLED:political_violence_events — ⭐ Battles + explosions/remote violence + violence against civilians
- ACLED:fatalities — ⭐ Deaths from the above
- ACLED:demonstration_events — Protests + riots
- ACLED:civilian_targeting_events — Events targeting civilians
- ACLED:civilian_fatalities — Deaths from civilian-targeting events
- Known gap: granular event-level context (ACLED `Notes` column) not yet loaded, unlike the analogous UCDP `conflict_context`

### Category: State Capacity & Institutions ✅

**Dimension: Government Effectiveness** — World Bank Worldwide Governance Indicators (WGI), 1996–2023
- WB:GE.EST — ⭐ Government effectiveness
- WB:RQ.EST — ⭐ Regulatory quality
- WB:PV.EST — Political stability (absence of violence)
- WB:VA.EST — Voice and accountability

**Dimension: Military & Defence**
- SIPRI:milex_gdp — ⭐ Military expenditure (% GDP)
- WB:MS.MIL.XPND.GD.ZS — Military expenditure (% GDP, World Bank series)
- WB:MS.MIL.XPND.CD — Military expenditure (current US$)

**Dimension: State Fragility**
- FSI:total — Fragile States Index, aggregate score only (0–120 scale; the 12 sub-components are deliberately not loaded as separate indicators — they overlap with Economy, Rule of Law & Rights, Security & Conflict, and Population categories already documented elsewhere)

---

## 08. Culture, Society & Beliefs 📋

**~99 indicators.** Sources: World Values Survey, Hofstede, World Happiness Report, Pew Research, UNESCO (WHC+ICH), Nobel Prize, IMDb, Glottolog, CAF World Giving Index, Edelman Trust Barometer. Data-rich, documentation not yet started.

### Identity & Values
- **Cultural Dimensions** — HOFSTEDE:idv, HOFSTEDE:pdi, HOFSTEDE:mas (+ 3 more)
- **Values Survey** — WVS aggregated country-level indicators
- **Languages** — GLOTTOLOG:n_languages, GLOTTOLOG:n_families, GLOTTOLOG:ldi

### Religion & Belief
- **Religious Composition** — PEW_REL:christians, PEW_REL:muslims, PEW_REL:unaffiliated (+ others), PEW_REL:rdi (Religious Diversity Index)

### Cultural Production
- **Recognition & Media** — NOBEL prizes by country, IMDB:film/TV data, OLY (Olympics medals)

### Heritage & Memory
- **World Heritage** — UNESCO_WHC (sites), UNESCO_ICH (intangible heritage)

### Trust & Wellbeing
- **Trust** — EDELMAN:trust_business/government/media/ngo (9 segments × 4 institutions)
- **Wellbeing** — WHR (World Happiness Report)
- **Giving** — CAF_WGI (World Giving Index)

---

## 09. History & Collective Memory 📋

**~10 indicators — stub, but strong niche sources.** Long time depth: Maddison (year 1–2022), COW (1816+), CCP (1789+), COLDAT.

### Economic History
- **Historical GDP/Population** — MADDISON:gdppc, MADDISON:pop (year 1 to 2022)

### Colonial Legacy
- **Relational:** `international.colonial_history` (COLDAT, 160 relationships)

### Conflict & War
- **Interstate Conflict** — COW:war_count, COW:battle_deaths
- Note: overlaps conceptually with Politics/Security & Conflict (UCDP) — historical COW data (pre-1946) is the distinguishing value here

### State & Sovereignty
- **Relational:** `politics.coups`, `politics.constitutional_events`
- **Ethnic Composition** — EPR:n_groups, EPR:discriminated_share, EPR:excluded_share; relational `history.ethnic_groups` (1946–2023)

---

## 10. International Relations & Global Integration 🔧

**~38 indicators, concept fully defined, Encyclopedia documentation not started.** The project's most unique data: no standard portfolio has ATOP + UNGA voting + COW IGO together.

### Diplomatic Alignment
- **UN Voting** (16 indicators) — UNVOTE:yes_share, UNVOTE:agree_usa, UNVOTE:agree_rus, UNVOTE:agree_chn, UNVOTE:agree_eu, UNVOTE:agree_brics, UNVOTE:minority_share + thematic (disarmament, human rights, Palestine, decolonization, environment)

### Security Alliances
- **Military Alliances** (6 indicators) — ATOP:n_alliances, ATOP:has_defense, ATOP:has_offense, ATOP:has_neutral, ATOP:has_nonagg, ATOP:has_consul

### Multilateral Integration
- **IGO Membership** (3 indicators) — IGO:n_memberships, IGO:n_full, IGO:n_observer

### Globalisation
- **Globalisation Index** (9 indicators) — KOF:gi, KOF:ecgi, KOF:trgi, KOF:figi, KOF:sogi, KOF:pogi, KOF:cugi, KOF:ingi, KOF:ipgi
- **Passport Freedom** (4 indicators) — HENLEY:visa_free_total, HENLEY:visa_required, HENLEY:evisa, HENLEY:visa_on_arrival

### Diplomatic Representation — not yet assigned to a category
- **Relational, not in indicator_metadata:** `international.diplomatic_relations` (DASID, 1985–2019, 1.2M dyadic rows), `international.diplomatic_representation` (DDR, 1960–2024, 433k rows — embassies sent/received per country)
- Open decision: own 5th category, or folded into Diplomatic Alignment as a second dimension

---

## Summary Table

| # | Domain | Indicators | Category Status |
|---|--------|-----------|------------------|
| 01 | Population & Demographics | ~84 | ✅ Confirmed |
| 02 | Health & Survival | ~121 | 📋 Planned |
| 03 | Education, Science & Innovation | ~10 | 📋 Planned (thin) |
| 04 | Economy, Wealth & Labor | ~145 | ✅ Confirmed (5/7) |
| 05 | Infrastructure & Technology | ~17 | 📋 Planned (thin) |
| 06 | Environment, Climate & Resources | ~77 | 📋 Planned |
| 07 | Politics, Governance & Law | ~124 | ✅ Confirmed |
| 08 | Culture, Society & Beliefs | ~99 | 📋 Planned |
| 09 | History & Collective Memory | ~10 | 📋 Planned (stub) |
| 10 | International Relations & Global Integration | ~38 | 🔧 Concept confirmed, docs pending |
| | **Total** | **~725** | |

**Strategic read (unchanged since the June planning pass):** for a showcase portfolio, Economy, Politics, and International Relations are the strongest cards — depth *and* niche sources no standard portfolio has. Education and Infrastructure are honestly thin and stay labeled Phase 4 rather than being padded out.
