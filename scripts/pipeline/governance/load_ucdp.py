import pandas as pd
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

DATA_DIR = "data/raw/governance/UCDP"

# --- Gleditsch-Ward -> ISO3 Mapping aus DB laden ---
cur.execute("SELECT gw_code, iso_code_3 FROM countries WHERE gw_code IS NOT NULL")
gw_to_iso = {row[0]: row[1] for row in cur.fetchall()}

def gw_lookup(gw_code):
    try:
        return gw_to_iso.get(int(gw_code))
    except (ValueError, TypeError):
        return None

def clean_date(val):
    if pd.isna(val) or val == '':
        return None
    return val

def clean_int(val):
    if pd.isna(val):
        return None
    return int(val)

# --- 1. UcdpPrioConflict laden ---
print("Lade UcdpPrioConflict...")
df_conf = pd.read_csv(f"{DATA_DIR}/UcdpPrioConflict_v26_1.csv")

inserted = 0
for _, row in df_conf.iterrows():
    gw = str(row['gwno_loc']).strip().split(',')[0]  # erste Location falls mehrere
    iso3 = gw_lookup(gw)
    if not iso3:
        continue  # z.B. Hyderabad (751) - kein moderner Staat

    cur.execute("""
        INSERT INTO conflicts_state
        (conflict_id, country_iso, gwno_loc, year, side_a, side_b,
         incompatibility, intensity_level, type_of_conflict,
         start_date, ep_end, ep_end_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        clean_int(row['conflict_id']), iso3, clean_int(gw), clean_int(row['year']),
        row['side_a'], row['side_b'],
        clean_int(row['incompatibility']), clean_int(row['intensity_level']),
        clean_int(row['type_of_conflict']),
        clean_date(row['start_date']), bool(row['ep_end']) if not pd.isna(row['ep_end']) else None,
        clean_date(row['ep_end_date'])
    ))
    inserted += 1

conn.commit()
print(f"  {inserted} Zeilen in conflicts_state")

# --- 2. BattleDeaths dazu-joinen (Update auf bestehende Zeilen) ---
print("Lade BattleDeaths...")
df_bd = pd.read_csv(f"{DATA_DIR}/BattleDeaths_v26_1_conf.csv")

updated = 0
for _, row in df_bd.iterrows():
    cur.execute("""
        UPDATE conflicts_state
        SET bd_best = %s, bd_low = %s, bd_high = %s
        WHERE conflict_id = %s AND year = %s
    """, (
        clean_int(row['bd_best']), clean_int(row['bd_low']), clean_int(row['bd_high']),
        clean_int(row['conflict_id']), clean_int(row['year'])
    ))
    if cur.rowcount > 0:
        updated += 1

conn.commit()
print(f"  {updated} Zeilen mit Battle Deaths aktualisiert")

# --- 3. Actors aus side_b extrahieren (comma-separated aufsplitten) ---
print("Extrahiere Actors...")
actor_count = 0
for _, row in df_conf.iterrows():
    if pd.isna(row['side_b']):
        continue
    actors = [a.strip() for a in str(row['side_b']).split(',')]
    for actor in actors:
        cur.execute("""
            INSERT INTO conflicts_state_actors (conflict_id, year, actor_name, actor_role)
            VALUES (%s, %s, %s, 'side_b')
        """, (clean_int(row['conflict_id']), clean_int(row['year']), actor))
        actor_count += 1

conn.commit()
print(f"  {actor_count} Actor-Einträge")

# --- 4. NonState Conflicts laden ---
print("Lade NonState...")
df_ns = pd.read_csv(f"{DATA_DIR}/NonState_v26_1.csv")

ns_inserted = 0
for _, row in df_ns.iterrows():
    gw = str(row['gwno_location']).strip().split(',')[0]
    iso3 = gw_lookup(gw)
    if not iso3:
        continue

    cur.execute("""
        INSERT INTO conflicts_nonstate
        (conflict_id, country_iso, gwno_loc, year, side_a, side_b,
         fatality_best, fatality_low, fatality_high,
         start_date, ep_end, ep_end_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        clean_int(row['conflict_id']), iso3, clean_int(gw), clean_int(row['year']),
        row['side_a_name'], row['side_b_name'],
        clean_int(row['best_fatality_estimate']), clean_int(row['low_fatality_estimate']),
        clean_int(row['high_fatality_estimate']),
        clean_date(row['start_date']), bool(row['ep_end']) if not pd.isna(row['ep_end']) else None,
        clean_date(row['ep_end_date'])
    ))
    ns_inserted += 1

conn.commit()
print(f"  {ns_inserted} Zeilen in conflicts_nonstate")

cur.close()
conn.close()
print("\nFertig!")
