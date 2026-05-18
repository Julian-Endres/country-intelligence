import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Project Status",
    layout="wide"
)

st.title("Country Intelligence – Project Status")

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

conn = get_connection()

# ── Top Metrics ───────────────────────────────────────────────────────────────
overview = pd.read_sql("""
    SELECT 
        COUNT(*) as datapoints,
        COUNT(DISTINCT indicator_code) as indicators,
        COUNT(DISTINCT iso_numeric) as countries,
        MIN(time_period) as from_year,
        MAX(time_period) as to_year
    FROM indicators
""", conn).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Datapoints", f"{int(overview.datapoints):,}")
c2.metric("Indicators loaded", int(overview.indicators))
c3.metric("Countries", f"{int(overview.countries)} / 249")
c4.metric("Time range", f"{overview.from_year} – {overview.to_year}")

st.divider()

# ── Domain Overview ───────────────────────────────────────────────────────────
st.subheader("By Domain")

domain_df = pd.read_sql("""
    SELECT 
        COALESCE(im.domain, '— unmapped —') as domain,
        COALESCE(im.dimension, '—') as dimension,
        COUNT(DISTINCT im.indicator_code) as indicators,
        COUNT(i.id) as datapoints,
        ROUND(AVG(sub.countries)) as avg_countries
    FROM indicator_metadata im
    LEFT JOIN indicators i ON im.indicator_code = i.indicator_code
    LEFT JOIN (
        SELECT indicator_code, COUNT(DISTINCT iso_numeric) as countries
        FROM indicators GROUP BY indicator_code
    ) sub ON im.indicator_code = sub.indicator_code
    GROUP BY im.domain, im.dimension
    ORDER BY im.domain NULLS LAST, im.dimension
""", conn)

st.dataframe(
    domain_df.rename(columns={
        'domain': 'Domain',
        'dimension': 'Dimension',
        'indicators': 'Indicators',
        'datapoints': 'Datapoints',
        'avg_countries': 'Ø Countries'
    }),
    use_container_width=True,
    hide_index=True,
    height=400
)

st.divider()

# ── Indicator Detail ──────────────────────────────────────────────────────────
st.subheader("Indicator Detail")

col1, col2 = st.columns([1, 3])
with col1:
    domains = ['All'] + sorted(
        domain_df[domain_df['domain'] != '— unmapped —']['domain'].unique().tolist()
    )
    selected = st.selectbox("Domain", domains)

indicator_df = pd.read_sql("""
    SELECT 
        im.indicator_code as code,
        im.name,
        COALESCE(im.domain, '— unmapped —') as domain,
        COALESCE(im.dimension, '—') as dimension,
        COUNT(DISTINCT i.iso_numeric) as countries,
        MIN(i.time_period) as from_year,
        MAX(i.time_period) as to_year
    FROM indicator_metadata im
    LEFT JOIN indicators i ON im.indicator_code = i.indicator_code
    GROUP BY im.indicator_code, im.name, im.domain, im.dimension
    ORDER BY im.domain NULLS LAST, im.dimension, im.name
""", conn)

if selected != 'All':
    indicator_df = indicator_df[indicator_df['domain'] == selected]

st.dataframe(
    indicator_df.rename(columns={
        'code': 'Code', 'name': 'Name', 'domain': 'Domain',
        'dimension': 'Dimension', 'countries': 'Countries',
        'from_year': 'From', 'to_year': 'To'
    }),
    use_container_width=True,
    hide_index=True,
    height=500
)

st.divider()

# ── Country Coverage ──────────────────────────────────────────────────────────
st.subheader("Country Coverage")

coverage_df = pd.read_sql("""
    SELECT 
        c.name,
        c.region,
        c.subregion,
        COUNT(DISTINCT i.indicator_code) as indicators,
        ROUND(COUNT(DISTINCT i.indicator_code)::numeric / 
            (SELECT COUNT(*) FROM indicator_metadata) * 100, 1) as coverage_pct
    FROM countries c
    LEFT JOIN indicators i ON c.iso_numeric = i.iso_numeric
    GROUP BY c.name, c.region, c.subregion
    ORDER BY indicators DESC
""", conn)

col1, col2 = st.columns([1, 3])
with col1:
    regions = ['All'] + sorted(coverage_df['region'].dropna().unique().tolist())
    selected_region = st.selectbox("Region", regions)

if selected_region != 'All':
    coverage_df = coverage_df[coverage_df['region'] == selected_region]

st.dataframe(
    coverage_df.rename(columns={
        'name': 'Country', 'region': 'Region',
        'subregion': 'Subregion', 'indicators': 'Indicators',
        'coverage_pct': 'Coverage %'
    }),
    use_container_width=True,
    hide_index=True,
    height=400
)