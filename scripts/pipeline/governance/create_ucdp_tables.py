import psycopg2
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
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS conflicts_state (
    episode_id SERIAL PRIMARY KEY,
    conflict_id INT,
    country_iso VARCHAR(3),
    gwno_loc INT,
    year INT,
    side_a TEXT,
    side_b TEXT,
    incompatibility SMALLINT,
    intensity_level SMALLINT,
    type_of_conflict SMALLINT,
    start_date DATE,
    ep_end BOOLEAN,
    ep_end_date DATE,
    bd_best INT,
    bd_low INT,
    bd_high INT,
    source VARCHAR(20) DEFAULT 'UCDP'
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS conflicts_state_actors (
    id SERIAL PRIMARY KEY,
    conflict_id INT,
    year INT,
    actor_name TEXT,
    actor_role VARCHAR(10)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS conflicts_nonstate (
    episode_id SERIAL PRIMARY KEY,
    conflict_id INT,
    country_iso VARCHAR(3),
    gwno_loc INT,
    year INT,
    side_a TEXT,
    side_b TEXT,
    fatality_best INT,
    fatality_low INT,
    fatality_high INT,
    start_date DATE,
    ep_end BOOLEAN,
    ep_end_date DATE,
    source VARCHAR(20) DEFAULT 'UCDP'
);
""")

conn.commit()
print("Tabellen angelegt.")
cur.close()
conn.close()
