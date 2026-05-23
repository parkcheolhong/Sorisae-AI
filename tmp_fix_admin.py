import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DATABASE_URL", "")
sync_url = DB_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
eng = create_engine(sync_url)
with eng.connect() as con:
    con.execute(text(
        "UPDATE users SET is_admin=true, is_active=true WHERE email='ui.admin.round@devanalysis.local'"
    ))
    con.commit()
    rows = con.execute(text(
        "SELECT email, is_admin, is_active, is_superuser FROM users WHERE email='ui.admin.round@devanalysis.local'"
    )).fetchall()
    for r in rows:
        print("Updated:", r)
