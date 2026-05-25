from fastapi import APIRouter, HTTPException
from api.db import get_connection

router = APIRouter()

# ─── Indicator Types ──────────────────────────────────────────────────────────
# neutral:  increasing / stable / decreasing (no value judgment)
# flow:     net_inflow / balanced / net_outflow (value itself shows direction)
# positive: improving / stable / declining (higher = better)
# negative: improving / stable / declining (lower = better)

INDICATOR_TYPES = {
    # Population
    "WB:SP.POP.TOTL":           "neutral",
    "WB:SP.POP.GROW":           "neutral",
    "WB:SP.POP.TOTL.FE.ZS":     "neutral",
    "WB:SP.POP.TOTL.MA.ZS":     "neutral",
    "WB:SP.POP.TOTL.FE.IN":     "neutral",
    "WB:SP.POP.TOTL.MA.IN":     "neutral",
    "WB:EN.POP.DNST":           "neutral",
    "WB:SP.POP.DPND":           "neutral",
    "WB:SP.POP.DPND.YG":        "neutral",
    "WB:SP.POP.DPND.OL":        "neutral",
    "WB:SP.POP.0014.TO.ZS":     "neutral",
    "WB:SP.POP.1564.TO.ZS":     "neutral",
    "WB:SP.POP.65UP.TO.ZS":     "neutral",
    "WB:SP.POP.BRTH.MF":        "neutral",
    # Fertility
    "WB:SP.DYN.TFRT.IN":        "neutral",
    "WB:SP.DYN.CBRT.IN":        "neutral",
    "WB:SP.DYN.CDRT.IN":        "neutral",
    "WB:SP.ADO.TFRT":           "neutral",
    # Migration
    "WB:SM.POP.NETM":           "flow",
    "WB:SM.POP.TOTL":           "neutral",
    "WB:SM.POP.TOTL.ZS":        "neutral",
    "WB:SM.POP.RHCR.EO":        "neutral",
    "WB:SM.POP.RHCR.EA":        "neutral",
    # Urbanization
    "WB:SP.URB.TOTL.IN.ZS":     "neutral",
    "WB:SP.URB.GROW":           "neutral",
    "WB:SP.URB.TOTL":           "neutral",
    "WB:SP.RUR.TOTL.ZS":        "neutral",
    "WB:SP.RUR.TOTL.ZG":        "neutral",
    "WB:SP.RUR.TOTL":           "neutral",
    "WB:EN.POP.SLUM.UR.ZS":     "neutral",
    # Economy
    "WB:NY.GDP.PCAP.CD":        "positive",
    "WB:NY.GDP.MKTP.CD":        "positive",
    "WB:SL.UEM.TOTL.ZS":        "negative",
    "WB:FP.CPI.TOTL.ZG":        "negative",
    # Health
    "WB:SP.DYN.LE00.IN":        "positive",
    "WB:SP.DYN.IMRT.IN":        "negative",
    "WB:SH.DYN.MORT":           "negative",
    "WB:SH.STA.MMRT":           "negative",
    # Governance
    "VDEM:v2x_polyarchy":       "positive",
    "FH:PR":                    "negative",
    "FH:CL":                    "negative",
    "CPI:score":                "positive",
}

def get_trend_label(indicator_code: str, trend_short: float, current_value: float = None) -> str:
    """Gibt das korrekte Trend-Label basierend auf Indikator-Typ zurück."""
    if trend_short is None:
        return "unknown"

    itype = INDICATOR_TYPES.get(indicator_code, "neutral")
    threshold = 0.01

    if itype == "flow":
        # Wert selbst zeigt Richtung, Trend zeigt Stärke
        if current_value is not None:
            direction = "net_inflow" if current_value > 0 else "net_outflow" if current_value < 0 else "balanced"
        else:
            direction = "balanced"
        if abs(trend_short) > threshold:
            momentum = "accelerating" if trend_short > 0 else "decelerating"
            return f"{direction} ({momentum})"
        return direction

    elif itype == "neutral":
        if trend_short > threshold:
            return "increasing"
        elif trend_short < -threshold:
            return "decreasing"
        return "stable"

    elif itype == "positive":
        if trend_short > threshold:
            return "improving"
        elif trend_short < -threshold:
            return "declining"
        return "stable"

    elif itype == "negative":
        # Für negative Indikatoren ist sinkender Trend gut
        if trend_short < -threshold:
            return "improving"
        elif trend_short > threshold:
            return "declining"
        return "stable"

    return "stable"


# ─── Demography Config ────────────────────────────────────────────────────────

DEMOGRAPHY_CATEGORIES = {
    "population": {
        "label": "Population Structure",
        "key_indicator": "WB:SP.POP.TOTL",
        "indicators": [
            "WB:SP.POP.TOTL",
            "WB:SP.POP.GROW",
            "WB:SP.POP.TOTL.FE.ZS",
            "WB:SP.POP.BRTH.MF",
            "WB:EN.POP.DNST",
            "WB:SP.POP.DPND",
            "WB:SP.POP.DPND.YG",
            "WB:SP.POP.DPND.OL",
            "WB:SP.POP.0014.TO.ZS",
            "WB:SP.POP.1564.TO.ZS",
            "WB:SP.POP.65UP.TO.ZS",
        ]
    },
    "fertility": {
        "label": "Fertility & Natural Movement",
        "key_indicator": "WB:SP.DYN.TFRT.IN",
        "indicators": [
            "WB:SP.DYN.TFRT.IN",
            "WB:SP.DYN.CBRT.IN",
            "WB:SP.DYN.CDRT.IN",
            "WB:SP.ADO.TFRT",
        ]
    },
    "migration": {
        "label": "Migration",
        "key_indicator": "WB:SM.POP.NETM",
        "indicators": [
            "WB:SM.POP.NETM",
            "WB:SM.POP.TOTL",
            "WB:SM.POP.TOTL.ZS",
            "WB:SM.POP.RHCR.EO",
            "WB:SM.POP.RHCR.EA",
        ]
    },
    "urbanization": {
        "label": "Urbanization",
        "key_indicator": "WB:SP.URB.TOTL.IN.ZS",
        "indicators": [
            "WB:SP.URB.TOTL.IN.ZS",
            "WB:SP.URB.GROW",
            "WB:SP.URB.TOTL",
            "WB:SP.RUR.TOTL.ZS",
            "WB:SP.RUR.TOTL.ZG",
            "WB:EN.POP.SLUM.UR.ZS",
        ]
    },
}

PYRAMID_INDICATORS = [
    "WB:SP.POP.0004.FE.5Y", "WB:SP.POP.0004.MA.5Y",
    "WB:SP.POP.0509.FE.5Y", "WB:SP.POP.0509.MA.5Y",
    "WB:SP.POP.1014.FE.5Y", "WB:SP.POP.1014.MA.5Y",
    "WB:SP.POP.1519.FE.5Y", "WB:SP.POP.1519.MA.5Y",
    "WB:SP.POP.2024.FE.5Y", "WB:SP.POP.2024.MA.5Y",
    "WB:SP.POP.2529.FE.5Y", "WB:SP.POP.2529.MA.5Y",
    "WB:SP.POP.3034.FE.5Y", "WB:SP.POP.3034.MA.5Y",
    "WB:SP.POP.3539.FE.5Y", "WB:SP.POP.3539.MA.5Y",
    "WB:SP.POP.4044.FE.5Y", "WB:SP.POP.4044.MA.5Y",
    "WB:SP.POP.4549.FE.5Y", "WB:SP.POP.4549.MA.5Y",
    "WB:SP.POP.5054.FE.5Y", "WB:SP.POP.5054.MA.5Y",
    "WB:SP.POP.5559.FE.5Y", "WB:SP.POP.5559.MA.5Y",
    "WB:SP.POP.6064.FE.5Y", "WB:SP.POP.6064.MA.5Y",
    "WB:SP.POP.6569.FE.5Y", "WB:SP.POP.6569.MA.5Y",
    "WB:SP.POP.7074.FE.5Y", "WB:SP.POP.7074.MA.5Y",
    "WB:SP.POP.7579.FE.5Y", "WB:SP.POP.7579.MA.5Y",
    "WB:SP.POP.80UP.FE.5Y", "WB:SP.POP.80UP.MA.5Y",
]

# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_indicator_summary(cur, iso_code: str, indicator_code: str):
    cur.execute("""
        WITH all_values AS (
            SELECT i.time_period::int AS year, i.value
            FROM indicators i
            JOIN countries c ON i.iso_numeric = c.iso_numeric
            WHERE c.iso_code_3 = %s AND i.indicator_code = %s
        ),
        stats AS (
            SELECT AVG(value) AS hist_avg, STDDEV(value) AS hist_std,
                   regr_slope(value, year) AS trend_long, COUNT(*) AS n_years
            FROM all_values
        ),
        recent AS (
            SELECT regr_slope(value, year) AS trend_short
            FROM all_values
            WHERE year >= (SELECT MAX(year) - 4 FROM all_values)
        ),
        current_val AS (
            SELECT value AS current_value, year
            FROM all_values
            WHERE year = (SELECT MAX(year) FROM all_values)
        ),
        global_rank AS (
            SELECT COUNT(*) + 1 AS rank
            FROM indicators i2
            JOIN countries c2 ON i2.iso_numeric = c2.iso_numeric
            WHERE i2.indicator_code = %s
            AND i2.time_period = (SELECT MAX(time_period) FROM indicators WHERE indicator_code = %s)
            AND i2.value > (SELECT current_value FROM current_val)
        ),
        regional_rank AS (
            SELECT COUNT(*) + 1 AS rank
            FROM indicators i2
            JOIN countries c2 ON i2.iso_numeric = c2.iso_numeric
            WHERE i2.indicator_code = %s
            AND c2.subregion = (SELECT subregion FROM countries WHERE iso_code_3 = %s)
            AND i2.time_period = (SELECT MAX(time_period) FROM indicators WHERE indicator_code = %s)
            AND i2.value > (SELECT current_value FROM current_val)
        ),
        global_avg AS (
            SELECT AVG(value) AS avg, COUNT(*) AS n_countries
            FROM indicators i2
            WHERE i2.indicator_code = %s
            AND i2.time_period = (SELECT MAX(time_period) FROM indicators WHERE indicator_code = %s)
        )
        SELECT
            ROUND(cv.current_value::numeric, 3),
            ROUND(((cv.current_value - s.hist_avg) / NULLIF(s.hist_std, 0))::numeric, 2),
            ROUND(s.trend_long::numeric, 6),
            ROUND(r.trend_short::numeric, 6),
            gr.rank,
            rr.rank,
            cv.year,
            ROUND(ga.avg::numeric, 3),
            ga.n_countries
        FROM current_val cv, stats s, recent r, global_rank gr, regional_rank rr, global_avg ga
    """, (
        iso_code, indicator_code,
        indicator_code, indicator_code,
        indicator_code, iso_code, indicator_code,
        indicator_code, indicator_code
    ))

    row = cur.fetchone()
    if not row:
        return None

    value = float(row[0]) if row[0] is not None else None
    trend_short = float(row[3]) if row[3] is not None else None

    return {
        "value": value,
        "z_score": float(row[1]) if row[1] is not None else None,
        "trend_long": float(row[2]) if row[2] is not None else None,
        "trend_short": trend_short,
        "trend_label": get_trend_label(indicator_code, trend_short, value),
        "global_rank": row[4],
        "regional_rank": row[5],
        "latest_year": row[6],
        "global_avg": float(row[7]) if row[7] is not None else None,
        "n_countries": row[8],
    }


def get_timeseries(cur, iso_code: str, indicator_code: str):
    cur.execute("""
        SELECT i.time_period::int, i.value
        FROM indicators i
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s AND i.indicator_code = %s
        ORDER BY i.time_period::int ASC
    """, (iso_code, indicator_code))
    rows = cur.fetchall()
    return [{"year": r[0], "value": round(float(r[1]), 4) if r[1] else None} for r in rows]


def get_indicator_meta(cur, indicator_code: str):
    cur.execute("""
        SELECT name, unit, dimension
        FROM indicator_metadata
        WHERE indicator_code = %s
    """, (indicator_code,))
    row = cur.fetchone()
    if not row:
        return {"name": indicator_code, "unit": None, "dimension": None}
    return {"name": row[0], "unit": row[1], "dimension": row[2]}


# ─── Country Overview ─────────────────────────────────────────────────────────

@router.get("/country/{iso_code}")
def get_country(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, iso_code_3, iso_code_2, region, subregion,
               capital, latitude, longitude, area_km2, is_landlocked, flag_url
        FROM countries WHERE iso_code_3 = %s
    """, (iso_code.upper(),))

    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Country not found")

    kpis = {}
    for code in ["WB:SP.POP.TOTL", "WB:NY.GDP.PCAP.CD", "WB:SP.DYN.LE00.IN"]:
        summary = get_indicator_summary(cur, iso_code.upper(), code)
        if summary:
            meta = get_indicator_meta(cur, code)
            kpis[code] = {
                "name": meta["name"],
                "value": summary["value"],
                "unit": meta["unit"],
                "year": summary["latest_year"],
                "trend_label": summary["trend_label"],
                "global_rank": summary["global_rank"],
            }

    cur.close(); conn.close()

    return {
        "name": row[0], "iso_code_3": row[1], "iso_code_2": row[2],
        "region": row[3], "subregion": row[4], "capital": row[5],
        "latitude": row[6], "longitude": row[7], "area_km2": row[8],
        "is_landlocked": row[9], "flag_url": row[10],
        "kpis": kpis,
    }


# ─── Demography: Domain Overview ─────────────────────────────────────────────

@router.get("/country/{iso_code}/demography")
def get_demography_overview(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()

    categories = {}
    for slug, config in DEMOGRAPHY_CATEGORIES.items():
        summary = get_indicator_summary(cur, iso, config["key_indicator"])
        meta = get_indicator_meta(cur, config["key_indicator"])
        categories[slug] = {
            "label": config["label"],
            "key_indicator": config["key_indicator"],
            "key_indicator_name": meta["name"],
            "unit": meta["unit"],
            "summary": summary,
        }

    cur.close(); conn.close()
    return {
        "country": iso,
        "domain": "Population & Demographics",
        "categories": categories,
    }


# ─── Demography: Category Detail ─────────────────────────────────────────────

@router.get("/country/{iso_code}/demography/pyramid")
def get_demography_pyramid(iso_code: str, year: int = None):
    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()

    if not year:
        cur.execute("""
            SELECT MAX(i.time_period::int)
            FROM indicators i
            JOIN countries c ON i.iso_numeric = c.iso_numeric
            WHERE c.iso_code_3 = %s AND i.indicator_code = %s
        """, (iso, PYRAMID_INDICATORS[0]))
        row = cur.fetchone()
        year = row[0] if row and row[0] else 2023

    placeholders = ','.join(['%s'] * len(PYRAMID_INDICATORS))
    cur.execute(f"""
        SELECT im.indicator_code, i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s
        AND i.indicator_code IN ({placeholders})
        AND i.time_period = %s
    """, [iso] + PYRAMID_INDICATORS + [str(year)])

    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No pyramid data for {iso} in {year}")

    data = {r[0]: float(r[1]) if r[1] else 0 for r in rows}
    age_ranges = [
        "0004", "0509", "1014", "1519", "2024", "2529",
        "3034", "3539", "4044", "4549", "5054", "5559",
        "6064", "6569", "7074", "7579", "80UP"
    ]

    age_groups = []
    for age in age_ranges:
        if age == "80UP":
            label = "80+"
        else:
            label = f"{age[:2]}-{age[2:]}"
        age_groups.append({
            "age_group": label,
            "female": data.get(f"WB:SP.POP.{age}.FE.5Y", 0),
            "male": data.get(f"WB:SP.POP.{age}.MA.5Y", 0),
        })

    return {"country": iso, "year": year, "age_groups": age_groups}


@router.get("/country/{iso_code}/demography/{category}")
def get_demography_category(iso_code: str, category: str):
    if category not in DEMOGRAPHY_CATEGORIES:
        raise HTTPException(
            status_code=404,
            detail=f"Category '{category}' not found. Available: {list(DEMOGRAPHY_CATEGORIES.keys())}"
        )

    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()
    config = DEMOGRAPHY_CATEGORIES[category]

    indicators = []
    for code in config["indicators"]:
        meta = get_indicator_meta(cur, code)
        summary = get_indicator_summary(cur, iso, code)
        timeseries = get_timeseries(cur, iso, code)
        if not summary and not timeseries:
            continue
        indicators.append({
            "indicator_code": code,
            "name": meta["name"],
            "unit": meta["unit"],
            "summary": summary,
            "timeseries": timeseries,
        })

    cur.close(); conn.close()

    if not indicators:
        raise HTTPException(status_code=404, detail="No data found")

    return {
        "country": iso,
        "domain": "Population & Demographics",
        "category": category,
        "label": config["label"],
        "indicators": indicators,
    }


# ─── Timeseries ───────────────────────────────────────────────────────────────

@router.get("/country/{iso_code}/timeseries/{indicator_code:path}")
def get_indicator_timeseries(iso_code: str, indicator_code: str):
    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()

    meta = get_indicator_meta(cur, indicator_code)
    summary = get_indicator_summary(cur, iso, indicator_code)
    timeseries = get_timeseries(cur, iso, indicator_code)

    cur.close(); conn.close()

    if not timeseries:
        raise HTTPException(status_code=404, detail="No data found")

    return {
        "country": iso,
        "indicator_code": indicator_code,
        "name": meta["name"],
        "unit": meta["unit"],
        "summary": summary,
        "timeseries": timeseries,
    }


# ─── Governance ───────────────────────────────────────────────────────────────

@router.get("/country/{iso_code}/governance")
def get_governance(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()

    summary = get_indicator_summary(cur, iso, "VDEM:v2x_polyarchy")

    cur.execute("""
        SELECT im.dimension, im.indicator_code, im.name, im.unit, i.time_period, i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s AND im.domain = 'Politics & Governance'
        AND i.time_period = (
            SELECT MAX(i2.time_period) FROM indicators i2
            WHERE i2.indicator_code = i.indicator_code AND i2.iso_numeric = i.iso_numeric
        )
        ORDER BY im.dimension, im.name
    """, (iso,))

    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No governance data found")

    detail = {}
    for dimension, code, name, unit, year, value in rows:
        if dimension not in detail:
            detail[dimension] = []
        detail[dimension].append({
            "indicator": code, "name": name, "unit": unit,
            "year": year, "value": round(float(value), 4) if value else None
        })

    return {"country": iso, "domain": "Politics & Governance", "summary": summary, "detail": detail}


# ─── Economy ──────────────────────────────────────────────────────────────────

@router.get("/country/{iso_code}/economy")
def get_economy(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()
    iso = iso_code.upper()

    summary = get_indicator_summary(cur, iso, "WB:NY.GDP.PCAP.CD")

    cur.execute("""
        SELECT im.dimension, im.indicator_code, im.name, im.unit, i.time_period, i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s AND im.domain = 'Economy & Infrastructure'
        AND i.time_period = (
            SELECT MAX(i2.time_period) FROM indicators i2
            WHERE i2.indicator_code = i.indicator_code AND i2.iso_numeric = i.iso_numeric
        )
        ORDER BY im.dimension, im.name
    """, (iso,))

    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No economy data found")

    detail = {}
    for dimension, code, name, unit, year, value in rows:
        if dimension not in detail:
            detail[dimension] = []
        detail[dimension].append({
            "indicator": code, "name": name, "unit": unit,
            "year": year, "value": round(float(value), 4) if value else None
        })

    return {"country": iso, "domain": "Economy & Infrastructure", "summary": summary, "detail": detail}