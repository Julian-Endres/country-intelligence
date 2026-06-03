# SIF Domain Structure — Full 4-Level Hierarchy

**Last updated:** 2026-06-03
**Levels:** Domain → Category → Dimension → Indicator (examples)

---

## 1. Population & Demographics

### Fertility
- **Fertility Rate** — WB:SP.DYN.TFRT.IN, WB:SP.DYN.CBRT.IN

### Migration
- **Migration** — WB:SM.POP.NETM, WB:SM.POP.TOTL.ZS, UNHCR refugee data

### Population
- **Population** — WB:SP.POP.TOTL, WB:SP.POP.GROW, WB:SP.POP.0014.ZS

### Urbanization
- **Urbanization** — WB:SP.URB.TOTL.IN.ZS, WB:SP.URB.GROW, WB:EN.POP.DNST

---

## 2. Geography & Environment

### Biodiversity
- **Species Occurrences** — GBIF:total, GBIF:mammals, GBIF:birds, GBIF:plants
- **Threatened Species** — GBIF:iucn_cr, GBIF:iucn_en, GBIF:iucn_vu

### Climate & Emissions
- **Air Quality** — WHO:SDGPM25, WB:EN.ATM.PM25.MC.M3
- **Emissions & Climate** — OWID_CO2:co2, OWID_CO2:co2_per_capita, WB:EN.GHG.ALL.MT.CE.AR5
- **Energy Mix** — Ember:renewables_share_elec, Ember:solar_share_elec, EI:fossil_share_energy

### Environmental Inequality
- **GHG by Income Group** — WID:lpfghgi999 (p0p50, p90p100, p99p100)

### Land & Ecosystems
- **Biodiversity & Protection** — WB:ER.LND.PTLD.ZS, WB:ER.PTD.TOTL.ZS
- **Land Use** — FAO_LAND:forest_land, FAO_LAND:agricultural_land, WB:AG.LND.FRST.ZS

### Water & Weather
- **Climate & Weather** — OPENMETEO:temp_mean, OPENMETEO:precip_sum
- **Water Resources** — WB:ER.H2O.FWST.ZS, WB:ER.H2O.INTR.PC

---

## 3. Economy & Infrastructure

### Economic Structure
- **Investment & Capital** — WB:NE.GDI.TOTL.ZS, WB:BX.KLT.DINV.CD.WD
- **Sectoral Composition** — WB:NV.AGR.TOTL.ZS, WB:NV.IND.TOTL.ZS, WB:NV.SRV.TOTL.ZS
- **Tourism & Remittances** — WB:ST.INT.ARVL, WB:BX.TRF.PWKR.CD.DT
- **Trade** — WB:TG.VAL.TOTL.GD.ZS, WB:TX.VAL.MRCH.CD.WT

### Human Development
- **Human Development** — UNDP:hdi, UNDP:gii, UNDP:gnipc, UNDP:mpi

### Labour & Employment
- **Employment Structure** — WB:SL.AGR.EMPL.ZS, ILO:EMP_2EMP_SEX_STE_NB
- **Labour Market** — WB:SL.TLF.CACT.ZS, ILO:SDG_0852_SEX_AGE_RT
- **Wages & Hours** — ILO:EAR_EHRA_SEX_NB, PWT:avh

### Output & Growth
- **GDP & Growth** — WB:NY.GDP.MKTP.CD, WB:NY.GDP.PCAP.CD, PWT:rgdpe
- **Inflation & Prices** — WB:FP.CPI.TOTL.ZG, WB:NY.GDP.DEFL.KD.ZG
- **National Accounts** — PWT:csh_c, PWT:csh_g, PWT:labsh

### Public Finance & Energy
- **Energy & Electricity** — WB:EG.ELC.ACCS.ZS, WB:EG.ELC.RNEW.ZS, EIA:energy_per_capita
- **Government Finance** — WB:GC.TAX.TOTL.GD.ZS, WB:GC.DOD.TOTL.GD.ZS
- **Infrastructure** — WB:LP.LPI.OVRL.XQ, WB:IS.AIR.PSGR, WB:IS.RRS.TOTL.KM

### Wealth & Inequality
- **Income Distribution** — WB:SI.POV.GINI, WID:sptincj992 (p0p50, p90p100)
- **Poverty** — WB:SI.POV.DDAY, WB:SI.POV.NAHC
- **Wealth Distribution** — WID:shwealj992 (p0p50, p90p100)

---

## 4. Politics & Governance

### Democracy & Elections
- **Civil & Political Rights** — FH:political_rights, FH:civil_liberties
- **Democracy & Regime** — VDEM:v2x_polyarchy, VDEM:v2x_libdem, POLITY5:polity2
- **Electoral Integrity** — VDEM:v2x_elecreg, WB:SG.GEN.PARL.ZS
- **Political Participation** — VDEM:v2x_partip, VDEM:v2x_cspart

### Rule of Law & Rights
- **Civil Liberties** — VDEM:v2x_civlib, VDEM:v2x_freexp
- **Corruption** — TI:cpi_score, WB:CC.EST, VDEM:v2x_corr
- **Gender & Political Equality** — VDEM:v2x_gender, WEF_GGGI:political
- **Rule of Law** — WB:RL.EST, VDEM:v2x_jucon, WB:VA.EST

### Security & Conflict
- **Homicide & Crime** — UNODC:homicide_rate
- **Organized Crime** — GITOC:criminality, GITOC:resilience

### State Capacity & Institutions
- **Executive Power** — VDEM:v2x_execonst
- **Government Effectiveness** — WB:GE.EST, WB:RQ.EST, WB:PV.EST
- **Military & Defence** — SIPRI:milex_gdp, WB:MS.MIL.XPND.GD.ZS
- **Press Freedom** — RSF:press_freedom
- **State Fragility** — FSI:total, FSI:c1_security

**Relational:** politics.marpor_elections (5.3k+ elections, 56 policy categories), politics.coups (919), politics.constitutional_events (4.1k)

---

## 5. Culture & Identity

### Cultural Production
- **Film & TV** — IMDB:movies, IMDB:tvseries, IMDB:total
- **Science & Achievement** — NOBEL:total, NOBEL:lit, NOBEL:pea
- **Food Culture** — CULTURE:has_national_dish (relational: culture.national_dishes)

### Heritage & Memory
- **Cultural Heritage** — UNESCO_WHC:total, UNESCO_ICH:total, UNESCO_ICH:rl

### Identity & Values
- **Cultural Dimensions** — HOFSTEDE:pdi, HOFSTEDE:idv, HOFSTEDE:mas, HOFSTEDE:uai, HOFSTEDE:lto, HOFSTEDE:ivr
- **Language Diversity** — GLOTTOLOG:ldi, GLOTTOLOG:n_languages, GLOTTOLOG:n_families
- **Values & Attitudes** — WVS:trust_people, WVS:importance_family

### Religion & Belief
- **Religion** — PEW_REL:christians, PEW_REL:muslims, PEW_REL:unaffiliated, PEW_REL:rdi

---

## 6. Social Fabric & Daily Life

### Basic Services
- **WASH** — WHO:WSH_WATER_BASIC, WHO:WSH_SANITATION_BASIC

### Civic Life
- **Civic Engagement & Giving** — CAF_WGI:total_score, CAF_WGI:donating_money, CAF_WGI:volunteering_time

### Trust & Institutions
- **Institutional Trust** — EDELMAN:government_general, EDELMAN:media_general, EDELMAN:business_general

### Wellbeing
- **Wellbeing & Happiness** — WHR:ladder_score, WHR:social_support, WHR:freedom, WHR:generosity

---

## 7. Communication & Media

### Digital Access
- **Internet & ICT** — WB:IT.NET.USER.ZS, WB:IT.CEL.SETS.P2, WB:IT.NET.BBND.P2, WB:IT.NET.SECR.P6
- **Literacy** — WB:SE.ADT.LITR.ZS

### Press & Media Freedom
- **Press Freedom** — RSF:press_freedom

*Note: thinnest domain. Planned: Reuters Digital News Report, ITU DataHub.*

---

## 8. Health, Body & Behavior

### Disease & Burden
- **Disease & Epidemics** — WHO:WHS3_62, WB:SH.TBS.INCD, WB:SH.HIV.INCD.ZS
- **Mental Health** — (IHME GBD planned)

### Environment & WASH
- **WASH** — WHO:WSH_WATER_BASIC, WB:SH.H2O.BASW.ZS

### Health System
- **Healthcare System** — WHO:UHC_INDEX_REPORTED, WB:SH.MED.PHYS.ZS, WB:SH.XPD.CHEX.GD.ZS
- **Immunization** — WB:SH.IMM.MEAS, WB:SH.IMM.IDPT

### Nutrition & Food
- **Nutrition & Food Security** — WHO:NCD_BMI_30A, GHI:ghi_score, FAO_FOOD:energy_kcal, FAO_FOOD_GRP:*

### Risk Behavior
- **Reproductive Health** — WHO:MDG_0000000003, WB:SH.STA.MMRT
- **Substance Use** — WHO:NCD_PAA, WB:SH.ALC.PCAP.LI

### Survival & Mortality
- **Child Health** — WB:SH.STA.STNT.ME.ZS, GHI:stunting, GHI:wasting
- **Mortality & Life Expectancy** — WB:SP.DYN.LE00.IN, WB:SH.DYN.MORT, UNDP:le

---

## 9. History & Collective Memory

### Conflict & War
- **Interstate Conflict** — COW:war_count, COW:battle_deaths

### Economic History
- **Historical Economy** — MADDISON:gdppc, MADDISON:pop

### Ethnicity & Peoples
- **Ethnic Composition** — EPR:n_groups, EPR:discriminated_share, EPR:excluded_share
- **Relational:** history.ethnic_groups (32.5k rows, 1946–2023)

### State & Sovereignty
- **Relational:** politics.coups, politics.constitutional_events, international.colonial_history

---

## 10. International Relations & Global Integration

### Diplomatic Alignment
- **UN Voting** — UNVOTE:yes_share, UNVOTE:agree_usa, UNVOTE:agree_rus, UNVOTE:agree_chn, UNVOTE:agree_eu, UNVOTE:agree_brics, UNVOTE:minority_share + thematic (disarmament, human rights, Palestine, decolonize, environment)

### Globalisation
- **Globalisation Index** — KOF:gi, KOF:ecgi, KOF:sogi, KOF:pogi (+ 5 more)
- **Passport Freedom** — HENLEY:visa_free

### Multilateral Integration
- **IGO Membership** — IGO:n_memberships

### Security Alliances
- **Military Alliances** — ATOP:n_alliances, ATOP:has_defense, ATOP:has_offense, ATOP:has_neutral, ATOP:has_nonagg, ATOP:has_consul

**Relational:** international.diplomatic_relations (DASID, 1.2M), international.diplomatic_representation (DDR, 433k), trade.trade_partners (bilateral flows)

---

## Summary Table

| Domain | Categories | Dimensions | Approx. Indicators |
|--------|-----------|-----------|-------------------|
| Population & Demographics | 4 | 4 | ~84 |
| Geography & Environment | 5 | 9 | ~75 |
| Economy & Infrastructure | 6 | 14 | ~165 |
| Politics & Governance | 4 | 14 | ~115 |
| Culture & Identity | 4 | 8 | ~55 |
| Social Fabric & Daily Life | 4 | 4 | ~49 |
| Communication & Media | 2 | 3 | ~7 |
| Health, Body & Behavior | 6 | 10 | ~103 |
| History & Collective Memory | 4 | 5 | ~10 |
| International Relations | 4 | 5 | ~38 |
| **TOTAL** | **43** | **76+** | **~700** |
