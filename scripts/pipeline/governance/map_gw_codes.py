import psycopg2
import os
from dotenv import load_dotenv
import country_converter as coco

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT")
)
cur = conn.cursor()

# Spalte anlegen falls nicht vorhanden
cur.execute("""
    ALTER TABLE countries ADD COLUMN IF NOT EXISTS gw_code INT;
""")

# Alle GW-Codes 1-1000 durchmappen (deckt alle realistischen Codes ab)
cc = coco.CountryConverter()
gw_codes = list(range(1, 1000))
mapping = cc.convert(names=gw_codes, src='GWcode', to='ISO3')

matched = 0
for gw, iso3 in zip(gw_codes, mapping):
    if iso3 != 'not found':
        cur.execute("""
            UPDATE countries SET gw_code = %s WHERE iso_code_3 = %s
        """, (gw, iso3))
        if cur.rowcount > 0:
            matched += 1

# Explizite Overrides für die 4 bekannten Edge Cases (analog zu cow_code Konvention)
overrides = {
    345: 'SRB',  # Serbia (Yugoslavia) - COW/GW Konvention
    678: 'YEM',  # Yemen (North Yemen) - vor Vereinigung 1990
    816: 'VNM',  # Vietnam (North Vietnam) - vor Wiedervereinigung 1975
    # 751 Hyderabad: kein moderner ISO-Nachfolger, bewusst NICHT gemappt
}
for gw, iso3 in overrides.items():
    cur.execute("UPDATE countries SET gw_code = %s WHERE iso_code_3 = %s", (gw, iso3))
    print(f"Override gesetzt: GW {gw} -> {iso3}")

conn.commit()
cur.execute("SELECT COUNT(*) FROM countries WHERE gw_code IS NOT NULL")
print(f"\nGesamt gemappt: {cur.fetchone()[0]} Länder")
print(f"Automatisch via coco: {matched}")

cur.close()
conn.close()
