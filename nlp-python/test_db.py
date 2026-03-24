import os
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL", "postgresql://postgres:1234@localhost:5432/legal_db")
print(f"Testing connection to: {DB_URL}")

try:
    with ConnectionPool(conninfo=DB_URL, min_size=1, max_size=1) as pool:
        print("Connected successfully!")
except Exception as e:
    print(f"Connection failed: {e}")
