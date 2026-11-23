from pathlib import Path

import psycopg2
import pyarrow.dataset as ds

from config import postgres_config

LOCAL_HOST = "localhost"
LOCAL_PORT = 5434

path = Path(__file__).parent / "parquet_data" / "facility_name_min_time_spent_per_visit_date"

conn = psycopg2.connect(
    host=LOCAL_HOST, port=LOCAL_PORT,
    dbname=postgres_config.db, user=postgres_config.user, password=postgres_config.password,
)
cur = conn.cursor()

cur.execute("SELECT COUNT(DISTINCT facility_name) FROM facilities")
db_all = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(DISTINCT f.facility_name)
    FROM facilities f
    WHERE EXISTS (SELECT 1 FROM visits v WHERE v.facility_id = f.id)
""")
db_with_visits = cur.fetchone()[0]
conn.close()

table = ds.dataset(path, format="parquet").to_table(columns=["facility_name"])
parquet_distinct = len(table.column("facility_name").unique())

print("Distinct facility_name in database (all facilities):", db_all)
print("Distinct facility_name in database (with visits):   ", db_with_visits)
print("Distinct facility_name in Parquet target:           ", parquet_distinct)