import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

conn = get_connection()

# UI
st.title("🌍 Country Intelligence – Indicator Explorer")
st.markdown("Durchsuche alle verfügbaren Indikatoren aus internationalen Datenquellen.")

# Sidebar Filter
st.sidebar.header("🔧 Filter")

search = st.sidebar.text_input("🔍 Suchbegriff", placeholder="z.B. education, railway...")

categories = pd.read_sql("""
    SELECT DISTINCT category FROM indicator_catalog 
    WHERE category IS NOT NULL AND category != ''
    ORDER BY category
""", conn)
selected_category = st.sidebar.selectbox(
    "📁 Kategorie",
    ["Alle"] + categories['category'].tolist()
)

min_coverage = st.sidebar.slider("🌐 Mindest-Länder (gesamt)", 0, 249, 50)
min_recent = st.sidebar.slider("📅 Mindest-Länder (ab 2015)", 0, 249, 0)
min_year = st.sidebar.slider("📆 Neuestes Jahr mindestens", 2000, 2024, 2010)

# Tabs
tab1, tab2, tab3 = st.tabs(["🔍 Suche", "📊 Kategorien", "🔬 Detail"])

with tab1:
    query = """
        SELECT 
            source_code AS "Code",
            name AS "Name",
            category AS "Kategorie",
            country_coverage AS "Länder",
            coverage_recent AS "Länder ab 2015",
            latest_year AS "Neuestes Jahr",
            source AS "Quelle"
        FROM indicator_catalog
        WHERE country_coverage >= %s
        AND (latest_year >= %s OR latest_year IS NULL)
    """
    params = [min_coverage, min_year]

    if search:
        query += """ AND (
            LOWER(name) LIKE %s OR
            LOWER(description) LIKE %s OR
            LOWER(category) LIKE %s
        )"""
        params.extend([f"%{search.lower()}%"] * 3)

    if selected_category != "Alle":
        query += " AND category = %s"
        params.append(selected_category)

    if min_recent > 0:
        query += " AND coverage_recent >= %s"
        params.append(min_recent)

    query += " ORDER BY country_coverage DESC NULLS LAST LIMIT 50"

    df = pd.read_sql(query, conn, params=params)
    st.markdown(f"**{len(df)} Ergebnisse**")
    st.dataframe(df, use_container_width=True)

with tab2:
    cat_df = pd.read_sql("""
        SELECT 
            category AS "Kategorie",
            COUNT(*) AS "Total",
            COUNT(country_coverage) AS "Gecheckt",
            ROUND(AVG(country_coverage)::numeric, 0) AS "Ø Länder",
            ROUND(AVG(coverage_recent)::numeric, 0) AS "Ø Länder ab 2015",
            MAX(latest_year) AS "Neuestes Jahr"
        FROM indicator_catalog
        GROUP BY category
        ORDER BY ROUND(AVG(country_coverage)::numeric, 0) DESC NULLS LAST
    """, conn)
    st.dataframe(cat_df, use_container_width=True)

with tab3:
    check_code = st.text_input("Code eingeben:", placeholder="z.B. WB:SP.DYN.LE00.IN")
    if check_code:
        result = pd.read_sql("""
            SELECT name, category, country_coverage, coverage_recent, 
                   latest_year, description, source
            FROM indicator_catalog
            WHERE source_code = %s
        """, conn, params=[check_code])
        
        if not result.empty:
            row = result.iloc[0]
            col1, col2, col3 = st.columns(3)
            col1.metric("Länder gesamt", f"{row['country_coverage'] or '?'}/249")
            col2.metric("Länder ab 2015", f"{row['coverage_recent'] or '?'}/249")
            col3.metric("Neuestes Jahr", row['latest_year'] or '?')
            st.write(f"**Name:** {row['name']}")
            st.write(f"**Kategorie:** {row['category']}")
            st.write(f"**Quelle:** {row['source']}")
            if row['description']:
                st.write(f"**Beschreibung:** {row['description'][:400]}...")
        else:
            st.warning("Code nicht gefunden.")