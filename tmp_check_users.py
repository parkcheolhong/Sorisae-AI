import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL", "")
sync_url = DB_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
eng = create_engine(sync_url)

with eng.connect() as con:
    cols = con.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='users' ORDER BY ordinal_position"
    )).fetchall()
    print("columns:", [c[0] for c in cols])
    rows = con.execute(text("SELECT email, is_active FROM users LIMIT 10")).fetchall()
    for r in rows:
        print(r[0], r[1])
