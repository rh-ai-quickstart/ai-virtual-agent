import os
import sys

import psycopg2

DB_NAME = os.getenv("DB_NAME") or sys.argv[1]
DB_USER = os.getenv("DB_USER") or sys.argv[2]
DB_PASSWORD = os.getenv("DB_PASSWORD") or sys.argv[3]
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
SCHEMA_FILE = os.getenv("SCHEMA_FILE", "/db/schema.sql")

if not (DB_NAME and DB_USER and DB_PASSWORD):
    print("Usage: python init_db.py <DB_NAME> <DB_USER> <DB_PASSWORD>")
    sys.exit(1)

conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)
conn.autocommit = True
cur = conn.cursor()

with open(SCHEMA_FILE, "r") as f:
    sql = f.read()

try:
    cur.execute(sql)
    print("Database schema initialized successfully.")
except Exception as e:
    print("Error initializing database schema:", e)
    sys.exit(1)
finally:
    cur.close()
    conn.close()
