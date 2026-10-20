import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg

load_dotenv()

schema = Path(__file__).with_name("schema.sql").read_text()

with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
    with conn.cursor() as cur:
        cur.execute(schema)
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name;"
        )
        print("Tables in database:", [row[0] for row in cur.fetchall()])