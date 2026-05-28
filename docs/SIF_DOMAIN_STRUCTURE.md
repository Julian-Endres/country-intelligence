# SIF Domain Structure – Full 4-Level Hierarchy

**Stand:** 2026-05-28  
**Ebenen:** Domain → Category → Dimension → Indicator (Beispiele)

---

## 1. Population & Demographics

### Fertility
- **Fertility Rate** — WB:SP.DYN.TFRT.IN, WB:SP.DYN.CBRT.IN

### Migration
- **Migration** — WB:SM.POP.NETM, WB:SM.POP.TOTL.ZS, UNDP:...

### Population
- **Population** — WB:SP.POP.TOTL, WB:SP.POP.GROW, WB:SP.POP.0014.ZS

### Urbanization
- **Urbanization** — WB:SP.URB.TOTL.IN.ZS, WB:SP.URB.GROW, WB:EN.POP.DNST

---

## 2. Health, Body & Behavior

### Disease & Burden
- **Disease & Epidemics** — WHO:WHS3_62, WHO:TB_c_newinc, WB:SH.TBS.INCD, WB:SH.HIV.INCD.ZS
- **Mental Health** — (IHME GBD planned)

### Environment & WASH
- **WASH** — WHO:WSH_WATER_BASIC, WHO:WSH_SANITATION_BASIC, WB:SH.H2O.BASW.ZS

### Health System
- **Healthcare System** — WHO:UHC_INDEX_REPORTED, WB:SH.MED.PHYS.ZS, WB:SH.XPD.CHEX.GD.ZS
- **Immunization** — WB:SH.IMM.MEAS, WB:SH.IMM.IDPT

### Nutrition & Food
- **Nutrition & Food Security** — WHO:NCD_BMI_30A, WHO:NCD_BMI_18A, GHI:ghi_score, WB:SN.ITK.DEFC.ZS

### Risk Behavior
- **Reproductive Health** — WHO:MDG_0000000003, WB:SH.STA.MMRT
- **Substance Use** — WHO:NCD_PAA, WB:SH.ALC.PCAP.LI

### Survival & Mortality
- **Child Health** — WB:SH.STA.STNT.ME.ZS, GHI:stunting, GHI:wasting
- **Mortality & Life Expectancy** — WB:SP.DYN.LE00.IN, WB:SH.DYN.MORT, UNDP:le

---

## 3. Politics & Governance

### Democracy & Elections
- **Civil & Political Rights** — FH:PR, FH:CL
- **Democracy & Regime** — VDEM:v2x_polyarchy, VDEM:v2x_libdem, POLITY5:polity2
- **Electoral Integrity** — VDEM:v2x_elecreg, WB:SG.GEN.PARL.ZS
- **Political Participation** — VDEM:v2x_partip, VDEM:v2x_cspart

### Political Economy
- **Aid & Development Finance** — WB:DT.ODA.ALLD.CD, WB:DT.ODA.ODAT.GN.ZS

### Rule of Law & Rights
- **Civil Liberties** — VDEM:v2x_civlib, VDEM:v2x_freexp
- **Corruption** — TI:CPI, WB:CC.EST, VDEM:v2x_corr
- **Gender & Political Equality** — VDEM:v2x_gender, VDEM:v2x_egal
- **Rule of Law** — WB:RL.EST, VDEM:v2x_jucon, WB:VA.EST

### Security & Conflict
- **Homicide & Crime** — UNODC:homicide_rate
- **Organized Crime** — GITOC:overall_score

### State Capacity & Institutions
- **Executive Power** — VDEM:v2x_execonst, VDEM:v2xcs_ccsi
- **Government Effectiveness** — WB:GE.EST, WB:RQ.EST, WB:PV.EST
- **Military & Defence** — SIPRI:milex_gdp, WB:MS.MIL.XPND.GD.ZS
- **Press Freedom** — RSF:score, RSF:rank
- **State Fragility** — FSI:total, FSI:c1_security, FSI:p1_state_legitimacy

---

## 4. Culture & Identity

### Cultural Production
- **Film & TV** — IMDB:movies, IMDB:tvseries, IMDB:total
- **Science & Achievement** — NOBEL:total, NOBEL:lit, NOBEL:pea
- **Sport** — (Olympics planned)

### Heritage & Memory
- **Cultural Heritage** — UNESCO_WHC:total, UNESCO_ICH:total, UNESCO_ICH:rep_list

### Identity & Values
- **Cultural Dimensions** — HOFSTEDE:pdi, HOFSTEDE:idv, HOFSTEDE:mas, HOFSTEDE:uai, HOFSTEDE:lto, HOFSTEDE:ind
- **Values & Attitudes** — WVS:importance_family, WVS:interpersonal_trust, WVS:homosexuality_justifiable

### Religion & Belief
- **Religion** — PEW_REL:christians, PEW_REL:muslims, PEW_REL:unaffiliated, PEW_REL:rdi

---

## 5. Economy & Infrastructure

### Economic Structure
- **Investment & Capital** — WB:NE.GDI.TOTL.ZS, WB:BX.KLT.DINV.CD.WD
- **Sectoral Composition** — WB:NV.AGR.TOTL.ZS, WB:NV.IND.TOTL.ZS, WB:NV.SRV.TOTL.ZS
- **Tourism & Remittances** — WB:ST.INT.ARVL, WB:BX.TRF.PWKR.CD.DT
- **Trade** — WB:TG.VAL.TOTL.GD.ZS, WB:TX.VAL.MRCH.CD.WT, WB:TM.VAL.MRCH.CD.WT

### Human Development
- **Human Development** — UNDP:hdi, UNDP:gii, UNDP:gnipc, UNDP:mpi

### Labour & Employment
- **Employment Structure** — WB:SL.AGR.EMPL.ZS, WB:SL.SRV.EMPL.ZS, ILO:EMP_2EMP_SEX_STE_NB
- **Labour Market** — WB:SL.TLF.CACT.ZS, ILO:SDG_0852_SEX_AGE_RT, ILO:SDG_0831_SEX_ECO_RT
- **Wages & Hours** — ILO:EAR_EHRA_SEX_NB, ILO:HOW_2TOT_SEX_NB, PWT:avh

### Output & Growth
- **GDP & Growth** — WB:NY.GDP.MKTP.CD, WB:NY.GDP.PCAP.CD, PWT:rgdpe
- **Inflation & Prices** — WB:FP.CPI.TOTL.ZG, WB:NY.GDP.DEFL.KD.ZG
- **National Accounts** — PWT:csh_c, PWT:csh_g, PWT:labsh, PWT:irr

### Public Finance & Energy
- **Energy & Electricity** — WB:EG.ELC.ACCS.ZS, WB:EG.ELC.RNEW.ZS, EIA:energy_per_capita
- **Government Finance** — WB:GC.TAX.TOTL.GD.ZS, WB:GC.DOD.TOTL.GD.ZS, WB:DT.ODA.ALLD.CD
- **Infrastructure** — WB:LP.LPI.OVRL.XQ, WB:IS.AIR.PSGR, WB:IS.RRS.TOTL.KM, WB:IS.SHP.GCNW.XQ

### Wealth & Inequality
- **Income Distribution** — WB:SI.POV.GINI, WID:gdiincj992:p0p100, WID:sptincj992:p0p50, WID:sptincj992:p90p100
- **Poverty** — WB:SI.POV.DDAY, WB:SI.POV.NAHC, WB:poverty_3_day
- **Wealth Distribution** — WID:ghwealj992:p0p100, WID:shwealj992:p0p50, WID:shwealj992:p90p100

---

## 6. Social Fabric & Daily Life

### Basic Services
- **WASH** — WHO:WSH_WATER_BASIC, WHO:WSH_SANITATION_BASIC

### Civic Life
- **Civic Engagement & Giving** — CAF_WGI:total_score, CAF_WGI:donating_money, CAF_WGI:volunteering_time

### Trust & Institutions
- **Institutional Trust** — EDELMAN:trust_government:total, EDELMAN:trust_media:total, EDELMAN:trust_business:total

### Wellbeing
- **Wellbeing & Happiness** — WHR:life_evaluation, WHR:social_support, WHR:freedom, WHR:generosity

---

## 7. Communication & Media

### Digital Access
- **Internet & ICT** — WB:IT.NET.USER.ZS, WB:IT.CEL.SETS.P2, WB:IT.NET.BBND.P2, WB:IT.NET.SECR.P6
- **Literacy** — WB:SE.ADT.LITR.ZS

### Press & Media Freedom
- **Press Freedom** — RSF:press_freedom

---

## 8. Geography & Environment

### Biodiversity
- **Species Occurrences** — GBIF:total, GBIF:mammals, GBIF:birds, GBIF:plants
- **Threatened Species** — GBIF:iucn_cr, GBIF:iucn_en, GBIF:iucn_vu

### Climate & Emissions
- **Air Quality** — WHO:SDGPM25, WB:EN.ATM.PM25.MC.M3
- **Emissions & Climate** — OWID_CO2:co2, OWID_CO2:co2_per_capita, WB:EN.GHG.ALL.MT.CE.AR5
  - Energy mix: EMBER:renewables_share_energy, EMBER:solar_share_elec, EI:fossil_share_energy

### Environmental Inequality
- **GHG by Income Group** — WID:lpfghgi999:p0p50, WID:lpfghgi999:p90p100, WID:lpfghgi999:p99p100

### Land & Ecosystems
- **Biodiversity & Protection** — WB:ER.LND.PTLD.ZS, WB:ER.PTD.TOTL.ZS
- **Land Use** — FAO_LAND:forest_land, FAO_LAND:agricultural_land, WB:AG.LND.FRST.ZS

### Water & Weather
- **Climate & Weather** — OPENMETEO:temp_mean, OPENMETEO:precip_sum
- **Water Resources** — WB:ER.H2O.FWST.ZS, WB:ER.H2O.INTR.PC

---

## 9. History & Collective Memory

### Conflict & War
- **Interstate Conflict** — COW:interstate_wars, COW:battle_deaths

### Economic History
- **Historical Economy** — MADDISON:gdppc, MADDISON:pop

### Ethnicity & Peoples
- **Ethnic Composition** — EPR:n_groups, EPR:discriminated_share, EPR:excluded_share
- Relational: `history.ethnic_groups` — 800+ groups, 1946-2023

### State & Sovereignty
- Relational: `politics.coups` (5.285 events), `politics.constitutional_events`
- Relational: `international.colonial_history` (5.258 entries)

---

## 10. International Relations & Global Integration

⏳ **No indicators yet — needs new sources**

Planned:
- UN Voting Data (Voeten) → voting alignment with blocs
- IGO Membership (COW) → number of memberships, specific orgs
- Alliance Data (ATOP) → military alliances

Available relational data:
- `international.diplomatic_relations` (DASID, 1.2M rows)
- `international.diplomatic_representation` (DDR, 433k rows)
- `trade.trade_partners` (bilateral trade flows)

---

## Summary Table

| Domain | Categories | Dimensions | Approx. Indicators |
|--------|-----------|-----------|-------------------|
| Population & Demographics | 4 | 4 | ~84 |
| Health, Body & Behavior | 6 | 10 | ~103 |
| Politics & Governance | 5 | 14 | ~115 |
| Culture & Identity | 4 | 7 | ~50 |
| Economy & Infrastructure | 6 | 14 | ~165 |
| Social Fabric & Daily Life | 4 | 4 | ~65 |
| Communication & Media | 2 | 3 | ~7 |
| Geography & Environment | 5 | 9 | ~75 |
| History & Collective Memory | 4 | 5 | ~10 |
| International Relations | ⏳ | ⏳ | 0 |
| **TOTAL** | **40** | **70+** | **~674** |
