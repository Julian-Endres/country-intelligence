from fastapi import APIRouter, HTTPException
from api.db import get_connection

router = APIRouter()
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
        )
        SELECT
            ROUND(cv.current_value::numeric, 3) AS value,
            ROUND(((cv.current_value - s.hist_avg) / NULLIF(s.hist_std, 0))::numeric, 2) AS z_score,
            ROUND(s.trend_long::numeric, 4) AS trend_long,
            ROUND(r.trend_short::numeric, 4) AS trend_short,
            CASE
                WHEN r.trend_short > 0.01  THEN 'improving'
                WHEN r.trend_short < -0.01 THEN 'declining'
                ELSE 'stable'
            END AS trend_label,
            gr.rank AS global_rank,
            rr.rank AS regional_rank,
            cv.year AS latest_year
        FROM current_val cv, stats s, recent r, global_rank gr, regional_rank rr
    """, (iso_code, indicator_code, indicator_code, indicator_code, indicator_code, iso_code, indicator_code))

    row = cur.fetchone()
    if not row:
        return None

    return {
        "value": float(row[0]) if row[0] else None,
        "z_score": float(row[1]) if row[1] else None,
        "trend_long": float(row[2]) if row[2] else None,
        "trend_short": float(row[3]) if row[3] else None,
        "trend_label": row[4],
        "global_rank": row[5],
        "regional_rank": row[6],
        "latest_year": row[7]
    }


@router.get("/country/{iso_code}")
def get_country(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, iso_code_3, iso_code_2, region, subregion,
               capital, latitude, longitude, area_km2,
               is_landlocked, flag_url
        FROM countries
        WHERE iso_code_3 = %s
    """, (iso_code.upper(),))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Country not found")

    return {
        "name": row[0],
        "iso_code_3": row[1],
        "iso_code_2": row[2],
        "region": row[3],
        "subregion": row[4],
        "capital": row[5],
        "latitude": row[6],
        "longitude": row[7],
        "area_km2": row[8],
        "is_landlocked": row[9],
        "flag_url": row[10]
    }

@router.get("/country/{iso_code}/demography")
def get_demography(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            im.dimension,
            im.indicator_code,
            im.name,
            i.time_period,
            i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s
        AND im.domain = 'Population & Demographics'
        AND i.time_period = (
            SELECT MAX(i2.time_period)
            FROM indicators i2
            WHERE i2.indicator_code = i.indicator_code
            AND i2.iso_numeric = i.iso_numeric
        )
        ORDER BY im.dimension, im.name
    """, (iso_code.upper(),))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No demography data found")

    result = {}
    for dimension, indicator_code, name, year, value in rows:
        if dimension not in result:
            result[dimension] = []
        result[dimension].append({
            "indicator": indicator_code,
            "name": name,
            "year": year,
            "value": round(value, 2) if value else None
        })

    return {
        "country": iso_code.upper(),
        "domain": "Population & Demographics",
        "data": result
    }

@router.get("/country/{iso_code}/governance")
def get_governance(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()

    # Summary für Key Indicator
    summary = get_indicator_summary(cur, iso_code.upper(), "VDEM:v2x_polyarchy")

    # Detail - alle Governance Indikatoren
    cur.execute("""
        SELECT im.dimension, im.indicator_code, im.name, im.unit, i.time_period, i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s
        AND im.domain = 'Politics & Governance'
        AND i.time_period = (
            SELECT MAX(i2.time_period) FROM indicators i2
            WHERE i2.indicator_code = i.indicator_code
            AND i2.iso_numeric = i.iso_numeric
        )
        ORDER BY im.dimension, im.name
    """, (iso_code.upper(),))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No governance data found")

    detail = {}
    for dimension, indicator_code, name, unit, year, value in rows:
        if dimension not in detail:
            detail[dimension] = []
        detail[dimension].append({
            "indicator": indicator_code,
            "name": name,
            "unit": unit,
            "year": year,
            "value": round(float(value), 4) if value else None
        })

    return {
        "country": iso_code.upper(),
        "domain": "Politics & Governance",
        "summary": summary,
        "detail": detail
    }

@router.get("/country/{iso_code}/economy")
def get_economy(iso_code: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            im.dimension,
            im.indicator_code,
            im.name,
            im.unit,
            i.time_period,
            i.value
        FROM indicators i
        JOIN indicator_metadata im ON i.indicator_code = im.indicator_code
        JOIN countries c ON i.iso_numeric = c.iso_numeric
        WHERE c.iso_code_3 = %s
        AND im.domain = 'Economy & Infrastructure'
        AND i.time_period = (
            SELECT MAX(i2.time_period)
            FROM indicators i2
            WHERE i2.indicator_code = i.indicator_code
            AND i2.iso_numeric = i.iso_numeric
        )
        ORDER BY im.dimension, im.name
    """, (iso_code.upper(),))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No economy data found")

    result = {}
    for dimension, indicator_code, name, unit, year, value in rows:
        if dimension not in result:
            result[dimension] = []
        result[dimension].append({
            "indicator": indicator_code,
            "name": name,
            "unit": unit,
            "year": year,
            "value": round(value, 2) if value else None
        })

    return {
        "country": iso_code.upper(),
        "domain": "Economy & Infrastructure",
        "data": result
    }