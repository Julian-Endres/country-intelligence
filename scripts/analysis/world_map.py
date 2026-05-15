import psycopg2
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)

# Daten aus Datenbank laden
query = """
    SELECT 
        c.name,
        c.iso_code_3,
        c.region,
        i.value AS gdp_per_capita
    FROM indicators i
    JOIN countries c ON i.iso_numeric = c.iso_numeric
    WHERE i.indicator_code = 'WB:NY.GDP.PCAP.CD'
"""

df = pd.read_sql(query, conn)
conn.close()

print(f"Länder geladen: {len(df)}")
print(df.head())

# Weltkarte erstellen
fig = px.choropleth(
    df,
    locations="iso_code_3",
    color="gdp_per_capita",
    hover_name="name",
    color_continuous_scale="Viridis",
    title="GDP per Capita (World Bank, aktuellstes Jahr)",
    labels={"gdp_per_capita": "BIP pro Kopf (USD)"}
)

fig.update_layout(
    geo=dict(showframe=False, showcoastlines=True),
    coloraxis_colorbar=dict(title="USD")
)

fig.write_html("map.html")
print("Karte gespeichert als map.html")