import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL", "")
sync_url = DB_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
eng = create_engine(sync_url)
with eng.connect() as con:
    rows = con.execute(text(
        "SELECT email, is_admin, is_staff, is_superuser FROM users WHERE is_admin=true OR is_staff=true OR is_superuser=true LIMIT 10"
    )).fetchall()
    for r in rows:
        print(r)
    if not rows:
        print("No admin users found")
        all_rows = con.execute(text("SELECT email, is_admin FROM users LIMIT 5")).fetchall()
        for r in all_rows: print(r)
